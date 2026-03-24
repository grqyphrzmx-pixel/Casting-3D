"""
铸造行业2D到3D转换 - 图像分析模块核心包

本包包含图像分析的核心功能，包括数据结构定义和主分析器。
"""

from .data_structures import (
    # 枚举类型
    SourceType,
    FeatureType,
    ShapeType,
    DimensionType,
    ConstraintType,
    ProcessingStatus,
    
    # 基础几何类型
    Point2D,
    Vector2D,
    BoundingBox,
    LineSegment,
    Circle,
    Arc,
    Ellipse,
    Polygon,
    GeometryType,
    
    # 轮廓和特征
    Contour,
    GeometricFeature,
    FeatureMetadata,
    
    # 尺寸和约束
    Dimension,
    Constraint,
    
    # 分析结果
    ImageInfo,
    AnalysisMetadata,
    AnalysisResult,
    
    # 辅助函数
    create_contour_from_numpy,
    merge_contours,
    calculate_bounding_box_of_features
)

from .image_analyzer import (
    # 配置类
    PreprocessingConfig,
    EdgeDetectionConfig,
    ContourConfig,
    FeatureExtractionConfig,
    DimensionExtractionConfig,
    AnalyzerConfig,
    
    # 核心类
    AnalysisLogger,
    ImagePreprocessor,
    EdgeDetector,
    ContourAnalyzer,
    ImageAnalyzer,
    
    # 便捷函数
    analyze_image
)

__version__ = "1.0.0"

__all__ = [
    # 枚举类型
    'SourceType',
    'FeatureType',
    'ShapeType',
    'DimensionType',
    'ConstraintType',
    'ProcessingStatus',
    
    # 基础几何类型
    'Point2D',
    'Vector2D',
    'BoundingBox',
    'LineSegment',
    'Circle',
    'Arc',
    'Ellipse',
    'Polygon',
    'GeometryType',
    
    # 轮廓和特征
    'Contour',
    'GeometricFeature',
    'FeatureMetadata',
    
    # 尺寸和约束
    'Dimension',
    'Constraint',
    
    # 分析结果
    'ImageInfo',
    'AnalysisMetadata',
    'AnalysisResult',
    
    # 配置类
    'PreprocessingConfig',
    'EdgeDetectionConfig',
    'ContourConfig',
    'FeatureExtractionConfig',
    'DimensionExtractionConfig',
    'AnalyzerConfig',
    
    # 核心类
    'AnalysisLogger',
    'ImagePreprocessor',
    'EdgeDetector',
    'ContourAnalyzer',
    'ImageAnalyzer',
    
    # 辅助函数
    'create_contour_from_numpy',
    'merge_contours',
    'calculate_bounding_box_of_features',
    'analyze_image'
]
