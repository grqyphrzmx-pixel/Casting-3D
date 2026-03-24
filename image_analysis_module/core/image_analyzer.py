"""
铸造行业2D到3D转换 - 图像分析主模块

本模块提供图像分析的主入口，协调各个子模块完成从图像到几何特征
的完整分析流程。
"""

import cv2
import numpy as np
import logging
import time
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# 导入数据结构
from .data_structures import (
    SourceType, FeatureType, ShapeType, DimensionType, ConstraintType,
    Point2D, LineSegment, Circle, Arc, Ellipse, Polygon,
    Contour, GeometricFeature, FeatureMetadata,
    Dimension, Constraint,
    ImageInfo, AnalysisMetadata, AnalysisResult,
    create_contour_from_numpy
)


# =============================================================================
# 配置类
# =============================================================================

@dataclass
class PreprocessingConfig:
    """预处理配置"""
    denoise_method: str = "gaussian"  # gaussian, median, bilateral
    gaussian_sigma: float = 1.5
    median_kernel_size: int = 5
    bilateral_d: int = 9
    bilateral_sigma_color: float = 75.0
    bilateral_sigma_space: float = 75.0
    
    contrast_method: str = "clahe"  # clahe, gamma, none
    clahe_clip_limit: float = 2.0
    clahe_grid_size: int = 8
    gamma_value: float = 1.0
    
    binarization_method: str = "otsu"  # otsu, adaptive, manual
    adaptive_block_size: int = 11
    adaptive_c: float = 2.0
    manual_threshold: int = 127
    
    morphology_enabled: bool = True
    morphology_operations: List[Dict] = field(default_factory=lambda: [
        {"type": "open", "kernel_size": 3},
        {"type": "close", "kernel_size": 3}
    ])


@dataclass
class EdgeDetectionConfig:
    """边缘检测配置"""
    method: str = "canny"  # canny, sobel, laplacian
    canny_low_threshold: int = 50
    canny_high_threshold: int = 150
    canny_aperture_size: int = 3
    canny_l2_gradient: bool = False
    sobel_kernel_size: int = 3
    laplacian_kernel_size: int = 3


@dataclass
class ContourConfig:
    """轮廓分析配置"""
    retrieval_mode: str = "tree"  # external, list, tree
    approximation_method: str = "simple"  # none, simple, tc89_l1, tc89_kcos
    min_area: float = 100.0
    min_perimeter: float = 50.0
    max_area_ratio: float = 0.95  # 相对于图像面积的最大比例
    min_vertices: int = 3
    polygon_epsilon_factor: float = 0.01  # 多边形近似的epsilon因子


@dataclass
class FeatureExtractionConfig:
    """特征提取配置"""
    min_confidence: float = 0.7
    line_angle_tolerance: float = 5.0  # 度
    circle_circularity_threshold: float = 0.85
    arc_min_angle_span: float = 15.0  # 度
    polygon_angle_tolerance: float = 10.0  # 度
    enabled_recognizers: List[str] = field(default_factory=lambda: [
        "line", "circle", "arc", "ellipse", "polygon"
    ])


@dataclass
class DimensionExtractionConfig:
    """尺寸提取配置"""
    ocr_enabled: bool = True
    min_text_height: int = 10
    text_confidence_threshold: float = 0.6
    dimension_line_extension: float = 10.0
    arrow_detection_enabled: bool = True


@dataclass
class AnalyzerConfig:
    """分析器配置"""
    preprocessing: PreprocessingConfig = field(default_factory=PreprocessingConfig)
    edge_detection: EdgeDetectionConfig = field(default_factory=EdgeDetectionConfig)
    contour: ContourConfig = field(default_factory=ContourConfig)
    feature: FeatureExtractionConfig = field(default_factory=FeatureExtractionConfig)
    dimension: DimensionExtractionConfig = field(default_factory=DimensionExtractionConfig)
    debug_mode: bool = False
    log_level: str = "INFO"


# =============================================================================
# 日志系统
# =============================================================================

