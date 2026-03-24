"""
模块适配器

提供各个模块之间的接口适配和数据转换。
负责将图像分析模块、3D建模引擎、CAD导出模块和铸造规则引擎整合在一起。
"""

import logging
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import numpy as np

from .event_bus import EventBus
from .workflow_manager import WorkflowContext

logger = logging.getLogger(__name__)


class ImageAnalysisAdapter:
    """
    图像分析模块适配器
    
    封装图像分析模块，提供统一的接口。
    """
    
    def __init__(self):
        self._analyzer = None
        self._init_analyzer()
    
    def _init_analyzer(self):
        """初始化分析器"""
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'image_analysis_module'))
            from image_analysis_module.core.image_analyzer import ImageAnalyzer, AnalyzerConfig
            from image_analysis_module.core.data_structures import SourceType
            
            self._analyzer = ImageAnalyzer(AnalyzerConfig())
            self._source_type = SourceType
            logger.info("ImageAnalyzer initialized")
        except ImportError as e:
            logger.warning(f"ImageAnalyzer not available: {e}")
    
    def is_available(self) -> bool:
        """检查分析器是否可用"""
        return self._analyzer is not None
    
    def analyze_image(self, image_path: str, 
                      source_type: str = "unknown") -> Optional[Any]:
        """
        分析图像
        
        Args:
            image_path: 图像文件路径
            source_type: 图像源类型
            
        Returns:
            分析结果
        """
        if not self._analyzer:
            logger.error("ImageAnalyzer not available")
            return None
        
        try:
            # 转换源类型
            src_type = self._source_type.UNKNOWN
            if source_type.lower() in ["technical_drawing", "drawing"]:
                src_type = self._source_type.TECHNICAL_DRAWING
            elif source_type.lower() in ["photo", "image"]:
                src_type = self._source_type.PHOTO
            
            # 执行分析
            result = self._analyzer.analyze_file(image_path, src_type)
            
            logger.info(f"Image analysis completed: {image_path}")
            return result
            
        except Exception as e:
            logger.error(f"Image analysis failed: {e}")
            return None
    
    def get_features(self, analysis_result: Any) -> List[Any]:
        """从分析结果中提取特征"""
        if analysis_result and hasattr(analysis_result, 'features'):
            return analysis_result.features
        return []
    
    def get_contours(self, analysis_result: Any) -> List[Any]:
        """从分析结果中提取轮廓"""
        if analysis_result and hasattr(analysis_result, 'contours'):
            return analysis_result.contours
        return []
    
    def get_dimensions(self, analysis_result: Any) -> List[Any]:
        """从分析结果中提取尺寸"""
        if analysis_result and hasattr(analysis_result, 'dimensions'):
            return analysis_result.dimensions
        return []


