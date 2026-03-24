"""
输入接口模块

定义与图像分析模块的接口，将2D特征数据转换为建模引擎输入
"""

import logging
from typing import Dict, List, Optional, Tuple, Any, Protocol
import math

from ..core.types import (
    FeatureType, Point3D, Vector3D, Plane, Profile2D, GeometryType
)

logger = logging.getLogger(__name__)


class ImageAnalysisOutput(Protocol):
    """
    图像分析模块输出接口协议
    
    图像分析模块应实现此接口以与建模引擎集成
    """
    
    def get_contours(self) -> List[Profile2D]:
        """获取检测到的轮廓列表"""
        ...
    
    def get_features(self) -> List[Dict[str, Any]]:
        """获取特征分类信息"""
        ...
    
    def get_dimensions(self) -> Dict[str, float]:
        """获取尺寸信息"""
        ...
    
    def get_symmetry(self) -> Dict[str, Any]:
        """获取对称性信息"""
        ...
    
    def get_constraints(self) -> List[Dict[str, Any]]:
        """获取约束信息"""
        ...


class ModelBuilderInput:
    """
    模型构建器输入数据类
    
    将图像分析输出转换为建模引擎输入格式
    """
    
    def __init__(self, image_analysis: ImageAnalysisOutput):
        """
        初始化
        
        Args:
            image_analysis: 图像分析模块输出
        """
        self._image_analysis = image_analysis
        self._data = self._convert()
    
    def _convert(self) -> Dict[str, Any]:
        """转换数据格式"""
        contours = self._image_analysis.get_contours()
        features = self._image_analysis.get_features()
        dimensions = self._image_analysis.get_dimensions()
        symmetry = self._image_analysis.get_symmetry()
        constraints = self._image_analysis.get_constraints()
        
        # 确定基体轮廓
        base_profile = self._select_base_profile(contours)
        
        # 转换特征
        converted_features = self._convert_features(features)
        
        # 确定建模方式
        base_type = self._determine_base_type(contours, symmetry)
        
        # 处理对称性
        if symmetry.get('has_symmetry', False):
            base_profile = self._apply_symmetry(base_profile, symmetry)
        
        return {
            'base_profile': base_profile,
            'features': converted_features,
            'dimensions': dimensions,
            'symmetry': symmetry,
            'constraints': constraints,
            'base_type': base_type,
            'depth': dimensions.get('depth', 10.0),
            'draft_angle': dimensions.get('draft_angle', 0.0),
            'wall_thickness': dimensions.get('wall_thickness', 0.0)
        }
    
    def _select_base_profile(self, contours: List[Profile2D]) -> Profile2D:
        """
        选择基体轮廓（最大的封闭轮廓）
        
        Args:
            contours: 轮廓列表
        
        Returns:
            选中的基体轮廓
        """
        if not contours:
            logger.warning("No contours provided")
            return Profile2D()
        
        # 计算每个轮廓的面积
        def calculate_area(profile: Profile2D) -> float:
            if len(profile.vertices) < 3:
                return 0.0
            return profile.calculate_area()
        
        # 选择最大的封闭轮廓
        closed_contours = [c for c in contours if c.is_closed]
        if closed_contours:
            base = max(closed_contours, key=calculate_area)
            logger.info(f"Selected base profile with area {calculate_area(base):.2f}")
            return base
        
        # 如果没有封闭轮廓，使用最大的开放轮廓
        if contours:
            base = max(contours, key=calculate_area)
            logger.warning(f"Using open contour as base (area: {calculate_area(base):.2f})")
            return base
        
        return Profile2D()
    
    def _convert_features(self, features: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        转换特征数据
        
        Args:
            features: 图像分析输出的特征列表
        
        Returns:
            转换后的特征列表
        """
        converted = []
        
        for feature in features:
            feature_type = feature.get('type')
            
            if feature_type == 'hole':
                converted.append(self._convert_hole_feature(feature))
            elif feature_type == 'slot':
                converted.append(self._convert_slot_feature(feature))
            elif feature_type == 'pocket':
                converted.append(self._convert_pocket_feature(feature))
            elif feature_type == 'boss':
                converted.append(self._convert_boss_feature(feature))
            elif feature_type == 'fillet':
                converted.append(self._convert_fillet_feature(feature))
            elif feature_type == 'chamfer':
                converted.append(self._convert_chamfer_feature(feature))
            else:
                logger.warning(f"Unknown feature type: {feature_type}")
        
        return converted
    
    def _convert_hole_feature(self, feature: Dict[str, Any]) -> Dict[str, Any]:
        """转换孔特征"""
        return {
            'type': 'hole',
            'center': Point3D(
                feature.get('center_x', 0),
                feature.get('center_y', 0),
                0
            ),
            'diameter': feature.get('diameter', 10.0),
            'depth': feature.get('depth', 0),
            'direction': Vector3D(0, 0, 1),
            'hole_type': feature.get('hole_type', 'simple'),
            'counterbore_diameter': feature.get('counterbore_diameter', 0),
            'counterbore_depth': feature.get('counterbore_depth', 0),
            'countersink_angle': feature.get('countersink_angle', 90)
        }
    
    def _convert_slot_feature(self, feature: Dict[str, Any]) -> Dict[str, Any]:
        """转换槽特征"""
        return {
            'type': 'slot',
            'center': Point3D(
                feature.get('center_x', 0),
                feature.get('center_y', 0),
                0
            ),
            'width': feature.get('width', 5.0),
            'length': feature.get('length', 20.0),
            'angle': feature.get('angle', 0),
            'depth': feature.get('depth', 5.0),
            'direction': Vector3D(0, 0, 1)
        }
    
    def _convert_pocket_feature(self, feature: Dict[str, Any]) -> Dict[str, Any]:
        """转换腔体特征"""
        profile = feature.get('profile')
        if profile is None:
            # 创建矩形腔体轮廓
            center = Point3D(
                feature.get('center_x', 0),
                feature.get('center_y', 0),
                0
            )
            width = feature.get('width', 10.0)
            height = feature.get('height', 10.0)
            
            profile = Profile2D(
                vertices=[
                    Point3D(center.x - width/2, center.y - height/2, 0),
                    Point3D(center.x + width/2, center.y - height/2, 0),
                    Point3D(center.x + width/2, center.y + height/2, 0),
                    Point3D(center.x - width/2, center.y + height/2, 0)
                ],
                is_closed=True
            )
        
        return {
            'type': 'pocket',
            'profile': profile,
            'depth': feature.get('depth', 5.0),
            'direction': Vector3D(0, 0, 1)
        }
    
    def _convert_boss_feature(self, feature: Dict[str, Any]) -> Dict[str, Any]:
        """转换凸台特征"""
        return {
            'type': 'boss',
            'center': Point3D(
                feature.get('center_x', 0),
                feature.get('center_y', 0),
                0
            ),
            'radius': feature.get('radius', 5.0),
            'height': feature.get('height', 5.0),
            'direction': Vector3D(0, 0, 1)
        }
    
    def _convert_fillet_feature(self, feature: Dict[str, Any]) -> Dict[str, Any]:
        """转换圆角特征"""
        return {
            'type': 'fillet',
            'edge_ids': feature.get('edge_ids', []),
            'radius': feature.get('radius', 2.0)
        }
    
    def _convert_chamfer_feature(self, feature: Dict[str, Any]) -> Dict[str, Any]:
        """转换倒角特征"""
        return {
            'type': 'chamfer',
            'edge_ids': feature.get('edge_ids', []),
            'distance': feature.get('distance', 1.0)
        }
    
    def _determine_base_type(self, contours: List[Profile2D], 
                             symmetry: Dict[str, Any]) -> str:
        """
        确定基体类型
        
        根据轮廓形状和对称性决定建模方式
        """
        # 如果有旋转对称性，使用旋转
        if symmetry.get('has_rotational_symmetry', False):
            return 'revolve'
        
        # 检查轮廓是否适合旋转
        for contour in contours:
            if len(contour.vertices) >= 3:
                # 检查是否所有点都在一个平面内
                center = contour.get_center()
                # 简化：假设XY平面
                return 'extrude'
        
        return 'extrude'
    
    def _apply_symmetry(self, profile: Profile2D, 
                        symmetry: Dict[str, Any]) -> Profile2D:
        """
        应用对称性
        
        如果检测到对称性，镜像轮廓以创建完整形状
        """
        if not symmetry.get('has_symmetry', False):
            return profile
        
        axis = symmetry.get('symmetry_axis', 'y')
        
        # 镜像顶点
        mirrored_vertices = []
        for v in profile.vertices:
            if axis == 'x':
                mirrored_vertices.append(Point3D(v.x, -v.y, v.z))
            else:  # axis == 'y' or default
                mirrored_vertices.append(Point3D(-v.x, v.y, v.z))
        
        # 合并轮廓（原始 + 镜像，镜像逆序）
        merged_vertices = profile.vertices + mirrored_vertices[::-1]
        
        return Profile2D(
            vertices=merged_vertices,
            is_closed=True
        )
    
    def get_data(self) -> Dict[str, Any]:
        """获取转换后的数据"""
        return self._data
    
    def get_base_profile(self) -> Profile2D:
        """获取基体轮廓"""
        return self._data['base_profile']
    
    def get_features(self) -> List[Dict[str, Any]]:
        """获取特征列表"""
        return self._data['features']
    
    def get_dimensions(self) -> Dict[str, float]:
        """获取尺寸信息"""
        return self._data['dimensions']
    
    def get_base_type(self) -> str:
        """获取基体类型"""
        return self._data['base_type']


class MockImageAnalysisOutput:
    """
    模拟图像分析输出
    用于测试和演示
    """
    
    def __init__(self):
        """创建模拟数据"""
        self._contours = self._create_mock_contours()
        self._features = self._create_mock_features()
        self._dimensions = self._create_mock_dimensions()
        self._symmetry = self._create_mock_symmetry()
        self._constraints = []
    
    def _create_mock_contours(self) -> List[Profile2D]:
        """创建模拟轮廓"""
        # 创建一个100x80的矩形轮廓
        base_contour = Profile2D(
            vertices=[
                Point3D(0, 0, 0),
                Point3D(100, 0, 0),
                Point3D(100, 80, 0),
                Point3D(0, 80, 0)
            ],
            is_closed=True
        )
        return [base_contour]
    
    def _create_mock_features(self) -> List[Dict[str, Any]]:
        """创建模拟特征"""
        return [
            {
                'type': 'hole',
                'center_x': 30,
                'center_y': 40,
                'diameter': 15,
                'depth': 0  # 通孔
            },
            {
                'type': 'hole',
                'center_x': 70,
                'center_y': 40,
                'diameter': 15,
                'depth': 0
            }
        ]
    
    def _create_mock_dimensions(self) -> Dict[str, float]:
        """创建模拟尺寸"""
        return {
            'width': 100.0,
            'height': 80.0,
            'depth': 25.0,
            'draft_angle': 2.0
        }
    
    def _create_mock_symmetry(self) -> Dict[str, Any]:
        """创建模拟对称性信息"""
        return {
            'has_symmetry': True,
            'symmetry_axis': 'y',
            'has_rotational_symmetry': False
        }
    
    def get_contours(self) -> List[Profile2D]:
        return self._contours
    
    def get_features(self) -> List[Dict[str, Any]]:
        return self._features
    
    def get_dimensions(self) -> Dict[str, float]:
        return self._dimensions
    
    def get_symmetry(self) -> Dict[str, Any]:
        return self._symmetry
    
    def get_constraints(self) -> List[Dict[str, Any]]:
        return self._constraints


class InputValidator:
    """
    输入验证器
    验证2D输入数据的完整性和有效性
    """
    
    @staticmethod
    def validate_profile(profile: Profile2D) -> Tuple[bool, str]:
        """验证轮廓"""
        if not profile.vertices:
            return False, "Profile has no vertices"
        
        if len(profile.vertices) < 2:
            return False, "Profile must have at least 2 vertices"
        
        if profile.is_closed and len(profile.vertices) < 3:
            return False, "Closed profile must have at least 3 vertices"
        
        # 检查是否有重复点
        seen = set()
        for v in profile.vertices:
            key = (round(v.x, 6), round(v.y, 6), round(v.z, 6))
            if key in seen:
                return False, "Profile has duplicate vertices"
            seen.add(key)
        
        return True, ""
    
    @staticmethod
    def validate_dimensions(dimensions: Dict[str, float]) -> Tuple[bool, str]:
        """验证尺寸"""
        required_keys = ['depth']
        for key in required_keys:
            if key not in dimensions:
                return False, f"Missing required dimension: {key}"
        
        if dimensions['depth'] <= 0:
            return False, "Depth must be positive"
        
        return True, ""
    
    @staticmethod
    def validate_input_data(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """验证完整输入数据"""
        errors = []
        
        # 检查基体轮廓
        base_profile = data.get('base_profile')
        if base_profile is None:
            errors.append("Missing base_profile")
        else:
            valid, msg = InputValidator.validate_profile(base_profile)
            if not valid:
                errors.append(f"Invalid base_profile: {msg}")
        
        # 检查尺寸
        dimensions = data.get('dimensions', {})
        valid, msg = InputValidator.validate_dimensions(dimensions)
        if not valid:
            errors.append(f"Invalid dimensions: {msg}")
        
        return len(errors) == 0, errors