class AnalysisLogger:
    """分析过程日志记录器"""
    
    _instance = None
    
    def __new__(cls, name: str = "image_analyzer"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, name: str = "image_analyzer"):
        if self._initialized:
            return
        
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # 清除已有的处理器
        self.logger.handlers.clear()
        
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
        
        self._initialized = True
    
    def debug(self, message: str):
        self.logger.debug(message)
    
    def info(self, message: str):
        self.logger.info(message)
    
    def warning(self, message: str):
        self.logger.warning(message)
    
    def error(self, message: str):
        self.logger.error(message)
    
    def log_step(self, step_name: str, params: Dict = None):
        """记录处理步骤"""
        msg = f"Step: {step_name}"
        if params:
            msg += f", Params: {params}"
        self.logger.debug(msg)
    
    def log_result(self, step_name: str, result_summary: Dict):
        """记录处理结果"""
        self.logger.info(f"Step: {step_name}, Result: {result_summary}")
    
    def log_error(self, step_name: str, error: Exception):
        """记录错误"""
        self.logger.error(f"Step: {step_name}, Error: {str(error)}")


# =============================================================================
# 图像预处理器
# =============================================================================

class ImagePreprocessor:
    """图像预处理模块"""
    
    def __init__(self, config: PreprocessingConfig):
        self.config = config
        self.logger = AnalysisLogger()
    
    def process(self, image: np.ndarray, 
                source_type: SourceType = SourceType.UNKNOWN) -> np.ndarray:
        """
        执行完整的图像预处理流程
        
        Args:
            image: 输入图像 (BGR或灰度)
            source_type: 图像源类型
            
        Returns:
            预处理后的二值图像
        """
        start_time = time.time()
        self.logger.log_step("preprocessing_start", {"source_type": source_type.name})
        
        # 1. 灰度转换
        result = self._convert_to_grayscale(image)
        
        # 2. 去噪
        result = self._denoise(result)
        
        # 3. 对比度增强
        result = self._enhance_contrast(result)
        
        # 4. 二值化
        result = self._binarize(result, source_type)
        
        # 5. 形态学操作
        if self.config.morphology_enabled:
            result = self._apply_morphology(result)
        
        elapsed = time.time() - start_time
        self.logger.log_result("preprocessing", {
            "elapsed_ms": round(elapsed * 1000, 2),
            "output_shape": result.shape
        })
        
        return result
    
    def _convert_to_grayscale(self, image: np.ndarray) -> np.ndarray:
        """转换为灰度图像"""
        if len(image.shape) == 3:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return image.copy()
    
    def _denoise(self, image: np.ndarray) -> np.ndarray:
        """去噪处理"""
        method = self.config.denoise_method
        
        if method == "gaussian":
            kernel_size = int(6 * self.config.gaussian_sigma) | 1  # 确保奇数
            return cv2.GaussianBlur(
                image, 
                (kernel_size, kernel_size),
                self.config.gaussian_sigma
            )
        elif method == "median":
            return cv2.medianBlur(image, self.config.median_kernel_size)
        elif method == "bilateral":
            return cv2.bilateralFilter(
                image,
                self.config.bilateral_d,
                self.config.bilateral_sigma_color,
                self.config.bilateral_sigma_space
            )
        else:
            return image
    
    def _enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """对比度增强"""
        method = self.config.contrast_method
        
        if method == "clahe":
            clahe = cv2.createCLAHE(
                clipLimit=self.config.clahe_clip_limit,
                tileGridSize=(self.config.clahe_grid_size, 
                             self.config.clahe_grid_size)
            )
            return clahe.apply(image)
        elif method == "gamma":
            inv_gamma = 1.0 / self.config.gamma_value
            table = np.array([
                ((i / 255.0) ** inv_gamma) * 255 
                for i in range(256)
            ]).astype("uint8")
            return cv2.LUT(image, table)
        else:
            return image
    
    def _binarize(self, image: np.ndarray, 
                  source_type: SourceType) -> np.ndarray:
        """二值化"""
        method = self.config.binarization_method
        
        if method == "otsu":
            _, binary = cv2.threshold(
                image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
            )
            return binary
        elif method == "adaptive":
            return cv2.adaptiveThreshold(
                image, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY_INV,
                self.config.adaptive_block_size,
                self.config.adaptive_c
            )
        elif method == "manual":
            _, binary = cv2.threshold(
                image, self.config.manual_threshold, 255, cv2.THRESH_BINARY_INV
            )
            return binary
        else:
            return image
    
    def _apply_morphology(self, image: np.ndarray) -> np.ndarray:
        """形态学操作"""
        result = image.copy()
        
        for op in self.config.morphology_operations:
            op_type = op.get("type", "open")
            kernel_size = op.get("kernel_size", 3)
            kernel = cv2.getStructuringElement(
                cv2.MORPH_RECT, 
                (kernel_size, kernel_size)
            )
            
            if op_type == "open":
                result = cv2.morphologyEx(result, cv2.MORPH_OPEN, kernel)
            elif op_type == "close":
                result = cv2.morphologyEx(result, cv2.MORPH_CLOSE, kernel)
            elif op_type == "erode":
                result = cv2.erode(result, kernel)
            elif op_type == "dilate":
                result = cv2.dilate(result, kernel)
        
        return result


