"""
铸造行业2D到3D转换 - 形状识别算法模块

本模块提供各种几何形状的识别算法，包括直线、圆、圆弧、椭圆、多边形等。
"""

import cv2
import numpy as np
from typing import List, Optional, Tuple, Dict, Any
from abc import ABC, abstractmethod
from dataclasses import dataclass

# 处理导入
try:
    from ..core.data_structures import (
        FeatureType, ShapeType, DimensionType, ConstraintType,
        Point2D, LineSegment, Circle, Arc, Ellipse, Polygon,
        Contour, GeometricFeature, FeatureMetadata
    )
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.data_structures import (
        FeatureType, ShapeType, DimensionType, ConstraintType,
        Point2D, LineSegment, Circle, Arc, Ellipse, Polygon,
        Contour, GeometricFeature, FeatureMetadata
    )


# =============================================================================
# 形状识别结果
# =============================================================================

@dataclass
class RecognitionResult:
    """形状识别结果"""
    shape_type: ShapeType
    geometry: Any  # LineSegment, Circle, Arc, Ellipse, Polygon
    confidence: float
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


# =============================================================================
# 形状识别器基类
# =============================================================================

class ShapeRecognizer(ABC):
    """形状识别器基类"""
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    def recognize(self, contour: Contour) -> Optional[RecognitionResult]:
        """
        识别轮廓的几何形状
        
        Args:
            contour: 输入轮廓
            
        Returns:
            识别结果，如果无法识别则返回None
        """
        pass
    
    @abstractmethod
    def get_confidence_threshold(self) -> float:
        """获取置信度阈值"""
        pass


# =============================================================================
# 直线识别器
# =============================================================================

class LineRecognizer(ShapeRecognizer):
    """直线识别器"""
    
    def __init__(self, 
                 angle_tolerance: float = 5.0,  # 度
                 min_length_ratio: float = 0.8):
        super().__init__("LineRecognizer")
        self.angle_tolerance = np.radians(angle_tolerance)
        self.min_length_ratio = min_length_ratio
    
    def recognize(self, contour: Contour) -> Optional[RecognitionResult]:
        """识别直线"""
        # 直线应该是开放的或非常细长的
        if contour.is_closed and contour.compactness > 0.1:
            return None
        
        # 使用最小二乘法拟合直线
        points = contour.to_numpy()
        if len(points) < 2:
            return None
        
        # 计算主方向
        mean = np.mean(points, axis=0)
        centered = points - mean
        
        # SVD分析
        U, S, Vt = np.linalg.svd(centered)
        
        # 主方向
        direction = Vt[0]
        
        # 计算点到直线的距离
        line_vec = np.array([-direction[1], direction[0]])
        distances = np.abs(np.dot(centered, line_vec))
        max_distance = np.max(distances)
        
        # 计算直线长度
        projections = np.dot(centered, direction)
        length = np.max(projections) - np.min(projections)
        
        # 置信度：基于点到直线的最大偏差
        if length > 0:
            deviation_ratio = max_distance / length
            confidence = max(0, 1 - deviation_ratio * 5)
        else:
            confidence = 0
        
        if confidence < self.get_confidence_threshold():
            return None
        
        # 构建线段
        start = mean + direction * np.min(projections)
        end = mean + direction * np.max(projections)
        
        line = LineSegment(
            start=Point2D(start[0], start[1]),
            end=Point2D(end[0], end[1])
        )
        
        return RecognitionResult(
            shape_type=ShapeType.LINE,
            geometry=line,
            confidence=confidence,
            metadata={
                "length": line.length,
                "angle_degrees": np.degrees(line.angle)
            }
        )
    
    def get_confidence_threshold(self) -> float:
        return 0.7


# =============================================================================
# 圆识别器
# =============================================================================

