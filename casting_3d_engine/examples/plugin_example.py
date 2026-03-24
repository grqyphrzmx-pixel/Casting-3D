"""
插件系统示例

演示如何创建和使用自定义特征插件
"""

import logging
from typing import Dict, Any, Tuple, Optional

logging.basicConfig(level=logging.INFO)

from casting_3d_engine import (
    Casting3DEngine,
    Point3D, Vector3D, Profile2D,
    FeatureType, FeatureParameters
)
from casting_3d_engine.core.feature_base import Feature, FeatureFactory
from casting_3d_engine.core.geometry_kernel import GeometryKernel


# ==================== 自定义特征插件示例 ====================

class RibParameters(FeatureParameters):
    """加强筋参数"""
    def __init__(self, **kwargs):
        super().__init__(feature_type=FeatureType.RIB, **kwargs)
        self.start_point: Point3D = kwargs.get('start_point', Point3D())
        self.end_point: Point3D = kwargs.get('end_point', Point3D())
        self.height: float = kwargs.get('height', 10.0)
        self.thickness: float = kwargs.get('thickness', 3.0)
        self.draft_angle: float = kwargs.get('draft_angle', 2.0)


class RibFeature(Feature):
    """
    加强筋特征（铸造专用）
    
    加强筋用于增加零件的强度和刚度
    """
    
    def __init__(self, params: RibParameters, kernel: GeometryKernel):
        super().__init__(params, kernel)
        self._params: RibParameters = params
    
    def validate(self) -> Tuple[bool, str]:
        """验证参数"""
        if self._params.height <= 0:
            return False, "Height must be positive"
        if self._params.thickness <= 0:
            return False, "Thickness must be positive"
        if self._params.start_point == self._params.end_point:
            return False, "Start and end points must be different"
        return True, ""
    
    def build(self) -> Optional[str]:
        """构建加强筋"""
        if self._params.is_suppressed:
            return None
        
        valid, msg = self.validate()
        if not valid:
            logging.error(f"Rib validation failed: {msg}")
            return None
        
        try:
            # 计算加强筋轮廓
            # 简化实现：创建一个矩形拉伸
            start = self._params.start_point
            end = self._params.end_point
            height = self._params.height
            thickness = self._params.thickness
            
            # 计算方向向量
            direction = Vector3D.from_points(start, end)
            length = direction.length()
            direction = direction.normalize()
            
            # 计算垂直方向（假设在XY平面）
            perp = Vector3D(-direction.y, direction.x, 0).normalize()
            
            # 创建轮廓
            half_t = thickness / 2
            profile = Profile2D(
                vertices=[
                    Point3D(start.x - half_t * perp.x, 
                           start.y - half_t * perp.y, 0),
                    Point3D(start.x + half_t * perp.x, 
                           start.y + half_t * perp.y, 0),
                    Point3D(end.x + half_t * perp.x, 
                           end.y + half_t * perp.y, 0),
                    Point3D(end.x - half_t * perp.x, 
                           end.y - half_t * perp.y, 0)
                ],
                is_closed=True
            )
            
            # 创建拉伸
            wire = self._kernel.create_wire_from_profile(profile)
            if wire is None:
                return None
            
            face = self._kernel.create_face_from_wire(wire)
            if face is None:
                return None
            
            shape = self._kernel.extrude_face(
                face, Vector3D(0, 0, 1), height, self._params.draft_angle)
            
            if shape is None:
                return None
            
            self._result_shape_id = self._params.feature_id
            self._kernel.register_shape(self._result_shape_id, shape)
            self._is_dirty = False
            
            logging.info(f"Rib feature built: {self.feature_id[:8]}")
            return self._result_shape_id
            
        except Exception as e:
            logging.error(f"Rib build failed: {e}")
            return None
    
    def _serialize_parameters(self) -> Dict[str, Any]:
        return {
            'start_point': self._params.start_point.to_tuple(),
            'end_point': self._params.end_point.to_tuple(),
            'height': self._params.height,
            'thickness': self._params.thickness,
            'draft_angle': self._params.draft_angle
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], 
                  kernel: GeometryKernel) -> 'RibFeature':
        params_data = data['parameters']
        
        params = RibParameters(
            feature_id=data['feature_id'],
            start_point=Point3D(*params_data['start_point']),
            end_point=Point3D(*params_data['end_point']),
            height=params_data['height'],
            thickness=params_data['thickness'],
            draft_angle=params_data.get('draft_angle', 2.0)
        )
        
        return cls(params, kernel)