# =============================================================================
# 边缘检测器
# =============================================================================

class EdgeDetector:
    """边缘检测模块"""
    
    def __init__(self, config: EdgeDetectionConfig):
        self.config = config
        self.logger = AnalysisLogger()
    
    def detect(self, image: np.ndarray) -> np.ndarray:
        """
        检测图像边缘
        
        Args:
            image: 输入图像（灰度或二值）
            
        Returns:
            边缘图像
        """
        start_time = time.time()
        self.logger.log_step("edge_detection", {"method": self.config.method})
        
        method = self.config.method
        
        if method == "canny":
            edges = cv2.Canny(
                image,
                self.config.canny_low_threshold,
                self.config.canny_high_threshold,
                apertureSize=self.config.canny_aperture_size,
                L2gradient=self.config.canny_l2_gradient
            )
        elif method == "sobel":
            sobelx = cv2.Sobel(image, cv2.CV_64F, 1, 0, 
                              ksize=self.config.sobel_kernel_size)
            sobely = cv2.Sobel(image, cv2.CV_64F, 0, 1,
                              ksize=self.config.sobel_kernel_size)
            edges = np.sqrt(sobelx**2 + sobely**2).astype(np.uint8)
            _, edges = cv2.threshold(edges, 50, 255, cv2.THRESH_BINARY)
        elif method == "laplacian":
            edges = cv2.Laplacian(image, cv2.CV_64F,
                                 ksize=self.config.laplacian_kernel_size)
            edges = np.abs(edges).astype(np.uint8)
            _, edges = cv2.threshold(edges, 50, 255, cv2.THRESH_BINARY)
        else:
            edges = image.copy()
        
        elapsed = time.time() - start_time
        self.logger.log_result("edge_detection", {
            "elapsed_ms": round(elapsed * 1000, 2),
            "edge_pixels": int(np.sum(edges > 0))
        })
        
        return edges


# =============================================================================
# 轮廓分析器
# =============================================================================