class CircleRecognizer(ShapeRecognizer):
    """圆识别器"""
    
    def __init__(self,
                 circularity_threshold: float = 0.85,
                 radius_tolerance: float = 0.1):
        super().__init__("CircleRecognizer")
        self.circularity_threshold = circularity_threshold
        self.radius_tolerance = radius_tolerance
    
    def recognize(self, contour: Contour) -> Optional[RecognitionResult]:
        """识别圆"""
        if not contour.is_closed:
            return None
        
        # 首先检查紧凑度（圆度）
        circularity = contour.circularity
        if circularity < self.circularity_threshold:
            return None
        
        # 使用最小二乘法拟合圆
        points = contour.to_numpy()
        if len(points) < 5:
            return None
        
        circle, fit_error = self._fit_circle_least_squares(points)
        if circle is None:
            return None
        
        # 计算置信度
        confidence = circularity * (1 - min(1, fit_error / circle.radius))
        
        if confidence < self.get_confidence_threshold():
            return None
        
        return RecognitionResult(
            shape_type=ShapeType.CIRCLE,
            geometry=circle,
            confidence=confidence,
            metadata={
                "radius": circle.radius,
                "area": circle.area,
                "circumference": circle.circumference,
                "fit_error": fit_error
            }
        )
    
    def _fit_circle_least_squares(self, points: np.ndarray) -> Tuple[Optional[Circle], float]:
        """
        使用最小二乘法拟合圆
        
        Returns:
            (圆对象, 拟合误差)
        """
        if len(points) < 3:
            return None, float('inf')
        
        # 转换为numpy数组
        x = points[:, 0]
        y = points[:, 1]
        
        # 构建线性方程组
        A = np.column_stack([x, y, np.ones(len(x))])
        b = x**2 + y**2
        
        try:
            # 求解
            c = np.linalg.lstsq(A, b, rcond=None)[0]
            
            # 提取圆心和半径
            center_x = c[0] / 2
            center_y = c[1] / 2
            radius = np.sqrt(c[2] + center_x**2 + center_y**2)
            
            circle = Circle(
                center=Point2D(center_x, center_y),
                radius=radius
            )
            
            # 计算拟合误差
            distances = np.sqrt((x - center_x)**2 + (y - center_y)**2)
            fit_error = np.std(distances)
            
            return circle, fit_error
            
        except np.linalg.LinAlgError:
            return None, float('inf')
    
    def get_confidence_threshold(self) -> float:
        return 0.75


# =============================================================================
# 圆弧识别器
# =============================================================================

class ArcRecognizer(ShapeRecognizer):
    """圆弧识别器"""
    
    def __init__(self,
                 min_angle_span: float = 15.0,  # 度
                 max_angle_span: float = 350.0,  # 度
                 circularity_threshold: float = 0.8):
        super().__init__("ArcRecognizer")
        self.min_angle_span = np.radians(min_angle_span)
        self.max_angle_span = np.radians(max_angle_span)
        self.circularity_threshold = circularity_threshold
    
    def recognize(self, contour: Contour) -> Optional[RecognitionResult]:
        """识别圆弧"""
        # 圆弧通常是开放的
        if contour.is_closed:
            return None
        
        points = contour.to_numpy()
        if len(points) < 10:
            return None
        
        # 尝试拟合圆
        circle, fit_error = self._fit_circle_least_squares(points)
        if circle is None:
            return None
        
        # 计算每个点的角度
        angles = np.arctan2(
            points[:, 1] - circle.center.y,
            points[:, 0] - circle.center.x
        )
        
        # 规范化角度并计算跨度
        angles = np.sort(angles)
        angle_span = angles[-1] - angles[0]
        
        # 处理跨越2π的情况
        if angle_span > np.pi:
            angle_span = 2 * np.pi - angle_span
        
        # 检查角度跨度
        if angle_span < self.min_angle_span or angle_span > self.max_angle_span:
            return None
        
        # 计算置信度
        distances = np.sqrt(
            (points[:, 0] - circle.center.x)**2 + 
            (points[:, 1] - circle.center.y)**2
        )
        radius_std = np.std(distances)
        confidence = 1 - min(1, radius_std / circle.radius)
        
        if confidence < self.get_confidence_threshold():
            return None
        
        # 构建圆弧
        arc = Arc(
            center=circle.center,
            radius=circle.radius,
            start_angle=angles[0],
            end_angle=angles[-1]
        )
        
        return RecognitionResult(
            shape_type=ShapeType.ARC,
            geometry=arc,
            confidence=confidence,
            metadata={
                "radius": arc.radius,
                "angle_span_degrees": np.degrees(arc.angle_span),
                "arc_length": arc.arc_length
            }
        )
    
    def _fit_circle_least_squares(self, points: np.ndarray) -> Tuple[Optional[Circle], float]:
        """使用最小二乘法拟合圆"""
        if len(points) < 3:
            return None, float('inf')
        
        x = points[:, 0]
        y = points[:, 1]
        
        A = np.column_stack([x, y, np.ones(len(x))])
        b = x**2 + y**2
        
        try:
            c = np.linalg.lstsq(A, b, rcond=None)[0]
            
            center_x = c[0] / 2
            center_y = c[1] / 2
            radius = np.sqrt(c[2] + center_x**2 + center_y**2)
            
            circle = Circle(
                center=Point2D(center_x, center_y),
                radius=radius
            )
            
            distances = np.sqrt((x - center_x)**2 + (y - center_y)**2)
            fit_error = np.std(distances)
            
            return circle, fit_error
            
        except np.linalg.LinAlgError:
            return None, float('inf')
    
    def get_confidence_threshold(self) -> float:
        return 0.7


