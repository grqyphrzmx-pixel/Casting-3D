"""
工作流管理器模块

管理工作流状态和执行，支持完整的2D到3D转换流程。
实现状态机模式，提供可扩展的工作流框架。
"""

import logging
from typing import Dict, List, Callable, Any, Optional, Union
from enum import Enum, auto
from dataclasses import dataclass, field
from datetime import datetime
import threading
import uuid

from .event_bus import EventBus, EventPriority

logger = logging.getLogger(__name__)


class WorkflowState(Enum):
    """工作流状态"""
    IDLE = auto()
    INITIALIZING = auto()
    IMAGE_LOADING = auto()
    IMAGE_LOADED = auto()
    ANALYZING = auto()
    ANALYSIS_DONE = auto()
    MODELING = auto()
    MODEL_DONE = auto()
    APPLYING_RULES = auto()
    RULES_APPLIED = auto()
    EXPORTING = auto()
    COMPLETED = auto()
    CANCELLED = auto()
    FAILED = auto()


class WorkflowType(Enum):
    """工作流类型"""
    FULL = "full"                    # 完整流程：图像→分析→建模→导出
    ANALYSIS_ONLY = "analysis_only"  # 仅分析
    MODELING_ONLY = "modeling_only"  # 仅建模
    EXPORT_ONLY = "export_only"      # 仅导出
    RULES_ONLY = "rules_only"        # 仅应用规则


@dataclass
class WorkflowStep:
    """工作流步骤"""
    step_id: str
    name: str
    state: WorkflowState
    progress: float = 0.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: str = ""
    result: Any = None
    
    @property
    def duration(self) -> float:
        """获取步骤执行时间（秒）"""
        if self.start_time:
            end = self.end_time or datetime.now()
            return (end - self.start_time).total_seconds()
        return 0.0
    
    @property
    def is_completed(self) -> bool:
        return self.state in [WorkflowState.COMPLETED, WorkflowState.ANALYSIS_DONE,
                             WorkflowState.MODEL_DONE, WorkflowState.RULES_APPLIED]


@dataclass
class WorkflowContext:
    """工作流上下文数据"""
    workflow_id: str
    workflow_type: WorkflowType
    input_data: Dict[str, Any] = field(default_factory=dict)
    intermediate_results: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def set(self, key: str, value: Any):
        """设置中间结果"""
        self.intermediate_results[key] = value
    
    def get(self, key: str, default=None) -> Any:
        """获取中间结果"""
        return self.intermediate_results.get(key, default)


