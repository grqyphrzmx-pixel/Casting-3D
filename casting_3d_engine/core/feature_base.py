"""
特征基类和工厂模块

定义所有建模特征的抽象基类和特征工厂
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any

from .types import FeatureType, FeatureParameters
from .geometry_kernel import GeometryKernel

logger = logging.getLogger(__name__)


class Feature(ABC):
    """
    特征基类
    所有建模特征的抽象基类
    """
    
    def __init__(self, params: FeatureParameters, kernel: GeometryKernel):
        self._params = params
        self._kernel = kernel
        self._result_shape_id: Optional[str] = None
        self._children: List['Feature'] = []
        self._parent: Optional['Feature'] = None
        self._is_dirty: bool = True
        
    @property
    def feature_id(self) -> str:
        """特征唯一标识"""
        return self._params.feature_id
    
    @property
    def feature_type(self) -> FeatureType:
        """特征类型"""
        return self._params.feature_type
    
    @property
    def parameters(self) -> FeatureParameters:
        """特征参数"""
        return self._params
    
    @parameters.setter
    def parameters(self, params: FeatureParameters):
        """设置特征参数"""
        self._params = params
        self._is_dirty = True
    
    @property
    def result_shape_id(self) -> Optional[str]:
        """生成的形状ID"""
        return self._result_shape_id
    
    @property
    def is_dirty(self) -> bool:
        """是否需要更新"""
        return self._is_dirty
    
    @property
    def is_suppressed(self) -> bool:
        """是否被抑制"""
        return self._params.is_suppressed
    
    @property
    def parent(self) -> Optional['Feature']:
        """父特征"""
        return self._parent
    
    @property
    def children(self) -> List['Feature']:
        """子特征列表"""
        return self._children.copy()
    
    def add_child(self, feature: 'Feature'):
        """添加子特征"""
        if feature not in self._children:
            self._children.append(feature)
            feature._parent = self
            logger.debug(f"Added child {feature.feature_id[:8]} to {self.feature_id[:8]}")
    
    def remove_child(self, feature: 'Feature'):
        """移除子特征"""
        if feature in self._children:
            self._children.remove(feature)
            feature._parent = None
            logger.debug(f"Removed child {feature.feature_id[:8]} from {self.feature_id[:8]}")
    
    def get_all_descendants(self) -> List['Feature']:
        """获取所有后代特征"""
        descendants = []
        for child in self._children:
            descendants.append(child)
            descendants.extend(child.get_all_descendants())
        return descendants
    
    @abstractmethod
    def build(self) -> Optional[str]:
        """
        构建特征
        
        Returns:
            生成的形状ID，如果构建失败返回None
        """
        pass
    
    @abstractmethod
    def validate(self) -> Tuple[bool, str]:
        """
        验证参数有效性
        
        Returns:
            (是否有效, 错误信息)
        """
        pass
    
    def update(self) -> Optional[str]:
        """更新特征（如果参数已更改）"""
        if self._is_dirty and not self._params.is_suppressed:
            return self.build()
        return self._result_shape_id
    
    def suppress(self):
        """抑制特征"""
        self._params.is_suppressed = True
        self._is_dirty = True
        logger.debug(f"Suppressed feature {self.feature_id[:8]}")
    
    def unsuppress(self):
        """取消抑制特征"""
        self._params.is_suppressed = False
        self._is_dirty = True
        logger.debug(f"Unsuppressed feature {self.feature_id[:8]}")
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            'feature_id': self.feature_id,
            'feature_type': self.feature_type.name,
            'parameters': self._serialize_parameters(),
            'children': [child.feature_id for child in self._children],
            'parent_id': self._parent.feature_id if self._parent else None,
            'is_suppressed': self._params.is_suppressed,
            'result_shape_id': self._result_shape_id
        }
    
    @abstractmethod
    def _serialize_parameters(self) -> Dict[str, Any]:
        """序列化参数（子类实现）"""
        pass
    
    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any], 
                  kernel: GeometryKernel) -> 'Feature':
        """从字典反序列化（子类实现）"""
        pass
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.feature_id[:8]}, type={self.feature_type.name})"


class FeatureFactory:
    """
    特征工厂类
    负责创建和管理特征实例
    """
    
    _registry: Dict[FeatureType, type] = {}
    
    @classmethod
    def register(cls, feature_type: FeatureType, feature_class: type):
        """
        注册特征类
        
        Args:
            feature_type: 特征类型
            feature_class: 特征类（必须继承自Feature）
        """
        if not issubclass(feature_class, Feature):
            raise TypeError("Feature class must inherit from Feature")
        cls._registry[feature_type] = feature_class
        logger.info(f"Registered feature type: {feature_type.name}")
    
    @classmethod
    def create(cls, feature_type: FeatureType, 
               params: FeatureParameters,
               kernel: GeometryKernel) -> Feature:
        """
        创建特征实例
        
        Args:
            feature_type: 特征类型
            params: 特征参数
            kernel: 几何内核
        
        Returns:
            特征实例
        
        Raises:
            ValueError: 如果特征类型未注册
        """
        feature_class = cls._registry.get(feature_type)
        if feature_class is None:
            raise ValueError(f"Unknown feature type: {feature_type}")
        return feature_class(params, kernel)
    
    @classmethod
    def create_from_dict(cls, data: Dict[str, Any],
                         kernel: GeometryKernel) -> Feature:
        """
        从字典创建特征
        
        Args:
            data: 特征数据字典
            kernel: 几何内核
        
        Returns:
            特征实例
        """
        feature_type = FeatureType[data['feature_type']]
        feature_class = cls._registry.get(feature_type)
        if feature_class is None:
            raise ValueError(f"Unknown feature type: {feature_type}")
        return feature_class.from_dict(data, kernel)
    
    @classmethod
    def get_registered_types(cls) -> List[FeatureType]:
        """获取已注册的特征类型"""
        return list(cls._registry.keys())
    
    @classmethod
    def is_registered(cls, feature_type: FeatureType) -> bool:
        """检查特征类型是否已注册"""
        return feature_type in cls._registry
    
    @classmethod
    def unregister(cls, feature_type: FeatureType):
        """注销特征类型"""
        if feature_type in cls._registry:
            del cls._registry[feature_type]
            logger.info(f"Unregistered feature type: {feature_type.name}")
    
    @classmethod
    def clear_registry(cls):
        """清空注册表"""
        cls._registry.clear()
        logger.info("Feature registry cleared")
