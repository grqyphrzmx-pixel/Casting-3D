"""
================================================================================
铸造行业模块与通用模块集成接口定义
Casting Module Integration Interface Definition
================================================================================
版本: 1.0
日期: 2024年

本文件定义了铸造行业专用模块与通用2D到3D转换模块之间的集成接口
"""

from typing import List, Dict, Optional, Tuple, Any, Protocol
from dataclasses import dataclass
from abc import ABC, abstractmethod
import numpy as np

# ==============================================================================
# 1. 核心集成接口定义
# ==============================================================================

class ICastingFeatureExtractor(ABC):
    """铸造特征提取器接口
    
    通用模块调用此接口来识别铸造相关的几何特征
    """
    
    @abstractmethod
    def extract_wall_features(self, mesh_data: np.ndarray) -> List[Dict]:
        """提取壁特征
        
        Args:
            mesh_data: 输入网格数据
            
        Returns:
            壁特征列表，每个特征包含厚度、面积、位置等信息
        """
        pass
    
    @abstractmethod
    def extract_hole_features(self, mesh_data: np.ndarray) -> List[Dict]:
        """提取孔特征
        
        Args:
            mesh_data: 输入网格数据
            
        Returns:
            孔特征列表，包含直径、深度、类型等信息
        """
        pass
    
    @abstractmethod
    def extract_rib_features(self, mesh_data: np.ndarray) -> List[Dict]:
        """提取加强筋/肋特征
        
        Args:
            mesh_data: 输入网格数据
            
        Returns:
            肋特征列表
        """
        pass
    
    @abstractmethod
    def detect_draft_angles(self, mesh_data: np.ndarray, 
                           parting_direction: np.ndarray) -> List[Dict]:
        """检测拔模斜度
        
        Args:
            mesh_data: 输入网格数据
            parting_direction: 分型方向向量
            
        Returns:
            拔模斜度信息列表
        """
        pass
    
    @abstractmethod
    def detect_fillets(self, mesh_data: np.ndarray) -> List[Dict]:
        """检测圆角特征
        
        Args:
            mesh_data: 输入网格数据
            
        Returns:
            圆角特征列表
        """
        pass


class ICastingQualityChecker(ABC):
    """铸造质量检查器接口
    
    通用模块调用此接口来验证模型是否符合铸造工艺要求
    """
    
    @abstractmethod
    def check_wall_thickness(self, features: List[Dict], 
                             material: str, 
                             process: str) -> Dict:
        """检查壁厚是否符合要求
        
        Args:
            features: 壁特征列表
            material: 材料类型
            process: 铸造工艺类型
            
        Returns:
            检查结果，包含状态、问题列表、建议等
        """
        pass
    
    @abstractmethod
    def check_draft_compliance(self, draft_features: List[Dict],
                               process: str) -> Dict:
        """检查拔模斜度合规性
        
        Args:
            draft_features: 拔模特征列表
            process: 铸造工艺类型
            
        Returns:
            检查结果
        """
        pass
    
    @abstractmethod
    def check_fillet_compliance(self, fillet_features: List[Dict]) -> Dict:
        """检查圆角合规性
        
        Args:
            fillet_features: 圆角特征列表
            
        Returns:
            检查结果
        """
        pass
    
    @abstractmethod
    def check_hot_spots(self, features: List[Dict]) -> List[Dict]:
        """检查热点区域（潜在缩孔位置）
        
        Args:
            features: 所有几何特征
            
        Returns:
            热点区域列表
        """
        pass
    
    @abstractmethod
    def generate_quality_report(self, part_data: Dict) -> Dict:
        """生成质量检查报告
        
        Args:
            part_data: 零件完整数据
            
        Returns:
            质量报告
        """
        pass


