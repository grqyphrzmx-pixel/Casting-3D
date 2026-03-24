# 铸造行业3D建模引擎核心架构设计

## 1. 概述

### 1.1 设计目标
本3D建模引擎专为铸造行业2D到3D转换应用设计，负责将2D特征数据转换为精确的3D实体模型，支持铸造零件的典型几何形状。

### 1.2 核心能力
- **几何内核**: OpenCASCADE Technology (OCCT) 7.6+
- **编程语言**: Python 3.9+ (使用pythonOCC绑定)
- **建模精度**: 双精度浮点数 (1e-7 mm)
- **输出格式**: STL, STEP, IGES, BREP

### 1.3 架构原则
1. **模块化设计**: 松耦合、高内聚的组件架构
2. **插件化扩展**: 支持新特征类型的动态加载
3. **参数化建模**: 支持尺寸驱动的模型更新
4. **命令模式**: 支持撤销/重做操作
5. **版本兼容**: 向前/向后兼容的序列化机制

---

## 2. 几何内核架构

### 2.1 内核选择: OpenCASCADE Technology

```
┌─────────────────────────────────────────────────────────────────┐
│                    OpenCASCADE Technology                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  TKGeomBase │  │   TKBRep    │  │  TKPrim     │             │
│  │  几何基础   │  │  B-rep表示  │  │  基本体素   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  TKBool     │  │  TKOffset   │  │  TKFeat     │             │
│  │  布尔运算   │  │  偏移/加厚  │  │  特征建模   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  TKMesh     │  │  TKSTEP     │  │  TKIGES     │             │
│  │  网格生成   │  │  STEP接口   │  │  IGES接口   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 B-rep数据结构

```
TopoDS_Shape (拓扑形状基类)
    ├── TopoDS_Compound (复合体)
    ├── TopoDS_CompSolid (复合实体)
    ├── TopoDS_Solid (实体)
    │   └── TopoDS_Shell (外壳)
    │       └── TopoDS_Face (面)
    │           └── TopoDS_Wire (线框)
    │               └── TopoDS_Edge (边)
    │                   └── TopoDS_Vertex (顶点)
    └── TopoDS_Shell (开外壳)
```

### 2.3 几何-拓扑关系

```
TopoDS_Face ──► Geom_Surface (几何曲面)
    │              ├── Geom_Plane (平面)
    │              ├── Geom_CylindricalSurface (圆柱面)
    │              ├── Geom_ConicalSurface (圆锥面)
    │              ├── Geom_SphericalSurface (球面)
    │              ├── Geom_ToroidalSurface (环面)
    │              └── Geom_BSplineSurface (B样条曲面)
    │
    └── TopoDS_Wire ──► TopoDS_Edge ──► Geom_Curve (几何曲线)
                                          ├── Geom_Line (直线)
                                          ├── Geom_Circle (圆)
                                          ├── Geom_Ellipse (椭圆)
                                          ├── Geom_BSplineCurve (B样条曲线)
                                          └── Geom_TrimmedCurve (裁剪曲线)
```

---

## 3. 核心类架构设计

### 3.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Casting3DEngine                              │
│                         (主引擎类)                                   │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │ FeatureManager  │  │  ModelBuilder   │  │ ExportManager   │     │
│  │   (特征管理)    │  │   (模型构建)    │  │   (导出管理)    │     │
│  └────────┬────────┘  └────────┬────────┘  └─────────────────┘     │
│           │                    │                                     │
│           ▼                    ▼                                     │
│  ┌─────────────────┐  ┌─────────────────┐                          │
│  │ FeatureFactory  │  │ GeometryKernel  │                          │
│  │   (特征工厂)    │◄─┤   (几何内核)    │                          │
│  └────────┬────────┘  └─────────────────┘                          │
│           │                                                          │
│           ▼                                                          │
│  ┌─────────────────────────────────────────┐                        │
│  │           Feature Plugins               │                        │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐   │                        │
│  │  │Extrude  │ │Revolve  │ │Sweep    │   │  ... 更多特征插件       │
│  │  │Feature  │ │Feature  │ │Feature  │   │                        │
│  │  └─────────┘ └─────────┘ └─────────┘   │                        │
│  └─────────────────────────────────────────┘                        │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │ CommandManager  │  │ ParameterSystem │  │ HistoryManager  │     │
│  │   (命令管理)    │  │   (参数系统)    │  │   (历史管理)    │     │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 核心类定义

#### 3.2.1 基础数据类

```python
# ============================================
# 基础数据结构和枚举定义
# ============================================

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any, Callable
from abc import ABC, abstractmethod
import numpy as np
from uuid import uuid4

class FeatureType(Enum):
    """特征类型枚举"""
    # 基体特征
    EXTRUDE = auto()      # 拉伸
    REVOLVE = auto()      # 旋转
    SWEEP = auto()        # 扫掠
    LOFT = auto()         # 放样
    PRIMITIVE_BOX = auto()      # 基本体-立方体
    PRIMITIVE_CYLINDER = auto() # 基本体-圆柱
    PRIMITIVE_SPHERE = auto()   # 基本体-球体
    
    # 附加特征
    HOLE = auto()         # 孔
    SLOT = auto()         # 槽
    POCKET = auto()       # 腔体
    BOSS = auto()         # 凸台
    FILLET = auto()       # 圆角
    CHAMFER = auto()      # 倒角
    
    # 铸造专用特征
    DRAFT = auto()        # 拔模斜度
    PARTING_LINE = auto() # 分型线
    PARTING_SURFACE = auto() # 分型面
    RIB = auto()          # 加强筋
    
    # 布尔特征
    BOOLEAN_UNION = auto()      # 布尔并
    BOOLEAN_SUBTRACT = auto()   # 布尔减
    BOOLEAN_INTERSECT = auto()  # 布尔交

class GeometryType(Enum):
    """几何类型枚举"""
    POINT = auto()
    LINE = auto()
    CIRCLE = auto()
    ARC = auto()
    ELLIPSE = auto()
    BEZIER = auto()
    BSPLINE = auto()
    POLYLINE = auto()

@dataclass
class Point3D:
    """3D点"""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    
    def to_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)
    
    def to_numpy(self) -> np.ndarray:
        return np.array([self.x, self.y, self.z])
    
    @staticmethod
    def from_tuple(t: Tuple[float, float, float]) -> 'Point3D':
        return Point3D(t[0], t[1], t[2])

@dataclass
class Vector3D:
    """3D向量"""
    x: float = 0.0
    y: float = 0.0
    z: float = 1.0
    
    def normalize(self) -> 'Vector3D':
        length = np.sqrt(self.x**2 + self.y**2 + self.z**2)
        if length > 1e-10:
            return Vector3D(self.x/length, self.y/length, self.z/length)
        return Vector3D(0, 0, 1)
    
    def to_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)

@dataclass
class Plane:
    """平面定义"""
    origin: Point3D = field(default_factory=Point3D)
    normal: Vector3D = field(default_factory=Vector3D)
    x_dir: Vector3D = field(default_factory=lambda: Vector3D(1, 0, 0))

@dataclass
class Profile2D:
    """2D轮廓数据"""
    vertices: List[Point3D] = field(default_factory=list)
    geometry_type: GeometryType = GeometryType.POLYLINE
    is_closed: bool = False
    
    # 圆弧/曲线参数
    arcs: List[Dict[str, Any]] = field(default_factory=list)
    
    # 约束信息
    constraints: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class FeatureParameters:
    """特征参数基类"""
    feature_id: str = field(default_factory=lambda: str(uuid4()))
    feature_type: FeatureType = FeatureType.EXTRUDE
    name: str = ""
    parent_id: Optional[str] = None
    is_suppressed: bool = False
    
    # 变换参数
    position: Point3D = field(default_factory=Point3D)
    rotation: Tuple[float, float, float] = (0, 0, 0)  # Euler angles

@dataclass
class ExtrudeParameters(FeatureParameters):
    """拉伸特征参数"""
    profile: Profile2D = field(default_factory=Profile2D)
    plane: Plane = field(default_factory=Plane)
    direction: Vector3D = field(default_factory=lambda: Vector3D(0, 0, 1))
    depth: float = 10.0
    taper_angle: float = 0.0  # 拔模角度
    is_symmetric: bool = False
    is_cut: bool = False  # 是否为切除

@dataclass
class RevolveParameters(FeatureParameters):
    """旋转特征参数"""
    profile: Profile2D = field(default_factory=Profile2D)
    axis_origin: Point3D = field(default_factory=Point3D)
    axis_direction: Vector3D = field(default_factory=lambda: Vector3D(0, 0, 1))
    angle: float = 360.0
    is_cut: bool = False

@dataclass
class HoleParameters(FeatureParameters):
    """孔特征参数"""
    center: Point3D = field(default_factory=Point3D)
    direction: Vector3D = field(default_factory=lambda: Vector3D(0, 0, 1))
    diameter: float = 10.0
    depth: float = 10.0  # 0表示通孔
    hole_type: str = "simple"  # simple, counterbore, countersink
    counterbore_diameter: float = 0.0
    counterbore_depth: float = 0.0
    countersink_angle: float = 90.0

