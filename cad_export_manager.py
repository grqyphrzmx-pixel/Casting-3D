"""
CAD导出管理器
CAD Export Manager

统一接口管理所有CAD格式导出器
"""

from pathlib import Path
from typing import Union, List, Dict, Optional, Callable, Any, Type
import json

from cad_exporter_base import (
    CADExporter, ExportOptions, ExportFormat, ExportMetadata,
    ExportProgress, MeshData, BRepSolid, UnitType,
    ExporterFactory, get_exporter_for_file
)
from stl_exporter import STLExporter, STLRepairTool
from step_exporter import STEPExporter, STEPUtils
from iges_exporter import IGESExporter, IGESUtils


# 注册所有导出器
ExporterFactory.register(ExportFormat.STL_ASCII, STLExporter)
ExporterFactory.register(ExportFormat.STL_BINARY, STLExporter)
ExporterFactory.register(ExportFormat.STEP_AP203, STEPExporter)
ExporterFactory.register(ExportFormat.STEP_AP214, STEPExporter)
ExporterFactory.register(ExportFormat.IGES_5_3, IGESExporter)


class CADExportManager:
    """
    CAD导出管理器
    
    提供统一的接口来管理所有CAD格式导出操作。
    支持格式自动检测、批量导出、配置管理等功能。
    """
    
    def __init__(self):
        self._exporters: Dict[ExportFormat, CADExporter] = {}
        self._progress_callback: Optional[Callable[[ExportProgress], None]] = None
        self._config: Dict[str, Any] = {}
        self._load_default_config()
    
    def _load_default_config(self):
        """加载默认配置"""
        self._config = {
            'default_format': 'stl_binary',
            'default_unit': 'millimeter',
            'default_precision': 0.001,
            'default_tolerance': 0.01,
            'stl_ascii': False,
            'step_schema': 'AP214',
            'iges_unit': 2,  # mm
            'write_colors': True,
            'auto_fix_mesh': True,
            'validate_before_export': True,
        }
    
    def set_progress_callback(self, callback: Callable[[ExportProgress], None]):
        """设置进度回调函数"""
        self._progress_callback = callback
    
    def load_config(self, config_path: Union[str, Path]):
        """从文件加载配置"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                self._config.update(loaded_config)
        except Exception as e:
            print(f"Warning: Failed to load config from {config_path}: {e}")
    
    def save_config(self, config_path: Union[str, Path]):
        """保存配置到文件"""
        try:
            Path(config_path).parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save config to {config_path}: {e}")
    
    def update_config(self, **kwargs):
        """更新配置"""
        self._config.update(kwargs)
    
    def get_config(self, key: str, default=None):
        """获取配置值"""
        return self._config.get(key, default)
    
    def _create_options(self, format_type: ExportFormat, overrides: Optional[Dict] = None) -> ExportOptions:
        """创建导出选项"""
        options = ExportOptions()
        
        # 单位映射
        unit_map = {
            'millimeter': UnitType.MILLIMETER,
            'centimeter': UnitType.CENTIMETER,
            'meter': UnitType.METER,
            'inch': UnitType.INCH,
            'mm': UnitType.MILLIMETER,
            'cm': UnitType.CENTIMETER,
            'm': UnitType.METER,
            'in': UnitType.INCH,
        }
        unit_str = self._config.get('default_unit', 'millimeter').lower()
        options.unit = unit_map.get(unit_str, UnitType.MILLIMETER)
        
        options.precision = self._config.get('default_precision', 0.001)
        options.tolerance = self._config.get('default_tolerance', 0.01)
        options.stl_ascii = self._config.get('stl_ascii', False)
        options.step_schema = self._config.get('step_schema', 'AP214')
        options.iges_unit_flag = self._config.get('iges_unit', 2)
        options.step_write_colors = self._config.get('write_colors', True)
        options.iges_write_colors = self._config.get('write_colors', True)
        
        # 应用覆盖选项
        if overrides:
            for key, value in overrides.items():
                if hasattr(options, key):
                    setattr(options, key, value)
        
        return options
    
    def _get_exporter(self, format_type: ExportFormat) -> CADExporter:
        """获取或创建导出器"""
        if format_type not in self._exporters:
            options = self._create_options(format_type)
            exporter = ExporterFactory.create(format_type, options)
            if self._progress_callback:
                exporter.set_progress_callback(self._progress_callback)
            self._exporters[format_type] = exporter
        return self._exporters[format_type]
    
    def export_mesh(self, mesh: MeshData, filepath: Union[str, Path], 
                    format_type: Optional[ExportFormat] = None,
                    options: Optional[Dict] = None) -> bool:
        """
        导出网格模型
        
        Args:
            mesh: 网格数据
            filepath: 输出文件路径
            format_type: 导出格式（如果为None则自动检测）
            options: 覆盖选项
            
        Returns:
            导出是否成功
        """
        # 自动检测格式
        if format_type is None:
            format_type = get_exporter_for_file(filepath)
            if format_type is None:
                print(f"Error: Cannot detect format from file extension: {filepath}")
                return False
        
        # 获取导出器
        exporter = self._get_exporter(format_type)
        
        # 应用覆盖选项
        if options:
            for key, value in options.items():
                if hasattr(exporter.options, key):
                    setattr(exporter.options, key, value)
        
        # 自动修复网格
        if self._config.get('auto_fix_mesh', True):
            mesh = self._auto_fix_mesh(mesh)
        
        # 验证
        if self._config.get('validate_before_export', True):
            if not exporter.validate_mesh(mesh):
                errors = exporter.get_errors()
                print(f"Validation failed: {errors}")
                return False
        
        # 执行导出
        return exporter.export_mesh(mesh, filepath)
    
    def export_brep(self, solid: BRepSolid, filepath: Union[str, Path],
                    format_type: Optional[ExportFormat] = None,
                    options: Optional[Dict] = None) -> bool:
        """
        导出B-rep实体模型
        
        Args:
            solid: B-rep实体数据
            filepath: 输出文件路径
            format_type: 导出格式（如果为None则自动检测）
            options: 覆盖选项
            
        Returns:
            导出是否成功
        """
        # 自动检测格式
        if format_type is None:
            format_type = get_exporter_for_file(filepath)
            if format_type is None:
                print(f"Error: Cannot detect format from file extension: {filepath}")
                return False
        
        # 获取导出器
        exporter = self._get_exporter(format_type)
        
        # 应用覆盖选项
        if options:
            for key, value in options.items():
                if hasattr(exporter.options, key):
                    setattr(exporter.options, key, value)
        
        # 验证
        if self._config.get('validate_before_export', True):
            if not exporter.validate_brep(solid):
                errors = exporter.get_errors()
                print(f"Validation failed: {errors}")
                return False
        
        # 执行导出
        return exporter.export_brep(solid, filepath)
    
    def export_multiple(self, items: List[Union[MeshData, BRepSolid]], 
                        filepaths: List[Union[str, Path]],
                        format_types: Optional[List[ExportFormat]] = None) -> List[bool]:
        """
        批量导出多个模型
        
        Args:
            items: 模型数据列表
            filepaths: 输出文件路径列表
            format_types: 格式类型列表（如果为None则自动检测）
            
        Returns:
            每个导出操作的结果列表
        """
        results = []
        
        for i, (item, filepath) in enumerate(zip(items, filepaths)):
            format_type = None
            if format_types and i < len(format_types):
                format_type = format_types[i]
            
            if isinstance(item, MeshData):
                result = self.export_mesh(item, filepath, format_type)
            elif isinstance(item, BRepSolid):
                result = self.export_brep(item, filepath, format_type)
            else:
                print(f"Error: Unknown item type at index {i}")
                result = False
            
            results.append(result)
        
        return results
    
    def _auto_fix_mesh(self, mesh: MeshData) -> MeshData:
        """自动修复网格"""
        # 移除退化三角形
        mesh = STLRepairTool.remove_degenerate_triangles(mesh, tolerance=1e-10)
        
        # 修复法向量
        mesh = STLRepairTool.fix_normals(mesh)
        
        return mesh
    
    def get_supported_formats(self) -> List[str]:
        """获取支持的格式列表"""
        formats = []
        for fmt in ExporterFactory.get_supported_formats():
            formats.append(fmt.value)
        return formats
    
    def get_exporter_info(self, format_type: ExportFormat) -> Dict[str, str]:
        """获取导出器信息"""
        exporter = self._get_exporter(format_type)
        return {
            'format_name': exporter.format_name,
            'file_extension': exporter.file_extension,
        }
    
    def validate_file(self, filepath: Union[str, Path]) -> tuple:
        """
        验证CAD文件
        
        Returns:
            (是否有效, 错误信息列表)
        """
        ext = Path(filepath).suffix.lower()
        
        if ext in ['.step', '.stp']:
            return STEPUtils.validate_step_file(filepath)
        elif ext in ['.iges', '.igs']:
            return IGESUtils.validate_iges_file(filepath)
        elif ext == '.stl':
            # STL验证
            try:
                format_type = STLExporter.detect_format(filepath)
                if format_type == 'unknown':
                    return False, ["Cannot detect STL format"]
                return True, []
            except Exception as e:
                return False, [str(e)]
        else:
            return False, [f"Unsupported file format: {ext}"]


# ============================================================================
# 便捷函数
# ============================================================================

def export_mesh(mesh: MeshData, filepath: Union[str, Path], 
                format_type: Optional[ExportFormat] = None,
                progress_callback: Optional[Callable[[ExportProgress], None]] = None,
                **options) -> bool:
    """
    便捷函数：导出网格
    
    Args:
        mesh: 网格数据
        filepath: 输出文件路径
        format_type: 导出格式
        progress_callback: 进度回调函数
        **options: 导出选项
        
    Returns:
        导出是否成功
    """
    manager = CADExportManager()
    if progress_callback:
        manager.set_progress_callback(progress_callback)
    return manager.export_mesh(mesh, filepath, format_type, options)


def export_brep(solid: BRepSolid, filepath: Union[str, Path],
                format_type: Optional[ExportFormat] = None,
                progress_callback: Optional[Callable[[ExportProgress], None]] = None,
                **options) -> bool:
    """
    便捷函数：导出B-rep
    
    Args:
        solid: B-rep实体数据
        filepath: 输出文件路径
        format_type: 导出格式
        progress_callback: 进度回调函数
        **options: 导出选项
        
    Returns:
        导出是否成功
    """
    manager = CADExportManager()
    if progress_callback:
        manager.set_progress_callback(progress_callback)
    return manager.export_brep(solid, filepath, format_type, options)


def convert_stl_to_step(stl_path: Union[str, Path], step_path: Union[str, Path],
                        progress_callback: Optional[Callable[[ExportProgress], None]] = None) -> bool:
    """
    将STL文件转换为STEP格式
    
    Args:
        stl_path: STL文件路径
        step_path: 输出STEP文件路径
        progress_callback: 进度回调函数
        
    Returns:
        转换是否成功
    """
    try:
        # 读取STL
        format_type = STLExporter.detect_format(stl_path)
        if format_type == 'ascii':
            mesh = STLExporter.read_ascii_stl(stl_path)
        elif format_type == 'binary':
            mesh = STLExporter.read_binary_stl(stl_path)
        else:
            print(f"Error: Cannot detect STL format: {stl_path}")
            return False
        
        # 导出为STEP
        return export_mesh(mesh, step_path, ExportFormat.STEP_AP214, progress_callback)
        
    except Exception as e:
        print(f"Error converting STL to STEP: {e}")
        return False


def get_file_info(filepath: Union[str, Path]) -> Dict[str, Any]:
    """
    获取CAD文件信息
    
    Args:
        filepath: 文件路径
        
    Returns:
        文件信息字典
    """
    info = {
        'filepath': str(filepath),
        'exists': Path(filepath).exists(),
        'size': Path(filepath).stat().st_size if Path(filepath).exists() else 0,
        'format': None,
        'entity_counts': {},
        'valid': False,
        'errors': []
    }
    
    if not info['exists']:
        info['errors'].append("File does not exist")
        return info
    
    ext = Path(filepath).suffix.lower()
    
    try:
        if ext == '.stl':
            info['format'] = 'STL'
            info['format_subtype'] = STLExporter.detect_format(filepath)
            info['valid'] = info['format_subtype'] != 'unknown'
            
        elif ext in ['.step', '.stp']:
            info['format'] = 'STEP'
            info['schema'] = STEPUtils.detect_schema(filepath)
            info['entity_counts'] = STEPUtils.count_entities(filepath)
            valid, errors = STEPUtils.validate_step_file(filepath)
            info['valid'] = valid
            info['errors'] = errors
            
        elif ext in ['.iges', '.igs']:
            info['format'] = 'IGES'
            info['version'] = IGESUtils.detect_version(filepath)
            info['entity_counts'] = IGESUtils.count_entities(filepath)
            valid, errors = IGESUtils.validate_iges_file(filepath)
            info['valid'] = valid
            info['errors'] = errors
            
        else:
            info['errors'].append(f"Unsupported file format: {ext}")
            
    except Exception as e:
        info['errors'].append(str(e))
    
    return info


print("CAD导出管理器加载完成")
print("=" * 60)
