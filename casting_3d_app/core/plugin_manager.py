"""
插件管理器模块

提供插件系统架构，支持动态加载、管理和扩展应用程序功能。
支持多种插件类型：图像处理、特征识别、导出器、铸造规则等。
"""

import os
import sys
import importlib
import importlib.util
import logging
from typing import Dict, List, Callable, Any, Optional, Type, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
import json
import threading

logger = logging.getLogger(__name__)


class IPlugin(ABC):
    """
    插件接口基类
    
    所有插件必须实现此接口。
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """插件名称"""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """插件版本"""
        pass
    
    @property
    def description(self) -> str:
        """插件描述"""
        return ""
    
    @property
    def author(self) -> str:
        """插件作者"""
        return ""
    
    @property
    def dependencies(self) -> List[str]:
        """依赖的插件列表"""
        return []
    
    @abstractmethod
    def initialize(self, app_context: Any) -> bool:
        """
        初始化插件
        
        Args:
            app_context: 应用程序上下文
            
        Returns:
            是否初始化成功
        """
        pass
    
    @abstractmethod
    def shutdown(self) -> None:
        """关闭插件"""
        pass
    
    def get_config_schema(self) -> Dict[str, Any]:
        """
        获取配置模式
        
        Returns:
            配置模式定义
        """
        return {}
    
    def on_config_changed(self, key: str, value: Any):
        """
        配置变更回调
        
        Args:
            key: 配置键
            value: 配置值
        """
        pass


class IImageProcessorPlugin(IPlugin):
    """图像处理插件接口"""
    
    @abstractmethod
    def process(self, image: Any) -> Any:
        """
        处理图像
        
        Args:
            image: 输入图像
            
        Returns:
            处理后的图像
        """
        pass
    
    @property
    def processing_order(self) -> int:
        """处理顺序（越小越先执行）"""
        return 100


class IFeatureRecognizerPlugin(IPlugin):
    """特征识别插件接口"""
    
    @abstractmethod
    def recognize(self, contour: Any) -> Optional[Any]:
        """
        识别轮廓特征
        
        Args:
            contour: 轮廓数据
            
        Returns:
            识别的特征，无法识别返回None
        """
        pass
    
    @property
    def supported_types(self) -> List[str]:
        """支持的特征类型"""
        return []


class IExporterPlugin(IPlugin):
    """导出器插件接口"""
    
    @abstractmethod
    def export(self, data: Any, filepath: str, options: Dict = None) -> bool:
        """
        导出数据
        
        Args:
            data: 要导出的数据
            filepath: 输出文件路径
            options: 导出选项
            
        Returns:
            是否导出成功
        """
        pass
    
    @property
    @abstractmethod
    def file_extension(self) -> str:
        """文件扩展名"""
        pass
    
    @property
    @abstractmethod
    def format_name(self) -> str:
        """格式名称"""
        pass


class ICastingRulePlugin(IPlugin):
    """铸造规则插件接口"""
    
    @abstractmethod
    def check(self, part: Any) -> List[Any]:
        """
        检查零件
        
        Args:
            part: 零件数据
            
        Returns:
            检查结果列表
        """
        pass
    
    @property
    def rule_category(self) -> str:
        """规则类别"""
        return "general"
    
    @property
    def auto_fixable(self) -> bool:
        """是否支持自动修复"""
        return False
    
    def auto_fix(self, part: Any, issues: List[Any]) -> bool:
        """
        自动修复问题
        
        Args:
            part: 零件数据
            issues: 问题列表
            
        Returns:
            是否修复成功
        """
        return False


@dataclass
class PluginInfo:
    """插件信息"""
    name: str
    version: str
    description: str
    author: str
    plugin_type: str
    file_path: str
    loaded_at: datetime = None
    enabled: bool = True
    error_message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'author': self.author,
            'plugin_type': self.plugin_type,
            'file_path': self.file_path,
            'loaded_at': self.loaded_at.isoformat() if self.loaded_at else None,
            'enabled': self.enabled,
            'error_message': self.error_message
        }


class PluginManager:
    """
    插件管理器
    
    管理插件的加载、启用/禁用、配置和生命周期。
    单例模式实现。
    
    使用示例:
        manager = PluginManager()
        
        # 加载插件目录
        manager.load_plugins_from_directory('/path/to/plugins')
        
        # 获取插件
        plugin = manager.get_plugin('MyPlugin')
        
        # 启用/禁用插件
        manager.enable_plugin('MyPlugin')
        manager.disable_plugin('MyPlugin')
    """
    
    _instance = None
    _lock = threading.Lock()
    
    # 插件类型映射
    PLUGIN_TYPES = {
        'image_processor': IImageProcessorPlugin,
        'feature_recognizer': IFeatureRecognizerPlugin,
        'exporter': IExporterPlugin,
        'casting_rule': ICastingRulePlugin
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
        
        self._plugins: Dict[str, IPlugin] = {}
        self._plugin_info: Dict[str, PluginInfo] = {}
        self._plugin_types: Dict[str, Type[IPlugin]] = {}
        
        # 按类型组织的插件
        self._plugins_by_type: Dict[str, List[str]] = {
            'image_processor': [],
            'feature_recognizer': [],
            'exporter': [],
            'casting_rule': []
        }
        
        # 插件目录
        self._plugin_directories: List[Path] = []
        
        # 应用程序上下文
        self._app_context: Any = None
        
        # 配置
        self._plugin_configs: Dict[str, Dict] = {}
        
        self._initialized = True
        logger.info("PluginManager initialized")
    
    def set_app_context(self, context: Any):
        """设置应用程序上下文"""
        self._app_context = context
    
    def register_plugin_type(self, type_name: str, interface_class: Type[IPlugin]):
        """
        注册插件类型
        
        Args:
            type_name: 类型名称
            interface_class: 接口类
        """
        self.PLUGIN_TYPES[type_name] = interface_class
        if type_name not in self._plugins_by_type:
            self._plugins_by_type[type_name] = []
        logger.info(f"Registered plugin type: {type_name}")
    
    def add_plugin_directory(self, directory: Union[str, Path]):
        """
        添加插件目录
        
        Args:
            directory: 插件目录路径
        """
        path = Path(directory)
        if path.exists() and path.is_dir():
            self._plugin_directories.append(path)
            logger.info(f"Added plugin directory: {path}")
    
    def load_plugin_from_file(self, filepath: Union[str, Path]) -> Optional[str]:
        """
        从文件加载插件
        
        Args:
            filepath: 插件文件路径
            
        Returns:
            插件名称，失败返回None
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            logger.error(f"Plugin file not found: {filepath}")
            return None
        
        try:
            # 加载模块
            module_name = filepath.stem
            spec = importlib.util.spec_from_file_location(module_name, filepath)
            module = importlib.util.module_from_spec(spec)
            
            # 添加到sys.modules
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # 查找插件类
            plugin_class = self._find_plugin_class(module)
            if not plugin_class:
                logger.error(f"No plugin class found in {filepath}")
                return None
            
            # 实例化插件
            plugin = plugin_class()
            
            # 检查依赖
            if not self._check_dependencies(plugin):
                logger.error(f"Dependency check failed for plugin {plugin.name}")
                return None
            
            # 初始化插件
            if not plugin.initialize(self._app_context):
                logger.error(f"Plugin initialization failed: {plugin.name}")
                return None
            
            # 注册插件
            self._plugins[plugin.name] = plugin
            
            # 创建插件信息
            plugin_type = self._determine_plugin_type(plugin)
            self._plugin_info[plugin.name] = PluginInfo(
                name=plugin.name,
                version=plugin.version,
                description=plugin.description,
                author=plugin.author,
                plugin_type=plugin_type,
                file_path=str(filepath),
                loaded_at=datetime.now()
            )
            
            # 按类型组织
            if plugin_type in self._plugins_by_type:
                self._plugins_by_type[plugin_type].append(plugin.name)
            
            logger.info(f"Loaded plugin: {plugin.name} v{plugin.version}")
            return plugin.name
            
        except Exception as e:
            logger.error(f"Failed to load plugin from {filepath}: {e}")
            return None
    
    def _find_plugin_class(self, module) -> Optional[Type[IPlugin]]:
        """在模块中查找插件类"""
        for name in dir(module):
            obj = getattr(module, name)
            if (isinstance(obj, type) and 
                issubclass(obj, IPlugin) and 
                obj is not IPlugin and
                not getattr(obj, '__abstractmethods__', None)):
                return obj
        return None
    
    def _determine_plugin_type(self, plugin: IPlugin) -> str:
        """确定插件类型"""
        for type_name, interface_class in self.PLUGIN_TYPES.items():
            if isinstance(plugin, interface_class):
                return type_name
        return "unknown"
    
    def _check_dependencies(self, plugin: IPlugin) -> bool:
        """检查插件依赖"""
        for dep in plugin.dependencies:
            if dep not in self._plugins:
                logger.error(f"Plugin {plugin.name} requires {dep} but it's not loaded")
                return False
        return True
    
    def load_plugins_from_directory(self, directory: Union[str, Path] = None) -> int:
        """
        从目录加载所有插件
        
        Args:
            directory: 插件目录，None表示使用已添加的目录
            
        Returns:
            加载的插件数量
        """
        directories = [directory] if directory else self._plugin_directories
        count = 0
        
        for dir_path in directories:
            path = Path(dir_path)
            if not path.exists():
                continue
            
            # 查找所有Python文件
            for file_path in path.glob("*.py"):
                if file_path.name.startswith("_"):
                    continue
                
                if self.load_plugin_from_file(file_path):
                    count += 1
        
        logger.info(f"Loaded {count} plugins from directories")
        return count
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """
        卸载插件
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            是否成功卸载
        """
        if plugin_name not in self._plugins:
            return False
        
        plugin = self._plugins[plugin_name]
        
        # 检查是否有其他插件依赖此插件
        for name, other_plugin in self._plugins.items():
            if name != plugin_name and plugin_name in other_plugin.dependencies:
                logger.error(f"Cannot unload {plugin_name}: {name} depends on it")
                return False
        
        try:
            # 关闭插件
            plugin.shutdown()
            
            # 移除插件
            del self._plugins[plugin_name]
            del self._plugin_info[plugin_name]
            
            # 从类型列表中移除
            for type_list in self._plugins_by_type.values():
                if plugin_name in type_list:
                    type_list.remove(plugin_name)
            
            logger.info(f"Unloaded plugin: {plugin_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unload plugin {plugin_name}: {e}")
            return False
    
    def enable_plugin(self, plugin_name: str) -> bool:
        """启用插件"""
        if plugin_name in self._plugin_info:
            self._plugin_info[plugin_name].enabled = True
            logger.info(f"Enabled plugin: {plugin_name}")
            return True
        return False
    
    def disable_plugin(self, plugin_name: str) -> bool:
        """禁用插件"""
        if plugin_name in self._plugin_info:
            self._plugin_info[plugin_name].enabled = False
            logger.info(f"Disabled plugin: {plugin_name}")
            return True
        return False
    
    def get_plugin(self, plugin_name: str) -> Optional[IPlugin]:
        """获取插件实例"""
        plugin = self._plugins.get(plugin_name)
        if plugin and self._plugin_info.get(plugin_name, PluginInfo("", "", "", "", "", "")).enabled:
            return plugin
        return None
    
    def get_plugins_by_type(self, plugin_type: str) -> List[IPlugin]:
        """获取指定类型的所有插件"""
        result = []
        for name in self._plugins_by_type.get(plugin_type, []):
            plugin = self.get_plugin(name)
            if plugin:
                result.append(plugin)
        return result
    
    def get_all_plugins(self) -> List[IPlugin]:
        """获取所有启用的插件"""
        return [p for name, p in self._plugins.items() 
                if self._plugin_info[name].enabled]
    
    def get_plugin_info(self, plugin_name: str) -> Optional[PluginInfo]:
        """获取插件信息"""
        return self._plugin_info.get(plugin_name)
    
    def get_all_plugin_info(self) -> List[PluginInfo]:
        """获取所有插件信息"""
        return list(self._plugin_info.values())
    
    def is_plugin_loaded(self, plugin_name: str) -> bool:
        """检查插件是否已加载"""
        return plugin_name in self._plugins
    
    def is_plugin_enabled(self, plugin_name: str) -> bool:
        """检查插件是否已启用"""
        info = self._plugin_info.get(plugin_name)
        return info.enabled if info else False
    
    def get_plugin_config(self, plugin_name: str) -> Dict:
        """获取插件配置"""
        return self._plugin_configs.get(plugin_name, {})
    
    def set_plugin_config(self, plugin_name: str, config: Dict):
        """设置插件配置"""
        self._plugin_configs[plugin_name] = config
        
        # 通知插件配置变更
        plugin = self._plugins.get(plugin_name)
        if plugin:
            for key, value in config.items():
                plugin.on_config_changed(key, value)
    
    def save_plugin_configs(self, filepath: Union[str, Path]):
        """保存所有插件配置"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self._plugin_configs, f, indent=2)
            logger.info(f"Plugin configs saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save plugin configs: {e}")
    
    def load_plugin_configs(self, filepath: Union[str, Path]):
        """加载插件配置"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self._plugin_configs = json.load(f)
            logger.info(f"Plugin configs loaded from {filepath}")
        except Exception as e:
            logger.error(f"Failed to load plugin configs: {e}")
    
    def shutdown_all(self):
        """关闭所有插件"""
        for name, plugin in list(self._plugins.items()):
            try:
                plugin.shutdown()
                logger.info(f"Shutdown plugin: {name}")
            except Exception as e:
                logger.error(f"Error shutting down plugin {name}: {e}")
        
        self._plugins.clear()
        self._plugin_info.clear()
        for type_list in self._plugins_by_type.values():
            type_list.clear()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'total_plugins': len(self._plugins),
            'enabled_plugins': sum(1 for info in self._plugin_info.values() if info.enabled),
            'plugins': [info.to_dict() for info in self._plugin_info.values()],
            'plugin_directories': [str(d) for d in self._plugin_directories]
        }


