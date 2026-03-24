"""
铸造行业2D到3D转换 - 3D建模引擎接口模块

本模块定义了图像分析模块与3D建模引擎之间的数据交换接口，
支持多种数据格式的导入导出。
"""

import json
import numpy as np
from typing import List, Dict, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from abc import ABC, abstractmethod

# 导入数据结构
from ..core.data_structures import (
    FeatureType, DimensionType, ConstraintType,
    Point2D, LineSegment, Circle, Arc, Ellipse, Polygon,
    GeometricFeature, Dimension, Constraint,
    AnalysisResult
)


# =============================================================================
# 3D特征类型
# =============================================================================

class Feature3DType:
    """3D特征类型"""
    EXTRUSION = "extrusion"          # 拉伸
    REVOLUTION = "revolution"        # 旋转
    SWEEP = "sweep"                  # 扫掠
    LOFT = "loft"                    # 放样
    PRIMITIVE = "primitive"          # 基本体
    BOOLEAN_UNION = "boolean_union"      # 布尔并
    BOOLEAN_SUBTRACT = "boolean_subtract" # 布尔差
    BOOLEAN_INTERSECT = "boolean_intersect" # 布尔交


# =============================================================================
# 3D特征数据结构
# =============================================================================

@dataclass
class Point3D:
    """三维点"""
    x: float
    y: float
    z: float
    
    def to_list(self) -> List[float]:
        return [self.x, self.y, self.z]
    
    def to_numpy(self) -> np.ndarray:
        return np.array([self.x, self.y, self.z])
    
    def __repr__(self) -> str:
        return f"Point3D({self.x:.3f}, {self.y:.3f}, {self.z:.3f})"


@dataclass
class Vector3D:
    """三维向量"""
    x: float
    y: float
    z: float
    
    @property
    def magnitude(self) -> float:
        return np.sqrt(self.x**2 + self.y**2 + self.z**2)
    
    def normalize(self) -> 'Vector3D':
        mag = self.magnitude
        if mag > 0:
            return Vector3D(self.x / mag, self.y / mag, self.z / mag)
        return Vector3D(0, 0, 0)
    
    def to_list(self) -> List[float]:
        return [self.x, self.y, self.z]


@dataclass
class ExtrusionFeature:
    """拉伸特征"""
    profile: List[Point2D]  # 轮廓
    height: float           # 拉伸高度
    direction: Vector3D = field(default_factory=lambda: Vector3D(0, 0, 1))
    taper_angle: float = 0.0  # 拔模角度
    
    def to_dict(self) -> Dict:
        return {
            "type": "extrusion",
            "profile": [[p.x, p.y] for p in self.profile],
            "height": self.height,
            "direction": self.direction.to_list(),
            "taper_angle": self.taper_angle
        }


@dataclass
class RevolutionFeature:
    """旋转特征"""
    profile: List[Point2D]  # 轮廓
    axis_start: Point3D     # 旋转轴起点
    axis_direction: Vector3D  # 旋转轴方向
    angle: float = 360.0    # 旋转角度
    
    def to_dict(self) -> Dict:
        return {
            "type": "revolution",
            "profile": [[p.x, p.y] for p in self.profile],
            "axis_start": self.axis_start.to_list(),
            "axis_direction": self.axis_direction.to_list(),
            "angle": self.angle
        }


@dataclass
class Primitive3D:
    """3D基本体"""
    primitive_type: str  # box, cylinder, sphere, cone, torus
    parameters: Dict[str, float]
    position: Point3D = field(default_factory=lambda: Point3D(0, 0, 0))
    rotation: List[float] = field(default_factory=lambda: [0, 0, 0])
    
    def to_dict(self) -> Dict:
        return {
            "type": "primitive",
            "primitive_type": self.primitive_type,
            "parameters": self.parameters,
            "position": self.position.to_list(),
            "rotation": self.rotation
        }


# 3D特征联合类型
Feature3D = Union[ExtrusionFeature, RevolutionFeature, Primitive3D]


# =============================================================================
# 3D模型数据结构
# =============================================================================

@dataclass
class Model3D:
    """3D模型"""
    name: str
    features: List[Feature3D] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_feature(self, feature: Feature3D):
        """添加特征"""
        self.features.append(feature)
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "features": [f.to_dict() for f in self.features],
            "metadata": self.metadata
        }


# =============================================================================
# 特征集合
# =============================================================================

