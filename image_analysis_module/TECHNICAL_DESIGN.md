# 铸造行业2D到3D转换 - 图像分析模块技术设计方案

## 1. 模块概述

### 1.1 设计目标
本模块负责从铸造零件的2D图纸或照片中提取关键几何特征，为3D重建提供结构化的数据基础。

### 1.2 输入输出
- **输入**: 技术图纸(CAD导出/扫描)、零件照片、手绘草图
- **输出**: 结构化几何特征数据（点、线、圆弧、多边形、轮廓）

### 1.3 技术栈
- Python 3.8+
- OpenCV 4.x
- NumPy
- SciPy
- scikit-image

---

## 2. 算法设计

### 2.1 图像预处理流程

```
输入图像
    ↓
[图像类型检测] → 技术图纸/照片/草图
    ↓
[灰度转换] (彩色→灰度)
    ↓
[去噪处理]
    ├── 高斯滤波 (σ=1.0-2.0)
    ├── 中值滤波 (核大小3x3或5x5)
    └── 双边滤波 (保留边缘)
    ↓
[对比度增强]
    ├── CLAHE (自适应直方图均衡)
    └── 伽马校正
    ↓
[二值化]
    ├── Otsu自动阈值
    ├── 自适应阈值
    └── 多阈值分割(草图)
    ↓
[形态学操作]
    ├── 开运算 (去噪点)
    ├── 闭运算 (填补小孔)
    └── 骨架提取(草图)
    ↓
预处理完成图像
```

### 2.2 边缘检测和轮廓提取

#### 2.2.1 边缘检测算法选择

| 算法 | 适用场景 | 优点 | 缺点 |
|------|----------|------|------|
| Canny | 技术图纸 | 精度高，噪声抑制好 | 参数敏感 |
| Sobel | 快速预览 | 计算快 | 边缘较粗 |
| Laplacian | 细节增强 | 各向同性 | 噪声敏感 |
| 自定义(图纸专用) | 工程图纸 | 针对线条优化 | 通用性差 |

**推荐方案**: 技术图纸使用Canny + 霍夫变换，照片使用自适应Canny

#### 2.2.2 轮廓提取流程

```
边缘图像
    ↓
[轮廓查找] (cv2.findContours)
    ├── RETR_EXTERNAL (仅外层)
    ├── RETR_LIST (所有轮廓)
    └── RETR_TREE (层级结构)
    ↓
[轮廓筛选]
    ├── 面积阈值过滤
    ├── 周长阈值过滤
    └── 形状复杂度过滤
    ↓
[轮廓近似]
    ├── Douglas-Peucker算法
    └── 多边形逼近
    ↓
[轮廓分类]
    ├── 封闭轮廓
    ├── 开放轮廓
    └── 嵌套轮廓(孔洞)
```

### 2.3 形状识别和特征分类

#### 2.3.1 基本几何形状识别

```python
形状识别决策树:
轮廓
    ↓
[判断封闭性]
    ├── 开放 → 线段/曲线
    └── 封闭 → 继续分类
        ↓
    [顶点数分析]
        ├── 3顶点 → 三角形
        ├── 4顶点 → 四边形(矩形/平行四边形/梯形)
        ├── >4顶点 → 多边形/圆
        └── 0顶点 → 圆/椭圆/自由曲线
```

#### 2.3.2 圆和圆弧检测

- **霍夫圆变换**: 检测完整圆
- **三点定圆**: 从轮廓点拟合圆
- **圆弧检测**: 基于曲率变化识别圆弧段

#### 2.3.3 直线和角度检测

- **霍夫直线变换**: 检测图像中所有直线
- **RANSAC直线拟合**: 鲁棒性直线检测
- **角度计算**: 基于直线斜率计算夹角

### 2.4 尺寸标识别和提取

#### 2.4.1 尺寸标注检测

```
[文字区域检测] (OCR预处理)
    ↓
[尺寸线识别]
    ├── 双箭头线
    ├── 延伸线
    └── 标注文字
    ↓
[尺寸关联]
    ├── 最近几何特征匹配
    └── 约束关系建立
```

#### 2.4.2 比例因子计算

- 从已知尺寸标注计算像素-毫米比例
- 多尺寸交叉验证
- 置信度评估

---

## 3. 数据结构设计

### 3.1 基础几何类型

```python
# 点
class Point2D:
    x: float
    y: float
    confidence: float

# 线段
class LineSegment:
    start: Point2D
    end: Point2D
    length: float
    angle: float

# 圆弧
class Arc:
    center: Point2D
    radius: float
    start_angle: float
    end_angle: float

# 圆
class Circle:
    center: Point2D
    radius: float
```

### 3.2 轮廓数据结构