class ICastingGeometryModifier(ABC):
    """铸造几何修改器接口
    
    用于自动添加铸造工艺特征到3D模型
    """
    
    @abstractmethod
    def add_draft_angle(self, mesh_data: np.ndarray,
                       surface_indices: List[int],
                       draft_angle: float,
                       direction: np.ndarray) -> np.ndarray:
        """添加拔模斜度
        
        Args:
            mesh_data: 原始网格数据
            surface_indices: 需要添加拔模的表面索引
            draft_angle: 拔模角度（度）
            direction: 拔模方向
            
        Returns:
            修改后的网格数据
        """
        pass
    
    @abstractmethod
    def add_fillet(self, mesh_data: np.ndarray,
                   edge_indices: List[int],
                   radius: float) -> np.ndarray:
        """添加圆角
        
        Args:
            mesh_data: 原始网格数据
            edge_indices: 需要添加圆角的边索引
            radius: 圆角半径
            
        Returns:
            修改后的网格数据
        """
        pass
    
    @abstractmethod
    def add_machining_allowance(self, mesh_data: np.ndarray,
                                surface_indices: List[int],
                                allowance: float) -> np.ndarray:
        """添加加工余量
        
        Args:
            mesh_data: 原始网格数据
            surface_indices: 需要加工的表面索引
            allowance: 加工余量值
            
        Returns:
            修改后的网格数据
        """
        pass
    
    @abstractmethod
    def apply_shrinkage_compensation(self, mesh_data: np.ndarray,
                                     shrinkage_factor: float) -> np.ndarray:
        """应用收缩补偿
        
        Args:
            mesh_data: 原始网格数据
            shrinkage_factor: 收缩补偿系数
            
        Returns:
            修改后的网格数据
        """
        pass


class ICastingProcessAdvisor(ABC):
    """铸造工艺顾问接口
    
    提供铸造工艺相关的建议和推荐
    """
    
    @abstractmethod
    def recommend_casting_process(self, part_data: Dict) -> List[Dict]:
        """推荐适合的铸造工艺
        
        Args:
            part_data: 零件数据
            
        Returns:
            工艺推荐列表，按适合度排序
        """
        pass
    
    @abstractmethod
    def suggest_parting_surface(self, mesh_data: np.ndarray,
                                material: str) -> List[Dict]:
        """推荐分型面位置
        
        Args:
            mesh_data: 网格数据
            material: 材料类型
            
        Returns:
            分型面建议列表
        """
        pass
    
    @abstractmethod
    def suggest_gating_system(self, part_data: Dict,
                             process: str) -> Dict:
        """推荐浇注系统设计
        
        Args:
            part_data: 零件数据
            process: 铸造工艺
            
        Returns:
            浇注系统建议
        """
        pass
    
    @abstractmethod
    def get_material_properties(self, material_code: str) -> Dict:
        """获取材料属性
        
        Args:
            material_code: 材料代码
            
        Returns:
            材料属性字典
        """
        pass


# ==============================================================================
# 2. 数据交换格式定义
# ==============================================================================

@dataclass
class CastingFeatureData:
    """铸造特征数据交换格式"""
    feature_id: str
    feature_type: str  # wall, hole, rib, fillet, draft, joint
    
    # 几何信息
    center: Tuple[float, float, float]
    bounding_box: Tuple[Tuple[float, float, float], Tuple[float, float, float]]
    
    # 特征属性（根据类型变化）
    properties: Dict[str, Any]
    
    # 关联信息
    related_features: List[str]
    
    # 质量标记
    quality_issues: List[str]
    suggestions: List[str]


@dataclass
class CastingProcessData:
    """铸造工艺数据交换格式"""
    process_type: str
    material_code: str
    
    # 工艺参数
    pouring_temperature: float
    mold_temperature: float
    cooling_time: float
    
    # 收缩补偿
    shrinkage_factor: float
    
    # 加工余量
    machining_allowance: float


@dataclass
class CastingQualityResult:
    """铸造质量检查结果交换格式"""
    check_id: str
    check_name: str
    check_category: str
    
    status: str  # PASS, FAIL, WARNING
    
    actual_value: Any
    target_value: Any
    tolerance: float
    
    affected_features: List[str]
    description: str
    suggestion: str
    
    is_auto_fixable: bool


# ==============================================================================
# 3. 事件回调接口定义
# ==============================================================================

class ICastingEventHandler(ABC):
    """铸造事件处理器接口
    
    用于通用模块接收铸造模块的事件通知
    """
    
    @abstractmethod
    def on_feature_detected(self, feature_data: CastingFeatureData):
        """当检测到铸造特征时调用"""
        pass
    
    @abstractmethod
    def on_quality_issue_found(self, issue: CastingQualityResult):
        """当发现质量问题时调用"""
        pass
    
    @abstractmethod
    def on_process_recommended(self, recommendations: List[Dict]):
        """当推荐工艺时调用"""
        pass
    
    @abstractmethod
    def on_geometry_modified(self, modification_type: str, 
                            affected_areas: List[str]):
        """当几何被修改时调用"""
        pass


