"""
CAD导出模块使用示例
Usage Examples for CAD Export Module

演示如何使用CAD导出模块进行各种导出操作
"""

import numpy as np
from pathlib import Path

# 导入模块
from cad_exporter_base import (
    MeshData, Triangle, Vector3D, BRepSolid, BRepFace, BRepEdge,
    ExportFormat, ExportOptions, UnitType, ExportMetadata
)
from cad_export_manager import (
    CADExportManager, export_mesh, export_brep, 
    convert_stl_to_step, get_file_info
)
from stl_exporter import STLExporter, STLRepairTool


def create_sample_cube_mesh(size: float = 10.0) -> MeshData:
    """创建示例立方体网格"""
    mesh = MeshData(name="SampleCube")
    
    # 立方体的8个顶点
    vertices = [
        Vector3D(0, 0, 0),
        Vector3D(size, 0, 0),
        Vector3D(size, size, 0),
        Vector3D(0, size, 0),
        Vector3D(0, 0, size),
        Vector3D(size, 0, size),
        Vector3D(size, size, size),
        Vector3D(0, size, size),
    ]
    mesh.vertices = vertices
    
    # 立方体的12个三角形面（每个面2个三角形）
    # 底面 (z=0)
    mesh.triangles.append(Triangle(
        normal=Vector3D(0, 0, -1),
        v1=vertices[0], v2=vertices[2], v3=vertices[1]
    ))
    mesh.triangles.append(Triangle(
        normal=Vector3D(0, 0, -1),
        v1=vertices[0], v2=vertices[3], v3=vertices[2]
    ))
    
    # 顶面 (z=size)
    mesh.triangles.append(Triangle(
        normal=Vector3D(0, 0, 1),
        v1=vertices[4], v2=vertices[5], v3=vertices[6]
    ))
    mesh.triangles.append(Triangle(
        normal=Vector3D(0, 0, 1),
        v1=vertices[4], v2=vertices[6], v3=vertices[7]
    ))
    
    # 前面 (y=0)
    mesh.triangles.append(Triangle(
        normal=Vector3D(0, -1, 0),
        v1=vertices[0], v2=vertices[1], v3=vertices[5]
    ))
    mesh.triangles.append(Triangle(
        normal=Vector3D(0, -1, 0),
        v1=vertices[0], v2=vertices[5], v3=vertices[4]
    ))
    
    # 后面 (y=size)
    mesh.triangles.append(Triangle(
        normal=Vector3D(0, 1, 0),
        v1=vertices[3], v2=vertices[7], v3=vertices[6]
    ))
    mesh.triangles.append(Triangle(
        normal=Vector3D(0, 1, 0),
        v1=vertices[3], v2=vertices[6], v3=vertices[2]
    ))
    
    # 左面 (x=0)
    mesh.triangles.append(Triangle(
        normal=Vector3D(-1, 0, 0),
        v1=vertices[0], v2=vertices[4], v3=vertices[7]
    ))
    mesh.triangles.append(Triangle(
        normal=Vector3D(-1, 0, 0),
        v1=vertices[0], v2=vertices[7], v3=vertices[3]
    ))
    
    # 右面 (x=size)
    mesh.triangles.append(Triangle(
        normal=Vector3D(1, 0, 0),
        v1=vertices[1], v2=vertices[2], v3=vertices[6]
    ))
    mesh.triangles.append(Triangle(
        normal=Vector3D(1, 0, 0),
        v1=vertices[1], v2=vertices[6], v3=vertices[5]
    ))
    
    return mesh


def create_sample_sphere_mesh(radius: float = 5.0, segments: int = 16) -> MeshData:
    """创建示例球体网格（经纬度细分）"""
    mesh = MeshData(name="SampleSphere")
    
    vertices = []
    
    # 生成顶点
    for i in range(segments + 1):
        phi = np.pi * i / segments
        for j in range(segments + 1):
            theta = 2 * np.pi * j / segments
            
            x = radius * np.sin(phi) * np.cos(theta)
            y = radius * np.sin(phi) * np.sin(theta)
            z = radius * np.cos(phi)
            
            vertices.append(Vector3D(x, y, z))
    
    mesh.vertices = vertices
    
    # 生成三角形
    for i in range(segments):
        for j in range(segments):
            v0 = i * (segments + 1) + j
            v1 = v0 + 1
            v2 = (i + 1) * (segments + 1) + j
            v3 = v2 + 1
            
            # 第一个三角形
            tri1 = Triangle(
                normal=Vector3D(),  # 稍后计算
                v1=vertices[v0],
                v2=vertices[v2],
                v3=vertices[v1]
            )
            tri1.normal = tri1.compute_normal()
            mesh.triangles.append(tri1)
            
            # 第二个三角形
            tri2 = Triangle(
                normal=Vector3D(),
                v1=vertices[v1],
                v2=vertices[v2],
                v3=vertices[v3]
            )
            tri2.normal = tri2.compute_normal()
            mesh.triangles.append(tri2)
    
    return mesh