@dataclass
class FilletParameters(FeatureParameters):
    """圆角特征参数"""
    edge_ids: List[str] = field(default_factory=list)
    radius: float = 2.0
    is_variable: bool = False
    variable_radii: Dict[str, Tuple[float, float]] = field(default_factory=dict)

@dataclass
class DraftParameters(FeatureParameters):
    """拔模特征参数 (铸造专用)"""
    face_ids: List[str] = field(default_factory=list)
    neutral_plane: Plane = field(default_factory=Plane)
    pull_direction: Vector3D = field(default_factory=lambda: Vector3D(0, 0, 1))
    draft_angle: float = 2.0  # 度
    is_inward: bool = True

@dataclass
class BooleanParameters(FeatureParameters):
    """布尔运算参数"""
    target_body_id: str = ""
    tool_body_id: str = ""
    operation: str = "union"  # union, subtract, intersect
```

---

## 4. 核心引擎类实现

### 4.1 几何内核封装

```python
# ============================================
# geometry_kernel.py - 几何内核封装
# ============================================

from OCC.Core.gp import (
    gp_Pnt, gp_Vec, gp_Dir, gp_Ax1, gp_Ax2, gp_Ax3,
    gp_Trsf, gp_Quaternion, gp_Mat
)
from OCC.Core.BRepBuilderAPI import (
    BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire,
    BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeShell,
    BRepBuilderAPI_MakeSolid, BRepBuilderAPI_Transform,
    BRepBuilderAPI_MakePolygon
)
from OCC.Core.BRepPrimAPI import (
    BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder,
    BRepPrimAPI_MakeSphere, BRepPrimAPI_MakeCone,
    BRepPrimAPI_MakeTorus, BRepPrimAPI_MakePrism,
    BRepPrimAPI_MakeRevol
)
from OCC.Core.BRepAlgoAPI import (
    BRepAlgoAPI_Fuse, BRepAlgoAPI_Cut, BRepAlgoAPI_Common
)
from OCC.Core.BRepFilletAPI import (
    BRepFilletAPI_MakeFillet, BRepFilletAPI_MakeChamfer
)
from OCC.Core.BRepOffsetAPI import (
    BRepOffsetAPI_MakeDraft, BRepOffsetAPI_MakeThickSolid
)
from OCC.Core.BRepTools import BRepTools_WireExplorer
from OCC.Core.TopoDS import (
    TopoDS_Shape, TopoDS_Face, TopoDS_Wire, TopoDS_Edge,
    TopoDS_Vertex, TopoDS_Solid, TopoDS_Compound
)
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_FACE, TopAbs_EDGE, TopAbs_VERTEX
from OCC.Core.GC import GC_MakeArcOfCircle, GC_MakeSegment
from OCC.Core.Geom import Geom_Curve, Geom_Surface
from OCC.Core.BRep import BRep_Tool
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.StlAPI import StlAPI_Writer
from OCC.Core.STEPControl import STEPControl_Writer, STEPControl_AsIs
from OCC.Core.IGESControl import IGESControl_Writer
from OCC.Core.Interface import Interface_Static
from OCC.Core.BRepCheck import BRepCheck_Analyzer
from OCC.Core.BRepGProp import BRepGProp_Face, BRepGProp_VolumeProperties
from OCC.Core.GProp import GProp_GProps
import logging

logger = logging.getLogger(__name__)

class OCCConverter:
    """OCC类型转换器"""
    
    @staticmethod
    def point_to_gp(p: Point3D) -> gp_Pnt:
        return gp_Pnt(p.x, p.y, p.z)
    
    @staticmethod
    def gp_to_point(gp: gp_Pnt) -> Point3D:
        return Point3D(gp.X(), gp.Y(), gp.Z())
    
    @staticmethod
    def vector_to_gp(v: Vector3D) -> gp_Vec:
        return gp_Vec(v.x, v.y, v.z)
    
    @staticmethod
    def gp_to_vector(gp: gp_Vec) -> Vector3D:
        return Vector3D(gp.X(), gp.Y(), gp.Z())
    
    @staticmethod
    def plane_to_gp(plane: Plane) -> gp_Ax3:
        origin = OCCConverter.point_to_gp(plane.origin)
        normal = gp_Dir(plane.normal.x, plane.normal.y, plane.normal.z)
        x_dir = gp_Dir(plane.x_dir.x, plane.x_dir.y, plane.x_dir.z)
        return gp_Ax3(origin, normal, x_dir)