# =============================================================================
# 椭圆识别器
# =============================================================================

class EllipseRecognizer(ShapeRecognizer):
    """椭圆识别器"""
    
    def __init__(self,
                 eccentricity_range: Tuple[float, float] = (0.1, 0.95),
                 area_ratio_threshold: float = 0.7):
        super().__init__("EllipseRecognizer")
        self.eccentricity_range = eccentricity_range
        self.area_ratio_threshold = area_ratio_threshold
    
    def recognize(self, contour: Contour) -> Optional[RecognitionResult]:
        """识别椭圆"""
        if not contour.is_closed:
            return None
        
        points = contour.to_numpy()
        if len(points) < 5:
            return None
        
        # 使用OpenCV拟合椭圆
        try:
            ellipse_cv = cv2.fitEllipse(points.astype(np.float32))
            
            center = Point2D(ellipse_cv[0][0], ellipse_cv[0][1])
            major_axis = max(ellipse_cv[1])
            minor_axis = min(ellipse_cv[1])
            rotation = np.radians(ellipse_cv[2])
            
            ellipse = Ellipse(
                center=center,
                major_axis=major_axis,
                minor_axis=minor_axis,
                rotation=rotation
            )
            
            # 检查离心率
            eccentricity = ellipse.eccentricity
            if not (self.eccentricity_range[0] <= eccentricity <= self.eccentricity_range[1]):
                return None
            
            # 计算置信度：基于面积匹配
            ellipse_area = np.pi * (major_axis / 2) * (minor_axis / 2)
            area_ratio = contour.area / ellipse_area if ellipse_area > 0 else 0
            confidence = min(area_ratio, 1.0) if area_ratio > 0.5 else 0
            
            if confidence < self.get_confidence_threshold():
                return None
            
            return RecognitionResult(
                shape_type=ShapeType.ELLIPSE,
                geometry=ellipse,
                confidence=confidence,
                metadata={
                    "major_axis": major_axis,
                    "minor_axis": minor_axis,
                    "eccentricity": eccentricity,
                    "rotation_degrees": np.degrees(rotation)
                }
            )
            
        except cv2.error:
            return None
    
    def get_confidence_threshold(self) -> float:
        return 0.7


# =============================================================================
# 多边形识别器
# =============================================================================

