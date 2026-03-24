"""
铸造行业2D到3D转换 - 图像分析模块工具包

本包包含各种工具函数和配置管理。
"""

from .config_loader import (
    ConfigLoader,
    PreprocessingConfig,
    EdgeDetectionConfig,
    ContourConfig,
    FeatureExtractionConfig,
    DimensionExtractionConfig,
    DebugConfig,
    LoggingConfig,
    PerformanceConfig,
    OutputConfig,
    AnalyzerConfig,
    dict_to_config,
    config_to_dict,
    load_config,
    save_config
)

from .geometry_utils import (
    # 点相关
    point_distance,
    point_to_line_distance,
    point_in_polygon,
    closest_point_on_line,
    
    # 直线相关
    line_intersection,
    line_angle,
    lines_parallel,
    lines_perpendicular,
    fit_line_least_squares,
    
    # 圆相关
    fit_circle_least_squares,
    fit_circle_algebraic,
    circle_from_three_points,
    circle_circularity,
    
    # 圆弧相关
    arc_from_points,
    arc_length,
    arc_midpoint,
    
    # 多边形相关
    polygon_area,
    polygon_centroid,
    polygon_perimeter,
    convex_hull,
    douglas_peucker,
    
    # 变换相关
    rotate_point,
    scale_point,
    translate_point,
    
    # 其他
    angle_between_vectors,
    normalize_angle,
    is_rectangle,
    bounding_box
)

__all__ = [
    # 配置加载
    'ConfigLoader',
    'PreprocessingConfig',
    'EdgeDetectionConfig',
    'ContourConfig',
    'FeatureExtractionConfig',
    'DimensionExtractionConfig',
    'DebugConfig',
    'LoggingConfig',
    'PerformanceConfig',
    'OutputConfig',
    'AnalyzerConfig',
    'dict_to_config',
    'config_to_dict',
    'load_config',
    'save_config',
    
    # 几何工具
    'point_distance',
    'point_to_line_distance',
    'point_in_polygon',
    'closest_point_on_line',
    'line_intersection',
    'line_angle',
    'lines_parallel',
    'lines_perpendicular',
    'fit_line_least_squares',
    'fit_circle_least_squares',
    'fit_circle_algebraic',
    'circle_from_three_points',
    'circle_circularity',
    'arc_from_points',
    'arc_length',
    'arc_midpoint',
    'polygon_area',
    'polygon_centroid',
    'polygon_perimeter',
    'convex_hull',
    'douglas_peucker',
    'rotate_point',
    'scale_point',
    'translate_point',
    'angle_between_vectors',
    'normalize_angle',
    'is_rectangle',
    'bounding_box'
]