class GeometryKernel:
    """
    OpenCASCADE几何内核封装类
    提供高级几何操作接口
    """
    
    def __init__(self):
        self._shapes: Dict[str, TopoDS_Shape] = {}
        self._shape_properties: Dict[str, Dict] = {}
        self._precision = 1e-7
        
    def register_shape(self, shape_id: str, shape: TopoDS_Shape) -> bool:
        """注册形状到内核"""
        if self._validate_shape(shape):
            self._shapes[shape_id] = shape
            self._update_properties(shape_id)
            return True
        return False
    
    def get_shape(self, shape_id: str) -> Optional[TopoDS_Shape]:
        """获取已注册的形状"""
        return self._shapes.get(shape_id)
    
    def remove_shape(self, shape_id: str) -> bool:
        """移除形状"""
        if shape_id in self._shapes:
            del self._shapes[shape_id]
            if shape_id in self._shape_properties:
                del self._shape_properties[shape_id]
            return True
        return False
    
    def _validate_shape(self, shape: TopoDS_Shape) -> bool:
        """验证形状有效性"""
        if shape.IsNull():
            return False
        analyzer = BRepCheck_Analyzer(shape)
        return analyzer.IsValid()
    
    def _update_properties(self, shape_id: str):
        """更新形状属性"""
        shape = self._shapes.get(shape_id)
        if shape is None:
            return
        
        props = GProp_GProps()
        BRepGProp_VolumeProperties(shape, props)
        
        self._shape_properties[shape_id] = {
            'volume': props.Mass(),
            'centroid': (
                props.CentreOfMass().X(),
                props.CentreOfMass().Y(),
                props.CentreOfMass().Z()
            ),
            'moment_of_inertia': props.MatrixOfInertia()
        }
    
    def get_volume(self, shape_id: str) -> float:
        """获取形状体积"""
        props = self._shape_properties.get(shape_id, {})
        return props.get('volume', 0.0)
    
    def create_edge_from_points(self, p1: Point3D, p2: Point3D) -> TopoDS_Edge:
        """从两点创建边"""
        gp_p1 = OCCConverter.point_to_gp(p1)
        gp_p2 = OCCConverter.point_to_gp(p2)
        segment = GC_MakeSegment(gp_p1, gp_p2).Value()
        return BRepBuilderAPI_MakeEdge(segment).Edge()
    
    def create_edge_from_arc(self, center: Point3D, radius: float, 
                            start_angle: float, end_angle: float,
                            normal: Vector3D = None) -> TopoDS_Edge:
        """从圆弧参数创建边"""
        if normal is None:
            normal = Vector3D(0, 0, 1)
        
        gp_center = OCCConverter.point_to_gp(center)
        gp_normal = gp_Dir(normal.x, normal.y, normal.z)
        gp_x_dir = gp_Dir(1, 0, 0)
        
        if abs(normal.z) > 0.99:
            gp_x_dir = gp_Dir(1, 0, 0)
        else:
            gp_x_dir = gp_Dir(-normal.y, normal.x, 0)
        
        circle_axis = gp_Ax2(gp_center, gp_normal, gp_x_dir)
        arc = GC_MakeArcOfCircle(circle_axis, radius, 
                                  np.radians(start_angle), 
                                  np.radians(end_angle)).Value()
        return BRepBuilderAPI_MakeEdge(arc).Edge()
    
    def create_wire_from_profile(self, profile: Profile2D, 
                                  plane: Plane = None) -> TopoDS_Wire:
        """从2D轮廓创建线框"""
        if plane is None:
            plane = Plane()
        
        wire_maker = BRepBuilderAPI_MakeWire()
        vertices = profile.vertices
        
        # 处理圆弧
        arc_index = 0
        for i in range(len(vertices)):
            p1 = vertices[i]
            p2 = vertices[(i + 1) % len(vertices)] if profile.is_closed else vertices[i + 1]
            
            if i >= len(vertices) - 1 and not profile.is_closed:
                break
            
            # 检查是否有圆弧连接
            if arc_index < len(profile.arcs):
                arc = profile.arcs[arc_index]
                if arc.get('start_idx') == i:
                    # 创建圆弧边
                    center = arc.get('center', Point3D())
                    radius = arc.get('radius', 0)
                    start_angle = arc.get('start_angle', 0)
                    end_angle = arc.get('end_angle', 0)
                    edge = self.create_edge_from_arc(center, radius, 
                                                      start_angle, end_angle)
                    arc_index += 1
                else:
                    edge = self.create_edge_from_points(p1, p2)
            else:
                edge = self.create_edge_from_points(p1, p2)
            
            wire_maker.Add(edge)
        
        return wire_maker.Wire()
    
    def create_face_from_wire(self, wire: TopoDS_Wire, 
                              plane: Plane = None) -> TopoDS_Face:
        """从线框创建面"""
        if plane is None:
            plane = Plane()
        
        gp_plane = OCCConverter.plane_to_gp(plane)
        return BRepBuilderAPI_MakeFace(gp_plane, wire).Face()
    
    def extrude_face(self, face: TopoDS_Face, direction: Vector3D, 
                     depth: float, taper_angle: float = 0.0) -> TopoDS_Shape:
        """拉伸面创建实体"""
        gp_dir = gp_Dir(direction.x, direction.y, direction.z)
        
        if abs(taper_angle) < 0.001:
            # 直拉伸
            vec = gp_Vec(gp_dir) * depth
            prism = BRepPrimAPI_MakePrism(face, vec)
            return prism.Shape()
        else:
            # 带拔模的拉伸
            # 使用BRepOffsetAPI_MakeDraft实现拔模
            # 简化处理：先直拉伸再拔模
            vec = gp_Vec(gp_dir) * depth
            prism = BRepPrimAPI_MakePrism(face, vec)
            return prism.Shape()
    
    def revolve_face(self, face: TopoDS_Face, axis_origin: Point3D,
                     axis_direction: Vector3D, angle: float) -> TopoDS_Shape:
        """旋转面创建实体"""
        gp_origin = OCCConverter.point_to_gp(axis_origin)
        gp_dir = gp_Dir(axis_direction.x, axis_direction.y, axis_direction.z)
        axis = gp_Ax1(gp_origin, gp_dir)
        
        revol = BRepPrimAPI_MakeRevol(face, axis, np.radians(angle))
        return revol.Shape()
    
    def boolean_union(self, shape1: TopoDS_Shape, 
                      shape2: TopoDS_Shape) -> TopoDS_Shape:
        """布尔并运算"""
        fuse = BRepAlgoAPI_Fuse(shape1, shape2)
        if fuse.IsDone():
            return fuse.Shape()
        raise RuntimeError("Boolean union failed")
    
    def boolean_subtract(self, shape1: TopoDS_Shape, 
                         shape2: TopoDS_Shape) -> TopoDS_Shape:
        """布尔减运算"""
        cut = BRepAlgoAPI_Cut(shape1, shape2)
        if cut.IsDone():
            return cut.Shape()
        raise RuntimeError("Boolean subtract failed")
    
    def boolean_intersect(self, shape1: TopoDS_Shape, 
                          shape2: TopoDS_Shape) -> TopoDS_Shape:
        """布尔交运算"""
        common = BRepAlgoAPI_Common(shape1, shape2)
        if common.IsDone():
            return common.Shape()
        raise RuntimeError("Boolean intersect failed")
    
    def apply_fillet(self, shape: TopoDS_Shape, edges: List[TopoDS_Edge],
                     radius: float) -> TopoDS_Shape:
        """应用圆角"""
        fillet = BRepFilletAPI_MakeFillet(shape)
        for edge in edges:
            fillet.Add(radius, edge)
        return fillet.Shape()
    
    def apply_chamfer(self, shape: TopoDS_Shape, edges: List[TopoDS_Edge],
                      distance: float) -> TopoDS_Shape:
        """应用倒角"""
        chamfer = BRepFilletAPI_MakeChamfer(shape)
        for edge in edges:
            chamfer.Add(distance, edge)
        return chamfer.Shape()
    
    def apply_draft(self, shape: TopoDS_Shape, faces: List[TopoDS_Face],
                    neutral_plane: Plane, pull_direction: Vector3D,
                    angle: float, is_inward: bool = True) -> TopoDS_Shape:
        """应用拔模 (铸造专用)"""
        # 使用BRepOffsetAPI_MakeDraft实现拔模
        draft_angle = np.radians(angle) if is_inward else -np.radians(angle)
        
        # 简化实现：使用面偏移模拟拔模效果
        # 实际应用中需要更复杂的算法
        return shape
    
    def export_stl(self, shape_id: str, filepath: str, 
                   linear_deflection: float = 0.5,
                   angular_deflection: float = 0.5) -> bool:
        """导出为STL格式"""
        shape = self._shapes.get(shape_id)
        if shape is None:
            return False
        
        # 生成网格
        BRepMesh_IncrementalMesh(shape, linear_deflection, False, 
                                  angular_deflection)
        
        writer = StlAPI_Writer()
        return writer.Write(shape, filepath)
    
    def export_step(self, shape_id: str, filepath: str) -> bool:
        """导出为STEP格式"""
        shape = self._shapes.get(shape_id)
        if shape is None:
            return False
        
        writer = STEPControl_Writer()
        Interface_Static.SetCVal("write.step.schema", "AP214IS")
        writer.Transfer(shape, STEPControl_AsIs)
        return writer.Write(filepath)
    
    def export_iges(self, shape_id: str, filepath: str) -> bool:
        """导出为IGES格式"""
        shape = self._shapes.get(shape_id)
        if shape is None:
            return False
        
        writer = IGESControl_Writer()
        writer.AddShape(shape)
        return writer.Write(filepath)
```

---

## 5. 特征建模系统

### 5.1 特征基类与工厂

```python
# ============================================
# feature_base.py - 特征基类和接口
# ============================================

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
        return self._params.feature_id
    
    @property
    def feature_type(self) -> FeatureType:
        return self._params.feature_type
    
    @property
    def parameters(self) -> FeatureParameters:
        return self._params
    
    @parameters.setter
    def parameters(self, params: FeatureParameters):
        self._params = params
        self._is_dirty = True
    
    @property
    def result_shape_id(self) -> Optional[str]:
        return self._result_shape_id
    
    @property
    def is_dirty(self) -> bool:
        return self._is_dirty
    
    def add_child(self, feature: 'Feature'):
        """添加子特征"""
        self._children.append(feature)
        feature._parent = self
    
    def remove_child(self, feature: 'Feature'):
        """移除子特征"""
        if feature in self._children:
            self._children.remove(feature)
            feature._parent = None
    
    @abstractmethod
    def build(self) -> Optional[str]:
        """
        构建特征
        返回生成的形状ID
        """
        pass
    
    @abstractmethod
    def validate(self) -> Tuple[bool, str]:
        """
        验证参数有效性
        返回 (是否有效, 错误信息)
        """
        pass
    
    def update(self) -> Optional[str]:
        """更新特征（如果参数已更改）"""
        if self._is_dirty:
            return self.build()
        return self._result_shape_id
    
    def suppress(self):
        """抑制特征"""
        self._params.is_suppressed = True
        self._is_dirty = True
    
    def unsuppress(self):
        """取消抑制特征"""
        self._params.is_suppressed = False
        self._is_dirty = True
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            'feature_id': self.feature_id,
            'feature_type': self.feature_type.name,
            'parameters': self._serialize_parameters(),
            'children': [child.feature_id for child in self._children],
            'parent_id': self._parent.feature_id if self._parent else None,
            'is_suppressed': self._params.is_suppressed
        }
    
    @abstractmethod
    def _serialize_parameters(self) -> Dict[str, Any]:
        """序列化参数"""
        pass
    
    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any], 
                  kernel: GeometryKernel) -> 'Feature':
        """从字典反序列化"""
        pass


class FeatureFactory:
    """
    特征工厂类
    负责创建和管理特征实例
    """
    
    _registry: Dict[FeatureType, type] = {}
    
    @classmethod
    def register(cls, feature_type: FeatureType, 
                 feature_class: type):
        """注册特征类"""
        if not issubclass(feature_class, Feature):
            raise TypeError("Feature class must inherit from Feature")
        cls._registry[feature_type] = feature_class
    
    @classmethod
    def create(cls, feature_type: FeatureType, 
               params: FeatureParameters,
               kernel: GeometryKernel) -> Feature:
        """创建特征实例"""
        feature_class = cls._registry.get(feature_type)
        if feature_class is None:
            raise ValueError(f"Unknown feature type: {feature_type}")
        return feature_class(params, kernel)
    
    @classmethod
    def create_from_dict(cls, data: Dict[str, Any],
                         kernel: GeometryKernel) -> Feature:
        """从字典创建特征"""
        feature_type = FeatureType[data['feature_type']]
        feature_class = cls._registry.get(feature_type)
        if feature_class is None:
            raise ValueError(f"Unknown feature type: {feature_type}")
        return feature_class.from_dict(data, kernel)
    
    @classmethod
    def get_registered_types(cls) -> List[FeatureType]:
        """获取已注册的特征类型"""
        return list(cls._registry.keys())
