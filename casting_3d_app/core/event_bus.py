"""
事件总线模块

实现发布-订阅模式，用于模块间的松耦合通信。
支持同步和异步事件处理，事件优先级管理，以及事件日志记录。
"""

import logging
import threading
import queue
from typing import Dict, List, Callable, Any, Optional
from enum import Enum, auto
from dataclasses import dataclass
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class EventPriority(Enum):
    """事件优先级"""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


@dataclass
class Event:
    """事件数据类"""
    event_type: str
    data: Any
    source: str
    timestamp: datetime
    priority: EventPriority
    event_id: str
    
    def __init__(self, event_type: str, data: Any = None, 
                 source: str = "", priority: EventPriority = EventPriority.NORMAL):
        self.event_type = event_type
        self.data = data
        self.source = source
        self.timestamp = datetime.now()
        self.priority = priority
        self.event_id = str(uuid.uuid4())[:8]


class EventSubscription:
    """事件订阅"""
    
    def __init__(self, event_type: str, callback: Callable, 
                 priority: EventPriority = EventPriority.NORMAL,
                 filter_func: Callable = None):
        self.event_type = event_type
        self.callback = callback
        self.priority = priority
        self.filter_func = filter_func
        self.active = True
        self.call_count = 0
        self.created_at = datetime.now()
    
    def matches(self, event: Event) -> bool:
        """检查事件是否匹配订阅"""
        if not self.active:
            return False
        if self.event_type != event.event_type:
            return False
        if self.filter_func and not self.filter_func(event):
            return False
        return True
    
    def invoke(self, event: Event):
        """调用回调函数"""
        try:
            self.callback(event)
            self.call_count += 1
        except Exception as e:
            logger.error(f"Event callback error for {self.event_type}: {e}")