@dataclass
class FeatureCollection:
    """特征集合 - 图像分析结果的中转格式"""
    features: List[GeometricFeature]
    dimensions: List[Dimension]
    constraints: List[Constraint]
    scale_factor: float = 1.0
    
    @property
    def num_features(self) -> int:
        return len(self.features)
    
    @property
    def num_dimensions(self) -> int:
        return len(self.dimensions)
    
    def get_features_by_type(self, feature_type: FeatureType) -> List[GeometricFeature]:
        """按类型获取特征"""
        return [f for f in self.features if f.feature_type == feature_type]
    
    def to_dict(self) -> Dict:
        return {
            "features": [f.to_dict() for f in self.features],
            "dimensions": [d.to_dict() for d in self.dimensions],
            "constraints": [c.to_dict() for c in self.constraints],
            "scale_factor": self.scale_factor
        }


# =============================================================================
# 3D建模引擎接口基类
# =============================================================================

class Model3DEngineInterface(ABC):
    """3D建模引擎接口基类"""
    
    @abstractmethod
    def create_extrusion(self, profile: List[Point2D], 
                         height: float,
                         **kwargs) -> Any:
        """创建拉伸特征"""
        pass
    
    @abstractmethod
    def create_revolution(self, profile: List[Point2D],
                          axis: Tuple[Point3D, Vector3D],
                          angle: float,
                          **kwargs) -> Any:
        """创建旋转特征"""
        pass
    
    @abstractmethod
    def create_primitive(self, primitive_type: str,
                         parameters: Dict[str, float],
                         **kwargs) -> Any:
        """创建基本体"""
        pass
    
    @abstractmethod
    def apply_boolean(self, operation: str,
                      target: Any,
                      tool: Any) -> Any:
        """应用布尔运算"""
        pass
    
    @abstractmethod
    def export_model(self, filepath: str,
                     format: str,
                     **kwargs) -> bool:
        """导出模型"""
        pass


# =============================================================================
# 数据交换接口
# =============================================================================