class Workflow:
    """
    工作流基类
    
    定义工作流的基本结构和行为。
    """
    
    def __init__(self, workflow_type: WorkflowType, context: WorkflowContext = None):
        self.workflow_id = str(uuid.uuid4())[:8]
        self.workflow_type = workflow_type
        self.context = context or WorkflowContext(self.workflow_id, workflow_type)
        
        self._state = WorkflowState.IDLE
        self._steps: List[WorkflowStep] = []
        self._current_step_index = -1
        self._state_handlers: Dict[WorkflowState, Callable] = {}
        self._transitions: Dict[WorkflowState, List[WorkflowState]] = {}
        
        self._cancelled = False
        self._failed = False
        self._error_message = ""
        
        self._on_state_changed: Optional[Callable] = None
        self._on_progress: Optional[Callable] = None
        self._on_completed: Optional[Callable] = None
        self._on_failed: Optional[Callable] = None
        
        self._lock = threading.Lock()
        
        self._setup_transitions()
        self._setup_handlers()
    
    def _setup_transitions(self):
        """设置状态转换规则"""
        self._transitions = {
            WorkflowState.IDLE: [WorkflowState.INITIALIZING],
            WorkflowState.INITIALIZING: [WorkflowState.IMAGE_LOADING, WorkflowState.ANALYZING],
            WorkflowState.IMAGE_LOADING: [WorkflowState.IMAGE_LOADED, WorkflowState.FAILED],
            WorkflowState.IMAGE_LOADED: [WorkflowState.ANALYZING, WorkflowState.MODELING],
            WorkflowState.ANALYZING: [WorkflowState.ANALYSIS_DONE, WorkflowState.FAILED],
            WorkflowState.ANALYSIS_DONE: [WorkflowState.MODELING, WorkflowState.COMPLETED],
            WorkflowState.MODELING: [WorkflowState.MODEL_DONE, WorkflowState.FAILED],
            WorkflowState.MODEL_DONE: [WorkflowState.APPLYING_RULES, WorkflowState.EXPORTING, WorkflowState.COMPLETED],
            WorkflowState.APPLYING_RULES: [WorkflowState.RULES_APPLIED, WorkflowState.FAILED],
            WorkflowState.RULES_APPLIED: [WorkflowState.EXPORTING, WorkflowState.COMPLETED],
            WorkflowState.EXPORTING: [WorkflowState.COMPLETED, WorkflowState.FAILED],
            WorkflowState.COMPLETED: [WorkflowState.IDLE],
            WorkflowState.CANCELLED: [WorkflowState.IDLE],
            WorkflowState.FAILED: [WorkflowState.IDLE]
        }
    
    def _setup_handlers(self):
        """设置状态处理器（子类重写）"""
        pass
    
    def register_state_handler(self, state: WorkflowState, handler: Callable):
        """注册状态处理器"""
        self._state_handlers[state] = handler
    
    def can_transition_to(self, new_state: WorkflowState) -> bool:
        """检查是否可以转换到目标状态"""
        return new_state in self._transitions.get(self._state, [])
    
    def transition_to(self, new_state: WorkflowState, data: Any = None) -> bool:
        """
        转换到新的状态
        
        Args:
            new_state: 目标状态
            data: 附加数据
            
        Returns:
            是否成功转换
        """
        with self._lock:
            if not self.can_transition_to(new_state):
                logger.warning(f"Invalid transition: {self._state.name} -> {new_state.name}")
                return False
            
            old_state = self._state
            self._state = new_state
            
            # 更新当前步骤
            if self._current_step_index >= 0 and self._current_step_index < len(self._steps):
                step = self._steps[self._current_step_index]
                step.end_time = datetime.now()
                step.result = data
            
            logger.info(f"Workflow {self.workflow_id}: {old_state.name} -> {new_state.name}")
            
            # 触发回调
            if self._on_state_changed:
                self._on_state_changed(old_state, new_state, data)
            
            # 执行状态处理器
            handler = self._state_handlers.get(new_state)
            if handler:
                try:
                    handler(data)
                except Exception as e:
                    logger.error(f"State handler error for {new_state.name}: {e}")
                    self._set_failed(str(e))
                    return False
            
            # 发布事件
            self._publish_state_event(old_state, new_state, data)
            
            return True
    
    def _publish_state_event(self, old_state: WorkflowState, new_state: WorkflowState, data: Any):
        """发布状态变更事件"""
        event_bus = EventBus()
        event_data = {
            'workflow_id': self.workflow_id,
            'workflow_type': self.workflow_type.value,
            'old_state': old_state.name,
            'new_state': new_state.name,
            'data': data
        }
        event_bus.publish(f"workflow.state_changed", event_data, "Workflow")
    
    def start(self, input_data: Dict[str, Any] = None) -> bool:
        """
        启动工作流
        
        Args:
            input_data: 输入数据
            
        Returns:
            是否成功启动
        """
        if self._state != WorkflowState.IDLE:
            logger.warning(f"Cannot start workflow from state {self._state.name}")
            return False
        
        if input_data:
            self.context.input_data.update(input_data)
        
        self._cancelled = False
        self._failed = False
        self._error_message = ""
        
        logger.info(f"Starting workflow {self.workflow_id} ({self.workflow_type.value})")
        
        return self.transition_to(WorkflowState.INITIALIZING)
    
    def cancel(self) -> bool:
        """取消工作流"""
        if self._state in [WorkflowState.COMPLETED, WorkflowState.CANCELLED, WorkflowState.FAILED]:
            return False
        
        self._cancelled = True
        logger.info(f"Workflow {self.workflow_id} cancelled")
        return self.transition_to(WorkflowState.CANCELLED)
    
    def _set_failed(self, error_message: str):
        """设置失败状态"""
        self._failed = True
        self._error_message = error_message
        logger.error(f"Workflow {self.workflow_id} failed: {error_message}")
        
        if self._on_failed:
            self._on_failed(error_message)
        
        self.transition_to(WorkflowState.FAILED)
    
    def add_step(self, name: str, state: WorkflowState) -> WorkflowStep:
        """添加步骤"""
        step = WorkflowStep(
            step_id=f"{self.workflow_id}_{len(self._steps)}",
            name=name,
            state=state
        )
        self._steps.append(step)
        return step
    
    def start_step(self, step_index: int) -> bool:
        """开始执行步骤"""
        if step_index < 0 or step_index >= len(self._steps):
            return False
        
        self._current_step_index = step_index
        step = self._steps[step_index]
        step.start_time = datetime.now()
        step.progress = 0.0
        
        logger.info(f"Starting step: {step.name}")
        return True
    
    def update_step_progress(self, progress: float, message: str = ""):
        """更新步骤进度"""
        if self._current_step_index >= 0 and self._current_step_index < len(self._steps):
            step = self._steps[self._current_step_index]
            step.progress = max(0.0, min(1.0, progress))
            
            if self._on_progress:
                self._on_progress(step, progress, message)
    
    @property
    def state(self) -> WorkflowState:
        return self._state
    
    @property
    def is_running(self) -> bool:
        return self._state not in [WorkflowState.IDLE, WorkflowState.COMPLETED, 
                                   WorkflowState.CANCELLED, WorkflowState.FAILED]
    
    @property
    def is_completed(self) -> bool:
        return self._state == WorkflowState.COMPLETED
    
    @property
    def is_failed(self) -> bool:
        return self._state == WorkflowState.FAILED
    
    @property
    def progress(self) -> float:
        """获取整体进度"""
        if not self._steps:
            return 0.0
        
        total_progress = sum(s.progress for s in self._steps)
        return total_progress / len(self._steps)
    
    def get_step_by_state(self, state: WorkflowState) -> Optional[WorkflowStep]:
        """根据状态获取步骤"""
        for step in self._steps:
            if step.state == state:
                return step
        return None
    
    def on_state_changed(self, callback: Callable):
        """设置状态变更回调"""
        self._on_state_changed = callback
    
    def on_progress(self, callback: Callable):
        """设置进度回调"""
        self._on_progress = callback
    
    def on_completed(self, callback: Callable):
        """设置完成回调"""
        self._on_completed = callback
    
    def on_failed(self, callback: Callable):
        """设置失败回调"""
        self._on_failed = callback
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'workflow_id': self.workflow_id,
            'workflow_type': self.workflow_type.value,
            'state': self._state.name,
            'progress': self.progress,
            'steps': [
                {
                    'name': s.name,
                    'state': s.state.name,
                    'progress': s.progress,
                    'duration': s.duration
                }
                for s in self._steps
            ],
            'cancelled': self._cancelled,
            'failed': self._failed,
            'error_message': self._error_message
        }