```python
class Contour:
    id: int
    points: List[Point2D]
    is_closed: bool
    area: float
    perimeter: float
    parent_id: int  # 层级关系
    children_ids: List[int]
    shape_type: ShapeType
    approx_points: List[Point2D]  # 多边形近似
    bounding_box: BoundingBox
    confidence: float
```

### 3.3 特征数据结构

```python
class GeometricFeature:
    id: int
    feature_type: FeatureType  # LINE, ARC, CIRCLE, POLYGON, etc.
    geometry: Union[LineSegment, Arc, Circle, Polygon]
    source_contour_id: int
    metadata: FeatureMetadata
    confidence: float

class FeatureMetadata:
    detection_method: str
    processing_params: Dict
    timestamp: datetime
    quality_score: float
```

### 3.4 尺寸和约束数据结构

```python
class Dimension:
    id: int
    dimension_type: DimensionType  # LINEAR, ANGULAR, RADIUS, DIAMETER
    value: float
    unit: str
    text_position: Point2D
    associated_features: List[int]
    confidence: float

class Constraint:
    id: int
    constraint_type: ConstraintType  # PARALLEL, PERPENDICULAR, TANGENT, etc.
    feature_ids: List[int]
    parameters: Dict
    confidence: float
```

### 3.5 分析结果数据结构

```python
class AnalysisResult:
    image_info: ImageInfo
    preprocessing_params: PreprocessingParams
    contours: List[Contour]
    features: List[GeometricFeature]
    dimensions: List[Dimension]
    constraints: List[Constraint]
    scale_factor: float
    metadata: AnalysisMetadata

class ImageInfo:
    width: int
    height: int
    source_type: SourceType  # TECHNICAL_DRAWING, PHOTO, SKETCH
    original_path: str
```

---

## 4. 代码架构设计

### 4.1 模块结构

```
image_analysis_module/
├── core/
│   ├── __init__.py
│   ├── image_analyzer.py      # 主分析器类
│   ├── feature_extractor.py   # 特征提取器
│   └── result_builder.py      # 结果构建器
├── algorithms/
│   ├── __init__.py
│   ├── preprocessing.py       # 预处理算法
│   ├── edge_detection.py      # 边缘检测
│   ├── contour_analysis.py    # 轮廓分析
│   ├── shape_recognition.py   # 形状识别
│   └── dimension_extraction.py # 尺寸提取
├── utils/
│   ├── __init__.py
│   ├── geometry_utils.py      # 几何计算工具
│   ├── image_utils.py         # 图像处理工具
│   └── validators.py          # 数据验证
├── interfaces/
│   ├── __init__.py
│   └── model3d_interface.py   # 3D建模引擎接口
├── config/
│   ├── __init__.py
│   └── default_config.yaml    # 默认配置
└── tests/
    └── ...
```

### 4.2 核心类设计

#### 4.2.1 图像分析器 (ImageAnalyzer)

```python
class ImageAnalyzer:
    """主分析器类，协调整个分析流程"""
    
    def __init__(self, config: AnalyzerConfig):
        self.config = config
        self.preprocessor = ImagePreprocessor(config.preprocessing)
        self.edge_detector = EdgeDetector(config.edge_detection)
        self.contour_analyzer = ContourAnalyzer(config.contour)
        self.feature_extractor = FeatureExtractor(config.feature)
        self.dimension_extractor = DimensionExtractor(config.dimension)
    
    def analyze(self, image: np.ndarray, 
                source_type: SourceType) -> AnalysisResult:
        """执行完整的图像分析"""
        # 1. 预处理
        processed = self.preprocessor.process(image, source_type)
        
        # 2. 边缘检测
        edges = self.edge_detector.detect(processed)
        
        # 3. 轮廓分析
        contours = self.contour_analyzer.analyze(edges)
        
        # 4. 特征提取
        features = self.feature_extractor.extract(contours)
        
        # 5. 尺寸提取
        dimensions = self.dimension_extractor.extract(image, features)
        
        # 6. 构建结果
        return self._build_result(image, contours, features, dimensions)
```

#### 4.2.2 图像预处理器 (ImagePreprocessor)

```python
class ImagePreprocessor:
    """图像预处理模块"""
    
    def __init__(self, config: PreprocessingConfig):
        self.config = config
        self.pipeline = self._build_pipeline()
    
    def _build_pipeline(self) -> List[ProcessingStep]:
        """构建处理管道"""
        return [
            GrayscaleConversion(),
            NoiseReduction(self.config.denoise),
            ContrastEnhancement(self.config.contrast),
            Binarization(self.config.binarization),
            MorphologicalOperations(self.config.morphology)
        ]
    
    def process(self, image: np.ndarray, 
                source_type: SourceType) -> np.ndarray:
        """执行预处理流程"""
        result = image.copy()
        for step in self.pipeline:
            result = step.apply(result, source_type)
        return result
```

