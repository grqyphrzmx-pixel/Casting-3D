"""
铸造行业2D到3D转换 - 图像分析模块数据结构定义

本模块定义了图像分析过程中使用的所有数据结构，包括几何类型、
轮廓、特征、尺寸和约束等。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Union, Tuple, Any
from enum import Enum, auto
from datetime import datetime
import numpy as np


# =============================================================================
# 枚举类型定义
# =============================================================================

class SourceType(Enum):
    """输入图像源类型"""
    TECHNICAL_DRAWING = auto()  # 技术图纸
    PHOTO = auto()              # 零件照片
    SKETCH = auto()             # 手绘草图
    UNKNOWN = auto()            # 未知类型


class FeatureType(Enum):
    """几何特征类型"""
    POINT = auto()
    LINE = auto()
    ARC = auto()
    CIRCLE = auto()
    ELLIPSE = auto()
    POLYGON = auto()
    BEZIER_CURVE = auto()
    SPLINE = auto()
    COMPOSITE = auto()


class ShapeType(Enum):
    """形状类型（用于轮廓分类）"""
    UNKNOWN = auto()
    LINE = auto()
    CIRCLE = auto()
    ARC = auto()
    ELLIPSE = auto()
    TRIANGLE = auto()
    RECTANGLE = auto()
    POLYGON = auto()
    IRREGULAR = auto()


class DimensionType(Enum):
    """尺寸类型"""
    LINEAR = auto()      # 线性尺寸
    ANGULAR = auto()     # 角度尺寸
    RADIUS = auto()      # 半径
    DIAMETER = auto()    # 直径
    CHAMFER = auto()     # 倒角
    DEPTH = auto()       # 深度


class ConstraintType(Enum):
    """几何约束类型"""
    PARALLEL = auto()       # 平行
    PERPENDICULAR = auto()  # 垂直
    TANGENT = auto()        # 相切
    COINCIDENT = auto()     # 重合
    CONCENTRIC = auto()     # 同心
    HORIZONTAL = auto()     # 水平
    VERTICAL = auto()       # 竖直
    EQUAL_LENGTH = auto()   # 等长
    EQUAL_RADIUS = auto()   # 等半径
    SYMMETRIC = auto()      # 对称


class ProcessingStatus(Enum):
    """处理状态"""
    PENDING = auto()
    PROCESSING = auto()
    COMPLETED = auto()
    FAILED = auto()
    PARTIAL = auto()


# =============================================================================
# 基础几何类型
# =============================================================================

@dataclass
class Point2D:
    """二维点"""
    x: float
    y: float
    confidence: float = 1.0
    
    def to_tuple(self) -> Tuple[float, float]:
        """转换为元组"""
        return (self.x, self.y)
    
    def to_numpy(self) -> np.ndarray:
        """转换为numpy数组"""
        return np.array([self.x, self.y])
    
    def distance_to(self, other: 'Point2D') -> float:
        """计算到另一点的距离"""
        return np.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
    
    def __add__(self, other: 'Point2D') -> 'Point2D':
        return Point2D(self.x + other.x, self.y + other.y, min(self.confidence, other.confidence))
    
    def __sub__(self, other: 'Point2D') -> 'Point2D':
        return Point2D(self.x - other.x, self.y - other.y, min(self.confidence, other.confidence))
    
    def __mul__(self, scalar: float) -> 'Point2D':
        return Point2D(self.x * scalar, self.y * scalar, self.confidence)
    
    def __repr__(self) -> str:
        return f"Point2D({self.x:.2f}, {self.y:.2f})"


@dataclass
class Vector2D:
    """二维向量"""
    x: float
    y: float
    
    @property
    def magnitude(self) -> float:
        """向量长度"""
        return np.sqrt(self.x**2 + self.y**2)
    
    @property
    def angle(self) -> float:
        """向量角度（弧度）"""
        return np.arctan2(self.y, self.x)
    
    def normalize(self) -> 'Vector2D':
        """归一化"""
        mag = self.magnitude
        if mag > 0:
            return Vector2D(self.x / mag, self.y / mag)
        return Vector2D(0, 0)
    
    def dot(self, other: 'Vector2D') -> float:
        """点积"""
        return self.x * other.x + self.y * other.y
    
    def cross(self, other: 'Vector2D') -> float:
        """叉积（标量）"""
        return self.x * other.y - self.y * other.x
    
    def angle_between(self, other: 'Vector2D') -> float:
        """计算两向量夹角（弧度）"""
        cos_angle = self.dot(other) / (self.magnitude * other.magnitude)
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        return np.arccos(cos_angle)


@dataclass
class BoundingBox:
    """边界框"""
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    
    @property
    def width(self) -> float:
        return self.x_max - self.x_min
    
    @property
    def height(self) -> float:
        return self.y_max - self.y_min
    
    @property
    def area(self) -> float:
        return self.width * self.height
    
    @property
    def center(self) -> Point2D:
        return Point2D(
            (self.x_min + self.x_max) / 2,
            (self.y_min + self.y_max) / 2
        )
    
    @property
    def aspect_ratio(self) -> float:
        """宽高比"""
        if self.height > 0:
            return self.width / self.height
        return 0
    
    def contains(self, point: Point2D) -> bool:
        """检查点是否在边界框内"""
        return (self.x_min <= point.x <= self.x_max and
                self.y_min <= point.y <= self.y_max)
    
    def intersects(self, other: 'BoundingBox') -> bool:
        """检查是否与另一个边界框相交"""
        return not (self.x_max < other.x_min or self.x_min > other.x_max or
                   self.y_max < other.y_min or self.y_min > other.y_max)
    
    def to_tuple(self) -> Tuple[float, float, float, float]:
        return (self.x_min, self.y_min, self.x_max, self.y_max)


# =============================================================================
# 几何特征类型
# =============================================================================

@dataclass
class LineSegment:
    """线段"""
    start: Point2D
    end: Point2D
    
    @property
    def length(self) -> float:
        """线段长度"""
        return self.start.distance_to(self.end)
    
    @property
    def direction(self) -> Vector2D:
        """方向向量"""
        return Vector2D(
            self.end.x - self.start.x,
            self.end.y - self.start.y
        )
    
    @property
    def angle(self) -> float:
        """线段角度（弧度）"""
        return self.direction.angle
    
    @property
    def midpoint(self) -> Point2D:
        """中点"""
        return Point2D(
            (self.start.x + self.end.x) / 2,
            (self.start.y + self.end.y) / 2
        )
    
    def point_at(self, t: float) -> Point2D:
        """参数t处的点 (t in [0, 1])"""
        return Point2D(
            self.start.x + t * (self.end.x - self.start.x),
            self.start.y + t * (self.end.y - self.start.y)
        )
    
    def distance_to_point(self, point: Point2D) -> float:
        """点到线段的距离"""
        # 投影参数
        line_vec = self.direction
        point_vec = Vector2D(point.x - self.start.x, point.y - self.start.y)
        
        line_len_sq = line_vec.x**2 + line_vec.y**2
        if line_len_sq == 0:
            return self.start.distance_to(point)
        
        t = max(0, min(1, point_vec.dot(line_vec) / line_len_sq))
        projection = self.point_at(t)
        return projection.distance_to(point)


@dataclass
class Circle:
    """圆"""
    center: Point2D
    radius: float
    
    @property
    def diameter(self) -> float:
        return 2 * self.radius
    
    @property
    def circumference(self) -> float:
        return 2 * np.pi * self.radius
    
    @property
    def area(self) -> float:
        return np.pi * self.radius**2
    
    def point_at_angle(self, angle: float) -> Point2D:
        """角度处的点（弧度）"""
        return Point2D(
            self.center.x + self.radius * np.cos(angle),
            self.center.y + self.radius * np.sin(angle)
        )
    
    def contains(self, point: Point2D) -> bool:
        """检查点是否在圆内"""
        return self.center.distance_to(point) <= self.radius
    
    def distance_to_point(self, point: Point2D) -> float:
        """点到圆的距离"""
        return abs(self.center.distance_to(point) - self.radius)


@dataclass
class Arc:
    """圆弧"""
    center: Point2D
    radius: float
    start_angle: float  # 弧度
    end_angle: float    # 弧度
    
    @property
    def angle_span(self) -> float:
        """圆弧跨度（弧度）"""
        span = self.end_angle - self.start_angle
        # 规范化到 [-2π, 2π]
        while span > 2 * np.pi:
            span -= 2 * np.pi
        while span < -2 * np.pi:
            span += 2 * np.pi
        return span
    
    @property
    def arc_length(self) -> float:
        """弧长"""
        return self.radius * abs(self.angle_span)
    
    @property
    def start_point(self) -> Point2D:
        return self.point_at_angle(self.start_angle)
    
    @property
    def end_point(self) -> Point2D:
        return self.point_at_angle(self.end_angle)
    
    def point_at_angle(self, angle: float) -> Point2D:
        """角度处的点"""
        return Point2D(
            self.center.x + self.radius * np.cos(angle),
            self.center.y + self.radius * np.sin(angle)
        )
    
    def is_angle_on_arc(self, angle: float) -> bool:
        """检查角度是否在圆弧范围内"""
        # 规范化角度
        angle = angle % (2 * np.pi)
        start = self.start_angle % (2 * np.pi)
        end = self.end_angle % (2 * np.pi)
        
        if self.angle_span > 0:
            if start <= end:
                return start <= angle <= end
            else:
                return angle >= start or angle <= end
        else:
            if start >= end:
                return end <= angle <= start
            else:
                return angle <= start or angle >= end


@dataclass
class Ellipse:
    """椭圆"""
    center: Point2D
    major_axis: float    # 长轴长度
    minor_axis: float    # 短轴长度
    rotation: float      # 旋转角度（弧度）
    
    @property
    def eccentricity(self) -> float:
        """离心率"""
        a = self.major_axis / 2
        b = self.minor_axis / 2
        if a > b:
            return np.sqrt(1 - (b**2 / a**2))
        return 0
    
    def point_at_angle(self, angle: float) -> Point2D:
        """参数角度处的点"""
        a = self.major_axis / 2
        b = self.minor_axis / 2
        
        # 未旋转的点
        x = a * np.cos(angle)
        y = b * np.sin(angle)
        
        # 旋转
        cos_r = np.cos(self.rotation)
        sin_r = np.sin(self.rotation)
        
        return Point2D(
            self.center.x + x * cos_r - y * sin_r,
            self.center.y + x * sin_r + y * cos_r
        )


@dataclass
class Polygon:
    """多边形"""
    vertices: List[Point2D]
    is_closed: bool = True
    
    @property
    def num_vertices(self) -> int:
        return len(self.vertices)
    
    @property
    def edges(self) -> List[LineSegment]:
        """边列表"""
        edges = []
        for i in range(len(self.vertices)):
            start = self.vertices[i]
            end = self.vertices[(i + 1) % len(self.vertices)]
            edges.append(LineSegment(start, end))
        return edges
    
    @property
    def perimeter(self) -> float:
        """周长"""
        return sum(edge.length for edge in self.edges)
    
    @property
    def area(self) -> float:
        """面积（鞋带公式）"""
        n = len(self.vertices)
        if n < 3:
            return 0
        
        area = 0
        for i in range(n):
            j = (i + 1) % n
            area += self.vertices[i].x * self.vertices[j].y
            area -= self.vertices[j].x * self.vertices[i].y
        
        return abs(area) / 2
    
    @property
    def centroid(self) -> Point2D:
        """质心"""
        n = len(self.vertices)
        if n == 0:
            return Point2D(0, 0)
        
        cx = sum(v.x for v in self.vertices) / n
        cy = sum(v.y for v in self.vertices) / n
        return Point2D(cx, cy)
    
    @property
    def bounding_box(self) -> BoundingBox:
        """边界框"""
        if not self.vertices:
            return BoundingBox(0, 0, 0, 0)
        
        xs = [v.x for v in self.vertices]
        ys = [v.y for v in self.vertices]
        return BoundingBox(min(xs), min(ys), max(xs), max(ys))
    
    def contains(self, point: Point2D) -> bool:
        """射线法判断点是否在多边形内"""
        n = len(self.vertices)
        inside = False
        
        j = n - 1
        for i in range(n):
            vi = self.vertices[i]
            vj = self.vertices[j]
            
            if ((vi.y > point.y) != (vj.y > point.y)) and \
               (point.x < (vj.x - vi.x) * (point.y - vi.y) / (vj.y - vi.y) + vi.x):
                inside = not inside
            j = i
        
        return inside


# 几何特征联合类型
GeometryType = Union[Point2D, LineSegment, Circle, Arc, Ellipse, Polygon]


# =============================================================================
# 轮廓数据结构
# =============================================================================

@dataclass
class Contour:
    """轮廓数据结构"""
    id: int
    points: List[Point2D]
    is_closed: bool = False
    parent_id: Optional[int] = None
    children_ids: List[int] = field(default_factory=list)
    shape_type: ShapeType = ShapeType.UNKNOWN
    confidence: float = 0.0
    
    # 缓存的计算属性
    _area: Optional[float] = None
    _perimeter: Optional[float] = None
    _bounding_box: Optional[BoundingBox] = None
    _centroid: Optional[Point2D] = None
    _approx_points: Optional[List[Point2D]] = None
    
    @property
    def num_points(self) -> int:
        return len(self.points)
    
    @property
    def area(self) -> float:
        """轮廓面积（使用多边形面积公式）"""
        if self._area is None:
            if len(self.points) < 3:
                self._area = 0
            else:
                polygon = Polygon(self.points, self.is_closed)
                self._area = polygon.area
        return self._area
    
    @property
    def perimeter(self) -> float:
        """轮廓周长"""
        if self._perimeter is None:
            if len(self.points) < 2:
                self._perimeter = 0
            else:
                total = 0
                for i in range(len(self.points) - 1):
                    total += self.points[i].distance_to(self.points[i + 1])
                if self.is_closed and len(self.points) > 2:
                    total += self.points[-1].distance_to(self.points[0])
                self._perimeter = total
        return self._perimeter
    
    @property
    def bounding_box(self) -> BoundingBox:
        """边界框"""
        if self._bounding_box is None:
            if not self.points:
                self._bounding_box = BoundingBox(0, 0, 0, 0)
            else:
                xs = [p.x for p in self.points]
                ys = [p.y for p in self.points]
                self._bounding_box = BoundingBox(min(xs), min(ys), max(xs), max(ys))
        return self._bounding_box
    
    @property
    def centroid(self) -> Point2D:
        """质心"""
        if self._centroid is None:
            if not self.points:
                self._centroid = Point2D(0, 0)
            else:
                cx = sum(p.x for p in self.points) / len(self.points)
                cy = sum(p.y for p in self.points) / len(self.points)
                self._centroid = Point2D(cx, cy)
        return self._centroid
    
    @property
    def compactness(self) -> float:
        """紧凑度 (4π × 面积 / 周长²)，圆形为1"""
        if self.perimeter > 0:
            return 4 * np.pi * self.area / (self.perimeter ** 2)
        return 0
    
    @property
    def circularity(self) -> float:
        """圆度（与圆的相似度）"""
        return self.compactness
    
    def to_numpy(self) -> np.ndarray:
        """转换为numpy数组"""
        return np.array([[p.x, p.y] for p in self.points])
    
    def get_approx_polygon(self, epsilon: float = None) -> List[Point2D]:
        """获取多边形近似（Douglas-Peucker算法）"""
        if self._approx_points is None:
            # 这里需要OpenCV的approxPolyDP实现
            # 暂时返回原始点
            self._approx_points = self.points
        return self._approx_points


# =============================================================================
# 特征数据结构
# =============================================================================

@dataclass
class FeatureMetadata:
    """特征元数据"""
    detection_method: str = ""
    processing_params: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    quality_score: float = 0.0
    processing_time_ms: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "detection_method": self.detection_method,
            "processing_params": self.processing_params,
            "timestamp": self.timestamp.isoformat(),
            "quality_score": self.quality_score,
            "processing_time_ms": self.processing_time_ms
        }


@dataclass
class GeometricFeature:
    """几何特征"""
    id: int
    feature_type: FeatureType
    geometry: GeometryType
    source_contour_id: Optional[int] = None
    metadata: FeatureMetadata = field(default_factory=FeatureMetadata)
    confidence: float = 0.0
    
    @property
    def bounding_box(self) -> BoundingBox:
        """获取特征的边界框"""
        if isinstance(self.geometry, Point2D):
            return BoundingBox(
                self.geometry.x, self.geometry.y,
                self.geometry.x, self.geometry.y
            )
        elif isinstance(self.geometry, LineSegment):
            xs = [self.geometry.start.x, self.geometry.end.x]
            ys = [self.geometry.start.y, self.geometry.end.y]
            return BoundingBox(min(xs), min(ys), max(xs), max(ys))
        elif isinstance(self.geometry, (Circle, Arc)):
            r = self.geometry.radius
            return BoundingBox(
                self.geometry.center.x - r, self.geometry.center.y - r,
                self.geometry.center.x + r, self.geometry.center.y + r
            )
        elif isinstance(self.geometry, Ellipse):
            # 简化处理，使用长轴作为半径
            r = self.geometry.major_axis / 2
            return BoundingBox(
                self.geometry.center.x - r, self.geometry.center.y - r,
                self.geometry.center.x + r, self.geometry.center.y + r
            )
        elif isinstance(self.geometry, Polygon):
            return self.geometry.bounding_box
        return BoundingBox(0, 0, 0, 0)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        geo_dict = {}
        
        if isinstance(self.geometry, Point2D):
            geo_dict = {"x": self.geometry.x, "y": self.geometry.y}
        elif isinstance(self.geometry, LineSegment):
            geo_dict = {
                "start": {"x": self.geometry.start.x, "y": self.geometry.start.y},
                "end": {"x": self.geometry.end.x, "y": self.geometry.end.y}
            }
        elif isinstance(self.geometry, Circle):
            geo_dict = {
                "center": {"x": self.geometry.center.x, "y": self.geometry.center.y},
                "radius": self.geometry.radius
            }
        elif isinstance(self.geometry, Arc):
            geo_dict = {
                "center": {"x": self.geometry.center.x, "y": self.geometry.center.y},
                "radius": self.geometry.radius,
                "start_angle": self.geometry.start_angle,
                "end_angle": self.geometry.end_angle
            }
        elif isinstance(self.geometry, Ellipse):
            geo_dict = {
                "center": {"x": self.geometry.center.x, "y": self.geometry.center.y},
                "major_axis": self.geometry.major_axis,
                "minor_axis": self.geometry.minor_axis,
                "rotation": self.geometry.rotation
            }
        elif isinstance(self.geometry, Polygon):
            geo_dict = {
                "vertices": [{"x": v.x, "y": v.y} for v in self.geometry.vertices],
                "is_closed": self.geometry.is_closed
            }
        
        return {
            "id": self.id,
            "type": self.feature_type.name.lower(),
            "geometry": geo_dict,
            "confidence": self.confidence,
            "metadata": self.metadata.to_dict()
        }


# =============================================================================
# 尺寸和约束数据结构
# =============================================================================

@dataclass
class Dimension:
    """尺寸标注"""
    id: int
    dimension_type: DimensionType
    value: float
    unit: str = "mm"
    text_position: Optional[Point2D] = None
    associated_features: List[int] = field(default_factory=list)
    confidence: float = 0.0
    raw_text: str = ""  # OCR识别的原始文本
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.dimension_type.name.lower(),
            "value": self.value,
            "unit": self.unit,
            "text_position": self.text_position.to_tuple() if self.text_position else None,
            "associated_features": self.associated_features,
            "confidence": self.confidence,
            "raw_text": self.raw_text
        }


@dataclass
class Constraint:
    """几何约束"""
    id: int
    constraint_type: ConstraintType
    feature_ids: List[int]
    parameters: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.constraint_type.name.lower(),
            "feature_ids": self.feature_ids,
            "parameters": self.parameters,
            "confidence": self.confidence
        }


# =============================================================================
# 分析结果数据结构
# =============================================================================

@dataclass
class ImageInfo:
    """图像信息"""
    width: int
    height: int
    source_type: SourceType
    original_path: str = ""
    format: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "width": self.width,
            "height": self.height,
            "source_type": self.source_type.name.lower(),
            "original_path": self.original_path,
            "format": self.format
        }


@dataclass
class AnalysisMetadata:
    """分析元数据"""
    version: str = "1.0.0"
    processing_time_seconds: float = 0.0
    algorithm_version: str = "1.0.0"
    timestamp: datetime = field(default_factory=datetime.now)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "version": self.version,
            "processing_time_seconds": self.processing_time_seconds,
            "algorithm_version": self.algorithm_version,
            "timestamp": self.timestamp.isoformat(),
            "errors": self.errors,
            "warnings": self.warnings
        }


@dataclass
class AnalysisResult:
    """分析结果"""
    image_info: ImageInfo
    contours: List[Contour] = field(default_factory=list)
    features: List[GeometricFeature] = field(default_factory=list)
    dimensions: List[Dimension] = field(default_factory=list)
    constraints: List[Constraint] = field(default_factory=list)
    scale_factor: float = 1.0  # 像素到毫米的比例
    metadata: AnalysisMetadata = field(default_factory=AnalysisMetadata)
    
    @property
    def num_contours(self) -> int:
        return len(self.contours)
    
    @property
    def num_features(self) -> int:
        return len(self.features)
    
    @property
    def num_dimensions(self) -> int:
        return len(self.dimensions)
    
    def get_features_by_type(self, feature_type: FeatureType) -> List[GeometricFeature]:
        """按类型获取特征"""
        return [f for f in self.features if f.feature_type == feature_type]
    
    def get_feature_by_id(self, feature_id: int) -> Optional[GeometricFeature]:
        """按ID获取特征"""
        for f in self.features:
            if f.id == feature_id:
                return f
        return None
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "image_info": self.image_info.to_dict(),
            "contours": [
                {
                    "id": c.id,
                    "num_points": c.num_points,
                    "is_closed": c.is_closed,
                    "shape_type": c.shape_type.name.lower(),
                    "area": c.area,
                    "perimeter": c.perimeter,
                    "confidence": c.confidence
                }
                for c in self.contours
            ],
            "features": [f.to_dict() for f in self.features],
            "dimensions": [d.to_dict() for d in self.dimensions],
            "constraints": [c.to_dict() for c in self.constraints],
            "scale_factor": self.scale_factor,
            "metadata": self.metadata.to_dict()
        }
    
    def to_json(self, indent: int = 2) -> str:
        """转换为JSON字符串"""
        import json
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


# =============================================================================
# 辅助函数
# =============================================================================

def create_contour_from_numpy(points: np.ndarray, 
                               contour_id: int = 0,
                               is_closed: bool = False) -> Contour:
    """从numpy数组创建轮廓"""
    point_list = [Point2D(float(p[0]), float(p[1])) for p in points]
    return Contour(
        id=contour_id,
        points=point_list,
        is_closed=is_closed
    )


def merge_contours(contours: List[Contour], 
                   new_id: int = 0) -> Contour:
    """合并多个轮廓"""
    all_points = []
    for c in contours:
        all_points.extend(c.points)
    return Contour(
        id=new_id,
        points=all_points,
        is_closed=False
    )


def calculate_bounding_box_of_features(features: List[GeometricFeature]) -> BoundingBox:
    """计算多个特征的联合边界框"""
    if not features:
        return BoundingBox(0, 0, 0, 0)
    
    boxes = [f.bounding_box for f in features]
    return BoundingBox(
        min(b.x_min for b in boxes),
        min(b.y_min for b in boxes),
        max(b.x_max for b in boxes),
        max(b.y_max for b in boxes)
    )


# 模块测试
if __name__ == "__main__":
    # 测试基础几何类型
    p1 = Point2D(0, 0)
    p2 = Point2D(3, 4)
    print(f"Point1: {p1}")
    print(f"Point2: {p2}")
    print(f"Distance: {p1.distance_to(p2)}")
    
    # 测试线段
    line = LineSegment(p1, p2)
    print(f"Line length: {line.length}")
    print(f"Line angle: {np.degrees(line.angle)} degrees")
    
    # 测试圆
    circle = Circle(Point2D(0, 0), 5)
    print(f"Circle area: {circle.area}")
    print(f"Circle circumference: {circle.circumference}")
    
    # 测试多边形
    polygon = Polygon([
        Point2D(0, 0),
        Point2D(4, 0),
        Point2D(4, 3),
        Point2D(0, 3)
    ])
    print(f"Polygon area: {polygon.area}")
    print(f"Polygon perimeter: {polygon.perimeter}")
    
    # 测试轮廓
    contour = Contour(
        id=1,
        points=[Point2D(0, 0), Point2D(1, 0), Point2D(1, 1), Point2D(0, 1)],
        is_closed=True
    )
    print(f"Contour area: {contour.area}")
    print(f"Contour perimeter: {contour.perimeter}")
    
    print("\nAll tests passed!")
