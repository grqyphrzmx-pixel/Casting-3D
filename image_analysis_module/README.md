# 铸造行业2D到3D转换 - 图像分析模块

## 概述

本模块是铸造行业2D到3D转换应用的核心组件，负责从铸造零件的2D图纸或照片中提取关键几何特征，为3D重建提供结构化的数据基础。

## 功能特性

### 图像预处理
- 多种去噪算法（高斯、中值、双边滤波）
- 对比度增强（CLAHE、伽马校正）
- 自适应二值化（Otsu、自适应阈值）
- 形态学操作（开运算、闭运算）

### 边缘检测与轮廓提取
- Canny边缘检测（默认）
- Sobel、Laplacian边缘检测
- 轮廓查找与层级分析
- 轮廓筛选与多边形近似

### 形状识别
- 直线识别（最小二乘法拟合）
- 圆识别（圆度分析 + 最小二乘拟合）
- 圆弧识别（角度跨度分析）
- 椭圆识别（OpenCV拟合）
- 多边形识别（顶点分析）

### 3D建模接口
- JSON格式数据交换
- STEP/IGES/STL导出（需3D建模引擎）
- 特征集合管理

## 安装

### 依赖项

```bash
pip install opencv-python numpy scipy scikit-image pyyaml
```

### 可选依赖

```bash
# 用于3D建模导出
pip install FreeCAD-python  # 或根据实际安装方式
```

## 快速开始

### 基本使用

```python
from image_analysis_module import ImageAnalyzer, SourceType

# 创建分析器
analyzer = ImageAnalyzer()

# 分析图像文件
result = analyzer.analyze_file("casting_drawing.png", SourceType.TECHNICAL_DRAWING)

# 查看结果
print(f"Found {result.num_contours} contours")
print(f"Found {result.num_features} geometric features")

# 导出为JSON
json_output = result.to_json()
print(json_output)
```

### 使用自定义配置

```python
from image_analysis_module import ImageAnalyzer, AnalyzerConfig
from image_analysis_module.utils import load_config

# 加载自定义配置
config = load_config("custom_config.yaml")

# 创建分析器
analyzer = ImageAnalyzer(config)

# 分析图像
result = analyzer.analyze_file("drawing.png")
```

### 特征提取与3D转换

```python
from image_analysis_module import ImageAnalyzer, SourceType
from image_analysis_module.interfaces import Model3DInterface

# 分析图像
analyzer = ImageAnalyzer()
result = analyzer.analyze_file("part_drawing.png", SourceType.TECHNICAL_DRAWING)

# 转换为3D模型
interface = Model3DInterface()
model = interface.convert_to_3d(result, extrusion_height=20.0)

# 导出为JSON
json_str = interface.export_to_json(result, "output.json")
```

## 模块结构

```
image_analysis_module/
├── __init__.py              # 包入口
├── README.md                # 本文档
├── TECHNICAL_DESIGN.md      # 技术设计文档
│
├── core/                    # 核心模块
│   ├── __init__.py
│   ├── data_structures.py   # 数据结构定义
│   └── image_analyzer.py    # 主分析器
│
├── algorithms/              # 算法模块
│   ├── __init__.py
│   └── shape_recognition.py # 形状识别算法
│
├── interfaces/              # 接口模块
│   ├── __init__.py
│   └── model3d_interface.py # 3D建模引擎接口
│
├── utils/                   # 工具模块
│   ├── __init__.py
│   ├── config_loader.py     # 配置加载
│   └── geometry_utils.py    # 几何计算工具
│
└── config/                  # 配置目录
    └── default_config.yaml  # 默认配置
```

## 配置说明

### 默认配置

模块提供默认配置文件 `config/default_config.yaml`，包含所有可配置参数。

### 配置项说明

#### 预处理配置
```yaml
preprocessing:
  denoise_method: "gaussian"      # 去噪方法
  gaussian_sigma: 1.5             # 高斯滤波sigma
  contrast_method: "clahe"        # 对比度增强方法
  binarization_method: "otsu"     # 二值化方法
  morphology_enabled: true        # 是否启用形态学操作
```

#### 边缘检测配置
```yaml
edge_detection:
  method: "canny"                 # 边缘检测方法
  canny_low_threshold: 50         # Canny低阈值
  canny_high_threshold: 150       # Canny高阈值
```

#### 轮廓分析配置
```yaml
contour:
  retrieval_mode: "tree"          # 轮廓检索模式
  min_area: 100.0                 # 最小面积
  min_perimeter: 50.0             # 最小周长
```

#### 特征提取配置
```yaml
feature:
  min_confidence: 0.7             # 最小置信度
  circle_circularity_threshold: 0.85  # 圆度阈值
```

## API参考

### ImageAnalyzer

主分析器类，协调整个图像分析流程。

```python
class ImageAnalyzer:
    def __init__(self, config: AnalyzerConfig = None)
    def analyze(self, image: np.ndarray, source_type: SourceType) -> AnalysisResult
    def analyze_file(self, filepath: str, source_type: SourceType = None) -> AnalysisResult
```