#### 4.2.3 特征提取器 (FeatureExtractor)

```python
class FeatureExtractor:
    """几何特征提取器"""
    
    def __init__(self, config: FeatureConfig):
        self.config = config
        self.shape_recognizers = {
            ShapeType.LINE: LineRecognizer(),
            ShapeType.CIRCLE: CircleRecognizer(),
            ShapeType.ARC: ArcRecognizer(),
            ShapeType.POLYGON: PolygonRecognizer(),
            ShapeType.ELLIPSE: EllipseRecognizer()
        }
    
    def extract(self, contours: List[Contour]) -> List[GeometricFeature]:
        """从轮廓中提取几何特征"""
        features = []
        for contour in contours:
            feature = self._recognize_feature(contour)
            if feature:
                features.append(feature)
        return features
    
    def _recognize_feature(self, contour: Contour) -> Optional[GeometricFeature]:
        """识别单个轮廓的几何类型"""
        # 使用多种识别器，选择置信度最高的结果
        candidates = []
        for shape_type, recognizer in self.shape_recognizers.items():
            result = recognizer.recognize(contour)
            if result and result.confidence > self.config.min_confidence:
                candidates.append(result)
        
        return max(candidates, key=lambda x: x.confidence) if candidates else None
```

### 4.3 算法接口设计

```python
# 所有算法实现统一的接口

class AlgorithmInterface(ABC):
    """算法接口基类"""
    
    @abstractmethod
    def configure(self, params: Dict) -> None:
        """配置算法参数"""
        pass
    
    @abstractmethod
    def process(self, input_data: Any) -> Any:
        """执行算法处理"""
        pass
    
    @abstractmethod
    def get_metadata(self) -> Dict:
        """获取算法元数据"""
        pass

class PreprocessingAlgorithm(AlgorithmInterface):
    """预处理算法接口"""
    pass

class EdgeDetectionAlgorithm(AlgorithmInterface):
    """边缘检测算法接口"""
    pass

class ShapeRecognitionAlgorithm(AlgorithmInterface):
    """形状识别算法接口"""
    pass
```

---

## 5. 与3D建模引擎的接口

### 5.1 数据交换格式

```python
class Model3DInterface:
    """与3D建模引擎的数据交换接口"""
    
    def export_to_json(self, result: AnalysisResult) -> str:
        """导出为JSON格式"""
        data = {
            "version": "1.0",
            "features": self._serialize_features(result.features),
            "dimensions": self._serialize_dimensions(result.dimensions),
            "constraints": self._serialize_constraints(result.constraints),
            "scale_factor": result.scale_factor
        }
        return json.dumps(data, indent=2)
    
    def export_to_step(self, result: AnalysisResult, 
                       filepath: str) -> bool:
        """导出为STEP格式（通过外部库）"""
        # 调用OCC或FreeCAD接口
        pass
    
    def get_feature_collection(self, result: AnalysisResult) -> FeatureCollection:
        """获取特征集合对象"""
        return FeatureCollection(
            features=result.features,
            dimensions=result.dimensions,
            constraints=result.constraints
        )
```

### 5.2 数据序列化格式

```json
{
  "version": "1.0",
  "image_info": {
    "width": 1024,
    "height": 768,
    "source_type": "technical_drawing"
  },
  "features": [
    {
      "id": 1,
      "type": "circle",
      "geometry": {
        "center": {"x": 100.5, "y": 200.3},
        "radius": 50.0
      },
      "confidence": 0.95
    },
    {
      "id": 2,
      "type": "line",
      "geometry": {
        "start": {"x": 0, "y": 0},
        "end": {"x": 100, "y": 0}
      },
      "confidence": 0.98
    }
  ],
  "dimensions": [
    {
      "id": 1,
      "type": "diameter",
      "value": 100.0,
      "unit": "mm",
      "associated_features": [1]
    }
  ],
  "scale_factor": 0.5,
  "metadata": {
    "processing_time": 1.5,
    "algorithm_version": "1.0.0"
  }
}
```

---

## 6. 维护性设计

### 6.1 模块化设计

- **算法插件化**: 每种算法实现独立接口，便于替换
- **配置外部化**: 所有参数通过配置文件管理
- **管道可配置**: 预处理流程可动态调整

### 6.2 配置管理

