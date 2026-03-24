"""
基础数据类型定义

包含所有建模引擎使用的基础数据结构和枚举类型
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
import numpy as np
from uuid import uuid4


class FeatureType(Enum):
    """特征类型枚举"""
    # 基体特征
    EXTRUDE = auto()      # 拉伸
    REVOLVE = auto()      # 旋转
    SWEEP = auto()        # 扫掠
    LOFT = auto()         # 放样
    PRIMITIVE_BOX = auto()      # 基本体-立方体
    PRIMITIVE_CYLINDER = auto() # 基本体-圆柱
    PRIMITIVE_SPHERE = auto()   # 基本体-球体
    
    # 附加特征
    HOLE = auto()         # 孔
    SLOT = auto()         # 槽
    POCKET = auto()       # 腔体
    BOSS = auto()         # 凸台
    FILLET = auto()       # 圆角
    CHAMFER = auto()      # 倒角
    
    # 铸造专用特征
    DRAFT = auto()        # 拔模斜度
    PARTING_LINE = auto() # 分型线
    PARTING_SURFACE = auto() # 分型面
    RIB = auto()          # 加强筋
    
    # 布尔特征
    BOOLEAN_UNION = auto()      # 布尔并
    BOOLEAN_SUBTRACT = auto()   # 布尔减
    BOOLEAN_INTERSECT = auto()  # 布尔交


class GeometryType(Enum):
    """几何类型枚举"""
    POINT = auto()
    LINE = auto()
    CIRCLE = auto()
    ARC = auto()
    ELLIPSE = auto()
    BEZIER = auto()
    BSPLINE = auto()
    POLYLINE = auto()


@dataclass
class Point3D:
    """3D点"""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    
    def to_tuple(self) -> Tuple[float, float, float]:
        """转换为元组"""
        return (self.x, self.y, self.z)
    
    def to_numpy(self) -> np.ndarray:
        """转换为numpy数组"""
        return np.array([self.x, self.y, self.z])
    
    @staticmethod
    def from_tuple(t: Tuple[float, float, float]) -> 'Point3D':
        """从元组创建"""
        return Point3D(t[0], t[1], t[2])
    
    def __add__(self, other: 'Point3D') -> 'Point3D':
        """点加法"""
        return Point3D(self.x + other.x, self.y + other.y, self.z + other.z)
    
    def __sub__(self, other: 'Point3D') -> 'Point3D':
        """点减法"""
        return Point3D(self.x - other.x, self.y - other.y, self.z - other.z)
    
    def __repr__(self) -> str:
        return f"Point3D({self.x:.3f}, {self.y:.3f}, {self.z:.3f})"


@dataclass
class Vector3D:
    """3D向量"""
    x: float = 0.0
    y: float = 0.0
    z: float = 1.0
    
    def length(self) -> float:
        """向量长度"""
        return np.sqrt(self.x**2 + self.y**2 + self.z**2)
    
    def normalize(self) -> 'Vector3D':
        """归一化"""
        length = self.length()
        if length > 1e-10:
            return Vector3D(self.x/length, self.y/length, self.z/length)
        return Vector3D(0, 0, 1)
    
    def to_tuple(self) -> Tuple[float, float, float]:
        """转换为元组"""
        return (self.x, self.y, self.z)
    
    def dot(self, other: 'Vector3D') -> float:
        """点积"""
        return self.x * other.x + self.y * other.y + self.z * other.z
    
    def cross(self, other: 'Vector3D') -> 'Vector3D':
        """叉积"""
        return Vector3D(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x
        )
    
    @staticmethod
    def from_points(p1: Point3D, p2: Point3D) -> 'Vector3D':
        """从两点创建向量"""
        return Vector3D(p2.x - p1.x, p2.y - p1.y, p2.z - p1.z)
    
    def __repr__(self) -> str:
        return f"Vector3D({self.x:.3f}, {self.y:.3f}, {self.z:.3f})"


@dataclass
class Plane:
    """平面定义"""
    origin: Point3D = field(default_factory=Point3D)
    normal: Vector3D = field(default_factory=lambda: Vector3D(0, 0, 1))
    x_dir: Vector3D = field(default_factory=lambda: Vector3D(1, 0, 0))
    
    def __post_init__(self):
        """确保向量归一化"""
        self.normal = self.normal.normalize()
        self.x_dir = self.x_dir.normalize()
    
    def get_y_dir(self) -> Vector3D:
        """获取Y方向（与normal和x_dir正交）"""
        return self.normal.cross(self.x_dir).normalize()
    
    def project_point(self, point: Point3D) -> Point3D:
        """将点投影到平面"""
        vec = Vector3D.from_points(self.origin, point)
        dist = vec.dot(self.normal)
        return Point3D(
            point.x - dist * self.normal.x,
            point.y - dist * self.normal.y,
            point.z - dist * self.normal.z
        )
    
    def __repr__(self) -> str:
        return f"Plane(origin={self.origin}, normal={self.normal})"


@dataclass
class Profile2D:
    """2D轮廓数据"""
    vertices: List[Point3D] = field(default_factory=list)
    geometry_type: GeometryType = GeometryType.POLYLINE
    is_closed: bool = False
    
    # 圆弧/曲线参数
    arcs: List[Dict[str, Any]] = field(default_factory=list)
    
    # 约束信息
    constraints: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_vertex(self, point: Point3D):
        """添加顶点"""
        self.vertices.append(point)
    
    def close(self):
        """闭合轮廓"""
        self.is_closed = True
    
    def get_bounds(self) -> Tuple[Point3D, Point3D]:
        """获取边界框"""
        if not self.vertices:
            return Point3D(), Point3D()
        
        min_x = min(v.x for v in self.vertices)
        min_y = min(v.y for v in self.vertices)
        min_z = min(v.z for v in self.vertices)
        max_x = max(v.x for v in self.vertices)
        max_y = max(v.y for v in self.vertices)
        max_z = max(v.z for v in self.vertices)
        
        return Point3D(min_x, min_y, min_z), Point3D(max_x, max_y, max_z)
    
    def get_center(self) -> Point3D:
        """获取轮廓中心"""
        if not self.vertices:
            return Point3D()
        
        min_p, max_p = self.get_bounds()
        return Point3D(
            (min_p.x + max_p.x) / 2,
            (min_p.y + max_p.y) / 2,
            (min_p.z + max_p.z) / 2
        )
    
    def calculate_area(self) -> float:
        """计算轮廓面积（使用Shoelace公式）"""
        if len(self.vertices) < 3:
            return 0.0
        
        area = 0.0
        n = len(self.vertices)
        for i in range(n):
            j = (i + 1) % n
            area += self.vertices[i].x * self.vertices[j].y
            area -= self.vertices[j].x * self.vertices[i].y
        
        return abs(area) / 2.0
    
    def __repr__(self) -> str:
        return f"Profile2D(vertices={len(self.vertices)}, closed={self.is_closed})"


@dataclass
class FeatureParameters:
    """特征参数基类"""
    feature_id: str = field(default_factory=lambda: str(uuid4()))
    feature_type: FeatureType = FeatureType.EXTRUDE
    name: str = ""
    parent_id: Optional[str] = None
    is_suppressed: bool = False
    
    # 变换参数
    position: Point3D = field(default_factory=Point3D)
    rotation: Tuple[float, float, float] = (0, 0, 0)  # Euler angles (degrees)
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.feature_id[:8]}, type={self.feature_type.name})"


@dataclass
class ExtrudeParameters(FeatureParameters):
    """拉伸特征参数"""
    profile: Profile2D = field(default_factory=Profile2D)
    plane: Plane = field(default_factory=Plane)
    direction: Vector3D = field(default_factory=lambda: Vector3D(0, 0, 1))
    depth: float = 10.0
    taper_angle: float = 0.0  # 拔模角度（度）
    is_symmetric: bool = False
    is_cut: bool = False  # 是否为切除
    
    def __repr__(self) -> str:
        return f"ExtrudeParameters(depth={self.depth}, taper={self.taper_angle}°)"


@dataclass
class RevolveParameters(FeatureParameters):
    """旋转特征参数"""
    profile: Profile2D = field(default_factory=Profile2D)
    axis_origin: Point3D = field(default_factory=Point3D)
    axis_direction: Vector3D = field(default_factory=lambda: Vector3D(0, 0, 1))
    angle: float = 360.0
    is_cut: bool = False
    
    def __repr__(self) -> str:
        return f"RevolveParameters(angle={self.angle}°)"


@dataclass
class HoleParameters(FeatureParameters):
    """孔特征参数"""
    center: Point3D = field(default_factory=Point3D)
    direction: Vector3D = field(default_factory=lambda: Vector3D(0, 0, 1))
    diameter: float = 10.0
    depth: float = 10.0  # 0表示通孔
    hole_type: str = "simple"  # simple, counterbore, countersink
    counterbore_diameter: float = 0.0
    counterbore_depth: float = 0.0
    countersink_angle: float = 90.0
    
    def __repr__(self) -> str:
        return f"HoleParameters(diameter={self.diameter}, depth={self.depth})"


@dataclass
class FilletParameters(FeatureParameters):
    """圆角特征参数"""
    edge_ids: List[str] = field(default_factory=list)
    radius: float = 2.0
    is_variable: bool = False
    variable_radii: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    
    def __repr__(self) -> str:
        return f"FilletParameters(radius={self.radius}, edges={len(self.edge_ids)})"


@dataclass
class ChamferParameters(FeatureParameters):
    """倒角特征参数"""
    edge_ids: List[str] = field(default_factory=list)
    distance: float = 1.0
    distance2: float = 0.0  # 非对称倒角
    angle: float = 45.0  # 角度倒角
    
    def __repr__(self) -> str:
        return f"ChamferParameters(distance={self.distance})"


@dataclass
class DraftParameters(FeatureParameters):
    """拔模特征参数 (铸造专用)"""
    face_ids: List[str] = field(default_factory=list)
    neutral_plane: Plane = field(default_factory=Plane)
    pull_direction: Vector3D = field(default_factory=lambda: Vector3D(0, 0, 1))
    draft_angle: float = 2.0  # 度
    is_inward: bool = True
    
    def __repr__(self) -> str:
        return f"DraftParameters(angle={self.draft_angle}°, faces={len(self.face_ids)})"


@dataclass
class BooleanParameters(FeatureParameters):
    """布尔运算参数"""
    target_body_id: str = ""
    tool_body_id: str = ""
    operation: str = "union"  # union, subtract, intersect
    
    def __repr__(self) -> str:
        return f"BooleanParameters({self.operation})"


@dataclass
class PrimitiveBoxParameters(FeatureParameters):
    """基本体-立方体参数"""
    corner: Point3D = field(default_factory=Point3D)
    dimensions: Tuple[float, float, float] = (10.0, 10.0, 10.0)  # width, depth, height
    
    def __repr__(self) -> str:
        return f"PrimitiveBoxParameters({self.dimensions})"


@dataclass
class PrimitiveCylinderParameters(FeatureParameters):
    """基本体-圆柱参数"""
    center: Point3D = field(default_factory=Point3D)
    axis: Vector3D = field(default_factory=lambda: Vector3D(0, 0, 1))
    radius: float = 5.0
    height: float = 10.0
    
    def __repr__(self) -> str:
        return f"PrimitiveCylinderParameters(radius={self.radius}, height={self.height})"


@dataclass
class PrimitiveSphereParameters(FeatureParameters):
    """基本体-球体参数"""
    center: Point3D = field(default_factory=Point3D)
    radius: float = 5.0
    
    def __repr__(self) -> str:
        return f"PrimitiveSphereParameters(radius={self.radius})"