# ==============================================================================
# 4. 导出接口定义
# ==============================================================================

class ICastingExporter(ABC):
    """铸造专用导出接口"""
    
    @abstractmethod
    def export_for_procast(self, part_data: Dict, 
                          file_path: str) -> bool:
        """导出为ProCAST格式"""
        pass
    
    @abstractmethod
    def export_for_magma(self, part_data: Dict,
                        file_path: str) -> bool:
        """导出为MAGMA格式"""
        pass
    
    @abstractmethod
    def export_process_parameters(self, part_data: Dict,
                                  file_path: str,
                                  format: str = "json") -> bool:
        """导出工艺参数"""
        pass
    
    @abstractmethod
    def generate_technical_report(self, part_data: Dict,
                                  file_path: str) -> bool:
        """生成技术报告"""
        pass


# ==============================================================================
# 5. 配置接口定义
# ==============================================================================

class ICastingConfigProvider(ABC):
    """铸造配置提供器接口"""
    
    @abstractmethod
    def load_process_rules(self, process_type: str) -> Dict:
        """加载工艺规则"""
        pass
    
    @abstractmethod
    def load_material_database(self) -> Dict:
        """加载材料数据库"""
        pass
    
    @abstractmethod
    def save_custom_rules(self, rules: Dict, 
                         rule_name: str) -> bool:
        """保存自定义规则"""
        pass
    
    @abstractmethod
    def get_standard_versions(self) -> List[str]:
        """获取支持的标准版本列表"""
        pass


# ==============================================================================
# 6. 集成适配器基类
# ==============================================================================

class CastingModuleAdapter:
    """铸造模块适配器基类
    
    通用模块通过此适配器与铸造模块交互
    """
    
    def __init__(self):
        self.feature_extractor: Optional[ICastingFeatureExtractor] = None
        self.quality_checker: Optional[ICastingQualityChecker] = None
        self.geometry_modifier: Optional[ICastingGeometryModifier] = None
        self.process_advisor: Optional[ICastingProcessAdvisor] = None
        self.event_handler: Optional[ICastingEventHandler] = None
        self.exporter: Optional[ICastingExporter] = None
        self.config_provider: Optional[ICastingConfigProvider] = None
    
    def initialize(self, config: Dict) -> bool:
        """初始化适配器"""
        # 子类实现具体的初始化逻辑
        return True
    
    def extract_casting_features(self, mesh_data: np.ndarray) -> List[CastingFeatureData]:
        """提取铸造特征"""
        if not self.feature_extractor:
            return []
        
        features = []
        
        # 提取各类特征
        wall_features = self.feature_extractor.extract_wall_features(mesh_data)
        hole_features = self.feature_extractor.extract_hole_features(mesh_data)
        rib_features = self.feature_extractor.extract_rib_features(mesh_data)
        draft_features = self.feature_extractor.detect_draft_angles(mesh_data, np.array([0, 0, 1]))
        fillet_features = self.feature_extractor.detect_fillets(mesh_data)
        
        # 转换为统一格式
        for f in wall_features:
            features.append(CastingFeatureData(
                feature_id=f.get("id", ""),
                feature_type="wall",
                center=f.get("center", (0, 0, 0)),
                bounding_box=f.get("bbox", ((0,0,0), (0,0,0))),
                properties={"thickness": f.get("thickness", 0)},
                related_features=[],
                quality_issues=[],
                suggestions=[]
            ))
        
        return features
    
    def validate_for_casting(self, part_data: Dict) -> List[CastingQualityResult]:
        """验证铸造可行性"""
        if not self.quality_checker:
            return []
        
        results = []
        
        # 获取特征数据
        wall_features = part_data.get("wall_features", [])
        draft_features = part_data.get("draft_features", [])
        fillet_features = part_data.get("fillet_features", [])
        
        material = part_data.get("material", "")
        process = part_data.get("process", "")
        
        # 执行各项检查
        wall_check = self.quality_checker.check_wall_thickness(wall_features, material, process)
        draft_check = self.quality_checker.check_draft_compliance(draft_features, process)
        fillet_check = self.quality_checker.check_fillet_compliance(fillet_features)
        
        # 转换为统一格式
        if wall_check.get("status") != "PASS":
            results.append(CastingQualityResult(
                check_id="WALL_001",
                check_name="壁厚检查",
                check_category="壁厚",
                status=wall_check.get("status", "PASS"),
                actual_value=wall_check.get("actual", 0),
                target_value=wall_check.get("target", 0),
                tolerance=0.5,
                affected_features=wall_check.get("affected", []),
                description=wall_check.get("description", ""),
                suggestion=wall_check.get("suggestion", ""),
                is_auto_fixable=False
            ))
        
        return results
    
    def apply_casting_modifications(self, mesh_data: np.ndarray,
                                    modifications: List[Dict]) -> np.ndarray:
        """应用铸造修改"""
        if not self.geometry_modifier:
            return mesh_data
        
        result = mesh_data
        
        for mod in modifications:
            mod_type = mod.get("type", "")
            
            if mod_type == "draft":
                result = self.geometry_modifier.add_draft_angle(
                    result,
                    mod.get("surfaces", []),
                    mod.get("angle", 1.5),
                    np.array(mod.get("direction", [0, 0, 1]))
                )
            elif mod_type == "fillet":
                result = self.geometry_modifier.add_fillet(
                    result,
                    mod.get("edges", []),
                    mod.get("radius", 2.0)
                )
            elif mod_type == "machining_allowance":
                result = self.geometry_modifier.add_machining_allowance(
                    result,
                    mod.get("surfaces", []),
                    mod.get("allowance", 2.0)
                )
        
        return result
    
    def get_process_recommendations(self, part_data: Dict) -> List[Dict]:
        """获取工艺推荐"""
        if not self.process_advisor:
            return []
        
        return self.process_advisor.recommend_casting_process(part_data)
    
    def export_for_simulation(self, part_data: Dict,
                             file_path: str,
                             target_software: str) -> bool:
        """导出用于仿真分析"""
        if not self.exporter:
            return False
        
        if target_software.lower() == "procast":
            return self.exporter.export_for_procast(part_data, file_path)
        elif target_software.lower() == "magma":
            return self.exporter.export_for_magma(part_data, file_path)
        
        return False