```yaml
# default_config.yaml
version: "1.0"

preprocessing:
  denoise:
    method: "gaussian"
    sigma: 1.5
  contrast:
    method: "clahe"
    clip_limit: 2.0
  binarization:
    method: "otsu"
  morphology:
    operations:
      - type: "open"
        kernel_size: 3

edge_detection:
  method: "canny"
  low_threshold: 50
  high_threshold: 150
  aperture_size: 3

contour:
  retrieval_mode: "tree"
  approximation_method: "simple"
  min_area: 100
  min_perimeter: 50

feature:
  min_confidence: 0.7
  shape_recognizers:
    - "line"
    - "circle"
    - "arc"
    - "polygon"

dimension:
  ocr_enabled: true
  min_text_height: 10
```

### 6.3 日志和调试

```python
import logging

class AnalysisLogger:
    """分析过程日志记录器"""
    
    def __init__(self, name: str = "image_analyzer"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # 文件处理器
        fh = logging.FileHandler("analysis.log")
        fh.setLevel(logging.DEBUG)
        
        # 控制台处理器
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # 格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
    
    def log_step(self, step_name: str, params: Dict):
        """记录处理步骤"""
        self.logger.debug(f"Step: {step_name}, Params: {params}")
    
    def log_result(self, step_name: str, result_summary: Dict):
        """记录处理结果"""
        self.logger.info(f"Step: {step_name}, Result: {result_summary}")
    
    def log_error(self, step_name: str, error: Exception):
        """记录错误"""
        self.logger.error(f"Step: {step_name}, Error: {str(error)}")
```

### 6.4 调试可视化

```python
class DebugVisualizer:
    """调试可视化工具"""
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.visualizations = []
    
    def show_preprocessing(self, original: np.ndarray, 
                          processed: np.ndarray):
        """显示预处理结果"""
        if not self.enabled:
            return
        # 创建对比图
        fig, axes = plt.subplots(1, 2, figsize=(12, 6))
        axes[0].imshow(original, cmap='gray')
        axes[0].set_title('Original')
        axes[1].imshow(processed, cmap='gray')
        axes[1].set_title('Processed')
        self.visualizations.append(fig)
    
    def show_contours(self, image: np.ndarray, 
                     contours: List[Contour]):
        """显示检测到的轮廓"""
        if not self.enabled:
            return
        # 绘制轮廓
        result = cv2.drawContours(
            image.copy(), 
            [c.points for c in contours], 
            -1, (0, 255, 0), 2
        )
        self._save_visualization(result, "contours")
    
    def show_features(self, image: np.ndarray, 
                     features: List[GeometricFeature]):
        """显示提取的特征"""
        if not self.enabled:
            return
        # 绘制不同类型的特征
        result = image.copy()
        for feature in features:
            self._draw_feature(result, feature)
        self._save_visualization(result, "features")
```

---

## 7. 性能优化

### 7.1 计算优化

- **多线程处理**: 独立轮廓并行分析
- **GPU加速**: OpenCV CUDA支持
- **图像金字塔**: 多尺度处理

### 7.2 内存优化

- **流式处理**: 大图像分块处理
- **延迟加载**: 按需加载图像数据

---

## 8. 错误处理

```python
class AnalysisError(Exception):
    """分析错误基类"""
    pass

class PreprocessingError(AnalysisError):
    """预处理错误"""
    pass

class FeatureExtractionError(AnalysisError):
    """特征提取错误"""
    pass

class ErrorHandler:
    """错误处理器"""
    
    def handle(self, error: Exception, 
               context: Dict) -> AnalysisResult:
        """处理错误并返回部分结果"""
        if isinstance(error, PreprocessingError):
            # 尝试使用备用预处理方法
            return self._fallback_preprocess(context)
        elif isinstance(error, FeatureExtractionError):
            # 返回已提取的特征
            return self._partial_result(context)
        else:
            # 记录错误并抛出
            raise error
```

---

## 9. 测试策略

### 9.1 单元测试

- 每个算法类独立测试
- 使用合成图像验证
- 边界条件测试

### 9.2 集成测试

- 完整流程测试
- 多种输入类型测试
- 性能基准测试

### 9.3 回归测试

- 标准测试图像集
- 结果对比验证

---

## 10. 扩展性设计

### 10.1 添加新算法

1. 实现对应的算法接口
2. 在配置中注册
3. 更新算法工厂

### 10.2 添加新特征类型

1. 定义新的几何类型
2. 实现对应的识别器
3. 更新序列化器

### 10.3 添加新输入类型

1. 实现专用的预处理器
2. 配置输入类型检测
3. 更新处理管道

---

## 附录A: 依赖清单

```
opencv-python>=4.5.0
numpy>=1.19.0
scipy>=1.5.0
scikit-image>=0.17.0
pyyaml>=5.3.0
pillow>=8.0.0
matplotlib>=3.3.0
```

## 附录B: 参考标准

- ISO 128: 技术制图标准
- ASME Y14.5: 尺寸和公差标准
- OpenCV文档: https://docs.opencv.org/