class ContourAnalyzer:
    """轮廓分析模块"""
    
    def __init__(self, config: ContourConfig):
        self.config = config
        self.logger = AnalysisLogger()
        self._contour_id_counter = 0
    
    def analyze(self, edge_image: np.ndarray) -> List[Contour]:
        """
        分析边缘图像，提取轮廓
        
        Args:
            edge_image: 边缘图像
            
        Returns:
            轮廓列表
        """
        start_time = time.time()
        self.logger.log_step("contour_analysis")
        
        # 查找轮廓
        retrieval_mode = self._get_retrieval_mode()
        approx_method = self._get_approximation_method()
        
        contours_cv, hierarchy = cv2.findContours(
            edge_image,
            retrieval_mode,
            approx_method
        )
        
        self.logger.info(f"Found {len(contours_cv)} raw contours")
        
        # 转换为内部格式并筛选
        contours = []
        image_area = edge_image.shape[0] * edge_image.shape[1]
        
        for i, cnt_cv in enumerate(contours_cv):
            contour = self._convert_contour(cnt_cv, hierarchy, i)
            
            # 应用筛选条件
            if self._filter_contour(contour, image_area):
                contours.append(contour)
        
        # 建立层级关系
        contours = self._build_hierarchy(contours, hierarchy)
        
        elapsed = time.time() - start_time
        self.logger.log_result("contour_analysis", {
            "elapsed_ms": round(elapsed * 1000, 2),
            "filtered_contours": len(contours)
        })
        
        return contours
    
    def _get_retrieval_mode(self) -> int:
        """获取轮廓检索模式"""
        modes = {
            "external": cv2.RETR_EXTERNAL,
            "list": cv2.RETR_LIST,
            "tree": cv2.RETR_TREE,
            "ccomp": cv2.RETR_CCOMP
        }
        return modes.get(self.config.retrieval_mode, cv2.RETR_TREE)
    
    def _get_approximation_method(self) -> int:
        """获取近似方法"""
        methods = {
            "none": cv2.CHAIN_APPROX_NONE,
            "simple": cv2.CHAIN_APPROX_SIMPLE,
            "tc89_l1": cv2.CHAIN_APPROX_TC89_L1,
            "tc89_kcos": cv2.CHAIN_APPROX_TC89_KCOS
        }
        return methods.get(self.config.approximation_method, cv2.CHAIN_APPROX_SIMPLE)
    
    def _convert_contour(self, cnt_cv: np.ndarray, 
                         hierarchy: np.ndarray,
                         index: int) -> Contour:
        """将OpenCV轮廓转换为内部格式"""
        self._contour_id_counter += 1
        
        # 转换点
        points = [Point2D(float(p[0][0]), float(p[0][1])) for p in cnt_cv]
        
        # 判断封闭性
        is_closed = len(points) > 2 and points[0].distance_to(points[-1]) < 1.0
        
        # 获取层级信息
        parent_id = None
        if hierarchy is not None and hierarchy[0][index][3] >= 0:
            parent_id = hierarchy[0][index][3]
        
        return Contour(
            id=self._contour_id_counter,
            points=points,
            is_closed=is_closed,
            parent_id=parent_id
        )
    
    def _filter_contour(self, contour: Contour, 
                        image_area: int) -> bool:
        """筛选轮廓"""
        # 面积筛选
        if contour.area < self.config.min_area:
            return False
        
        if contour.area > image_area * self.config.max_area_ratio:
            return False
        
        # 周长筛选
        if contour.perimeter < self.config.min_perimeter:
            return False
        
        # 顶点数筛选
        if len(contour.points) < self.config.min_vertices:
            return False
        
        return True
    
    def _build_hierarchy(self, contours: List[Contour], 
                         hierarchy: np.ndarray) -> List[Contour]:
        """建立轮廓层级关系"""
        if hierarchy is None:
            return contours
        
        # 构建ID到轮廓的映射
        contour_map = {c.id: c for c in contours}
        
        # 更新子轮廓关系
        for contour in contours:
            if contour.parent_id is not None:
                parent = contour_map.get(contour.parent_id)
                if parent:
                    parent.children_ids.append(contour.id)
        
        return contours
    
    def approximate_polygon(self, contour: Contour, 
                           epsilon_factor: float = None) -> List[Point2D]:
        """
        使用Douglas-Peucker算法近似多边形
        
        Args:
            contour: 输入轮廓
            epsilon_factor: 近似精度因子
            
        Returns:
            近似后的顶点列表
        """
        if epsilon_factor is None:
            epsilon_factor = self.config.polygon_epsilon_factor
        
        epsilon = epsilon_factor * contour.perimeter
        
        # 转换为OpenCV格式
        cnt_cv = np.array([[p.x, p.y] for p in contour.points], dtype=np.float32)
        
        # 近似
        approx_cv = cv2.approxPolyDP(cnt_cv, epsilon, contour.is_closed)
        
        # 转换回内部格式
        approx_points = [Point2D(float(p[0][0]), float(p[0][1])) for p in approx_cv]
        
        return approx_points


# =============================================================================
# 主分析器类
# =============================================================================