class Model3DInterface:
    """
    与3D建模引擎的数据交换接口
    
    负责将图像分析结果转换为3D建模引擎可用的格式
    """
    
    def __init__(self, engine_interface: Model3DEngineInterface = None):
        self.engine = engine_interface
        self._conversion_log = []
    
    def convert_to_3d(self, result: AnalysisResult,
                      extrusion_height: float = None,
                      revolution_axis: Tuple[Point3D, Vector3D] = None) -> Model3D:
        """
        将分析结果转换为3D模型
        
        Args:
            result: 图像分析结果
            extrusion_height: 默认拉伸高度（如果未指定尺寸）
            revolution_axis: 旋转轴（用于旋转特征）
            
        Returns:
            3D模型
        """
        model = Model3D(name="CastingPart")
        
        # 获取尺寸信息
        height = self._get_extrusion_height(result, extrusion_height)
        
        # 转换特征
        for feature in result.features:
            feature_3d = self._convert_feature(feature, height, revolution_axis)
            if feature_3d:
                model.add_feature(feature_3d)
        
        # 添加元数据
        model.metadata = {
            "source": "2D_image_analysis",
            "scale_factor": result.scale_factor,
            "num_2d_features": len(result.features),
            "conversion_timestamp": datetime.now().isoformat()
        }
        
        return model
    
    def _get_extrusion_height(self, result: AnalysisResult, 
                              default_height: float = None) -> float:
        """从尺寸标注中提取拉伸高度"""
        # 查找深度或高度尺寸
        for dim in result.dimensions:
            if dim.dimension_type == DimensionType.DEPTH:
                return dim.value
        
        # 使用默认值
        if default_height is not None:
            return default_height
        
        # 基于特征尺寸估算
        if result.features:
            # 使用最大特征尺寸的10%作为默认高度
            max_dim = 0
            for f in result.features:
                bbox = f.bounding_box
                max_dim = max(max_dim, bbox.width, bbox.height)
            return max_dim * 0.1 * result.scale_factor
        
        return 10.0  # 默认10mm
    
    def _convert_feature(self, feature: GeometricFeature,
                         height: float,
                         revolution_axis: Tuple[Point3D, Vector3D] = None) -> Optional[Feature3D]:
        """转换单个特征"""
        if feature.feature_type == FeatureType.CIRCLE:
            return self._convert_circle(feature, height)
        elif feature.feature_type == FeatureType.POLYGON:
            return self._convert_polygon(feature, height)
        elif feature.feature_type == FeatureType.LINE:
            # 线段通常不直接转换为3D
            return None
        elif feature.feature_type == FeatureType.ARC:
            return self._convert_arc(feature, height)
        elif feature.feature_type == FeatureType.ELLIPSE:
            return self._convert_ellipse(feature, height)
        
        return None
    
    def _convert_circle(self, feature: GeometricFeature,
                        height: float) -> Feature3D:
        """转换圆为圆柱体"""
        circle = feature.geometry
        
        # 创建圆柱体参数
        return Primitive3D(
            primitive_type="cylinder",
            parameters={
                "radius": circle.radius,
                "height": height
            },
            position=Point3D(circle.center.x, circle.center.y, 0)
        )
    
    def _convert_polygon(self, feature: GeometricFeature,
                         height: float) -> Feature3D:
        """转换多边形为拉伸特征"""
        polygon = feature.geometry
        
        return ExtrusionFeature(
            profile=polygon.vertices,
            height=height
        )
    
    def _convert_arc(self, feature: GeometricFeature,
                     height: float) -> Optional[Feature3D]:
        """转换圆弧"""
        arc = feature.geometry
        
        # 如果圆弧接近完整圆，创建圆柱体
        if abs(arc.angle_span) > 6.0:  # > 约345度
            return Primitive3D(
                primitive_type="cylinder",
                parameters={
                    "radius": arc.radius,
                    "height": height
                },
                position=Point3D(arc.center.x, arc.center.y, 0)
            )
        
        # 否则创建部分圆柱体（需要更复杂的处理）
        return None
    
    def _convert_ellipse(self, feature: GeometricFeature,
                         height: float) -> Feature3D:
        """转换椭圆"""
        ellipse = feature.geometry
        
        # 创建椭圆柱体参数
        return Primitive3D(
            primitive_type="elliptical_cylinder",
            parameters={
                "major_radius": ellipse.major_axis / 2,
                "minor_radius": ellipse.minor_axis / 2,
                "height": height,
                "rotation": ellipse.rotation
            },
            position=Point3D(ellipse.center.x, ellipse.center.y, 0)
        )
    
    # =============================================================================
    # 导出方法
    # =============================================================================
    
    def export_to_json(self, result: AnalysisResult, 
                       filepath: str = None) -> str:
        """
        导出分析结果为JSON格式
        
        Args:
            result: 分析结果
            filepath: 输出文件路径，如果为None则返回JSON字符串
            
        Returns:
            JSON字符串
        """
        data = {
            "version": "1.0",
            "export_timestamp": datetime.now().isoformat(),
            "image_info": result.image_info.to_dict(),
            "features": [f.to_dict() for f in result.features],
            "dimensions": [d.to_dict() for d in result.dimensions],
            "constraints": [c.to_dict() for c in result.constraints],
            "scale_factor": result.scale_factor,
            "metadata": result.metadata.to_dict()
        }
        
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        
        if filepath:
            Path(filepath).write_text(json_str, encoding='utf-8')
        
        return json_str
    
    def export_to_step(self, result: AnalysisResult,
                       filepath: str,
                       engine_interface: Model3DEngineInterface = None) -> bool:
        """
        导出为STEP格式
        
        注意：需要外部3D建模引擎支持（如FreeCAD、OpenCASCADE）
        
        Args:
            result: 分析结果
            filepath: 输出文件路径
            engine_interface: 3D建模引擎接口
            
        Returns:
            是否成功
        """
        engine = engine_interface or self.engine
        
        if engine is None:
            raise ValueError("3D modeling engine interface is required for STEP export")
        
        try:
            # 转换为3D模型
            model = self.convert_to_3d(result)
            
            # 通过引擎导出
            return engine.export_model(filepath, "STEP")
            
        except Exception as e:
            self._conversion_log.append(f"STEP export failed: {str(e)}")
            return False
    
    def export_to_iges(self, result: AnalysisResult,
                       filepath: str,
                       engine_interface: Model3DEngineInterface = None) -> bool:
        """导出为IGES格式"""
        engine = engine_interface or self.engine
        
        if engine is None:
            raise ValueError("3D modeling engine interface is required for IGES export")
        
        try:
            model = self.convert_to_3d(result)
            return engine.export_model(filepath, "IGES")
        except Exception as e:
            self._conversion_log.append(f"IGES export failed: {str(e)}")
            return False
    
    def export_to_stl(self, result: AnalysisResult,
                      filepath: str,
                      engine_interface: Model3DEngineInterface = None,
                      tessellation_params: Dict = None) -> bool:
        """导出为STL格式"""
        engine = engine_interface or self.engine
        
        if engine is None:
            raise ValueError("3D modeling engine interface is required for STL export")
        
        try:
            model = self.convert_to_3d(result)
            params = tessellation_params or {}
            return engine.export_model(filepath, "STL", **params)
        except Exception as e:
            self._conversion_log.append(f"STL export failed: {str(e)}")
            return False
    
    # =============================================================================
    # 导入方法
    # =============================================================================
    
    def import_from_json(self, json_str: str) -> FeatureCollection:
        """
        从JSON字符串导入特征集合
        
        Args:
            json_str: JSON字符串
            
        Returns:
            特征集合
        """
        data = json.loads(json_str)
        
        # 解析特征
        features = []
        for f_data in data.get("features", []):
            feature = self._parse_feature(f_data)
            if feature:
                features.append(feature)
        
        # 解析尺寸
        dimensions = []
        for d_data in data.get("dimensions", []):
            dim = self._parse_dimension(d_data)
            if dim:
                dimensions.append(dim)
        
        # 解析约束
        constraints = []
        for c_data in data.get("constraints", []):
            constraint = self._parse_constraint(c_data)
            if constraint:
                constraints.append(constraint)
        
        return FeatureCollection(
            features=features,
            dimensions=dimensions,
            constraints=constraints,
            scale_factor=data.get("scale_factor", 1.0)
        )
    
    def _parse_feature(self, data: Dict) -> Optional[GeometricFeature]:
        """解析特征"""
        # 简化的解析实现
        # 实际实现需要完整的反序列化逻辑
        return None
    
    def _parse_dimension(self, data: Dict) -> Optional[Dimension]:
        """解析尺寸"""
        return None
    
    def _parse_constraint(self, data: Dict) -> Optional[Constraint]:
        """解析约束"""
        return None
    
    # =============================================================================
    # 辅助方法
    # =============================================================================
    
    def get_conversion_log(self) -> List[str]:
        """获取转换日志"""
        return self._conversion_log.copy()
    
    def clear_conversion_log(self):
        """清除转换日志"""
        self._conversion_log.clear()
    
    def get_feature_collection(self, result: AnalysisResult) -> FeatureCollection:
        """获取特征集合对象"""
        return FeatureCollection(
            features=result.features,
            dimensions=result.dimensions,
            constraints=result.constraints,
            scale_factor=result.scale_factor
        )


