"""
================================================================================
铸造工艺规则引擎实现 (Casting Process Rules Engine)
================================================================================
版本: 1.0
日期: 2024年
"""

from typing import List, Dict, Optional, Tuple, Callable
from dataclasses import dataclass
import numpy as np
import json

# 导入数据模型
from casting_data_models import (
    CastingPart, PartingSurface, QualityReport, QualityCheckItem,
    CheckStatus, CastingProcess, Point3D, Vector3D
)


class DraftAngleRuleEngine:
    """拔模斜度规则引擎"""
    
    # 默认拔模斜度表 (度)
    DEFAULT_DRAFT_TABLE = {
        "sand_casting": {
            "external": {
                (0, 20): (0.5, 1.0),
                (20, 50): (1.0, 1.5),
                (50, 100): (1.5, 2.0),
                (100, 200): (2.0, 2.5),
                (200, float('inf')): (2.5, 3.0)
            },
            "internal": {
                (0, 20): (1.0, 1.5),
                (20, 50): (1.5, 2.0),
                (50, 100): (2.0, 2.5),
                (100, 200): (2.5, 3.0),
                (200, float('inf')): (3.0, 4.0)
            },
            "core_hole": {
                (0, 20): (1.5, 2.0),
                (20, 50): (2.0, 2.5),
                (50, 100): (2.5, 3.0),
                (100, 200): (3.0, 4.0),
                (200, float('inf')): (4.0, 5.0)
            }
        },
        "die_casting": {
            "external": {
                (0, 10): (0.25, 0.5),
                (10, 30): (0.5, 1.0),
                (30, 60): (1.0, 1.5),
                (60, float('inf')): (1.5, 2.0)
            },
            "internal": {
                (0, 10): (0.5, 1.0),
                (10, 30): (1.0, 1.5),
                (30, 60): (1.5, 2.0),
                (60, float('inf')): (2.0, 2.5)
            },
            "core_hole": {
                (0, 10): (1.0, 1.5),
                (10, 30): (1.5, 2.0),
                (30, 60): (2.0, 2.5),
                (60, float('inf')): (2.5, 3.0)
            }
        },
        "investment_casting": {
            "external": {(0, float('inf')): (0.0, 0.5)},
            "internal": {(0, float('inf')): (0.0, 0.5)},
            "core_hole": {(0, float('inf')): (0.0, 0.5)}
        }
    }
    
    def __init__(self, custom_rules: Optional[Dict] = None):
        self.rules = custom_rules or self.DEFAULT_DRAFT_TABLE
    
    def get_recommended_draft(self, process: str, surface_type: str, 
                              height_mm: float) -> Tuple[float, float, float]:
        """
        获取推荐拔模角度
        Returns: (min_angle, max_angle, recommended_angle)
        """
        process_rules = self.rules.get(process, self.rules["sand_casting"])
        surface_rules = process_rules.get(surface_type, process_rules["external"])
        
        for (h_min, h_max), (a_min, a_max) in surface_rules.items():
            if h_min <= height_mm < h_max:
                return (a_min, a_max, (a_min + a_max) / 2)
        
        # 默认返回值
        return (1.0, 2.0, 1.5)
    
    def check_draft_angle(self, actual_angle: float, process: str, 
                          surface_type: str, height_mm: float) -> Dict:
        """检查拔模角度是否合适"""
        min_angle, max_angle, recommended = self.get_recommended_draft(
            process, surface_type, height_mm
        )
        
        status = "PASS"
        issues = []
        
        if actual_angle < min_angle:
            status = "FAIL"
            issues.append(f"拔模角度不足: {actual_angle:.2f}° < 最小值 {min_angle:.2f}°")
        elif actual_angle > max_angle * 1.5:
            status = "WARNING"
            issues.append(f"拔模角度过大: {actual_angle:.2f}° > 推荐最大值 {max_angle:.2f}°")
        
        return {
            "status": status,
            "actual_angle": actual_angle,
            "recommended_range": (min_angle, max_angle),
            "recommended_value": recommended,
            "deviation": actual_angle - recommended,
            "issues": issues
        }


