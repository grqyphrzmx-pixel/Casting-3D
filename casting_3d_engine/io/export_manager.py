"""
导出管理器模块

管理模型导出到各种格式
"""

import logging
from enum import Enum, auto
from typing import Dict, List, Callable, Optional, Any
from pathlib import Path

from ..core.geometry_kernel import GeometryKernel

logger = logging.getLogger(__name__)


class ExportFormat(Enum):
    """导出格式枚举"""
    STL = "stl"
    STEP = "step"
    IGES = "iges"
    BREP = "brep"
    OBJ = "obj"
    PLY = "ply"
    VRML = "vrml"


class ExportOptions:
    """导出选项"""
    
    def __init__(self):
        # 网格生成参数
        self.linear_deflection: float = 0.5
        self.angular_deflection: float = 0.5
        self.relative_mode: bool = False
        
        # 导出选项
        self.export_colors: bool = False
        self.export_normals: bool = True
        self.export_uvs: bool = False
        
        # 文件选项
        self.compress: bool = False
        self.binary: bool = True  # 二进制格式（STL等）
        
        # 元数据
        self.author: str = ""
        self.description: str = ""
        self.organization: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'linear_deflection': self.linear_deflection,
            'angular_deflection': self.angular_deflection,
            'relative_mode': self.relative_mode,
            'export_colors': self.export_colors,
            'export_normals': self.export_normals,
            'export_uvs': self.export_uvs,
            'compress': self.compress,
            'binary': self.binary
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExportOptions':
        """从字典创建"""
        options = cls()
        options.linear_deflection = data.get('linear_deflection', 0.5)
        options.angular_deflection = data.get('angular_deflection', 0.5)
        options.relative_mode = data.get('relative_mode', False)
        options.export_colors = data.get('export_colors', False)
        options.export_normals = data.get('export_normals', True)
        options.export_uvs = data.get('export_uvs', False)
        options.compress = data.get('compress', False)
        options.binary = data.get('binary', True)
        return options