# ==============================================================================
# 7. 使用示例
# ==============================================================================

def example_usage():
    """集成接口使用示例"""
    
    # 创建适配器实例
    adapter = CastingModuleAdapter()
    
    # 初始化（实际使用时需要传入具体的实现类）
    adapter.initialize({
        "process_type": "sand_casting",
        "material": "A356"
    })
    
    # 模拟网格数据
    mesh_data = np.random.rand(100, 3)  # 示例数据
    
    # 提取铸造特征
    features = adapter.extract_casting_features(mesh_data)
    print(f"提取到 {len(features)} 个铸造特征")
    
    # 模拟零件数据
    part_data = {
        "part_id": "TEST_001",
        "material": "aluminum_alloy",
        "process": "sand_casting",
        "wall_features": [{"thickness": 4.0}, {"thickness": 5.0}],
        "draft_features": [{"angle": 1.5}],
        "fillet_features": [{"radius": 2.0}]
    }
    
    # 验证铸造可行性
    quality_results = adapter.validate_for_casting(part_data)
    print(f"发现 {len(quality_results)} 个质量问题")
    
    # 获取工艺推荐
    recommendations = adapter.get_process_recommendations(part_data)
    print(f"推荐工艺: {recommendations[0]['process'] if recommendations else 'N/A'}")
    
    # 应用修改
    modifications = [
        {"type": "draft", "surfaces": [0, 1, 2], "angle": 1.5, "direction": [0, 0, 1]},
        {"type": "fillet", "edges": [0, 1], "radius": 2.0}
    ]
    modified_mesh = adapter.apply_casting_modifications(mesh_data, modifications)
    print(f"修改后网格形状: {modified_mesh.shape}")


if __name__ == "__main__":
    print("铸造模块集成接口定义加载成功！")
    print("=" * 60)
    print("主要接口类:")
    print("  - ICastingFeatureExtractor: 铸造特征提取器")
    print("  - ICastingQualityChecker: 铸造质量检查器")
    print("  - ICastingGeometryModifier: 铸造几何修改器")
    print("  - ICastingProcessAdvisor: 铸造工艺顾问")
    print("  - ICastingExporter: 铸造专用导出器")
    print("  - CastingModuleAdapter: 铸造模块适配器")
    print("=" * 60)
