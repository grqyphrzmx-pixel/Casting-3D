"""
配置管理器模块

提供统一的配置管理功能，支持多级配置、配置验证和动态更新。
实现单例模式，确保全局配置一致性。
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, Callable, Union
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import threading

logger = logging.getLogger(__name__)


class ConfigLevel(Enum):
    """配置级别"""
    SYSTEM = 0      # 系统默认
    USER = 1        # 用户配置
    PROJECT = 2     # 项目配置
    RUNTIME = 3     # 运行时覆盖


@dataclass
class ImageAnalysisConfig:
    """图像分析配置"""
    # 预处理
    denoise_method: str = "gaussian"
    gaussian_sigma: float = 1.5
    contrast_method: str = "clahe"
    binarization_method: str = "otsu"
    morphology_enabled: bool = True
    
    # 边缘检测
    edge_method: str = "canny"
    canny_low_threshold: int = 50
    canny_high_threshold: int = 150
    
    # 轮廓分析
    min_contour_area: float = 100.0
    min_contour_perimeter: float = 50.0
    polygon_epsilon_factor: float = 0.01
    
    # 特征识别
    circle_circularity_threshold: float = 0.85
    line_angle_tolerance: float = 5.0
    min_confidence: float = 0.7


@dataclass
class ModelingConfig:
    """3D建模配置"""
    # 默认参数
    default_extrusion_depth: float = 10.0
    default_draft_angle: float = 1.5
    default_fillet_radius: float = 2.0
    
    # 精度设置
    linear_deflection: float = 0.5
    angular_deflection: float = 0.5
    
    # 重建选项
    auto_rebuild: bool = True
    max_history: int = 100
    
    # 特征选项
    auto_apply_fillets: bool = True
    auto_apply_draft: bool = True


@dataclass
class ExportConfig:
    """导出配置"""
    # 默认格式
    default_format: str = "stl_binary"
    default_unit: str = "millimeter"
    
    # STL选项
    stl_binary: bool = True
    stl_tolerance: float = 0.01
    
    # STEP选项
    step_schema: str = "AP214"
    step_write_colors: bool = True
    
    # IGES选项
    iges_unit_flag: int = 2
    iges_write_colors: bool = True
    
    # 通用选项
    auto_fix_mesh: bool = True
    validate_before_export: bool = True


@dataclass
class CastingConfig:
    """铸造工艺配置"""
    # 默认工艺
    default_process: str = "sand_casting"
    default_material: str = "A356"
    
    # 拔模斜度
    draft_angle_external: float = 1.5
    draft_angle_internal: float = 2.0
    draft_angle_core: float = 2.5
    
    # 圆角
    min_fillet_radius: float = 1.5
    fillet_ratio: float = 0.5
    
    # 壁厚
    min_wall_thickness: float = 3.0
    max_thickness_ratio: float = 2.0
    
    # 加工余量
    machining_allowance: float = 2.0
    
    # 质量检查
    enable_quality_check: bool = True
    auto_fix_issues: bool = False


@dataclass
class UIConfig:
    """UI配置"""
    # 主题
    theme: str = "light"
    language: str = "zh_CN"
    
    # 窗口
    window_width: int = 1400
    window_height: int = 900
    window_maximized: bool = False
    
    # 视图
    show_grid: bool = True
    show_axes: bool = True
    background_color: str = "#f0f0f0"
    
    # 最近文件
    recent_files_max: int = 10
    recent_files: List[str] = None
    
    def __post_init__(self):
        if self.recent_files is None:
            self.recent_files = []


class ConfigManager:
    """
    配置管理器
    
    单例模式实现，提供全局配置管理功能。
    支持多级配置：系统默认 < 用户配置 < 项目配置 < 运行时覆盖
    
    使用示例:
        config = ConfigManager()
        
        # 获取配置值
        value = config.get("image_analysis.denoise_method")
        
        # 设置配置值
        config.set("image_analysis.denoise_method", "median")
        
        # 保存配置
        config.save_user_config()
    """
    
    _instance = None
    _lock = threading.Lock()
    
    # 默认配置
    DEFAULT_CONFIG = {
        'image_analysis': asdict(ImageAnalysisConfig()),
        'modeling': asdict(ModelingConfig()),
        'export': asdict(ExportConfig()),
        'casting': asdict(CastingConfig()),
        'ui': asdict(UIConfig()),
        'version': '1.0.0'
    }
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # 多级配置存储
        self._system_config: Dict[str, Any] = {}
        self._user_config: Dict[str, Any] = {}
        self._project_config: Dict[str, Any] = {}
        self._runtime_config: Dict[str, Any] = {}
        
        # 配置变更回调
        self._change_callbacks: List[Callable] = []
        
        # 配置文件路径
        self._user_config_dir: Path = None
        self._user_config_file: Path = None
        self._project_config_file: Path = None
        
        # 验证器
        self._validators: Dict[str, Callable] = {}
        
        self._initialized = True
        
        # 初始化
        self._init_system_config()
        self._init_user_config_path()
        self.load_user_config()
        
        logger.info("ConfigManager initialized")
    
    def _init_system_config(self):
        """初始化系统默认配置"""
        self._system_config = self._deep_copy(self.DEFAULT_CONFIG)
    
    def _init_user_config_path(self):
        """初始化用户配置路径"""
        # 获取用户配置目录
        home = Path.home()
        
        if os.name == 'nt':  # Windows
            config_dir = home / 'AppData' / 'Local' / 'Casting3D'
        elif os.name == 'darwin':  # macOS
            config_dir = home / 'Library' / 'Application Support' / 'Casting3D'
        else:  # Linux
            config_dir = home / '.config' / 'casting3d'
        
        self._user_config_dir = config_dir
        self._user_config_file = config_dir / 'config.json'
        
        # 确保目录存在
        self._user_config_dir.mkdir(parents=True, exist_ok=True)
    
    def _deep_copy(self, obj: Any) -> Any:
        """深拷贝对象"""
        return json.loads(json.dumps(obj))
    
    def _get_nested_value(self, config: Dict, key_path: str) -> Any:
        """获取嵌套配置值"""
        keys = key_path.split('.')
        value = config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        
        return value
    
    def _set_nested_value(self, config: Dict, key_path: str, value: Any):
        """设置嵌套配置值"""
        keys = key_path.split('.')
        target = config
        
        for key in keys[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]
        
        target[keys[-1]] = value
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置值
        
        按优先级查找：运行时 > 项目 > 用户 > 系统
        
        Args:
            key_path: 配置键路径，如 "image_analysis.denoise_method"
            default: 默认值
            
        Returns:
            配置值
        """
        # 按优先级查找
        for config in [self._runtime_config, self._project_config, 
                       self._user_config, self._system_config]:
            value = self._get_nested_value(config, key_path)
            if value is not None:
                return value
        
        return default
    
    def set(self, key_path: str, value: Any, level: ConfigLevel = ConfigLevel.RUNTIME):
        """
        设置配置值
        
        Args:
            key_path: 配置键路径
            value: 配置值
            level: 配置级别
        """
        # 验证值
        validator = self._validators.get(key_path)
        if validator and not validator(value):
            logger.warning(f"Config validation failed for {key_path}: {value}")
            return
        
        # 根据级别设置
        if level == ConfigLevel.SYSTEM:
            self._set_nested_value(self._system_config, key_path, value)
        elif level == ConfigLevel.USER:
            self._set_nested_value(self._user_config, key_path, value)
        elif level == ConfigLevel.PROJECT:
            self._set_nested_value(self._project_config, key_path, value)
        else:  # RUNTIME
            self._set_nested_value(self._runtime_config, key_path, value)
        
        # 触发变更回调
        self._notify_change(key_path, value)
        
        logger.debug(f"Config set: {key_path} = {value} (level: {level.name})")
    
    def get_config_object(self, config_name: str) -> Any:
        """
        获取配置对象
        
        Args:
            config_name: 配置对象名称，如 "image_analysis"
            
        Returns:
            配置字典
        """
        result = {}
        
        # 合并各级配置
        for config in [self._system_config, self._user_config, 
                       self._project_config, self._runtime_config]:
            if config_name in config:
                result.update(config[config_name])
        
        return result
    
    def load_user_config(self) -> bool:
        """
        加载用户配置
        
        Returns:
            是否成功加载
        """
        if not self._user_config_file.exists():
            logger.info("User config file not found, using defaults")
            return False
        
        try:
            with open(self._user_config_file, 'r', encoding='utf-8') as f:
                self._user_config = json.load(f)
            logger.info(f"User config loaded from {self._user_config_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to load user config: {e}")
            return False
    
    def save_user_config(self) -> bool:
        """
        保存用户配置
        
        Returns:
            是否成功保存
        """
        try:
            with open(self._user_config_file, 'w', encoding='utf-8') as f:
                json.dump(self._user_config, f, indent=2, ensure_ascii=False)
            logger.info(f"User config saved to {self._user_config_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save user config: {e}")
            return False
    
    def load_project_config(self, project_path: Union[str, Path]) -> bool:
        """
        加载项目配置
        
        Args:
            project_path: 项目路径
            
        Returns:
            是否成功加载
        """
        project_path = Path(project_path)
        config_file = project_path / 'project_config.json'
        
        if not config_file.exists():
            return False
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                self._project_config = json.load(f)
            self._project_config_file = config_file
            logger.info(f"Project config loaded from {config_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to load project config: {e}")
            return False
    
    def save_project_config(self, project_path: Union[str, Path] = None) -> bool:
        """
        保存项目配置
        
        Args:
            project_path: 项目路径，None表示使用当前项目
            
        Returns:
            是否成功保存
        """
        if project_path:
            config_file = Path(project_path) / 'project_config.json'
        elif self._project_config_file:
            config_file = self._project_config_file
        else:
            logger.error("No project config file specified")
            return False
        
        try:
            config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self._project_config, f, indent=2, ensure_ascii=False)
            logger.info(f"Project config saved to {config_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save project config: {e}")
            return False
    
    def reset_to_defaults(self):
        """重置为默认配置"""
        self._user_config = {}
        self._project_config = {}
        self._runtime_config = {}
        logger.info("Config reset to defaults")
    
    def register_validator(self, key_path: str, validator: Callable[[Any], bool]):
        """
        注册配置验证器
        
        Args:
            key_path: 配置键路径
            validator: 验证函数，返回True表示验证通过
        """
        self._validators[key_path] = validator
    
    def on_change(self, callback: Callable[[str, Any], None]):
        """
        注册配置变更回调
        
        Args:
            callback: 回调函数，接收(key_path, value)参数
        """
        self._change_callbacks.append(callback)
    
    def _notify_change(self, key_path: str, value: Any):
        """通知配置变更"""
        for callback in self._change_callbacks:
            try:
                callback(key_path, value)
            except Exception as e:
                logger.error(f"Config change callback error: {e}")
        
        # 发布事件
        from .event_bus import EventBus
        EventBus().publish("config.changed", {'key': key_path, 'value': value}, "ConfigManager")
    
    def get_user_config_dir(self) -> Path:
        """获取用户配置目录"""
        return self._user_config_dir
    
    def export_config(self, filepath: Union[str, Path], level: ConfigLevel = ConfigLevel.USER):
        """
        导出配置到文件
        
        Args:
            filepath: 输出文件路径
            level: 要导出的配置级别
        """
        if level == ConfigLevel.SYSTEM:
            config = self._system_config
        elif level == ConfigLevel.USER:
            config = self._user_config
        elif level == ConfigLevel.PROJECT:
            config = self._project_config
        else:
            config = self._runtime_config
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            logger.info(f"Config exported to {filepath}")
        except Exception as e:
            logger.error(f"Failed to export config: {e}")
    
    def import_config(self, filepath: Union[str, Path], level: ConfigLevel = ConfigLevel.USER):
        """
        从文件导入配置
        
        Args:
            filepath: 配置文件路径
            level: 导入到的配置级别
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            if level == ConfigLevel.USER:
                self._user_config.update(config)
            elif level == ConfigLevel.PROJECT:
                self._project_config.update(config)
            elif level == ConfigLevel.RUNTIME:
                self._runtime_config.update(config)
            
            logger.info(f"Config imported from {filepath}")
        except Exception as e:
            logger.error(f"Failed to import config: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（合并所有级别）"""
        result = self._deep_copy(self._system_config)
        self._deep_merge(result, self._user_config)
        self._deep_merge(result, self._project_config)
        self._deep_merge(result, self._runtime_config)
        return result
    
    def _deep_merge(self, base: Dict, override: Dict):
        """深度合并字典"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value


# 便捷函数
def get_config_manager() -> ConfigManager:
    """获取配置管理器实例"""
    return ConfigManager()


def get_config(key_path: str, default: Any = None) -> Any:
    """便捷函数：获取配置值"""
    return ConfigManager().get(key_path, default)


def set_config(key_path: str, value: Any, level: ConfigLevel = ConfigLevel.RUNTIME):
    """便捷函数：设置配置值"""
    ConfigManager().set(key_path, value, level)


if __name__ == "__main__":
    # 测试代码
    print("ConfigManager Test")
    print("=" * 50)
    
    config = ConfigManager()
    
    # 测试获取配置
    print(f"Denoise method: {config.get('image_analysis.denoise_method')}")
    print(f"Default format: {config.get('export.default_format')}")
    print(f"Theme: {config.get('ui.theme')}")
    
    # 测试设置配置
    config.set('image_analysis.denoise_method', 'median', ConfigLevel.RUNTIME)
    print(f"After set: {config.get('image_analysis.denoise_method')}")
    
    # 测试配置对象
    image_config = config.get_config_object('image_analysis')
    print(f"\nImage analysis config: {image_config}")
    
    # 测试导出
    config.export_config('/tmp/test_config.json')
    print("\nConfig exported to /tmp/test_config.json")
    
    print("\nTest completed!")