class ExportManager:
    """
    导出管理器
    管理模型导出到各种格式
    """
    
    def __init__(self, kernel: GeometryKernel):
        self._kernel = kernel
        self._exporters: Dict[ExportFormat, Callable] = {
            ExportFormat.STL: self._export_stl,
            ExportFormat.STEP: self._export_step,
            ExportFormat.IGES: self._export_iges,
            ExportFormat.BREP: self._export_brep
        }
        self._default_options = ExportOptions()
    
    def export(self, shape_id: str, filepath: str, 
               format: ExportFormat = None,
               options: ExportOptions = None) -> bool:
        """
        导出模型
        
        Args:
            shape_id: 要导出的形状ID
            filepath: 输出文件路径
            format: 导出格式（如果为None，从文件扩展名推断）
            options: 导出选项
        
        Returns:
            导出是否成功
        """
        if options is None:
            options = self._default_options
        
        # 从文件扩展名推断格式
        if format is None:
            format = self._infer_format_from_extension(filepath)
        
        if format is None:
            logger.error(f"Cannot infer format from filepath: {filepath}")
            return False
        
        exporter = self._exporters.get(format)
        if exporter is None:
            logger.error(f"Unsupported export format: {format}")
            return False
        
        # 确保输出目录存在
        output_path = Path(filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        return exporter(shape_id, filepath, options)
    
    def _infer_format_from_extension(self, filepath: str) -> Optional[ExportFormat]:
        """从文件扩展名推断格式"""
        ext = Path(filepath).suffix.lower()
        
        format_map = {
            '.stl': ExportFormat.STL,
            '.step': ExportFormat.STEP,
            '.stp': ExportFormat.STEP,
            '.iges': ExportFormat.IGES,
            '.igs': ExportFormat.IGES,
            '.brep': ExportFormat.BREP,
            '.obj': ExportFormat.OBJ,
            '.ply': ExportFormat.PLY,
            '.wrl': ExportFormat.VRML,
            '.vrml': ExportFormat.VRML
        }
        
        return format_map.get(ext)
    
    def _export_stl(self, shape_id: str, filepath: str,
                    options: ExportOptions) -> bool:
        """导出为STL"""
        try:
            result = self._kernel.export_stl(
                shape_id, filepath,
                options.linear_deflection,
                options.angular_deflection)
            
            if result:
                logger.info(f"Exported STL: {filepath}")
            return result
            
        except Exception as e:
            logger.error(f"STL export failed: {e}")
            return False
    
    def _export_step(self, shape_id: str, filepath: str,
                     options: ExportOptions) -> bool:
        """导出为STEP"""
        try:
            result = self._kernel.export_step(shape_id, filepath)
            
            if result:
                logger.info(f"Exported STEP: {filepath}")
            return result
            
        except Exception as e:
            logger.error(f"STEP export failed: {e}")
            return False
    
    def _export_iges(self, shape_id: str, filepath: str,
                     options: ExportOptions) -> bool:
        """导出为IGES"""
        try:
            result = self._kernel.export_iges(shape_id, filepath)
            
            if result:
                logger.info(f"Exported IGES: {filepath}")
            return result
            
        except Exception as e:
            logger.error(f"IGES export failed: {e}")
            return False
    
    def _export_brep(self, shape_id: str, filepath: str,
                     options: ExportOptions) -> bool:
        """导出为BREP (OpenCASCADE原生格式)"""
        try:
            from OCC.Core.BRepTools import breptools_Write
            
            shape = self._kernel.get_shape(shape_id)
            if shape is None:
                logger.error(f"Shape not found: {shape_id}")
                return False
            
            success = breptools_Write(shape, filepath)
            
            if success:
                logger.info(f"Exported BREP: {filepath}")
            return success
            
        except Exception as e:
            logger.error(f"BREP export failed: {e}")
            return False
    
    def register_exporter(self, format: ExportFormat, 
                          exporter: Callable[[str, str, ExportOptions], bool]):
        """
        注册自定义导出器
        
        Args:
            format: 导出格式
            exporter: 导出函数 (shape_id, filepath, options) -> bool
        """
        self._exporters[format] = exporter
        logger.info(f"Registered exporter for format: {format.value}")
    
    def unregister_exporter(self, format: ExportFormat):
        """注销导出器"""
        if format in self._exporters:
            del self._exporters[format]
            logger.info(f"Unregistered exporter for format: {format.value}")
    
    def get_supported_formats(self) -> List[ExportFormat]:
        """获取支持的导出格式"""
        return list(self._exporters.keys())
    
    def get_supported_extensions(self) -> List[str]:
        """获取支持的文件扩展名"""
        extension_map = {
            ExportFormat.STL: ['.stl'],
            ExportFormat.STEP: ['.step', '.stp'],
            ExportFormat.IGES: ['.iges', '.igs'],
            ExportFormat.BREP: ['.brep'],
            ExportFormat.OBJ: ['.obj'],
            ExportFormat.PLY: ['.ply'],
            ExportFormat.VRML: ['.wrl', '.vrml']
        }
        
        extensions = []
        for fmt in self.get_supported_formats():
            extensions.extend(extension_map.get(fmt, []))
        return extensions
    
    def set_default_options(self, options: ExportOptions):
        """设置默认导出选项"""
        self._default_options = options
    
    def get_default_options(self) -> ExportOptions:
        """获取默认导出选项"""
        return self._default_options
    
    def batch_export(self, shape_id: str, 
                     exports: List[Dict[str, Any]]) -> Dict[str, bool]:
        """
        批量导出
        
        Args:
            shape_id: 形状ID
            exports: 导出配置列表
                [
                    {'filepath': 'model.stl', 'format': ExportFormat.STL},
                    {'filepath': 'model.step', 'format': ExportFormat.STEP},
                    ...
                ]
        
        Returns:
            导出结果字典 {filepath: success}
        """
        results = {}
        
        for export_config in exports:
            filepath = export_config['filepath']
            format = export_config.get('format')
            options = export_config.get('options')
            
            results[filepath] = self.export(shape_id, filepath, format, options)
        
        return results


class CastingExportPreset:
    """
    铸造行业导出预设
    提供针对铸造仿真的优化导出设置
    """
    
    @staticmethod
    def get_stl_preset() -> ExportOptions:
        """获取STL导出预设（适合铸造仿真）"""
        options = ExportOptions()
        options.linear_deflection = 0.1  # 高精度
        options.angular_deflection = 0.1
        options.export_normals = True
        options.binary = True
        return options
    
    @staticmethod
    def get_step_preset() -> ExportOptions:
        """获取STEP导出预设（适合CAD交换）"""
        options = ExportOptions()
        # STEP不需要网格参数
        return options
    
    @staticmethod
    def get_iges_preset() -> ExportOptions:
        """获取IGES导出预设（适合遗留系统）"""
        options = ExportOptions()
        # IGES不需要网格参数
        return options
    
    @staticmethod
    def get_3d_printing_preset() -> ExportOptions:
        """获取3D打印导出预设"""
        options = ExportOptions()
        options.linear_deflection = 0.05  # 超高精度
        options.angular_deflection = 0.05
        options.export_normals = True
        options.binary = True
        return options