class ImageAnalyzer:
    """
    图像分析主类
    
    协调各个子模块完成从图像到几何特征的完整分析流程。
    """
    
    def __init__(self, config: AnalyzerConfig = None):
        """
        初始化分析器
        
        Args:
            config: 分析器配置，如果为None则使用默认配置
        """
        self.config = config or AnalyzerConfig()
        self.logger = AnalysisLogger()
        
        # 初始化子模块
        self.preprocessor = ImagePreprocessor(self.config.preprocessing)
        self.edge_detector = EdgeDetector(self.config.edge_detection)
        self.contour_analyzer = ContourAnalyzer(self.config.contour)
        
        # 特征提取器将在单独模块中实现
        self.feature_extractor = None
        self.dimension_extractor = None
        
        self.logger.info("ImageAnalyzer initialized")
    
    def analyze(self, image: np.ndarray, 
                source_type: SourceType = SourceType.UNKNOWN,
                original_path: str = "") -> AnalysisResult:
        """
        执行完整的图像分析
        
        Args:
            image: 输入图像
            source_type: 图像源类型
            original_path: 原始图像路径
            
        Returns:
            分析结果
        """
        start_time = time.time()
        self.logger.info(f"Starting analysis of image: {original_path}")
        
        # 创建图像信息
        height, width = image.shape[:2]
        image_info = ImageInfo(
            width=width,
            height=height,
            source_type=source_type,
            original_path=original_path
        )
        
        try:
            # 1. 预处理
            processed = self.preprocessor.process(image, source_type)
            
            # 2. 边缘检测
            edges = self.edge_detector.detect(processed)
            
            # 3. 轮廓分析
            contours = self.contour_analyzer.analyze(edges)
            
            # 4. 特征提取（简化版本）
            features = self._extract_basic_features(contours)
            
            # 5. 构建结果
            elapsed = time.time() - start_time
            
            metadata = AnalysisMetadata(
                processing_time_seconds=elapsed,
                timestamp=datetime.now()
            )
            
            result = AnalysisResult(
                image_info=image_info,
                contours=contours,
                features=features,
                metadata=metadata
            )
            
            self.logger.info(f"Analysis completed in {elapsed:.2f}s")
            self.logger.info(f"Found {len(contours)} contours, {len(features)} features")
            
            return result
            
        except Exception as e:
            self.logger.log_error("analysis", e)
            # 返回部分结果
            return AnalysisResult(
                image_info=image_info,
                metadata=AnalysisMetadata(
                    errors=[str(e)],
                    processing_time_seconds=time.time() - start_time
                )
            )
    
    def analyze_file(self, filepath: str, 
                     source_type: SourceType = None) -> AnalysisResult:
        """
        分析图像文件
        
        Args:
            filepath: 图像文件路径
            source_type: 图像源类型，如果为None则自动检测
            
        Returns:
            分析结果
        """
        # 读取图像
        image = cv2.imread(filepath)
        if image is None:
            raise ValueError(f"Failed to load image: {filepath}")
        
        # 自动检测源类型
        if source_type is None:
            source_type = self._detect_source_type(filepath)
        
        return self.analyze(image, source_type, filepath)
    
    def _detect_source_type(self, filepath: str) -> SourceType:
        """自动检测图像源类型"""
        # 简单的启发式规则
        ext = Path(filepath).suffix.lower()
        
        # 根据文件扩展名初步判断
        if ext in ['.dxf', '.dwg', '.svg']:
            return SourceType.TECHNICAL_DRAWING
        
        # 默认根据图像特征判断
        # 这里可以实现更复杂的检测逻辑
        return SourceType.UNKNOWN
    
    def _extract_basic_features(self, contours: List[Contour]) -> List[GeometricFeature]:
        """提取基本几何特征（简化版本）"""
        features = []
        feature_id = 0
        
        for contour in contours:
            # 尝试识别为圆
            circle = self._fit_circle(contour)
            if circle and circle.confidence > 0.8:
                feature_id += 1
                features.append(GeometricFeature(
                    id=feature_id,
                    feature_type=FeatureType.CIRCLE,
                    geometry=circle,
                    source_contour_id=contour.id,
                    confidence=circle.confidence
                ))
                continue
            
            # 尝试近似为多边形
            approx_points = self.contour_analyzer.approximate_polygon(contour)
            
            if len(approx_points) == 2:
                # 线段
                feature_id += 1
                line = LineSegment(approx_points[0], approx_points[1])
                features.append(GeometricFeature(
                    id=feature_id,
                    feature_type=FeatureType.LINE,
                    geometry=line,
                    source_contour_id=contour.id,
                    confidence=0.9
                ))
            elif len(approx_points) > 2:
                # 多边形
                feature_id += 1
                polygon = Polygon(approx_points, contour.is_closed)
                features.append(GeometricFeature(
                    id=feature_id,
                    feature_type=FeatureType.POLYGON,
                    geometry=polygon,
                    source_contour_id=contour.id,
                    confidence=0.85
                ))
        
        return features
    
    def _fit_circle(self, contour: Contour) -> Optional[Circle]:
        """拟合圆"""
        if len(contour.points) < 5:
            return None
        
        # 使用OpenCV拟合圆
        points_cv = np.array([[p.x, p.y] for p in contour.points], dtype=np.float32)
        
        try:
            (x, y), radius = cv2.minEnclosingCircle(points_cv)
            
            # 计算圆度
            circle_area = np.pi * radius ** 2
            circularity = contour.area / circle_area if circle_area > 0 else 0
            
            if circularity > self.config.feature.circle_circularity_threshold:
                return Circle(
                    center=Point2D(x, y),
                    radius=radius,
                    confidence=circularity
                )
        except:
            pass
        
        return None
    
    def get_config(self) -> Dict:
        """获取当前配置"""
        return {
            "preprocessing": {
                "denoise_method": self.config.preprocessing.denoise_method,
                "contrast_method": self.config.preprocessing.contrast_method,
                "binarization_method": self.config.preprocessing.binarization_method
            },
            "edge_detection": {
                "method": self.config.edge_detection.method
            },
            "contour": {
                "retrieval_mode": self.config.contour.retrieval_mode,
                "min_area": self.config.contour.min_area
            }
        }


