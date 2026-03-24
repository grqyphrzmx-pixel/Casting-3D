"""
================================================================================
铸造行业2D到3D转换应用 - 数据模型定义
Casting Industry 2D to 3D Converter - Data Model Definitions
================================================================================
版本: 1.0
日期: 2024年
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Union, Callable
from enum import Enum, auto
import numpy as np
from datetime import datetime

# ==============================================================================
# 4.1 枚举类型定义
# ==============================================================================

class CastingProcess(Enum):
    """铸造工艺类型"""
    SAND_CASTING = "砂型铸造"
    INVESTMENT_CASTING = "熔模铸造"
    DIE_CASTING = "压铸"
    CENTRIFUGAL_CASTING = "离心铸造"
    PERMANENT_MOLD = "金属型铸造"
    SHELL_MOLDING = "壳型铸造"
    PLASTER_MOLDING = "石膏型铸造"


class MaterialType(Enum):
    """铸造材料类型"""
    ALUMINUM_ALLOY = "铝合金"
    ZINC_ALLOY = "锌合金"
    MAGNESIUM_ALLOY = "镁合金"
    GRAY_IRON = "灰铸铁"
    DUCTILE_IRON = "球墨铸铁"
    STEEL = "铸钢"
    COPPER_ALLOY = "铜合金"
    NICKEL_ALLOY = "镍合金"
    TITANIUM_ALLOY = "钛合金"


class SurfaceType(Enum):
    """表面类型"""
    EXTERNAL = "外表面"
    INTERNAL = "内表面"
    CORE_HOLE = "型芯孔"
    PARTING_SURFACE = "分型面"


class JointType(Enum):
    """接头类型"""
    L_JOINT = "L型接头"
    T_JOINT = "T型接头"
    X_JOINT = "X型接头"
    Y_JOINT = "Y型接头"


class QualityLevel(Enum):
    """质量等级"""
    CRITICAL = "关键"
    MAJOR = "主要"
    MINOR = "次要"
    INFO = "信息"


class CheckStatus(Enum):
    """检查状态"""
    PASS = "通过"
    FAIL = "失败"
    WARNING = "警告"
    NOT_CHECKED = "未检查"


# ==============================================================================
# 4.2 材料属性数据模型
# ==============================================================================

@dataclass
class MaterialProperties:
    """铸造材料属性"""
    # 基本信息
    material_type: MaterialType
    material_code: str  # 材料牌号，如 "A356", "ZL104"
    material_name: str
    
    # 物理属性
    density: float  # g/cm³
    melting_point: float  # °C
    pouring_temperature: float  # °C
    solidus_temperature: float  # °C
    liquidus_temperature: float  # °C
    
    # 收缩特性
    linear_shrinkage: float  # % 线收缩率
    volume_shrinkage: float  # % 体积收缩率
    
    # 工艺参数
    min_wall_thickness: Dict[CastingProcess, float]  # 各工艺最小壁厚(mm)
    recommended_draft_angle: Dict[CastingProcess, Dict[str, float]]  # 推荐拔模角度
    
    # 热物性
    thermal_conductivity: float  # W/(m·K)
    specific_heat: float  # J/(kg·K)
    thermal_expansion: float  # 1/K
    
    # 机械性能
    tensile_strength: float  # MPa
    yield_strength: float  # MPa
    elongation: float  # %
    hardness: float  # HB
    
    # 备注
    notes: str = ""
    
    def get_min_wall_thickness(self, process: CastingProcess) -> float:
        """获取指定工艺的最小壁厚"""
        return self.min_wall_thickness.get(process, 3.0)
    
    def get_draft_angle(self, process: CastingProcess, surface_type: SurfaceType, 
                        height_mm: float) -> float:
        """根据工艺和表面类型获取推荐拔模角度"""
        draft_config = self.recommended_draft_angle.get(process, {})
        base_angle = draft_config.get(surface_type.value, 1.0)
        
        # 根据高度调整角度
        if height_mm < 20:
            return base_angle * 0.5
        elif height_mm < 50:
            return base_angle * 0.75
        elif height_mm < 100:
            return base_angle
        elif height_mm < 200:
            return base_angle * 1.25
        else:
            return base_angle * 1.5


# ==============================================================================
# 4.3 几何特征数据模型
# ==============================================================================

@dataclass
class Point3D:
    """三维点"""
    x: float
    y: float
    z: float
    
    def to_array(self) -> np.ndarray:
        return np.array([self.x, self.y, self.z])
    
    def distance_to(self, other: 'Point3D') -> float:
        return np.sqrt((self.x - other.x)**2 + (self.y - other.y)**2 + (self.z - other.z)**2)


@dataclass
class Vector3D:
    """三维向量"""
    x: float
    y: float
    z: float
    
    def normalize(self) -> 'Vector3D':
        length = np.sqrt(self.x**2 + self.y**2 + self.z**2)
        if length > 0:
            return Vector3D(self.x/length, self.y/length, self.z/length)
        return Vector3D(0, 0, 0)


@dataclass
class GeometricFeature:
    """几何特征基类"""
    feature_id: str
    feature_type: str
    name: str
    
    # 几何信息
    center_point: Point3D
    bounding_box: Tuple[Point3D, Point3D]  # (min, max)
    
    # 尺寸信息
    dimensions: Dict[str, float] = field(default_factory=dict)
    
    # 表面信息
    surface_area: float = 0.0
    volume: float = 0.0
    
    # 关联特征
    parent_feature: Optional[str] = None
    child_features: List[str] = field(default_factory=list)


@dataclass
class WallFeature(GeometricFeature):
    """壁特征"""
    thickness: float = 0.0  # 壁厚
    nominal_thickness: float = 0.0  # 标称壁厚
    thickness_variation: float = 0.0  # 厚度变化率
    
    # 相邻特征
    adjacent_walls: List[str] = field(default_factory=list)
    connected_joints: List[str] = field(default_factory=list)
    
    # 质量属性
    is_uniform: bool = True
    is_too_thin: bool = False
    is_too_thick: bool = False


@dataclass
class HoleFeature(GeometricFeature):
    """孔特征"""
    hole_type: str = "通孔"  # 通孔、盲孔、螺纹孔
    diameter: float = 0.0
    depth: float = 0.0  # 盲孔深度，通孔为0
    
    # 铸造相关
    is_castable: bool = True
    min_castable_diameter: float = 5.0  # 最小可铸造孔径
    core_required: bool = False
    
    # 拔模相关
    draft_angle: float = 0.0
    draft_direction: Optional[Vector3D] = None


@dataclass
class RibFeature(GeometricFeature):
    """加强筋/肋特征"""
    rib_thickness: float = 0.0
    rib_height: float = 0.0
    rib_length: float = 0.0
    
    # 设计参数
    thickness_ratio: float = 0.0  # 筋厚/主壁厚
    height_to_thickness_ratio: float = 0.0  # 高厚比
    
    # 端部处理
    end_fillet_radius: float = 0.0
    root_fillet_radius: float = 0.0
    
    # 质量检查
    is_valid_design: bool = True
    design_issues: List[str] = field(default_factory=list)


@dataclass
class FilletFeature(GeometricFeature):
    """圆角特征"""
    fillet_type: str = "内圆角"  # 内圆角、外圆角
    radius: float = 0.0
    
    # 连接的壁
    wall1_id: str = ""
    wall2_id: str = ""
    wall1_thickness: float = 0.0
    wall2_thickness: float = 0.0
    
    # 推荐值
    recommended_radius: float = 0.0
    radius_ratio: float = 0.0  # 实际/推荐
    
    # 质量检查
    is_adequate: bool = True
    is_too_small: bool = False
    is_too_large: bool = False


@dataclass
class DraftFeature(GeometricFeature):
    """拔模斜度特征"""
    surface_type: SurfaceType = SurfaceType.EXTERNAL
    draft_angle: float = 0.0  # 度
    draft_direction: Vector3D = field(default_factory=lambda: Vector3D(0, 0, 1))
    
    # 表面信息
    surface_height: float = 0.0
    surface_area: float = 0.0
    
    # 推荐值
    recommended_angle: float = 0.0
    angle_deviation: float = 0.0  # 实际与推荐的偏差
    
    # 质量检查
    is_adequate: bool = True
    is_insufficient: bool = False
    is_excessive: bool = False


@dataclass
class JointFeature(GeometricFeature):
    """接头特征（T型、X型、L型等）"""
    joint_type: JointType = JointType.L_JOINT
    
    # 连接的壁
    connected_walls: List[str] = field(default_factory=list)
    wall_thicknesses: List[float] = field(default_factory=list)
    avg_wall_thickness: float = 0.0
    
    # 圆角信息
    inner_fillet_radius: float = 0.0
    outer_fillet_radius: float = 0.0
    recommended_inner_radius: float = 0.0
    recommended_outer_radius: float = 0.0
    
    # 热点分析
    is_hot_spot: bool = False
    hot_spot_risk_level: str = "低"  # 低、中、高


# ==============================================================================
# 4.4 铸造零件数据模型
# ==============================================================================

@dataclass
class PartingSurface:
    """分型面数据模型"""
    surface_id: str
    name: str
    
    # 几何定义
    plane_origin: Point3D
    plane_normal: Vector3D
    
    # 分型线
    parting_line: List[Point3D] = field(default_factory=list)
    
    # 分型面类型
    is_flat: bool = True
    is_complex: bool = False
    
    # 验证结果
    draft_check_passed: bool = True
    undercut_detected: bool = False
    undercut_areas: List[Tuple[Point3D, Point3D]] = field(default_factory=list)
    
    # 优化建议
    optimization_suggestions: List[str] = field(default_factory=list)


@dataclass
class CastingPart:
    """铸造零件主数据模型"""
    # 基本信息
    part_id: str
    part_name: str
    part_number: str
    revision: str = "A"
    
    # 工艺信息
    casting_process: CastingProcess = CastingProcess.SAND_CASTING
    material: Optional[MaterialProperties] = None
    
    # 几何信息
    overall_dimensions: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # L x W x H
    bounding_box: Tuple[Point3D, Point3D] = field(
        default_factory=lambda: (Point3D(0,0,0), Point3D(0,0,0))
    )
    surface_area: float = 0.0
    volume: float = 0.0
    weight: float = 0.0  # 计算重量
    
    # 特征列表
    wall_features: List[WallFeature] = field(default_factory=list)
    hole_features: List[HoleFeature] = field(default_factory=list)
    rib_features: List[RibFeature] = field(default_factory=list)
    fillet_features: List[FilletFeature] = field(default_factory=list)
    draft_features: List[DraftFeature] = field(default_factory=list)
    joint_features: List[JointFeature] = field(default_factory=list)
    
    # 分型面信息
    parting_surface: Optional[PartingSurface] = None
    
    # 加工信息
    machining_allowance: float = 2.0  # 默认加工余量mm
    surfaces_to_machine: List[str] = field(default_factory=list)
    
    # 收缩补偿
    shrinkage_compensation: float = 1.0  # 收缩补偿系数
    
    # 元数据
    created_date: datetime = field(default_factory=datetime.now)
    modified_date: datetime = field(default_factory=datetime.now)
    author: str = ""
    notes: str = ""
    
    def calculate_weight(self) -> float:
        """计算零件重量"""
        if self.material:
            self.weight = self.volume * self.material.density / 1000  # kg
        return self.weight
    
    def get_feature_by_id(self, feature_id: str) -> Optional[GeometricFeature]:
        """根据ID获取特征"""
        all_features = (
            self.wall_features + self.hole_features + 
            self.rib_features + self.fillet_features +
            self.draft_features + self.joint_features
        )
        for feature in all_features:
            if feature.feature_id == feature_id:
                return feature
        return None
    
    def get_average_wall_thickness(self) -> float:
        """获取平均壁厚"""
        if not self.wall_features:
            return 0.0
        return sum(w.thickness for w in self.wall_features) / len(self.wall_features)


# ==============================================================================
# 4.5 工艺参数数据模型
# ==============================================================================

@dataclass
class ProcessParameters:
    """铸造工艺参数"""
    # 工艺类型
    casting_process: CastingProcess
    
    # 模具参数
    mold_temperature: float = 200.0  # °C
    mold_material: str = "H13"  # 模具材料
    
    # 浇注参数
    pouring_temperature: float = 700.0  # °C
    pouring_time: float = 5.0  # s
    filling_rate: float = 0.5  # m/s
    
    # 冷却参数
    cooling_time: float = 30.0  # s
    cooling_method: str = "自然冷却"
    
    # 压铸专用参数
    injection_pressure: float = 0.0  # MPa
    injection_speed: float = 0.0  # m/s
    
    # 砂型铸造参数
    sand_type: str = "树脂砂"
    sand_hardness: str = "中硬"
    
    # 收缩补偿
    shrinkage_factor: float = 1.0  # 模具尺寸放大系数


@dataclass
class Riser:
    """冒口数据模型"""
    riser_id: str
    riser_type: str = "圆柱形"  # 圆柱形、球形、腰形
    
    # 尺寸
    diameter: float = 0.0
    height: float = 0.0
    volume: float = 0.0
    
    # 模数
    modulus: float = 0.0
    
    # 位置
    position: Point3D = field(default_factory=lambda: Point3D(0, 0, 0))
    attached_to: str = ""  # 连接的铸件部位
    
    # 设计验证
    is_adequate: bool = True
    modulus_ratio: float = 0.0  # 冒口模数/铸件模数


@dataclass
class GatingSystem:
    """浇注系统数据模型"""
    system_id: str
    name: str
    
    # 浇口杯
    sprue_cup_diameter: float = 0.0
    sprue_cup_height: float = 0.0
    
    # 直浇道
    sprue_top_diameter: float = 0.0
    sprue_bottom_diameter: float = 0.0
    sprue_height: float = 0.0
    
    # 横浇道
    runner_cross_section: str = "梯形"  # 梯形、圆形
    runner_area: float = 0.0
    runner_length: float = 0.0
    
    # 内浇口
    ingate_area: float = 0.0
    ingate_thickness: float = 0.0
    ingate_width: float = 0.0
    num_ingates: int = 1
    
    # 冒口
    risers: List[Riser] = field(default_factory=list)
    
    # 流道比
    sprue_runner_ratio: float = 1.15
    runner_ingate_ratio: float = 1.1


# ==============================================================================
# 4.6 质量检查数据模型
# ==============================================================================

@dataclass
class QualityCheckItem:
    """质量检查项"""
    check_id: str
    check_name: str
    check_category: str
    
    # 检查状态
    status: CheckStatus = CheckStatus.NOT_CHECKED
    quality_level: QualityLevel = QualityLevel.INFO
    
    # 检查值
    actual_value: Union[float, str, bool] = ""
    target_value: Union[float, str, bool] = ""
    tolerance: float = 0.0
    
    # 位置信息
    affected_features: List[str] = field(default_factory=list)
    affected_areas: List[Tuple[Point3D, Point3D]] = field(default_factory=list)
    
    # 问题描述
    description: str = ""
    suggestion: str = ""
    
    # 修复信息
    is_auto_fixable: bool = False
    auto_fix_applied: bool = False
    fix_result: str = ""


@dataclass
class QualityReport:
    """质量检查报告"""
    report_id: str
    part_id: str
    generated_date: datetime = field(default_factory=datetime.now)
    
    # 检查项列表
    check_items: List[QualityCheckItem] = field(default_factory=list)
    
    # 统计信息
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    warning_checks: int = 0
    
    # 综合评分
    overall_score: float = 100.0  # 0-100
    manufacturability_rating: str = "优秀"  # 优秀、良好、一般、差
    
    # 改进建议
    improvement_suggestions: List[str] = field(default_factory=list)
    critical_issues: List[str] = field(default_factory=list)
    
    def generate_summary(self) -> Dict:
        """生成报告摘要"""
        return {
            "report_id": self.report_id,
            "part_id": self.part_id,
            "overall_score": self.overall_score,
            "rating": self.manufacturability_rating,
            "total_checks": self.total_checks,
            "passed": self.passed_checks,
            "failed": self.failed_checks,
            "warnings": self.warning_checks,
            "critical_issues": len(self.critical_issues)
        }


# ==============================================================================
# 4.7 输入/输出数据模型
# ==============================================================================

@dataclass
class InputImage:
    """输入图像数据模型"""
    image_id: str
    file_path: str
    image_type: str  # 正视图、俯视图、侧视图、剖视图、等轴测图
    
    # 图像属性
    width: int = 0
    height: int = 0
    dpi: int = 300
    
    # 处理结果
    processed: bool = False
    detected_features: List[str] = field(default_factory=list)
    detected_dimensions: Dict[str, float] = field(default_factory=dict)
    
    # 对齐信息
    alignment_transform: Optional[np.ndarray] = None
    scale_factor: float = 1.0


@dataclass
class ExportConfig:
    """导出配置数据模型"""
    # 导出格式
    export_stl: bool = True
    export_step: bool = True
    export_iges: bool = False
    export_obj: bool = False
    
    # STL参数
    stl_binary: bool = True
    stl_tolerance: float = 0.01  # mm
    
    # 单位
    length_unit: str = "mm"
    
    # 坐标系
    coordinate_system: str = "右手系"
    
    # 仿真导出
    export_for_procast: bool = False
    export_for_magma: bool = False
    export_for_flow3d: bool = False
    
    # 工艺信息
    include_process_info: bool = True
    include_material_info: bool = True
    include_quality_report: bool = True


# ==============================================================================
# 4.8 预设材料数据库
# ==============================================================================

MATERIAL_DATABASE = {
    "A356": MaterialProperties(
        material_type=MaterialType.ALUMINUM_ALLOY,
        material_code="A356",
        material_name="铸造铝合金A356",
        density=2.68,
        melting_point=615,
        pouring_temperature=720,
        solidus_temperature=555,
        liquidus_temperature=615,
        linear_shrinkage=1.3,
        volume_shrinkage=6.5,
        min_wall_thickness={
            CastingProcess.SAND_CASTING: 3.0,
            CastingProcess.DIE_CASTING: 1.0,
            CastingProcess.INVESTMENT_CASTING: 1.5
        },
        recommended_draft_angle={
            CastingProcess.SAND_CASTING: {"外表面": 1.5, "内表面": 2.0, "型芯孔": 2.5},
            CastingProcess.DIE_CASTING: {"外表面": 0.5, "内表面": 1.0, "型芯孔": 1.5},
            CastingProcess.INVESTMENT_CASTING: {"外表面": 0.0, "内表面": 0.0, "型芯孔": 0.0}
        },
        thermal_conductivity=150,
        specific_heat=963,
        thermal_expansion=21.5e-6,
        tensile_strength=260,
        yield_strength=195,
        elongation=5,
        hardness=70,
        notes="常用铸造铝合金，良好的流动性和机械性能"
    ),
    "HT250": MaterialProperties(
        material_type=MaterialType.GRAY_IRON,
        material_code="HT250",
        material_name="灰铸铁HT250",
        density=7.1,
        melting_point=1200,
        pouring_temperature=1350,
        solidus_temperature=1150,
        liquidus_temperature=1200,
        linear_shrinkage=1.0,
        volume_shrinkage=3.5,
        min_wall_thickness={
            CastingProcess.SAND_CASTING: 4.0,
            CastingProcess.INVESTMENT_CASTING: 2.0
        },
        recommended_draft_angle={
            CastingProcess.SAND_CASTING: {"外表面": 1.5, "内表面": 2.0, "型芯孔": 2.5},
            CastingProcess.INVESTMENT_CASTING: {"外表面": 0.5, "内表面": 0.5, "型芯孔": 0.5}
        },
        thermal_conductivity=52,
        specific_heat=544,
        thermal_expansion=10.5e-6,
        tensile_strength=250,
        yield_strength=0,
        elongation=0,
        hardness=190,
        notes="常用灰铸铁，良好的铸造性能和减震性能"
    ),
    "ZG270-500": MaterialProperties(
        material_type=MaterialType.STEEL,
        material_code="ZG270-500",
        material_name="铸钢ZG270-500",
        density=7.85,
        melting_point=1500,
        pouring_temperature=1580,
        solidus_temperature=1490,
        liquidus_temperature=1500,
        linear_shrinkage=2.0,
        volume_shrinkage=6.0,
        min_wall_thickness={
            CastingProcess.SAND_CASTING: 5.0,
            CastingProcess.INVESTMENT_CASTING: 2.5
        },
        recommended_draft_angle={
            CastingProcess.SAND_CASTING: {"外表面": 2.0, "内表面": 2.5, "型芯孔": 3.0},
            CastingProcess.INVESTMENT_CASTING: {"外表面": 0.5, "内表面": 0.5, "型芯孔": 0.5}
        },
        thermal_conductivity=46,
        specific_heat=460,
        thermal_expansion=12.0e-6,
        tensile_strength=500,
        yield_strength=270,
        elongation=18,
        hardness=140,
        notes="通用铸钢，良好的综合机械性能"
    )
}


def get_material(material_code: str) -> Optional[MaterialProperties]:
    """从数据库获取材料属性"""
    return MATERIAL_DATABASE.get(material_code)


def list_available_materials() -> List[str]:
    """列出所有可用材料代码"""
    return list(MATERIAL_DATABASE.keys())


if __name__ == "__main__":
    # 测试代码
    print("铸造数据模型定义加载成功！")
    print(f"可用材料: {list_available_materials()}")
    
    # 测试材料查询
    material = get_material("A356")
    if material:
        print(f"\\n材料 {material.material_name} 属性:")
        print(f"  密度: {material.density} g/cm³")
        print(f"  浇注温度: {material.pouring_temperature} °C")
        print(f"  线收缩率: {material.linear_shrinkage}%")
