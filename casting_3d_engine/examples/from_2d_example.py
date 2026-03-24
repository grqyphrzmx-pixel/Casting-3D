"""
从2D数据构建模型示例

演示如何从图像分析模块的输出构建3D模型
"""

import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)

from casting_3d_engine import (
    Casting3DEngine,
    Point3D, Vector3D, Profile2D
)
from casting_3d_engine.io.input_interface import (
    MockImageAnalysisOutput, ModelBuilderInput
)


def example_from_2d_data():
    """示例：从2D数据构建3D模型"""
    print("=" * 60)
    print("示例：从2D数据构建3D模型")
    print("=" * 60)
    
    # 创建引擎
    engine = Casting3DEngine()
    
    # 使用模拟的图像分析输出
    image_analysis = MockImageAnalysisOutput()
    
    # 转换为建模引擎输入
    builder_input = ModelBuilderInput(image_analysis)
    data = builder_input.get_data()
    
    print(f"基体类型: {data['base_type']}")
    print(f"基体轮廓顶点数: {len(data['base_profile'].vertices)}")
    print(f"特征数量: {len(data['features'])}")
    print(f"深度: {data['depth']} mm")
    print(f"拔模角度: {data['draft_angle']}°")
    
    # 构建3D模型
    shape_id = engine.build_from_2d(data)
    
    if shape_id:
        print(f"\n模型构建成功: {shape_id[:8]}")
        print(f"模型体积: {engine.volume:.2f} mm³")
        print(f"特征数量: {engine.feature_count}")
        
        # 导出
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        engine.export_stl(shape_id, str(output_dir / "from_2d_model.stl"))
        engine.export_step(shape_id, str(output_dir / "from_2d_model.step"))
        
        print(f"\n导出文件:")
        print(f"  STL: {output_dir / 'from_2d_model.stl'}")
        print(f"  STEP: {output_dir / 'from_2d_model.step'}")
    else:
        print("模型构建失败")
    
    return engine


def example_custom_2d_data():
    """示例：使用自定义2D数据"""
    print("\n" + "=" * 60)
    print("示例：使用自定义2D数据")
    print("=" * 60)
    
    engine = Casting3DEngine()
    
    # 创建自定义2D数据
    data = {
        'base_profile': Profile2D(
            vertices=[
                Point3D(0, 0, 0),
                Point3D(120, 0, 0),
                Point3D(120, 90, 0),
                Point3D(60, 100, 0),  # 梯形顶部
                Point3D(0, 90, 0)
            ],
            is_closed=True
        ),
        'features': [
            {
                'type': 'hole',
                'center_x': 30,
                'center_y': 45,
                'diameter': 20,
                'depth': 0
            },
            {
                'type': 'hole',
                'center_x': 90,
                'center_y': 45,
                'diameter': 20,
                'depth': 0
            },
            {
                'type': 'slot',
                'center_x': 60,
                'center_y': 75,
                'width': 8,
                'length': 30,
                'angle': 0,
                'depth': 10
            }
        ],
        'dimensions': {
            'depth': 30.0,
            'draft_angle': 3.0,
            'wall_thickness': 5.0
        },
        'symmetry': {
            'has_symmetry': False
        },
        'base_type': 'extrude'
    }
    
    print(f"自定义数据:")
    print(f"  基体轮廓顶点数: {len(data['base_profile'].vertices)}")
    print(f"  特征数量: {len(data['features'])}")
    print(f"  深度: {data['dimensions']['depth']} mm")
    
    # 构建模型
    shape_id = engine.build_from_2d(data)
    
    if shape_id:
        print(f"\n模型构建成功!")
        print(f"  体积: {engine.volume:.2f} mm³")
        
        # 导出
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        engine.export_stl(shape_id, str(output_dir / "custom_model.stl"))
    
    return engine


def example_casting_part():
    """示例：创建铸造零件"""
    print("\n" + "=" * 60)
    print("示例：创建铸造零件（带拔模斜度）")
    print("=" * 60)
    
    engine = Casting3DEngine()
    
    # 铸造零件数据
    data = {
        'base_profile': Profile2D(
            vertices=[
                Point3D(-50, -40, 0),
                Point3D(50, -40, 0),
                Point3D(50, 40, 0),
                Point3D(-50, 40, 0)
            ],
            is_closed=True
        ),
        'features': [
            # 安装孔
            {'type': 'hole', 'center_x': -35, 'center_y': -25, 'diameter': 12, 'depth': 0},
            {'type': 'hole', 'center_x': 35, 'center_y': -25, 'diameter': 12, 'depth': 0},
            {'type': 'hole', 'center_x': -35, 'center_y': 25, 'diameter': 12, 'depth': 0},
            {'type': 'hole', 'center_x': 35, 'center_y': 25, 'diameter': 12, 'depth': 0},
            # 中心大孔
            {'type': 'hole', 'center_x': 0, 'center_y': 0, 'diameter': 30, 'depth': 0},
        ],
        'dimensions': {
            'depth': 20.0,
            'draft_angle': 2.0,  # 铸造拔模角度
            'wall_thickness': 5.0
        },
        'symmetry': {
            'has_symmetry': True,
            'symmetry_axis': 'both'
        },
        'base_type': 'extrude',
        'draft': {
            'face_ids': ['side_faces'],
            'angle': 2.0,
            'is_inward': True
        }
    }
    
    print("铸造零件参数:")
    print(f"  尺寸: 100x80x20 mm")
    print(f"  拔模角度: {data['dimensions']['draft_angle']}°")
    print(f"  安装孔: 4xØ12")
    print(f"  中心孔: Ø30")
    
    # 构建模型
    shape_id = engine.build_from_2d(data)
    
    if shape_id:
        print(f"\n铸造零件构建成功!")
        print(f"  体积: {engine.volume:.2f} mm³")
        print(f"  质心: {engine.centroid}")
        
        # 导出
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        engine.export_stl(shape_id, str(output_dir / "casting_part.stl"))
        engine.export_step(shape_id, str(output_dir / "casting_part.step"))
    
    return engine


