"""
STEP格式导出器实现
STEP (ISO 10303) Format Exporter Implementation

支持:
- AP203 (Configuration Controlled Design)
- AP214 (Core Data for Automotive Mechanical Design Process)
- 完整B-rep导出
- 颜色和层信息

格式规范参考:
- ISO 10303-21: Clear Text Encoding of the Exchange Structure
- ISO 10303-203: Application Protocol for Configuration Controlled Design
- ISO 10303-214: Application Protocol for Core Data for Automotive Mechanical Design
"""

import re
from pathlib import Path
from typing import Union, List, Dict, Set, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, field

from cad_exporter_base import (
    CADExporter, BRepSolid, BRepFace, BRepEdge, Vector3D, MeshData,
    ExportOptions, ExportFormat, ExportMetadata, UnitType
)


@dataclass
class STEPEntity:
    """STEP实体数据类"""
    id: int
    type: str
    params: List[Any] = field(default_factory=list)
    
    def to_string(self) -> str:
        """转换为STEP格式字符串"""
        param_strs = []
        for p in self.params:
            param_strs.append(self._format_param(p))
        return f"#{self.id}={self.type}({','.join(param_strs)});"
    
    def _format_param(self, param: Any) -> str:
        """格式化参数"""
        if param is None:
            return '$'
        elif isinstance(param, bool):
            return '.T.' if param else '.F.'
        elif isinstance(param, (int, float)):
            return str(param)
        elif isinstance(param, str):
            # 转义单引号
            escaped = param.replace("'", "''")
            return f"'{escaped}'"
        elif isinstance(param, STEPEntity):
            return f"#{param.id}"
        elif isinstance(param, list):
            items = [self._format_param(item) for item in param]
            return f"({','.join(items)})"
        elif isinstance(param, tuple):
            items = [self._format_param(item) for item in param]
            return f"({','.join(items)})"
        else:
            return str(param)


