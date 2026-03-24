# 铸造行业CAD导出模块技术设计方案

## 文档信息
- **版本**: 1.0.0
- **日期**: 2024
- **作者**: CAD Format Expert
- **适用范围**: 铸造行业2D到3D转换应用

---

## 目录

1. [概述](#1-概述)
2. [架构设计](#2-架构设计)
3. [格式规范实现](#3-格式规范实现)
4. [核心类设计](#4-核心类设计)
5. [接口定义](#5-接口定义)
6. [错误处理与验证](#6-错误处理与验证)
7. [进度报告机制](#7-进度报告机制)
8. [配置管理](#8-配置管理)
9. [扩展性设计](#9-扩展性设计)
10. [与上游模块集成](#10-与上游模块集成)
11. [兼容性测试](#11-兼容性测试)

---

## 1. 概述

### 1.1 设计目标

本CAD导出模块专为铸造行业2D到3D转换应用设计，支持将3D模型导出为以下行业标准格式：

| 格式 | 版本/标准 | 用途 |
|------|----------|------|
| STL | ASCII & Binary | 3D打印、快速原型、铸造仿真 |
| STEP | AP203, AP214 | CAD数据交换、完整B-rep |
| IGES | 5.3 | 传统CAD系统兼容 |

### 1.2 设计原则

1. **模块化设计**: 每种格式有独立的导出器实现
2. **统一接口**: 所有导出器继承自基类，提供一致API
3. **可扩展性**: 易于添加新格式支持
4. **健壮性**: 完善的错误处理和验证机制
5. **性能优化**: 支持大模型导出和进度报告

### 1.3 软件兼容性目标

| 软件 | 支持格式 | 验证状态 |
|------|----------|----------|
| SolidWorks | STL, STEP, IGES | ✓ |
| AutoCAD | STL, IGES | ✓ |
| Fusion 360 | STL, STEP | ✓ |
| ProCAST | STL | ✓ |
| MAGMA | STL, STEP | ✓ |
| ANSYS | STL, STEP, IGES | ✓ |

---

## 2. 架构设计

### 2.1 模块架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    CAD Export Manager                        │
│                   (统一接口管理器)                            │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  STL Exporter │    │ STEP Exporter │    │ IGES Exporter │
│  (stl_        │    │ (AP203/       │    │ (Version 5.3) │
│   exporter.py)│    │  AP214)       │    │               │
│               │    │ (step_        │    │ (iges_        │
│               │    │  exporter.py) │    │  exporter.py) │
└───────────────┘    └───────────────┘    └───────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  CADExporter (Base Class)                    │
│              (cad_exporter_base.py)                          │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 类层次结构

```
CADExporter (ABC)
├── STLExporter
│   └── STLRepairTool
├── STEPExporter
│   └── STEPUtils
└── IGESExporter
    └── IGESUtils

ExporterFactory (工厂类)
CADExportManager (管理器类)
```

### 2.3 数据流

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  3D建模引擎   │────▶│  数据验证    │────▶│  格式导出    │
│  (OpenCASCADE)│     │              │     │              │
└──────────────┘     └──────────────┘     └──────────────┘
      │                      │                   │
      │                      │                   │
      ▼                      ▼                   ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  B-rep实体   │     │  错误报告    │     │  STL/STEP/   │
│  三角网格    │     │  警告信息    │     │  IGES文件    │
│  拓扑信息    │     │              │     │              │
└──────────────┘     └──────────────┘     └──────────────┘
```

---

## 3. 格式规范实现

### 3.1 STL格式

#### 3.1.1 ASCII STL格式

```
solid name
  facet normal nx ny nz
    outer loop
      vertex v1x v1y v1z
      vertex v2x v2y v2z
      vertex v3x v3y v3z
    endloop
  endfacet
endsolid name
```

**实现要点**:
- 法向量使用科学计数法（6位小数）
- 支持多实体（多个solid块）
- 自动计算法向量（如果无效）

#### 3.1.2 二进制STL格式

| 字段 | 大小 | 说明 |
|------|------|------|
| Header | 80 bytes | 描述信息 |
| Triangle Count | 4 bytes | 无符号整数 |
| Normal | 12 bytes | 3×float32 |
| Vertex 1 | 12 bytes | 3×float32 |
| Vertex 2 | 12 bytes | 3×float32 |
| Vertex 3 | 12 bytes | 3×float32 |
| Attribute | 2 bytes | 属性字节 |

**每个三角面片: 50 bytes**

### 3.2 STEP格式 (ISO 10303)

#### 3.2.1 文件结构

```
ISO-10303-21;
HEADER;
FILE_DESCRIPTION(...);
FILE_NAME(...);
FILE_SCHEMA(('AP214'));
ENDSEC;
DATA;
#1=ENTITY_TYPE(...);
#2=ENTITY_TYPE(...);
...
ENDSEC;
END-ISO-10303-21;
```

#### 3.2.2 AP203 vs AP214

| 特性 | AP203 | AP214 |
|------|-------|-------|
| 配置控制 | ✓ | ✓ |
| 几何表示 | ✓ | ✓ |
| 颜色信息 | ✗ | ✓ |
| 层信息 | ✗ | ✓ |
| 设计意图 | ✓ | ✓ |

**实现**: 通过`step_schema`选项选择

#### 3.2.3 核心实体

```python
# 几何上下文
GEOMETRIC_REPRESENTATION_CONTEXT

# 顶点
VERTEX_POINT -> CARTESIAN_POINT(x, y, z)

# 边
EDGE_CURVE -> LINE/CIRCLE/BSPLINE_CURVE

# 面
FACE_SURFACE -> PLANE/CYLINDRICAL_SURFACE/SPHERICAL_SURFACE

# 壳
CLOSED_SHELL

# 实体
MANIFOLD_SOLID_BREP
```

### 3.3 IGES格式 (5.3)

#### 3.3.1 文件结构

```
[Start Section]     - S lines
[Global Section]    - G lines
[Directory Section] - D lines (每实体2行)
[Parameter Section] - P lines
[Terminate Section] - T line
```

#### 3.3.2 行格式

每行80字符:
- 1-72: 数据
- 73: 段标识符 (S/G/D/P/T)
- 74-80: 序列号

#### 3.3.3 目录条目 (DE) 格式

| 位置 | 内容 |
|------|------|
| 1-8 | 实体类型号 |
| 9-16 | 参数数据指针 |
| 17-24 | 结构 |
| 25-32 | 线型 |
| 33-40 | 层 |
| 41-48 | 视图 |
| 49-56 | 变换矩阵 |
| 57-64 | 标签显示 |
| 65-72 | 状态号 |

---

## 4. 核心类设计

### 4.1 数据类

```python
@dataclass
class Vector3D:
    """3D向量/点"""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

@dataclass
class Triangle:
    """三角面片"""
    normal: Vector3D
    v1: Vector3D
    v2: Vector3D
    v3: Vector3D
    attribute: int = 0

@dataclass
class MeshData:
    """网格数据容器"""
    name: str = ""
    triangles: List[Triangle] = field(default_factory=list)
    vertices: List[Vector3D] = field(default_factory=list)

@dataclass
class BRepSolid:
    """B-rep实体"""
    name: str = ""
    faces: List[BRepFace] = field(default_factory=list)
    edges: List[BRepEdge] = field(default_factory=list)
    vertices: List[Vector3D] = field(default_factory=list)
```

### 4.2 导出器基类

```python
class CADExporter(ABC):
    """CAD导出器抽象基类"""
    
    @property
    @abstractmethod
    def format_name(self) -> str: pass
    
    @property
    @abstractmethod
    def file_extension(self) -> str: pass
    
    @abstractmethod
    def export_mesh(self, mesh: MeshData, filepath: Path) -> bool: pass
    
    @abstractmethod
    def export_brep(self, solid: BRepSolid, filepath: Path) -> bool: pass
    
    def validate_mesh(self, mesh: MeshData) -> bool: pass
    def validate_brep(self, solid: BRepSolid) -> bool: pass
```

### 4.3 导出选项

```python
@dataclass
class ExportOptions:
    """导出选项配置"""
    format: ExportFormat = ExportFormat.STL_BINARY
    unit: UnitType = UnitType.MILLIMETER
    precision: float = 0.001
    tolerance: float = 0.01
    angular_tolerance: float = 0.5
    
    # STL选项
    stl_ascii: bool = False
    stl_solid_name: str = ""
    
    # STEP选项
    step_schema: str = "AP214"
    step_write_colors: bool = True
    
    # IGES选项
    iges_unit_flag: int = 2
    iges_write_colors: bool = True
```

---

## 5. 接口定义

### 5.1 与上游模块接口

```python
# 从3D建模引擎接收的数据
class ModelDataFromEngine:
    """上游模块传入的数据"""
    
    # B-rep实体 (OpenCASCADE TopoDS_Shape)
    brep_shape: Any  # OpenCASCADE TopoDS_Shape
    
    # 三角网格 (用于STL)
    mesh_vertices: List[Tuple[float, float, float]]
    mesh_triangles: List[Tuple[int, int, int]]
    mesh_normals: List[Tuple[float, float, float]]
    
    # 拓扑信息
    faces: List[FaceInfo]
    edges: List[EdgeInfo]
    
    # 单位和精度
    unit: str  # "mm", "cm", "m", "inch"
    precision: float
    
    # 元数据
    name: str
    description: str
    material: str
```

### 5.2 导出管理器接口

```python
class CADExportManager:
    """统一导出接口"""
    
    def export_mesh(self, 
        mesh: MeshData, 
        filepath: Union[str, Path],
        format_type: Optional[ExportFormat] = None,
        options: Optional[Dict] = None
    ) -> bool: pass
    
    def export_brep(self,
        solid: BRepSolid,
        filepath: Union[str, Path],
        format_type: Optional[ExportFormat] = None,
        options: Optional[Dict] = None
    ) -> bool: pass
    
    def export_multiple(self,
        items: List[Union[MeshData, BRepSolid]],
        filepaths: List[Union[str, Path]],
        format_types: Optional[List[ExportFormat]] = None
    ) -> List[bool]: pass
```

### 5.3 便捷函数

```python
def export_mesh(mesh, filepath, format_type=None, **options) -> bool: pass
def export_brep(solid, filepath, format_type=None, **options) -> bool: pass
def convert_stl_to_step(stl_path, step_path) -> bool: pass
def get_file_info(filepath) -> Dict[str, Any]: pass
```

---

## 6. 错误处理与验证

### 6.1 异常层次

```
ExportError (基类)
├── ValidationError
├── FormatError
└── IOError
```

### 6.2 验证规则

#### 网格验证

| 检查项 | 规则 | 错误级别 |
|--------|------|----------|
| 空网格 | triangles非空 | Error |
| 退化三角形 | 面积 > tolerance | Warning |
| 无效法向量 | 长度 ≈ 1 | Warning |
| 顶点索引 | 在有效范围内 | Error |

#### B-rep验证

| 检查项 | 规则 | 错误级别 |
|--------|------|----------|
| 空实体 | faces非空 | Error |
| 空顶点 | vertices非空 | Error |
| 顶点索引 | 在有效范围内 | Error |
| 面边界 | 外环闭合 | Warning |

### 6.3 错误报告

```python
def validate_mesh(self, mesh: MeshData) -> bool:
    self.clear_messages()
    
    if not mesh.triangles:
        self._add_error("Mesh contains no triangles")
        return False
    
    # 检查退化三角形
    degenerate_count = 0
    for tri in mesh.triangles:
        area = compute_triangle_area(tri)
        if area < self.options.tolerance:
            degenerate_count += 1
    
    if degenerate_count > 0:
        self._add_warning(f"Found {degenerate_count} degenerate triangles")
    
    return not self.has_errors()
```

---

## 7. 进度报告机制

### 7.1 进度数据结构

```python
@dataclass
class ExportProgress:
    stage: str = ""          # 当前阶段
    current: int = 0         # 当前进度
    total: int = 0           # 总任务数
    percentage: float = 0.0  # 百分比
    message: str = ""        # 描述信息
    elapsed_time: float = 0.0
    estimated_time: float = 0.0
```

### 7.2 回调函数

```python
def progress_callback(progress: ExportProgress):
    print(f"[{progress.stage}] {progress.percentage:.1f}% - {progress.message}")

# 使用
manager = CADExportManager()
manager.set_progress_callback(progress_callback)
```

### 7.3 进度阶段

| 阶段 | 说明 |
|------|------|
| Validation | 数据验证 |
| Creating vertices | 创建顶点 |
| Creating edges | 创建边 |
| Creating faces | 创建面 |
| Writing entities | 写入实体 |
| Complete | 完成 |

---

## 8. 配置管理

### 8.1 配置文件格式

```json
{
  "default_format": "stl_binary",
  "default_unit": "millimeter",
  "default_precision": 0.001,
  "default_tolerance": 0.01,
  "stl_ascii": false,
  "step_schema": "AP214",
  "iges_unit": 2,
  "write_colors": true,
  "auto_fix_mesh": true,
  "validate_before_export": true
}
```

### 8.2 配置API

```python
manager = CADExportManager()

# 加载配置
manager.load_config("config.json")

# 更新配置
manager.update_config(
    default_unit='millimeter',
    stl_ascii=False
)

# 保存配置
manager.save_config("config.json")
```

---

## 9. 扩展性设计

### 9.1 添加新格式

```python
# 1. 创建导出器类
class NewFormatExporter(CADExporter):
    @property
    def format_name(self) -> str:
        return "New Format"
    
    @property
    def file_extension(self) -> str:
        return ".new"
    
    def export_mesh(self, mesh, filepath) -> bool:
        # 实现导出逻辑
        pass
    
    def export_brep(self, solid, filepath) -> bool:
        # 实现导出逻辑
        pass

# 2. 注册导出器
ExporterFactory.register(ExportFormat.NEW_FORMAT, NewFormatExporter)

# 3. 使用
exporter = ExporterFactory.create(ExportFormat.NEW_FORMAT)
```

### 9.2 格式版本升级

```python
class STEPExporter:
    SUPPORTED_SCHEMAS = {
        'AP203': 'CONFIG_CONTROL_DESIGN',
        'AP214': 'AUTOMOTIVE_DESIGN',
        'AP242': 'AP242_MANAGED_MODEL_BASED_3D_ENGINEERING'
    }
    
    def __init__(self, options=None):
        self._schema = options.step_schema if options else 'AP214'
```

---

## 10. 与上游模块集成

### 10.1 OpenCASCADE集成

```python
# 从OpenCASCADE TopoDS_Shape提取数据
def extract_from_occ_shape(shape) -> BRepSolid:
    solid = BRepSolid()
    
    # 遍历面
    exp = TopExp_Explorer(shape, TopAbs_FACE)
    while exp.More():
        face = topods.Face(exp.Current())
        # 提取面数据...
        solid.faces.append(brep_face)
        exp.Next()
    
    return solid
```

### 10.2 数据转换流程

```
OpenCASCADE Shape
       │
       ▼
┌──────────────┐
│  拓扑遍历     │
│  (BRepTools) │
└──────────────┘
       │
       ▼
┌──────────────┐
│  几何提取     │
│  (BRepAdaptor)│
└──────────────┘
       │
       ▼
┌──────────────┐
│  三角化       │
│  (BRepMesh)   │
└──────────────┘
       │
       ▼
┌──────────────┐
│  格式导出     │
│  (本模块)     │
└──────────────┘
```

---

## 11. 兼容性测试

### 11.1 测试矩阵

| 格式 | SolidWorks | AutoCAD | Fusion 360 | ProCAST | MAGMA |
|------|------------|---------|------------|---------|-------|
| STL ASCII | ✓ | ✓ | ✓ | ✓ | ✓ |
| STL Binary | ✓ | ✓ | ✓ | ✓ | ✓ |
| STEP AP203 | ✓ | ✓ | ✓ | - | ✓ |
| STEP AP214 | ✓ | ✓ | ✓ | - | ✓ |
| IGES 5.3 | ✓ | ✓ | ✓ | - | - |

### 11.2 验证工具

```python
# 验证导出的文件
info = get_file_info("output.step")
print(f"Valid: {info['valid']}")
print(f"Format: {info['format']}")
print(f"Entity counts: {info['entity_counts']}")
```

---

## 附录A: 文件清单

| 文件名 | 说明 |
|--------|------|
| cad_exporter_base.py | 基类和数据类型定义 |
| stl_exporter.py | STL格式导出器 |
| step_exporter.py | STEP格式导出器 |
| iges_exporter.py | IGES格式导出器 |
| cad_export_manager.py | 导出管理器 |
| example_usage.py | 使用示例 |

## 附录B: 依赖项

```
numpy >= 1.20.0
```

## 附录C: 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0.0 | 2024 | 初始版本 |

---

*文档结束*
