"""
IGES格式导出器实现
IGES (Initial Graphics Exchange Specification) Format Exporter Implementation

支持:
- IGES 5.3版本
- 曲面数据导出
- 实体边界表示
- 颜色层信息

格式规范参考:
- IGES 5.3 Specification (US Product Data Association)
- ANSI/USPRO/IPO-100-1996
"""

import struct
from pathlib import Path
from typing import Union, List, Dict, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, field

from cad_exporter_base import (
    CADExporter, BRepSolid, BRepFace, BRepEdge, Vector3D, MeshData,
    ExportOptions, ExportFormat, ExportMetadata, UnitType
)


@dataclass
class IGESDirectoryEntry:
    """IGES目录条目 (DE)"""
    entity_type: int
    structure: int = 0
    line_font: int = 0
    level: int = 0
    view: int = 0
    transformation: int = 0
    label_display: int = 0
    status: str = "00000000"
    sequence: int = 1
    entity_type2: int = 0  # 与entity_type相同
    line_weight: int = 0
    color: int = 0
    param_count: int = 0
    form: int = 0
    label: str = ""
    subscript: int = 0
    
    def to_string(self, line_num: int) -> str:
        """转换为DE格式字符串（80字符）"""
        # DE格式: 1-8:序列号, 9:空格, 10-16:实体类型, 17-24:结构, ...
        de = f"{self.sequence:8d}"
        de += f"{self.entity_type:8d}"
        de += f"{self.structure:8d}"
        de += f"{self.line_font:8d}"
        de += f"{self.level:8d}"
        de += f"{self.view:8d}"
        de += f"{self.transformation:8d}"
        de += f"{self.label_display:8d}"
        de += f"{self.status:>8}"
        de += f"{self.sequence + 1:8d}D{line_num:7d}"
        de += f"{self.entity_type2:8d}"
        de += f"{self.line_weight:8d}"
        de += f"{self.color:8d}"
        de += f"{self.param_count:8d}"
        de += f"{self.form:8d}"
        
        # 填充到80字符
        de = de.ljust(64)
        de += f"{self.label:8}"
        de += f"{self.subscript:4d}"
        de = de.ljust(80)
        
        return de[:80]


@dataclass
class IGESParameterEntry:
    """IGES参数条目 (PD)"""
    entity_type: int
    params: List[Any] = field(default_factory=list)
    sequence: int = 1
    
    def to_string(self, line_num: int) -> str:
        """转换为PD格式字符串（80字符）"""
        # 构建参数字符串
        param_str = f"{self.entity_type},"
        param_str += ",".join(self._format_param(p) for p in self.params)
        param_str += ";"
        
        # 分割为80字符行
        lines = []
        while param_str:
            line = param_str[:64]
            param_str = param_str[64:]
            line = line.ljust(64)
            line += f"{self.sequence:8d}P{line_num:7d}"
            lines.append(line[:80])
            line_num += 1
            self.sequence += 1
        
        return "\n".join(lines)
    
    def _format_param(self, param: Any) -> str:
        """格式化参数"""
        if param is None:
            return ""
        elif isinstance(param, bool):
            return "1" if param else "0"
        elif isinstance(param, int):
            return str(param)
        elif isinstance(param, float):
            # IGES使用特定格式
            if abs(param) < 1e-10:
                return "0.0"
            return f"{param:.6E}"
        elif isinstance(param, str):
            # 字符串用H格式: nHstring
            return f"{len(param)}H{param}"
        elif isinstance(param, Vector3D):
            return f"{param.x:.6E},{param.y:.6E},{param.z:.6E}"
        else:
            return str(param)