class FilletRuleEngine:
    """圆角规则引擎"""
    
    # 接头类型系数
    JOINT_COEFFICIENTS = {
        "L_JOINT": {"outer": 1/3, "inner": 1/2},
        "T_JOINT": {"outer": 1/2, "inner": 2/3},
        "X_JOINT": {"outer": 2/3, "inner": 1.0},
        "Y_JOINT": {"outer": 1/2, "inner": 2/3}
    }
    
    def __init__(self, min_radius: float = 1.5, max_radius_ratio: float = 1.0):
        self.min_radius = min_radius
        self.max_radius_ratio = max_radius_ratio
    
    def calculate_recommended_radius(self, wall_thickness: float, 
                                     joint_type: str = "L_JOINT",
                                     fillet_type: str = "inner") -> float:
        """计算推荐圆角半径"""
        coeff = self.JOINT_COEFFICIENTS.get(joint_type, self.JOINT_COEFFICIENTS["L_JOINT"])
        ratio = coeff.get(fillet_type, 0.5)
        
        recommended = wall_thickness * ratio
        return max(recommended, self.min_radius)
    
    def calculate_recommended_radius_for_walls(self, wall1_thickness: float,
                                                wall2_thickness: float,
                                                joint_type: str = "L_JOINT",
                                                fillet_type: str = "inner") -> float:
        """根据两个壁厚计算推荐圆角半径"""
        avg_thickness = (wall1_thickness + wall2_thickness) / 2
        return self.calculate_recommended_radius(avg_thickness, joint_type, fillet_type)
    
    def check_fillet_radius(self, actual_radius: float, wall_thickness: float,
                            joint_type: str = "L_JOINT", 
                            fillet_type: str = "inner") -> Dict:
        """检查圆角半径是否合适"""
        recommended = self.calculate_recommended_radius(wall_thickness, joint_type, fillet_type)
        max_allowed = wall_thickness * self.max_radius_ratio
        
        status = "PASS"
        issues = []
        
        if actual_radius < self.min_radius:
            status = "FAIL"
            issues.append(f"圆角半径过小: {actual_radius:.2f}mm < 最小值 {self.min_radius}mm")
        elif actual_radius < recommended * 0.8:
            status = "WARNING"
            issues.append(f"圆角半径偏小: {actual_radius:.2f}mm < 推荐值 {recommended:.2f}mm")
        elif actual_radius > max_allowed:
            status = "WARNING"
            issues.append(f"圆角半径过大: {actual_radius:.2f}mm > 最大值 {max_allowed:.2f}mm")
        
        return {
            "status": status,
            "actual_radius": actual_radius,
            "recommended_radius": recommended,
            "min_radius": self.min_radius,
            "max_radius": max_allowed,
            "deviation_ratio": actual_radius / recommended if recommended > 0 else 0,
            "issues": issues
        }


class WallThicknessRuleEngine:
    """壁厚规则引擎"""
    
    # 最小壁厚表 (mm)
    MIN_WALL_THICKNESS = {
        "aluminum_alloy": {
            "sand_casting": 3.0,
            "die_casting": 1.0,
            "investment_casting": 1.5
        },
        "zinc_alloy": {
            "sand_casting": 2.0,
            "die_casting": 0.8,
            "investment_casting": 1.0
        },
        "magnesium_alloy": {
            "sand_casting": 3.0,
            "die_casting": 1.0,
            "investment_casting": 1.5
        },
        "gray_iron": {
            "sand_casting": 4.0,
            "investment_casting": 2.0
        },
        "ductile_iron": {
            "sand_casting": 4.0,
            "investment_casting": 2.0
        },
        "steel": {
            "sand_casting": 5.0,
            "investment_casting": 2.5
        },
        "copper_alloy": {
            "sand_casting": 3.0,
            "die_casting": 1.5,
            "investment_casting": 1.5
        }
    }
    
    def __init__(self, max_thickness_ratio: float = 2.0):
        self.max_thickness_ratio = max_thickness_ratio
    
    def get_min_wall_thickness(self, material: str, process: str) -> float:
        """获取最小壁厚要求"""
        material_rules = self.MIN_WALL_THICKNESS.get(material, 
                                                      self.MIN_WALL_THICKNESS["aluminum_alloy"])
        return material_rules.get(process, 3.0)
    
    def check_wall_thickness(self, thickness: float, material: str, 
                             process: str) -> Dict:
        """检查壁厚是否合适"""
        min_required = self.get_min_wall_thickness(material, process)
        
        status = "PASS"
        issues = []
        
        if thickness < min_required:
            status = "FAIL"
            issues.append(f"壁厚不足: {thickness:.2f}mm < 最小值 {min_required}mm")
        elif thickness < min_required * 1.2:
            status = "WARNING"
            issues.append(f"壁厚偏小: {thickness:.2f}mm 接近最小值 {min_required}mm")
        
        return {
            "status": status,
            "actual_thickness": thickness,
            "min_required": min_required,
            "recommended": min_required * 1.5,
            "issues": issues
        }
    
    def check_thickness_uniformity(self, thicknesses: List[float]) -> Dict:
        """检查壁厚均匀性"""
        if not thicknesses or len(thicknesses) < 2:
            return {"status": "PASS", "uniformity_ratio": 1.0, "issues": []}
        
        min_thick = min(thicknesses)
        max_thick = max(thicknesses)
        avg_thick = sum(thicknesses) / len(thicknesses)
        
        ratio = max_thick / min_thick if min_thick > 0 else float('inf')
        
        status = "PASS"
        issues = []
        
        if ratio > self.max_thickness_ratio:
            status = "FAIL"
            issues.append(f"壁厚变化过大: 比值 {ratio:.2f} > 允许值 {self.max_thickness_ratio}")
        elif ratio > self.max_thickness_ratio * 0.75:
            status = "WARNING"
            issues.append(f"壁厚变化较大: 比值 {ratio:.2f}")
        
        return {
            "status": status,
            "min_thickness": min_thick,
            "max_thickness": max_thick,
            "avg_thickness": avg_thick,
            "uniformity_ratio": ratio,
            "issues": issues
        }


