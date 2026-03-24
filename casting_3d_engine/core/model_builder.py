"""
模型构建器模块

负责从2D特征数据构建3D模型
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from uuid import uuid4

from .types import (
    FeatureType, Point3D, Vector3D, Plane, Profile2D,
    ExtrudeParameters, RevolveParameters, HoleParameters,
    DraftParameters, BooleanParameters
)
from .geometry_kernel import GeometryKernel
from .feature_base import Feature, FeatureFactory
from .features import (
    ExtrudeFeature, RevolveFeature, HoleFeature,
    BooleanFeature, DraftFeature
)
from .feature_manager import FeatureManager

logger = logging.getLogger(__name__)


class ModelBuilder:
    """
    模型构建器
    负责从2D特征数据构建3D模型
    """
    
    def __init__(self, kernel: GeometryKernel, 
                 feature_manager: FeatureManager):
        self._kernel = kernel
        self._feature_manager = feature_manager
        
    def build_from_2d_data(self, data: Dict[str, Any]) -> Optional[str]:
        """
        从2D数据构建3D模型
        
        Args:
            data: 包含2D特征数据的字典
                {
                    'base_profile': Profile2D,  # 基体轮廓
                    'features': [  # 附加特征列表
                        {'type': 'hole', 'center': Point3D, ...},
                        {'type': 'slot', ...},
                        ...
                    ],
                    'dimensions': {  # 尺寸信息
                        'depth': float,
                        'draft_angle': float,
                        ...
                    },
                    'symmetry': {  # 对称性信息
                        'has_symmetry': bool,
                        'symmetry_axis': str
                    }
                }
        
        Returns:
            生成的实体形状ID
        """
        try:
            # 1. 创建基体特征
            base_feature = self._create_base_feature(data)
            if base_feature is None:
                logger.error("Failed to create base feature")
                return None
            
            self._feature_manager.add_feature(base_feature)
            base_result = base_feature.build()
            
            if base_result is None:
                logger.error("Base feature build failed")
                self._feature_manager.remove_feature(base_feature.feature_id)
                return None
            
            body_id = base_feature.feature_id
            current_shape_id = body_id
            
            # 2. 添加附加特征
            for feature_data in data.get('features', []):
                feature = self._create_feature(feature_data, body_id)
                if feature:
                    self._feature_manager.add_feature(feature)
                    feature_result = feature.build()
                    
                    if feature_result is None:
                        logger.warning(f"Feature build failed: {feature.feature_type.name}")
                        continue
                    
                    # 执行布尔运算
                    bool_result = self._apply_boolean(feature, current_shape_id)
                    if bool_result:
                        current_shape_id = bool_result
            
            # 3. 应用铸造专用特征
            casting_result = self._apply_casting_features(data, current_shape_id)
            if casting_result:
                current_shape_id = casting_result
            
            logger.info(f"Model built successfully: {current_shape_id[:8]}")
            return current_shape_id
            
        except Exception as e:
            logger.error(f"Build from 2D data failed: {e}")
            return None
    
    def _create_base_feature(self, data: Dict[str, Any]) -> Optional[Feature]:
        """创建基体特征"""
        profile = data.get('base_profile')
        if profile is None:
            logger.error("No base profile provided")
            return None
        
        # 根据轮廓类型选择建模方式
        base_type = data.get('base_type', 'extrude')
        dimensions = data.get('dimensions', {})
        
        if base_type == 'extrude':
            params = ExtrudeParameters(
                feature_id=str(uuid4()),
                feature_type=FeatureType.EXTRUDE,
                profile=profile,
                depth=dimensions.get('depth', 10.0),
                taper_angle=dimensions.get('draft_angle', 0.0)
            )
            return ExtrudeFeature(params, self._kernel)
        
        elif base_type == 'revolve':
            params = RevolveParameters(
                feature_id=str(uuid4()),
                feature_type=FeatureType.REVOLVE,
                profile=profile,
                axis_origin=data.get('axis_origin', Point3D()),
                axis_direction=data.get('axis_direction', Vector3D(0, 0, 1)),
                angle=dimensions.get('angle', 360.0)
            )
            return RevolveFeature(params, self._kernel)
        
        else:
            logger.error(f"Unknown base type: {base_type}")
            return None
    
    def _create_feature(self, feature_data: Dict[str, Any], 
                        body_id: str) -> Optional[Feature]:
        """创建附加特征"""
        feature_type = feature_data.get('type')
        
        if feature_type == 'hole':
            params = HoleParameters(
                feature_id=str(uuid4()),
                feature_type=FeatureType.HOLE,
                center=feature_data.get('center', Point3D()),
                direction=feature_data.get('direction', Vector3D(0, 0, 1)),
                diameter=feature_data.get('diameter', 10.0),
                depth=feature_data.get('depth', 0),
                hole_type=feature_data.get('hole_type', 'simple'),
                counterbore_diameter=feature_data.get('counterbore_diameter', 0),
                counterbore_depth=feature_data.get('counterbore_depth', 0),
                countersink_angle=feature_data.get('countersink_angle', 90)
            )
            return HoleFeature(params, self._kernel)
        
        elif feature_type == 'slot':
            # 槽特征实现
            return self._create_slot_feature(feature_data)
        
        elif feature_type == 'pocket':
            # 腔体特征实现
            return self._create_pocket_feature(feature_data)
        
        elif feature_type == 'boss':
            # 凸台特征实现
            return self._create_boss_feature(feature_data)
        
        else:
            logger.warning(f"Unknown feature type: {feature_type}")
            return None
    
    def _create_slot_feature(self, data: Dict[str, Any]) -> Optional[Feature]:
        """创建槽特征"""
        # 槽可以看作是一个拉伸切除
        # 创建槽的轮廓
        center = data.get('center', Point3D())
        width = data.get('width', 5.0)
        length = data.get('length', 20.0)
        angle = data.get('angle', 0.0)
        depth = data.get('depth', 10.0)
        
        import math
        cos_a = math.cos(math.radians(angle))
        sin_a = math.sin(math.radians(angle))
        
        # 计算槽的四个角点
        half_w = width / 2
        half_l = length / 2
        
        vertices = [
            Point3D(center.x - half_l * cos_a + half_w * sin_a,
                   center.y - half_l * sin_a - half_w * cos_a, 0),
            Point3D(center.x + half_l * cos_a + half_w * sin_a,
                   center.y + half_l * sin_a - half_w * cos_a, 0),
            Point3D(center.x + half_l * cos_a - half_w * sin_a,
                   center.y + half_l * sin_a + half_w * cos_a, 0),
            Point3D(center.x - half_l * cos_a - half_w * sin_a,
                   center.y - half_l * sin_a + half_w * cos_a, 0),
        ]
        
        profile = Profile2D(vertices=vertices, is_closed=True)
        
        params = ExtrudeParameters(
            feature_id=str(uuid4()),
            feature_type=FeatureType.EXTRUDE,
            profile=profile,
            depth=depth,
            is_cut=True
        )
        
        return ExtrudeFeature(params, self._kernel)
    
    def _create_pocket_feature(self, data: Dict[str, Any]) -> Optional[Feature]:
        """创建腔体特征"""
        # 腔体类似于槽，但可以有更复杂的形状
        profile = data.get('profile')
        if profile is None:
            return None
        
        params = ExtrudeParameters(
            feature_id=str(uuid4()),
            feature_type=FeatureType.EXTRUDE,
            profile=profile,
            depth=data.get('depth', 5.0),
            is_cut=True
        )
        
        return ExtrudeFeature(params, self._kernel)
    
    def _create_boss_feature(self, data: Dict[str, Any]) -> Optional[Feature]:
        """创建凸台特征"""
        profile = data.get('profile')
        if profile is None:
            # 创建圆形凸台
            center = data.get('center', Point3D())
            radius = data.get('radius', 5.0)
            
            # 创建圆形轮廓
            import math
            vertices = []
            num_segments = 32
            for i in range(num_segments):
                angle = 2 * math.pi * i / num_segments
                x = center.x + radius * math.cos(angle)
                y = center.y + radius * math.sin(angle)
                vertices.append(Point3D(x, y, 0))
            
            profile = Profile2D(vertices=vertices, is_closed=True)
        
        params = ExtrudeParameters(
            feature_id=str(uuid4()),
            feature_type=FeatureType.EXTRUDE,
            profile=profile,
            depth=data.get('height', 5.0),
            is_cut=False
        )
        
        return ExtrudeFeature(params, self._kernel)
    
    def _apply_boolean(self, feature: Feature, 
                       current_shape_id: str) -> Optional[str]:
        """应用布尔运算"""
        feature_type = feature.feature_type
        
        # 切除特征
        if feature_type in [FeatureType.HOLE, FeatureType.SLOT, FeatureType.POCKET]:
            bool_params = BooleanParameters(
                feature_id=str(uuid4()),
                feature_type=FeatureType.BOOLEAN_SUBTRACT,
                target_body_id=current_shape_id,
                tool_body_id=feature.feature_id,
                operation='subtract'
            )
            bool_feature = BooleanFeature(bool_params, self._kernel)
            self._feature_manager.add_feature(bool_feature)
            result = bool_feature.build()
            
            if result:
                return result
            else:
                logger.warning("Boolean subtract failed")
        
        # 添加特征
        elif feature_type in [FeatureType.BOSS]:
            bool_params = BooleanParameters(
                feature_id=str(uuid4()),
                feature_type=FeatureType.BOOLEAN_UNION,
                target_body_id=current_shape_id,
                tool_body_id=feature.feature_id,
                operation='union'
            )
            bool_feature = BooleanFeature(bool_params, self._kernel)
            self._feature_manager.add_feature(bool_feature)
            result = bool_feature.build()
            
            if result:
                return result
            else:
                logger.warning("Boolean union failed")
        
        return None
    
    def _apply_casting_features(self, data: Dict[str, Any], 
                                body_id: str) -> Optional[str]:
        """应用铸造专用特征"""
        current_shape_id = body_id
        
        # 应用拔模斜度
        draft_data = data.get('draft')
        if draft_data:
            params = DraftParameters(
                feature_id=str(uuid4()),
                feature_type=FeatureType.DRAFT,
                face_ids=draft_data.get('face_ids', []),
                neutral_plane=draft_data.get('neutral_plane', Plane()),
                pull_direction=draft_data.get('pull_direction', Vector3D(0, 0, 1)),
                draft_angle=draft_data.get('angle', 2.0),
                is_inward=draft_data.get('is_inward', True)
            )
            draft_feature = DraftFeature(params, self._kernel)
            self._feature_manager.add_feature(draft_feature)
            draft_feature.build()
        
        # 应用分型面
        parting_data = data.get('parting_surface')
        if parting_data:
            # 分型面实现
            pass
        
        # 应用加强筋
        ribs_data = data.get('ribs', [])
        for rib_data in ribs_data:
            # 加强筋实现
            pass
        
        return current_shape_id
    
    def build_primitive_box(self, corner: Point3D, 
                            dimensions: Tuple[float, float, float]) -> Optional[str]:
        """构建基本体-立方体"""
        from .types import PrimitiveBoxParameters
        from .features import PrimitiveBoxFeature
        
        params = PrimitiveBoxParameters(
            feature_id=str(uuid4()),
            feature_type=FeatureType.PRIMITIVE_BOX,
            corner=corner,
            dimensions=dimensions
        )
        
        feature = PrimitiveBoxFeature(params, self._kernel)
        self._feature_manager.add_feature(feature)
        return feature.build()
    
    def build_primitive_cylinder(self, center: Point3D, axis: Vector3D,
                                  radius: float, height: float) -> Optional[str]:
        """构建基本体-圆柱"""
        from .types import PrimitiveCylinderParameters
        from .features import PrimitiveCylinderFeature
        
        params = PrimitiveCylinderParameters(
            feature_id=str(uuid4()),
            feature_type=FeatureType.PRIMITIVE_CYLINDER,
            center=center,
            axis=axis,
            radius=radius,
            height=height
        )
        
        feature = PrimitiveCylinderFeature(params, self._kernel)
        self._feature_manager.add_feature(feature)
        return feature.build()
    
    def build_primitive_sphere(self, center: Point3D, 
                               radius: float) -> Optional[str]:
        """构建基本体-球体"""
        from .types import PrimitiveSphereParameters
        from .features import PrimitiveSphereFeature
        
        params = PrimitiveSphereParameters(
            feature_id=str(uuid4()),
            feature_type=FeatureType.PRIMITIVE_SPHERE,
            center=center,
            radius=radius
        )
        
        feature = PrimitiveSphereFeature(params, self._kernel)
        self._feature_manager.add_feature(feature)
        return feature.build()
    
    def create_symmetric_model(self, profile: Profile2D, 
                               axis: str = 'y',
                               dimensions: Dict[str, float] = None) -> Optional[str]:
        """
        创建对称模型
        
        Args:
            profile: 半边轮廓
            axis: 对称轴 ('x' 或 'y')
            dimensions: 尺寸信息
        
        Returns:
            生成的形状ID
        """
        if dimensions is None:
            dimensions = {}
        
        # 镜像轮廓
        mirrored_profile = self._mirror_profile(profile, axis)
        
        # 合并轮廓
        full_profile = Profile2D(
            vertices=profile.vertices + mirrored_profile.vertices[::-1],
            is_closed=True
        )
        
        # 创建拉伸特征
        data = {
            'base_profile': full_profile,
            'base_type': 'extrude',
            'dimensions': dimensions
        }
        
        return self.build_from_2d_data(data)
    
    def _mirror_profile(self, profile: Profile2D, 
                        axis: str) -> Profile2D:
        """镜像轮廓"""
        mirrored_vertices = []
        
        for v in profile.vertices:
            if axis == 'x':
                mirrored_vertices.append(Point3D(v.x, -v.y, v.z))
            else:  # axis == 'y'
                mirrored_vertices.append(Point3D(-v.x, v.y, v.z))
        
        return Profile2D(
            vertices=mirrored_vertices,
            is_closed=profile.is_closed
        )
