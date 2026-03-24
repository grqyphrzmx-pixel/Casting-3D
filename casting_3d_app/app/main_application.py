"""
应用程序主类模块

铸造行业2D到3D转换应用程序的主入口类。
负责初始化所有模块、管理应用程序生命周期和协调各组件。
"""

import sys
import os
import logging
from typing import Optional, Dict, Any, Callable
from pathlib import Path
from datetime import datetime
import traceback

# 确保可以导入其他模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.event_bus import EventBus, EventPriority
from core.workflow_manager import WorkflowManager, WorkflowType, WorkflowContext
from core.config_manager import ConfigManager, ConfigLevel
from core.plugin_manager import PluginManager

logger = logging.getLogger(__name__)


class ApplicationContext:
    """
    应用程序上下文
    
    提供给插件和其他组件访问应用程序核心功能的接口。
    """
    
    def __init__(self, app: 'MainApplication'):
        self._app = app
    
    @property
    def event_bus(self) -> EventBus:
        return self._app.event_bus
    
    @property
    def workflow_manager(self) -> WorkflowManager:
        return self._app.workflow_manager
    
    @property
    def config_manager(self) -> ConfigManager:
        return self._app.config_manager
    
    @property
    def plugin_manager(self) -> PluginManager:
        return self._app.plugin_manager
    
    def get_service(self, service_name: str) -> Any:
        """获取服务实例"""
        return self._app.get_service(service_name)
    
    def publish_event(self, event_type: str, data: Any = None):
        """发布事件"""
        self._app.publish_event(event_type, data)


class ServiceLocator:
    """
    服务定位器
    
    管理应用程序中的各种服务实例。
    """
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
    
    def register(self, name: str, service: Any):
        """注册服务"""
        self._services[name] = service
        logger.info(f"Registered service: {name}")
    
    def get(self, name: str) -> Optional[Any]:
        """获取服务"""
        return self._services.get(name)
    
    def unregister(self, name: str):
        """注销服务"""
        if name in self._services:
            del self._services[name]