```

### 5.2 具体特征实现

```python
# ============================================
# features.py - 具体特征实现
# ============================================

class ExtrudeFeature(Feature):
    """拉伸特征"""
    
    def __init__(self, params: ExtrudeParameters, kernel: GeometryKernel):
        super().__init__(params, kernel)
        self._params: ExtrudeParameters = params
    
    def validate(self) -> Tuple[bool, str]:
        """验证拉伸参数"""
        if len(self._params.profile.vertices) < 2:
            return False, "Profile must have at least 2 vertices"
        if self._params.depth <= 0:
            return False, "Depth must be positive"
        if abs(self._params.taper_angle) >= 90:
            return False, "Taper angle must be less than 90 degrees"
        return True, ""
    
    def build(self) -> Optional[str]:
        """构建拉伸特征"""
        if self._params.is_suppressed:
            return None
        
        valid, msg = self.validate()
        if not valid:
            logger.error(f"Extrude validation failed: {msg}")
            return None
        
        try:
            # 创建线框
            wire = self._kernel.create_wire_from_profile(
                self._params.profile, self._params.plane)
            
            # 创建面
            face = self._kernel.create_face_from_wire(wire, self._params.plane)
            
            # 拉伸
            shape = self._kernel.extrude_face(
                face, self._params.direction, 
                self._params.depth, self._params.taper_angle)
            
            # 注册形状
            self._result_shape_id = self._params.feature_id
            self._kernel.register_shape(self._result_shape_id, shape)
            self._is_dirty = False
            
            return self._result_shape_id
            
        except Exception as e:
            logger.error(f"Extrude build failed: {e}")
            return None
    
    def _serialize_parameters(self) -> Dict[str, Any]:
        return {
            'profile': {
                'vertices': [v.to_tuple() for v in self._params.profile.vertices],
                'is_closed': self._params.profile.is_closed,
                'arcs': self._params.profile.arcs
            },
            'plane': {
                'origin': self._params.plane.origin.to_tuple(),
                'normal': self._params.plane.normal.to_tuple(),
                'x_dir': self._params.plane.x_dir.to_tuple()
            },
            'direction': self._params.direction.to_tuple(),
            'depth': self._params.depth,
            'taper_angle': self._params.taper_angle,
            'is_symmetric': self._params.is_symmetric,
            'is_cut': self._params.is_cut
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], 
                  kernel: GeometryKernel) -> 'ExtrudeFeature':
        params_data = data['parameters']
        
        profile = Profile2D(
            vertices=[Point3D(*v) for v in params_data['profile']['vertices']],
            is_closed=params_data['profile']['is_closed'],
            arcs=params_data['profile'].get('arcs', [])
        )
        
        plane = Plane(
            origin=Point3D(*params_data['plane']['origin']),
            normal=Vector3D(*params_data['plane']['normal']),
            x_dir=Vector3D(*params_data['plane']['x_dir'])
        )
        
        params = ExtrudeParameters(
            feature_id=data['feature_id'],
            feature_type=FeatureType.EXTRUDE,
            name=data.get('name', ''),
            profile=profile,
            plane=plane,
            direction=Vector3D(*params_data['direction']),
            depth=params_data['depth'],
            taper_angle=params_data.get('taper_angle', 0),
            is_symmetric=params_data.get('is_symmetric', False),
            is_cut=params_data.get('is_cut', False)
        )
        
        return cls(params, kernel)


class RevolveFeature(Feature):
    """旋转特征"""
    
    def __init__(self, params: RevolveParameters, kernel: GeometryKernel):
        super().__init__(params, kernel)
        self._params: RevolveParameters = params
    
    def validate(self) -> Tuple[bool, str]:
        if len(self._params.profile.vertices) < 2:
            return False, "Profile must have at least 2 vertices"
        if self._params.angle <= 0 or self._params.angle > 360:
            return False, "Angle must be between 0 and 360 degrees"
        return True, ""
    
    def build(self) -> Optional[str]:
        if self._params.is_suppressed:
            return None
        
        valid, msg = self.validate()
        if not valid:
            logger.error(f"Revolve validation failed: {msg}")
            return None
        
        try:
            wire = self._kernel.create_wire_from_profile(
                self._params.profile, Plane())
            face = self._kernel.create_face_from_wire(wire, Plane())
            
            shape = self._kernel.revolve_face(
                face, self._params.axis_origin,
                self._params.axis_direction, self._params.angle)
            
            self._result_shape_id = self._params.feature_id
            self._kernel.register_shape(self._result_shape_id, shape)
            self._is_dirty = False
            
            return self._result_shape_id
            
        except Exception as e:
            logger.error(f"Revolve build failed: {e}")
            return None
    
    def _serialize_parameters(self) -> Dict[str, Any]:
        return {
            'profile': {
                'vertices': [v.to_tuple() for v in self._params.profile.vertices],
                'is_closed': self._params.profile.is_closed
            },
            'axis_origin': self._params.axis_origin.to_tuple(),
            'axis_direction': self._params.axis_direction.to_tuple(),
            'angle': self._params.angle,
            'is_cut': self._params.is_cut
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], 
                  kernel: GeometryKernel) -> 'RevolveFeature':
        params_data = data['parameters']
        
        profile = Profile2D(
            vertices=[Point3D(*v) for v in params_data['profile']['vertices']],
            is_closed=params_data['profile']['is_closed']
        )
        
        params = RevolveParameters(
            feature_id=data['feature_id'],
            feature_type=FeatureType.REVOLVE,
            profile=profile,
            axis_origin=Point3D(*params_data['axis_origin']),
            axis_direction=Vector3D(*params_data['axis_direction']),
            angle=params_data['angle'],
            is_cut=params_data.get('is_cut', False)
        )
        
        return cls(params, kernel)


class HoleFeature(Feature):
    """孔特征"""
    
    def __init__(self, params: HoleParameters, kernel: GeometryKernel):
        super().__init__(params, kernel)
        self._params: HoleParameters = params
    
    def validate(self) -> Tuple[bool, str]:
        if self._params.diameter <= 0:
            return False, "Diameter must be positive"
        if self._params.depth < 0:
            return False, "Depth must be non-negative"
        return True, ""
    
    def build(self) -> Optional[str]:
        if self._params.is_suppressed:
            return None
        
        valid, msg = self.validate()
        if not valid:
            logger.error(f"Hole validation failed: {msg}")
            return None
        
        try:
            # 创建圆柱体作为孔工具
            from OCC.Core.gp import gp_Ax2
            from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeCylinder
            
            origin = OCCConverter.point_to_gp(self._params.center)
            direction = gp_Dir(self._params.direction.x,
                              self._params.direction.y,
                              self._params.direction.z)
            
            # 计算圆柱高度
            height = self._params.depth if self._params.depth > 0 else 1000.0
            
            # 创建圆柱轴
            ax2 = gp_Ax2(origin, direction)
            cylinder = BRepPrimAPI_MakeCylinder(ax2, 
                                                 self._params.diameter / 2, 
                                                 height).Shape()
            
            self._result_shape_id = self._params.feature_id
            self._kernel.register_shape(self._result_shape_id, cylinder)
            self._is_dirty = False
            
            return self._result_shape_id
            
        except Exception as e:
            logger.error(f"Hole build failed: {e}")
            return None
    
    def _serialize_parameters(self) -> Dict[str, Any]:
        return {
            'center': self._params.center.to_tuple(),
            'direction': self._params.direction.to_tuple(),
            'diameter': self._params.diameter,
            'depth': self._params.depth,
            'hole_type': self._params.hole_type,
            'counterbore_diameter': self._params.counterbore_diameter,
            'counterbore_depth': self._params.counterbore_depth,
            'countersink_angle': self._params.countersink_angle
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], 
                  kernel: GeometryKernel) -> 'HoleFeature':
        params_data = data['parameters']
        
        params = HoleParameters(
            feature_id=data['feature_id'],
            feature_type=FeatureType.HOLE,
            center=Point3D(*params_data['center']),
            direction=Vector3D(*params_data['direction']),
            diameter=params_data['diameter'],
            depth=params_data['depth'],
            hole_type=params_data.get('hole_type', 'simple'),
            counterbore_diameter=params_data.get('counterbore_diameter', 0),
            counterbore_depth=params_data.get('counterbore_depth', 0),
            countersink_angle=params_data.get('countersink_angle', 90)
        )
        
        return cls(params, kernel)


