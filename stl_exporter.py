"""
STL格式导出器实现
STL (Stereolithography) Format Exporter Implementation

支持:
- ASCII STL格式
- 二进制STL格式
- 多实体导出
- 法向量自动计算

格式规范参考:
- 3D Systems Stereolithography Interface Specification
"""

import struct
from pathlib import Path
from typing import Union, List, BinaryIO, Optional
import numpy as np

from cad_exporter_base import (
    CADExporter, MeshData, Triangle, Vector3D,
    ExportOptions, ExportFormat, ExportProgress
)


class STLExporter(CADExporter):
    """
    STL格式导出器
    
    STL (Stereolithography) 是3D打印和快速原型制造的标准格式。
    每个文件包含一个或多个三角面片集合（solid）。
    """
    
    def __init__(self, options: Optional[ExportOptions] = None):
        super().__init__(options)
        self._update_ascii_flag(options)
    
    def _update_ascii_flag(self, options: Optional[ExportOptions] = None):
        """更新ASCII标志"""
        if options:
            self._is_ascii = options.stl_ascii
        elif self.options:
            self._is_ascii = self.options.stl_ascii
        else:
            self._is_ascii = False
    
    @property
    def format_name(self) -> str:
        return "STL (Stereolithography)"
    
    @property
    def file_extension(self) -> str:
        return ".stl"
    
    def export_mesh(self, mesh: MeshData, filepath: Union[str, Path]) -> bool:
        """
        导出网格为STL格式
        
        Args:
            mesh: 网格数据
            filepath: 输出文件路径
            
        Returns:
            导出是否成功
        """
        # 更新ASCII标志（选项可能已更改）
        self._update_ascii_flag()
        
        # 验证数据
        if not self.validate_mesh(mesh):
            return False
        
        self._report_stage("STL Export", f"Exporting {len(mesh.triangles)} triangles")
        
        # 确保法向量正确
        mesh = self._ensure_normals(mesh)
        
        # 选择导出格式
        if self._is_ascii:
            return self._export_ascii(mesh, filepath)
        else:
            return self._export_binary(mesh, filepath)
    
    def export_meshes(self, meshes: List[MeshData], filepath: Union[str, Path]) -> bool:
        """
        导出多个网格（多实体）
        
        Args:
            meshes: 网格数据列表
            filepath: 输出文件路径
            
        Returns:
            导出是否成功
        """
        self._report_stage("Multi-Mesh STL Export", f"Exporting {len(meshes)} solids")
        
        if self._is_ascii:
            return self._export_multi_ascii(meshes, filepath)
        else:
            return self._export_multi_binary(meshes, filepath)
    
    def export_brep(self, solid, filepath: Union[str, Path]) -> bool:
        """
        导出B-rep为STL（需要先三角化）
        
        注意: B-rep需要首先转换为网格
        """
        self._add_error("STL format requires mesh data. Please convert B-rep to mesh first.")
        return False
    
    def _ensure_normals(self, mesh: MeshData) -> MeshData:
        """确保所有三角形有正确的法向量"""
        new_mesh = MeshData(name=mesh.name)
        new_mesh.vertices = mesh.vertices.copy()
        
        for tri in mesh.triangles:
            # 计算法向量
            computed_normal = tri.compute_normal()
            
            # 检查现有法向量是否有效
            existing_length = np.sqrt(
                tri.normal.x**2 + tri.normal.y**2 + tri.normal.z**2
            )
            
            if existing_length < 0.99 or existing_length > 1.01:
                # 使用计算的法向量
                normal = computed_normal
            else:
                # 保持现有法向量
                normal = tri.normal
            
            new_tri = Triangle(
                normal=normal,
                v1=tri.v1,
                v2=tri.v2,
                v3=tri.v3,
                attribute=tri.attribute
            )
            new_mesh.triangles.append(new_tri)
        
        return new_mesh
    
    def _export_ascii(self, mesh: MeshData, filepath: Union[str, Path]) -> bool:
        """导出ASCII格式STL"""
        try:
            path = self._ensure_directory(filepath)
            solid_name = self.options.stl_solid_name or mesh.name or "Solid"
            
            with open(path, 'w', encoding='utf-8') as f:
                # 写入solid头
                f.write(f"solid {solid_name}\n")
                
                total = len(mesh.triangles)
                for i, tri in enumerate(mesh.triangles):
                    self._report_progress("Writing triangles", i + 1, total)
                    
                    # 写入facet
                    f.write(f"  facet normal {tri.normal.x:.6e} {tri.normal.y:.6e} {tri.normal.z:.6e}\n")
                    f.write("    outer loop\n")
                    
                    # 写入顶点
                    f.write(f"      vertex {tri.v1.x:.6e} {tri.v1.y:.6e} {tri.v1.z:.6e}\n")
                    f.write(f"      vertex {tri.v2.x:.6e} {tri.v2.y:.6e} {tri.v2.z:.6e}\n")
                    f.write(f"      vertex {tri.v3.x:.6e} {tri.v3.y:.6e} {tri.v3.z:.6e}\n")
                    
                    f.write("    endloop\n")
                    f.write("  endfacet\n")
                
                # 写入solid尾
                f.write(f"endsolid {solid_name}\n")
            
            self._report_stage("Complete", f"ASCII STL exported to {path}")
            return True
            
        except Exception as e:
            self._add_error(f"Failed to export ASCII STL: {str(e)}")
            return False
    
    def _export_binary(self, mesh: MeshData, filepath: Union[str, Path]) -> bool:
        """导出二进制格式STL"""
        try:
            path = self._ensure_directory(filepath)
            
            with open(path, 'wb') as f:
                # 写入80字节头部（可包含描述信息）
                header = f"STL Binary - {mesh.name}".encode('utf-8')[:80]
                header = header.ljust(80, b'\x00')
                f.write(header)
                
                # 写入三角形数量（4字节无符号整数）
                num_triangles = len(mesh.triangles)
                f.write(struct.pack('<I', num_triangles))
                
                # 写入每个三角形
                for i, tri in enumerate(mesh.triangles):
                    self._report_progress("Writing triangles", i + 1, num_triangles)
                    
                    # 法向量（3个float32）
                    f.write(struct.pack('<3f', tri.normal.x, tri.normal.y, tri.normal.z))
                    
                    # 顶点1（3个float32）
                    f.write(struct.pack('<3f', tri.v1.x, tri.v1.y, tri.v1.z))
                    
                    # 顶点2（3个float32）
                    f.write(struct.pack('<3f', tri.v2.x, tri.v2.y, tri.v2.z))
                    
                    # 顶点3（3个float32）
                    f.write(struct.pack('<3f', tri.v3.x, tri.v3.y, tri.v3.z))
                    
                    # 属性字节计数（2字节，通常为0）
                    f.write(struct.pack('<H', tri.attribute))
            
            self._report_stage("Complete", f"Binary STL exported to {path}")
            return True
            
        except Exception as e:
            self._add_error(f"Failed to export binary STL: {str(e)}")
            return False
    
    def _export_multi_ascii(self, meshes: List[MeshData], filepath: Union[str, Path]) -> bool:
        """导出多个网格为ASCII格式"""
        try:
            path = self._ensure_directory(filepath)
            
            with open(path, 'w', encoding='utf-8') as f:
                for mesh_idx, mesh in enumerate(meshes):
                    solid_name = mesh.name or f"Solid_{mesh_idx + 1}"
                    
                    # 写入solid头
                    f.write(f"solid {solid_name}\n")
                    
                    total = len(mesh.triangles)
                    for i, tri in enumerate(mesh.triangles):
                        self._report_progress(
                            f"Writing solid {mesh_idx + 1}/{len(meshes)}", 
                            i + 1, total
                        )
                        
                        # 写入facet
                        f.write(f"  facet normal {tri.normal.x:.6e} {tri.normal.y:.6e} {tri.normal.z:.6e}\n")
                        f.write("    outer loop\n")
                        
                        # 写入顶点
                        f.write(f"      vertex {tri.v1.x:.6e} {tri.v1.y:.6e} {tri.v1.z:.6e}\n")
                        f.write(f"      vertex {tri.v2.x:.6e} {tri.v2.y:.6e} {tri.v2.z:.6e}\n")
                        f.write(f"      vertex {tri.v3.x:.6e} {tri.v3.y:.6e} {tri.v3.z:.6e}\n")
                        
                        f.write("    endloop\n")
                        f.write("  endfacet\n")
                    
                    # 写入solid尾
                    f.write(f"endsolid {solid_name}\n")
            
            self._report_stage("Complete", f"Multi-solid ASCII STL exported to {path}")
            return True
            
        except Exception as e:
            self._add_error(f"Failed to export multi-solid ASCII STL: {str(e)}")
            return False
    
    def _export_multi_binary(self, meshes: List[MeshData], filepath: Union[str, Path]) -> bool:
        """导出多个网格为二进制格式（合并为一个文件）"""
        try:
            path = self._ensure_directory(filepath)
            
            # 计算总三角形数
            total_triangles = sum(len(m.triangles) for m in meshes)
            
            with open(path, 'wb') as f:
                # 写入80字节头部
                header = b"Multi-Solid Binary STL"
                header = header.ljust(80, b'\x00')
                f.write(header)
                
                # 写入总三角形数量
                f.write(struct.pack('<I', total_triangles))
                
                # 写入所有三角面片
                triangle_count = 0
                for mesh in meshes:
                    for tri in mesh.triangles:
                        triangle_count += 1
                        self._report_progress("Writing triangles", triangle_count, total_triangles)
                        
                        # 法向量
                        f.write(struct.pack('<3f', tri.normal.x, tri.normal.y, tri.normal.z))
                        
                        # 顶点
                        f.write(struct.pack('<3f', tri.v1.x, tri.v1.y, tri.v1.z))
                        f.write(struct.pack('<3f', tri.v2.x, tri.v2.y, tri.v2.z))
                        f.write(struct.pack('<3f', tri.v3.x, tri.v3.y, tri.v3.z))
                        
                        # 属性字节
                        f.write(struct.pack('<H', tri.attribute))
            
            self._report_stage("Complete", f"Multi-solid binary STL exported to {path}")
            return True
            
        except Exception as e:
            self._add_error(f"Failed to export multi-solid binary STL: {str(e)}")
            return False
    
    @staticmethod
    def read_ascii_stl(filepath: Union[str, Path]) -> MeshData:
        """
        读取ASCII格式STL文件
        
        Args:
            filepath: STL文件路径
            
        Returns:
            网格数据
        """
        mesh = MeshData()
        mesh.name = Path(filepath).stem
        
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        current_normal = Vector3D(0, 0, 1)
        vertices = []
        
        for line in lines:
            line = line.strip().lower()
            
            if line.startswith('facet normal'):
                # 解析法向量
                parts = line.split()
                if len(parts) >= 6:
                    current_normal = Vector3D(
                        float(parts[2]), float(parts[3]), float(parts[4])
                    )
            
            elif line.startswith('vertex'):
                # 解析顶点
                parts = line.split()
                if len(parts) >= 4:
                    vertices.append(Vector3D(
                        float(parts[1]), float(parts[2]), float(parts[3])
                    ))
                    
                    # 每3个顶点构成一个三角形
                    if len(vertices) == 3:
                        tri = Triangle(
                            normal=current_normal,
                            v1=vertices[0],
                            v2=vertices[1],
                            v3=vertices[2]
                        )
                        mesh.triangles.append(tri)
                        mesh.vertices.extend(vertices)
                        vertices = []
        
        return mesh
    
    @staticmethod
    def read_binary_stl(filepath: Union[str, Path]) -> MeshData:
        """
        读取二进制格式STL文件
        
        Args:
            filepath: STL文件路径
            
        Returns:
            网格数据
        """
        mesh = MeshData()
        mesh.name = Path(filepath).stem
        
        with open(filepath, 'rb') as f:
            # 跳过80字节头部
            f.read(80)
            
            # 读取三角形数量
            num_triangles = struct.unpack('<I', f.read(4))[0]
            
            for _ in range(num_triangles):
                # 读取法向量
                normal_data = struct.unpack('<3f', f.read(12))
                normal = Vector3D(normal_data[0], normal_data[1], normal_data[2])
                
                # 读取3个顶点
                v1_data = struct.unpack('<3f', f.read(12))
                v2_data = struct.unpack('<3f', f.read(12))
                v3_data = struct.unpack('<3f', f.read(12))
                
                v1 = Vector3D(v1_data[0], v1_data[1], v1_data[2])
                v2 = Vector3D(v2_data[0], v2_data[1], v2_data[2])
                v3 = Vector3D(v3_data[0], v3_data[1], v3_data[2])
                
                # 读取属性字节
                attribute = struct.unpack('<H', f.read(2))[0]
                
                tri = Triangle(
                    normal=normal,
                    v1=v1,
                    v2=v2,
                    v3=v3,
                    attribute=attribute
                )
                mesh.triangles.append(tri)
                mesh.vertices.extend([v1, v2, v3])
        
        return mesh
    
    @staticmethod
    def detect_format(filepath: Union[str, Path]) -> str:
        """
        检测STL文件格式（ASCII或二进制）
        
        Args:
            filepath: STL文件路径
            
        Returns:
            'ascii', 'binary', 或 'unknown'
        """
        with open(filepath, 'rb') as f:
            header = f.read(80)
            
            # 检查是否包含"solid"关键字（ASCII特征）
            try:
                header_str = header.decode('utf-8', errors='ignore').lower()
                if 'solid' in header_str:
                    # 进一步验证
                    f.seek(0)
                    content = f.read().decode('utf-8', errors='ignore').lower()
                    if 'facet normal' in content and 'vertex' in content:
                        return 'ascii'
            except:
                pass
            
            # 检查文件大小是否匹配二进制格式
            try:
                f.seek(80)
                num_triangles = struct.unpack('<I', f.read(4))[0]
                expected_size = 80 + 4 + num_triangles * 50
                actual_size = Path(filepath).stat().st_size
                if expected_size == actual_size:
                    return 'binary'
            except:
                pass
        
        return 'unknown'