class MainApplication:
    """
    主应用程序类
    
    铸造行业2D到3D转换应用程序的核心类。
    负责初始化、运行和关闭应用程序。
    
    使用示例:
        app = MainApplication()
        if app.initialize():
            app.run()
        app.shutdown()
    """
    
    VERSION = "1.0.0"
    APP_NAME = "铸造2D到3D转换器"
    APP_NAME_EN = "Casting2D3DConverter"
    
    def __init__(self):
        # 核心组件
        self._event_bus: Optional[EventBus] = None
        self._workflow_manager: Optional[WorkflowManager] = None
        self._config_manager: Optional[ConfigManager] = None
        self._plugin_manager: Optional[PluginManager] = None
        self._service_locator: Optional[ServiceLocator] = None
        
        # 应用程序上下文
        self._app_context: Optional[ApplicationContext] = None
        
        # 模块接口
        self._image_analyzer = None
        self._modeling_engine = None
        self._export_manager = None
        self._casting_rules = None
        
        # 状态
        self._initialized = False
        self._running = False
        self._start_time: Optional[datetime] = None
        
        # 主窗口（GUI）
        self._main_window = None
        
        # 错误处理
        self._error_handlers: List[Callable] = []
    
    # ==================== 属性访问 ====================
    
    @property
    def event_bus(self) -> EventBus:
        return self._event_bus
    
    @property
    def workflow_manager(self) -> WorkflowManager:
        return self._workflow_manager
    
    @property
    def config_manager(self) -> ConfigManager:
        return self._config_manager
    
    @property
    def plugin_manager(self) -> PluginManager:
        return self._plugin_manager
    
    @property
    def app_context(self) -> ApplicationContext:
        return self._app_context
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    @property
    def uptime(self) -> float:
        """获取运行时间（秒）"""
        if self._start_time:
            return (datetime.now() - self._start_time).total_seconds()
        return 0.0
    
    # ==================== 初始化 ====================
    
    def initialize(self, args: Dict[str, Any] = None) -> bool:
        """
        初始化应用程序
        
        Args:
            args: 启动参数
            
        Returns:
            是否初始化成功
        """
        if self._initialized:
            logger.warning("Application already initialized")
            return True
        
        try:
            logger.info(f"Initializing {self.APP_NAME} v{self.VERSION}")
            
            # 1. 初始化日志系统
            self._init_logging()
            
            # 2. 初始化核心组件
            self._init_core_components()
            
            # 3. 加载配置
            self._load_configuration()
            
            # 4. 初始化模块接口
            self._init_module_interfaces()
            
            # 5. 加载插件
            self._load_plugins()
            
            # 6. 注册服务
            self._register_services()
            
            # 7. 订阅核心事件
            self._subscribe_events()
            
            self._initialized = True
            self._start_time = datetime.now()
            
            # 发布应用程序启动事件
            self.publish_event(EventBus.EVENT_APP_STARTED, {
                'version': self.VERSION,
                'start_time': self._start_time.isoformat()
            })
            
            logger.info("Application initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Application initialization failed: {e}")
            logger.error(traceback.format_exc())
            self._handle_fatal_error(e)
            return False
    
    def _init_logging(self):
        """初始化日志系统"""
        log_level = logging.INFO
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(logging.Formatter(log_format))
        
        # 文件处理器
        log_dir = Path.home() / '.casting3d' / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f'app_{datetime.now().strftime("%Y%m%d")}.log'
        
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(log_format))
        
        # 根日志配置
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)
        
        logger.info("Logging system initialized")
    
    def _init_core_components(self):
        """初始化核心组件"""
        # 事件总线
        self._event_bus = EventBus()
        self._event_bus.start_async_processing()
        logger.info("EventBus initialized")
        
        # 配置管理器
        self._config_manager = ConfigManager()
        logger.info("ConfigManager initialized")
        
        # 工作流管理器
        self._workflow_manager = WorkflowManager()
        logger.info("WorkflowManager initialized")
        
        # 插件管理器
        self._plugin_manager = PluginManager()
        logger.info("PluginManager initialized")
        
        # 服务定位器
        self._service_locator = ServiceLocator()
        
        # 应用程序上下文
        self._app_context = ApplicationContext(self)
        self._plugin_manager.set_app_context(self._app_context)
    
    def _load_configuration(self):
        """加载配置"""
        # 配置已在ConfigManager初始化时加载
        # 这里可以添加额外的配置处理
        logger.info("Configuration loaded")
    
    def _init_module_interfaces(self):
        """初始化模块接口"""
        try:
            # 尝试导入图像分析模块
            sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'image_analysis_module'))
            from image_analysis_module.core.image_analyzer import ImageAnalyzer
            self._image_analyzer = ImageAnalyzer()
            logger.info("ImageAnalyzer initialized")
        except ImportError as e:
            logger.warning(f"ImageAnalyzer not available: {e}")
        
        try:
            # 尝试导入3D建模引擎
            sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'casting_3d_engine'))
            from casting_3d_engine.core.casting_3d_engine import Casting3DEngine
            self._modeling_engine = Casting3DEngine()
            logger.info("Casting3DEngine initialized")
        except ImportError as e:
            logger.warning(f"Casting3DEngine not available: {e}")
        
        try:
            # 尝试导入CAD导出模块
            sys.path.insert(0, str(Path(__file__).parent.parent.parent))
            from cad_export_manager import CADExportManager
            self._export_manager = CADExportManager()
            logger.info("CADExportManager initialized")
        except ImportError as e:
            logger.warning(f"CADExportManager not available: {e}")
        
        try:
            # 尝试导入铸造规则引擎
            sys.path.insert(0, str(Path(__file__).parent.parent.parent))
            from casting_rules_engine import QualityCheckEngine
            self._casting_rules = QualityCheckEngine()
            logger.info("QualityCheckEngine initialized")
        except ImportError as e:
            logger.warning(f"QualityCheckEngine not available: {e}")
    
    def _load_plugins(self):
        """加载插件"""
        # 添加插件目录
        plugin_dirs = [
            Path(__file__).parent.parent / 'plugins',
            Path.home() / '.casting3d' / 'plugins'
        ]
        
        for plugin_dir in plugin_dirs:
            if plugin_dir.exists():
                self._plugin_manager.add_plugin_directory(plugin_dir)
        
        # 加载插件
        count = self._plugin_manager.load_plugins_from_directory()
        logger.info(f"Loaded {count} plugins")
    
    def _register_services(self):
        """注册服务"""
        self._service_locator.register('event_bus', self._event_bus)
        self._service_locator.register('workflow_manager', self._workflow_manager)
        self._service_locator.register('config_manager', self._config_manager)
        self._service_locator.register('plugin_manager', self._plugin_manager)
        
        if self._image_analyzer:
            self._service_locator.register('image_analyzer', self._image_analyzer)
        if self._modeling_engine:
            self._service_locator.register('modeling_engine', self._modeling_engine)
        if self._export_manager:
            self._service_locator.register('export_manager', self._export_manager)
        if self._casting_rules:
            self._service_locator.register('casting_rules', self._casting_rules)
    
    def _subscribe_events(self):
        """订阅核心事件"""
        # 错误事件
        self._event_bus.subscribe(
            EventBus.EVENT_ERROR_OCCURRED,
            self._on_error_occurred,
            EventPriority.HIGH
        )
    
    def _on_error_occurred(self, event):
        """错误事件处理"""
        error_data = event.data
        logger.error(f"Error occurred: {error_data}")
        
        # 调用错误处理器
        for handler in self._error_handlers:
            try:
                handler(error_data)
            except Exception as e:
                logger.error(f"Error handler failed: {e}")
    
    # ==================== 运行 ====================
    
    def run(self):
        """运行应用程序"""
        if not self._initialized:
            logger.error("Application not initialized")
            return
        
        self._running = True
        logger.info(f"{self.APP_NAME} v{self.VERSION} is running")
        
        try:
            # 运行主循环（GUI或命令行）
            self._run_main_loop()
        except Exception as e:
            logger.error(f"Application error: {e}")
            logger.error(traceback.format_exc())
        finally:
            self._running = False
    
    def _run_main_loop(self):
        """运行主循环（由子类实现GUI版本）"""
        # 命令行版本的主循环
        logger.info("Running in command line mode")
        
        # 这里可以添加命令行交互逻辑
        # 或者由GUI子类重写此方法
        
        import time
        try:
            while self._running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
    
    # ==================== 关闭 ====================
    
    def shutdown(self):
        """关闭应用程序"""
        if not self._initialized:
            return
        
        logger.info("Shutting down application...")
        
        # 发布关闭事件
        self.publish_event(EventBus.EVENT_APP_CLOSING)
        
        # 停止异步事件处理
        if self._event_bus:
            self._event_bus.stop_async_processing()
        
        # 关闭插件
        if self._plugin_manager:
            self._plugin_manager.shutdown_all()
        
        # 保存配置
        if self._config_manager:
            self._config_manager.save_user_config()
        
        self._initialized = False
        self._running = False
        
        # 发布关闭完成事件
        self.publish_event(EventBus.EVENT_APP_CLOSED, {
            'uptime': self.uptime
        })
        
        logger.info("Application shutdown complete")
    
    # ==================== 公共方法 ====================
    
    def publish_event(self, event_type: str, data: Any = None):
        """发布事件"""
        if self._event_bus:
            self._event_bus.publish(event_type, data, "MainApplication")
    
    def get_service(self, service_name: str) -> Any:
        """获取服务"""
        if self._service_locator:
            return self._service_locator.get(service_name)
        return None
    
    def register_error_handler(self, handler: Callable):
        """注册错误处理器"""
        self._error_handlers.append(handler)
    
    def create_workflow(self, workflow_type: WorkflowType, 
                        input_data: Dict[str, Any] = None) -> Any:
        """
        创建工作流
        
        Args:
            workflow_type: 工作流类型
            input_data: 输入数据
            
        Returns:
            工作流实例
        """
        if not self._workflow_manager:
            return None
        
        workflow = self._workflow_manager.create_workflow(workflow_type)
        
        if input_data:
            workflow.context.input_data.update(input_data)
        
        return workflow
    
    def start_workflow(self, workflow: Any) -> bool:
        """启动工作流"""
        if not self._workflow_manager:
            return False
        return self._workflow_manager.start_workflow(workflow)
    
    def _handle_fatal_error(self, error: Exception):
        """处理致命错误"""
        logger.critical(f"Fatal error: {error}")
        
        # 保存恢复信息
        try:
            recovery_dir = Path.home() / '.casting3d' / 'recovery'
            recovery_dir.mkdir(parents=True, exist_ok=True)
            
            recovery_file = recovery_dir / f'recovery_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            recovery_data = {
                'timestamp': datetime.now().isoformat(),
                'error': str(error),
                'traceback': traceback.format_exc()
            }
            
            import json
            with open(recovery_file, 'w') as f:
                json.dump(recovery_data, f, indent=2)
            
            logger.info(f"Recovery info saved to {recovery_file}")
        except Exception as e:
            logger.error(f"Failed to save recovery info: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取应用程序统计信息"""
        return {
            'app_name': self.APP_NAME,
            'version': self.VERSION,
            'initialized': self._initialized,
            'running': self._running,
            'uptime': self.uptime,
            'event_bus': self._event_bus.get_stats() if self._event_bus else {},
            'plugins': self._plugin_manager.to_dict() if self._plugin_manager else {},
            'workflows': self._workflow_manager.to_dict() if self._workflow_manager else {}
        }


# 便捷函数
def create_application() -> MainApplication:
    """创建应用程序实例"""
    return MainApplication()


if __name__ == "__main__":
    # 测试代码
    print(f"{MainApplication.APP_NAME} v{MainApplication.VERSION}")
    print("=" * 50)
    
    app = create_application()
    
    if app.initialize():
        print("Application initialized successfully")
        print(f"Statistics: {app.get_statistics()}")
        
        # 运行一段时间后关闭
        import time
        time.sleep(1)
        
        app.shutdown()
        print("Application shutdown")
    else:
        print("Application initialization failed")
    
    print("\nTest completed!")
