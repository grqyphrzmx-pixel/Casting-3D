"""
铸造行业2D到3D转换 - 配置加载模块

本模块提供配置文件的加载、验证和合并功能。
"""

import yaml
import json
from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field


# =============================================================================
# 配置加载器
# =============================================================================

class ConfigLoader:
    """配置加载器"""
    
    def __init__(self, default_config_path: str = None):
        """
        初始化配置加载器
        
        Args:
            default_config_path: 默认配置文件路径
        """
        if default_config_path is None:
            # 使用默认路径
            module_dir = Path(__file__).parent.parent
            default_config_path = module_dir / "config" / "default_config.yaml"
        
        self.default_config_path = Path(default_config_path)
        self._default_config = None
        self._user_config = None
    
    def load(self, user_config_path: str = None) -> Dict[str, Any]:
        """
        加载配置
        
        Args:
            user_config_path: 用户配置文件路径
            
        Returns:
            合并后的配置字典
        """
        # 加载默认配置
        self._default_config = self._load_file(self.default_config_path)
        
        # 加载用户配置
        if user_config_path:
            self._user_config = self._load_file(Path(user_config_path))
        else:
            self._user_config = {}
        
        # 合并配置
        config = self._merge_configs(self._default_config, self._user_config)
        
        # 验证配置
        self._validate_config(config)
        
        return config
    
    def _load_file(self, filepath: Path) -> Dict[str, Any]:
        """加载配置文件"""
        if not filepath.exists():
            raise FileNotFoundError(f"Config file not found: {filepath}")
        
        suffix = filepath.suffix.lower()
        
        if suffix in ['.yaml', '.yml']:
            with open(filepath, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        elif suffix == '.json':
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            raise ValueError(f"Unsupported config file format: {suffix}")
    
    def _merge_configs(self, default: Dict, user: Dict) -> Dict:
        """递归合并配置"""
        result = default.copy()
        
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _validate_config(self, config: Dict) -> bool:
        """验证配置"""
        required_sections = [
            'preprocessing',
            'edge_detection',
            'contour',
            'feature'
        ]
        
        for section in required_sections:
            if section not in config:
                raise ValueError(f"Missing required config section: {section}")
        
        return True
    
    def get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        if self._default_config is None:
            self._default_config = self._load_file(self.default_config_path)
        return self._default_config.copy()
    
    def save_config(self, config: Dict, filepath: str):
        """保存配置到文件"""
        path = Path(filepath)
        suffix = path.suffix.lower()
        
        if suffix in ['.yaml', '.yml']:
            with open(path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        elif suffix == '.json':
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        else:
            raise ValueError(f"Unsupported output format: {suffix}")


# =============================================================================
# 配置对象
# =============================================================================

@dataclass
class PreprocessingConfig:
    """预处理配置"""
    denoise_method: str = "gaussian"
    gaussian_sigma: float = 1.5
    median_kernel_size: int = 5
    bilateral_d: int = 9
    bilateral_sigma_color: float = 75.0
    bilateral_sigma_space: float = 75.0
    contrast_method: str = "clahe"
    clahe_clip_limit: float = 2.0
    clahe_grid_size: int = 8
    gamma_value: float = 1.0
    binarization_method: str = "otsu"
    adaptive_block_size: int = 11
    adaptive_c: float = 2.0
    manual_threshold: int = 127
    morphology_enabled: bool = True
    morphology_operations: list = field(default_factory=list)


@dataclass
class EdgeDetectionConfig:
    """边缘检测配置"""
    method: str = "canny"
    canny_low_threshold: int = 50
    canny_high_threshold: int = 150
    canny_aperture_size: int = 3
    canny_l2_gradient: bool = False
    sobel_kernel_size: int = 3
    laplacian_kernel_size: int = 3


@dataclass
class ContourConfig:
    """轮廓分析配置"""
    retrieval_mode: str = "tree"
    approximation_method: str = "simple"
    min_area: float = 100.0
    max_area_ratio: float = 0.95
    min_perimeter: float = 50.0
    min_vertices: int = 3
    polygon_epsilon_factor: float = 0.01


@dataclass
class FeatureExtractionConfig:
    """特征提取配置"""
    min_confidence: float = 0.7
    line_angle_tolerance: float = 5.0
    circle_circularity_threshold: float = 0.85
    arc_min_angle_span: float = 15.0
    arc_max_angle_span: float = 350.0
    polygon_angle_tolerance: float = 10.0
    enabled_recognizers: list = field(default_factory=list)


@dataclass
class DimensionExtractionConfig:
    """尺寸提取配置"""
    ocr_enabled: bool = True
    min_text_height: int = 10
    text_confidence_threshold: float = 0.6
    dimension_line_extension: float = 10.0
    arrow_detection_enabled: bool = True


@dataclass
class DebugConfig:
    """调试配置"""
    enabled: bool = False
    visualize_intermediate: bool = False
    save_intermediate: bool = False
    intermediate_path: str = "./debug_output"


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = "INFO"
    file: str = "image_analysis.log"
    console_output: bool = True
    file_output: bool = True


@dataclass
class PerformanceConfig:
    """性能配置"""
    multithreading: bool = True
    max_threads: int = 0
    gpu_acceleration: bool = False
    pyramid_levels: int = 1
    max_image_size: int = 4096


@dataclass
class OutputConfig:
    """输出配置"""
    default_format: str = "json"
    include_contours: bool = True
    include_parameters: bool = True
    coordinate_precision: int = 3
    unit: str = "mm"


@dataclass
class AnalyzerConfig:
    """分析器完整配置"""
    preprocessing: PreprocessingConfig = field(default_factory=PreprocessingConfig)
    edge_detection: EdgeDetectionConfig = field(default_factory=EdgeDetectionConfig)
    contour: ContourConfig = field(default_factory=ContourConfig)
    feature: FeatureExtractionConfig = field(default_factory=FeatureExtractionConfig)
    dimension: DimensionExtractionConfig = field(default_factory=DimensionExtractionConfig)
    debug: DebugConfig = field(default_factory=DebugConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    version: str = "1.0"


# =============================================================================
# 配置转换函数
# =============================================================================

def dict_to_config(config_dict: Dict[str, Any]) -> AnalyzerConfig:
    """
    将配置字典转换为配置对象
    
    Args:
        config_dict: 配置字典
        
    Returns:
        配置对象
    """
    config = AnalyzerConfig()
    
    # 预处理配置
    if 'preprocessing' in config_dict:
        prep = config_dict['preprocessing']
        config.preprocessing = PreprocessingConfig(
            denoise_method=prep.get('denoise_method', 'gaussian'),
            gaussian_sigma=prep.get('gaussian_sigma', 1.5),
            median_kernel_size=prep.get('median_kernel_size', 5),
            bilateral_d=prep.get('bilateral_d', 9),
            bilateral_sigma_color=prep.get('bilateral_sigma_color', 75.0),
            bilateral_sigma_space=prep.get('bilateral_sigma_space', 75.0),
            contrast_method=prep.get('contrast_method', 'clahe'),
            clahe_clip_limit=prep.get('clahe_clip_limit', 2.0),
            clahe_grid_size=prep.get('clahe_grid_size', 8),
            gamma_value=prep.get('gamma_value', 1.0),
            binarization_method=prep.get('binarization_method', 'otsu'),
            adaptive_block_size=prep.get('adaptive_block_size', 11),
            adaptive_c=prep.get('adaptive_c', 2.0),
            manual_threshold=prep.get('manual_threshold', 127),
            morphology_enabled=prep.get('morphology_enabled', True),
            morphology_operations=prep.get('morphology_operations', [])
        )
    
    # 边缘检测配置
    if 'edge_detection' in config_dict:
        edge = config_dict['edge_detection']
        config.edge_detection = EdgeDetectionConfig(
            method=edge.get('method', 'canny'),
            canny_low_threshold=edge.get('canny_low_threshold', 50),
            canny_high_threshold=edge.get('canny_high_threshold', 150),
            canny_aperture_size=edge.get('canny_aperture_size', 3),
            canny_l2_gradient=edge.get('canny_l2_gradient', False),
            sobel_kernel_size=edge.get('sobel_kernel_size', 3),
            laplacian_kernel_size=edge.get('laplacian_kernel_size', 3)
        )
    
    # 轮廓配置
    if 'contour' in config_dict:
        cont = config_dict['contour']
        config.contour = ContourConfig(
            retrieval_mode=cont.get('retrieval_mode', 'tree'),
            approximation_method=cont.get('approximation_method', 'simple'),
            min_area=cont.get('min_area', 100.0),
            max_area_ratio=cont.get('max_area_ratio', 0.95),
            min_perimeter=cont.get('min_perimeter', 50.0),
            min_vertices=cont.get('min_vertices', 3),
            polygon_epsilon_factor=cont.get('polygon_epsilon_factor', 0.01)
        )
    
    # 特征提取配置
    if 'feature' in config_dict:
        feat = config_dict['feature']
        config.feature = FeatureExtractionConfig(
            min_confidence=feat.get('min_confidence', 0.7),
            line_angle_tolerance=feat.get('line_angle_tolerance', 5.0),
            circle_circularity_threshold=feat.get('circle_circularity_threshold', 0.85),
            arc_min_angle_span=feat.get('arc_min_angle_span', 15.0),
            arc_max_angle_span=feat.get('arc_max_angle_span', 350.0),
            polygon_angle_tolerance=feat.get('polygon_angle_tolerance', 10.0),
            enabled_recognizers=feat.get('enabled_recognizers', ['line', 'circle', 'arc', 'ellipse', 'polygon'])
        )
    
    # 尺寸提取配置
    if 'dimension' in config_dict:
        dim = config_dict['dimension']
        config.dimension = DimensionExtractionConfig(
            ocr_enabled=dim.get('ocr_enabled', True),
            min_text_height=dim.get('min_text_height', 10),
            text_confidence_threshold=dim.get('text_confidence_threshold', 0.6),
            dimension_line_extension=dim.get('dimension_line_extension', 10.0),
            arrow_detection_enabled=dim.get('arrow_detection_enabled', True)
        )
    
    # 调试配置
    if 'debug' in config_dict:
        dbg = config_dict['debug']
        config.debug = DebugConfig(
            enabled=dbg.get('enabled', False),
            visualize_intermediate=dbg.get('visualize_intermediate', False),
            save_intermediate=dbg.get('save_intermediate', False),
            intermediate_path=dbg.get('intermediate_path', './debug_output')
        )
    
    # 日志配置
    if 'logging' in config_dict:
        log = config_dict['logging']
        config.logging = LoggingConfig(
            level=log.get('level', 'INFO'),
            file=log.get('file', 'image_analysis.log'),
            console_output=log.get('console_output', True),
            file_output=log.get('file_output', True)
        )
    
    # 性能配置
    if 'performance' in config_dict:
        perf = config_dict['performance']
        config.performance = PerformanceConfig(
            multithreading=perf.get('multithreading', True),
            max_threads=perf.get('max_threads', 0),
            gpu_acceleration=perf.get('gpu_acceleration', False),
            pyramid_levels=perf.get('pyramid_levels', 1),
            max_image_size=perf.get('max_image_size', 4096)
        )
    
    # 输出配置
    if 'output' in config_dict:
        out = config_dict['output']
        config.output = OutputConfig(
            default_format=out.get('default_format', 'json'),
            include_contours=out.get('include_contours', True),
            include_parameters=out.get('include_parameters', True),
            coordinate_precision=out.get('coordinate_precision', 3),
            unit=out.get('unit', 'mm')
        )
    
    # 版本
    config.version = config_dict.get('version', '1.0')
    
    return config


def config_to_dict(config: AnalyzerConfig) -> Dict[str, Any]:
    """
    将配置对象转换为字典
    
    Args:
        config: 配置对象
        
    Returns:
        配置字典
    """
    return {
        'version': config.version,
        'preprocessing': {
            'denoise_method': config.preprocessing.denoise_method,
            'gaussian_sigma': config.preprocessing.gaussian_sigma,
            'median_kernel_size': config.preprocessing.median_kernel_size,
            'bilateral_d': config.preprocessing.bilateral_d,
            'bilateral_sigma_color': config.preprocessing.bilateral_sigma_color,
            'bilateral_sigma_space': config.preprocessing.bilateral_sigma_space,
            'contrast_method': config.preprocessing.contrast_method,
            'clahe_clip_limit': config.preprocessing.clahe_clip_limit,
            'clahe_grid_size': config.preprocessing.clahe_grid_size,
            'gamma_value': config.preprocessing.gamma_value,
            'binarization_method': config.preprocessing.binarization_method,
            'adaptive_block_size': config.preprocessing.adaptive_block_size,
            'adaptive_c': config.preprocessing.adaptive_c,
            'manual_threshold': config.preprocessing.manual_threshold,
            'morphology_enabled': config.preprocessing.morphology_enabled,
            'morphology_operations': config.preprocessing.morphology_operations
        },
        'edge_detection': {
            'method': config.edge_detection.method,
            'canny_low_threshold': config.edge_detection.canny_low_threshold,
            'canny_high_threshold': config.edge_detection.canny_high_threshold,
            'canny_aperture_size': config.edge_detection.canny_aperture_size,
            'canny_l2_gradient': config.edge_detection.canny_l2_gradient,
            'sobel_kernel_size': config.edge_detection.sobel_kernel_size,
            'laplacian_kernel_size': config.edge_detection.laplacian_kernel_size
        },
        'contour': {
            'retrieval_mode': config.contour.retrieval_mode,
            'approximation_method': config.contour.approximation_method,
            'min_area': config.contour.min_area,
            'max_area_ratio': config.contour.max_area_ratio,
            'min_perimeter': config.contour.min_perimeter,
            'min_vertices': config.contour.min_vertices,
            'polygon_epsilon_factor': config.contour.polygon_epsilon_factor
        },
        'feature': {
            'min_confidence': config.feature.min_confidence,
            'line_angle_tolerance': config.feature.line_angle_tolerance,
            'circle_circularity_threshold': config.feature.circle_circularity_threshold,
            'arc_min_angle_span': config.feature.arc_min_angle_span,
            'arc_max_angle_span': config.feature.arc_max_angle_span,
            'polygon_angle_tolerance': config.feature.polygon_angle_tolerance,
            'enabled_recognizers': config.feature.enabled_recognizers
        },
        'dimension': {
            'ocr_enabled': config.dimension.ocr_enabled,
            'min_text_height': config.dimension.min_text_height,
            'text_confidence_threshold': config.dimension.text_confidence_threshold,
            'dimension_line_extension': config.dimension.dimension_line_extension,
            'arrow_detection_enabled': config.dimension.arrow_detection_enabled
        },
        'debug': {
            'enabled': config.debug.enabled,
            'visualize_intermediate': config.debug.visualize_intermediate,
            'save_intermediate': config.debug.save_intermediate,
            'intermediate_path': config.debug.intermediate_path
        },
        'logging': {
            'level': config.logging.level,
            'file': config.logging.file,
            'console_output': config.logging.console_output,
            'file_output': config.logging.file_output
        },
        'performance': {
            'multithreading': config.performance.multithreading,
            'max_threads': config.performance.max_threads,
            'gpu_acceleration': config.performance.gpu_acceleration,
            'pyramid_levels': config.performance.pyramid_levels,
            'max_image_size': config.performance.max_image_size
        },
        'output': {
            'default_format': config.output.default_format,
            'include_contours': config.output.include_contours,
            'include_parameters': config.output.include_parameters,
            'coordinate_precision': config.output.coordinate_precision,
            'unit': config.output.unit
        }
    }


# =============================================================================
# 便捷函数
# =============================================================================

def load_config(config_path: str = None) -> AnalyzerConfig:
    """
    便捷函数：加载配置
    
    Args:
        config_path: 配置文件路径，None则使用默认配置
        
    Returns:
        配置对象
    """
    loader = ConfigLoader()
    config_dict = loader.load(config_path)
    return dict_to_config(config_dict)


def save_config(config: AnalyzerConfig, filepath: str):
    """
    便捷函数：保存配置
    
    Args:
        config: 配置对象
        filepath: 输出文件路径
    """
    config_dict = config_to_dict(config)
    loader = ConfigLoader()
    loader.save_config(config_dict, filepath)


# 模块测试
if __name__ == "__main__":
    # 测试配置加载
    print("Testing ConfigLoader\n")
    
    # 加载默认配置
    loader = ConfigLoader()
    config_dict = loader.load()
    
    print(f"Loaded config version: {config_dict.get('version')}")
    print(f"Preprocessing denoise method: {config_dict['preprocessing']['denoise_method']}")
    print(f"Edge detection method: {config_dict['edge_detection']['method']}")
    
    # 转换为配置对象
    config = dict_to_config(config_dict)
    
    print(f"\nConfig object:")
    print(f"  Preprocessing.gaussian_sigma: {config.preprocessing.gaussian_sigma}")
    print(f"  EdgeDetection.canny_low_threshold: {config.edge_detection.canny_low_threshold}")
    print(f"  Contour.min_area: {config.contour.min_area}")
    print(f"  Feature.min_confidence: {config.feature.min_confidence}")
    
    # 测试配置保存
    test_config_path = "/mnt/okcomputer/output/image_analysis_module/config/test_config.yaml"
    save_config(config, test_config_path)
    print(f"\nConfig saved to: {test_config_path}")
    
    print("\nAll tests passed!")
