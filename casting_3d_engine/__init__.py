"""
铸造行业3D建模引擎

基于OpenCASCADE Technology的3D建模引擎，
专门用于铸造零件的2D到3D转换。

作者: 3D图形引擎架构师
版本: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "3D Graphics Engine Architect"

# 导出主要类和接口
from .core.types import (
    FeatureType, GeometryType,
    Point3D, Vector3D, Plane, Profile2D,
    FeatureParameters, ExtrudeParameters, RevolveParameters,
    HoleParameters, FilletParameters, DraftParameters, BooleanParameters
)

from .core.geometry_kernel import GeometryKernel, OCCConverter
from .core.feature_base import Feature, FeatureFactory
from .core.features import (
    ExtrudeFeature, RevolveFeature, HoleFeature,
    BooleanFeature, DraftFeature
)
from .core.command_system import Command, CommandManager
from .core.feature_manager import FeatureManager
from .core.model_builder import ModelBuilder
from .core.casting_3d_engine import Casting3DEngine

from .io.export_manager import ExportManager, ExportFormat, ExportOptions
from .io.input_interface import ModelBuilderInput

__all__ = [
    # 类型定义
    'FeatureType', 'GeometryType',
    'Point3D', 'Vector3D', 'Plane', 'Profile2D',
    'FeatureParameters', 'ExtrudeParameters', 'RevolveParameters',
    'HoleParameters', 'FilletParameters', 'DraftParameters', 'BooleanParameters',
    
    # 核心类
    'GeometryKernel', 'OCCConverter',
    'Feature', 'FeatureFactory',
    'ExtrudeFeature', 'RevolveFeature', 'HoleFeature',
    'BooleanFeature', 'DraftFeature',
    'Command', 'CommandManager',
    'FeatureManager', 'ModelBuilder',
    'Casting3DEngine',
    
    # IO类
    'ExportManager', 'ExportFormat', 'ExportOptions',
    'ModelBuilderInput',
]