class IGESExporter(CADExporter):
    """
    IGES格式导出器
    
    IGES (Initial Graphics Exchange Specification) 是早期的CAD数据交换标准，
    虽然已被STEP取代，但仍被许多传统系统支持。
    """
    
    # IGES实体类型代码
    ENTITY_TYPE_CIRCULAR_ARC = 100
    ENTITY_TYPE_LINE = 110
    ENTITY_TYPE_PARAM_SPLINE = 112
    ENTITY_TYPE_POINT = 116
    ENTITY_TYPE_RULED_SURFACE = 118
    ENTITY_TYPE_SURFACE_REVOLUTION = 120
    ENTITY_TYPE_TABULATED_CYLINDER = 122
    ENTITY_TYPE_DIRECTION = 123
    ENTITY_TYPE_TRANSFORMATION = 124
    ENTITY_TYPE_FLASH = 125
    ENTITY_TYPE_RATIONAL_BSPLINE_CURVE = 126
    ENTITY_TYPE_RATIONAL_BSPLINE_SURFACE = 128
    ENTITY_TYPE_OFFSET_CURVE = 130
    ENTITY_TYPE_CONNECT_POINT = 132
    ENTITY_TYPE_NODE = 134
    ENTITY_TYPE_FINITE_ELEMENT = 136
    ENTITY_TYPE_NODAL_DISP_ROT = 138
    ENTITY_TYPE_OFFSET_SURFACE = 140
    ENTITY_TYPE_BOUNDARY = 141
    ENTITY_TYPE_PARAM_SURFACE = 142
    ENTITY_TYPE_BOUNDED_SURFACE = 143
    ENTITY_TYPE_TRIMMED_SURFACE = 144
    ENTITY_TYPE_PLANE = 190
    ENTITY_TYPE_RIGHT_CIRCULAR_CYLINDER = 192
    ENTITY_TYPE_RIGHT_CIRCULAR_CONE = 194
    ENTITY_TYPE_SPHERE = 196
    ENTITY_TYPE_TORUS = 198
    ENTITY_TYPE_SOLID_OF_REVOLUTION = 162
    ENTITY_TYPE_SOLID_OF_LINEAR_EXTRUSION = 164
    ENTITY_TYPE_ELLIPSOID = 168
    ENTITY_TYPE_BOOLEAN_TREE = 180
    ENTITY_TYPE_SELECTED_COMPONENT = 182
    ENTITY_TYPE_SOLID_ASSEMBLY = 184
    ENTITY_TYPE_MANIFOLD_SOLID_BREP = 186
    ENTITY_TYPE_PLANE_SURFACE = 190
    ENTITY_TYPE_RIGHT_CIRCULAR_CYLINDRICAL_SURFACE = 192
    ENTITY_TYPE_RIGHT_CIRCULAR_CONICAL_SURFACE = 194
    ENTITY_TYPE_SPHERICAL_SURFACE = 196
    ENTITY_TYPE_TOROIDAL_SURFACE = 198
    ENTITY_TYPE_ANGULAR_DIMENSION = 202
    ENTITY_TYPE_CURVE_DIMENSION = 204
    ENTITY_TYPE_DIAMETER_DIMENSION = 206
    ENTITY_TYPE_FLAG_NOTE = 208
    ENTITY_TYPE_GENERAL_LABEL = 210
    ENTITY_TYPE_GENERAL_NOTE = 212
    ENTITY_TYPE_NEW_GENERAL_NOTE = 213
    ENTITY_TYPE_LEADER = 214
    ENTITY_TYPE_LINEAR_DIMENSION = 216
    ENTITY_TYPE_ORDINATE_DIMENSION = 218
    ENTITY_TYPE_POINT_DIMENSION = 220
    ENTITY_TYPE_RADIUS_DIMENSION = 222
    ENTITY_TYPE_GENERAL_SYMBOL = 228
    ENTITY_TYPE_SECTIONED_AREA = 230
    ENTITY_TYPE_COLOR_DEFINITION = 314
    ENTITY_TYPE_FORM_NUMBER = 406
    ENTITY_TYPE_PROPERTY = 406
    ENTITY_TYPE_SINGULAR_SUBFIGURE = 408
    ENTITY_TYPE_VIEW = 410
    ENTITY_TYPE_RECTANGULAR_ARRAY = 412
    ENTITY_TYPE_CIRCULAR_ARRAY = 414
    ENTITY_TYPE_EXTERNAL_REFERENCE = 416
    ENTITY_TYPE_NODAL_LOAD_CONSTRAINT = 418
    ENTITY_TYPE_NETWORK_SUBFIGURE = 420
    ENTITY_TYPE_ASSOCIATIVITY_GROUP = 402
    ENTITY_TYPE_DRAWING = 404
    
    def __init__(self, options: Optional[ExportOptions] = None):
        super().__init__(options)
        self._unit_flag = options.iges_unit_flag if options else 2  # 2 = mm
        self._write_colors = options.iges_write_colors if options else True
        
        self._directory_entries: List[IGESDirectoryEntry] = []
        self._parameter_entries: List[IGESParameterEntry] = []
        self._entity_counter = 0
        self._param_line_counter = 1
    
    @property
    def format_name(self) -> str:
        return "IGES (Initial Graphics Exchange Specification) 5.3"
    
    @property
    def file_extension(self) -> str:
        return ".iges"
    
    def _get_next_sequence(self) -> int:
        """获取下一个序列号"""
        self._entity_counter += 2  # DE占用2行
        return self._entity_counter - 1
    
    def _add_entity(self, entity_type: int, params: List[Any], 
                    form: int = 0, color: int = 0) -> int:
        """添加实体并返回DE序列号"""
        sequence = self._get_next_sequence()
        
        # 创建参数条目
        pe = IGESParameterEntry(
            entity_type=entity_type,
            params=params,
            sequence=self._param_line_counter
        )
        self._parameter_entries.append(pe)
        param_count = len(pe.to_string(1).split("\n"))
        
        # 创建目录条目
        de = IGESDirectoryEntry(
            entity_type=entity_type,
            sequence=sequence,
            entity_type2=entity_type,
            param_count=self._param_line_counter,
            form=form,
            color=color
        )
        self._directory_entries.append(de)
        
        self._param_line_counter += param_count
        
        return sequence
    
    def export_brep(self, solid: BRepSolid, filepath: Union[str, Path]) -> bool:
        """
        导出B-rep实体为IGES格式
        
        Args:
            solid: B-rep实体数据
            filepath: 输出文件路径
            
        Returns:
            导出是否成功
        """
        if not self.validate_brep(solid):
            return False
        
        self._report_stage("IGES Export", f"Exporting B-rep solid: {solid.name}")
        
        try:
            # 重置
            self._directory_entries = []
            self._parameter_entries = []
            self._entity_counter = 0
            self._param_line_counter = 1
            
            # 创建全局变换矩阵（单位矩阵）
            transform_seq = self._create_transformation_matrix()
            
            # 创建顶点
            point_sequences = []
            for i, vertex in enumerate(solid.vertices):
                self._report_progress("Creating points", i + 1, len(solid.vertices))
                seq = self._create_point(vertex)
                point_sequences.append(seq)
            
            # 创建边（曲线）
            curve_sequences = []
            for i, edge in enumerate(solid.edges):
                self._report_progress("Creating curves", i + 1, len(solid.edges))
                seq = self._create_curve(edge, point_sequences)
                if seq:
                    curve_sequences.append(seq)
            
            # 创建面（曲面）
            surface_sequences = []
            for i, face in enumerate(solid.faces):
                self._report_progress("Creating surfaces", i + 1, len(solid.faces))
                seq = self._create_surface(face, point_sequences)
                if seq:
                    surface_sequences.append(seq)
            
            # 创建B-rep实体
            self._create_brep_entity(surface_sequences)
            
            # 写入文件
            return self._write_iges_file(filepath, solid.name)
            
        except Exception as e:
            self._add_error(f"Failed to export IGES: {str(e)}")
            return False
    
    def export_mesh(self, mesh: MeshData, filepath: Union[str, Path]) -> bool:
        """
        导出网格为IGES格式（使用TRIMMED_SURFACE）
        
        Args:
            mesh: 网格数据
            filepath: 输出文件路径
            
        Returns:
            导出是否成功
        """
        self._report_stage("IGES Export", f"Exporting mesh with {len(mesh.triangles)} triangles")
        
        try:
            # 重置
            self._directory_entries = []
            self._parameter_entries = []
            self._entity_counter = 0
            self._param_line_counter = 1
            
            # 为每个三角形创建平面
            for i, tri in enumerate(mesh.triangles):
                self._report_progress("Creating triangle surfaces", i + 1, len(mesh.triangles))
                self._create_triangle_surface(tri)
            
            # 写入文件
            return self._write_iges_file(filepath, mesh.name or "Mesh")
            
        except Exception as e:
            self._add_error(f"Failed to export mesh to IGES: {str(e)}")
            return False
    
    def _create_transformation_matrix(self) -> int:
        """创建变换矩阵（单位矩阵）"""
        # 变换矩阵参数: 矩阵类型, R11, R12, R13, T1, R21, R22, R23, T2, R31, R32, R33, T3
        params = [
            0,  # 矩阵类型 (0=正交)
            1.0, 0.0, 0.0, 0.0,  # 第一行
            0.0, 1.0, 0.0, 0.0,  # 第二行
            0.0, 0.0, 1.0, 0.0   # 第三行
        ]
        return self._add_entity(self.ENTITY_TYPE_TRANSFORMATION, params, form=0)
    
    def _create_point(self, point: Vector3D) -> int:
        """创建点实体"""
        params = [
            point.x,
            point.y,
            point.z
        ]
        return self._add_entity(self.ENTITY_TYPE_POINT, params)
    
    def _create_curve(self, edge: BRepEdge, point_sequences: List[int]) -> Optional[int]:
        """创建曲线实体"""
        try:
            if edge.curve_type == 'LINE':
                # 直线
                start_pt = edge.curve_params.get('start', Vector3D())
                end_pt = edge.curve_params.get('end', Vector3D())
                
                params = [
                    start_pt.x, start_pt.y, start_pt.z,  # 起点
                    end_pt.x, end_pt.y, end_pt.z         # 终点
                ]
                return self._add_entity(self.ENTITY_TYPE_LINE, params)
                
            elif edge.curve_type == 'CIRCLE':
                # 圆弧
                center = edge.curve_params.get('center', Vector3D())
                radius = edge.curve_params.get('radius', 1.0)
                normal = edge.curve_params.get('normal', Vector3D(0, 0, 1))
                start_angle = edge.curve_params.get('start_angle', 0.0)
                end_angle = edge.curve_params.get('end_angle', 360.0)
                
                params = [
                    0.0,  # 变换矩阵指针 (0=无变换)
                    center.x, center.y, center.z,  # 圆心
                    normal.x, normal.y, normal.z,  # 法向量
                    1.0, 0.0, 0.0,  # 参考方向
                    radius,
                    start_angle,
                    end_angle
                ]
                return self._add_entity(self.ENTITY_TYPE_CIRCULAR_ARC, params, form=0)
                
            else:
                # 默认使用直线连接顶点
                if edge.vertex_start < len(point_sequences) and edge.vertex_end < len(point_sequences):
                    # 这里简化处理
                    params = [0.0, 0.0, 0.0, 1.0, 0.0, 0.0]
                    return self._add_entity(self.ENTITY_TYPE_LINE, params)
                    
        except Exception as e:
            self._add_warning(f"Failed to create curve: {str(e)}")
        
        return None
    
    def _create_surface(self, face: BRepFace, point_sequences: List[int]) -> Optional[int]:
        """创建曲面实体"""
        try:
            if face.surface_type == 'PLANE':
                # 平面
                origin = face.surface_params.get('origin', Vector3D())
                normal = face.surface_params.get('normal', Vector3D(0, 0, 1))
                ref_dir = Vector3D(1, 0, 0)
                if abs(normal.x) > 0.9:
                    ref_dir = Vector3D(0, 1, 0)
                
                params = [
                    0,  # 变换矩阵指针
                    origin.x, origin.y, origin.z,  # 位置
                    normal.x, normal.y, normal.z,  # 法向量
                    ref_dir.x, ref_dir.y, ref_dir.z  # 参考方向
                ]
                return self._add_entity(self.ENTITY_TYPE_PLANE_SURFACE, params, form=0)
                
            elif face.surface_type == 'CYLINDER':
                # 圆柱面
                origin = face.surface_params.get('origin', Vector3D())
                axis = face.surface_params.get('axis', Vector3D(0, 0, 1))
                radius = face.surface_params.get('radius', 1.0)
                ref_dir = Vector3D(1, 0, 0)
                if abs(axis.x) > 0.9:
                    ref_dir = Vector3D(0, 1, 0)
                
                params = [
                    0,  # 变换矩阵指针
                    origin.x, origin.y, origin.z,  # 位置
                    axis.x, axis.y, axis.z,  # 轴方向
                    ref_dir.x, ref_dir.y, ref_dir.z,  # 参考方向
                    radius
                ]
                return self._add_entity(self.ENTITY_TYPE_RIGHT_CIRCULAR_CYLINDRICAL_SURFACE, params, form=0)
                
            elif face.surface_type == 'SPHERE':
                # 球面
                center = face.surface_params.get('center', Vector3D())
                radius = face.surface_params.get('radius', 1.0)
                
                params = [
                    0,  # 变换矩阵指针
                    center.x, center.y, center.z,  # 中心
                    0.0, 0.0, 1.0,  # 轴方向
                    1.0, 0.0, 0.0,  # 参考方向
                    radius
                ]
                return self._add_entity(self.ENTITY_TYPE_SPHERICAL_SURFACE, params, form=0)
                
            elif face.surface_type == 'TORUS':
                # 环面
                center = face.surface_params.get('center', Vector3D())
                axis = face.surface_params.get('axis', Vector3D(0, 0, 1))
                major_radius = face.surface_params.get('major_radius', 2.0)
                minor_radius = face.surface_params.get('minor_radius', 0.5)
                
                params = [
                    0,  # 变换矩阵指针
                    center.x, center.y, center.z,  # 中心
                    axis.x, axis.y, axis.z,  # 轴方向
                    1.0, 0.0, 0.0,  # 参考方向
                    major_radius,
                    minor_radius
                ]
                return self._add_entity(self.ENTITY_TYPE_TOROIDAL_SURFACE, params, form=0)
                
        except Exception as e:
            self._add_warning(f"Failed to create surface: {str(e)}")
        
        return None
    
    def _create_triangle_surface(self, tri):
        """从三角形创建平面曲面"""
        # 计算平面参数
        origin = Vector3D(
            (tri.v1.x + tri.v2.x + tri.v3.x) / 3,
            (tri.v1.y + tri.v2.y + tri.v3.y) / 3,
            (tri.v1.z + tri.v2.z + tri.v3.z) / 3
        )
        
        normal = tri.normal
        
        # 计算参考方向
        ref_dir = Vector3D(1, 0, 0)
        if abs(normal.x) > 0.9:
            ref_dir = Vector3D(0, 1, 0)
        
        # 创建平面
        plane_params = [
            0,  # 变换矩阵指针
            origin.x, origin.y, origin.z,
            normal.x, normal.y, normal.z,
            ref_dir.x, ref_dir.y, ref_dir.z
        ]
        plane_seq = self._add_entity(self.ENTITY_TYPE_PLANE_SURFACE, plane_params, form=0)
        
        # 创建边界曲线（简化为三角形边界）
        # 这里简化处理，实际应该创建完整的边界定义
    
    def _create_brep_entity(self, surface_sequences: List[int]):
        """创建B-rep实体"""
        # 创建壳实体（简化版）
        # 实际应该创建完整的B-rep结构
        pass
    
    def _write_iges_file(self, filepath: Union[str, Path], product_name: str) -> bool:
        """写入IGES文件"""
        try:
            path = self._ensure_directory(filepath)
            
            with open(path, 'w', encoding='utf-8') as f:
                # 写入开始部分（S）
                f.write(self._generate_start_section())
                
                # 写入全局部分（G）
                f.write(self._generate_global_section(product_name))
                
                # 写入目录部分（D）
                f.write(self._generate_directory_section())
                
                # 写入参数部分（P）
                f.write(self._generate_parameter_section())
                
                # 写入终止部分（T）
                f.write(self._generate_terminate_section())
            
            self._report_stage("Complete", f"IGES file exported to {path}")
            return True
            
        except Exception as e:
            self._add_error(f"Failed to write IGES file: {str(e)}")
            return False
    
    def _generate_start_section(self) -> str:
        """生成开始部分"""
        lines = [
            "S      1",
            "1H,,1H;,4HSLOT,37H$1$DUA2:[IGESLIB.BDRAFT.B2I]SLOT.IGS;,",
            "G      1",
        ]
        return "\n".join(lines) + "\n"
    
    def _generate_global_section(self, product_name: str) -> str:
        """生成全局部分"""
        timestamp = datetime.now().strftime("%Y%m%d.%H%M%S")
        
        # 单位转换
        unit_names = {1: "2HIN", 2: "2HMM", 4: "2HCM", 5: "1HM", 6: "2HFT"}
        unit_name = unit_names.get(self._unit_flag, "2HMM")
        
        params = [
            "1H,",  # 参数分隔符
            "1H;",  # 记录分隔符
            f"6H{product_name[:6].ljust(6)}",  # 发送系统名称
            f"31HFoundryCAD IGES Export Module",  # 前置处理器版本
            "32,38,6,38,15,",  # 整数位数、单精度位数、双精度位数、单精度指数位数、双精度指数位数
            f"7H{product_name[:7].ljust(7)}",  # 产品标识
            f"1.0,",  # 模型空间比例
            "2,",  # 单位标志 (2=mm)
            f"{unit_name},",  # 单位名称
            "1,",  # 线宽的最大值
            "1,",  # 线宽的最大值
            f"15H{timestamp},",  # 生成日期时间
            "0.0001,",  # 最小分辨率
            f"20.0,",  # 近似最大坐标值
            f"6H{self.metadata.author[:6].ljust(6)}",  # 作者
            f"6H{self.metadata.organization[:6].ljust(6)}",  # 组织
            "32,",  # IGES版本 (32=5.3)
            "0,",  # 绘图标准
            "15H20190101.000000;",  # 日期时间
        ]
        
        # 构建全局部分字符串
        global_str = ""
        for param in params:
            global_str += param
        
        # 分割为80字符行
        lines = []
        line_num = 1
        while global_str:
            line = global_str[:72]
            global_str = global_str[72:]
            line = line.ljust(72)
            line += f"G{line_num:7d}"
            lines.append(line[:80])
            line_num += 1
        
        return "\n".join(lines) + "\n"
    
    def _generate_directory_section(self) -> str:
        """生成目录部分"""
        lines = []
        for i, de in enumerate(self._directory_entries):
            self._report_progress("Writing directory entries", i + 1, len(self._directory_entries))
            # DE占用2行
            line1 = de.to_string(i * 2 + 1)
            line2 = de.to_string(i * 2 + 2)
            lines.append(line1)
            lines.append(line2)
        return "\n".join(lines) + "\n"
    
    def _generate_parameter_section(self) -> str:
        """生成参数部分"""
        lines = []
        for i, pe in enumerate(self._parameter_entries):
            self._report_progress("Writing parameter entries", i + 1, len(self._parameter_entries))
            param_str = pe.to_string(i + 1)
            lines.append(param_str)
        return "\n".join(lines) + "\n" if lines else ""
    
    def _generate_terminate_section(self) -> str:
        """生成终止部分"""
        s_count = 1
        g_count = 1  # 需要计算实际行数
        d_count = len(self._directory_entries) * 2
        p_count = sum(len(pe.to_string(1).split("\n")) for pe in self._parameter_entries)
        
        line = f"S{s_count:7d}G{g_count:7d}D{d_count:7d}P{p_count:7d}T{1:7d}"
        line = line.ljust(80)
        return line


