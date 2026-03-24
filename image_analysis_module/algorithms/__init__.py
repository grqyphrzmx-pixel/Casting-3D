"""
铸造行业2D到3D转换 - 图像分析模块算法包

本包包含各种图像处理和分析算法。
"""

from .shape_recognition import (
    # 识别结果
    RecognitionResult,
    
    # 识别器基类
    ShapeRecognizer,
    
    # 具体识别器
    LineRecognizer,
    CircleRecognizer,
    ArcRecognizer,
    EllipseRecognizer,
    PolygonRecognizer,
    
    # 特征提取器
    FeatureExtractor,
    
    # 便捷函数
    recognize_shape
)

__all__ = [
    'RecognitionResult',
    'ShapeRecognizer',
    'LineRecognizer',
    'CircleRecognizer',
    'ArcRecognizer',
    'EllipseRecognizer',
    'PolygonRecognizer',
    'FeatureExtractor',
    'recognize_shape'
]