class CoolingChannelParameters(FeatureParameters):
    """冷却通道参数（铸造模具用）"""
    def __init__(self, **kwargs):
        super().__init__(feature_type=FeatureType.SLOT, **kwargs)
        self.path_points: list = kwargs.get('path_points', [])
        self.diameter: float = kwargs.get('diameter', 10.0)
        self.is_straight: bool = kwargs.get('is_straight', True)


class CoolingChannelFeature(Feature):
    """
    冷却通道特征（铸造模具专用）
    
    用于创建模具中的冷却通道
    """
    
    def __init__(self, params: CoolingChannelParameters, kernel: GeometryKernel):
        super().__init__(params, kernel)
        self._params: CoolingChannelParameters = params
    
    def validate(self) -> Tuple[bool, str]:
        if len(self._params.path_points) < 2:
            return False, "Path must have at least 2 points"
        if self._params.diameter <= 0:
            return False, "Diameter must be positive"
        return True, ""
    
    def build(self) -> Optional[str]:
        if self._params.is_suppressed:
            return None
        
        valid, msg = self.validate()
        if not valid:
            logging.error(f"Cooling channel validation failed: {msg}")
            return None
        
        try:
            # 简化实现：创建圆柱体作为通道
            start = self._params.path_points[0]
            end = self._params.path_points[-1]
            
            direction = Vector3D.from_points(start, end)
            height = direction.length()
            
            if height < 1e-6:
                return None
            
            shape = self._kernel.create_cylinder(
                start, direction.normalize(),
                self._params.diameter / 2, height)
            
            if shape is None:
                return None
            
            self._result_shape_id = self._params.feature_id
            self._kernel.register_shape(self._result_shape_id, shape)
            self._is_dirty = False
            
            logging.info(f"Cooling channel built: {self.feature_id[:8]}")
            return self._result_shape_id
            
        except Exception as e:
            logging.error(f"Cooling channel build failed: {e}")
            return None
    
    def _serialize_parameters(self) -> Dict[str, Any]:
        return {
            'path_points': [p.to_tuple() for p in self._params.path_points],
            'diameter': self._params.diameter,
            'is_straight': self._params.is_straight
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], 
                  kernel: GeometryKernel) -> 'CoolingChannelFeature':
        params_data = data['parameters']
        
        params = CoolingChannelParameters(
            feature_id=data['feature_id'],
            path_points=[Point3D(*p) for p in params_data['path_points']],
            diameter=params_data['diameter'],
            is_straight=params_data.get('is_straight', True)
        )
        
        return cls(params, kernel)


# ==================== 插件使用示例 ====================

def example_register_custom_features():
    """示例：注册自定义特征"""
    print("=" * 60)
    print("示例：注册自定义特征")
    print("=" * 60)
    
    # 注册加强筋特征
    FeatureFactory.register(FeatureType.RIB, RibFeature)
    print("✓ 注册加强筋特征 (RibFeature)")
    
    # 注册冷却通道特征
    FeatureFactory.register(FeatureType.SLOT, CoolingChannelFeature)
    print("✓ 注册冷却通道特征 (CoolingChannelFeature)")
    
    # 查看已注册的特征类型
    registered_types = FeatureFactory.get_registered_types()
    print(f"\n已注册的特征类型 ({len(registered_types)}个):")
    for ft in registered_types:
        print(f"  - {ft.name}")


def example_create_rib():
    """示例：创建加强筋"""
    print("\n" + "=" * 60)
    print("示例：创建加强筋")
    print("=" * 60)
    
    # 注册特征
    FeatureFactory.register(FeatureType.RIB, RibFeature)
    
    # 创建引擎
    engine = Casting3DEngine()
    
    # 首先创建基体
    profile = Profile2D(
        vertices=[
            Point3D(0, 0, 0),
            Point3D(100, 0, 0),
            Point3D(100, 80, 0),
            Point3D(0, 80, 0)
        ],
        is_closed=True
    )
    
    base_id = engine.create_extrude(profile, depth=20.0, name="BasePlate")
    print(f"基体创建: {base_id}")
    
    # 创建加强筋参数
    rib_params = RibParameters(
        feature_id="rib_001",
        name="Rib1",
        start_point=Point3D(20, 20, 20),
        end_point=Point3D(80, 20, 20),
        height=15.0,
        thickness=5.0,
        draft_angle=2.0
    )
    
    # 创建加强筋特征
    rib_feature = RibFeature(rib_params, engine.kernel)
    engine.feature_manager.add_feature(rib_feature)
    rib_result = rib_feature.build()
    
    if rib_result:
        print(f"加强筋创建: {rib_result[:8]}")
        print(f"  起点: {rib_params.start_point}")
        print(f"  终点: {rib_params.end_point}")
        print(f"  高度: {rib_params.height} mm")
        print(f"  厚度: {rib_params.thickness} mm")
    
    return engine


