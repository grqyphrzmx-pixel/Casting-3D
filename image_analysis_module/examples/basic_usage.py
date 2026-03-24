"""
铸造行业2D到3D转换 - 图像分析模块使用示例

本示例展示如何使用图像分析模块进行基本的图像分析。
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np
from image_analysis_module import (
    ImageAnalyzer, SourceType,
    Point2D, LineSegment, Circle, Arc, Ellipse, Polygon
)
from image_analysis_module.interfaces import Model3DInterface
from image_analysis_module.utils import load_config


def create_test_image():
    """创建测试图像"""
    # 创建空白图像
    image = np.ones((600, 800), dtype=np.uint8) * 255
    
    # 绘制圆（外轮廓）
    cv2.circle(image, (400, 300), 200, 0, 2)
    
    # 绘制内圆（孔）
    cv2.circle(image, (400, 300), 100, 0, 2)
    
    # 绘制矩形特征
    cv2.rectangle(image, (150, 150), (250, 250), 0, 2)
    
    # 绘制另一个矩形
    cv2.rectangle(image, (550, 350), (650, 450), 0, 2)
    
    # 绘制直线
    cv2.line(image, (100, 500), (300, 500), 0, 2)
    
    # 绘制圆弧
    cv2.ellipse(image, (600, 150), (80, 80), 0, 0, 180, 0, 2)
    
    return image


def example_basic_analysis():
    """示例1: 基本图像分析"""
    print("=" * 60)
    print("示例1: 基本图像分析")
    print("=" * 60)
    
    # 创建测试图像
    image = create_test_image()
    
    # 保存测试图像
    cv2.imwrite("/mnt/okcomputer/output/image_analysis_module/examples/test_drawing.png", image)
    print("测试图像已保存: test_drawing.png")
    
    # 创建分析器
    analyzer = ImageAnalyzer()
    
    # 分析图像
    result = analyzer.analyze(image, SourceType.TECHNICAL_DRAWING)
    
    # 输出结果
    print(f"\n分析结果:")
    print(f"  图像尺寸: {result.image_info.width} x {result.image_info.height}")
    print(f"  源类型: {result.image_info.source_type.name}")
    print(f"  轮廓数量: {result.num_contours}")
    print(f"  特征数量: {result.num_features}")
    print(f"  处理时间: {result.metadata.processing_time_seconds:.3f}秒")
    
    # 输出特征详情
    print(f"\n特征详情:")
    for feature in result.features:
        print(f"\n  特征 {feature.id}: {feature.feature_type.name}")
        print(f"    置信度: {feature.confidence:.2f}")
        
        if isinstance(feature.geometry, Circle):
            circle = feature.geometry
            print(f"    圆心: ({circle.center.x:.1f}, {circle.center.y:.1f})")
            print(f"    半径: {circle.radius:.1f}")
            print(f"    直径: {circle.diameter:.1f}")
        
        elif isinstance(feature.geometry, LineSegment):
            line = feature.geometry
            print(f"    起点: ({line.start.x:.1f}, {line.start.y:.1f})")
            print(f"    终点: ({line.end.x:.1f}, {line.end.y:.1f})")
            print(f"    长度: {line.length:.1f}")
            print(f"    角度: {np.degrees(line.angle):.1f}°")
        
        elif isinstance(feature.geometry, Polygon):
            polygon = feature.geometry
            print(f"    顶点数: {polygon.num_vertices}")
            print(f"    面积: {polygon.area:.1f}")
            print(f"    周长: {polygon.perimeter:.1f}")
    
    return result


def example_custom_config():
    """示例2: 使用自定义配置"""
    print("\n" + "=" * 60)
    print("示例2: 使用自定义配置")
    print("=" * 60)
    
    # 加载默认配置
    config = load_config()
    
    # 修改配置
    config.preprocessing.gaussian_sigma = 2.0
    config.edge_detection.canny_low_threshold = 30
    config.edge_detection.canny_high_threshold = 100
    config.contour.min_area = 50
    config.feature.min_confidence = 0.6
    
    print("\n自定义配置:")
    print(f"  高斯滤波 sigma: {config.preprocessing.gaussian_sigma}")
    print(f"  Canny低阈值: {config.edge_detection.canny_low_threshold}")
    print(f"  Canny高阈值: {config.edge_detection.canny_high_threshold}")
    print(f"  最小轮廓面积: {config.contour.min_area}")
    print(f"  最小置信度: {config.feature.min_confidence}")
    
    # 创建分析器
    analyzer = ImageAnalyzer(config)
    
    # 创建测试图像
    image = create_test_image()
    
    # 分析
    result = analyzer.analyze(image, SourceType.TECHNICAL_DRAWING)
    
    print(f"\n分析结果:")
    print(f"  轮廓数量: {result.num_contours}")
    print(f"  特征数量: {result.num_features}")
    
    return result


def example_export_json():
    """示例3: 导出为JSON格式"""
    print("\n" + "=" * 60)
    print("示例3: 导出为JSON格式")
    print("=" * 60)
    
    # 分析图像
    analyzer = ImageAnalyzer()
    image = create_test_image()
    result = analyzer.analyze(image, SourceType.TECHNICAL_DRAWING)
    
    # 导出为JSON
    json_output = result.to_json(indent=2)
    
    # 保存到文件
    output_path = "/mnt/okcomputer/output/image_analysis_module/examples/analysis_result.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(json_output)
    
    print(f"\nJSON输出已保存: {output_path}")
    print(f"\nJSON内容预览 (前1000字符):")
    print(json_output[:1000])
    print("...")
    
    return result


def example_convert_to_3d():
    """示例4: 转换为3D模型"""
    print("\n" + "=" * 60)
    print("示例4: 转换为3D模型")
    print("=" * 60)
    
    # 分析图像
    analyzer = ImageAnalyzer()
    image = create_test_image()
    result = analyzer.analyze(image, SourceType.TECHNICAL_DRAWING)
    
    # 创建3D接口
    interface = Model3DInterface()
    
    # 转换为3D模型
    model = interface.convert_to_3d(result, extrusion_height=25.0)
    
    print(f"\n3D模型信息:")
    print(f"  名称: {model.name}")
    print(f"  特征数量: {len(model.features)}")
    
    print(f"\n3D特征详情:")
    for i, feature in enumerate(model.features):
        print(f"\n  特征 {i+1}:")
        
        if hasattr(feature, 'primitive_type'):
            print(f"    类型: {feature.primitive_type}")
            print(f"    参数: {feature.parameters}")
            print(f"    位置: ({feature.position.x:.1f}, {feature.position.y:.1f}, {feature.position.z:.1f})")
        
        elif hasattr(feature, 'profile'):
            print(f"    类型: extrusion")
            print(f"    拉伸高度: {feature.height}")
            print(f"    轮廓顶点数: {len(feature.profile)}")
    
    # 导出JSON
    json_path = "/mnt/okcomputer/output/image_analysis_module/examples/3d_model.json"
    interface.export_to_json(result, json_path)
    print(f"\n3D模型JSON已保存: {json_path}")
    
    return model


def example_analyze_different_sources():
    """示例5: 分析不同类型的源图像"""
    print("\n" + "=" * 60)
    print("示例5: 分析不同类型的源图像")
    print("=" * 60)
    
    # 创建不同类型的测试图像
    
    # 技术图纸类型
    drawing = np.ones((400, 400), dtype=np.uint8) * 255
    cv2.circle(drawing, (200, 200), 150, 0, 2)
    cv2.rectangle(drawing, (100, 100), (300, 300), 0, 2)
    
    # 照片类型（模拟）
    photo = np.ones((400, 400), dtype=np.uint8) * 200
    cv2.circle(photo, (200, 200), 150, 100, 3)
    # 添加噪声模拟照片
    noise = np.random.normal(0, 10, photo.shape).astype(np.uint8)
    photo = cv2.add(photo, noise)
    
    # 草图类型（模拟）
    sketch = np.ones((400, 400), dtype=np.uint8) * 255
    # 绘制不规则线条模拟手绘
    for i in range(50):
        x1 = np.random.randint(50, 350)
        y1 = np.random.randint(50, 350)
        x2 = x1 + np.random.randint(-50, 50)
        y2 = y1 + np.random.randint(-50, 50)
        cv2.line(sketch, (x1, y1), (x2, y2), 0, 1)
    
    # 分析不同类型
    analyzer = ImageAnalyzer()
    
    for source_type, image, name in [
        (SourceType.TECHNICAL_DRAWING, drawing, "技术图纸"),
        (SourceType.PHOTO, photo, "照片"),
        (SourceType.SKETCH, sketch, "手绘草图")
    ]:
        print(f"\n{name}分析:")
        result = analyzer.analyze(image, source_type)
        print(f"  轮廓数量: {result.num_contours}")
        print(f"  特征数量: {result.num_features}")


def example_batch_processing():
    """示例6: 批量处理"""
    print("\n" + "=" * 60)
    print("示例6: 批量处理")
    print("=" * 60)
    
    # 创建多个测试图像
    images = []
    for i in range(3):
        img = np.ones((300, 300), dtype=np.uint8) * 255
        # 每个图像绘制不同的形状
        if i == 0:
            cv2.circle(img, (150, 150), 100, 0, 2)
        elif i == 1:
            cv2.rectangle(img, (50, 50), (250, 250), 0, 2)
        else:
            cv2.ellipse(img, (150, 150), (100, 60), 0, 0, 360, 0, 2)
        images.append(img)
    
    # 批量分析
    analyzer = ImageAnalyzer()
    results = []
    
    print("\n批量分析结果:")
    for i, image in enumerate(images):
        result = analyzer.analyze(image, SourceType.TECHNICAL_DRAWING)
        results.append(result)
        print(f"  图像 {i+1}: {result.num_features} 个特征")
    
    print(f"\n总计处理了 {len(results)} 张图像")
    
    return results


def main():
    """主函数"""
    print("铸造行业2D到3D转换 - 图像分析模块使用示例")
    print("=" * 60)
    
    try:
        # 运行各个示例
        example_basic_analysis()
        example_custom_config()
        example_export_json()
        example_convert_to_3d()
        example_analyze_different_sources()
        example_batch_processing()
        
        print("\n" + "=" * 60)
        print("所有示例运行完成!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
