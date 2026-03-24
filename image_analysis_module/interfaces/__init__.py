"""
铸造行业2D到3D转换 - 图像分析模块接口包

本包定义了与3D建模引擎的数据交换接口。
"""

from .model3d_interface import (
    # 3D特征类型
    Feature3DType,
    
    # 3D数据结构
    Point3D,
    Vector3D,
    ExtrusionFeature,
    RevolutionFeature,
    Primitive3D,
    Feature3D,
    Model3D,
    FeatureCollection,
    
    # 接口类
    Model3DEngineInterface,
    Model3DInterface,
    FreeCADInterface,
    
    # 便捷函数
    export_result,
    convert_to_3d_model
)

__all__ = [
    'Feature3DType',
    'Point3D',
    'Vector3D',
    'ExtrusionFeature',
    'RevolutionFeature',
    'Primitive3D',
    'Feature3D',
    'Model3D',
    'FeatureCollection',
    'Model3DEngineInterface',
    'Model3DInterface',
    'FreeCADInterface',
    'export_result',
    'convert_to_3d_model'
]