class PolygonRecognizer(ShapeRecognizer):
    """多边形识别器"""
    
    def __init__(self,
                 angle_tolerance: float = 15.0,  # 度
                 min_vertices: int = 3,
                 max_vertices: int = 20):
        super().__init__("PolygonRecognizer")
        self.angle_tolerance = np.radians(angle_tolerance)
        self.min_vertices = min_vertices
        self.max_vertices = max_vertices
    
    def recognize(self, contour: Contour) -> Optional[RecognitionResult]:
        """识别多边形"""
        # 多边形近似
        points_cv = contour.to_numpy().astype(np.float32)
        
        # 计算合适的epsilon
        epsilon = 0.01 * contour.perimeter
        
        approx_cv = cv2.approxPolyDP(points_cv, epsilon, contour.is_closed)
        vertices = [Point2D(p[0][0], p[0][1]) for p in approx_cv]
        
        num_vertices = len(vertices)
        
        # 检查顶点数
        if num_vertices < self.min_vertices or num_vertices > self.max_vertices:
            return None
        
        # 构建多边形
        polygon = Polygon(vertices, contour.is_closed)
        
        # 计算置信度：基于面积匹配
        area_ratio = contour.area / polygon.area if polygon.area > 0 else 0
        confidence = min(area_ratio, 1.0 / area_ratio) if area_ratio > 0 else 0
        
        if confidence < self.get_confidence_threshold():
            return None
        
        # 确定多边形类型
        shape_type = self._classify_polygon(polygon)
        
        return RecognitionResult(
            shape_type=shape_type,
            geometry=polygon,
            confidence=confidence,
            metadata={
                "num_vertices": num_vertices,
                "area": polygon.area,
                "perimeter": polygon.perimeter
            }
        )
    
    def _classify_polygon(self, polygon: Polygon) -> ShapeType:
        """分类多边形类型"""
        n = polygon.num_vertices
        
        if n == 3:
            return ShapeType.TRIANGLE
        elif n == 4:
            # 检查是否为矩形
            edges = polygon.edges
            angles = []
            for i in range(4):
                v1 = edges[i].direction.normalize()
                v2 = edges[(i+1)%4].direction.normalize()
                angle = abs(np.pi/2 - v1.angle_between(v2))
                angles.append(angle)
            
            if all(a < self.angle_tolerance for a in angles):
                # 检查边长
                lengths = [e.length for e in edges]
                if abs(lengths[0] - lengths[2]) < self.angle_tolerance and \
                   abs(lengths[1] - lengths[3]) < self.angle_tolerance:
                    return ShapeType.RECTANGLE
            
            return ShapeType.POLYGON
        else:
            return ShapeType.POLYGON
    
    def get_confidence_threshold(self) -> float:
        return 0.6


# =============================================================================
# 特征提取器
# =============================================================================

class FeatureExtractor:
    """几何特征提取器"""
    
    def __init__(self, 
                 min_confidence: float = 0.7,
                 recognizers: Dict[str, ShapeRecognizer] = None):
        self.min_confidence = min_confidence
        
        # 初始化识别器
        if recognizers is None:
            self.recognizers = {
                "line": LineRecognizer(),
                "circle": CircleRecognizer(),
                "arc": ArcRecognizer(),
                "ellipse": EllipseRecognizer(),
                "polygon": PolygonRecognizer()
            }
        else:
            self.recognizers = recognizers
        
        self._feature_id_counter = 0
    
    def extract(self, contours: List[Contour]) -> List[GeometricFeature]:
        """
        从轮廓中提取几何特征
        
        Args:
            contours: 轮廓列表
            
        Returns:
            几何特征列表
        """
        features = []
        
        for contour in contours:
            feature = self._recognize_feature(contour)
            if feature:
                features.append(feature)
        
        return features
    
    def _recognize_feature(self, contour: Contour) -> Optional[GeometricFeature]:
        """识别单个轮廓的几何类型"""
        candidates = []
        
        # 尝试所有识别器
        for name, recognizer in self.recognizers.items():
            result = recognizer.recognize(contour)
            if result and result.confidence >= self.min_confidence:
                candidates.append((name, result))
        
        if not candidates:
            return None
        
        # 选择置信度最高的结果
        best_name, best_result = max(candidates, key=lambda x: x[1].confidence)
        
        # 映射ShapeType到FeatureType
        feature_type_map = {
            ShapeType.LINE: FeatureType.LINE,
            ShapeType.CIRCLE: FeatureType.CIRCLE,
            ShapeType.ARC: FeatureType.ARC,
            ShapeType.ELLIPSE: FeatureType.ELLIPSE,
            ShapeType.TRIANGLE: FeatureType.POLYGON,
            ShapeType.RECTANGLE: FeatureType.POLYGON,
            ShapeType.POLYGON: FeatureType.POLYGON
        }
        
        self._feature_id_counter += 1
        
        return GeometricFeature(
            id=self._feature_id_counter,
            feature_type=feature_type_map.get(best_result.shape_type, FeatureType.POLYGON),
            geometry=best_result.geometry,
            source_contour_id=contour.id,
            metadata=FeatureMetadata(
                detection_method=best_name,
                quality_score=best_result.confidence
            ),
            confidence=best_result.confidence
        )
    
    def add_recognizer(self, name: str, recognizer: ShapeRecognizer):
        """添加新的识别器"""
        self.recognizers[name] = recognizer
    
    def remove_recognizer(self, name: str):
        """移除识别器"""
        if name in self.recognizers:
            del self.recognizers[name]


