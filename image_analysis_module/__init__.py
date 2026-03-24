"""
铸造行业2D到3D转换 - 图像分析模块

本模块提供从铸造零件的2D图纸或照片中提取几何特征的功能，
为3D重建提供结构化的数据基础。

主要功能:
    - 图像预处理（去噪、增强、二值化）
    - 边缘检测和轮廓提取
    - 形状识别（直线、圆、圆弧、椭圆、多边形）
    - 尺寸标注提取
    - 与3D建模引擎的数据交换

使用示例:
    >>> from image_analysis_module import ImageAnalyzer, SourceType
    >>> analyzer = ImageAnalyzer()
    >>> result = analyzer.analyze_file("drawing.png", SourceType.TECHNICAL_DRAWING)
    >>> print(f"Found {result.num_features} features")
    >>> print(result.to_json())

版本: 1.0.0
"""

# 核心模块
from .core import (
    # 枚举类型
    SourceType,
    FeatureType,
    ShapeType,
    DimensionType,
    ConstraintType,
    
    # 基础几何类型
    Point2D,
    Vector2D,
    BoundingBox,
    LineSegment,
    Circle,
    Arc,
    Ellipse,
    Polygon,
    
    # 轮廓和特征
    Contour,
    GeometricFeature,
    FeatureMetadata,
    Dimension,
    Constraint,
    
    # 分析结果
    ImageInfo,
    AnalysisMetadata,
    AnalysisResult,
    
    # 配置类
    AnalyzerConfig,
    PreprocessingConfig,
    EdgeDetectionConfig,
    ContourConfig,
    FeatureExtractionConfig,
    DimensionExtractionConfig,
    
    # 核心类
    ImageAnalyzer,
    ImagePreprocessor,
    EdgeDetector,
    ContourAnalyzer,
    AnalysisLogger,
    
    # 便捷函数
    analyze_image
)

# 算法模块
from .algorithms import (
    RecognitionResult,
    ShapeRecognizer,
    LineRecognizer,
    CircleRecognizer,
    ArcRecognizer,
    EllipseRecognizer,
    PolygonRecognizer,
    FeatureExtractor,
    recognize_shape
)

# 接口模块
from .interfaces import (
    Feature3DType,
    Point3D,
    Vector3D,
    ExtrusionFeature,
    RevolutionFeature,
    Primitive3D,
    Model3D,
    FeatureCollection,
    Model3DInterface,
    Model3DEngineInterface,
    export_result,
    convert_to_3d_model
)

# 工具模块
from .utils import (
    ConfigLoader,
    load_config,
    save_config,
    dict_to_config,
    config_to_dict
)

__version__ = "1.0.0"
__author__ = "Casting Industry 2D-3D Conversion Team"

__all__ = [
    # 版本信息
    '__version__',
    '__author__',
    
    # 枚举类型
    'SourceType',
    'FeatureType',
    'ShapeType',
    'DimensionType',
    'ConstraintType',
    
    # 基础几何类型
    'Point2D',
    'Vector2D',
    'BoundingBox',
    'LineSegment',
    'Circle',
    'Arc',
    'Ellipse',
    'Polygon',
    
    # 轮廓和特征
    'Contour',
    'GeometricFeature',
    'FeatureMetadata',
    'Dimension',
    'Constraint',
    
    # 分析结果
    'ImageInfo',
    'AnalysisMetadata',
    'AnalysisResult',
    
    # 配置类
    'AnalyzerConfig',
    'PreprocessingConfig',
    'EdgeDetectionConfig',
    'ContourConfig',
    'FeatureExtractionConfig',
    'DimensionExtractionConfig',
    
    # 核心类
    'ImageAnalyzer',
    'ImagePreprocessor',
    'EdgeDetector',
    'ContourAnalyzer',
    'AnalysisLogger',
    
    # 算法类
    'RecognitionResult',
    'ShapeRecognizer',
    'LineRecognizer',
    'CircleRecognizer',
    'ArcRecognizer',
    'EllipseRecognizer',
    'PolygonRecognizer',
    'FeatureExtractor',
    
    # 3D接口
    'Feature3DType',
    'Point3D',
    'Vector3D',
    'ExtrusionFeature',
    'RevolutionFeature',
    'Primitive3D',
    'Model3D',
    'FeatureCollection',
    'Model3DInterface',
    'Model3DEngineInterface',
    
    # 配置工具
    'ConfigLoader',
    'load_config',
    'save_config',
    'dict_to_config',
    'config_to_dict',
    
    # 便捷函数
    'analyze_image',
    'recognize_shape',
    'export_result',
    'convert_to_3d_model'
]