class PartingLineRuleEngine:
    """分型面规则引擎"""
    
    def __init__(self):
        self.optimization_weights = {
            "flatness": 0.3,
            "simplicity": 0.25,
            "draft_compliance": 0.25,
            "machining_avoidance": 0.2
        }
    
    def evaluate_parting_surface(self, part: CastingPart, 
                                  surface: PartingSurface) -> Dict:
        """评估分型面设计"""
        scores = {}
        issues = []
        
        # 1. 平面度评分
        if surface.is_flat:
            scores["flatness"] = 1.0
        else:
            scores["flatness"] = 0.5
            issues.append("分型面不是平面，可能增加模具成本")
        
        # 2. 简洁度评分
        if not surface.is_complex:
            scores["simplicity"] = 1.0
        else:
            scores["simplicity"] = 0.6
            issues.append("分型面形状复杂")
        
        # 3. 拔模合规性评分
        if surface.draft_check_passed:
            scores["draft_compliance"] = 1.0
        else:
            scores["draft_compliance"] = 0.3
            issues.append("分型面存在拔模问题")
        
        # 4. 倒扣检测
        if surface.undercut_detected:
            scores["draft_compliance"] = 0.0
            issues.append(f"检测到 {len(surface.undercut_areas)} 处倒扣")
        
        # 计算总分
        total_score = sum(scores.get(k, 0) * self.optimization_weights.get(k, 0) 
                         for k in self.optimization_weights.keys())
        
        return {
            "overall_score": total_score,
            "detail_scores": scores,
            "issues": issues,
            "is_acceptable": total_score >= 0.7
        }
    
    def suggest_parting_surface(self, part: CastingPart) -> List[Dict]:
        """推荐分型面位置"""
        suggestions = []
        
        bbox = part.bounding_box
        center_z = (bbox[0].z + bbox[1].z) / 2
        
        # 建议1: 中间分型
        suggestions.append({
            "type": "mid_height",
            "position": center_z,
            "reason": "位于零件中间高度，适合铸钢/铸铁",
            "confidence": 0.8
        })
        
        # 建议2: 低分型（铝合金推荐）
        if part.material and "aluminum" in part.material.material_type.value.lower():
            low_z = bbox[0].z + (bbox[1].z - bbox[0].z) * 0.3
            suggestions.append({
                "type": "low_position",
                "position": low_z,
                "reason": "低分型有利于铝合金补缩",
                "confidence": 0.9
            })
        
        return suggestions