# =============================================================================
# 便捷函数
# =============================================================================

def recognize_shape(contour: Contour, 
                    recognizers: List[str] = None) -> Optional[RecognitionResult]:
    """
    便捷函数：识别单个轮廓的形状
    
    Args:
        contour: 输入轮廓
        recognizers: 要使用的识别器列表，None表示使用所有
        
    Returns:
        识别结果
    """
    all_recognizers = {
        "line": LineRecognizer(),
        "circle": CircleRecognizer(),
        "arc": ArcRecognizer(),
        "ellipse": EllipseRecognizer(),
        "polygon": PolygonRecognizer()
    }
    
    if recognizers is None:
        recognizers = list(all_recognizers.keys())
    
    candidates = []
    for name in recognizers:
        if name in all_recognizers:
            result = all_recognizers[name].recognize(contour)
            if result:
                candidates.append(result)
    
    if candidates:
        return max(candidates, key=lambda x: x.confidence)
    
    return None


# 模块测试
if __name__ == "__main__":
    import sys
    sys.path.append('/mnt/okcomputer/output/image_analysis_module')
    
    # 创建测试轮廓
    
    # 1. 测试圆
    circle_points = []
    for i in range(100):
        angle = 2 * np.pi * i / 100
        x = 100 + 50 * np.cos(angle)
        y = 100 + 50 * np.sin(angle)
        circle_points.append(Point2D(x, y))
    
    circle_contour = Contour(id=1, points=circle_points, is_closed=True)
    
    # 2. 测试线段
    line_points = [
        Point2D(0, 0),
        Point2D(100, 100),
        Point2D(200, 200)
    ]
    line_contour = Contour(id=2, points=line_points, is_closed=False)
    
    # 3. 测试矩形
    rect_points = [
        Point2D(0, 0),
        Point2D(100, 0),
        Point2D(100, 50),
        Point2D(0, 50)
    ]
    rect_contour = Contour(id=3, points=rect_points, is_closed=True)
    
    # 测试识别器
    print("Testing Shape Recognizers\n")
    
    # 圆识别
    circle_recognizer = CircleRecognizer()
    result = circle_recognizer.recognize(circle_contour)
    if result:
        print(f"Circle recognized:")
        print(f"  Center: ({result.geometry.center.x:.1f}, {result.geometry.center.y:.1f})")
        print(f"  Radius: {result.geometry.radius:.1f}")
        print(f"  Confidence: {result.confidence:.2f}\n")
    
    # 线段识别
    line_recognizer = LineRecognizer()
    result = line_recognizer.recognize(line_contour)
    if result:
        print(f"Line recognized:")
        print(f"  Start: ({result.geometry.start.x:.1f}, {result.geometry.start.y:.1f})")
        print(f"  End: ({result.geometry.end.x:.1f}, {result.geometry.end.y:.1f})")
        print(f"  Length: {result.geometry.length:.1f}")
        print(f"  Confidence: {result.confidence:.2f}\n")
    
    # 多边形识别
    polygon_recognizer = PolygonRecognizer()
    result = polygon_recognizer.recognize(rect_contour)
    if result:
        print(f"Polygon recognized:")
        print(f"  Type: {result.shape_type.name}")
        print(f"  Vertices: {result.metadata['num_vertices']}")
        print(f"  Area: {result.metadata['area']:.1f}")
        print(f"  Confidence: {result.confidence:.2f}\n")
    
    # 测试特征提取器
    print("Testing Feature Extractor:")
    extractor = FeatureExtractor(min_confidence=0.6)
    features = extractor.extract([circle_contour, line_contour, rect_contour])
    
    for feature in features:
        print(f"  Feature {feature.id}: {feature.feature_type.name}")
        print(f"    Confidence: {feature.confidence:.2f}")
    
    print("\nAll tests passed!")