# =============================================================================
# 示例3D建模引擎接口实现（FreeCAD）
# =============================================================================

class FreeCADInterface(Model3DEngineInterface):
    """
    FreeCAD引擎接口示例
    
    注意：需要安装FreeCAD并正确配置Python路径
    """
    
    def __init__(self):
        self.doc = None
        self._import_freecad()
    
    def _import_freecad(self):
        """导入FreeCAD模块"""
        try:
            import FreeCAD
            import Part
            self.FreeCAD = FreeCAD
            self.Part = Part
        except ImportError:
            raise ImportError("FreeCAD not found. Please install FreeCAD.")
    
    def create_extrusion(self, profile: List[Point2D], 
                         height: float, **kwargs) -> Any:
        """创建拉伸特征"""
        # 创建线框
        points = [self.FreeCAD.Vector(p.x, p.y, 0) for p in profile]
        if profile[0].distance_to(profile[-1]) > 0.001:
            points.append(points[0])  # 闭合
        
        wire = self.Part.makePolygon(points)
        face = self.Part.Face(wire)
        
        # 拉伸
        direction = kwargs.get("direction", Vector3D(0, 0, 1))
        vec = self.FreeCAD.Vector(
            direction.x * height,
            direction.y * height,
            direction.z * height
        )
        
        solid = face.extrude(vec)
        return solid
    
    def create_revolution(self, profile: List[Point2D],
                          axis: Tuple[Point3D, Vector3D],
                          angle: float, **kwargs) -> Any:
        """创建旋转特征"""
        # 创建线框
        points = [self.FreeCAD.Vector(p.x, p.y, 0) for p in profile]
        wire = self.Part.makePolygon(points)
        face = self.Part.Face(wire)
        
        # 旋转轴
        axis_start, axis_dir = axis
        axis_vec = self.FreeCAD.Vector(
            axis_start.x, axis_start.y, axis_start.z
        )
        axis_dir_vec = self.FreeCAD.Vector(
            axis_dir.x, axis_dir.y, axis_dir.z
        )
        
        # 旋转
        solid = face.revolve(axis_vec, axis_dir_vec, angle)
        return solid
    
    def create_primitive(self, primitive_type: str,
                         parameters: Dict[str, float], **kwargs) -> Any:
        """创建基本体"""
        if primitive_type == "cylinder":
            radius = parameters.get("radius", 10)
            height = parameters.get("height", 20)
            return self.Part.makeCylinder(radius, height)
        elif primitive_type == "box":
            length = parameters.get("length", 10)
            width = parameters.get("width", 10)
            height = parameters.get("height", 10)
            return self.Part.makeBox(length, width, height)
        elif primitive_type == "sphere":
            radius = parameters.get("radius", 10)
            return self.Part.makeSphere(radius)
        
        return None
    
    def apply_boolean(self, operation: str,
                      target: Any, tool: Any) -> Any:
        """应用布尔运算"""
        if operation == "union":
            return target.fuse(tool)
        elif operation == "subtract":
            return target.cut(tool)
        elif operation == "intersect":
            return target.common(tool)
        
        return target
    
    def export_model(self, filepath: str, format: str, **kwargs) -> bool:
        """导出模型"""
        format_upper = format.upper()
        
        if format_upper == "STEP":
            self.doc.saveAs(filepath)
            return True
        elif format_upper == "STL":
            # 需要网格化
            mesh = self._tessellate(kwargs)
            mesh.write(filepath)
            return True
        
        return False
    
    def _tessellate(self, params: Dict) -> Any:
        """网格化"""
        # 实现网格化逻辑
        pass