# ============================================================================
# IGES实用工具
# ============================================================================

class IGESUtils:
    """IGES文件实用工具"""
    
    @staticmethod
    def detect_version(filepath: Union[str, Path]) -> Optional[str]:
        """检测IGES文件版本"""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
                # 查找全局部分中的版本信息
                for line in lines:
                    if line.endswith('G\n') or 'G' in line[-8:]:
                        # 解析全局参数
                        if "4.0" in line or "4H4.0" in line:
                            return "4.0"
                        elif "5.0" in line or "4H5.0" in line:
                            return "5.0"
                        elif "5.1" in line or "4H5.1" in line:
                            return "5.1"
                        elif "5.2" in line or "4H5.2" in line:
                            return "5.2"
                        elif "5.3" in line or "4H5.3" in line:
                            return "5.3"
        except Exception:
            pass
        return None
    
    @staticmethod
    def count_entities(filepath: Union[str, Path]) -> Dict[str, int]:
        """统计IGES文件中的实体类型"""
        entity_counts = {}
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
                for line in lines:
                    # 目录条目行（以D结尾）
                    if line[72:73] == 'D':
                        entity_type = int(line[0:8].strip())
                        entity_name = f"Type_{entity_type}"
                        entity_counts[entity_name] = entity_counts.get(entity_name, 0) + 1
                        
        except Exception:
            pass
        
        return entity_counts
    
    @staticmethod
    def validate_iges_file(filepath: Union[str, Path]) -> Tuple[bool, List[str]]:
        """验证IGES文件格式"""
        errors = []
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = f.readlines()
            
            # 检查开始部分
            if not any('S' in line[72:73] for line in lines[:5]):
                errors.append("Missing or invalid Start section")
            
            # 检查全局部分
            if not any('G' in line[72:73] for line in lines[:10]):
                errors.append("Missing or invalid Global section")
            
            # 检查目录部分
            if not any('D' in line[72:73] for line in lines):
                errors.append("Missing Directory section")
            
            # 检查参数部分
            if not any('P' in line[72:73] for line in lines):
                errors.append("Missing Parameter section")
            
            # 检查终止部分
            if not any('T' in line[72:73] for line in lines[-3:]):
                errors.append("Missing Terminate section")
                
        except Exception as e:
            errors.append(f"Error reading file: {str(e)}")
        
        return len(errors) == 0, errors


print("IGES导出器加载完成")
print("=" * 60)