class ModelingEngineAdapter:
    """
    3D建模引擎适配器
    
    封装3D建模引擎，提供统一的接口。
    """
    
    def __init__(self):
        self._engine = None
        self._init_engine()
    
    def _init_engine(self):
        """初始化引擎"""
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'casting_3d_engine'))
            from casting_3d_engine.core.casting_3d_engine import Casting3DEngine
            
            self._engine = Casting3DEngine()
            logger.info("Casting3DEngine initialized")
        except ImportError as e:
            logger.warning(f"Casting3DEngine not available: {e}")
    
    def is_available(self) -> bool:
        """检查引擎是否可用"""
        return self._engine is not None
    
    def create_extrusion(self, profile: List[Any], depth: float,
                        direction: Any = None, 
                        taper_angle: float = 0.0) -> Optional[str]:
        """
        创建拉伸特征
        
        Args:
            profile: 2D轮廓
            depth: 拉伸深度
            direction: 拉伸方向
            taper_angle: 拔模角度
            
        Returns:
            特征ID
        """
        if not self._engine:
            logger.error("Casting3DEngine not available")
            return None
        
        try:
            return self._engine.create_extrude(profile, depth, direction, taper_angle)
        except Exception as e:
            logger.error(f"Failed to create extrusion: {e}")
            return None
    
    def create_revolution(self, profile: List[Any], 
                         angle: float = 360.0) -> Optional[str]:
        """创建旋转特征"""
        if not self._engine:
            return None
        
        try:
            return self._engine.create_revolve(profile, angle)
        except Exception as e:
            logger.error(f"Failed to create revolution: {e}")
            return None
    
    def create_hole(self, center: Any, diameter: float,
                   depth: float = 0.0) -> Optional[str]:
        """创建孔特征"""
        if not self._engine:
            return None
        
        try:
            return self._engine.create_hole(center, diameter, depth)
        except Exception as e:
            logger.error(f"Failed to create hole: {e}")
            return None
    
    def create_fillet(self, edge_ids: List[str], 
                     radius: float) -> Optional[str]:
        """创建圆角特征"""
        if not self._engine:
            return None
        
        try:
            return self._engine.create_fillet(edge_ids, radius)
        except Exception as e:
            logger.error(f"Failed to create fillet: {e}")
            return None
    
    def create_draft(self, face_ids: List[str], 
                    angle: float) -> Optional[str]:
        """创建拔模特征"""
        if not self._engine:
            return None
        
        try:
            return self._engine.create_draft(face_ids, angle)
        except Exception as e:
            logger.error(f"Failed to create draft: {e}")
            return None
    
    def export_stl(self, shape_id: str, filepath: str) -> bool:
        """导出为STL格式"""
        if not self._engine:
            return False
        
        try:
            return self._engine.export_stl(shape_id, filepath)
        except Exception as e:
            logger.error(f"Failed to export STL: {e}")
            return False
    
    def export_step(self, shape_id: str, filepath: str) -> bool:
        """导出为STEP格式"""
        if not self._engine:
            return False
        
        try:
            return self._engine.export_step(shape_id, filepath)
        except Exception as e:
            logger.error(f"Failed to export STEP: {e}")
            return False
    
    def export_iges(self, shape_id: str, filepath: str) -> bool:
        """导出为IGES格式"""
        if not self._engine:
            return False
        
        try:
            return self._engine.export_iges(shape_id, filepath)
        except Exception as e:
            logger.error(f"Failed to export IGES: {e}")
            return False
    
    def undo(self) -> bool:
        """撤销操作"""
        if not self._engine:
            return False
        return self._engine.undo()
    
    def redo(self) -> bool:
        """重做操作"""
        if not self._engine:
            return False
        return self._engine.redo()


class CADExportAdapter:
    """
    CAD导出模块适配器
    
    封装CAD导出模块，提供统一的接口。
    """
    
    def __init__(self):
        self._manager = None
        self._init_manager()
    
    def _init_manager(self):
        """初始化导出管理器"""
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent.parent))
            from cad_export_manager import CADExportManager
            
            self._manager = CADExportManager()
            logger.info("CADExportManager initialized")
        except ImportError as e:
            logger.warning(f"CADExportManager not available: {e}")
    
    def is_available(self) -> bool:
        """检查导出管理器是否可用"""
        return self._manager is not None
    
    def export_mesh(self, mesh: Any, filepath: str, 
                   format_type: str = None) -> bool:
        """
        导出网格
        
        Args:
            mesh: 网格数据
            filepath: 输出文件路径
            format_type: 导出格式
            
        Returns:
            是否导出成功
        """
        if not self._manager:
            logger.error("CADExportManager not available")
            return False
        
        try:
            from cad_exporter_base import ExportFormat
            
            # 转换格式
            fmt = None
            if format_type:
                fmt_map = {
                    'stl_ascii': ExportFormat.STL_ASCII,
                    'stl_binary': ExportFormat.STL_BINARY,
                    'step_ap203': ExportFormat.STEP_AP203,
                    'step_ap214': ExportFormat.STEP_AP214,
                    'iges': ExportFormat.IGES_5_3
                }
                fmt = fmt_map.get(format_type.lower())
            
            return self._manager.export_mesh(mesh, filepath, fmt)
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False
    
    def get_supported_formats(self) -> List[str]:
        """获取支持的格式列表"""
        if not self._manager:
            return []
        return self._manager.get_supported_formats()


