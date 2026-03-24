"""
具体特征实现模块

实现各种具体的建模特征
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

from .types import (
    FeatureType, Point3D, Vector3D, Plane, Profile2D,
    ExtrudeParameters, RevolveParameters, HoleParameters,
    FilletParameters, ChamferParameters, DraftParameters,
    BooleanParameters, PrimitiveBoxParameters,
    PrimitiveCylinderParameters, PrimitiveSphereParameters
)
from .geometry_kernel import GeometryKernel, OCCConverter
from .feature_base import Feature, FeatureFactory

logger = logging.getLogger(__name__)

# OpenCASCADE导入
try:
    from OCC.Core.gp import gp_Pnt, gp_Vec, gp_Dir, gp_Ax1, gp_Ax2
    from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeCylinder
    from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
    from OCC.Core.GC import GC_MakeSegment
    HAS_OCC = True
except ImportError:
    HAS_OCC = False


class ExtrudeFeature(Feature):
    """拉伸特征"""
    
    def __init__(self, params: ExtrudeParameters, kernel: GeometryKernel):
        super().__init__(params, kernel)
        self._params: ExtrudeParameters = params
    
    def validate(self) -> Tuple[bool, str]:
        """验证拉伸参数"""
        if len(self._params.profile.vertices) < 2:
            return False, "Profile must have at least 2 vertices"
        if self._params.depth <= 0:
            return False, "Depth must be positive"
        if abs(self._params.taper_angle) >= 90:
            return False, "Taper angle must be less than 90 degrees"
        if not self._params.profile.is_closed:
            return False, "Profile must be closed for extrusion"
        return True, ""
    
    def build(self) -> Optional[str]:
        """构建拉伸特征"""
        if self._params.is_suppressed:
            return None
        
        valid, msg = self.validate()
        if not valid:
            logger.error(f"Extrude validation failed: {msg}")
            return None
        
        try:
            # 创建线框
            wire = self._kernel.create_wire_from_profile(
                self._params.profile, self._params.plane)
            
            if wire is None:
                logger.error("Failed to create wire from profile")
                return None
            
            # 创建面
            face = self._kernel.create_face_from_wire(wire, self._params.plane)
            
            if face is None:
                logger.error("Failed to create face from wire")
                return None
            
            # 拉伸
            shape = self._kernel.extrude_face(
                face, self._params.direction, 
                self._params.depth, self._params.taper_angle)
            
            if shape is None:
                logger.error("Failed to extrude face")
                return None
            
            # 注册形状
            self._result_shape_id = self._params.feature_id
            self._kernel.register_shape(self._result_shape_id, shape)
            self._is_dirty = False
            
            logger.info(f"Extrude feature built: {self.feature_id[:8]}")
            return self._result_shape_id
            
        except Exception as e:
            logger.error(f"Extrude build failed: {e}")
            return None
    
    def _serialize_parameters(self) -> Dict[str, Any]:
        return {
            'profile': {
                'vertices': [v.to_tuple() for v in self._params.profile.vertices],
                'is_closed': self._params.profile.is_closed,
                'arcs': self._params.profile.arcs,
                'constraints': self._params.profile.constraints
            },
            'plane': {
                'origin': self._params.plane.origin.to_tuple(),
                'normal': self._params.plane.normal.to_tuple(),
                'x_dir': self._params.plane.x_dir.to_tuple()
            },
            'direction': self._params.direction.to_tuple(),
            'depth': self._params.depth,
            'taper_angle': self._params.taper_angle,
            'is_symmetric': self._params.is_symmetric,
            'is_cut': self._params.is_cut,
            'position': self._params.position.to_tuple(),
            'rotation': self._params.rotation
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], 
                  kernel: GeometryKernel) -> 'ExtrudeFeature':
        params_data = data['parameters']
        
        profile = Profile2D(
            vertices=[Point3D(*v) for v in params_data['profile']['vertices']],
            is_closed=params_data['profile']['is_closed'],
            arcs=params_data['profile'].get('arcs', []),
            constraints=params_data['profile'].get('constraints', [])
        )
        
        plane = Plane(
            origin=Point3D(*params_data['plane']['origin']),
            normal=Vector3D(*params_data['plane']['normal']),
            x_dir=Vector3D(*params_data['plane']['x_dir'])
        )
        
        params = ExtrudeParameters(
            feature_id=data['feature_id'],
            feature_type=FeatureType.EXTRUDE,
            name=data.get('name', ''),
            profile=profile,
            plane=plane,
            direction=Vector3D(*params_data['direction']),
            depth=params_data['depth'],
            taper_angle=params_data.get('taper_angle', 0),
            is_symmetric=params_data.get('is_symmetric', False),
            is_cut=params_data.get('is_cut', False),
            position=Point3D(*params_data.get('position', (0, 0, 0))),
            rotation=params_data.get('rotation', (0, 0, 0))
        )
        
        return cls(params, kernel)


class RevolveFeature(Feature):
    """旋转特征"""
    
    def __init__(self, params: RevolveParameters, kernel: GeometryKernel):
        super().__init__(params, kernel)
        self._params: RevolveParameters = params
    
    def validate(self) -> Tuple[bool, str]:
        if len(self._params.profile.vertices) < 2:
            return False, "Profile must have at least 2 vertices"
        if self._params.angle <= 0 or self._params.angle > 360:
            return False, "Angle must be between 0 and 360 degrees"
        return True, ""
    
    def build(self) -> Optional[str]:
        if self._params.is_suppressed:
            return None
        
        valid, msg = self.validate()
        if not valid:
            logger.error(f"Revolve validation failed: {msg}")
            return None
        
        try:
            wire = self._kernel.create_wire_from_profile(
                self._params.profile, Plane())
            
            if wire is None:
                logger.error("Failed to create wire from profile")
                return None
            
            face = self._kernel.create_face_from_wire(wire, Plane())
            
            if face is None:
                logger.error("Failed to create face from wire")
                return None
            
            shape = self._kernel.revolve_face(
                face, self._params.axis_origin,
                self._params.axis_direction, self._params.angle)
            
            if shape is None:
                logger.error("Failed to revolve face")
                return None
            
            self._result_shape_id = self._params.feature_id
            self._kernel.register_shape(self._result_shape_id, shape)
            self._is_dirty = False
            
            logger.info(f"Revolve feature built: {self.feature_id[:8]}")
            return self._result_shape_id
            
        except Exception as e:
            logger.error(f"Revolve build failed: {e}")
            return None
    
    def _serialize_parameters(self) -> Dict[str, Any]:
        return {
            'profile': {
                'vertices': [v.to_tuple() for v in self._params.profile.vertices],
                'is_closed': self._params.profile.is_closed,
                'arcs': self._params.profile.arcs
            },
            'axis_origin': self._params.axis_origin.to_tuple(),
            'axis_direction': self._params.axis_direction.to_tuple(),
            'angle': self._params.angle,
            'is_cut': self._params.is_cut
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], 
                  kernel: GeometryKernel) -> 'RevolveFeature':
        params_data = data['parameters']
        
        profile = Profile2D(
            vertices=[Point3D(*v) for v in params_data['profile']['vertices']],
            is_closed=params_data['profile']['is_closed'],
            arcs=params_data['profile'].get('arcs', [])
        )
        
        params = RevolveParameters(
            feature_id=data['feature_id'],
            feature_type=FeatureType.REVOLVE,
            profile=profile,
            axis_origin=Point3D(*params_data['axis_origin']),
            axis_direction=Vector3D(*params_data['axis_direction']),
            angle=params_data['angle'],
            is_cut=params_data.get('is_cut', False)
        )
        
        return cls(params, kernel)


class HoleFeature(Feature):
    """孔特征"""
    
    def __init__(self, params: HoleParameters, kernel: GeometryKernel):
        super().__init__(params, kernel)
        self._params: HoleParameters = params
    
    def validate(self) -> Tuple[bool, str]:
        if self._params.diameter <= 0:
            return False, "Diameter must be positive"
        if self._params.depth < 0:
            return False, "Depth must be non-negative"
        return True, ""
    
    def build(self) -> Optional[str]:
        if self._params.is_suppressed:
            return None
        
        valid, msg = self.validate()
        if not valid:
            logger.error(f"Hole validation failed: {msg}")
            return None
        
        try:
            # 创建圆柱体作为孔工具
            if HAS_OCC:
                origin = OCCConverter.point_to_gp(self._params.center)
                direction = gp_Dir(self._params.direction.x,
                                  self._params.direction.y,
                                  self._params.direction.z)
                
                # 计算圆柱高度
                height = self._params.depth if self._params.depth > 0 else 1000.0
                
                # 创建圆柱轴
                ax2 = gp_Ax2(origin, direction)
                cylinder = BRepPrimAPI_MakeCylinder(ax2, 
                                                     self._params.diameter / 2, 
                                                     height).Shape()
            else:
                cylinder = None
            
            self._result_shape_id = self._params.feature_id
            self._kernel.register_shape(self._result_shape_id, cylinder)
            self._is_dirty = False
            
            logger.info(f"Hole feature built: {self.feature_id[:8]}")
            return self._result_shape_id
            
        except Exception as e:
            logger.error(f"Hole build failed: {e}")
            return None
    
    def _serialize_parameters(self) -> Dict[str, Any]:
        return {
            'center': self._params.center.to_tuple(),
            'direction': self._params.direction.to_tuple(),
            'diameter': self._params.diameter,
            'depth': self._params.depth,
            'hole_type': self._params.hole_type,
            'counterbore_diameter': self._params.counterbore_diameter,
            'counterbore_depth': self._params.counterbore_depth,
            'countersink_angle': self._params.countersink_angle
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], 
                  kernel: GeometryKernel) -> 'HoleFeature':
        params_data = data['parameters']
        
        params = HoleParameters(
            feature_id=data['feature_id'],
            feature_type=FeatureType.HOLE,
            center=Point3D(*params_data['center']),
            direction=Vector3D(*params_data['direction']),
            diameter=params_data['diameter'],
            depth=params_data['depth'],
            hole_type=params_data.get('hole_type', 'simple'),
            counterbore_diameter=params_data.get('counterbore_diameter', 0),
            counterbore_depth=params_data.get('counterbore_depth', 0),
            countersink_angle=params_data.get('countersink_angle', 90)
        )
        
        return cls(params, kernel)


class FilletFeature(Feature):
    """圆角特征"""
    
    def __init__(self, params: FilletParameters, kernel: GeometryKernel):
        super().__init__(params, kernel)
        self._params: FilletParameters = params
    
    def validate(self) -> Tuple[bool, str]:
        if not self._params.edge_ids:
            return False, "At least one edge must be selected"
        if self._params.radius <= 0:
            return False, "Radius must be positive"
        return True, ""
    
    def build(self) -> Optional[str]:
        if self._params.is_suppressed:
            return None
        
        valid, msg = self.validate()
        if not valid:
            logger.error(f"Fillet validation failed: {msg}")
            return None
        
        # 圆角需要父形状，这里简化处理
        logger.info(f"Fillet feature registered: {self.feature_id[:8]}")
        self._is_dirty = False
        return self._result_shape_id
    
    def _serialize_parameters(self) -> Dict[str, Any]:
        return {
            'edge_ids': self._params.edge_ids,
            'radius': self._params.radius,
            'is_variable': self._params.is_variable,
            'variable_radii': self._params.variable_radii
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], 
                  kernel: GeometryKernel) -> 'FilletFeature':
        params_data = data['parameters']
        
        params = FilletParameters(
            feature_id=data['feature_id'],
            feature_type=FeatureType.FILLET,
            edge_ids=params_data['edge_ids'],
            radius=params_data['radius'],
            is_variable=params_data.get('is_variable', False),
            variable_radii=params_data.get('variable_radii', {})
        )
        
        return cls(params, kernel)


class ChamferFeature(Feature):
    """倒角特征"""
    
    def __init__(self, params: ChamferParameters, kernel: GeometryKernel):
        super().__init__(params, kernel)
        self._params: ChamferParameters = params
    
    def validate(self) -> Tuple[bool, str]:
        if not self._params.edge_ids:
            return False, "At least one edge must be selected"
        if self._params.distance <= 0:
            return False, "Distance must be positive"
        return True, ""
    
    def build(self) -> Optional[str]:
        if self._params.is_suppressed:
            return None
        
        valid, msg = self.validate()
        if not valid:
            logger.error(f"Chamfer validation failed: {msg}")
            return None
        
        logger.info(f"Chamfer feature registered: {self.feature_id[:8]}")
        self._is_dirty = False
        return self._result_shape_id
    
    def _serialize_parameters(self) -> Dict[str, Any]:
        return {
            'edge_ids': self._params.edge_ids,
            'distance': self._params.distance,
            'distance2': self._params.distance2,
            'angle': self._params.angle
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], 
                  kernel: GeometryKernel) -> 'ChamferFeature':
        params_data = data['parameters']
        
        params = ChamferParameters(
            feature_id=data['feature_id'],
            feature_type=FeatureType.CHAMFER,
            edge_ids=params_data['edge_ids'],
            distance=params_data['distance'],
            distance2=params_data.get('distance2', 0),
            angle=params_data.get('angle', 45)
        )
        
        return cls(params, kernel)


class BooleanFeature(Feature):
    """布尔运算特征"""
    
    def __init__(self, params: BooleanParameters, kernel: GeometryKernel):
        super().__init__(params, kernel)
        self._params: BooleanParameters = params
    
    def validate(self) -> Tuple[bool, str]:
        if not self._params.target_body_id:
            return False, "Target body ID is required"
        if not self._params.tool_body_id:
            return False, "Tool body ID is required"
        if self._params.operation not in ['union', 'subtract', 'intersect']:
            return False, "Invalid boolean operation"
        return True, ""
    
    def build(self) -> Optional[str]:
        if self._params.is_suppressed:
            return None
        
        valid, msg = self.validate()
        if not valid:
            logger.error(f"Boolean validation failed: {msg}")
            return None
        
        try:
            target = self._kernel.get_shape(self._params.target_body_id)
            tool = self._kernel.get_shape(self._params.tool_body_id)
            
            if target is None or tool is None:
                logger.error("Target or tool shape not found")
                return None
            
            if self._params.operation == 'union':
                result = self._kernel.boolean_union(target, tool)
            elif self._params.operation == 'subtract':
                result = self._kernel.boolean_subtract(target, tool)
            else:  # intersect
                result = self._kernel.boolean_intersect(target, tool)
            
            if result is None:
                logger.error("Boolean operation failed")
                return None
            
            self._result_shape_id = self._params.feature_id
            self._kernel.register_shape(self._result_shape_id, result)
            self._is_dirty = False
            
            logger.info(f"Boolean feature built: {self.feature_id[:8]}")
            return self._result_shape_id
            
        except Exception as e:
            logger.error(f"Boolean build failed: {e}")
            return None
    
    def _serialize_parameters(self) -> Dict[str, Any]:
        return {
            'target_body_id': self._params.target_body_id,
            'tool_body_id': self._params.tool_body_id,
            'operation': self._params.operation
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], 
                  kernel: GeometryKernel) -> 'BooleanFeature':
        params_data = data['parameters']
        
        # 根据操作类型确定特征类型
        operation = params_data['operation']
        if operation == 'union':
            feature_type = FeatureType.BOOLEAN_UNION
        elif operation == 'subtract':
            feature_type = FeatureType.BOOLEAN_SUBTRACT
        else:
            feature_type = FeatureType.BOOLEAN_INTERSECT
        
        params = BooleanParameters(
            feature_id=data['feature_id'],
            feature_type=feature_type,
            target_body_id=params_data['target_body_id'],
            tool_body_id=params_data['tool_body_id'],
            operation=operation
        )
        
        return cls(params, kernel)


class DraftFeature(Feature):
    """拔模特征 (铸造专用)"""
    
    def __init__(self, params: DraftParameters, kernel: GeometryKernel):
        super().__init__(params, kernel)
        self._params: DraftParameters = params
    
    def validate(self) -> Tuple[bool, str]:
        if not self._params.face_ids:
            return False, "At least one face must be selected"
        if abs(self._params.draft_angle) >= 90:
            return False, "Draft angle must be less than 90 degrees"
        return True, ""
    
    def build(self) -> Optional[str]:
        if self._params.is_suppressed:
            return None
        
        valid, msg = self.validate()
        if not valid:
            logger.error(f"Draft validation failed: {msg}")
            return None
        
        try:
            # 拔模实现需要获取面并应用拔模
            # 这里简化处理，实际实现需要更复杂的逻辑
            logger.info(f"Draft feature built with angle {self._params.draft_angle}°")
            self._is_dirty = False
            return self._result_shape_id
            
        except Exception as e:
            logger.error(f"Draft build failed: {e}")
            return None
    
    def _serialize_parameters(self) -> Dict[str, Any]:
        return {
            'face_ids': self._params.face_ids,
            'neutral_plane': {
                'origin': self._params.neutral_plane.origin.to_tuple(),
                'normal': self._params.neutral_plane.normal.to_tuple(),
                'x_dir': self._params.neutral_plane.x_dir.to_tuple()
            },
            'pull_direction': self._params.pull_direction.to_tuple(),
            'draft_angle': self._params.draft_angle,
            'is_inward': self._params.is_inward
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], 
                  kernel: GeometryKernel) -> 'DraftFeature':
        params_data = data['parameters']
        
        neutral_plane = Plane(
            origin=Point3D(*params_data['neutral_plane']['origin']),
            normal=Vector3D(*params_data['neutral_plane']['normal']),
            x_dir=Vector3D(*params_data['neutral_plane']['x_dir'])
        )
        
        params = DraftParameters(
            feature_id=data['feature_id'],
            feature_type=FeatureType.DRAFT,
            face_ids=params_data['face_ids'],
            neutral_plane=neutral_plane,
            pull_direction=Vector3D(*params_data['pull_direction']),
            draft_angle=params_data['draft_angle'],
            is_inward=params_data.get('is_inward', True)
        )
        
        return cls(params, kernel)


class PrimitiveBoxFeature(Feature):
    """基本体-立方体特征"""
    
    def __init__(self, params: PrimitiveBoxParameters, kernel: GeometryKernel):
        super().__init__(params, kernel)
        self._params: PrimitiveBoxParameters = params
    
    def validate(self) -> Tuple[bool, str]:
        w, d, h = self._params.dimensions
        if w <= 0 or d <= 0 or h <= 0:
            return False, "All dimensions must be positive"
        return True, ""
    
    def build(self) -> Optional[str]:
        if self._params.is_suppressed:
            return None
        
        valid, msg = self.validate()
        if not valid:
            logger.error(f"Box validation failed: {msg}")
            return None
        
        try:
            shape = self._kernel.create_box(
                self._params.corner, self._params.dimensions)
            
            if shape is None:
                logger.error("Failed to create box")
                return None
            
            self._result_shape_id = self._params.feature_id
            self._kernel.register_shape(self._result_shape_id, shape)
            self._is_dirty = False
            
            logger.info(f"Box feature built: {self.feature_id[:8]}")
            return self._result_shape_id
            
        except Exception as e:
            logger.error(f"Box build failed: {e}")
            return None
    
    def _serialize_parameters(self) -> Dict[str, Any]:
        return {
            'corner': self._params.corner.to_tuple(),
            'dimensions': self._params.dimensions
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], 
                  kernel: GeometryKernel) -> 'PrimitiveBoxFeature':
        params_data = data['parameters']
        
        params = PrimitiveBoxParameters(
            feature_id=data['feature_id'],
            feature_type=FeatureType.PRIMITIVE_BOX,
            corner=Point3D(*params_data['corner']),
            dimensions=tuple(params_data['dimensions'])
        )
        
        return cls(params, kernel)


class PrimitiveCylinderFeature(Feature):
    """基本体-圆柱特征"""
    
    def __init__(self, params: PrimitiveCylinderParameters, kernel: GeometryKernel):
        super().__init__(params, kernel)
        self._params: PrimitiveCylinderParameters = params
    
    def validate(self) -> Tuple[bool, str]:
        if self._params.radius <= 0:
            return False, "Radius must be positive"
        if self._params.height <= 0:
            return False, "Height must be positive"
        return True, ""
    
    def build(self) -> Optional[str]:
        if self._params.is_suppressed:
            return None
        
        valid, msg = self.validate()
        if not valid:
            logger.error(f"Cylinder validation failed: {msg}")
            return None
        
        try:
            shape = self._kernel.create_cylinder(
                self._params.center, self._params.axis,
                self._params.radius, self._params.height)
            
            if shape is None:
                logger.error("Failed to create cylinder")
                return None
            
            self._result_shape_id = self._params.feature_id
            self._kernel.register_shape(self._result_shape_id, shape)
            self._is_dirty = False
            
            logger.info(f"Cylinder feature built: {self.feature_id[:8]}")
            return self._result_shape_id
            
        except Exception as e:
            logger.error(f"Cylinder build failed: {e}")
            return None
    
    def _serialize_parameters(self) -> Dict[str, Any]:
        return {
            'center': self._params.center.to_tuple(),
            'axis': self._params.axis.to_tuple(),
            'radius': self._params.radius,
            'height': self._params.height
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], 
                  kernel: GeometryKernel) -> 'PrimitiveCylinderFeature':
        params_data = data['parameters']
        
        params = PrimitiveCylinderParameters(
            feature_id=data['feature_id'],
            feature_type=FeatureType.PRIMITIVE_CYLINDER,
            center=Point3D(*params_data['center']),
            axis=Vector3D(*params_data['axis']),
            radius=params_data['radius'],
            height=params_data['height']
        )
        
        return cls(params, kernel)


class PrimitiveSphereFeature(Feature):
    """基本体-球体特征"""
    
    def __init__(self, params: PrimitiveSphereParameters, kernel: GeometryKernel):
        super().__init__(params, kernel)
        self._params: PrimitiveSphereParameters = params
    
    def validate(self) -> Tuple[bool, str]:
        if self._params.radius <= 0:
            return False, "Radius must be positive"
        return True, ""
    
    def build(self) -> Optional[str]:
        if self._params.is_suppressed:
            return None
        
        valid, msg = self.validate()
        if not valid:
            logger.error(f"Sphere validation failed: {msg}")
            return None
        
        try:
            shape = self._kernel.create_sphere(
                self._params.center, self._params.radius)
            
            if shape is None:
                logger.error("Failed to create sphere")
                return None
            
            self._result_shape_id = self._params.feature_id
            self._kernel.register_shape(self._result_shape_id, shape)
            self._is_dirty = False
            
            logger.info(f"Sphere feature built: {self.feature_id[:8]}")
            return self._result_shape_id
            
        except Exception as e:
            logger.error(f"Sphere build failed: {e}")
            return None
    
    def _serialize_parameters(self) -> Dict[str, Any]:
        return {
            'center': self._params.center.to_tuple(),
            'radius': self._params.radius
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], 
                  kernel: GeometryKernel) -> 'PrimitiveSphereFeature':
        params_data = data['parameters']
        
        params = PrimitiveSphereParameters(
            feature_id=data['feature_id'],
            feature_type=FeatureType.PRIMITIVE_SPHERE,
            center=Point3D(*params_data['center']),
            radius=params_data['radius']
        )
        
        return cls(params, kernel)


# 注册所有特征类
FeatureFactory.register(FeatureType.EXTRUDE, ExtrudeFeature)
FeatureFactory.register(FeatureType.REVOLVE, RevolveFeature)
FeatureFactory.register(FeatureType.HOLE, HoleFeature)
FeatureFactory.register(FeatureType.FILLET, FilletFeature)
FeatureFactory.register(FeatureType.CHAMFER, ChamferFeature)
FeatureFactory.register(FeatureType.BOOLEAN_UNION, BooleanFeature)
FeatureFactory.register(FeatureType.BOOLEAN_SUBTRACT, BooleanFeature)
FeatureFactory.register(FeatureType.BOOLEAN_INTERSECT, BooleanFeature)
FeatureFactory.register(FeatureType.DRAFT, DraftFeature)
FeatureFactory.register(FeatureType.PRIMITIVE_BOX, PrimitiveBoxFeature)
FeatureFactory.register(FeatureType.PRIMITIVE_CYLINDER, PrimitiveCylinderFeature)
FeatureFactory.register(FeatureType.PRIMITIVE_SPHERE, PrimitiveSphereFeature)
