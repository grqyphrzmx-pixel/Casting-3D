"""
基本使用示例

演示如何使用铸造3D建模引擎创建基本模型
"""

import logging
from pathlib import Path

# 设置日志
logging.basicConfig(level=logging.INFO)

from casting_3d_engine import (
    Casting3DEngine,
    Point3D, Vector3D, Plane, Profile2D,
    ExportFormat, ExportOptions
)


def example_create_box():
    """示例：创建立方体"""
    print("=" * 50)
    print("示例：创建立方体")
    print("=" * 50)
    
    # 创建引擎实例
    engine = Casting3DEngine()
    
    # 创建立方体
    box_id = engine.create_box(
        corner=Point3D(0, 0, 0),
        width=100.0,
        depth=80.0,
        height=50.0,
        name="BaseBox"
    )
    
    print(f"立方体特征ID: {box_id}")
    print(f"模型体积: {engine.volume:.2f} mm³")
    
    # 导出
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    engine.export_stl(box_id, str(output_dir / "box.stl"))
    
    return engine


def example_create_extrude():
    """示例：创建拉伸特征"""
    print("\n" + "=" * 50)
    print("示例：创建拉伸特征")
    print("=" * 50)
    
    engine = Casting3DEngine()
    
    # 创建矩形轮廓
    profile = Profile2D(
        vertices=[
            Point3D(0, 0, 0),
            Point3D(100, 0, 0),
            Point3D(100, 60, 0),
            Point3D(0, 60, 0)
        ],
        is_closed=True
    )
    
    # 创建拉伸特征
    extrude_id = engine.create_extrude(
        profile=profile,
        depth=30.0,
        taper_angle=2.0,  # 2度拔模角
        name="ExtrudedBody"
    )
    
    print(f"拉伸特征ID: {extrude_id}")
    print(f"模型体积: {engine.volume:.2f} mm³")
    
    return engine


def example_create_revolve():
    """示例：创建旋转特征"""
    print("\n" + "=" * 50)
    print("示例：创建旋转特征")
    print("=" * 50)
    
    engine = Casting3DEngine()
    
    # 创建旋转轮廓（半截面）
    profile = Profile2D(
        vertices=[
            Point3D(0, 0, 0),
            Point3D(50, 0, 0),
            Point3D(50, 30, 0),
            Point3D(30, 30, 0),
            Point3D(30, 60, 0),
            Point3D(0, 60, 0)
        ],
        is_closed=True
    )
    
    # 创建旋转特征
    revolve_id = engine.create_revolve(
        profile=profile,
        angle=360.0,
        axis_origin=Point3D(0, 0, 0),
        axis_direction=Vector3D(0, 1, 0),
        name="RevolvedBody"
    )
    
    print(f"旋转特征ID: {revolve_id}")
    print(f"模型体积: {engine.volume:.2f} mm³")
    
    return engine


def example_create_holes():
    """示例：创建孔特征"""
    print("\n" + "=" * 50)
    print("示例：创建孔特征")
    print("=" * 50)
    
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
    
    base_id = engine.create_extrude(profile, depth=25.0, name="BasePlate")
    print(f"基体特征ID: {base_id}")
    
    # 创建孔
    hole_positions = [
        Point3D(20, 20, 0),
        Point3D(80, 20, 0),
        Point3D(20, 60, 0),
        Point3D(80, 60, 0)
    ]
    
    for i, pos in enumerate(hole_positions):
        hole_id = engine.create_hole(
            center=pos,
            diameter=10.0,
            depth=0,  # 通孔
            name=f"Hole_{i+1}"
        )
        print(f"  孔{i+1}特征ID: {hole_id}")
    
    print(f"最终模型体积: {engine.volume:.2f} mm³")
    
    return engine


def example_undo_redo():
    """示例：撤销/重做"""
    print("\n" + "=" * 50)
    print("示例：撤销/重做")
    print("=" * 50)
    
    engine = Casting3DEngine()
    
    # 创建特征
    profile1 = Profile2D(
        vertices=[
            Point3D(0, 0, 0),
            Point3D(50, 0, 0),
            Point3D(50, 50, 0),
            Point3D(0, 50, 0)
        ],
        is_closed=True
    )
    
    id1 = engine.create_extrude(profile1, depth=10.0, name="Feature1")
    print(f"创建特征1: {id1}")
    print(f"  特征数量: {engine.feature_count}")
    
    profile2 = Profile2D(
        vertices=[
            Point3D(10, 10, 0),
            Point3D(40, 10, 0),
            Point3D(40, 40, 0),
            Point3D(10, 40, 0)
        ],
        is_closed=True
    )
    
    id2 = engine.create_extrude(profile2, depth=5.0, name="Feature2")
    print(f"创建特征2: {id2}")
    print(f"  特征数量: {engine.feature_count}")
    
    # 撤销
    print("\n执行撤销...")
    engine.undo()
    print(f"  特征数量: {engine.feature_count}")
    
    # 再次撤销
    print("再次撤销...")
    engine.undo()
    print(f"  特征数量: {engine.feature_count}")
    
    # 重做
    print("\n执行重做...")
    engine.redo()
    print(f"  特征数量: {engine.feature_count}")
    
    # 查看命令历史
    print(f"\n命令历史: {engine.get_command_history()}")
    
    return engine