def example_create_cooling_channel():
    """示例：创建冷却通道"""
    print("\n" + "=" * 60)
    print("示例：创建冷却通道")
    print("=" * 60)
    
    # 注册特征
    FeatureFactory.register(FeatureType.SLOT, CoolingChannelFeature)
    
    # 创建引擎
    engine = Casting3DEngine()
    
    # 创建模具基体
    profile = Profile2D(
        vertices=[
            Point3D(0, 0, 0),
            Point3D(200, 0, 0),
            Point3D(200, 150, 0),
            Point3D(0, 150, 0)
        ],
        is_closed=True
    )
    
    base_id = engine.create_extrude(profile, depth=50.0, name="MoldBase")
    print(f"模具基体创建: {base_id}")
    
    # 创建冷却通道
    channel_params = CoolingChannelParameters(
        feature_id="channel_001",
        name="CoolingChannel1",
        path_points=[
            Point3D(30, 30, 25),
            Point3D(170, 30, 25)
        ],
        diameter=12.0,
        is_straight=True
    )
    
    channel_feature = CoolingChannelFeature(channel_params, engine.kernel)
    engine.feature_manager.add_feature(channel_feature)
    channel_result = channel_feature.build()
    
    if channel_result:
        print(f"冷却通道创建: {channel_result[:8]}")
        print(f"  直径: {channel_params.diameter} mm")
        print(f"  长度: {Vector3D.from_points(channel_params.path_points[0], channel_params.path_points[1]).length():.1f} mm")
    
    return engine


def example_plugin_architecture():
    """示例：插件架构演示"""
    print("\n" + "=" * 60)
    print("示例：插件架构演示")
    print("=" * 60)
    
    print("""
插件架构说明:
==============

1. 创建自定义特征类:
   - 继承自 Feature 基类
   - 实现 validate(), build(), _serialize_parameters() 方法
   - 实现 from_dict() 类方法用于反序列化

2. 注册特征:
   - 使用 FeatureFactory.register(feature_type, feature_class)
   - 特征类型使用 FeatureType 枚举或自定义值

3. 使用特征:
   - 通过 FeatureFactory.create() 创建特征实例
   - 或使用特征类直接实例化

4. 插件加载（动态）:
   - 可以从外部文件动态加载插件
   - 使用 importlib 动态导入模块
   - 调用插件的 initialize() 方法

优势:
- 无需修改核心代码即可添加新特征
- 支持第三方扩展
- 易于维护和升级
""")


def example_feature_serialization():
    """示例：特征序列化"""
    print("\n" + "=" * 60)
    print("示例：特征序列化")
    print("=" * 60)
    
    # 注册特征
    FeatureFactory.register(FeatureType.RIB, RibFeature)
    
    # 创建引擎和特征
    engine = Casting3DEngine()
    
    rib_params = RibParameters(
        feature_id="rib_test",
        name="TestRib",
        start_point=Point3D(0, 0, 0),
        end_point=Point3D(50, 0, 0),
        height=10.0,
        thickness=3.0
    )
    
    rib = RibFeature(rib_params, engine.kernel)
    
    # 序列化
    data = rib.to_dict()
    print("序列化后的特征数据:")
    print(f"  ID: {data['feature_id']}")
    print(f"  类型: {data['feature_type']}")
    print(f"  参数: {data['parameters']}")
    
    # 反序列化
    rib_restored = RibFeature.from_dict(data, engine.kernel)
    print(f"\n反序列化后的特征:")
    print(f"  ID: {rib_restored.feature_id}")
    print(f"  类型: {rib_restored.feature_type.name}")
    print(f"  参数匹配: {rib_restored.parameters._serialize_parameters() == data['parameters']}")


def run_all_examples():
    """运行所有示例"""
    print("\n" + "=" * 70)
    print("铸造3D建模引擎 - 插件系统示例")
    print("=" * 70)
    
    examples = [
        ("注册自定义特征", example_register_custom_features),
        ("创建加强筋", example_create_rib),
        ("创建冷却通道", example_create_cooling_channel),
        ("插件架构说明", example_plugin_architecture),
        ("特征序列化", example_feature_serialization),
    ]
    
    for name, example_func in examples:
        try:
            print(f"\n{'='*70}")
            print(f"运行: {name}")
            print('='*70)
            example_func()
        except Exception as e:
            print(f"示例 '{name}' 失败: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("所有示例运行完成")
    print("=" * 70)


if __name__ == "__main__":
    run_all_examples()
