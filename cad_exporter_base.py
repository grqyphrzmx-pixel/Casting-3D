"""
铸造行业CAD导出模块 - 基类和核心架构
Foundry Industry CAD Export Module - Base Classes and Core Architecture

支持格式 / Supported Formats:
- STL (ASCII & Binary)
- STEP (AP203, AP214)
- IGES (Version 5.3)

作者: CAD Format Expert
版本: 1.0.0
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Callable, Any, Union
from enum import Enum, auto
import numpy as np
from pathlib import Path
import struct
import time
from datetime import datetime


# ============================================================================
# 数据类型定义 / Data Type Definitions
# ============================================================================

class ExportFormat(Enum):
    """支持的导出格式"""
    STL_ASCII = "stl_ascii"
    STL_BINARY = "stl_binary"
    STEP_AP203 = "step_ap203"
    STEP_AP214 = "step_ap214"
    IGES_5_3 = "iges_5_3"


class ExportError(Exception):
    """导出操作基础异常"""
    pass


class ValidationError(ExportError):
    """数据验证异常"""
    pass


class FormatError(ExportError):
    """格式错误异常"""
    pass


class UnitType(Enum):
    """单位类型"""
    MILLIMETER = "MM"
    CENTIMETER = "CM"
    METER = "M"
    INCH = "INCH"


@dataclass
class Vector3D:
    """3D向量/点数据类"""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    
    def __add__(self, other: 'Vector3D') -> 'Vector3D':
        return Vector3D(self.x + other.x, self.y + other.y, self.z + other.z)
    
    def __sub__(self, other: 'Vector3D') -> 'Vector3D':
        return Vector3D(self.x - other.x, self.y - other.y, self.z - other.z)
    
    def __mul__(self, scalar: float) -> 'Vector3D':
        return Vector3D(self.x * scalar, self.y * scalar, self.z * scalar)
    
    def to_array(self) -> np.ndarray:
        return np.array([self.x, self.y, self.z])
    
    @staticmethod
    def from_array(arr: np.ndarray) -> 'Vector3D':
        return Vector3D(float(arr[0]), float(arr[1]), float(arr[2]))
    
    def normalize(self) -> 'Vector3D':
        length = np.sqrt(self.x**2 + self.y**2 + self.z**2)
        if length < 1e-10:
            return Vector3D(0, 0, 1)
        return Vector3D(self.x/length, self.y/length, self.z/length)


@dataclass
class Triangle:
    """三角面片数据类"""
    normal: Vector3D
    v1: Vector3D
    v2: Vector3D
    v3: Vector3D
    attribute: int = 0  # STL属性字节
    
    def compute_normal(self) -> Vector3D:
        """计算法向量"""
        edge1 = self.v2 - self.v1
        edge2 = self.v3 - self.v1
        # 叉积计算法向量
        nx = edge1.y * edge2.z - edge1.z * edge2.y
        ny = edge1.z * edge2.x - edge1.x * edge2.z
        nz = edge1.x * edge2.y - edge1.y * edge2.x
        return Vector3D(nx, ny, nz).normalize()


@dataclass
class MeshData:
    """网格数据容器"""
    name: str = ""
    triangles: List[Triangle] = field(default_factory=list)
    vertices: List[Vector3D] = field(default_factory=list)
    normals: List[Vector3D] = field(default_factory=list)
    
    def get_bounds(self) -> Tuple[Vector3D, Vector3D]:
        """获取包围盒"""
        if not self.vertices:
            return Vector3D(), Vector3D()
        xs = [v.x for v in self.vertices]
        ys = [v.y for v in self.vertices]
        zs = [v.z for v in self.vertices]
        return Vector3D(min(xs), min(ys), min(zs)), Vector3D(max(xs), max(ys), max(zs))


@dataclass
class BRepFace:
    """B-rep面数据"""
    surface_type: str  # PLANE, CYLINDER, CONE, SPHERE, TORUS, BSURFACE
    surface_params: Dict[str, Any]
    outer_wire: List[int]  # 外环顶点索引
    inner_wires: List[List[int]] = field(default_factory=list)  # 内环（孔）
    color: Optional[Tuple[int, int, int]] = None


@dataclass
class BRepEdge:
    """B-rep边数据"""
    curve_type: str  # LINE, CIRCLE, ELLIPSE, PARABOLA, HYPERBOLA, BCURVE
    curve_params: Dict[str, Any]
    vertex_start: int
    vertex_end: int


@dataclass
class BRepSolid:
    """B-rep实体数据"""
    name: str = ""
    faces: List[BRepFace] = field(default_factory=list)
    edges: List[BRepEdge] = field(default_factory=list)
    vertices: List[Vector3D] = field(default_factory=list)
    color: Optional[Tuple[int, int, int]] = None


@dataclass
class ExportMetadata:
    """导出元数据"""
    author: str = "FoundryCAD Export Module"
    organization: str = ""
    description: str = ""
    created_date: str = field(default_factory=lambda: datetime.now().isoformat())
    source_system: str = "FoundryCAD 2D-3D Converter"
    unit: UnitType = UnitType.MILLIMETER
    precision: float = 0.001  # 默认精度 0.001mm


@dataclass
class ExportOptions:
    """导出选项配置"""
    format: ExportFormat = ExportFormat.STL_BINARY
    unit: UnitType = UnitType.MILLIMETER
    precision: float = 0.001
    tolerance: float = 0.01  # 几何容差
    angular_tolerance: float = 0.5  # 角度容差（度）
    # STL特定选项
    stl_ascii: bool = False
    stl_solid_name: str = ""
    # STEP特定选项
    step_schema: str = "AP214"  # AP203, AP214
    step_write_colors: bool = True
    # IGES特定选项
    iges_unit_flag: int = 2  # 1=inch, 2=mm, 4=cm, 5=m
    iges_write_colors: bool = True


# ============================================================================
# 进度报告 / Progress Reporting
# ============================================================================

@dataclass
class ExportProgress:
    """导出进度信息"""
    stage: str = ""
    current: int = 0
    total: int = 0
    percentage: float = 0.0
    message: str = ""
    elapsed_time: float = 0.0
    estimated_time: float = 0.0


class ProgressReporter:
    """进度报告器"""
    
    def __init__(self, callback: Optional[Callable[[ExportProgress], None]] = None):
        self.callback = callback
        self.start_time = time.time()
        self._current_stage = ""
    
    def report(self, stage: str, current: int, total: int, message: str = ""):
        """报告进度"""
        self._current_stage = stage
        elapsed = time.time() - self.start_time
        percentage = (current / total * 100) if total > 0 else 0
        
        # 估算剩余时间
        estimated = 0.0
        if current > 0 and percentage > 0:
            estimated = elapsed / (percentage / 100) - elapsed
        
        progress = ExportProgress(
            stage=stage,
            current=current,
            total=total,
            percentage=percentage,
            message=message,
            elapsed_time=elapsed,
            estimated_time=estimated
        )
        
        if self.callback:
            self.callback(progress)
    
    def report_stage(self, stage: str, message: str = ""):
        """报告阶段开始"""
        self._current_stage = stage
        elapsed = time.time() - self.start_time
        progress = ExportProgress(
            stage=stage,
            message=message,
            elapsed_time=elapsed
        )
        if self.callback:
            self.callback(progress)


# ============================================================================
# 导出器基类 / Exporter Base Class
# ============================================================================

class CADExporter(ABC):
    """
    CAD导出器抽象基类
    
    所有格式特定的导出器必须继承此类并实现抽象方法。
    """
    
    def __init__(self, options: Optional[ExportOptions] = None):
        self.options = options or ExportOptions()
        self.metadata = ExportMetadata()
        self._progress_reporter: Optional[ProgressReporter] = None
        self._errors: List[str] = []
        self._warnings: List[str] = []
    
    @property
    @abstractmethod
    def format_name(self) -> str:
        """返回格式名称"""
        pass
    
    @property
    @abstractmethod
    def file_extension(self) -> str:
        """返回文件扩展名"""
        pass
    
    def set_progress_callback(self, callback: Callable[[ExportProgress], None]):
        """设置进度回调函数"""
        self._progress_reporter = ProgressReporter(callback)
    
    def set_metadata(self, metadata: ExportMetadata):
        """设置导出元数据"""
        self.metadata = metadata
    
    def _report_progress(self, stage: str, current: int, total: int, message: str = ""):
        """内部进度报告"""
        if self._progress_reporter:
            self._progress_reporter.report(stage, current, total, message)
    
    def _report_stage(self, stage: str, message: str = ""):
        """报告阶段"""
        if self._progress_reporter:
            self._progress_reporter.report_stage(stage, message)
    
    def _add_error(self, message: str):
        """添加错误信息"""
        self._errors.append(message)
    
    def _add_warning(self, message: str):
        """添加警告信息"""
        self._warnings.append(message)
    
    def get_errors(self) -> List[str]:
        """获取错误列表"""
        return self._errors.copy()
    
    def get_warnings(self) -> List[str]:
        """获取警告列表"""
        return self._warnings.copy()
    
    def has_errors(self) -> bool:
        """检查是否有错误"""
        return len(self._errors) > 0
    
    def clear_messages(self):
        """清除消息"""
        self._errors.clear()
        self._warnings.clear()
    
    @abstractmethod
    def export_mesh(self, mesh: MeshData, filepath: Union[str, Path]) -> bool:
        """
        导出三角网格模型
        
        Args:
            mesh: 网格数据
            filepath: 输出文件路径
            
        Returns:
            导出是否成功
        """
        pass
    
    @abstractmethod
    def export_brep(self, solid: BRepSolid, filepath: Union[str, Path]) -> bool:
        """
        导出B-rep实体模型
        
        Args:
            solid: B-rep实体数据
            filepath: 输出文件路径
            
        Returns:
            导出是否成功
        """
        pass
    
    def validate_mesh(self, mesh: MeshData) -> bool:
        """
        验证网格数据
        
        Args:
            mesh: 要验证的网格数据
            
        Returns:
            验证是否通过
        """
        self.clear_messages()
        
        if not mesh.triangles:
            self._add_error("Mesh contains no triangles")
            return False
        
        # 检查退化三角形
        degenerate_count = 0
        for i, tri in enumerate(mesh.triangles):
            # 检查零面积三角形
            edge1 = tri.v2 - tri.v1
            edge2 = tri.v3 - tri.v1
            cross = Vector3D(
                edge1.y * edge2.z - edge1.z * edge2.y,
                edge1.z * edge2.x - edge1.x * edge2.z,
                edge1.x * edge2.y - edge1.y * edge2.x
            )
            area = np.sqrt(cross.x**2 + cross.y**2 + cross.z**2) / 2
            if area < self.options.tolerance:
                degenerate_count += 1
        
        if degenerate_count > 0:
            self._add_warning(f"Found {degenerate_count} degenerate triangles")
        
        # 检查法向量
        invalid_normal_count = 0
        for i, tri in enumerate(mesh.triangles):
            computed = tri.compute_normal()
            if abs(computed.x) < 1e-10 and abs(computed.y) < 1e-10 and abs(computed.z) < 1e-10:
                invalid_normal_count += 1
        
        if invalid_normal_count > 0:
            self._add_warning(f"Found {invalid_normal_count} triangles with invalid normals")
        
        return not self.has_errors()
    
    def validate_brep(self, solid: BRepSolid) -> bool:
        """
        验证B-rep数据
        
        Args:
            solid: 要验证的B-rep数据
            
        Returns:
            验证是否通过
        """
        self.clear_messages()
        
        if not solid.faces:
            self._add_error("Solid contains no faces")
            return False
        
        if not solid.vertices:
            self._add_error("Solid contains no vertices")
            return False
        
        # 检查顶点索引有效性
        for face in solid.faces:
            for idx in face.outer_wire:
                if idx < 0 or idx >= len(solid.vertices):
                    self._add_error(f"Invalid vertex index {idx} in face")
                    return False
        
        return not self.has_errors()
    
    def _ensure_directory(self, filepath: Union[str, Path]) -> Path:
        """确保输出目录存在"""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


# ============================================================================
# 导出器工厂 / Exporter Factory
# ============================================================================

class ExporterFactory:
    """导出器工厂类"""
    
    _exporters: Dict[ExportFormat, type] = {}
    
    @classmethod
    def register(cls, format_type: ExportFormat, exporter_class: type):
        """注册导出器"""
        if not issubclass(exporter_class, CADExporter):
            raise TypeError("Exporter class must inherit from CADExporter")
        cls._exporters[format_type] = exporter_class
    
    @classmethod
    def create(cls, format_type: ExportFormat, options: Optional[ExportOptions] = None) -> CADExporter:
        """创建导出器实例"""
        if format_type not in cls._exporters:
            raise ValueError(f"No exporter registered for format: {format_type}")
        return cls._exporters[format_type](options)
    
    @classmethod
    def get_supported_formats(cls) -> List[ExportFormat]:
        """获取支持的格式列表"""
        return list(cls._exporters.keys())
    
    @classmethod
    def is_format_supported(cls, format_type: ExportFormat) -> bool:
        """检查格式是否支持"""
        return format_type in cls._exporters


def get_exporter_for_file(filepath: Union[str, Path]) -> Optional[ExportFormat]:
    """根据文件扩展名获取导出格式"""
    ext = Path(filepath).suffix.lower()
    format_map = {
        '.stl': ExportFormat.STL_BINARY,
        '.step': ExportFormat.STEP_AP214,
        '.stp': ExportFormat.STEP_AP214,
        '.iges': ExportFormat.IGES_5_3,
        '.igs': ExportFormat.IGES_5_3,
    }
    return format_map.get(ext)


# ============================================================================
# 实用函数 / Utility Functions
# ============================================================================

def convert_units(value: float, from_unit: UnitType, to_unit: UnitType) -> float:
    """单位转换"""
    # 转换为毫米
    to_mm = {
        UnitType.MILLIMETER: 1.0,
        UnitType.CENTIMETER: 10.0,
        UnitType.METER: 1000.0,
        UnitType.INCH: 25.4,
    }
    # 从毫米转换
    from_mm = {
        UnitType.MILLIMETER: 1.0,
        UnitType.CENTIMETER: 0.1,
        UnitType.METER: 0.001,
        UnitType.INCH: 1/25.4,
    }
    mm_value = value * to_mm[from_unit]
    return mm_value * from_mm[to_unit]


def format_float(value: float, precision: int = 6) -> str:
    """格式化浮点数输出"""
    return f"{value:.{precision}f}"


def compute_triangle_area(tri: Triangle) -> float:
    """计算三角形面积"""
    edge1 = tri.v2 - tri.v1
    edge2 = tri.v3 - tri.v1
    cross = Vector3D(
        edge1.y * edge2.z - edge1.z * edge2.y,
        edge1.z * edge2.x - edge1.x * edge2.z,
        edge1.x * edge2.y - edge1.y * edge2.x
    )
    return np.sqrt(cross.x**2 + cross.y**2 + cross.z**2) / 2


def normalize_mesh_vertices(mesh: MeshData) -> MeshData:
    """归一化网格顶点（中心化并缩放到单位大小）"""
    if not mesh.vertices:
        return mesh
    
    # 计算包围盒
    min_pt, max_pt = mesh.get_bounds()
    center = Vector3D(
        (min_pt.x + max_pt.x) / 2,
        (min_pt.y + max_pt.y) / 2,
        (min_pt.z + max_pt.z) / 2
    )
    
    # 计算缩放因子
    size = max(
        max_pt.x - min_pt.x,
        max_pt.y - min_pt.y,
        max_pt.z - min_pt.z
    )
    scale = 1.0 / size if size > 0 else 1.0
    
    # 变换顶点
    new_mesh = MeshData(name=mesh.name)
    vertex_map = {}
    
    for i, v in enumerate(mesh.vertices):
        new_v = Vector3D(
            (v.x - center.x) * scale,
            (v.y - center.y) * scale,
            (v.z - center.z) * scale
        )
        new_mesh.vertices.append(new_v)
        vertex_map[i] = len(new_mesh.vertices) - 1
    
    # 变换三角形
    for tri in mesh.triangles:
        new_tri = Triangle(
            normal=tri.normal,
            v1=Vector3D(
                (tri.v1.x - center.x) * scale,
                (tri.v1.y - center.y) * scale,
                (tri.v1.z - center.z) * scale
            ),
            v2=Vector3D(
                (tri.v2.x - center.x) * scale,
                (tri.v2.y - center.y) * scale,
                (tri.v2.z - center.z) * scale
            ),
            v3=Vector3D(
                (tri.v3.x - center.x) * scale,
                (tri.v3.y - center.y) * scale,
                (tri.v3.z - center.z) * scale
            ),
            attribute=tri.attribute
        )
        new_mesh.triangles.append(new_tri)
    
    return new_mesh


print("CAD导出模块基类加载完成")
print("=" * 60)
