"""
核心组件模块

提供应用程序的核心功能组件：
- event_bus: 事件总线，用于模块间通信
- workflow_manager: 工作流管理器，管理工作流状态和执行
- config_manager: 配置管理器，管理应用程序配置
- plugin_manager: 插件管理器，管理插件系统
"""

from .event_bus import (
    EventBus,
    Event,
    EventPriority,
    EventSubscription,
    get_event_bus,
    publish_event,
    subscribe_event,
    EventListener
)

from .workflow_manager import (
    WorkflowManager,
    Workflow,
    WorkflowState,
    WorkflowType,
    WorkflowContext,
    WorkflowStep,
    FullConversionWorkflow,
    get_workflow_manager,
    create_full_workflow
)

from .config_manager import (
    ConfigManager,
    ConfigLevel,
    ImageAnalysisConfig,
    ModelingConfig,
    ExportConfig,
    CastingConfig,
    UIConfig,
    get_config_manager,
    get_config,
    set_config
)

from .plugin_manager import (
    PluginManager,
    IPlugin,
    IImageProcessorPlugin,
    IFeatureRecognizerPlugin,
    IExporterPlugin,
    ICastingRulePlugin,
    PluginInfo,
    get_plugin_manager,
    register_image_processor,
    get_image_processors
)

from .module_adapter import (
    ModuleAdapterManager,
    ImageAnalysisAdapter,
    ModelingEngineAdapter,
    CADExportAdapter,
    CastingRulesAdapter,
    get_module_adapter
)

__all__ = [
    # Event Bus
    'EventBus',
    'Event',
    'EventPriority',
    'EventSubscription',
    'get_event_bus',
    'publish_event',
    'subscribe_event',
    'EventListener',
    
    # Workflow Manager
    'WorkflowManager',
    'Workflow',
    'WorkflowState',
    'WorkflowType',
    'WorkflowContext',
    'WorkflowStep',
    'FullConversionWorkflow',
    'get_workflow_manager',
    'create_full_workflow',
    
    # Config Manager
    'ConfigManager',
    'ConfigLevel',
    'ImageAnalysisConfig',
    'ModelingConfig',
    'ExportConfig',
    'CastingConfig',
    'UIConfig',
    'get_config_manager',
    'get_config',
    'set_config',
    
    # Plugin Manager
    'PluginManager',
    'IPlugin',
    'IImageProcessorPlugin',
    'IFeatureRecognizerPlugin',
    'IExporterPlugin',
    'ICastingRulePlugin',
    'PluginInfo',
    'get_plugin_manager',
    'register_image_processor',
    'get_image_processors',
    
    # Module Adapter
    'ModuleAdapterManager',
    'ImageAnalysisAdapter',
    'ModelingEngineAdapter',
    'CADExportAdapter',
    'CastingRulesAdapter',
    'get_module_adapter'
]