# =============================================================================
# 便捷函数
# =============================================================================

def analyze_image(image_path: str, 
                  config: AnalyzerConfig = None,
                  source_type: SourceType = None) -> AnalysisResult:
    """
    便捷函数：分析图像文件
    
    Args:
        image_path: 图像文件路径
        config: 分析器配置
        source_type: 图像源类型
        
    Returns:
        分析结果
    """
    analyzer = ImageAnalyzer(config)
    return analyzer.analyze_file(image_path, source_type)


# 模块测试
if __name__ == "__main__":
    # 创建测试图像
    test_image = np.zeros((400, 400), dtype=np.uint8)
    
    # 绘制测试形状
    cv2.circle(test_image, (200, 200), 100, 255, 2)
    cv2.rectangle(test_image, (50, 50), (150, 150), 255, 2)
    cv2.line(test_image, (250, 50), (350, 150), 255, 2)
    
    # 创建分析器
    config = AnalyzerConfig()
    config.debug_mode = True
    
    analyzer = ImageAnalyzer(config)
    
    # 分析图像
    result = analyzer.analyze(test_image, SourceType.TECHNICAL_DRAWING, "test")
    
    print(f"\nAnalysis Results:")
    print(f"  Contours: {result.num_contours}")
    print(f"  Features: {result.num_features}")
    print(f"  Processing time: {result.metadata.processing_time_seconds:.3f}s")
    
    # 打印特征详情
    for feature in result.features:
        print(f"\n  Feature {feature.id}: {feature.feature_type.name}")
        print(f"    Confidence: {feature.confidence:.2f}")
        if isinstance(feature.geometry, Circle):
            print(f"    Center: ({feature.geometry.center.x:.1f}, {feature.geometry.center.y:.1f})")
            print(f"    Radius: {feature.geometry.radius:.1f}")
        elif isinstance(feature.geometry, LineSegment):
            print(f"    Start: ({feature.geometry.start.x:.1f}, {feature.geometry.start.y:.1f})")
            print(f"    End: ({feature.geometry.end.x:.1f}, {feature.geometry.end.y:.1f})")
    
    print("\nTest completed!")