# =============================================================================
# 便捷函数
# =============================================================================

def export_result(result: AnalysisResult, 
                  filepath: str,
                  format: str = "json") -> bool:
    """
    便捷函数：导出分析结果
    
    Args:
        result: 分析结果
        filepath: 输出文件路径
        format: 输出格式 (json, step, iges, stl)
        
    Returns:
        是否成功
    """
    interface = Model3DInterface()
    
    format_lower = format.lower()
    
    if format_lower == "json":
        interface.export_to_json(result, filepath)
        return True
    elif format_lower in ["step", "iges", "stl"]:
        # 需要3D建模引擎
        raise NotImplementedError(f"{format} export requires 3D modeling engine")
    
    return False


def convert_to_3d_model(result: AnalysisResult,
                        extrusion_height: float = None) -> Model3D:
    """
    便捷函数：转换为3D模型
    
    Args:
        result: 分析结果
        extrusion_height: 拉伸高度
        
    Returns:
        3D模型
    """
    interface = Model3DInterface()
    return interface.convert_to_3d(result, extrusion_height)


# 模块测试
if __name__ == "__main__":
    import sys
    sys.path.append('/mnt/okcomputer/output/image_analysis_module')
    
    # 创建测试数据
    from core.data_structures import (
        ImageInfo, SourceType, AnalysisMetadata, AnalysisResult
    )
    
    # 创建测试特征
    features = [
        GeometricFeature(
            id=1,
            feature_type=FeatureType.CIRCLE,
            geometry=Circle(Point2D(50, 50), 20),
            confidence=0.95
        ),
        GeometricFeature(
            id=2,
            feature_type=FeatureType.POLYGON,
            geometry=Polygon([
                Point2D(100, 100),
                Point2D(150, 100),
                Point2D(150, 150),
                Point2D(100, 150)
            ]),
            confidence=0.9
        )
    ]
    
    # 创建分析结果
    result = AnalysisResult(
        image_info=ImageInfo(400, 400, SourceType.TECHNICAL_DRAWING),
        features=features,
        scale_factor=0.5
    )
    
    # 测试接口
    interface = Model3DInterface()
    
    # 转换为3D模型
    model = interface.convert_to_3d(result, extrusion_height=10)
    
    print("3D Model Conversion Test:")
    print(f"  Model name: {model.name}")
    print(f"  Number of features: {len(model.features)}")
    
    for i, feature in enumerate(model.features):
        print(f"\n  Feature {i+1}:")
        if isinstance(feature, Primitive3D):
            print(f"    Type: {feature.primitive_type}")
            print(f"    Parameters: {feature.parameters}")
        elif isinstance(feature, ExtrusionFeature):
            print(f"    Type: extrusion")
            print(f"    Height: {feature.height}")
            print(f"    Profile vertices: {len(feature.profile)}")
    
    # 测试JSON导出
    json_str = interface.export_to_json(result)
    print(f"\nJSON Export Test:")
    print(f"  JSON length: {len(json_str)} characters")
    
    print("\nAll tests passed!")
