"""
命令系统模块

实现命令模式以支持撤销/重做功能
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

from .types import FeatureParameters
from .geometry_kernel import GeometryKernel
from .feature_base import Feature, FeatureFactory

logger = logging.getLogger(__name__)


class Command(ABC):
    """
    命令基类
    实现命令模式以支持撤销/重做
    """
    
    def __init__(self, name: str = ""):
        self._name = name
        self._is_executed = False
        self._timestamp: Optional[datetime] = None
        self._metadata: Dict[str, Any] = {}
    
    @property
    def name(self) -> str:
        """命令名称"""
        return self._name
    
    @property
    def is_executed(self) -> bool:
        """是否已执行"""
        return self._is_executed
    
    @property
    def timestamp(self) -> Optional[datetime]:
        """执行时间戳"""
        return self._timestamp
    
    def set_metadata(self, key: str, value: Any):
        """设置元数据"""
        self._metadata[key] = value
    
    def get_metadata(self, key: str) -> Any:
        """获取元数据"""
        return self._metadata.get(key)
    
    @abstractmethod
    def execute(self) -> bool:
        """执行命令"""
        pass
    
    @abstractmethod
    def undo(self) -> bool:
        """撤销命令"""
        pass
    
    @abstractmethod
    def redo(self) -> bool:
        """重做命令"""
        pass
    
    def _mark_executed(self):
        """标记为已执行"""
        self._is_executed = True
        self._timestamp = datetime.now()
    
    def _mark_undone(self):
        """标记为已撤销"""
        self._is_executed = False
    
    def __repr__(self) -> str:
        status = "executed" if self._is_executed else "pending"
        return f"Command({self._name}, {status})"


class CreateFeatureCommand(Command):
    """创建特征命令"""
    
    def __init__(self, feature_manager: 'FeatureManager',
                 params: FeatureParameters,
                 kernel: GeometryKernel,
                 name: str = None):
        if name is None:
            name = f"Create {params.feature_type.name}"
        super().__init__(name)
        self._feature_manager = feature_manager
        self._params = params
        self._kernel = kernel
        self._feature: Optional[Feature] = None
    
    def execute(self) -> bool:
        try:
            self._feature = FeatureFactory.create(
                self._params.feature_type, self._params, self._kernel)
            
            if self._feature is None:
                logger.error("Failed to create feature")
                return False
            
            self._feature_manager.add_feature(self._feature)
            result = self._feature.build()
            
            if result is None and not self._params.is_suppressed:
                # 构建失败，回滚
                self._feature_manager.remove_feature(self._feature.feature_id)
                logger.error("Feature build failed")
                return False
            
            self._mark_executed()
            logger.info(f"Created feature: {self._feature.feature_id[:8]}")
            return True
            
        except Exception as e:
            logger.error(f"Create feature command failed: {e}")
            return False
    
    def undo(self) -> bool:
        if self._feature:
            self._feature_manager.remove_feature(self._feature.feature_id)
            self._mark_undone()
            logger.info(f"Undone create feature: {self._feature.feature_id[:8]}")
            return True
        return False
    
    def redo(self) -> bool:
        return self.execute()
    
    def get_created_feature(self) -> Optional[Feature]:
        """获取创建的特征"""
        return self._feature


class DeleteFeatureCommand(Command):
    """删除特征命令"""
    
    def __init__(self, feature_manager: 'FeatureManager',
                 feature_id: str,
                 name: str = "Delete Feature"):
        super().__init__(name)
        self._feature_manager = feature_manager
        self._feature_id = feature_id
        self._deleted_feature: Optional[Feature] = None
        self._deleted_children: List[Feature] = []
    
    def execute(self) -> bool:
        self._deleted_feature = self._feature_manager.get_feature(self._feature_id)
        
        if self._deleted_feature is None:
            logger.error(f"Feature not found: {self._feature_id[:8]}")
            return False
        
        # 保存所有子特征
        self._deleted_children = self._deleted_feature.get_all_descendants()
        
        # 删除特征（会级联删除子特征）
        self._feature_manager.remove_feature(self._feature_id)
        
        self._mark_executed()
        logger.info(f"Deleted feature: {self._feature_id[:8]} "
                   f"(with {len(self._deleted_children)} children)")
        return True
    
    def undo(self) -> bool:
        if self._deleted_feature:
            # 恢复特征
            self._feature_manager.add_feature(self._deleted_feature)
            
            # 恢复子特征
            for child in self._deleted_children:
                self._feature_manager.add_feature(child)
            
            self._mark_undone()
            logger.info(f"Restored feature: {self._feature_id[:8]}")
            return True
        return False
    
    def redo(self) -> bool:
        return self.execute()
    
    def get_deleted_feature(self) -> Optional[Feature]:
        """获取删除的特征"""
        return self._deleted_feature


class ModifyFeatureCommand(Command):
    """修改特征命令"""
    
    def __init__(self, feature: Feature, new_params: FeatureParameters,
                 name: str = "Modify Feature"):
        super().__init__(name)
        self._feature = feature
        self._old_params = feature.parameters
        self._new_params = new_params
        self._old_shape_id: Optional[str] = None
    
    def execute(self) -> bool:
        try:
            # 保存旧形状ID
            self._old_shape_id = self._feature.result_shape_id
            
            # 应用新参数
            self._feature.parameters = self._new_params
            result = self._feature.update()
            
            self._mark_executed()
            logger.info(f"Modified feature: {self._feature.feature_id[:8]}")
            return True
            
        except Exception as e:
            logger.error(f"Modify feature command failed: {e}")
            return False
    
    def undo(self) -> bool:
        try:
            # 恢复旧参数
            self._feature.parameters = self._old_params
            self._feature.update()
            
            self._mark_undone()
            logger.info(f"Undone modify feature: {self._feature.feature_id[:8]}")
            return True
            
        except Exception as e:
            logger.error(f"Undo modify feature failed: {e}")
            return False
    
    def redo(self) -> bool:
        return self.execute()


class SuppressFeatureCommand(Command):
    """抑制特征命令"""
    
    def __init__(self, feature: Feature, name: str = "Suppress Feature"):
        super().__init__(name)
        self._feature = feature
        self._was_suppressed = feature.is_suppressed
    
    def execute(self) -> bool:
        if not self._was_suppressed:
            self._feature.suppress()
            self._feature.update()
            self._mark_executed()
            logger.info(f"Suppressed feature: {self._feature.feature_id[:8]}")
            return True
        return False
    
    def undo(self) -> bool:
        if not self._was_suppressed:
            self._feature.unsuppress()
            self._feature.update()
            self._mark_undone()
            logger.info(f"Unsuppressed feature: {self._feature.feature_id[:8]}")
            return True
        return False
    
    def redo(self) -> bool:
        return self.execute()


class UnsuppressFeatureCommand(Command):
    """取消抑制特征命令"""
    
    def __init__(self, feature: Feature, name: str = "Unsuppress Feature"):
        super().__init__(name)
        self._feature = feature
        self._was_suppressed = feature.is_suppressed
    
    def execute(self) -> bool:
        if self._was_suppressed:
            self._feature.unsuppress()
            self._feature.update()
            self._mark_executed()
            logger.info(f"Unsuppressed feature: {self._feature.feature_id[:8]}")
            return True
        return False
    
    def undo(self) -> bool:
        if self._was_suppressed:
            self._feature.suppress()
            self._feature.update()
            self._mark_undone()
            logger.info(f"Suppressed feature: {self._feature.feature_id[:8]}")
            return True
        return False
    
    def redo(self) -> bool:
        return self.execute()


class CompositeCommand(Command):
    """复合命令（宏命令）"""
    
    def __init__(self, name: str = "Composite Command"):
        super().__init__(name)
        self._commands: List[Command] = []
    
    def add_command(self, command: Command):
        """添加子命令"""
        self._commands.append(command)
    
    def execute(self) -> bool:
        executed = []
        try:
            for cmd in self._commands:
                if not cmd.execute():
                    # 回滚已执行的命令
                    for executed_cmd in reversed(executed):
                        executed_cmd.undo()
                    return False
                executed.append(cmd)
            
            self._mark_executed()
            return True
            
        except Exception as e:
            logger.error(f"Composite command failed: {e}")
            # 回滚
            for executed_cmd in reversed(executed):
                executed_cmd.undo()
            return False
    
    def undo(self) -> bool:
        try:
            # 逆序撤销所有子命令
            for cmd in reversed(self._commands):
                if cmd.is_executed:
                    cmd.undo()
            
            self._mark_undone()
            return True
            
        except Exception as e:
            logger.error(f"Undo composite command failed: {e}")
            return False
    
    def redo(self) -> bool:
        return self.execute()


class CommandManager:
    """
    命令管理器
    管理命令历史，支持撤销/重做
    """
    
    def __init__(self, max_history: int = 100):
        self._history: List[Command] = []
        self._current_index = -1
        self._max_history = max_history
        self._transaction_level = 0
        self._transaction_commands: List[Command] = []
    
    def execute(self, command: Command) -> bool:
        """执行命令"""
        # 如果在事务中，添加到事务
        if self._transaction_level > 0:
            self._transaction_commands.append(command)
            return True
        
        if command.execute():
            # 移除当前位置之后的命令
            self._history = self._history[:self._current_index + 1]
            
            # 添加新命令
            self._history.append(command)
            self._current_index += 1
            
            # 限制历史大小
            if len(self._history) > self._max_history:
                self._history.pop(0)
                self._current_index -= 1
            
            return True
        return False
    
    def begin_transaction(self, name: str = "Transaction"):
        """开始事务"""
        if self._transaction_level == 0:
            self._transaction_commands = []
        self._transaction_level += 1
        logger.debug(f"Begin transaction: {name} (level {self._transaction_level})")
    
    def end_transaction(self, name: str = "Transaction") -> bool:
        """结束事务"""
        if self._transaction_level > 0:
            self._transaction_level -= 1
            
            if self._transaction_level == 0 and self._transaction_commands:
                # 创建复合命令
                composite = CompositeCommand(name)
                for cmd in self._transaction_commands:
                    composite.add_command(cmd)
                
                self._transaction_commands = []
                return self.execute(composite)
            
            logger.debug(f"End transaction: {name} (level {self._transaction_level})")
            return True
        return False
    
    def cancel_transaction(self):
        """取消事务"""
        if self._transaction_level > 0:
            # 撤销事务中的所有命令
            for cmd in reversed(self._transaction_commands):
                if cmd.is_executed:
                    cmd.undo()
            
            self._transaction_commands = []
            self._transaction_level = 0
            logger.debug("Transaction cancelled")
    
    def can_undo(self) -> bool:
        """检查是否可以撤销"""
        return self._current_index >= 0
    
    def undo(self) -> bool:
        """撤销上一个命令"""
        if self.can_undo():
            command = self._history[self._current_index]
            if command.undo():
                self._current_index -= 1
                logger.info(f"Undo: {command.name}")
                return True
        return False
    
    def can_redo(self) -> bool:
        """检查是否可以重做"""
        return self._current_index < len(self._history) - 1
    
    def redo(self) -> bool:
        """重做下一个命令"""
        if self.can_redo():
            self._current_index += 1
            command = self._history[self._current_index]
            result = command.redo()
            if result:
                logger.info(f"Redo: {command.name}")
            return result
        return False
    
    def clear(self):
        """清空历史"""
        self._history.clear()
        self._current_index = -1
        self._transaction_commands = []
        self._transaction_level = 0
        logger.info("Command history cleared")
    
    def get_history(self) -> List[str]:
        """获取命令历史列表"""
        return [cmd.name for cmd in self._history]
    
    def get_history_with_status(self) -> List[Dict[str, Any]]:
        """获取带状态的命令历史"""
        return [
            {
                'name': cmd.name,
                'executed': cmd.is_executed,
                'timestamp': cmd.timestamp,
                'is_current': i == self._current_index
            }
            for i, cmd in enumerate(self._history)
        ]
    
    def get_current_command(self) -> Optional[Command]:
        """获取当前命令"""
        if 0 <= self._current_index < len(self._history):
            return self._history[self._current_index]
        return None
    
    def jump_to(self, index: int) -> bool:
        """跳转到指定历史位置"""
        if index < -1 or index >= len(self._history):
            return False
        
        # 撤销或重做到目标位置
        while self._current_index > index:
            self.undo()
        while self._current_index < index:
            self.redo()
        
        return True