def example_complex_part():
    """示例：创建复杂零件"""
    print("\n" + "=" * 60)
    print("示例：创建复杂零件")
    print("=" * 60)
    
    engine = Casting3DEngine()
    
    # 复杂零件数据
    data = {
        'base_profile': Profile2D(
            vertices=[
                Point3D(0, 0, 0),
                Point3D(150, 0, 0),
                Point3D(150, 100, 0),
                Point3D(100, 100, 0),
                Point3D(100, 80, 0),
                Point3D(50, 80, 0),
                Point3D(50, 100, 0),
                Point3D(0, 100, 0)
            ],
            is_closed=True
        ),
        'features': [
            # 左侧安装孔
            {'type': 'hole', 'center_x': 25, 'center_y': 50, 'diameter': 15, 'depth': 0},
            # 右侧安装孔
            {'type': 'hole', 'center_x': 125, 'center_y': 50, 'diameter': 15, 'depth': 0},
            # 中间凹槽
            {
                'type': 'pocket',
                'profile': Profile2D(
                    vertices=[
                        Point3D(55, 30, 0),
                        Point3D(95, 30, 0),
                        Point3D(95, 70, 0),
                        Point3D(55, 70, 0)
                    ],
                    is_closed=True
                ),
                'depth': 10
            },
            # 凹槽中的小孔
            {'type': 'hole', 'center_x': 75, 'center_y': 50, 'diameter': 8, 'depth': 10},
        ],
        'dimensions': {
            'depth': 25.0,
            'draft_angle': 1.5
        },
        'symmetry': {
            'has_symmetry': True,
            'symmetry_axis': 'y'
        },
        'base_type': 'extrude'
    }
    
    print("复杂零件参数:")
    print(f"  基体尺寸: 150x100x25 mm")
    print(f"  特征数量: {len(data['features'])}")
    
    # 构建模型
    shape_id = engine.build_from_2d(data)
    
    if shape_id:
        print(f"\n复杂零件构建成功!")
        print(f"  体积: {engine.volume:.2f} mm³")
        
        # 获取统计信息
        stats = engine.get_statistics()
        print(f"\n统计信息:")
        print(f"  特征数量: {stats['feature_count']}")
        print(f"  特征分布: {stats['feature_stats']['type_counts']}")
        
        # 导出
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        engine.export_stl(shape_id, str(output_dir / "complex_part.stl"))
    
    return engine


def example_step_by_step():
    """示例：逐步构建模型"""
    print("\n" + "=" * 60)
    print("示例：逐步构建模型")
    print("=" * 60)
    
    engine = Casting3DEngine()
    
    # 开始事务
    engine.begin_transaction("Create Part")
    
    # 步骤1: 创建基体
    print("\n步骤1: 创建基体")
    profile = Profile2D(
        vertices=[
            Point3D(0, 0, 0),
            Point3D(80, 0, 0),
            Point3D(80, 60, 0),
            Point3D(0, 60, 0)
        ],
        is_closed=True
    )
    base_id = engine.create_extrude(profile, depth=20.0, name="Base")
    print(f"  基体ID: {base_id}")
    print(f"  当前体积: {engine.volume:.2f} mm³")
    
    # 步骤2: 添加孔
    print("\n步骤2: 添加安装孔")
    hole1_id = engine.create_hole(
        Point3D(15, 15, 0), diameter=8.0, name="Hole1"
    )
    hole2_id = engine.create_hole(
        Point3D(65, 15, 0), diameter=8.0, name="Hole2"
    )
    hole3_id = engine.create_hole(
        Point3D(15, 45, 0), diameter=8.0, name="Hole3"
    )
    hole4_id = engine.create_hole(
        Point3D(65, 45, 0), diameter=8.0, name="Hole4"
    )
    print(f"  添加了4个孔")
    print(f"  当前体积: {engine.volume:.2f} mm³")
    
    # 步骤3: 添加中心大孔
    print("\n步骤3: 添加中心大孔")
    center_hole_id = engine.create_hole(
        Point3D(40, 30, 0), diameter=20.0, name="CenterHole"
    )
    print(f"  中心孔ID: {center_hole_id}")
    print(f"  当前体积: {engine.volume:.2f} mm³")
    
    # 结束事务
    engine.end_transaction("Create Part")
    
    # 步骤4: 尝试撤销
    print("\n步骤4: 撤销（删除中心孔）")
    engine.undo()
    print(f"  撤销后体积: {engine.volume:.2f} mm³")
    
    # 步骤5: 重做
    print("\n步骤5: 重做（恢复中心孔）")
    engine.redo()
    print(f"  重做后体积: {engine.volume:.2f} mm³")
    
    # 最终导出
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    features = engine.get_all_features()
    if features:
        last_shape_id = features[-1].result_shape_id
        if last_shape_id:
            engine.export_stl(last_shape_id, str(output_dir / "step_by_step.stl"))
            print(f"\n导出: {output_dir / 'step_by_step.stl'}")
    
    return engine


def run_all_examples():
    """运行所有示例"""
    print("\n" + "=" * 70)
    print("铸造3D建模引擎 - 从2D数据构建模型示例")
    print("=" * 70)
    
    examples = [
        ("从2D数据构建", example_from_2d_data),
        ("自定义2D数据", example_custom_2d_data),
        ("铸造零件", example_casting_part),
        ("复杂零件", example_complex_part),
        ("逐步构建", example_step_by_step),
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