def progress_callback(progress):
    """进度回调函数示例"""
    if progress.total > 0:
        print(f"[{progress.stage}] {progress.percentage:.1f}% - {progress.message}")
    else:
        print(f"[{progress.stage}] {progress.message}")


def example_1_basic_stl_export():
    """示例1: 基本STL导出"""
    print("\n" + "="*60)
    print("示例1: 基本STL导出")
    print("="*60)
    
    # 创建立方体网格
    mesh = create_sample_cube_mesh(size=10.0)
    print(f"Created mesh with {len(mesh.triangles)} triangles")
    
    # 导出为二进制STL
    output_path = "./examples/cube_binary.stl"
    result = export_mesh(
        mesh, 
        output_path,
        ExportFormat.STL_BINARY,
        progress_callback=progress_callback
    )
    print(f"Binary STL export: {'Success' if result else 'Failed'}")
    
    # 导出为ASCII STL
    output_path = "./examples/cube_ascii.stl"
    result = export_mesh(
        mesh,
        output_path,
        ExportFormat.STL_ASCII,
        progress_callback=progress_callback,
        stl_ascii=True
    )
    print(f"ASCII STL export: {'Success' if result else 'Failed'}")


def example_2_step_export():
    """示例2: STEP格式导出"""
    print("\n" + "="*60)
    print("示例2: STEP格式导出")
    print("="*60)
    
    # 创建立方体网格
    mesh = create_sample_cube_mesh(size=10.0)
    print(f"Created mesh with {len(mesh.triangles)} triangles")
    
    # 导出为STEP AP214
    output_path = "./examples/cube_ap214.step"
    result = export_mesh(
        mesh,
        output_path,
        ExportFormat.STEP_AP214,
        progress_callback=progress_callback
    )
    print(f"STEP AP214 export: {'Success' if result else 'Failed'}")
    
    # 导出为STEP AP203
    output_path = "./examples/cube_ap203.step"
    result = export_mesh(
        mesh,
        output_path,
        ExportFormat.STEP_AP203,
        progress_callback=progress_callback,
        step_schema="AP203"
    )
    print(f"STEP AP203 export: {'Success' if result else 'Failed'}")


def example_3_iges_export():
    """示例3: IGES格式导出"""
    print("\n" + "="*60)
    print("示例3: IGES格式导出")
    print("="*60)
    
    # 创建立方体网格
    mesh = create_sample_cube_mesh(size=10.0)
    print(f"Created mesh with {len(mesh.triangles)} triangles")
    
    # 导出为IGES
    output_path = "./examples/cube.iges"
    result = export_mesh(
        mesh,
        output_path,
        ExportFormat.IGES_5_3,
        progress_callback=progress_callback
    )
    print(f"IGES export: {'Success' if result else 'Failed'}")


def example_4_batch_export():
    """示例4: 批量导出"""
    print("\n" + "="*60)
    print("示例4: 批量导出")
    print("="*60)
    
    # 创建多个网格
    cube = create_sample_cube_mesh(size=10.0)
    sphere = create_sample_sphere_mesh(radius=5.0, segments=8)
    
    meshes = [cube, sphere]
    filepaths = [
        "./examples/batch_cube.stl",
        "./examples/batch_sphere.stl"
    ]
    
    # 使用导出管理器批量导出
    manager = CADExportManager()
    manager.set_progress_callback(progress_callback)
    
    results = manager.export_multiple(meshes, filepaths)
    
    for i, (mesh, path, result) in enumerate(zip(meshes, filepaths, results)):
        print(f"Export {i+1} ({mesh.name}): {'Success' if result else 'Failed'}")