# ============================================================================
# STL网格修复工具
# ============================================================================

class STLRepairTool:
    """STL网格修复工具"""
    
    @staticmethod
    def fix_normals(mesh: MeshData) -> MeshData:
        """修复法向量方向（统一朝外）"""
        # 计算模型中心
        if not mesh.vertices:
            return mesh
        
        center = Vector3D(
            sum(v.x for v in mesh.vertices) / len(mesh.vertices),
            sum(v.y for v in mesh.vertices) / len(mesh.vertices),
            sum(v.z for v in mesh.vertices) / len(mesh.vertices)
        )
        
        new_mesh = MeshData(name=mesh.name)
        new_mesh.vertices = mesh.vertices.copy()
        
        for tri in mesh.triangles:
            # 计算三角形中心
            tri_center = Vector3D(
                (tri.v1.x + tri.v2.x + tri.v3.x) / 3,
                (tri.v1.y + tri.v2.y + tri.v3.y) / 3,
                (tri.v1.z + tri.v2.z + tri.v3.z) / 3
            )
            
            # 从模型中心指向三角形中心的向量
            to_tri = Vector3D(
                tri_center.x - center.x,
                tri_center.y - center.y,
                tri_center.z - center.z
            ).normalize()
            
            # 计算正确的法向量
            computed = tri.compute_normal()
            
            # 检查法向量方向
            dot = computed.x * to_tri.x + computed.y * to_tri.y + computed.z * to_tri.z
            
            if dot < 0:
                # 翻转法向量
                computed = Vector3D(-computed.x, -computed.y, -computed.z)
                # 交换顶点顺序
                v1, v2, v3 = tri.v1, tri.v3, tri.v2
            else:
                v1, v2, v3 = tri.v1, tri.v2, tri.v3
            
            new_tri = Triangle(
                normal=computed,
                v1=v1,
                v2=v2,
                v3=v3,
                attribute=tri.attribute
            )
            new_mesh.triangles.append(new_tri)
        
        return new_mesh
    
    @staticmethod
    def remove_degenerate_triangles(mesh: MeshData, tolerance: float = 1e-10) -> MeshData:
        """移除退化三角形（零面积）"""
        new_mesh = MeshData(name=mesh.name)
        new_mesh.vertices = mesh.vertices.copy()
        
        removed_count = 0
        for tri in mesh.triangles:
            # 计算边长
            e1 = np.sqrt((tri.v2.x - tri.v1.x)**2 + (tri.v2.y - tri.v1.y)**2 + (tri.v2.z - tri.v1.z)**2)
            e2 = np.sqrt((tri.v3.x - tri.v2.x)**2 + (tri.v3.y - tri.v2.y)**2 + (tri.v3.z - tri.v2.z)**2)
            e3 = np.sqrt((tri.v1.x - tri.v3.x)**2 + (tri.v1.y - tri.v3.y)**2 + (tri.v1.z - tri.v3.z)**2)
            
            # 检查是否退化
            if e1 < tolerance or e2 < tolerance or e3 < tolerance:
                removed_count += 1
                continue
            
            new_mesh.triangles.append(tri)
        
        print(f"Removed {removed_count} degenerate triangles")
        return new_mesh
    
    @staticmethod
    def merge_duplicate_vertices(mesh: MeshData, tolerance: float = 1e-6) -> MeshData:
        """合并重复顶点"""
        if not mesh.vertices:
            return mesh
        
        # 使用空间哈希来加速查找
        vertex_map = {}  # 旧索引 -> 新索引
        new_vertices = []
        
        def get_vertex_key(v: Vector3D) -> tuple:
            """生成顶点哈希键"""
            scale = 1.0 / tolerance
            return (
                int(round(v.x * scale)),
                int(round(v.y * scale)),
                int(round(v.z * scale))
            )
        
        for i, v in enumerate(mesh.vertices):
            key = get_vertex_key(v)
            if key in vertex_map:
                # 使用已有顶点
                pass
            else:
                # 添加新顶点
                vertex_map[key] = len(new_vertices)
                new_vertices.append(v)
        
        # 重建三角形索引
        new_mesh = MeshData(name=mesh.name)
        new_mesh.vertices = new_vertices
        
        for tri in mesh.triangles:
            # 这里简化处理，实际应该重新映射顶点索引
            new_mesh.triangles.append(tri)
        
        print(f"Merged {len(mesh.vertices)} vertices to {len(new_vertices)}")
        return new_mesh


print("STL导出器加载完成")
print("=" * 60)