# 便捷函数
def get_plugin_manager() -> PluginManager:
    """获取插件管理器实例"""
    return PluginManager()


def register_image_processor(processor: IImageProcessorPlugin) -> bool:
    """便捷函数：注册图像处理器"""
    manager = PluginManager()
    if isinstance(processor, IImageProcessorPlugin):
        manager._plugins[processor.name] = processor
        manager._plugin_info[processor.name] = PluginInfo(
            name=processor.name,
            version=processor.version,
            description=processor.description,
            author=processor.author,
            plugin_type='image_processor',
            file_path='',
            loaded_at=datetime.now()
        )
        manager._plugins_by_type['image_processor'].append(processor.name)
        return True
    return False


def get_image_processors() -> List[IImageProcessorPlugin]:
    """便捷函数：获取所有图像处理器"""
    return PluginManager().get_plugins_by_type('image_processor')


if __name__ == "__main__":
    # 测试代码
    print("PluginManager Test")
    print("=" * 50)
    
    manager = PluginManager()
    
    # 创建测试插件
    class TestPlugin(IPlugin):
        @property
        def name(self) -> str:
            return "TestPlugin"
        
        @property
        def version(self) -> str:
            return "1.0.0"
        
        @property
        def description(self) -> str:
            return "A test plugin"
        
        def initialize(self, app_context) -> bool:
            print(f"TestPlugin initialized with context: {app_context}")
            return True
        
        def shutdown(self) -> None:
            print("TestPlugin shutdown")
    
    # 手动注册插件
    test_plugin = TestPlugin()
    manager._plugins[test_plugin.name] = test_plugin
    manager._plugin_info[test_plugin.name] = PluginInfo(
        name=test_plugin.name,
        version=test_plugin.version,
        description=test_plugin.description,
        author="Test",
        plugin_type="unknown",
        file_path="",
        loaded_at=datetime.now()
    )
    
    print(f"Registered plugins: {list(manager._plugins.keys())}")
    
    # 获取插件
    plugin = manager.get_plugin("TestPlugin")
    if plugin:
        print(f"Got plugin: {plugin.name} v{plugin.version}")
    
    # 获取插件信息
    info = manager.get_plugin_info("TestPlugin")
    if info:
        print(f"Plugin info: {info.to_dict()}")
    
    # 关闭所有插件
    manager.shutdown_all()
    print(f"After shutdown: {len(manager._plugins)} plugins remaining")
    
    print("\nTest completed!")
