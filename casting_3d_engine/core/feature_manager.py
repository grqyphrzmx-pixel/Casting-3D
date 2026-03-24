"""
特征管理器模块

管理所有特征的生命周期和依赖关系
"""

import logging
from typing import Dict, List, Optional, Set, Any
from collections import deque

from .types import FeatureType
from .geometry_kernel import GeometryKernel
from .feature_base import Feature, FeatureFactory

logger = logging.getLogger(__name__)


class FeatureManager:
    """
    特征管理器
    管理所有特征的生命周期和依赖关系
    """
    
    def __init__(self, kernel: GeometryKernel):
        self._kernel = kernel
        self._features: Dict[str, Feature] = {}
        self._feature_tree: Dict[str, List[str]] = {}  # parent -> children
        self._body_features: Dict[str, List[str]] = {}  # body_id -> feature_ids
        self._feature_order: List[str] = []  # 创建顺序
        
    def add_feature(self, feature: Feature) -> bool:
        """
        添加特征
        
        Args:
            feature: 要添加的特征
        
        Returns:
            是否添加成功
        """
        if feature.feature_id in self._features:
            logger.warning(f"Feature {feature.feature_id[:8]} already exists")
            return False
        
        self._features[feature.feature_id] = feature
        self._feature_order.append(feature.feature_id)
        
        # 更新特征树
        if feature.parent:
            parent_id = feature.parent.feature_id
            if parent_id not in self._feature_tree:
                self._feature_tree[parent_id] = []
            if feature.feature_id not in self._feature_tree[parent_id]:
                self._feature_tree[parent_id].append(feature.feature_id)
        
        logger.debug(f"Added feature: {feature.feature_id[:8]}")
        return True
    
    def remove_feature(self, feature_id: str) -> bool:
        """
        移除特征
        
        Args:
            feature_id: 要移除的特征ID
        
        Returns:
            是否移除成功
        """
        if feature_id not in self._features:
            return False
        
        feature = self._features[feature_id]
        
        # 递归移除子特征
        if feature_id in self._feature_tree:
            for child_id in self._feature_tree[feature_id][:]:
                self.remove_feature(child_id)
            del self._feature_tree[feature_id]
        
        # 从父特征的子列表中移除
        if feature.parent:
            parent_id = feature.parent.feature_id
            if parent_id in self._feature_tree:
                if feature_id in self._feature_tree[parent_id]:
                    self._feature_tree[parent_id].remove(feature_id)
        
        # 从内核中移除形状
        self._kernel.remove_shape(feature_id)
        
        # 从顺序列表中移除
        if feature_id in self._feature_order:
            self._feature_order.remove(feature_id)
        
        # 移除特征
        del self._features[feature_id]
        
        logger.debug(f"Removed feature: {feature_id[:8]}")
        return True
    
    def get_feature(self, feature_id: str) -> Optional[Feature]:
        """获取特征"""
        return self._features.get(feature_id)
    
    def get_all_features(self) -> List[Feature]:
        """获取所有特征（按创建顺序）"""
        return [self._features[fid] for fid in self._feature_order 
                if fid in self._features]
    
    def get_features_by_type(self, feature_type: FeatureType) -> List[Feature]:
        """按类型获取特征"""
        return [f for f in self._features.values() 
                if f.feature_type == feature_type]
    
    def get_features_by_types(self, feature_types: List[FeatureType]) -> List[Feature]:
        """按多个类型获取特征"""
        return [f for f in self._features.values() 
                if f.feature_type in feature_types]
    
    def get_root_features(self) -> List[Feature]:
        """获取根特征（没有父特征）"""
        return [f for f in self._features.values() if f.parent is None]
    
    def get_children(self, feature_id: str) -> List[Feature]:
        """获取子特征"""
        child_ids = self._feature_tree.get(feature_id, [])
        return [self._features[cid] for cid in child_ids if cid in self._features]
    
    def get_siblings(self, feature_id: str) -> List[Feature]:
        """获取兄弟特征（同一父特征的其他子特征）"""
        feature = self._features.get(feature_id)
        if feature is None or feature.parent is None:
            return []
        
        parent_id = feature.parent.feature_id
        siblings = self._feature_tree.get(parent_id, [])
        return [self._features[sid] for sid in siblings 
                if sid != feature_id and sid in self._features]
    
    def get_feature_tree(self, feature_id: str) -> Dict[str, Any]:
        """获取特征树结构"""
        feature = self._features.get(feature_id)
        if feature is None:
            return {}
        
        return {
            'feature_id': feature_id,
            'feature_type': feature.feature_type.name,
            'children': [
                self.get_feature_tree(cid) 
                for cid in self._feature_tree.get(feature_id, [])
            ]
        }
    
    def get_dependency_order(self) -> List[str]:
        """
        获取特征的依赖顺序（拓扑排序）
        确保父特征在子特征之前
        """
        # 构建依赖图
        in_degree = {fid: 0 for fid in self._features}
        
        for feature in self._features.values():
            if feature.parent:
                in_degree[feature.feature_id] += 1
        
        # 拓扑排序
        queue = deque([fid for fid, deg in in_degree.items() if deg == 0])
        order = []
        
        while queue:
            fid = queue.popleft()
            order.append(fid)
            
            for child_id in self._feature_tree.get(fid, []):
                in_degree[child_id] -= 1
                if in_degree[child_id] == 0:
                    queue.append(child_id)
        
        # 检查是否有循环依赖
        if len(order) != len(self._features):
            logger.warning("Circular dependency detected in feature tree")
            # 返回原始顺序
            return self._feature_order
        
        return order
    
    def get_body_shape(self, body_id: str) -> Optional[Any]:
        """获取实体形状"""
        feature_ids = self._body_features.get(body_id, [])
        if feature_ids:
            last_feature_id = feature_ids[-1]
            return self._kernel.get_shape(last_feature_id)
        return None
    
    def rebuild_all(self) -> bool:
        """
        重建所有特征
        按照依赖顺序重建
        """
        try:
            order = self.get_dependency_order()
            
            for feature_id in order:
                feature = self._features.get(feature_id)
                if feature:
                    feature.update()
            
            logger.info(f"Rebuilt {len(order)} features")
            return True
            
        except Exception as e:
            logger.error(f"Rebuild all failed: {e}")
            return False
    
    def rebuild_from(self, feature_id: str) -> bool:
        """从指定特征开始重建（包括该特征及其所有后代）"""
        try:
            feature = self._features.get(feature_id)
            if feature is None:
                return False
            
            # 重建该特征
            feature.update()
            
            # 重建所有后代
            descendants = feature.get_all_descendants()
            for desc in descendants:
                desc.update()
            
            logger.info(f"Rebuilt from feature {feature_id[:8]} "
                       f"(+ {len(descendants)} descendants)")
            return True
            
        except Exception as e:
            logger.error(f"Rebuild from failed: {e}")
            return False
    
    def suppress_feature(self, feature_id: str) -> bool:
        """抑制特征"""
        feature = self._features.get(feature_id)
        if feature:
            feature.suppress()
            feature.update()
            return True
        return False
    
    def unsuppress_feature(self, feature_id: str) -> bool:
        """取消抑制特征"""
        feature = self._features.get(feature_id)
        if feature:
            feature.unsuppress()
            feature.update()
            return True
        return False
    
    def find_features_by_name(self, name: str) -> List[Feature]:
        """按名称查找特征"""
        return [f for f in self._features.values() 
                if f.parameters.name == name]
    
    def find_features_containing_point(self, point: Any, 
                                        tolerance: float = 0.001) -> List[Feature]:
        """查找包含指定点的特征"""
        # 这里简化处理，实际实现需要几何查询
        return []
    
    def clear(self):
        """清空所有特征"""
        self._features.clear()
        self._feature_tree.clear()
        self._body_features.clear()
        self._feature_order.clear()
        logger.info("Feature manager cleared")
    
    def serialize(self) -> Dict[str, Any]:
        """序列化所有特征"""
        return {
            'version': '1.0',
            'features': [f.to_dict() for f in self.get_all_features()],
            'feature_tree': self._feature_tree,
            'body_features': self._body_features,
            'feature_order': self._feature_order
        }
    
    def deserialize(self, data: Dict[str, Any]) -> bool:
        """反序列化特征"""
        try:
            version = data.get('version', '1.0')
            
            self.clear()
            
            self._feature_tree = data.get('feature_tree', {})
            self._body_features = data.get('body_features', {})
            self._feature_order = data.get('feature_order', [])
            
            # 第一遍：创建所有特征
            for feature_data in data['features']:
                feature = FeatureFactory.create_from_dict(feature_data, 
                                                           self._kernel)
                self._features[feature.feature_id] = feature
            
            # 第二遍：重建父子关系
            for feature in self._features.values():
                feature_dict = feature.to_dict()
                parent_id = feature_dict.get('parent_id')
                if parent_id and parent_id in self._features:
                    feature._parent = self._features[parent_id]
            
            logger.info(f"Deserialized {len(self._features)} features")
            return True
            
        except Exception as e:
            logger.error(f"Deserialize failed: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        type_counts = {}
        for feature in self._features.values():
            type_name = feature.feature_type.name
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
        
        return {
            'total_features': len(self._features),
            'type_counts': type_counts,
            'root_features': len(self.get_root_features()),
            'suppressed_features': sum(1 for f in self._features.values() 
                                       if f.is_suppressed)
        }
    
    def __len__(self) -> int:
        """特征数量"""
        return len(self._features)
    
    def __contains__(self, feature_id: str) -> bool:
        """是否包含特征"""
        return feature_id in self._features