### AnalysisResult

分析结果类，包含所有提取的信息。

```python
class AnalysisResult:
    image_info: ImageInfo           # 图像信息
    contours: List[Contour]         # 轮廓列表
    features: List[GeometricFeature]  # 特征列表
    dimensions: List[Dimension]     # 尺寸列表
    constraints: List[Constraint]   # 约束列表
    scale_factor: float             # 像素到毫米比例
    
    def to_json(self) -> str        # 导出为JSON
    def to_dict(self) -> Dict       # 导出为字典
```

### GeometricFeature

几何特征类，表示提取的几何形状。

```python
class GeometricFeature:
    id: int                         # 特征ID
    feature_type: FeatureType       # 特征类型
    geometry: GeometryType          # 几何数据
    confidence: float               # 置信度
    
    def to_dict(self) -> Dict       # 导出为字典
```

## 数据结构

### 基础几何类型

- `Point2D`: 二维点 (x, y)
- `LineSegment`: 线段 (start, end)
- `Circle`: 圆 (center, radius)
- `Arc`: 圆弧 (center, radius, start_angle, end_angle)
- `Ellipse`: 椭圆 (center, major_axis, minor_axis, rotation)
- `Polygon`: 多边形 (vertices)

### 枚举类型

- `SourceType`: 输入源类型 (TECHNICAL_DRAWING, PHOTO, SKETCH)
- `FeatureType`: 特征类型 (LINE, CIRCLE, ARC, ELLIPSE, POLYGON)
- `ShapeType`: 形状类型
- `DimensionType`: 尺寸类型
- `ConstraintType`: 约束类型

## 算法说明

### 形状识别算法

#### 直线识别
- 使用SVD分析点集主方向
- 计算点到拟合直线的距离
- 根据距离偏差计算置信度

#### 圆识别
- 计算轮廓圆度（紧凑度）
- 使用最小二乘法拟合圆
- 根据拟合误差计算置信度

#### 圆弧识别
- 基于圆拟合结果
- 分析点的角度分布
- 检查角度跨度

#### 多边形识别
- Douglas-Peucker算法近似
- 顶点数分析
- 角度检查（矩形识别）

## 扩展开发

### 添加新的形状识别器

```python
from image_analysis_module.algorithms import ShapeRecognizer, RecognitionResult
from image_analysis_module.core import Contour, ShapeType

class MyShapeRecognizer(ShapeRecognizer):
    def recognize(self, contour: Contour) -> Optional[RecognitionResult]:
        # 实现识别逻辑
        pass
    
    def get_confidence_threshold(self) -> float:
        return 0.7
```

### 添加新的预处理步骤

```python
class MyPreprocessingStep:
    def apply(self, image: np.ndarray, source_type: SourceType) -> np.ndarray:
        # 实现处理逻辑
        return processed_image
```

## 调试与日志

### 启用调试模式

```python
from image_analysis_module.utils import load_config

config = load_config()
config.debug.enabled = True
config.debug.visualize_intermediate = True

analyzer = ImageAnalyzer(config)
```

### 日志输出

日志文件默认保存在 `image_analysis.log`，包含详细的处理步骤和结果信息。

## 性能优化

### 多线程处理
```yaml
performance:
  multithreading: true
  max_threads: 4
```

### GPU加速
```yaml
performance:
  gpu_acceleration: true
```

### 图像金字塔
```yaml
performance:
  pyramid_levels: 2
```

## 测试

### 运行单元测试

```bash
python -m pytest tests/
```

### 测试示例

```python
# 创建测试图像
import cv2
import numpy as np

test_image = np.zeros((400, 400), dtype=np.uint8)
cv2.circle(test_image, (200, 200), 100, 255, 2)
cv2.rectangle(test_image, (50, 50), (150, 150), 255, 2)

# 分析
analyzer = ImageAnalyzer()
result = analyzer.analyze(test_image, SourceType.TECHNICAL_DRAWING)

# 验证结果
assert result.num_features >= 2
```

## 常见问题

### Q: 如何处理低质量图像？
A: 调整预处理参数，增加去噪强度，使用CLAHE增强对比度。

### Q: 如何提高圆识别精度？
A: 降低 `circle_circularity_threshold`，或增加图像分辨率。

### Q: 如何导出到STEP格式？
A: 需要安装FreeCAD或其他3D建模引擎，实现 `Model3DEngineInterface` 接口。

### Q: 如何处理大尺寸图像？
A: 设置 `performance.max_image_size` 自动缩放，或使用图像金字塔。

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 创建 Pull Request

## 许可证

MIT License

## 联系方式

- 项目主页: [待添加]
- 问题反馈: [待添加]
- 文档: [待添加]

## 版本历史

### v1.0.0 (2024-01)
- 初始版本发布
- 基础图像预处理功能
- 形状识别算法（直线、圆、圆弧、椭圆、多边形）
- 3D建模引擎接口
- JSON数据交换格式