class CastingRulesAdapter:
    """
    铸造规则引擎适配器
    
    封装铸造规则引擎，提供统一的接口。
    """
    
    def __init__(self):
        self._engine = None
        self._init_engine()
    
    def _init_engine(self):
        """初始化规则引擎"""
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent.parent))
            from casting_rules_engine import QualityCheckEngine
            
            self._engine = QualityCheckEngine()
            logger.info("QualityCheckEngine initialized")
        except ImportError as e:
            logger.warning(f"QualityCheckEngine not available: {e}")
    
    def is_available(self) -> bool:
        """检查规则引擎是否可用"""
        return self._engine is not None
    
    def run_quality_check(self, part: Any) -> Optional[Any]:
        """
        运行质量检查
        
        Args:
            part: 零件数据
            
        Returns:
            质量报告
        """
        if not self._engine:
            logger.error("QualityCheckEngine not available")
            return None
        
        try:
            return self._engine.run_all_checks(part)
        except Exception as e:
            logger.error(f"Quality check failed: {e}")
            return None
    
    def check_draft_angle(self, angle: float, process: str,
                         surface_type: str, height: float) -> Dict[str, Any]:
        """检查拔模角度"""
        if not self._engine:
            return {'status': 'UNKNOWN', 'issues': ['Engine not available']}
        
        try:
            result = self._engine.draft_engine.check_draft_angle(
                angle, process, surface_type, height
            )
            return result
        except Exception as e:
            logger.error(f"Draft angle check failed: {e}")
            return {'status': 'ERROR', 'issues': [str(e)]}
    
    def check_fillet_radius(self, radius: float, 
                           wall_thickness: float) -> Dict[str, Any]:
        """检查圆角半径"""
        if not self._engine:
            return {'status': 'UNKNOWN', 'issues': ['Engine not available']}
        
        try:
            result = self._engine.fillet_engine.check_fillet_radius(
                radius, wall_thickness
            )
            return result
        except Exception as e:
            logger.error(f"Fillet check failed: {e}")
            return {'status': 'ERROR', 'issues': [str(e)]}
    
    def check_wall_thickness(self, thickness: float, 
                            material: str, process: str) -> Dict[str, Any]:
        """检查壁厚"""
        if not self._engine:
            return {'status': 'UNKNOWN', 'issues': ['Engine not available']}
        
        try:
            result = self._engine.wall_engine.check_wall_thickness(
                thickness, material, process
            )
            return result
        except Exception as e:
            logger.error(f"Wall thickness check failed: {e}")
            return {'status': 'ERROR', 'issues': [str(e)]}


class ModuleAdapterManager:
    """
    模块适配器管理器
    
    统一管理所有模块适配器。
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._image_adapter = ImageAnalysisAdapter()
        self._modeling_adapter = ModelingEngineAdapter()
        self._export_adapter = CADExportAdapter()
        self._rules_adapter = CastingRulesAdapter()
        
        self._initialized = True
        logger.info("ModuleAdapterManager initialized")
    
    @property
    def image_analysis(self) -> ImageAnalysisAdapter:
        return self._image_adapter
    
    @property
    def modeling_engine(self) -> ModelingEngineAdapter:
        return self._modeling_adapter
    
    @property
    def cad_export(self) -> CADExportAdapter:
        return self._export_adapter
    
    @property
    def casting_rules(self) -> CastingRulesAdapter:
        return self._rules_adapter
    
    def get_availability(self) -> Dict[str, bool]:
        """获取模块可用性状态"""
        return {
            'image_analysis': self._image_adapter.is_available(),
            'modeling_engine': self._modeling_adapter.is_available(),
            'cad_export': self._export_adapter.is_available(),
            'casting_rules': self._rules_adapter.is_available()
        }
    
    def check_all_available(self) -> bool:
        """检查所有模块是否都可用"""
        return all(self.get_availability().values())


# 便捷函数
def get_module_adapter() -> ModuleAdapterManager:
    """获取模块适配器管理器实例"""
    return ModuleAdapterManager()


if __name__ == "__main__":
    # 测试代码
    print("ModuleAdapter Test")
    print("=" * 50)
    
    adapter = get_module_adapter()
    
    # 检查模块可用性
    availability = adapter.get_availability()
    print("Module availability:")
    for name, available in availability.items():
        print(f"  {name}: {'Available' if available else 'Not Available'}")
    
    print("\nTest completed!")