class QualityCheckEngine:
    """质量检查引擎"""
    
    def __init__(self):
        self.draft_engine = DraftAngleRuleEngine()
        self.fillet_engine = FilletRuleEngine()
        self.wall_engine = WallThicknessRuleEngine()
        self.parting_engine = PartingLineRuleEngine()
        
        self.check_functions = {
            "draft_angle": self._check_draft_angles,
            "fillet_radius": self._check_fillet_radii,
            "wall_thickness": self._check_wall_thicknesses,
            "thickness_uniformity": self._check_thickness_uniformity,
            "parting_surface": self._check_parting_surface,
            "hot_spot": self._check_hot_spots
        }
    
    def run_all_checks(self, part: CastingPart) -> QualityReport:
        """运行所有质量检查"""
        from datetime import datetime
        
        report = QualityReport(
            report_id=f"QR_{part.part_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            part_id=part.part_id
        )
        
        for check_name, check_func in self.check_functions.items():
            try:
                check_items = check_func(part)
                report.check_items.extend(check_items)
            except Exception as e:
                print(f"检查 {check_name} 失败: {e}")
        
        # 统计结果
        report.total_checks = len(report.check_items)
        report.passed_checks = sum(1 for item in report.check_items 
                                   if item.status == CheckStatus.PASS)
        report.failed_checks = sum(1 for item in report.check_items 
                                   if item.status == CheckStatus.FAIL)
        report.warning_checks = sum(1 for item in report.check_items 
                                    if item.status == CheckStatus.WARNING)
        
        # 计算综合评分
        if report.total_checks > 0:
            report.overall_score = (report.passed_checks * 100 + 
                                   report.warning_checks * 50) / report.total_checks
        
        # 评级
        if report.overall_score >= 90:
            report.manufacturability_rating = "优秀"
        elif report.overall_score >= 75:
            report.manufacturability_rating = "良好"
        elif report.overall_score >= 60:
            report.manufacturability_rating = "一般"
        else:
            report.manufacturability_rating = "差"
        
        return report
    
    def _check_draft_angles(self, part: CastingPart) -> List[QualityCheckItem]:
        """检查拔模斜度"""
        items = []
        process = part.casting_process.value.lower().replace(" ", "_")
        
        for draft in part.draft_features:
            result = self.draft_engine.check_draft_angle(
                draft.draft_angle,
                process,
                draft.surface_type.value.lower().replace(" ", "_"),
                draft.surface_height
            )
            
            item = QualityCheckItem(
                check_id=f"DRAFT_{draft.feature_id}",
                check_name=f"拔模斜度检查 - {draft.feature_id}",
                check_category="拔模斜度",
                status=CheckStatus(result["status"]),
                actual_value=draft.draft_angle,
                target_value=result["recommended_value"],
                affected_features=[draft.feature_id],
                description=f"表面类型: {draft.surface_type.value}",
                suggestion="; ".join(result["issues"]) if result["issues"] else "符合要求"
            )
            items.append(item)
        
        return items
    
    def _check_fillet_radii(self, part: CastingPart) -> List[QualityCheckItem]:
        """检查圆角半径"""
        items = []
        
        for fillet in part.fillet_features:
            avg_thickness = (fillet.wall1_thickness + fillet.wall2_thickness) / 2
            result = self.fillet_engine.check_fillet_radius(
                fillet.radius,
                avg_thickness,
                "L_JOINT",  # 简化处理
                "inner" if fillet.fillet_type == "内圆角" else "outer"
            )
            
            item = QualityCheckItem(
                check_id=f"FILLET_{fillet.feature_id}",
                check_name=f"圆角检查 - {fillet.feature_id}",
                check_category="圆角",
                status=CheckStatus(result["status"]),
                actual_value=fillet.radius,
                target_value=result["recommended_radius"],
                affected_features=[fillet.feature_id, fillet.wall1_id, fillet.wall2_id],
                description=f"圆角类型: {fillet.fillet_type}",
                suggestion="; ".join(result["issues"]) if result["issues"] else "符合要求"
            )
            items.append(item)
        
        return items
    
    def _check_wall_thicknesses(self, part: CastingPart) -> List[QualityCheckItem]:
        """检查壁厚"""
        items = []
        material = part.material.material_type.value.lower().replace(" ", "_") if part.material else "aluminum_alloy"
        process = part.casting_process.value.lower().replace(" ", "_")
        
        for wall in part.wall_features:
            result = self.wall_engine.check_wall_thickness(
                wall.thickness, material, process
            )
            
            item = QualityCheckItem(
                check_id=f"WALL_{wall.feature_id}",
                check_name=f"壁厚检查 - {wall.feature_id}",
                check_category="壁厚",
                status=CheckStatus(result["status"]),
                actual_value=wall.thickness,
                target_value=result["recommended"],
                affected_features=[wall.feature_id],
                description=f"标称壁厚: {wall.nominal_thickness}mm",
                suggestion="; ".join(result["issues"]) if result["issues"] else "符合要求"
            )
            items.append(item)
        
        return items
    
    def _check_thickness_uniformity(self, part: CastingPart) -> List[QualityCheckItem]:
        """检查壁厚均匀性"""
        items = []
        
        thicknesses = [w.thickness for w in part.wall_features]
        if thicknesses:
            result = self.wall_engine.check_thickness_uniformity(thicknesses)
            
            item = QualityCheckItem(
                check_id="WALL_UNIFORMITY",
                check_name="壁厚均匀性检查",
                check_category="壁厚均匀性",
                status=CheckStatus(result["status"]),
                actual_value=result["uniformity_ratio"],
                target_value=2.0,
                affected_features=[w.feature_id for w in part.wall_features],
                description=f"最小: {result['min_thickness']:.2f}mm, 最大: {result['max_thickness']:.2f}mm",
                suggestion="; ".join(result["issues"]) if result["issues"] else "壁厚均匀性良好"
            )
            items.append(item)
        
        return items
    
    def _check_parting_surface(self, part: CastingPart) -> List[QualityCheckItem]:
        """检查分型面"""
        items = []
        
        if part.parting_surface:
            result = self.parting_engine.evaluate_parting_surface(part, part.parting_surface)
            
            status = CheckStatus.PASS if result["is_acceptable"] else CheckStatus.WARNING
            
            item = QualityCheckItem(
                check_id="PARTING_SURFACE",
                check_name="分型面设计检查",
                check_category="分型面",
                status=status,
                actual_value=result["overall_score"],
                target_value=0.7,
                affected_features=["parting_surface"],
                description=f"综合评分: {result['overall_score']:.2f}",
                suggestion="; ".join(result["issues"]) if result["issues"] else "分型面设计合理"
            )
            items.append(item)
        
        return items
    
    def _check_hot_spots(self, part: CastingPart) -> List[QualityCheckItem]:
        """检查热点区域"""
        items = []
        
        # 识别热点区域（接头处）
        hot_spot_joints = [j for j in part.joint_features if j.is_hot_spot]
        
        if hot_spot_joints:
            for joint in hot_spot_joints:
                item = QualityCheckItem(
                    check_id=f"HOTSPOT_{joint.feature_id}",
                    check_name=f"热点检查 - {joint.feature_id}",
                    check_category="热点分析",
                    status=CheckStatus.WARNING,
                    actual_value=joint.hot_spot_risk_level,
                    target_value="低",
                    affected_features=joint.connected_walls,
                    description=f"接头类型: {joint.joint_type.value}",
                    suggestion=f"建议在接头处增加冒口或冷铁，风险等级: {joint.hot_spot_risk_level}"
                )
                items.append(item)
        
        return items