class EventBus:
    """
    事件总线
    
    单例模式实现，提供全局事件发布和订阅功能。
    
    使用示例:
        # 订阅事件
        def on_image_loaded(event):
            print(f"Image loaded: {event.data}")
        
        event_bus = EventBus()
        subscription = event_bus.subscribe("image.loaded", on_image_loaded)
        
        # 发布事件
        event_bus.publish("image.loaded", {"path": "/path/to/image.jpg"})
        
        # 取消订阅
        event_bus.unsubscribe(subscription)
    """
    
    _instance = None
    _lock = threading.Lock()
    
    # 预定义事件类型
    EVENT_IMAGE_LOADED = "image.loaded"
    EVENT_IMAGE_ANALYSIS_STARTED = "image.analysis.started"
    EVENT_IMAGE_ANALYSIS_PROGRESS = "image.analysis.progress"
    EVENT_IMAGE_ANALYSIS_COMPLETED = "image.analysis.completed"
    EVENT_IMAGE_ANALYSIS_FAILED = "image.analysis.failed"
    
    EVENT_MODEL_CREATION_STARTED = "model.creation.started"
    EVENT_MODEL_CREATION_PROGRESS = "model.creation.progress"
    EVENT_MODEL_CREATED = "model.created"
    EVENT_MODEL_UPDATED = "model.updated"
    EVENT_MODEL_CREATION_FAILED = "model.creation.failed"
    
    EVENT_EXPORT_STARTED = "export.started"
    EVENT_EXPORT_PROGRESS = "export.progress"
    EVENT_EXPORT_COMPLETED = "export.completed"
    EVENT_EXPORT_FAILED = "export.failed"
    
    EVENT_FEATURE_SELECTED = "feature.selected"
    EVENT_FEATURE_MODIFIED = "feature.modified"
    EVENT_FEATURE_DELETED = "feature.deleted"
    
    EVENT_UNDO = "undo"
    EVENT_REDO = "redo"
    
    EVENT_SETTINGS_CHANGED = "settings.changed"
    EVENT_PLUGIN_LOADED = "plugin.loaded"
    EVENT_PLUGIN_UNLOADED = "plugin.unloaded"
    
    EVENT_ERROR_OCCURRED = "error.occurred"
    EVENT_WARNING = "warning"
    EVENT_INFO = "info"
    
    EVENT_APP_STARTED = "app.started"
    EVENT_APP_CLOSING = "app.closing"
    EVENT_APP_CLOSED = "app.closed"
    
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
        
        self._subscriptions: Dict[str, List[EventSubscription]] = {}
        self._event_history: List[Event] = []
        self._max_history = 1000
        self._history_enabled = True
        
        # 异步处理
        self._async_queue: queue.Queue = queue.Queue()
        self._async_thread: Optional[threading.Thread] = None
        self._async_running = False
        
        # 统计
        self._stats = {
            'published': 0,
            'delivered': 0,
            'dropped': 0
        }
        
        self._initialized = True
        logger.info("EventBus initialized")
    
    def subscribe(self, event_type: str, callback: Callable,
                  priority: EventPriority = EventPriority.NORMAL,
                  filter_func: Callable = None) -> EventSubscription:
        """
        订阅事件
        
        Args:
            event_type: 事件类型
            callback: 回调函数，接收Event参数
            priority: 订阅优先级
            filter_func: 可选的过滤函数
            
        Returns:
            订阅对象，用于取消订阅
        """
        if event_type not in self._subscriptions:
            self._subscriptions[event_type] = []
        
        subscription = EventSubscription(event_type, callback, priority, filter_func)
        self._subscriptions[event_type].append(subscription)
        
        # 按优先级排序
        self._subscriptions[event_type].sort(key=lambda s: s.priority.value)
        
        logger.debug(f"Subscribed to {event_type}")
        return subscription
    
    def unsubscribe(self, subscription: EventSubscription) -> bool:
        """
        取消订阅
        
        Args:
            subscription: 订阅对象
            
        Returns:
            是否成功取消
        """
        if subscription.event_type in self._subscriptions:
            subscription.active = False
            if subscription in self._subscriptions[subscription.event_type]:
                self._subscriptions[subscription.event_type].remove(subscription)
                logger.debug(f"Unsubscribed from {subscription.event_type}")
                return True
        return False
    
    def publish(self, event_type: str, data: Any = None,
                source: str = "", priority: EventPriority = EventPriority.NORMAL,
                async_delivery: bool = False) -> Event:
        """
        发布事件
        
        Args:
            event_type: 事件类型
            data: 事件数据
            source: 事件来源
            priority: 事件优先级
            async_delivery: 是否异步投递
            
        Returns:
            创建的事件对象
        """
        event = Event(event_type, data, source, priority)
        
        # 记录历史
        if self._history_enabled:
            self._event_history.append(event)
            if len(self._event_history) > self._max_history:
                self._event_history.pop(0)
        
        self._stats['published'] += 1
        
        if async_delivery:
            self._async_queue.put(event)
        else:
            self._deliver_event(event)
        
        return event
    
    def _deliver_event(self, event: Event):
        """投递事件到订阅者"""
        if event.event_type not in self._subscriptions:
            return
        
        subscriptions = self._subscriptions[event.event_type]
        delivered = 0
        
        for subscription in subscriptions:
            if subscription.matches(event):
                subscription.invoke(event)
                delivered += 1
        
        self._stats['delivered'] += delivered
        
        if delivered == 0:
            self._stats['dropped'] += 1
            logger.debug(f"Event {event.event_type} dropped (no subscribers)")
    
    def start_async_processing(self):
        """启动异步事件处理"""
        if self._async_running:
            return
        
        self._async_running = True
        self._async_thread = threading.Thread(target=self._async_loop, daemon=True)
        self._async_thread.start()
        logger.info("Async event processing started")
    
    def stop_async_processing(self):
        """停止异步事件处理"""
        self._async_running = False
        if self._async_thread:
            self._async_thread.join(timeout=2.0)
        logger.info("Async event processing stopped")
    
    def _async_loop(self):
        """异步事件处理循环"""
        while self._async_running:
            try:
                event = self._async_queue.get(timeout=0.1)
                self._deliver_event(event)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Async event processing error: {e}")
    
    def get_event_history(self, event_type: str = None, 
                          limit: int = 100) -> List[Event]:
        """
        获取事件历史
        
        Args:
            event_type: 事件类型过滤，None表示所有类型
            limit: 最大返回数量
            
        Returns:
            事件列表
        """
        history = self._event_history
        if event_type:
            history = [e for e in history if e.event_type == event_type]
        return history[-limit:]
    
    def clear_history(self):
        """清除事件历史"""
        self._event_history.clear()
        logger.info("Event history cleared")
    
    def enable_history(self, enabled: bool = True):
        """启用/禁用事件历史记录"""
        self._history_enabled = enabled
        if not enabled:
            self.clear_history()
    
    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        return self._stats.copy()
    
    def reset_stats(self):
        """重置统计信息"""
        self._stats = {'published': 0, 'delivered': 0, 'dropped': 0}
    
    def has_subscribers(self, event_type: str) -> bool:
        """检查是否有订阅者"""
        return event_type in self._subscriptions and len(self._subscriptions[event_type]) > 0
    
    def get_subscriber_count(self, event_type: str = None) -> int:
        """
        获取订阅者数量
        
        Args:
            event_type: 事件类型，None表示所有类型
            
        Returns:
            订阅者数量
        """
        if event_type:
            return len(self._subscriptions.get(event_type, []))
        return sum(len(subs) for subs in self._subscriptions.values())
    
    def wait_for_event(self, event_type: str, timeout: float = None) -> Optional[Event]:
        """
        等待特定事件（阻塞调用）
        
        Args:
            event_type: 事件类型
            timeout: 超时时间（秒）
            
        Returns:
            事件对象，超时返回None
        """
        result = [None]
        event_received = threading.Event()
        
        def callback(event):
            result[0] = event
            event_received.set()
        
        subscription = self.subscribe(event_type, callback)
        
        try:
            if event_received.wait(timeout):
                return result[0]
        finally:
            self.unsubscribe(subscription)
        
        return None