def example_export_formats():
    """示例：导出多种格式"""
    print("\n" + "=" * 50)
    print("示例：导出多种格式")
    print("=" * 50)
    
    engine = Casting3DEngine()
    
    # 创建简单模型
    profile = Profile2D(
        vertices=[
            Point3D(0, 0, 0),
            Point3D(50, 0, 0),
            Point3D(50, 40, 0),
            Point3D(0, 40, 0)
        ],
        is_closed=True
    )
    
    shape_id = engine.create_extrude(profile, depth=20.0)
    
    # 导出目录
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # 导出各种格式
    exports = [
        ("model.stl", "STL"),
        ("model.step", "STEP"),
        ("model.iges", "IGES"),
    ]
    
    for filename, format_name in exports:
        filepath = output_dir / filename
        if format_name == "STL":
            success = engine.export_stl(shape_id, str(filepath))
        elif format_name == "STEP":
            success = engine.export_step(shape_id, str(filepath))
        elif format_name == "IGES":
            success = engine.export_iges(shape_id, str(filepath))
        else:
            success = False
        
        status = "✓" if success else "✗"
        print(f"  {status} {format_name}: {filepath}")
    
    return engine


def example_save_load():
    """示例：保存和加载模型"""
    print("\n" + "=" * 50)
    print("示例：保存和加载模型")
    print("=" * 50)
    
    # 创建并保存模型
    engine1 = Casting3DEngine()
    
    profile = Profile2D(
        vertices=[
            Point3D(0, 0, 0),
            Point3D(60, 0, 0),
            Point3D(60, 40, 0),
            Point3D(0, 40, 0)
        ],
        is_closed=True
    )
    
    engine1.create_extrude(profile, depth=15.0, name="Base")
    engine1.create_hole(Point3D(30, 20, 0), diameter=10.0, name="CenterHole")
    
    print(f"原始模型特征数: {engine1.feature_count}")
    
    # 保存
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    save_path = output_dir / "model.json"
    
    success = engine1.save(str(save_path))
    print(f"保存模型: {'✓' if success else '✗'} {save_path}")
    
    # 加载模型
    engine2 = Casting3DEngine()
    success = engine2.load(str(save_path))
    print(f"加载模型: {'✓' if success else '✗'}")
    print(f"加载后特征数: {engine2.feature_count}")
    
    return engine1, engine2


def example_parameter_system():
    """示例：参数系统"""
    print("\n" + "=" * 50)
    print("示例：参数系统")
    print("=" * 50)
    
    engine = Casting3DEngine()
    
    # 设置参数
    engine.set_parameter("width", 100.0)
    engine.set_parameter("height", 80.0)
    engine.set_parameter("depth", 25.0)
    engine.set_parameter("hole_diameter", 15.0)
    
    # 使用参数创建模型
    w = engine.get_parameter("width")
    h = engine.get_parameter("height")
    d = engine.get_parameter("depth")
    
    profile = Profile2D(
        vertices=[
            Point3D(0, 0, 0),
            Point3D(w, 0, 0),
            Point3D(w, h, 0),
            Point3D(0, h, 0)
        ],
        is_closed=True
    )
    
    shape_id = engine.create_extrude(profile, depth=d, name="ParametricBody")
    
    # 创建孔
    hole_d = engine.get_parameter("hole_diameter")
    engine.create_hole(
        Point3D(w/2, h/2, 0),
        diameter=hole_d,
        name="ParametricHole"
    )
    
    print(f"参数化模型体积: {engine.volume:.2f} mm³")
    
    return engine


def run_all_examples():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("铸造3D建模引擎 - 使用示例")
    print("=" * 60)
    
    try:
        example_create_box()
    except Exception as e:
        print(f"创建立方体示例失败: {e}")
    
    try:
        example_create_extrude()
    except Exception as e:
        print(f"创建拉伸特征示例失败: {e}")
    
    try:
        example_create_revolve()
    except Exception as e:
        print(f"创建旋转特征示例失败: {e}")
    
    try:
        example_create_holes()
    except Exception as e:
        print(f"创建孔特征示例失败: {e}")
    
    try:
        example_undo_redo()
    except Exception as e:
        print(f"撤销/重做示例失败: {e}")
    
    try:
        example_export_formats()
    except Exception as e:
        print(f"导出格式示例失败: {e}")
    
    try:
        example_save_load()
    except Exception as e:
        print(f"保存/加载示例失败: {e}")
    
    try:
        example_parameter_system()
    except Exception as e:
        print(f"参数系统示例失败: {e}")
    
    print("\n" + "=" * 60)
    print("所有示例运行完成")
    print("=" * 60)


if __name__ == "__main__":
    run_all_examples()
