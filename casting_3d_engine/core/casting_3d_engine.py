"""
主引擎类

铸造3D建模引擎的主入口
"""

import logging
import json
from typing import Dict, List, Optional, Tuple, Any, Callable
from pathlib import Path

from .types import (
    FeatureType, Point3D, Vector3D, Plane, Profile2D,
    FeatureParameters, ExtrudeParameters, RevolveParameters,
    HoleParameters, DraftParameters, FilletParameters,
    PrimitiveBoxParameters, PrimitiveCylinderParameters, PrimitiveSphereParameters
)
from .geometry_kernel import GeometryKernel
from .feature_base import Feature, FeatureFactory
from .features import (
    ExtrudeFeature, RevolveFeature, HoleFeature,
    DraftFeature, FilletFeature
)
from .command_system import (
    Command, CommandManager,
    CreateFeatureCommand, DeleteFeatureCommand, ModifyFeatureCommand,
    SuppressFeatureCommand, UnsuppressFeatureCommand
)
from .feature_manager import FeatureManager
from .model_builder import ModelBuilder

logger = logging.getLogger(__name__)


class Casting3DEngine:
    """
    铸造3D建模引擎主类
    
    提供统一的建模接口，支持：
    - 2D到3D模型转换
    - 特征建模
    - 参数化设计
    - 撤销/重做
    - 多格式导出
    """
    
    VERSION = "1.0.0"
    
    def __init__(self):
        # 初始化内核
        self._kernel = GeometryKernel()
        
        # 初始化管理器
        self._feature_manager = FeatureManager(self._kernel)
        self._command_manager = CommandManager()
        self._model_builder = ModelBuilder(self._kernel, self._feature_manager)
        
        # 参数系统
        self._parameters: Dict[str, Any] = {}
        self._parameter_expressions: Dict[str, str] = {}  # 参数表达式
        
        # 事件回调
        self._event_callbacks: Dict[str, List[Callable]] = {}
        
        # 配置
        self._config = {
            'auto_rebuild': True,
            'max_history': 100,
            'default_linear_deflection': 0.5,
            'default_angular_deflection': 0.5
        }
        
        logger.info(f"Casting3DEngine v{self.VERSION} initialized")
    
    # ==================== 特征操作 ====================
    
    def create_extrude(self, profile: Profile2D, depth: float,
                       direction: Vector3D = None,
                       taper_angle: float = 0.0,
                       name: str = "") -> Optional[str]:
        """
        创建拉伸特征
        
        Args:
            profile: 2D轮廓
            depth: 拉伸深度
            direction: 拉伸方向（默认Z轴）
            taper_angle: 拔模角度（度）
            name: 特征名称
        
        Returns:
            特征ID
        """
        if direction is None:
            direction = Vector3D(0, 0, 1)
        
        params = ExtrudeParameters(
            feature_id=str(uuid4()),
            feature_type=FeatureType.EXTRUDE,
            name=name or "Extrude",
            profile=profile,
            direction=direction,
            depth=depth,
            taper_angle=taper_angle
        )
        
        command = CreateFeatureCommand(
            self._feature_manager, params, self._kernel)
        
        if self._command_manager.execute(command):
            self._emit_event('feature_created', params.feature_id)
            return params.feature_id
        return None
    
    def create_revolve(self, profile: Profile2D, angle: float = 360.0,
                       axis_origin: Point3D = None,
                       axis_direction: Vector3D = None,
                       name: str = "") -> Optional[str]:
        """
        创建旋转特征
        
        Args:
            profile: 2D轮廓
            angle: 旋转角度（度）
            axis_origin: 旋转轴原点
            axis_direction: 旋转轴方向
            name: 特征名称
        
        Returns:
            特征ID
        """
        if axis_origin is None:
            axis_origin = Point3D()
        if axis_direction is None:
            axis_direction = Vector3D(0, 0, 1)
        
        params = RevolveParameters(
            feature_id=str(uuid4()),
            feature_type=FeatureType.REVOLVE,
            name=name or "Revolve",
            profile=profile,
            axis_origin=axis_origin,
            axis_direction=axis_direction,
            angle=angle
        )
        
        command = CreateFeatureCommand(
            self._feature_manager, params, self._kernel)
        
        if self._command_manager.execute(command):
            self._emit_event('feature_created', params.feature_id)
            return params.feature_id
        return None
    
    def create_hole(self, center: Point3D, diameter: float,
                    depth: float = 0.0,
                    direction: Vector3D = None,
                    hole_type: str = "simple",
                    name: str = "") -> Optional[str]:
        """
        创建孔特征
        
        Args:
            center: 孔中心点
            diameter: 孔直径
            depth: 孔深度（0表示通孔）
            direction: 孔方向
            hole_type: 孔类型（simple, counterbore, countersink）
            name: 特征名称
        
        Returns:
            特征ID
        """
        if direction is None:
            direction = Vector3D(0, 0, 1)
        
        params = HoleParameters(
            feature_id=str(uuid4()),
            feature_type=FeatureType.HOLE,
            name=name or "Hole",
            center=center,
            direction=direction,
            diameter=diameter,
            depth=depth,
            hole_type=hole_type
        )
        
        command = CreateFeatureCommand(
            self._feature_manager, params, self._kernel)
        
        if self._command_manager.execute(command):
            self._emit_event('feature_created', params.feature_id)
            return params.feature_id
        return None
    
    def create_draft(self, face_ids: List[str], angle: float,
                     neutral_plane: Plane = None,
                     pull_direction: Vector3D = None,
                     is_inward: bool = True,
                     name: str = "") -> Optional[str]:
        """
        创建拔模特征（铸造专用）
        
        Args:
            face_ids: 要拔模的面ID列表
            angle: 拔模角度（度）
            neutral_plane: 中性平面
            pull_direction: 拔模方向
            is_inward: 是否向内拔模
            name: 特征名称
        
        Returns:
            特征ID
        """
        if neutral_plane is None:
            neutral_plane = Plane()
        if pull_direction is None:
            pull_direction = Vector3D(0, 0, 1)
        
        params = DraftParameters(
            feature_id=str(uuid4()),
            feature_type=FeatureType.DRAFT,
            name=name or "Draft",
            face_ids=face_ids,
            neutral_plane=neutral_plane,
            pull_direction=pull_direction,
            draft_angle=angle,
            is_inward=is_inward
        )
        
        command = CreateFeatureCommand(
            self._feature_manager, params, self._kernel)
        
        if self._command_manager.execute(command):
            self._emit_event('feature_created', params.feature_id)
            return params.feature_id
        return None
    
    def create_fillet(self, edge_ids: List[str], radius: float,
                      name: str = "") -> Optional[str]:
        """
        创建圆角特征
        
        Args:
            edge_ids: 边ID列表
            radius: 圆角半径
            name: 特征名称
        
        Returns:
            特征ID
        """
        params = FilletParameters(
            feature_id=str(uuid4()),
            feature_type=FeatureType.FILLET,
            name=name or "Fillet",
            edge_ids=edge_ids,
            radius=radius
        )
        
        command = CreateFeatureCommand(
            self._feature_manager, params, self._kernel)
        
        if self._command_manager.execute(command):
            self._emit_event('feature_created', params.feature_id)
            return params.feature_id
        return None
    
    def create_box(self, corner: Point3D, 
                   width: float, depth: float, height: float,
                   name: str = "") -> Optional[str]:
        """
        创建立方体
        
        Args:
            corner: 角点
            width: 宽度
            depth: 深度
            height: 高度
            name: 特征名称
        
        Returns:
            特征ID
        """
        params = PrimitiveBoxParameters(
            feature_id=str(uuid4()),
            feature_type=FeatureType.PRIMITIVE_BOX,
            name=name or "Box",
            corner=corner,
            dimensions=(width, depth, height)
        )
        
        from .features import PrimitiveBoxFeature
        feature = PrimitiveBoxFeature(params, self._kernel)
        self._feature_manager.add_feature(feature)
        result = feature.build()
        
        if result:
            self._emit_event('feature_created', params.feature_id)
            return params.feature_id
        return None
    
    def create_cylinder(self, center: Point3D, radius: float, height: float,
                        axis: Vector3D = None,
                        name: str = "") -> Optional[str]:
        """
        创建圆柱体
        
        Args:
            center: 中心点
            radius: 半径
            height: 高度
            axis: 轴向
            name: 特征名称
        
        Returns:
            特征ID
        """
        if axis is None:
            axis = Vector3D(0, 0, 1)
        
        params = PrimitiveCylinderParameters(
            feature_id=str(uuid4()),
            feature_type=FeatureType.PRIMITIVE_CYLINDER,
            name=name or "Cylinder",
            center=center,
            axis=axis,
            radius=radius,
            height=height
        )
        
        from .features import PrimitiveCylinderFeature
        feature = PrimitiveCylinderFeature(params, self._kernel)
        self._feature_manager.add_feature(feature)
        result = feature.build()
        
        if result:
            self._emit_event('feature_created', params.feature_id)
            return params.feature_id
        return None
    
    def create_sphere(self, center: Point3D, radius: float,
                      name: str = "") -> Optional[str]:
        """
        创建球体
        
        Args:
            center: 中心点
            radius: 半径
            name: 特征名称
        
        Returns:
            特征ID
        """
        params = PrimitiveSphereParameters(
            feature_id=str(uuid4()),
            feature_type=FeatureType.PRIMITIVE_SPHERE,
            name=name or "Sphere",
            center=center,
            radius=radius
        )
        
        from .features import PrimitiveSphereFeature
        feature = PrimitiveSphereFeature(params, self._kernel)
        self._feature_manager.add_feature(feature)
        result = feature.build()
        
        if result:
            self._emit_event('feature_created', params.feature_id)
            return params.feature_id
        return None
    
    def delete_feature(self, feature_id: str) -> bool:
        """
        删除特征
        
        Args:
            feature_id: 特征ID
        
        Returns:
            是否删除成功
        """
        command = DeleteFeatureCommand(self._feature_manager, feature_id)
        if self._command_manager.execute(command):
            self._emit_event('feature_deleted', feature_id)
            return True
        return False
    
    def modify_feature(self, feature_id: str, 
                       new_params: FeatureParameters) -> bool:
        """
        修改特征参数
        
        Args:
            feature_id: 特征ID
            new_params: 新参数
        
        Returns:
            是否修改成功
        """
        feature = self._feature_manager.get_feature(feature_id)
        if feature is None:
            return False
        
        command = ModifyFeatureCommand(feature, new_params)
        if self._command_manager.execute(command):
            self._emit_event('feature_modified', feature_id)
            return True
        return False
    
    def suppress_feature(self, feature_id: str) -> bool:
        """抑制特征"""
        feature = self._feature_manager.get_feature(feature_id)
        if feature is None:
            return False
        
        command = SuppressFeatureCommand(feature)
        return self._command_manager.execute(command)
    
    def unsuppress_feature(self, feature_id: str) -> bool:
        """取消抑制特征"""
        feature = self._feature_manager.get_feature(feature_id)
        if feature is None:
            return False
        
        command = UnsuppressFeatureCommand(feature)
        return self._command_manager.execute(command)
    
    def get_feature(self, feature_id: str) -> Optional[Feature]:
        """获取特征"""
        return self._feature_manager.get_feature(feature_id)
    
    def get_all_features(self) -> List[Feature]:
        """获取所有特征"""
        return self._feature_manager.get_all_features()
    
    # ==================== 模型构建 ====================
    
    def build_from_2d(self, data: Dict[str, Any]) -> Optional[str]:
        """
        从2D数据构建3D模型
        
        Args:
            data: 2D特征数据
        
        Returns:
            生成的形状ID
        """
        shape_id = self._model_builder.build_from_2d_data(data)
        if shape_id:
            self._emit_event('model_built', shape_id)
        return shape_id
    
    def rebuild_model(self) -> bool:
        """重新构建模型"""
        return self._feature_manager.rebuild_all()
    
    # ==================== 导出功能 ====================
    
    def export_stl(self, shape_id: str, filepath: str,
                   linear_deflection: float = None,
                   angular_deflection: float = None) -> bool:
        """
        导出为STL格式
        
        Args:
            shape_id: 形状ID
            filepath: 输出文件路径
            linear_deflection: 线性偏差
            angular_deflection: 角度偏差
        
        Returns:
            导出是否成功
        """
        if linear_deflection is None:
            linear_deflection = self._config['default_linear_deflection']
        if angular_deflection is None:
            angular_deflection = self._config['default_angular_deflection']
        
        return self._kernel.export_stl(shape_id, filepath, 
                                        linear_deflection, angular_deflection)
    
    def export_step(self, shape_id: str, filepath: str) -> bool:
        """导出为STEP格式"""
        return self._kernel.export_step(shape_id, filepath)
    
    def export_iges(self, shape_id: str, filepath: str) -> bool:
        """导出为IGES格式"""
        return self._kernel.export_iges(shape_id, filepath)
    
    # ==================== 撤销/重做 ====================
    
    def undo(self) -> bool:
        """撤销操作"""
        return self._command_manager.undo()
    
    def redo(self) -> bool:
        """重做操作"""
        return self._command_manager.redo()
    
    def can_undo(self) -> bool:
        """检查是否可以撤销"""
        return self._command_manager.can_undo()
    
    def can_redo(self) -> bool:
        """检查是否可以重做"""
        return self._command_manager.can_redo()
    
    def get_command_history(self) -> List[str]:
        """获取命令历史"""
        return self._command_manager.get_history()
    
    def begin_transaction(self, name: str = "Transaction"):
        """开始事务"""
        self._command_manager.begin_transaction(name)
    
    def end_transaction(self, name: str = "Transaction") -> bool:
        """结束事务"""
        return self._command_manager.end_transaction(name)
    
    def cancel_transaction(self):
        """取消事务"""
        self._command_manager.cancel_transaction()
    
    # ==================== 参数系统 ====================
    
    def set_parameter(self, name: str, value: Any):
        """设置参数"""
        self._parameters[name] = value
        self._emit_event('parameter_changed', {'name': name, 'value': value})
        
        # 如果启用自动重建，触发重建
        if self._config['auto_rebuild']:
            self._update_dependent_features(name)
    
    def get_parameter(self, name: str) -> Any:
        """获取参数"""
        return self._parameters.get(name)
    
    def set_parameter_expression(self, name: str, expression: str):
        """设置参数表达式"""
        self._parameter_expressions[name] = expression
    
    def evaluate_parameters(self):
        """评估所有参数表达式"""
        for name, expr in self._parameter_expressions.items():
            try:
                # 简单的表达式求值
                value = eval(expr, {}, self._parameters)
                self._parameters[name] = value
            except Exception as e:
                logger.warning(f"Failed to evaluate expression for {name}: {e}")
    
    def _update_dependent_features(self, param_name: str):
        """更新依赖参数的特征"""
        # 这里可以实现参数驱动的特征更新
        pass
    
    # ==================== 事件系统 ====================
    
    def register_callback(self, event: str, callback: Callable):
        """注册事件回调"""
        if event not in self._event_callbacks:
            self._event_callbacks[event] = []
        self._event_callbacks[event].append(callback)
    
    def unregister_callback(self, event: str, callback: Callable):
        """注销事件回调"""
        if event in self._event_callbacks:
            if callback in self._event_callbacks[event]:
                self._event_callbacks[event].remove(callback)
    
    def _emit_event(self, event: str, data: Any):
        """触发事件"""
        if event in self._event_callbacks:
            for callback in self._event_callbacks[event]:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Event callback error: {e}")
    
    # ==================== 序列化 ====================
    
    def save(self, filepath: str) -> bool:
        """
        保存模型
        
        Args:
            filepath: 文件路径
        
        Returns:
            保存是否成功
        """
        try:
            data = {
                'version': self.VERSION,
                'features': self._feature_manager.serialize(),
                'parameters': self._parameters,
                'parameter_expressions': self._parameter_expressions,
                'config': self._config
            }
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Model saved: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Save failed: {e}")
            return False
    
    def load(self, filepath: str) -> bool:
        """
        加载模型
        
        Args:
            filepath: 文件路径
        
        Returns:
            加载是否成功
        """
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            version = data.get('version', '1.0')
            
            # 加载特征
            self._feature_manager.deserialize(data['features'])
            
            # 加载参数
            self._parameters = data.get('parameters', {})
            self._parameter_expressions = data.get('parameter_expressions', {})
            self._config.update(data.get('config', {}))
            
            # 重建模型
            self.rebuild_model()
            
            logger.info(f"Model loaded: {filepath} (version {version})")
            return True
            
        except Exception as e:
            logger.error(f"Load failed: {e}")
            return False
    
    # ==================== 配置 ====================
    
    def set_config(self, key: str, value: Any):
        """设置配置"""
        self._config[key] = value
    
    def get_config(self, key: str) -> Any:
        """获取配置"""
        return self._config.get(key)
    
    # ==================== 属性访问 ====================
    
    @property
    def kernel(self) -> GeometryKernel:
        """几何内核"""
        return self._kernel
    
    @property
    def feature_manager(self) -> FeatureManager:
        """特征管理器"""
        return self._feature_manager
    
    @property
    def command_manager(self) -> CommandManager:
        """命令管理器"""
        return self._command_manager
    
    @property
    def model_builder(self) -> ModelBuilder:
        """模型构建器"""
        return self._model_builder
    
    @property
    def volume(self) -> float:
        """获取模型体积"""
        features = self._feature_manager.get_all_features()
        if features:
            last_feature = features[-1]
            return self._kernel.get_volume(last_feature.feature_id)
        return 0.0
    
    @property
    def centroid(self) -> Point3D:
        """获取模型质心"""
        features = self._feature_manager.get_all_features()
        if features:
            last_feature = features[-1]
            return self._kernel.get_centroid(last_feature.feature_id)
        return Point3D()
    
    @property
    def feature_count(self) -> int:
        """特征数量"""
        return len(self._feature_manager)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'version': self.VERSION,
            'feature_count': self.feature_count,
            'volume': self.volume,
            'centroid': self.centroid.to_tuple(),
            'feature_stats': self._feature_manager.get_statistics()
        }
    
    def __repr__(self) -> str:
        return f"Casting3DEngine(v{self.VERSION}, {self.feature_count} features)"


# 导入uuid
from uuid import uuid4