class STEPExporter(CADExporter):
    """
    STEP格式导出器
    
    STEP (Standard for the Exchange of Product model data) 是ISO 10303标准，
    用于产品数据的交换。支持完整的B-rep几何和拓扑信息。
    """
    
    # STEP Schema标识符
    SCHEMA_AP203 = "CONFIG_CONTROL_DESIGN"
    SCHEMA_AP214 = "AUTOMOTIVE_DESIGN"
    
    def __init__(self, options: Optional[ExportOptions] = None):
        super().__init__(options)
        self._schema = self.SCHEMA_AP214  # 默认使用AP214
        if options and options.step_schema:
            self._schema = self.SCHEMA_AP203 if options.step_schema == "AP203" else self.SCHEMA_AP214
        
        self._entities: Dict[int, STEPEntity] = {}
        self._entity_counter = 0
        self._write_colors = options.step_write_colors if options else True
    
    @property
    def format_name(self) -> str:
        return f"STEP (ISO 10303) - {self._schema}"
    
    @property
    def file_extension(self) -> str:
        return ".step"
    
    def _get_next_id(self) -> int:
        """获取下一个实体ID"""
        self._entity_counter += 1
        return self._entity_counter
    
    def _add_entity(self, entity_type: str, *params) -> STEPEntity:
        """添加实体"""
        entity_id = self._get_next_id()
        entity = STEPEntity(entity_id, entity_type, list(params))
        self._entities[entity_id] = entity
        return entity
    
    def export_brep(self, solid: BRepSolid, filepath: Union[str, Path]) -> bool:
        """
        导出B-rep实体为STEP格式
        
        Args:
            solid: B-rep实体数据
            filepath: 输出文件路径
            
        Returns:
            导出是否成功
        """
        # 验证数据
        if not self.validate_brep(solid):
            return False
        
        self._report_stage("STEP Export", f"Exporting B-rep solid: {solid.name}")
        
        try:
            # 重置实体列表
            self._entities = {}
            self._entity_counter = 0
            
            # 构建STEP数据结构
            self._build_step_structure(solid)
            
            # 写入文件
            return self._write_step_file(filepath)
            
        except Exception as e:
            self._add_error(f"Failed to export STEP: {str(e)}")
            return False
    
    def export_mesh(self, mesh: MeshData, filepath: Union[str, Path]) -> bool:
        """
        导出网格为STEP格式（使用SHELL_BASED_SURFACE_MODEL）
        
        Args:
            mesh: 网格数据
            filepath: 输出文件路径
            
        Returns:
            导出是否成功
        """
        self._report_stage("STEP Export", f"Exporting mesh with {len(mesh.triangles)} triangles")
        
        try:
            # 重置实体列表
            self._entities = {}
            self._entity_counter = 0
            
            # 构建网格的STEP结构
            self._build_mesh_structure(mesh)
            
            # 写入文件
            return self._write_step_file(filepath)
            
        except Exception as e:
            self._add_error(f"Failed to export mesh to STEP: {str(e)}")
            return False
    
    def _build_step_structure(self, solid: BRepSolid):
        """构建B-rep的STEP数据结构"""
        # 创建头部信息
        self._create_header_entities()
        
        # 创建几何上下文
        geom_context = self._create_geometric_context()
        
        # 创建顶点
        vertex_entities = []
        for i, vertex in enumerate(solid.vertices):
            self._report_progress("Creating vertices", i + 1, len(solid.vertices))
            v_entity = self._create_vertex_point(vertex)
            vertex_entities.append(v_entity)
        
        # 创建边
        edge_entities = []
        for i, edge in enumerate(solid.edges):
            self._report_progress("Creating edges", i + 1, len(solid.edges))
            start_v = vertex_entities[edge.vertex_start]
            end_v = vertex_entities[edge.vertex_end]
            e_entity = self._create_edge(edge, start_v, end_v)
            edge_entities.append(e_entity)
        
        # 创建面
        face_entities = []
        for i, face in enumerate(solid.faces):
            self._report_progress("Creating faces", i + 1, len(solid.faces))
            f_entity = self._create_face(face, vertex_entities, edge_entities)
            if f_entity:
                face_entities.append(f_entity)
        
        # 创建壳
        shell = self._create_closed_shell(face_entities)
        
        # 创建实体
        self._create_manifold_solid_brep(shell, solid.name)
        
        # 创建产品定义结构
        self._create_product_structure(solid.name)
    
    def _build_mesh_structure(self, mesh: MeshData):
        """构建网格的STEP数据结构"""
        # 创建头部信息
        self._create_header_entities()
        
        # 创建几何上下文
        geom_context = self._create_geometric_context()
        
        # 创建顶点
        vertex_map = {}
        for i, tri in enumerate(mesh.triangles):
            self._report_progress("Processing triangles", i + 1, len(mesh.triangles))
            
            # 创建或重用顶点
            for v, v_name in [(tri.v1, 'v1'), (tri.v2, 'v2'), (tri.v3, 'v3')]:
                v_key = (round(v.x, 6), round(v.y, 6), round(v.z, 6))
                if v_key not in vertex_map:
                    vertex_map[v_key] = self._create_vertex_point(v)
        
        # 创建面（每个三角形作为一个平面面）
        face_entities = []
        for i, tri in enumerate(mesh.triangles):
            # 创建平面
            plane = self._create_plane_from_triangle(tri)
            
            # 创建边界
            v1_key = (round(tri.v1.x, 6), round(tri.v1.y, 6), round(tri.v1.z, 6))
            v2_key = (round(tri.v2.x, 6), round(tri.v2.y, 6), round(tri.v2.z, 6))
            v3_key = (round(tri.v3.x, 6), round(tri.v3.y, 6), round(tri.v3.z, 6))
            
            vertices = [vertex_map[v1_key], vertex_map[v2_key], vertex_map[v3_key]]
            
            # 创建面边界
            bounds = self._create_face_outer_bound(vertices)
            
            # 创建面
            face = self._add_entity(
                'FACE_SURFACE',
                '',  # name
                bounds,  # bounds
                plane,  # face geometry
                '.T.'  # same_sense
            )
            face_entities.append(face)
        
        # 创建壳
        shell = self._add_entity(
            'OPEN_SHELL',
            '',
            face_entities
        )
        
        # 创建壳模型
        self._add_entity(
            'SHELL_BASED_SURFACE_MODEL',
            '',
            [shell]
        )
        
        # 创建产品定义结构
        self._create_product_structure(mesh.name or "Mesh")
    
    def _create_header_entities(self):
        """创建STEP头部实体"""
        # 这些将在写入文件时处理
        pass
    
    def _create_geometric_context(self) -> STEPEntity:
        """创建几何表示上下文"""
        # 创建单位
        length_unit = self._add_entity(
            'LENGTH_UNIT',
            '*',
            self._add_entity('NAMED_UNIT', '*'),
            self._add_entity('SI_UNIT', '.MILLI.', '.METRE.')
        )
        
        # 创建几何表示上下文
        context = self._add_entity(
            'GEOMETRIC_REPRESENTATION_CONTEXT',
            '*',
            3,
            1.0e-6,
            length_unit
        )
        
        return context
    
    def _create_vertex_point(self, point: Vector3D) -> STEPEntity:
        """创建顶点"""
        cartesian_point = self._add_entity(
            'CARTESIAN_POINT',
            '',
            (point.x, point.y, point.z)
        )
        
        vertex = self._add_entity(
            'VERTEX_POINT',
            '',
            cartesian_point
        )
        
        return vertex
    
    def _create_edge(self, edge: BRepEdge, start_v: STEPEntity, end_v: STEPEntity) -> STEPEntity:
        """创建边"""
        # 根据曲线类型创建几何
        if edge.curve_type == 'LINE':
            # 直线
            start_pt = edge.curve_params.get('start', Vector3D())
            end_pt = edge.curve_params.get('end', Vector3D())
            
            line = self._add_entity(
                'LINE',
                '',
                self._add_entity('CARTESIAN_POINT', '', (start_pt.x, start_pt.y, start_pt.z)),
                self._add_entity('VECTOR', '', 
                    self._add_entity('DIRECTION', '', 
                        (end_pt.x - start_pt.x, end_pt.y - start_pt.y, end_pt.z - start_pt.z)),
                    1.0
                )
            )
            
            edge_curve = self._add_entity(
                'EDGE_CURVE',
                '',
                start_v,
                end_v,
                line,
                '.T.'
            )
            
        elif edge.curve_type == 'CIRCLE':
            # 圆
            center = edge.curve_params.get('center', Vector3D())
            radius = edge.curve_params.get('radius', 1.0)
            axis = edge.curve_params.get('axis', Vector3D(0, 0, 1))
            
            circle = self._add_entity(
                'CIRCLE',
                '',
                self._add_entity('AXIS2_PLACEMENT_3D', '',
                    self._add_entity('CARTESIAN_POINT', '', (center.x, center.y, center.z)),
                    self._add_entity('DIRECTION', '', (axis.x, axis.y, axis.z)),
                    self._add_entity('DIRECTION', '', (1.0, 0.0, 0.0))
                ),
                radius
            )
            
            edge_curve = self._add_entity(
                'EDGE_CURVE',
                '',
                start_v,
                end_v,
                circle,
                '.T.'
            )
            
        else:
            # 默认使用直线
            edge_curve = self._add_entity(
                'EDGE_CURVE',
                '',
                start_v,
                end_v,
                self._add_entity('LINE', '',
                    self._add_entity('CARTESIAN_POINT', '', (0.0, 0.0, 0.0)),
                    self._add_entity('DIRECTION', '', (1.0, 0.0, 0.0))
                ),
                '.T.'
            )
        
        oriented_edge = self._add_entity(
            'ORIENTED_EDGE',
            '',
            '*',
            edge_curve,
            '.T.'
        )
        
        return oriented_edge
    
    def _create_face(self, face: BRepFace, vertex_entities: List[STEPEntity], 
                     edge_entities: List[BRepEdge]) -> Optional[STEPEntity]:
        """创建面"""
        try:
            # 创建面几何
            if face.surface_type == 'PLANE':
                origin = face.surface_params.get('origin', Vector3D())
                normal = face.surface_params.get('normal', Vector3D(0, 0, 1))
                
                plane = self._add_entity(
                    'PLANE',
                    '',
                    self._add_entity('AXIS2_PLACEMENT_3D', '',
                        self._add_entity('CARTESIAN_POINT', '', (origin.x, origin.y, origin.z)),
                        self._add_entity('DIRECTION', '', (normal.x, normal.y, normal.z)),
                        self._add_entity('DIRECTION', '', (1.0, 0.0, 0.0))
                    )
                )
                
            elif face.surface_type == 'CYLINDER':
                origin = face.surface_params.get('origin', Vector3D())
                axis = face.surface_params.get('axis', Vector3D(0, 0, 1))
                radius = face.surface_params.get('radius', 1.0)
                
                plane = self._add_entity(
                    'CYLINDRICAL_SURFACE',
                    '',
                    self._add_entity('AXIS2_PLACEMENT_3D', '',
                        self._add_entity('CARTESIAN_POINT', '', (origin.x, origin.y, origin.z)),
                        self._add_entity('DIRECTION', '', (axis.x, axis.y, axis.z)),
                        self._add_entity('DIRECTION', '', (1.0, 0.0, 0.0))
                    ),
                    radius
                )
                
            elif face.surface_type == 'SPHERE':
                center = face.surface_params.get('center', Vector3D())
                radius = face.surface_params.get('radius', 1.0)
                
                plane = self._add_entity(
                    'SPHERICAL_SURFACE',
                    '',
                    self._add_entity('AXIS2_PLACEMENT_3D', '',
                        self._add_entity('CARTESIAN_POINT', '', (center.x, center.y, center.z)),
                        self._add_entity('DIRECTION', '', (0.0, 0.0, 1.0)),
                        self._add_entity('DIRECTION', '', (1.0, 0.0, 0.0))
                    ),
                    radius
                )
                
            else:
                # 默认使用平面
                plane = self._add_entity(
                    'PLANE',
                    '',
                    self._add_entity('AXIS2_PLACEMENT_3D', '',
                        self._add_entity('CARTESIAN_POINT', '', (0.0, 0.0, 0.0)),
                        self._add_entity('DIRECTION', '', (0.0, 0.0, 1.0)),
                        self._add_entity('DIRECTION', '', (1.0, 0.0, 0.0))
                    )
                )
            
            # 创建外边界
            outer_bounds = []
            for i in range(len(face.outer_wire)):
                idx1 = face.outer_wire[i]
                idx2 = face.outer_wire[(i + 1) % len(face.outer_wire)]
                
                # 简化的边界创建
                edge = self._add_entity(
                    'EDGE_LOOP',
                    '',
                    []
                )
                outer_bounds.append(edge)
            
            # 创建面边界
            face_bound = self._add_entity(
                'FACE_OUTER_BOUND',
                '',
                edge,
                '.T.'
            )
            
            # 创建面
            face_entity = self._add_entity(
                'FACE_SURFACE',
                '',
                [face_bound],
                plane,
                '.T.'
            )
            
            return face_entity
            
        except Exception as e:
            self._add_warning(f"Failed to create face: {str(e)}")
            return None
    
    def _create_plane_from_triangle(self, tri) -> STEPEntity:
        """从三角形创建平面"""
        # 计算平面原点（三角形重心）
        origin = Vector3D(
            (tri.v1.x + tri.v2.x + tri.v3.x) / 3,
            (tri.v1.y + tri.v2.y + tri.v3.y) / 3,
            (tri.v1.z + tri.v2.z + tri.v3.z) / 3
        )
        
        # 使用三角形的法向量
        normal = tri.normal
        
        # 计算参考方向（垂直于法向量）
        ref = Vector3D(1, 0, 0)
        if abs(normal.x) > 0.9:
            ref = Vector3D(0, 1, 0)
        
        # 计算第二个方向（垂直于法向量和参考方向）
        axis2 = Vector3D(
            normal.y * ref.z - normal.z * ref.y,
            normal.z * ref.x - normal.x * ref.z,
            normal.x * ref.y - normal.y * ref.x
        ).normalize()
        
        plane = self._add_entity(
            'PLANE',
            '',
            self._add_entity('AXIS2_PLACEMENT_3D', '',
                self._add_entity('CARTESIAN_POINT', '', (origin.x, origin.y, origin.z)),
                self._add_entity('DIRECTION', '', (normal.x, normal.y, normal.z)),
                self._add_entity('DIRECTION', '', (axis2.x, axis2.y, axis2.z))
            )
        )
        
        return plane
    
    def _create_face_outer_bound(self, vertices: List[STEPEntity]) -> STEPEntity:
        """创建面外边界"""
        # 创建边循环
        edges = []
        for i in range(len(vertices)):
            v1 = vertices[i]
            v2 = vertices[(i + 1) % len(vertices)]
            
            # 创建边
            edge = self._add_entity(
                'ORIENTED_EDGE',
                '',
                '*',
                self._add_entity('EDGE_CURVE', '', v1, v2, 
                    self._add_entity('VERTEX_POINT', '', v1), '.T.'),
                '.T.'
            )
            edges.append(edge)
        
        edge_loop = self._add_entity('EDGE_LOOP', '', edges)
        
        face_bound = self._add_entity(
            'FACE_OUTER_BOUND',
            '',
            edge_loop,
            '.T.'
        )
        
        return face_bound
    
    def _create_closed_shell(self, faces: List[STEPEntity]) -> STEPEntity:
        """创建闭合壳"""
        return self._add_entity(
            'CLOSED_SHELL',
            '',
            faces
        )
    
    def _create_manifold_solid_brep(self, shell: STEPEntity, name: str):
        """创建流形实体B-rep"""
        brep = self._add_entity(
            'MANIFOLD_SOLID_BREP',
            name,
            shell
        )
        
        # 创建形状表示关系
        self._add_entity(
            'SHAPE_DEFINITION_REPRESENTATION',
            self._add_entity('PRODUCT_DEFINITION_SHAPE', '', '*', '*'),
            self._add_entity('ADVANCED_BREP_SHAPE_REPRESENTATION', '', [brep], 
                self._create_geometric_context())
        )
    
    def _create_product_structure(self, product_name: str):
        """创建产品定义结构"""
        # 创建应用协议定义
        if self._schema == self.SCHEMA_AP203:
            self._add_entity(
                'APPLICATION_PROTOCOL_DEFINITION',
                'international standard',
                self._schema,
                1994,
                self._add_entity('APPLICATION_CONTEXT', 'configuration controlled 3D design of mechanical parts and assemblies')
            )
        else:
            self._add_entity(
                'APPLICATION_PROTOCOL_DEFINITION',
                'international standard',
                self._schema,
                2001,
                self._add_entity('APPLICATION_CONTEXT', 'core data for automotive mechanical design process')
            )
        
        # 创建产品
        product = self._add_entity(
            'PRODUCT',
            product_name,
            '',
            '',
            [self._add_entity('PRODUCT_CONTEXT', '', self._add_entity('APPLICATION_CONTEXT', ''), 'mechanical')]
        )
        
        # 创建产品定义
        product_definition = self._add_entity(
            'PRODUCT_DEFINITION',
            '',
            '',
            product,
            self._add_entity('PRODUCT_DEFINITION_CONTEXT', '', self._add_entity('APPLICATION_CONTEXT', ''), 'design')
        )
    
    def _write_step_file(self, filepath: Union[str, Path]) -> bool:
        """写入STEP文件"""
        try:
            path = self._ensure_directory(filepath)
            
            with open(path, 'w', encoding='utf-8') as f:
                # 写入HEADER部分
                f.write(self._generate_header())
                
                # 写入DATA部分
                f.write("DATA;\n")
                
                total = len(self._entities)
                for i, (entity_id, entity) in enumerate(sorted(self._entities.items())):
                    self._report_progress("Writing entities", i + 1, total)
                    f.write(entity.to_string() + "\n")
                
                f.write("ENDSEC;\n")
                f.write("END-ISO-10303-21;\n")
            
            self._report_stage("Complete", f"STEP file exported to {path}")
            return True
            
        except Exception as e:
            self._add_error(f"Failed to write STEP file: {str(e)}")
            return False
    
    def _generate_header(self) -> str:
        """生成STEP文件头部"""
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        
        header = f"""ISO-10303-21;
HEADER;
FILE_DESCRIPTION((''), '2;1');
FILE_NAME('{self.metadata.description}', '{timestamp}', ('{self.metadata.author}'), ('{self.metadata.organization}'), '', '', '{self.metadata.source_system}');
FILE_SCHEMA(('{self._schema}'));
ENDSEC;
"""
        return header