# ==============================================================================
# 工艺规则配置管理器
# ==============================================================================

class ProcessRulesConfigManager:
    """工艺规则配置管理器"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file
        self.config = self._load_default_config()
        if config_file:
            self.load_config(config_file)
    
    def _load_default_config(self) -> Dict:
        """加载默认配置"""
        return {
            "version": "1.0",
            "draft_angle_rules": DraftAngleRuleEngine.DEFAULT_DRAFT_TABLE,
            "fillet_rules": {
                "min_radius": 1.5,
                "max_radius_ratio": 1.0,
                "joint_coefficients": FilletRuleEngine.JOINT_COEFFICIENTS
            },
            "wall_thickness_rules": WallThicknessRuleEngine.MIN_WALL_THICKNESS,
            "thickness_uniformity": {
                "max_ratio": 2.0
            }
        }
    
    def load_config(self, file_path: str) -> bool:
        """从文件加载配置"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                self.config.update(loaded_config)
            return True
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            return False
    
    def save_config(self, file_path: str) -> bool:
        """保存配置到文件"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False
    
    def get_rule(self, rule_path: str, default=None):
        """获取规则值"""
        keys = rule_path.split('.')
        value = self.config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key, default)
            else:
                return default
        return value
    
    def set_rule(self, rule_path: str, value) -> bool:
        """设置规则值"""
        keys = rule_path.split('.')
        config = self.config
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        config[keys[-1]] = value
        return True


# ==============================================================================
# 铸造工艺推荐器
# ==============================================================================

class CastingProcessRecommender:
    """铸造工艺推荐器"""
    
    def __init__(self):
        self.process_rules = {
            CastingProcess.SAND_CASTING: {
                "min_quantity": 1,
                "max_quantity": 10000,
                "min_wall_thickness": 3.0,
                "surface_finish": "Ra 6.3-25",
                "tolerance": "CT9-CT11",
                "suitable_materials": ["铝合金", "铸铁", "铸钢", "铜合金"],
                "cost_level": "低",
                "lead_time": "短"
            },
            CastingProcess.DIE_CASTING: {
                "min_quantity": 1000,
                "max_quantity": 1000000,
                "min_wall_thickness": 0.8,
                "surface_finish": "Ra 1.6-6.3",
                "tolerance": "CT4-CT7",
                "suitable_materials": ["铝合金", "锌合金", "镁合金"],
                "cost_level": "高（模具）",
                "lead_time": "长（模具制造）"
            },
            CastingProcess.INVESTMENT_CASTING: {
                "min_quantity": 10,
                "max_quantity": 10000,
                "min_wall_thickness": 1.5,
                "surface_finish": "Ra 1.6-6.3",
                "tolerance": "CT4-CT7",
                "suitable_materials": ["所有金属"],
                "cost_level": "中",
                "lead_time": "中"
            },
            CastingProcess.CENTRIFUGAL_CASTING: {
                "min_quantity": 1,
                "max_quantity": 1000,
                "min_wall_thickness": 5.0,
                "surface_finish": "Ra 3.2-12.5",
                "tolerance": "CT8-CT10",
                "suitable_materials": ["铸铁", "铸钢", "铜合金"],
                "cost_level": "中",
                "lead_time": "短"
            }
        }
    
    def recommend_process(self, part: CastingPart, quantity: int = 100) -> List[Dict]:
        """推荐适合的铸造工艺"""
        recommendations = []
        
        avg_wall_thickness = part.get_average_wall_thickness()
        material_type = part.material.material_type.value if part.material else "未知"
        
        for process, rules in self.process_rules.items():
            score = 0
            reasons = []
            
            # 数量匹配
            if rules["min_quantity"] <= quantity <= rules["max_quantity"]:
                score += 30
            else:
                reasons.append(f"数量 {quantity} 不在推荐范围 [{rules['min_quantity']}-{rules['max_quantity']}]")
            
            # 壁厚匹配
            if avg_wall_thickness >= rules["min_wall_thickness"]:
                score += 25
            else:
                reasons.append(f"壁厚 {avg_wall_thickness:.2f}mm 小于最小值 {rules['min_wall_thickness']}mm")
            
            # 材料匹配
            if material_type in rules["suitable_materials"] or "所有金属" in rules["suitable_materials"]:
                score += 25
            else:
                reasons.append(f"材料 {material_type} 不在推荐列表中")
            
            # 尺寸匹配（简化处理）
            max_dim = max(part.overall_dimensions)
            if max_dim < 500:  # 假设小于500mm适合大多数工艺
                score += 20
            
            recommendations.append({
                "process": process.value,
                "score": score,
                "confidence": "高" if score >= 80 else "中" if score >= 60 else "低",
                "surface_finish": rules["surface_finish"],
                "tolerance": rules["tolerance"],
                "cost_level": rules["cost_level"],
                "lead_time": rules["lead_time"],
                "issues": reasons if reasons else ["无明显问题"]
            })
        
        # 按分数排序
        recommendations.sort(key=lambda x: x["score"], reverse=True)
        return recommendations


if __name__ == "__main__":
    # 测试代码
    print("铸造工艺规则引擎加载成功！")
    
    # 测试拔模角度规则
    draft_engine = DraftAngleRuleEngine()
    result = draft_engine.get_recommended_draft("sand_casting", "external", 50)
    print(f"\\n砂型铸造外表面50mm高度推荐拔模角度: {result}")
    
    # 测试圆角规则
    fillet_engine = FilletRuleEngine()
    radius = fillet_engine.calculate_recommended_radius(5.0, "T_JOINT", "inner")
    print(f"5mm壁厚T型接头内圆角推荐半径: {radius:.2f}mm")
    
    # 测试壁厚规则
    wall_engine = WallThicknessRuleEngine()
    min_thick = wall_engine.get_min_wall_thickness("aluminum_alloy", "sand_casting")
    print(f"铝合金砂型铸造最小壁厚: {min_thick}mm")
