# 铸造行业3D建模引擎

基于OpenCASCADE Technology的3D建模引擎，专门用于铸造零件的2D到3D转换。

## 特性

- **2D到3D转换**: 从2D轮廓数据自动构建3D实体模型
- **特征建模**: 支持拉伸、旋转、扫掠、布尔运算等建模操作
- **铸造专用**: 支持拔模斜度、分型面、加强筋等铸造专用特征
- **参数化设计**: 支持尺寸驱动的模型更新
- **撤销/重做**: 完整的命令历史和撤销/重做功能
- **多格式导出**: 支持STL、STEP、IGES、BREP等格式
- **插件化架构**: 易于扩展新特征类型

## 安装

### 依赖

- Python 3.9+
- OpenCASCADE Technology 7.6+
- NumPy

### 安装步骤

```bash
# 使用conda安装（推荐）
conda install -c conda-forge pythonocc-core=7.7.0

# 安装本引擎
pip install -e .
```

## 快速开始

```python
from casting_3d_engine import Casting3DEngine, Point3D, Profile2D

# 创建引擎
engine = Casting3DEngine()

# 创建矩形轮廓
profile = Profile2D(
    vertices=[
        Point3D(0, 0, 0),
        Point3D(100, 0, 0),
        Point3D(100, 80, 0),
        Point3D(0, 80, 0)
    ],
    is_closed=True
)

# 创建拉伸特征
shape_id = engine.create_extrude(profile, depth=25.0)

# 导出
engine.export_stl(shape_id, "output.stl")
engine.export_step(shape_id, "output.step")
```

## 从2D数据构建模型

```python
from casting_3d_engine import Casting3DEngine, Point3D, Profile2D

engine = Casting3DEngine()

# 2D特征数据
data = {
    'base_profile': Profile2D(
        vertices=[
            Point3D(0, 0, 0),
            Point3D(100, 0, 0),
            Point3D(100, 80, 0),
            Point3D(0, 80, 0)
        ],
        is_closed=True
    ),
    'features': [
        {'type': 'hole', 'center_x': 30, 'center_y': 40, 'diameter': 15},
        {'type': 'hole', 'center_x': 70, 'center_y': 40, 'diameter': 15}
    ],
    'dimensions': {
        'depth': 25.0,
        'draft_angle': 2.0
    }
}

# 构建3D模型
shape_id = engine.build_from_2d(data)
```

## 核心架构

```
casting_3d_engine/
├── core/                   # 核心模块
│   ├── types.py           # 基础数据类型
│   ├── geometry_kernel.py # 几何内核封装
│   ├── feature_base.py    # 特征基类和工厂
│   ├── features.py        # 具体特征实现
│   ├── command_system.py  # 命令系统
│   ├── feature_manager.py # 特征管理器
│   ├── model_builder.py   # 模型构建器
│   └── casting_3d_engine.py # 主引擎类
├── io/                     # IO模块
│   ├── export_manager.py  # 导出管理器
│   └── input_interface.py # 输入接口
└── examples/               # 示例代码
    ├── basic_usage.py     # 基本使用
    ├── from_2d_example.py # 2D到3D转换
    └── plugin_example.py  # 插件开发
```

## 支持的建模特征

### 基体特征
- 拉伸 (Extrude)
- 旋转 (Revolve)
- 扫掠 (Sweep)
- 放样 (Loft)
- 基本体素（立方体、圆柱、球体）

### 附加特征
- 孔 (Hole) - 支持简单孔、沉头孔、锥孔
- 槽 (Slot)
- 腔体 (Pocket)
- 凸台 (Boss)
- 圆角 (Fillet)
- 倒角 (Chamfer)

### 铸造专用特征
- 拔模斜度 (Draft)
- 分型面 (Parting Surface)
- 加强筋 (Rib)
- 冷却通道 (Cooling Channel)

### 布尔运算
- 并 (Union)
- 减 (Subtract)
- 交 (Intersect)

## 导出格式

| 格式 | 用途 | 说明 |
|------|------|------|
| STL | 3D打印、铸造仿真 | 三角网格 |
| STEP | CAD交换 | 精确B-rep |
| IGES | 遗留系统兼容 | 精确B-rep |
| BREP | OpenCASCADE原生 | 完整拓扑信息 |

## 插件开发

创建自定义特征插件：

```python
from casting_3d_engine import Feature, FeatureFactory, FeatureType
from casting_3d_engine.core.types import FeatureParameters

class MyFeatureParameters(FeatureParameters):
    def __init__(self, **kwargs):
        super().__init__(feature_type=FeatureType.EXTRUDE, **kwargs)
        self.custom_param = kwargs.get('custom_param', 0)

class MyFeature(Feature):
    def validate(self):
        return True, ""
    
    def build(self):
        # 实现建模逻辑
        pass
    
    def _serialize_parameters(self):
        return {'custom_param': self._params.custom_param}
    
    @classmethod
    def from_dict(cls, data, kernel):
        # 反序列化
        pass

# 注册插件
FeatureFactory.register(FeatureType.EXTRUDE, MyFeature)
```

## 示例

运行示例代码：

```bash
# 基本使用示例
python -m casting_3d_engine.examples.basic_usage

# 2D到3D转换示例
python -m casting_3d_engine.examples.from_2d_example

# 插件开发示例
python -m casting_3d_engine.examples.plugin_example
```

## API文档

### Casting3DEngine

主引擎类，提供统一的建模接口。

#### 特征创建
- `create_extrude(profile, depth, ...)` - 创建拉伸特征
- `create_revolve(profile, angle, ...)` - 创建旋转特征
- `create_hole(center, diameter, ...)` - 创建孔特征
- `create_draft(face_ids, angle, ...)` - 创建拔模特征
- `create_fillet(edge_ids, radius, ...)` - 创建圆角特征

#### 模型构建
- `build_from_2d(data)` - 从2D数据构建3D模型
- `rebuild_model()` - 重新构建模型

#### 导出
- `export_stl(shape_id, filepath, ...)` - 导出STL
- `export_step(shape_id, filepath)` - 导出STEP
- `export_iges(shape_id, filepath)` - 导出IGES

#### 撤销/重做
- `undo()` - 撤销
- `redo()` - 重做
- `can_undo()` - 检查是否可以撤销
- `can_redo()` - 检查是否可以重做

#### 序列化
- `save(filepath)` - 保存模型
- `load(filepath)` - 加载模型

## 性能优化

- **增量更新**: 仅更新修改的特征及其依赖
- **空间分割**: 使用BVH加速几何查询
- **缓存机制**: 缓存中间计算结果
- **并行计算**: 利用多线程处理独立特征

## 版本历史

### v1.0.0
- 初始版本
- 支持基本建模特征
- 支持铸造专用特征
- 支持多格式导出
- 支持插件化架构

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！

## 联系方式

如有问题或建议，请联系开发团队。