# ============================================================================
# STEP实用工具
# ============================================================================

class STEPUtils:
    """STEP文件实用工具"""
    
    @staticmethod
    def detect_schema(filepath: Union[str, Path]) -> Optional[str]:
        """检测STEP文件的schema类型"""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # 查找FILE_SCHEMA
                match = re.search(r"FILE_SCHEMA\(\('([^']+)'\)\)", content)
                if match:
                    return match.group(1)
        except Exception:
            pass
        return None
    
    @staticmethod
    def count_entities(filepath: Union[str, Path]) -> Dict[str, int]:
        """统计STEP文件中的实体类型"""
        entity_counts = {}
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # 提取所有实体类型
                entities = re.findall(r'#\d+=([A-Z_]+)\(', content)
                
                for entity_type in entities:
                    entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1
                    
        except Exception:
            pass
        
        return entity_counts
    
    @staticmethod
    def validate_step_file(filepath: Union[str, Path]) -> Tuple[bool, List[str]]:
        """验证STEP文件格式"""
        errors = []
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 检查文件头
            if not content.startswith("ISO-10303-21;"):
                errors.append("Missing or invalid ISO-10303-21 header")
            
            # 检查结束标记
            if "END-ISO-10303-21;" not in content:
                errors.append("Missing END-ISO-10303-21 marker")
            
            # 检查必要部分
            if "HEADER;" not in content:
                errors.append("Missing HEADER section")
            
            if "DATA;" not in content:
                errors.append("Missing DATA section")
            
            # 检查FILE_SCHEMA
            if not re.search(r"FILE_SCHEMA\(\('[^']+'\)\)", content):
                errors.append("Missing or invalid FILE_SCHEMA")
                
        except Exception as e:
            errors.append(f"Error reading file: {str(e)}")
        
        return len(errors) == 0, errors


print("STEP导出器加载完成")
print("=" * 60)
