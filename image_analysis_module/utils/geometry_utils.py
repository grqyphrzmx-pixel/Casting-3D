"""
铸造行业2D到3D转换 - 几何计算工具模块

本模块提供各种几何计算工具函数。
"""

import numpy as np
from typing import List, Tuple, Optional
from scipy.optimize import least_squares

# 导入数据结构
try:
    from ..core.data_structures import Point2D, LineSegment, Circle, Arc
except ImportError:
    # 直接导入（用于独立测试）
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.data_structures import Point2D, LineSegment, Circle, Arc


# =============================================================================
# 点相关计算
# =============================================================================

def point_distance(p1: Point2D, p2: Point2D) -> float:
    """计算两点间距离"""
    return np.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)


def point_to_line_distance(point: Point2D, line: LineSegment) -> float:
    """计算点到线段的距离"""
    return line.distance_to_point(point)


def point_in_polygon(point: Point2D, polygon: List[Point2D]) -> bool:
    """
    射线法判断点是否在多边形内
    
    Args:
        point: 测试点
        polygon: 多边形顶点列表
        
    Returns:
        是否在多边形内
    """
    n = len(polygon)
    inside = False
    
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i].x, polygon[i].y
        xj, yj = polygon[j].x, polygon[j].y
        
        if ((yi > point.y) != (yj > point.y)) and \
           (point.x < (xj - xi) * (point.y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    
    return inside


def closest_point_on_line(point: Point2D, line: LineSegment) -> Point2D:
    """计算点到直线的最近点"""
    line_vec = np.array([line.end.x - line.start.x, line.end.y - line.start.y])
    point_vec = np.array([point.x - line.start.x, point.y - line.start.y])
    
    line_len_sq = np.dot(line_vec, line_vec)
    if line_len_sq == 0:
        return line.start
    
    t = max(0, min(1, np.dot(point_vec, line_vec) / line_len_sq))
    
    return Point2D(
        line.start.x + t * line_vec[0],
        line.start.y + t * line_vec[1]
    )


# =============================================================================
# 直线相关计算
# =============================================================================

def line_intersection(line1: LineSegment, line2: LineSegment) -> Optional[Point2D]:
    """
    计算两条线段的交点
    
    Args:
        line1: 第一条线段
        line2: 第二条线段
        
    Returns:
        交点，如果不相交则返回None
    """
    x1, y1 = line1.start.x, line1.start.y
    x2, y2 = line1.end.x, line1.end.y
    x3, y3 = line2.start.x, line2.start.y
    x4, y4 = line2.end.x, line2.end.y
    
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    
    if abs(denom) < 1e-10:
        return None  # 平行
    
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom
    
    if 0 <= t <= 1 and 0 <= u <= 1:
        x = x1 + t * (x2 - x1)
        y = y1 + t * (y2 - y1)
        return Point2D(x, y)
    
    return None


def line_angle(line: LineSegment) -> float:
    """计算线段角度（弧度）"""
    return np.arctan2(line.end.y - line.start.y, line.end.x - line.start.x)


def lines_parallel(line1: LineSegment, line2: LineSegment, 
                   tolerance: float = 1e-6) -> bool:
    """判断两条线段是否平行"""
    angle1 = line_angle(line1)
    angle2 = line_angle(line2)
    
    diff = abs(angle1 - angle2)
    diff = min(diff, np.pi - diff)  # 处理角度周期
    
    return diff < tolerance


def lines_perpendicular(line1: LineSegment, line2: LineSegment,
                        tolerance: float = 1e-6) -> bool:
    """判断两条线段是否垂直"""
    angle1 = line_angle(line1)
    angle2 = line_angle(line2)
    
    diff = abs(abs(angle1 - angle2) - np.pi / 2)
    
    return diff < tolerance


def fit_line_least_squares(points: List[Point2D]) -> Tuple[Point2D, Point2D, float]:
    """
    使用最小二乘法拟合直线
    
    Args:
        points: 点列表
        
    Returns:
        (直线上一点, 方向向量, 拟合误差)
    """
    if len(points) < 2:
        raise ValueError("At least 2 points required")
    
    # 转换为numpy数组
    pts = np.array([[p.x, p.y] for p in points])
    
    # 计算均值
    mean = np.mean(pts, axis=0)
    
    # SVD分析
    centered = pts - mean
    U, S, Vt = np.linalg.svd(centered)
    
    # 主方向
    direction = Vt[0]
    
    # 计算拟合误差
    perpendicular = np.array([-direction[1], direction[0]])
    distances = np.abs(np.dot(centered, perpendicular))
    fit_error = np.mean(distances)
    
    return Point2D(mean[0], mean[1]), Point2D(direction[0], direction[1]), fit_error


# =============================================================================
# 圆相关计算
# =============================================================================

def fit_circle_least_squares(points: List[Point2D]) -> Tuple[Optional[Circle], float]:
    """
    使用最小二乘法拟合圆
    
    Args:
        points: 点列表
        
    Returns:
        (圆对象, 拟合误差)
    """
    if len(points) < 3:
        return None, float('inf')
    
    # 转换为numpy数组
    x = np.array([p.x for p in points])
    y = np.array([p.y for p in points])
    
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


def fit_circle_algebraic(points: List[Point2D]) -> Tuple[Optional[Circle], float]:
    """
    使用代数方法拟合圆（更稳定）
    
    Args:
        points: 点列表
        
    Returns:
        (圆对象, 拟合误差)
    """
    if len(points) < 3:
        return None, float('inf')
    
    pts = np.array([[p.x, p.y] for p in points])
    
    # 中心化
    mean = np.mean(pts, axis=0)
    centered = pts - mean
    
    # 构建矩阵
    x = centered[:, 0]
    y = centered[:, 1]
    z = x**2 + y**2
    
    Z = np.column_stack([z, x, y, np.ones(len(x))])
    
    # SVD求解
    U, S, Vt = np.linalg.svd(Z)
    
    # 最小奇异值对应的解
    A = Vt[-1]
    
    # 提取参数
    a = -A[1] / (2 * A[0])
    b = -A[2] / (2 * A[0])
    r_squared = (A[1]**2 + A[2]**2 - 4 * A[0] * A[3]) / (4 * A[0]**2)
    
    if r_squared < 0:
        return None, float('inf')
    
    radius = np.sqrt(r_squared)
    center = Point2D(mean[0] + a, mean[1] + b)
    
    circle = Circle(center=center, radius=radius)
    
    # 计算拟合误差
    distances = np.sqrt((pts[:, 0] - center.x)**2 + (pts[:, 1] - center.y)**2)
    fit_error = np.std(distances)
    
    return circle, fit_error


def circle_from_three_points(p1: Point2D, p2: Point2D, p3: Point2D) -> Optional[Circle]:
    """
    通过三点确定圆
    
    Args:
        p1, p2, p3: 三个点
        
    Returns:
        圆对象，如果三点共线则返回None
    """
    # 计算行列式
    d = 2 * (p1.x * (p2.y - p3.y) + p2.x * (p3.y - p1.y) + p3.x * (p1.y - p2.y))
    
    if abs(d) < 1e-10:
        return None  # 三点共线
    
    ux = ((p1.x**2 + p1.y**2) * (p2.y - p3.y) +
          (p2.x**2 + p2.y**2) * (p3.y - p1.y) +
          (p3.x**2 + p3.y**2) * (p1.y - p2.y)) / d
    
    uy = ((p1.x**2 + p1.y**2) * (p3.x - p2.x) +
          (p2.x**2 + p2.y**2) * (p1.x - p3.x) +
          (p3.x**2 + p3.y**2) * (p2.x - p1.x)) / d
    
    center = Point2D(ux, uy)
    radius = point_distance(center, p1)
    
    return Circle(center=center, radius=radius)


def circle_circularity(points: List[Point2D], circle: Circle) -> float:
    """
    计算点集相对于圆的圆度
    
    Args:
        points: 点列表
        circle: 参考圆
        
    Returns:
        圆度值 (0-1)
    """
    if len(points) < 3:
        return 0
    
    distances = [point_distance(p, circle.center) for p in points]
    mean_dist = np.mean(distances)
    
    if mean_dist == 0:
        return 0
    
    std_dist = np.std(distances)
    circularity = max(0, 1 - std_dist / mean_dist)
    
    return circularity


# =============================================================================
# 圆弧相关计算
# =============================================================================

def arc_from_points(points: List[Point2D]) -> Tuple[Optional[Arc], float]:
    """
    从点序列拟合圆弧
    
    Args:
        points: 点列表
        
    Returns:
        (圆弧对象, 拟合误差)
    """
    if len(points) < 10:
        return None, float('inf')
    
    # 先拟合圆
    circle, fit_error = fit_circle_least_squares(points)
    if circle is None:
        return None, float('inf')
    
    # 计算每个点的角度
    angles = []
    for p in points:
        angle = np.arctan2(p.y - circle.center.y, p.x - circle.center.x)
        angles.append(angle)
    
    # 排序角度
    angles = np.array(angles)
    sorted_indices = np.argsort(angles)
    sorted_angles = angles[sorted_indices]
    
    # 计算角度跨度
    angle_span = sorted_angles[-1] - sorted_angles[0]
    
    # 处理跨越2π的情况
    if angle_span > np.pi:
        angle_span = 2 * np.pi - angle_span
    
    arc = Arc(
        center=circle.center,
        radius=circle.radius,
        start_angle=sorted_angles[0],
        end_angle=sorted_angles[-1]
    )
    
    return arc, fit_error


def arc_length(arc: Arc) -> float:
    """计算弧长"""
    return arc.radius * abs(arc.angle_span)


def arc_midpoint(arc: Arc) -> Point2D:
    """计算圆弧中点"""
    mid_angle = (arc.start_angle + arc.end_angle) / 2
    return Point2D(
        arc.center.x + arc.radius * np.cos(mid_angle),
        arc.center.y + arc.radius * np.sin(mid_angle)
    )


# =============================================================================
# 多边形相关计算
# =============================================================================

def polygon_area(points: List[Point2D]) -> float:
    """
    计算多边形面积（鞋带公式）
    
    Args:
        points: 多边形顶点
        
    Returns:
        面积
    """
    n = len(points)
    if n < 3:
        return 0
    
    area = 0
    for i in range(n):
        j = (i + 1) % n
        area += points[i].x * points[j].y
        area -= points[j].x * points[i].y
    
    return abs(area) / 2


def polygon_centroid(points: List[Point2D]) -> Point2D:
    """
    计算多边形质心
    
    Args:
        points: 多边形顶点
        
    Returns:
        质心点
    """
    n = len(points)
    if n == 0:
        return Point2D(0, 0)
    
    cx = sum(p.x for p in points) / n
    cy = sum(p.y for p in points) / n
    
    return Point2D(cx, cy)


def polygon_perimeter(points: List[Point2D], is_closed: bool = True) -> float:
    """
    计算多边形周长
    
    Args:
        points: 多边形顶点
        is_closed: 是否闭合
        
    Returns:
        周长
    """
    if len(points) < 2:
        return 0
    
    perimeter = 0
    for i in range(len(points) - 1):
        perimeter += point_distance(points[i], points[i + 1])
    
    if is_closed and len(points) > 2:
        perimeter += point_distance(points[-1], points[0])
    
    return perimeter


def convex_hull(points: List[Point2D]) -> List[Point2D]:
    """
    计算点集的凸包（Graham扫描算法）
    
    Args:
        points: 点列表
        
    Returns:
        凸包顶点列表
    """
    if len(points) < 3:
        return points
    
    # 找到最下方的点
    start = min(points, key=lambda p: (p.y, p.x))
    
    # 按极角排序
    def polar_angle(p):
        return np.arctan2(p.y - start.y, p.x - start.x)
    
    sorted_points = sorted([p for p in points if p != start], key=polar_angle)
    
    # Graham扫描
    hull = [start]
    for p in sorted_points:
        while len(hull) > 1:
            # 计算叉积
            v1 = np.array([hull[-1].x - hull[-2].x, hull[-1].y - hull[-2].y])
            v2 = np.array([p.x - hull[-1].x, p.y - hull[-1].y])
            cross = v1[0] * v2[1] - v1[1] * v2[0]
            
            if cross <= 0:
                hull.pop()
            else:
                break
        hull.append(p)
    
    return hull


def douglas_peucker(points: List[Point2D], epsilon: float) -> List[Point2D]:
    """
    Douglas-Peucker算法简化多边形
    
    Args:
        points: 点列表
        epsilon: 简化阈值
        
    Returns:
        简化后的点列表
    """
    if len(points) <= 2:
        return points
    
    # 找到距离最远的点
    line = LineSegment(points[0], points[-1])
    max_dist = 0
    max_index = 0
    
    for i in range(1, len(points) - 1):
        dist = point_to_line_distance(points[i], line)
        if dist > max_dist:
            max_dist = dist
            max_index = i
    
    if max_dist > epsilon:
        # 递归简化
        left = douglas_peucker(points[:max_index + 1], epsilon)
        right = douglas_peucker(points[max_index:], epsilon)
        
        return left[:-1] + right
    else:
        return [points[0], points[-1]]


# =============================================================================
# 变换相关计算
# =============================================================================

def rotate_point(point: Point2D, center: Point2D, angle: float) -> Point2D:
    """
    绕中心点旋转点
    
    Args:
        point: 要旋转的点
        center: 旋转中心
        angle: 旋转角度（弧度）
        
    Returns:
        旋转后的点
    """
    cos_a = np.cos(angle)
    sin_a = np.sin(angle)
    
    dx = point.x - center.x
    dy = point.y - center.y
    
    new_x = center.x + dx * cos_a - dy * sin_a
    new_y = center.y + dx * sin_a + dy * cos_a
    
    return Point2D(new_x, new_y)


def scale_point(point: Point2D, center: Point2D, scale: float) -> Point2D:
    """
    以中心点为基准缩放点
    
    Args:
        point: 要缩放的点
        center: 缩放中心
        scale: 缩放比例
        
    Returns:
        缩放后的点
    """
    dx = point.x - center.x
    dy = point.y - center.y
    
    return Point2D(
        center.x + dx * scale,
        center.y + dy * scale
    )


def translate_point(point: Point2D, dx: float, dy: float) -> Point2D:
    """平移点"""
    return Point2D(point.x + dx, point.y + dy)


# =============================================================================
# 其他工具函数
# =============================================================================

def angle_between_vectors(v1: Tuple[float, float], 
                          v2: Tuple[float, float]) -> float:
    """
    计算两个向量之间的夹角
    
    Args:
        v1: 第一个向量 (x, y)
        v2: 第二个向量 (x, y)
        
    Returns:
        夹角（弧度）
    """
    dot = v1[0] * v2[0] + v1[1] * v2[1]
    mag1 = np.sqrt(v1[0]**2 + v1[1]**2)
    mag2 = np.sqrt(v2[0]**2 + v2[1]**2)
    
    if mag1 == 0 or mag2 == 0:
        return 0
    
    cos_angle = dot / (mag1 * mag2)
    cos_angle = np.clip(cos_angle, -1.0, 1.0)
    
    return np.arccos(cos_angle)


def normalize_angle(angle: float) -> float:
    """将角度规范化到 [0, 2π)"""
    while angle < 0:
        angle += 2 * np.pi
    while angle >= 2 * np.pi:
        angle -= 2 * np.pi
    return angle


def is_rectangle(points: List[Point2D], 
                 angle_tolerance: float = np.radians(10)) -> bool:
    """
    判断点序列是否构成矩形
    
    Args:
        points: 点列表（4个顶点）
        angle_tolerance: 角度容差
        
    Returns:
        是否为矩形
    """
    if len(points) != 4:
        return False
    
    # 检查角度
    for i in range(4):
        p1 = points[i]
        p2 = points[(i + 1) % 4]
        p3 = points[(i + 2) % 4]
        
        v1 = (p1.x - p2.x, p1.y - p2.y)
        v2 = (p3.x - p2.x, p3.y - p2.y)
        
        angle = angle_between_vectors(v1, v2)
        
        if abs(angle - np.pi / 2) > angle_tolerance:
            return False
    
    return True


def bounding_box(points: List[Point2D]) -> Tuple[float, float, float, float]:
    """
    计算点集的边界框
    
    Args:
        points: 点列表
        
    Returns:
        (x_min, y_min, x_max, y_max)
    """
    if not points:
        return (0, 0, 0, 0)
    
    xs = [p.x for p in points]
    ys = [p.y for p in points]
    
    return (min(xs), min(ys), max(xs), max(ys))


# 模块测试
if __name__ == "__main__":
    import sys
    sys.path.append('/mnt/okcomputer/output/image_analysis_module')
    
    print("Testing Geometry Utils\n")
    
    # 测试点距离
    p1 = Point2D(0, 0)
    p2 = Point2D(3, 4)
    print(f"Distance between {p1} and {p2}: {point_distance(p1, p2)}")
    
    # 测试圆拟合
    circle_points = []
    for i in range(50):
        angle = 2 * np.pi * i / 50
        x = 100 + 50 * np.cos(angle) + np.random.normal(0, 1)
        y = 100 + 50 * np.sin(angle) + np.random.normal(0, 1)
        circle_points.append(Point2D(x, y))
    
    circle, error = fit_circle_least_squares(circle_points)
    print(f"\nFitted circle:")
    print(f"  Center: ({circle.center.x:.2f}, {circle.center.y:.2f})")
    print(f"  Radius: {circle.radius:.2f}")
    print(f"  Fit error: {error:.2f}")
    
    # 测试多边形面积
    rect_points = [
        Point2D(0, 0),
        Point2D(100, 0),
        Point2D(100, 50),
        Point2D(0, 50)
    ]
    area = polygon_area(rect_points)
    print(f"\nRectangle area: {area}")
    
    # 测试直线拟合
    line_points = [Point2D(i, 2*i + 3 + np.random.normal(0, 0.5)) for i in range(20)]
    point_on_line, direction, fit_error = fit_line_least_squares(line_points)
    print(f"\nFitted line:")
    print(f"  Point on line: {point_on_line}")
    print(f"  Direction: ({direction.x:.3f}, {direction.y:.3f})")
    print(f"  Fit error: {fit_error:.3f}")
    
    # 测试Douglas-Peucker
    dp_points = [
        Point2D(0, 0),
        Point2D(1, 0.1),
        Point2D(2, -0.1),
        Point2D(3, 0),
        Point2D(4, 0.05),
        Point2D(5, 0)
    ]
    simplified = douglas_peucker(dp_points, 0.5)
    print(f"\nDouglas-Peucker simplification:")
    print(f"  Original points: {len(dp_points)}")
    print(f"  Simplified points: {len(simplified)}")
    
    print("\nAll tests passed!")