class FullConversionWorkflow(Workflow):
    """
    完整转换工作流
    
    执行从图像加载到导出的完整流程。
    """
    
    def __init__(self, context: WorkflowContext = None):
        super().__init__(WorkflowType.FULL, context)
        
        # 添加步骤
        self.add_step("初始化", WorkflowState.INITIALIZING)
        self.add_step("加载图像", WorkflowState.IMAGE_LOADING)
        self.add_step("分析图像", WorkflowState.ANALYZING)
        self.add_step("创建3D模型", WorkflowState.MODELING)
        self.add_step("应用铸造规则", WorkflowState.APPLYING_RULES)
        self.add_step("导出模型", WorkflowState.EXPORTING)
    
    def _setup_handlers(self):
        """设置状态处理器"""
        self.register_state_handler(WorkflowState.INITIALIZING, self._on_initializing)
        self.register_state_handler(WorkflowState.IMAGE_LOADING, self._on_image_loading)
        self.register_state_handler(WorkflowState.ANALYZING, self._on_analyzing)
        self.register_state_handler(WorkflowState.MODELING, self._on_modeling)
        self.register_state_handler(WorkflowState.APPLYING_RULES, self._on_applying_rules)
        self.register_state_handler(WorkflowState.EXPORTING, self._on_exporting)
    
    def _on_initializing(self, data: Any):
        """初始化处理"""
        self.start_step(0)
        self.update_step_progress(1.0, "初始化完成")
        self.transition_to(WorkflowState.IMAGE_LOADING)
    
    def _on_image_loading(self, data: Any):
        """图像加载处理"""
        self.start_step(1)
        # 图像加载逻辑由外部实现
        pass
    
    def _on_analyzing(self, data: Any):
        """分析处理"""
        self.start_step(2)
        # 分析逻辑由外部实现
        pass
    
    def _on_modeling(self, data: Any):
        """建模处理"""
        self.start_step(3)
        # 建模逻辑由外部实现
        pass
    
    def _on_applying_rules(self, data: Any):
        """规则应用处理"""
        self.start_step(4)
        # 规则应用逻辑由外部实现
        pass
    
    def _on_exporting(self, data: Any):
        """导出处理"""
        self.start_step(5)
        # 导出逻辑由外部实现
        pass