def example_5_mesh_repair():
    """示例5: 网格修复"""
    print("\n" + "="*60)
    print("示例5: 网格修复")
    print("="*60)
    
    # 创建带有问题的网格（退化三角形）
    mesh = MeshData(name="DamagedMesh")
    
    # 添加正常三角形
    mesh.triangles.append(Triangle(
        normal=Vector3D(0, 0, 1),
        v1=Vector3D(0, 0, 0),
        v2=Vector3D(1, 0, 0),
        v3=Vector3D(0.5, 1, 0)
    ))
    
    # 添加退化三角形（零面积）
    mesh.triangles.append(Triangle(
        normal=Vector3D(0, 0, 1),
        v1=Vector3D(0, 0, 0),
        v2=Vector3D(0, 0, 0),
        v3=Vector3D(0, 0, 0)
    ))
    
    print(f"Original mesh: {len(mesh.triangles)} triangles")
    
    # 修复网格
    repaired = STLRepairTool.remove_degenerate_triangles(mesh, tolerance=1e-10)
    print(f"Repaired mesh: {len(repaired.triangles)} triangles")
    
    # 导出修复后的网格
    output_path = "./examples/repaired_mesh.stl"
    result = export_mesh(repaired, output_path, ExportFormat.STL_BINARY)
    print(f"Repaired mesh export: {'Success' if result else 'Failed'}")


def example_6_file_info():
    """示例6: 获取文件信息"""
    print("\n" + "="*60)
    print("示例6: 获取文件信息")
    print("="*60)
    
    # 首先导出一个文件
    mesh = create_sample_cube_mesh(size=10.0)
    filepath = "./examples/info_test.stl"
    export_mesh(mesh, filepath, ExportFormat.STL_BINARY)
    
    # 获取文件信息
    info = get_file_info(filepath)
    
    print(f"File: {info['filepath']}")
    print(f"Exists: {info['exists']}")
    print(f"Size: {info['size']} bytes")
    print(f"Format: {info['format']}")
    print(f"Format Subtype: {info.get('format_subtype', 'N/A')}")
    print(f"Valid: {info['valid']}")


def example_7_advanced_options():
    """示例7: 高级选项配置"""
    print("\n" + "="*60)
    print("示例7: 高级选项配置")
    print("="*60)
    
    # 创建立方体网格
    mesh = create_sample_cube_mesh(size=10.0)
    
    # 创建导出管理器
    manager = CADExportManager()
    
    # 配置选项
    manager.update_config(
        default_unit='millimeter',
        default_precision=0.0001,
        stl_ascii=False,
        auto_fix_mesh=True,
        validate_before_export=True
    )
    
    # 设置元数据
    metadata = ExportMetadata(
        author="Foundry Engineer",
        organization="Foundry Company",
        description="Casting part for simulation",
        unit=UnitType.MILLIMETER,
        precision=0.001
    )
    
    # 导出
    output_path = "./examples/advanced_options.stl"
    result = manager.export_mesh(mesh, output_path)
    print(f"Export with advanced options: {'Success' if result else 'Failed'}")
    
    # 保存配置
    config_path = "./examples/export_config.json"
    manager.save_config(config_path)
    print(f"Configuration saved to: {config_path}")


def example_8_sphere_multiple_formats():
    """示例8: 将球体导出为多种格式"""
    print("\n" + "="*60)
    print("示例8: 球体多格式导出")
    print("="*60)
    
    # 创建球体网格
    sphere = create_sample_sphere_mesh(radius=10.0, segments=16)
    print(f"Created sphere with {len(sphere.triangles)} triangles")
    
    formats = [
        (ExportFormat.STL_BINARY, "./examples/sphere.stl"),
        (ExportFormat.STL_ASCII, "./examples/sphere_ascii.stl"),
        (ExportFormat.STEP_AP214, "./examples/sphere.step"),
        (ExportFormat.IGES_5_3, "./examples/sphere.iges"),
    ]
    
    for fmt, path in formats:
        result = export_mesh(sphere, path, fmt, progress_callback=progress_callback)
        print(f"{fmt.value}: {'Success' if result else 'Failed'}")


def run_all_examples():
    """运行所有示例"""
    # 创建输出目录
    Path("./examples").mkdir(parents=True, exist_ok=True)
    
    examples = [
        example_1_basic_stl_export,
        example_2_step_export,
        example_3_iges_export,
        example_4_batch_export,
        example_5_mesh_repair,
        example_6_file_info,
        example_7_advanced_options,
        example_8_sphere_multiple_formats,
    ]
    
    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"Error in {example.__name__}: {e}")
    
    print("\n" + "="*60)
    print("所有示例运行完成!")
    print("="*60)


if __name__ == "__main__":
    run_all_examples()