class BooleanFeature(Feature):
    """布尔运算特征"""
    
    def __init__(self, params: BooleanParameters, kernel: GeometryKernel):
        super().__init__(params, kernel)
        self._params: BooleanParameters = params
    
    def validate(self) -> Tuple[bool, str]:
        if not self._params.target_body_id:
            return False, "Target body ID is required"
        if not self._params.tool_body_id:
            return False, "Tool body ID is required"
        if self._params.operation not in ['union', 'subtract', 'intersect']:
            return False, "Invalid boolean operation"
        return True, ""
    
    def build(self) -> Optional[str]:
        if self._params.is_suppressed:
            return None
        
        valid, msg = self.validate()
        if not valid:
            logger.error(f"Boolean validation failed: {msg}")
            return None
        
        try:
            target = self._kernel.get_shape(self._params.target_body_id)
            tool = self._kernel.get_shape(self._params.tool_body_id)
            
            if target is None or tool is None:
                logger.error("Target or tool shape not found")
                return None
            
            if self._params.operation == 'union':
                result = self._kernel.boolean_union(target, tool)
            elif self._params.operation == 'subtract':
                result = self._kernel.boolean_subtract(target, tool)
            else:  # intersect
                result = self._kernel.boolean_intersect(target, tool)
            
            self._result_shape_id = self._params.feature_id
            self._kernel.register_shape(self._result_shape_id, result)
            self._is_dirty = False
            
            return self._result_shape_id
            
        except Exception as e:
            logger.error(f"Boolean build failed: {e}")
            return None
    
    def _serialize_parameters(self) -> Dict[str, Any]:
        return {
            'target_body_id': self._params.target_body_id,
            'tool_body_id': self._params.tool_body_id,
            'operation': self._params.operation
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], 
                  kernel: GeometryKernel) -> 'BooleanFeature':
        params_data = data['parameters']
        
        params = BooleanParameters(
            feature_id=data['feature_id'],
            feature_type=FeatureType.BOOLEAN_UNION,
            target_body_id=params_data['target_body_id'],
            tool_body_id=params_data['tool_body_id'],
            operation=params_data['operation']
        )
        
        return cls(params, kernel)


class DraftFeature(Feature):
    """拔模特征 (铸造专用)"""
    
    def __init__(self, params: DraftParameters, kernel: GeometryKernel):
        super().__init__(params, kernel)
        self._params: DraftParameters = params
    
    def validate(self) -> Tuple[bool, str]:
        if not self._params.face_ids:
            return False, "At least one face must be selected"
        if abs(self._params.draft_angle) >= 90:
            return False, "Draft angle must be less than 90 degrees"
        return True, ""
    
    def build(self) -> Optional[str]:
        if self._params.is_suppressed:
            return None
        
        valid, msg = self.validate()
        if not valid:
            logger.error(f"Draft validation failed: {msg}")
            return None
        
        try:
            # 拔模实现需要获取面并应用拔模
            # 这里简化处理，实际实现需要更复杂的逻辑
            logger.info(f"Draft feature built with angle {self._params.draft_angle}")
            self._is_dirty = False
            return self._result_shape_id
            
        except Exception as e:
            logger.error(f"Draft build failed: {e}")
            return None
    
    def _serialize_parameters(self) -> Dict[str, Any]:
        return {
            'face_ids': self._params.face_ids,
            'neutral_plane': {
                'origin': self._params.neutral_plane.origin.to_tuple(),
                'normal': self._params.neutral_plane.normal.to_tuple()
            },
            'pull_direction': self._params.pull_direction.to_tuple(),
            'draft_angle': self._params.draft_angle,
            'is_inward': self._params.is_inward
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], 
                  kernel: GeometryKernel) -> 'DraftFeature':
        params_data = data['parameters']
        
        neutral_plane = Plane(
            origin=Point3D(*params_data['neutral_plane']['origin']),
            normal=Vector3D(*params_data['neutral_plane']['normal'])
        )
        
        params = DraftParameters(
            feature_id=data['feature_id'],
            feature_type=FeatureType.DRAFT,
            face_ids=params_data['face_ids'],
            neutral_plane=neutral_plane,
            pull_direction=Vector3D(*params_data['pull_direction']),
            draft_angle=params_data['draft_angle'],
            is_inward=params_data.get('is_inward', True)
        )
        
        return cls(params, kernel)


# 注册所有特征类
FeatureFactory.register(FeatureType.EXTRUDE, ExtrudeFeature)
FeatureFactory.register(FeatureType.REVOLVE, RevolveFeature)
FeatureFactory.register(FeatureType.HOLE, HoleFeature)
FeatureFactory.register(FeatureType.BOOLEAN_UNION, BooleanFeature)
FeatureFactory.register(FeatureType.BOOLEAN_SUBTRACT, BooleanFeature)
FeatureFactory.register(FeatureType.BOOLEAN_INTERSECT, BooleanFeature)
FeatureFactory.register(FeatureType.DRAFT, DraftFeature)
```

---

## 6. 命令模式与撤销/重做系统

```python
# ============================================
# command_system.py - 命令模式实现
# ============================================

class Command(ABC):
    """
    命令基类
    实现命令模式以支持撤销/重做
    """
    
    def __init__(self, name: str = ""):
        self._name = name
        self._is_executed = False
        self._timestamp = None
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def is_executed(self) -> bool:
        return self._is_executed
    
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


class CreateFeatureCommand(Command):
    """创建特征命令"""
    
    def __init__(self, feature_manager: 'FeatureManager',
                 params: FeatureParameters,
                 kernel: GeometryKernel):
        super().__init__(f"Create {params.feature_type.name}")
        self._feature_manager = feature_manager
        self._params = params
        self._kernel = kernel
        self._feature: Optional[Feature] = None
    
    def execute(self) -> bool:
        try:
            self._feature = FeatureFactory.create(
                self._params.feature_type, self._params, self._kernel)
            self._feature_manager.add_feature(self._feature)
            self._feature.build()
            self._is_executed = True
            return True
        except Exception as e:
            logger.error(f"Create feature command failed: {e}")
            return False
    
    def undo(self) -> bool:
        if self._feature:
            self._feature_manager.remove_feature(self._feature.feature_id)
            self._is_executed = False
            return True
        return False
    
    def redo(self) -> bool:
        return self.execute()


class DeleteFeatureCommand(Command):
    """删除特征命令"""
    
    def __init__(self, feature_manager: 'FeatureManager',
                 feature_id: str):
        super().__init__("Delete Feature")
        self._feature_manager = feature_manager
        self._feature_id = feature_id
        self._deleted_feature: Optional[Feature] = None
    
    def execute(self) -> bool:
        self._deleted_feature = self._feature_manager.get_feature(self._feature_id)
        if self._deleted_feature:
            self._feature_manager.remove_feature(self._feature_id)
            self._is_executed = True
            return True
        return False
    
    def undo(self) -> bool:
        if self._deleted_feature:
            self._feature_manager.add_feature(self._deleted_feature)
            self._is_executed = False
            return True
        return False
    
    def redo(self) -> bool:
        return self.execute()


class ModifyFeatureCommand(Command):
    """修改特征命令"""
    
    def __init__(self, feature: Feature, new_params: FeatureParameters):
        super().__init__("Modify Feature")
        self._feature = feature
        self._old_params = feature.parameters
        self._new_params = new_params
    
    def execute(self) -> bool:
        self._feature.parameters = self._new_params
        self._feature.update()
        self._is_executed = True
        return True
    
    def undo(self) -> bool:
        self._feature.parameters = self._old_params
        self._feature.update()
        self._is_executed = False
        return True
    
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
    
    def execute(self, command: Command) -> bool:
        """执行命令"""
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
    
    def can_undo(self) -> bool:
        """检查是否可以撤销"""
        return self._current_index >= 0
    
    def undo(self) -> bool:
        """撤销上一个命令"""
        if self.can_undo():
            command = self._history[self._current_index]
            if command.undo():
                self._current_index -= 1
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
            return command.redo()
        return False
    
    def clear(self):
        """清空历史"""
        self._history.clear()
        self._current_index = -1
    
    def get_history(self) -> List[str]:
        """获取命令历史列表"""
        return [cmd.name for cmd in self._history]