class WorkflowManager:
    """
    工作流管理器
    
    管理工作流的创建、执行和监控。
    单例模式实现。
    """
    
    _instance = None
    _lock = threading.Lock()
    
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
        
        self._workflows: Dict[str, Workflow] = {}
        self._active_workflow: Optional[Workflow] = None
        self._workflow_history: List[str] = []
        self._max_history = 50
        
        self._event_bus = EventBus()
        self._lock = threading.Lock()
        
        self._initialized = True
        logger.info("WorkflowManager initialized")
    
    def create_workflow(self, workflow_type: WorkflowType, 
                        context: WorkflowContext = None) -> Workflow:
        """
        创建工作流
        
        Args:
            workflow_type: 工作流类型
            context: 工作流上下文
            
        Returns:
            工作流实例
        """
        if workflow_type == WorkflowType.FULL:
            workflow = FullConversionWorkflow(context)
        else:
            workflow = Workflow(workflow_type, context)
        
        with self._lock:
            self._workflows[workflow.workflow_id] = workflow
            self._workflow_history.append(workflow.workflow_id)
            
            if len(self._workflow_history) > self._max_history:
                old_id = self._workflow_history.pop(0)
                if old_id in self._workflows:
                    del self._workflows[old_id]
        
        logger.info(f"Created workflow: {workflow.workflow_id} ({workflow_type.value})")
        return workflow
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """获取工作流"""
        return self._workflows.get(workflow_id)
    
    def get_active_workflow(self) -> Optional[Workflow]:
        """获取当前活动工作流"""
        return self._active_workflow
    
    def start_workflow(self, workflow: Workflow, input_data: Dict[str, Any] = None) -> bool:
        """
        启动工作流
        
        Args:
            workflow: 工作流实例
            input_data: 输入数据
            
        Returns:
            是否成功启动
        """
        with self._lock:
            if self._active_workflow and self._active_workflow.is_running:
                logger.warning("Another workflow is already running")
                return False
            
            self._active_workflow = workflow
        
        # 订阅工作流事件
        workflow.on_state_changed(self._on_workflow_state_changed)
        
        return workflow.start(input_data)
    
    def _on_workflow_state_changed(self, old_state: WorkflowState, 
                                   new_state: WorkflowState, data: Any):
        """工作流状态变更处理"""
        if new_state == WorkflowState.COMPLETED:
            logger.info("Workflow completed successfully")
        elif new_state == WorkflowState.FAILED:
            logger.error("Workflow failed")
        elif new_state == WorkflowState.CANCELLED:
            logger.info("Workflow cancelled")
    
    def cancel_active_workflow(self) -> bool:
        """取消当前活动工作流"""
        if self._active_workflow and self._active_workflow.is_running:
            return self._active_workflow.cancel()
        return False
    
    def get_all_workflows(self) -> List[Workflow]:
        """获取所有工作流"""
        return list(self._workflows.values())
    
    def get_running_workflows(self) -> List[Workflow]:
        """获取正在运行的工作流"""
        return [w for w in self._workflows.values() if w.is_running]
    
    def cleanup_completed(self):
        """清理已完成的工作流"""
        with self._lock:
            completed_ids = [
                wid for wid, w in self._workflows.items()
                if w.state in [WorkflowState.COMPLETED, WorkflowState.CANCELLED, WorkflowState.FAILED]
            ]
            for wid in completed_ids:
                del self._workflows[wid]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'active_workflow': self._active_workflow.workflow_id if self._active_workflow else None,
            'total_workflows': len(self._workflows),
            'running_workflows': len(self.get_running_workflows()),
            'workflows': [w.to_dict() for w in self._workflows.values()]
        }


# 便捷函数
def get_workflow_manager() -> WorkflowManager:
    """获取工作流管理器实例"""
    return WorkflowManager()


def create_full_workflow(input_data: Dict[str, Any] = None) -> Workflow:
    """便捷函数：创建完整转换工作流"""
    manager = WorkflowManager()
    workflow = manager.create_workflow(WorkflowType.FULL)
    return workflow


if __name__ == "__main__":
    # 测试代码
    print("WorkflowManager Test")
    print("=" * 50)
    
    manager = WorkflowManager()
    
    # 创建工作流
    workflow = manager.create_workflow(WorkflowType.FULL)
    print(f"Created workflow: {workflow.workflow_id}")
    print(f"Initial state: {workflow.state.name}")
    
    # 测试状态转换
    workflow.start({'image_path': '/test/image.jpg'})
    print(f"After start: {workflow.state.name}")
    
    # 模拟状态转换
    workflow.transition_to(WorkflowState.IMAGE_LOADED)
    print(f"After image loaded: {workflow.state.name}")
    
    workflow.transition_to(WorkflowState.ANALYSIS_DONE)
    print(f"After analysis: {workflow.state.name}")
    
    workflow.transition_to(WorkflowState.MODEL_DONE)
    print(f"After modeling: {workflow.state.name}")
    
    workflow.transition_to(WorkflowState.COMPLETED)
    print(f"Final state: {workflow.state.name}")
    
    print(f"\nWorkflow progress: {workflow.progress:.1%}")
    
    print("\nTest completed!")