# 便捷函数
def get_event_bus() -> EventBus:
    """获取事件总线实例"""
    return EventBus()


def publish_event(event_type: str, data: Any = None, source: str = ""):
    """便捷函数：发布事件"""
    return EventBus().publish(event_type, data, source)


def subscribe_event(event_type: str, callback: Callable) -> EventSubscription:
    """便捷函数：订阅事件"""
    return EventBus().subscribe(event_type, callback)


# 装饰器模式支持
class EventListener:
    """事件监听器装饰器"""
    
    def __init__(self, event_type: str, priority: EventPriority = EventPriority.NORMAL):
        self.event_type = event_type
        self.priority = priority
        self.subscription = None
    
    def __call__(self, func):
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        # 自动订阅
        bus = EventBus()
        self.subscription = bus.subscribe(self.event_type, func, self.priority)
        
        wrapper._event_subscription = self.subscription
        return wrapper


if __name__ == "__main__":
    # 测试代码
    print("EventBus Test")
    print("=" * 50)
    
    bus = EventBus()
    
    # 测试订阅和发布
    received_events = []
    
    def on_test_event(event):
        received_events.append(event.data)
        print(f"Received: {event.data}")
    
    sub = bus.subscribe("test.event", on_test_event)
    
    bus.publish("test.event", "Hello World!")
    bus.publish("test.event", {"key": "value"})
    
    print(f"\nTotal received: {len(received_events)}")
    
    # 测试统计
    stats = bus.get_stats()
    print(f"Stats: {stats}")
    
    # 取消订阅
    bus.unsubscribe(sub)
    bus.publish("test.event", "This should not be received")
    
    print(f"After unsubscribe, received: {len(received_events)}")
    
    print("\nTest completed!")