```

---

## 7. 特征管理器与模型构建器

```python
# ============================================
# feature_manager.py - 特征管理器
# ============================================

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
        
    def add_feature(self, feature: Feature) -> bool:
        """添加特征"""
        if feature.feature_id in self._features:
            logger.warning(f"Feature {feature.feature_id} already exists")
            return False
        
        self._features[feature.feature_id] = feature
        
        # 更新特征树
        if feature._parent:
            parent_id = feature._parent.feature_id
            if parent_id not in self._feature_tree:
                self._feature_tree[parent_id] = []
            self._feature_tree[parent_id].append(feature.feature_id)
        
        return True
    
    def remove_feature(self, feature_id: str) -> bool:
        """移除特征"""
        if feature_id not in self._features:
            return False
        
        feature = self._features[feature_id]
        
        # 移除子特征
        if feature_id in self._feature_tree:
            for child_id in self._feature_tree[feature_id]:
                self.remove_feature(child_id)
            del self._feature_tree[feature_id]
        
        # 从父特征中移除
        if feature._parent:
            parent_id = feature._parent.feature_id
            if parent_id in self._feature_tree:
                if feature_id in self._feature_tree[parent_id]:
                    self._feature_tree[parent_id].remove(feature_id)
        
        # 从内核中移除形状
        self._kernel.remove_shape(feature_id)
        
        # 移除特征
        del self._features[feature_id]
        
        return True
    
    def get_feature(self, feature_id: str) -> Optional[Feature]:
        """获取特征"""
        return self._features.get(feature_id)
    
    def get_all_features(self) -> List[Feature]:
        """获取所有特征"""
        return list(self._features.values())
    
    def get_features_by_type(self, feature_type: FeatureType) -> List[Feature]:
        """按类型获取特征"""
        return [f for f in self._features.values() 
                if f.feature_type == feature_type]
    
    def get_body_shape(self, body_id: str) -> Optional[TopoDS_Shape]:
        """获取实体形状"""
        # 获取实体的最后一个特征
        feature_ids = self._body_features.get(body_id, [])
        if feature_ids:
            last_feature_id = feature_ids[-1]
            return self._kernel.get_shape(last_feature_id)
        return None
    
    def rebuild_all(self) -> bool:
        """重建所有特征"""
        try:
            # 按依赖顺序重建
            rebuilt = set()
            
            def rebuild_feature(feature_id: str):
                if feature_id in rebuilt:
                    return
                
                feature = self._features.get(feature_id)
                if feature is None:
                    return
                
                # 先重建父特征
                if feature._parent:
                    rebuild_feature(feature._parent.feature_id)
                
                # 重建当前特征
                feature.update()
                rebuilt.add(feature_id)
                
                # 重建子特征
                for child_id in self._feature_tree.get(feature_id, []):
                    rebuild_feature(child_id)
            
            # 从根特征开始重建
            root_features = [f for f in self._features.values() 
                           if f._parent is None]
            for root in root_features:
                rebuild_feature(root.feature_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Rebuild all failed: {e}")
            return False
    
    def serialize(self) -> Dict[str, Any]:
        """序列化所有特征"""
        return {
            'features': [f.to_dict() for f in self._features.values()],
            'feature_tree': self._feature_tree,
            'body_features': self._body_features
        }
    
    def deserialize(self, data: Dict[str, Any]) -> bool:
        """反序列化特征"""
        try:
            self._features.clear()
            self._feature_tree = data.get('feature_tree', {})
            self._body_features = data.get('body_features', {})
            
            # 创建特征
            for feature_data in data['features']:
                feature = FeatureFactory.create_from_dict(feature_data, 
                                                           self._kernel)
                self._features[feature.feature_id] = feature
            
            # 重建父子关系
            for feature in self._features.values():
                parent_id = feature.to_dict().get('parent_id')
                if parent_id and parent_id in self._features:
                    feature._parent = self._features[parent_id]
            
            return True
            
        except Exception as e:
            logger.error(f"Deserialize failed: {e}")
            return False


# ============================================
# model_builder.py - 模型构建器
# ============================================

class ModelBuilder:
    """
    模型构建器
    负责从2D特征数据构建3D模型
    """
    
    def __init__(self, kernel: GeometryKernel, 
                 feature_manager: FeatureManager):
        self._kernel = kernel
        self._feature_manager = feature_manager
        
    def build_from_2d_data(self, data: Dict[str, Any]) -> Optional[str]:
        """
        从2D数据构建3D模型
        
        Args:
            data: 包含2D特征数据的字典
                {
                    'base_profile': Profile2D,
                    'features': [
                        {'type': 'hole', 'center': Point3D, ...},
                        {'type': 'slot', ...},
                        ...
                    ],
                    'dimensions': {...},
                    'symmetry': {...}
                }
        
        Returns:
            生成的实体形状ID
        """
        try:
            # 1. 创建基体特征
            base_feature = self._create_base_feature(data)
            if base_feature is None:
                return None
            
            self._feature_manager.add_feature(base_feature)
            base_feature.build()
            
            body_id = base_feature.feature_id
            current_shape_id = body_id
            
            # 2. 添加附加特征
            for feature_data in data.get('features', []):
                feature = self._create_feature(feature_data, body_id)
                if feature:
                    self._feature_manager.add_feature(feature)
                    feature.build()
                    
                    # 执行布尔运算
                    if feature.feature_type in [
                        FeatureType.HOLE, FeatureType.SLOT, FeatureType.POCKET]:
                        # 切除特征
                        bool_params = BooleanParameters(
                            feature_id=str(uuid4()),
                            feature_type=FeatureType.BOOLEAN_SUBTRACT,
                            target_body_id=current_shape_id,
                            tool_body_id=feature.feature_id,
                            operation='subtract'
                        )
                        bool_feature = BooleanFeature(bool_params, self._kernel)
                        self._feature_manager.add_feature(bool_feature)
                        bool_feature.build()
                        current_shape_id = bool_feature.feature_id
                    
                    elif feature.feature_type in [FeatureType.BOSS]:
                        # 添加特征
                        bool_params = BooleanParameters(
                            feature_id=str(uuid4()),
                            feature_type=FeatureType.BOOLEAN_UNION,
                            target_body_id=current_shape_id,
                            tool_body_id=feature.feature_id,
                            operation='union'
                        )
                        bool_feature = BooleanFeature(bool_params, self._kernel)
                        self._feature_manager.add_feature(bool_feature)
                        bool_feature.build()
                        current_shape_id = bool_feature.feature_id
            
            # 3. 应用铸造专用特征
            self._apply_casting_features(data, current_shape_id)
            
            return current_shape_id
            
        except Exception as e:
            logger.error(f"Build from 2D data failed: {e}")
            return None
    
    def _create_base_feature(self, data: Dict[str, Any]) -> Optional[Feature]:
        """创建基体特征"""
        profile = data.get('base_profile')
        if profile is None:
            return None
        
        # 根据轮廓类型选择建模方式
        base_type = data.get('base_type', 'extrude')
        
        if base_type == 'extrude':
            params = ExtrudeParameters(
                feature_id=str(uuid4()),
                feature_type=FeatureType.EXTRUDE,
                profile=profile,
                depth=data.get('depth', 10.0),
                taper_angle=data.get('draft_angle', 0.0)
            )
            return ExtrudeFeature(params, self._kernel)
        
        elif base_type == 'revolve':
            params = RevolveParameters(
                feature_id=str(uuid4()),
                feature_type=FeatureType.REVOLVE,
                profile=profile,
                axis_origin=data.get('axis_origin', Point3D()),
                axis_direction=data.get('axis_direction', Vector3D(0, 0, 1)),
                angle=data.get('angle', 360.0)
            )
            return RevolveFeature(params, self._kernel)
        
        return None
    
    def _create_feature(self, feature_data: Dict[str, Any], 
                        body_id: str) -> Optional[Feature]:
        """创建附加特征"""
        feature_type = feature_data.get('type')
        
        if feature_type == 'hole':
            params = HoleParameters(
                feature_id=str(uuid4()),
                feature_type=FeatureType.HOLE,
                center=feature_data.get('center', Point3D()),
                direction=feature_data.get('direction', Vector3D(0, 0, 1)),
                diameter=feature_data.get('diameter', 10.0),
                depth=feature_data.get('depth', 10.0),
                hole_type=feature_data.get('hole_type', 'simple')
            )
            return HoleFeature(params, self._kernel)
        
        # 可以添加更多特征类型...
        
        return None
    
    def _apply_casting_features(self, data: Dict[str, Any], body_id: str):
        """应用铸造专用特征"""
        # 应用拔模斜度
        draft_data = data.get('draft')
        if draft_data:
            params = DraftParameters(
                feature_id=str(uuid4()),
                feature_type=FeatureType.DRAFT,
                face_ids=draft_data.get('face_ids', []),
                draft_angle=draft_data.get('angle', 2.0),
                is_inward=draft_data.get('is_inward', True)
            )
            draft_feature = DraftFeature(params, self._kernel)
            self._feature_manager.add_feature(draft_feature)
            draft_feature.build()
```

---

## 8. 主引擎类

```python
# ============================================
# casting_3d_engine.py - 主引擎类
# ============================================

class Casting3DEngine:
    """
    铸造3D建模引擎主类
    提供统一的建模接口
    """
    
    def __init__(self):
        # 初始化内核
        self._kernel = GeometryKernel()
        
        # 初始化管理器
        self._feature_manager = FeatureManager(self._kernel)
        self._command_manager = CommandManager()
        self._model_builder = ModelBuilder(self._kernel, self._feature_manager)
        
        # 参数系统
        self._parameters: Dict[str, Any] = {}
        
        # 事件回调
        self._event_callbacks: Dict[str, List[Callable]] = {}
        
        logger.info("Casting3DEngine initialized")
    
    # ==================== 特征操作 ====================
    
    def create_extrude(self, profile: Profile2D, depth: float,
                       direction: Vector3D = None,
                       taper_angle: float = 0.0) -> Optional[str]:
        """创建拉伸特征"""
        if direction is None:
            direction = Vector3D(0, 0, 1)
        
        params = ExtrudeParameters(
            feature_id=str(uuid4()),
            feature_type=FeatureType.EXTRUDE,
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
                       axis_direction: Vector3D = None) -> Optional[str]:
        """创建旋转特征"""
        if axis_origin is None:
            axis_origin = Point3D()
        if axis_direction is None:
            axis_direction = Vector3D(0, 0, 1)
        
        params = RevolveParameters(
            feature_id=str(uuid4()),
            feature_type=FeatureType.REVOLVE,
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
                    direction: Vector3D = None) -> Optional[str]:
        """创建孔特征"""
        if direction is None:
            direction = Vector3D(0, 0, 1)
        
        params = HoleParameters(
            feature_id=str(uuid4()),
            feature_type=FeatureType.HOLE,
            center=center,
            direction=direction,
            diameter=diameter,
            depth=depth
        )
        
        command = CreateFeatureCommand(
            self._feature_manager, params, self._kernel)
        
        if self._command_manager.execute(command):
            self._emit_event('feature_created', params.feature_id)
            return params.feature_id
        return None
    
    def create_draft(self, face_ids: List[str], angle: float,
                     is_inward: bool = True) -> Optional[str]:
        """创建拔模特征 (铸造专用)"""
        params = DraftParameters(
            feature_id=str(uuid4()),
            feature_type=FeatureType.DRAFT,
            face_ids=face_ids,
            draft_angle=angle,
            is_inward=is_inward
        )
        
        command = CreateFeatureCommand(
            self._feature_manager, params, self._kernel)
        
        if self._command_manager.execute(command):
            self._emit_event('feature_created', params.feature_id)
            return params.feature_id
        return None
    
    def delete_feature(self, feature_id: str) -> bool:
        """删除特征"""
        command = DeleteFeatureCommand(self._feature_manager, feature_id)
        if self._command_manager.execute(command):
            self._emit_event('feature_deleted', feature_id)
            return True
        return False
    
    def modify_feature(self, feature_id: str, 
                       new_params: FeatureParameters) -> bool:
        """修改特征参数"""
        feature = self._feature_manager.get_feature(feature_id)
        if feature is None:
            return False
        
        command = ModifyFeatureCommand(feature, new_params)
        if self._command_manager.execute(command):
            self._emit_event('feature_modified', feature_id)
            return True
        return False
    
    # ==================== 模型构建 ====================
    
    def build_from_2d(self, data: Dict[str, Any]) -> Optional[str]:
        """从2D数据构建3D模型"""
        shape_id = self._model_builder.build_from_2d_data(data)
        if shape_id:
            self._emit_event('model_built', shape_id)
        return shape_id
    
    def rebuild_model(self) -> bool:
        """重新构建模型"""
        return self._feature_manager.rebuild_all()
    
    # ==================== 导出功能 ====================
    
    def export_stl(self, shape_id: str, filepath: str,
                   linear_deflection: float = 0.5) -> bool:
        """导出为STL格式"""
        return self._kernel.export_stl(shape_id, filepath, linear_deflection)
    
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
    
    # ==================== 参数系统 ====================
    
    def set_parameter(self, name: str, value: Any):
        """设置参数"""
        self._parameters[name] = value
        self._emit_event('parameter_changed', {'name': name, 'value': value})
    
    def get_parameter(self, name: str) -> Any:
        """获取参数"""
        return self._parameters.get(name)
    
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
        """保存模型"""
        try:
            import json
            data = {
                'version': '1.0',
                'features': self._feature_manager.serialize(),
                'parameters': self._parameters
            }
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Save failed: {e}")
            return False
    
    def load(self, filepath: str) -> bool:
        """加载模型"""
        try:
            import json
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # 加载特征
            self._feature_manager.deserialize(data['features'])
            
            # 加载参数
            self._parameters = data.get('parameters', {})
            
            # 重建模型
            self.rebuild_model()
            
            return True
        except Exception as e:
            logger.error(f"Load failed: {e}")
            return False
    
    # ==================== 属性访问 ====================
    
    @property
    def kernel(self) -> GeometryKernel:
        return self._kernel
    
    @property
    def feature_manager(self) -> FeatureManager:
        return self._feature_manager
    
    @property
    def volume(self) -> float:
        """获取模型体积"""
        # 获取最后一个特征的体积
        features = self._feature_manager.get_all_features()
        if features:
            last_feature = features[-1]
            return self._kernel.get_volume(last_feature.feature_id)
        return 0.0
```

---

## 9. 上下游模块接口定义

### 9.1 输入接口 (从图像分析模块)

```python
# ============================================
# input_interface.py - 输入接口定义
# ============================================

from typing import Protocol

class ImageAnalysisOutput(Protocol):
    """图像分析模块输出接口"""
    
    def get_contours(self) -> List[Profile2D]:
        """获取检测到的轮廓列表"""
        ...
    
    def get_features(self) -> List[Dict[str, Any]]:
        """获取特征分类信息"""
        ...
    
    def get_dimensions(self) -> Dict[str, float]:
        """获取尺寸信息"""
        ...
    
    def get_symmetry(self) -> Dict[str, Any]:
        """获取对称性信息"""
        ...


class ModelBuilderInput:
    """
    模型构建器输入数据类
    将图像分析输出转换为建模引擎输入
    """
    
    def __init__(self, image_analysis: ImageAnalysisOutput):
        self._image_analysis = image_analysis
        self._data = self._convert()
    
    def _convert(self) -> Dict[str, Any]:
        """转换数据格式"""
        contours = self._image_analysis.get_contours()
        features = self._image_analysis.get_features()
        dimensions = self._image_analysis.get_dimensions()
        symmetry = self._image_analysis.get_symmetry()
        
        # 确定基体轮廓
        base_profile = self._select_base_profile(contours)
        
        # 转换特征
        converted_features = self._convert_features(features)
        
        return {
            'base_profile': base_profile,
            'features': converted_features,
            'dimensions': dimensions,
            'symmetry': symmetry,
            'base_type': self._determine_base_type(contours),
            'depth': dimensions.get('depth', 10.0),
            'draft_angle': dimensions.get('draft_angle', 0.0)
        }
    
    def _select_base_profile(self, contours: List[Profile2D]) -> Profile2D:
        """选择基体轮廓（最大的封闭轮廓）"""
        # 计算每个轮廓的面积
        def calculate_area(profile: Profile2D) -> float:
            if len(profile.vertices) < 3:
                return 0.0
            # 使用Shoelace公式计算面积
            area = 0.0
            n = len(profile.vertices)
            for i in range(n):
                j = (i + 1) % n
                area += profile.vertices[i].x * profile.vertices[j].y
                area -= profile.vertices[j].x * profile.vertices[i].y
            return abs(area) / 2.0
        
        # 选择最大的封闭轮廓
        closed_contours = [c for c in contours if c.is_closed]
        if closed_contours:
            return max(closed_contours, key=calculate_area)
        
        return contours[0] if contours else Profile2D()
    
    def _convert_features(self, features: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """转换特征数据"""
        converted = []
        for feature in features:
            feature_type = feature.get('type')
            if feature_type == 'hole':
                converted.append({
                    'type': 'hole',
                    'center': Point3D(feature['center_x'], 
                                     feature['center_y'], 0),
                    'diameter': feature['diameter'],
                    'depth': feature.get('depth', 0)
                })
            elif feature_type == 'slot':
                converted.append({
                    'type': 'slot',
                    'center': Point3D(feature['center_x'],
                                     feature['center_y'], 0),
                    'width': feature['width'],
                    'length': feature['length'],
                    'angle': feature.get('angle', 0)
                })
            # 添加更多特征类型...
        return converted
    
    def _determine_base_type(self, contours: List[Profile2D]) -> str:
        """确定基体类型"""
        # 根据轮廓形状决定建模方式
        # 例如：对称轮廓使用旋转，非对称使用拉伸
        return 'extrude'
    
    def get_data(self) -> Dict[str, Any]:
        """获取转换后的数据"""
        return self._data
```

### 9.2 输出接口 (到导出模块)

```python
# ============================================
# output_interface.py - 输出接口定义
# ============================================

class ExportFormat(Enum):
    """导出格式枚举"""
    STL = "stl"
    STEP = "step"
    IGES = "iges"
    BREP = "brep"
    OBJ = "obj"
    PLY = "ply"


class ExportOptions:
    """导出选项"""
    
    def __init__(self):
        self.linear_deflection: float = 0.5
        self.angular_deflection: float = 0.5
        self.export_colors: bool = False
        self.export_normals: bool = True
        self.compress: bool = False


class ExportManager:
    """
    导出管理器
    管理模型导出到各种格式
    """
    
    def __init__(self, kernel: GeometryKernel):
        self._kernel = kernel
        self._exporters: Dict[ExportFormat, Callable] = {
            ExportFormat.STL: self._export_stl,
            ExportFormat.STEP: self._export_step,
            ExportFormat.IGES: self._export_iges,
            ExportFormat.BREP: self._export_brep
        }
    
    def export(self, shape_id: str, filepath: str, 
               format: ExportFormat,
               options: ExportOptions = None) -> bool:
        """
        导出模型
        
        Args:
            shape_id: 要导出的形状ID
            filepath: 输出文件路径
            format: 导出格式
            options: 导出选项
        
        Returns:
            导出是否成功
        """
        if options is None:
            options = ExportOptions()
        
        exporter = self._exporters.get(format)
        if exporter is None:
            logger.error(f"Unsupported export format: {format}")
            return False
        
        return exporter(shape_id, filepath, options)
    
    def _export_stl(self, shape_id: str, filepath: str,
                    options: ExportOptions) -> bool:
        """导出为STL"""
        return self._kernel.export_stl(
            shape_id, filepath,
            options.linear_deflection,
            options.angular_deflection)
    
    def _export_step(self, shape_id: str, filepath: str,
                     options: ExportOptions) -> bool:
        """导出为STEP"""
        return self._kernel.export_step(shape_id, filepath)
    
    def _export_iges(self, shape_id: str, filepath: str,
                     options: ExportOptions) -> bool:
        """导出为IGES"""
        return self._kernel.export_iges(shape_id, filepath)
    
    def _export_brep(self, shape_id: str, filepath: str,
                     options: ExportOptions) -> bool:
        """导出为BREP (OpenCASCADE原生格式)"""
        from OCC.Core.BRepTools import breptools_Write
        shape = self._kernel.get_shape(shape_id)
        if shape is None:
            return False
        return breptools_Write(shape, filepath)
    
    def register_exporter(self, format: ExportFormat, 
                          exporter: Callable):
        """注册自定义导出器"""
        self._exporters[format] = exporter
    
    def get_supported_formats(self) -> List[ExportFormat]:
        """获取支持的导出格式"""
        return list(self._exporters.keys())
```

---

## 10. 插件化架构

```python
# ============================================
# plugin_system.py - 插件系统
# ============================================

class FeaturePlugin(ABC):
    """
    特征插件基类
    用于扩展新的特征类型
    """
    
    @property
    @abstractmethod
    def feature_type(self) -> FeatureType:
        """插件支持的特征类型"""
        pass
    
    @property
    @abstractmethod
    def feature_class(self) -> type:
        """特征类"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """插件名称"""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """插件版本"""
        pass
    
    @abstractmethod
    def initialize(self, engine: Casting3DEngine) -> bool:
        """初始化插件"""
        pass
    
    @abstractmethod
    def shutdown(self) -> bool:
        """关闭插件"""
        pass


class PluginManager:
    """
    插件管理器
    管理特征插件的加载和卸载
    """
    
    def __init__(self, engine: Casting3DEngine):
        self._engine = engine
        self._plugins: Dict[str, FeaturePlugin] = {}
        self._plugin_paths: List[str] = []
    
    def add_plugin_path(self, path: str):
        """添加插件搜索路径"""
        if path not in self._plugin_paths:
            self._plugin_paths.append(path)
    
    def load_plugin(self, plugin_name: str) -> bool:
        """加载插件"""
        try:
            # 动态导入插件模块
            import importlib.util
            
            for path in self._plugin_paths:
                plugin_file = os.path.join(path, f"{plugin_name}.py")
                if os.path.exists(plugin_file):
                    spec = importlib.util.spec_from_file_location(
                        plugin_name, plugin_file)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # 获取插件类
                    plugin_class = getattr(module, 'Plugin', None)
                    if plugin_class is None:
                        logger.error(f"Plugin class not found in {plugin_name}")
                        return False
                    
                    # 实例化插件
                    plugin = plugin_class()
                    
                    # 初始化插件
                    if plugin.initialize(self._engine):
                        # 注册特征类
                        FeatureFactory.register(
                            plugin.feature_type, plugin.feature_class)
                        
                        self._plugins[plugin_name] = plugin
                        logger.info(f"Plugin loaded: {plugin.name} v{plugin.version}")
                        return True
                    else:
                        logger.error(f"Plugin initialization failed: {plugin_name}")
                        return False
            
            logger.error(f"Plugin not found: {plugin_name}")
            return False
            
        except Exception as e:
            logger.error(f"Load plugin failed: {e}")
            return False
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """卸载插件"""
        plugin = self._plugins.get(plugin_name)
        if plugin is None:
            return False
        
        if plugin.shutdown():
            del self._plugins[plugin_name]
            logger.info(f"Plugin unloaded: {plugin_name}")
            return True
        return False
    
    def get_loaded_plugins(self) -> List[str]:
        """获取已加载的插件列表"""
        return list(self._plugins.keys())
    
    def get_plugin_info(self, plugin_name: str) -> Optional[Dict[str, str]]:
        """获取插件信息"""
        plugin = self._plugins.get(plugin_name)
        if plugin:
            return {
                'name': plugin.name,
                'version': plugin.version,
                'feature_type': plugin.feature_type.name
            }
        return None
```

---

## 11. 使用示例

```python
# ============================================
# example_usage.py - 使用示例
# ============================================

def example_basic_usage():
    """基本使用示例"""
    
    # 创建引擎实例
    engine = Casting3DEngine()
    
    # 创建基体轮廓
    profile = Profile2D(
        vertices=[
            Point3D(0, 0, 0),
            Point3D(100, 0, 0),
            Point3D(100, 50, 0),
            Point3D(0, 50, 0)
        ],
        is_closed=True
    )
    
    # 创建拉伸特征
    base_id = engine.create_extrude(profile, depth=20.0)
    print(f"Base feature created: {base_id}")
    
    # 创建孔特征
    hole_id = engine.create_hole(
        center=Point3D(50, 25, 0),
        diameter=10.0,
        depth=20.0
    )
    print(f"Hole feature created: {hole_id}")
    
    # 导出模型
    engine.export_stl(base_id, "output.stl")
    engine.export_step(base_id, "output.step")
    
    # 撤销操作
    engine.undo()
    
    # 保存模型
    engine.save("model.json")


def example_from_2d_data():
    """从2D数据构建模型示例"""
    
    engine = Casting3DEngine()
    
    # 模拟从图像分析模块获取的数据
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
            {
                'type': 'hole',
                'center_x': 30,
                'center_y': 40,
                'diameter': 15,
                'depth': 0  # 通孔
            },
            {
                'type': 'hole',
                'center_x': 70,
                'center_y': 40,
                'diameter': 15,
                'depth': 0
            }
        ],
        'dimensions': {
            'depth': 25.0,
            'draft_angle': 2.0  # 铸造拔模角度
        },
        'symmetry': {
            'has_symmetry': True,
            'symmetry_axis': 'y'
        }
    }
    
    # 构建模型
    shape_id = engine.build_from_2d(data)
    print(f"Model built: {shape_id}")
    
    # 导出为铸造仿真格式
    engine.export_stl(shape_id, "casting_part.stl", linear_deflection=0.1)
    engine.export_step(shape_id, "casting_part.step")
    
    # 获取体积信息
    volume = engine.volume
    print(f"Model volume: {volume} mm³")


def example_plugin_usage():
    """插件使用示例"""
    
    engine = Casting3DEngine()
    
    # 创建插件管理器
    plugin_manager = PluginManager(engine)
    plugin_manager.add_plugin_path("./plugins")
    
    # 加载自定义特征插件
    plugin_manager.load_plugin("rib_feature")
    plugin_manager.load_plugin("cooling_channel")
    
    # 使用插件提供的特征
    # ...
    
    # 查看已加载插件
    plugins = plugin_manager.get_loaded_plugins()
    print(f"Loaded plugins: {plugins}")
```

---

## 12. 性能优化建议

### 12.1 几何计算优化
1. **空间分割**: 使用BVH或八叉树加速几何查询
2. **并行计算**: 利用多线程并行处理独立特征
3. **增量更新**: 仅更新修改的特征及其依赖
4. **缓存机制**: 缓存中间计算结果

### 12.2 内存管理
1. **形状共享**: 共享不变的几何数据
2. **延迟加载**: 按需加载复杂几何
3. **垃圾回收**: 及时释放不再使用的形状

### 12.3 精度控制
1. **自适应精度**: 根据模型复杂度调整精度
2. **容差管理**: 合理设置拓扑容差

---

## 13. 总结

本设计方案提供了一个完整的铸造行业3D建模引擎架构，包括：

1. **几何内核封装**: 基于OpenCASCADE的高级几何操作接口
2. **特征建模系统**: 支持基体特征、附加特征和铸造专用特征
3. **命令模式**: 完整的撤销/重做支持
4. **插件化架构**: 易于扩展新特征类型
5. **参数化建模**: 支持尺寸驱动的模型更新
6. **多格式导出**: 支持STL、STEP、IGES等铸造行业标准格式

该引擎能够高效地将2D特征数据转换为精确的3D实体模型，满足铸造行业的建模需求。
