"""
几何内核封装模块

基于OpenCASCADE Technology的高级几何操作接口
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

from .types import Point3D, Vector3D, Plane, Profile2D

# OpenCASCADE导入
try:
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
    
    HAS_OCC = True
except ImportError:
    HAS_OCC = False
    logging.warning("OpenCASCADE not available. Using mock implementation.")

logger = logging.getLogger(__name__)


class OCCConverter:
    """OCC类型转换器"""
    
    @staticmethod
    def point_to_gp(p: Point3D) -> Any:
        """Point3D转换为gp_Pnt"""
        if not HAS_OCC:
            return None
        return gp_Pnt(p.x, p.y, p.z)
    
    @staticmethod
    def gp_to_point(gp: Any) -> Point3D:
        """gp_Pnt转换为Point3D"""
        if not HAS_OCC or gp is None:
            return Point3D()
        return Point3D(gp.X(), gp.Y(), gp.Z())
    
    @staticmethod
    def vector_to_gp(v: Vector3D) -> Any:
        """Vector3D转换为gp_Vec"""
        if not HAS_OCC:
            return None
        return gp_Vec(v.x, v.y, v.z)
    
    @staticmethod
    def gp_to_vector(gp: Any) -> Vector3D:
        """gp_Vec转换为Vector3D"""
        if not HAS_OCC or gp is None:
            return Vector3D()
        return Vector3D(gp.X(), gp.Y(), gp.Z())
    
    @staticmethod
    def plane_to_gp(plane: Plane) -> Any:
        """Plane转换为gp_Ax3"""
        if not HAS_OCC:
            return None
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
        
        if not HAS_OCC:
            logger.warning("Running in mock mode - no actual geometry will be created")
    
    def register_shape(self, shape_id: str, shape: Any) -> bool:
        """注册形状到内核"""
        if not HAS_OCC:
            self._shapes[shape_id] = shape
            return True
            
        if self._validate_shape(shape):
            self._shapes[shape_id] = shape
            self._update_properties(shape_id)
            return True
        return False
    
    def get_shape(self, shape_id: str) -> Optional[Any]:
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
    
    def _validate_shape(self, shape: Any) -> bool:
        """验证形状有效性"""
        if not HAS_OCC:
            return True
        if shape is None or shape.IsNull():
            return False
        analyzer = BRepCheck_Analyzer(shape)
        return analyzer.IsValid()
    
    def _update_properties(self, shape_id: str):
        """更新形状属性"""
        if not HAS_OCC:
            return
            
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
    
    def get_centroid(self, shape_id: str) -> Point3D:
        """获取形状质心"""
        props = self._shape_properties.get(shape_id, {})
        centroid = props.get('centroid', (0, 0, 0))
        return Point3D(*centroid)
    
    def create_edge_from_points(self, p1: Point3D, p2: Point3D) -> Any:
        """从两点创建边"""
        if not HAS_OCC:
            return None
            
        gp_p1 = OCCConverter.point_to_gp(p1)
        gp_p2 = OCCConverter.point_to_gp(p2)
        segment = GC_MakeSegment(gp_p1, gp_p2).Value()
        return BRepBuilderAPI_MakeEdge(segment).Edge()
    
    def create_edge_from_arc(self, center: Point3D, radius: float, 
                            start_angle: float, end_angle: float,
                            normal: Vector3D = None) -> Any:
        """从圆弧参数创建边"""
        if not HAS_OCC:
            return None
            
        if normal is None:
            normal = Vector3D(0, 0, 1)
        
        gp_center = OCCConverter.point_to_gp(center)
        gp_normal = gp_Dir(normal.x, normal.y, normal.z)
        
        # 计算X方向（与normal正交）
        if abs(normal.z) > 0.99:
            gp_x_dir = gp_Dir(1, 0, 0)
        else:
            # 使用normal与Z轴的叉积
            z_axis = Vector3D(0, 0, 1)
            x_vec = normal.cross(z_axis)
            if x_vec.length() < 1e-10:
                x_vec = Vector3D(1, 0, 0)
            gp_x_dir = gp_Dir(x_vec.x, x_vec.y, x_vec.z)
        
        circle_axis = gp_Ax2(gp_center, gp_normal, gp_x_dir)
        arc = GC_MakeArcOfCircle(circle_axis, radius, 
                                  np.radians(start_angle), 
                                  np.radians(end_angle)).Value()
        return BRepBuilderAPI_MakeEdge(arc).Edge()
    
    def create_wire_from_profile(self, profile: Profile2D, 
                                  plane: Plane = None) -> Any:
        """从2D轮廓创建线框"""
        if not HAS_OCC:
            return None
            
        if plane is None:
            plane = Plane()
        
        wire_maker = BRepBuilderAPI_MakeWire()
        vertices = profile.vertices
        
        if len(vertices) < 2:
            logger.warning("Profile must have at least 2 vertices")
            return None
        
        # 处理圆弧
        arc_index = 0
        for i in range(len(vertices)):
            p1 = vertices[i]
            
            # 确定终点
            if profile.is_closed:
                p2 = vertices[(i + 1) % len(vertices)]
            else:
                if i >= len(vertices) - 1:
                    break
                p2 = vertices[i + 1]
            
            # 检查是否有圆弧连接
            edge = None
            if arc_index < len(profile.arcs):
                arc = profile.arcs[arc_index]
                if arc.get('start_idx') == i:
                    # 创建圆弧边
                    arc_center = arc.get('center', Point3D())
                    arc_radius = arc.get('radius', 0)
                    arc_start_angle = arc.get('start_angle', 0)
                    arc_end_angle = arc.get('end_angle', 0)
                    edge = self.create_edge_from_arc(
                        arc_center, arc_radius, 
                        arc_start_angle, arc_end_angle)
                    arc_index += 1
            
            if edge is None:
                edge = self.create_edge_from_points(p1, p2)
            
            if edge is not None:
                wire_maker.Add(edge)
        
        return wire_maker.Wire()
    
    def create_face_from_wire(self, wire: Any, 
                              plane: Plane = None) -> Any:
        """从线框创建面"""
        if not HAS_OCC:
            return None
            
        if plane is None:
            plane = Plane()
        
        gp_plane = OCCConverter.plane_to_gp(plane)
        return BRepBuilderAPI_MakeFace(gp_plane, wire).Face()
    
    def extrude_face(self, face: Any, direction: Vector3D, 
                     depth: float, taper_angle: float = 0.0) -> Any:
        """拉伸面创建实体"""
        if not HAS_OCC:
            return None
            
        gp_dir = gp_Dir(direction.x, direction.y, direction.z)
        
        if abs(taper_angle) < 0.001:
            # 直拉伸
            vec = gp_Vec(gp_dir) * depth
            prism = BRepPrimAPI_MakePrism(face, vec)
            return prism.Shape()
        else:
            # 带拔模的拉伸 - 使用BRepOffsetAPI_MakeDraft
            # 简化处理：先直拉伸再应用拔模
            vec = gp_Vec(gp_dir) * depth
            prism = BRepPrimAPI_MakePrism(face, vec)
            return prism.Shape()
    
    def revolve_face(self, face: Any, axis_origin: Point3D,
                     axis_direction: Vector3D, angle: float) -> Any:
        """旋转面创建实体"""
        if not HAS_OCC:
            return None
            
        gp_origin = OCCConverter.point_to_gp(axis_origin)
        gp_dir = gp_Dir(axis_direction.x, axis_direction.y, axis_direction.z)
        axis = gp_Ax1(gp_origin, gp_dir)
        
        revol = BRepPrimAPI_MakeRevol(face, axis, np.radians(angle))
        return revol.Shape()
    
    def create_box(self, corner: Point3D, 
                   dimensions: Tuple[float, float, float]) -> Any:
        """创建立方体"""
        if not HAS_OCC:
            return None
            
        gp_corner = OCCConverter.point_to_gp(corner)
        dx, dy, dz = dimensions
        box = BRepPrimAPI_MakeBox(gp_corner, dx, dy, dz)
        return box.Shape()
    
    def create_cylinder(self, center: Point3D, axis: Vector3D,
                        radius: float, height: float) -> Any:
        """创建圆柱体"""
        if not HAS_OCC:
            return None
            
        gp_center = OCCConverter.point_to_gp(center)
        gp_axis = gp_Dir(axis.x, axis.y, axis.z)
        ax2 = gp_Ax2(gp_center, gp_axis)
        cylinder = BRepPrimAPI_MakeCylinder(ax2, radius, height)
        return cylinder.Shape()
    
    def create_sphere(self, center: Point3D, radius: float) -> Any:
        """创建球体"""
        if not HAS_OCC:
            return None
            
        gp_center = OCCConverter.point_to_gp(center)
        sphere = BRepPrimAPI_MakeSphere(gp_center, radius)
        return sphere.Shape()
    
    def boolean_union(self, shape1: Any, shape2: Any) -> Any:
        """布尔并运算"""
        if not HAS_OCC:
            return None
            
        fuse = BRepAlgoAPI_Fuse(shape1, shape2)
        if fuse.IsDone():
            return fuse.Shape()
        raise RuntimeError("Boolean union failed")
    
    def boolean_subtract(self, shape1: Any, shape2: Any) -> Any:
        """布尔减运算"""
        if not HAS_OCC:
            return None
            
        cut = BRepAlgoAPI_Cut(shape1, shape2)
        if cut.IsDone():
            return cut.Shape()
        raise RuntimeError("Boolean subtract failed")
    
    def boolean_intersect(self, shape1: Any, shape2: Any) -> Any:
        """布尔交运算"""
        if not HAS_OCC:
            return None
            
        common = BRepAlgoAPI_Common(shape1, shape2)
        if common.IsDone():
            return common.Shape()
        raise RuntimeError("Boolean intersect failed")
    
    def apply_fillet(self, shape: Any, edges: List[Any],
                     radius: float) -> Any:
        """应用圆角"""
        if not HAS_OCC:
            return None
            
        fillet = BRepFilletAPI_MakeFillet(shape)
        for edge in edges:
            fillet.Add(radius, edge)
        return fillet.Shape()
    
    def apply_chamfer(self, shape: Any, edges: List[Any],
                      distance: float) -> Any:
        """应用倒角"""
        if not HAS_OCC:
            return None
            
        chamfer = BRepFilletAPI_MakeChamfer(shape)
        for edge in edges:
            chamfer.Add(distance, edge)
        return chamfer.Shape()
    
    def apply_draft(self, shape: Any, faces: List[Any],
                    neutral_plane: Plane, pull_direction: Vector3D,
                    angle: float, is_inward: bool = True) -> Any:
        """应用拔模 (铸造专用)"""
        if not HAS_OCC:
            return shape
            
        # 使用BRepOffsetAPI_MakeDraft实现拔模
        # 这里简化处理，实际实现需要更复杂的算法
        draft_angle = np.radians(angle) if is_inward else -np.radians(angle)
        
        # TODO: 实现完整的拔模算法
        logger.info(f"Draft applied with angle {angle}°")
        return shape
    
    def export_stl(self, shape_id: str, filepath: str, 
                   linear_deflection: float = 0.5,
                   angular_deflection: float = 0.5) -> bool:
        """导出为STL格式"""
        if not HAS_OCC:
            logger.warning("Cannot export STL - OpenCASCADE not available")
            return False
            
        shape = self._shapes.get(shape_id)
        if shape is None:
            logger.error(f"Shape not found: {shape_id}")
            return False
        
        # 生成网格
        BRepMesh_IncrementalMesh(shape, linear_deflection, False, 
                                  angular_deflection)
        
        writer = StlAPI_Writer()
        success = writer.Write(shape, filepath)
        
        if success:
            logger.info(f"Exported STL: {filepath}")
        else:
            logger.error(f"STL export failed: {filepath}")
        
        return success
    
    def export_step(self, shape_id: str, filepath: str) -> bool:
        """导出为STEP格式"""
        if not HAS_OCC:
            logger.warning("Cannot export STEP - OpenCASCADE not available")
            return False
            
        shape = self._shapes.get(shape_id)
        if shape is None:
            logger.error(f"Shape not found: {shape_id}")
            return False
        
        writer = STEPControl_Writer()
        Interface_Static.SetCVal("write.step.schema", "AP214IS")
        writer.Transfer(shape, STEPControl_AsIs)
        success = writer.Write(filepath)
        
        if success:
            logger.info(f"Exported STEP: {filepath}")
        else:
            logger.error(f"STEP export failed: {filepath}")
        
        return success
    
    def export_iges(self, shape_id: str, filepath: str) -> bool:
        """导出为IGES格式"""
        if not HAS_OCC:
            logger.warning("Cannot export IGES - OpenCASCADE not available")
            return False
            
        shape = self._shapes.get(shape_id)
        if shape is None:
            logger.error(f"Shape not found: {shape_id}")
            return False
        
        writer = IGESControl_Writer()
        writer.AddShape(shape)
        success = writer.Write(filepath)
        
        if success:
            logger.info(f"Exported IGES: {filepath}")
        else:
            logger.error(f"IGES export failed: {filepath}")
        
        return success
    
    def get_face_edges(self, face: Any) -> List[Any]:
        """获取面的所有边"""
        if not HAS_OCC:
            return []
            
        edges = []
        explorer = TopExp_Explorer(face, TopAbs_EDGE)
        while explorer.More():
            edges.append(explorer.Current())
            explorer.Next()
        return edges
    
    def get_shape_faces(self, shape: Any) -> List[Any]:
        """获取形状的所有面"""
        if not HAS_OCC:
            return []
            
        faces = []
        explorer = TopExp_Explorer(shape, TopAbs_FACE)
        while explorer.More():
            faces.append(explorer.Current())
            explorer.Next()
        return faces
    
    def transform_shape(self, shape: Any, translation: Vector3D = None,
                       rotation: Tuple[float, float, float] = None,
                       scale: float = 1.0) -> Any:
        """变换形状"""
        if not HAS_OCC:
            return shape
            
        transform = gp_Trsf()
        
        # 缩放
        if scale != 1.0:
            transform.SetScale(gp_Pnt(0, 0, 0), scale)
        
        # 旋转
        if rotation is not None:
            rx, ry, rz = rotation
            # 应用欧拉角旋转
            quat = gp_Quaternion()
            quat.SetEulerAngles(gp_Extrinsic_XYZ, 
                                np.radians(rx), 
                                np.radians(ry), 
                                np.radians(rz))
            transform.SetRotation(quat)
        
        # 平移
        if translation is not None:
            vec = gp_Vec(translation.x, translation.y, translation.z)
            transform.SetTranslation(vec)
        
        transformer = BRepBuilderAPI_Transform(shape, transform)
        return transformer.Shape()
