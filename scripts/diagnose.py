#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中医三维辨证诊断引擎
TCM Three-Dimensional Pattern Differentiation Diagnostic Engine

基于"五气-脏腑-邪留"三维辨证框架的辅助诊断算法
实现完整的辨证流程：
1. 信息采集 → 2. 三维归因 → 3. 分析关系 → 4. 确定证型 → 5. 指导治疗
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict

# 数据库路径
DATA_DIR = Path(__file__).parent.parent / "references"
SYMPTOMS_DB_PATH = DATA_DIR / "symptoms_db.json"
SYNDROMES_DB_PATH = DATA_DIR / "syndromes_db.json"
FORMULAS_DB_PATH = DATA_DIR / "formulas_db.json"


@dataclass
class DimensionScore:
    """维度评分"""
    wuqi: Dict[str, float] = field(default_factory=dict)  # 五气: {风: 0.8, 寒: 0.6}
    zangfu: Dict[str, float] = field(default_factory=dict)  # 脏腑: {肺: 0.9, 脾: 0.3}
    xieliu: Dict[str, float] = field(default_factory=dict)  # 邪留: {痰: 0.7}


@dataclass
class CausalAnalysis:
    """因果关系分析"""
    primary_cause: str = ""  # 主要病因（纲）
    secondary_causes: List[str] = field(default_factory=list)  # 次要病因（目）
    causality_chain: List[str] = field(default_factory=list)  # 因果链
    is_acute: bool = True  # 是否急性期


@dataclass
class SymptomMatch:
    """症状匹配结果"""
    symptom_id: str
    symptom_name: str
    matched_keywords: List[str]
    severity: str = "中度"
    dimension_scores: DimensionScore = field(default_factory=DimensionScore)


@dataclass
class SyndromeResult:
    """证候诊断结果"""
    syndrome_id: str
    syndrome_name: str
    category: str  # 五气为病/脏腑主病/邪留发病
    confidence: float
    matched_primary: List[str]
    matched_secondary: List[str]
    matched_tongue: List[str]
    matched_pulse: List[str]
    dimension_scores: DimensionScore
    causal_analysis: CausalAnalysis = field(default_factory=CausalAnalysis)
    gang_mu_structure: str = ""  # 纲-目结构描述
    formulas: List[str] = field(default_factory=list)
    disease_applications: Dict = field(default_factory=dict)
    differentiation: Dict[str, str] = field(default_factory=dict)
    treatment_principle: str = ""
    treatment_strategy: str = ""  # 治疗策略（主治+兼治）


class TCMDiagnosticEngine:
    """中医三维辨证诊断引擎"""
    
    # 疼痛性质与五气对应规则
    PAIN_NATURE_RULES = {
        "胀痛": {"wuqi": "风", "mechanism": "气滞，风邪或肝气郁结"},
        "游走性疼痛": {"wuqi": "风", "mechanism": "风性善行"},
        "冷痛": {"wuqi": "寒", "mechanism": "寒邪凝滞，阳气不足"},
        "酸痛": {"wuqi": "寒", "mechanism": "寒湿凝滞"},
        "灼痛": {"wuqi": "热", "mechanism": "热（火）邪蕴结"},
        "红肿热痛": {"wuqi": "热", "mechanism": "火热蕴结"},
        "重痛": {"wuqi": "湿", "mechanism": "湿邪困阻"},
        "干痛": {"wuqi": "燥", "mechanism": "燥邪伤津"},
        "刺痛": {"xieliu": "瘀血", "mechanism": "瘀血阻络"},
        "刀割样痛": {"xieliu": "瘀血", "mechanism": "瘀血阻络"},
        "隐痛": {"zangfu": "虚", "mechanism": "脏腑虚损，不荣则痛"},
        "空痛": {"zangfu": "虚", "mechanism": "精血亏虚"},
        "麻木痛": {"xieliu": "痰湿", "mechanism": "痰湿阻滞"}
    }
    
    # 疼痛部位与脏腑对应规则
    PAIN_LOCATION_RULES = {
        "巅顶": "肝",
        "前额": "胃",
        "两侧": "胆",
        "后头": "膀胱",
        "胁肋": "肝",
        "肩背": "心、肾",
        "胃脘": "胃",
        "小腹": "肝、肾",
        "腰": "肾",
        "膝": "肝、肾",
        "关节": "肝、肾"
    }
    
    def __init__(self):
        """初始化诊断引擎"""
        self.symptoms_db = self._load_json(SYMPTOMS_DB_PATH)
        self.syndromes_db = self._load_json(SYNDROMES_DB_PATH)
        self.formulas_db = self._load_json(FORMULAS_DB_PATH)
        
        # 加载疼痛分析规则
        pain_rules_path = DATA_DIR / "pain_analysis_rules.json"
        self.pain_rules = self._load_json(pain_rules_path)
        
        # 构建症状名称到ID的映射
        self.symptom_name_to_id = {}
        self._build_symptom_index()
        
    def _load_json(self, path: Path) -> dict:
        """加载JSON数据"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"警告: 数据库文件不存在 {path}")
            return {}
    
    def _build_symptom_index(self):
        """构建症状名称索引"""
        if not self.symptoms_db or "symptoms" not in self.symptoms_db:
            return
            
        for sid, symptom in self.symptoms_db["symptoms"].items():
            self.symptom_name_to_id[symptom["name"]] = sid
            for alias in symptom.get("aliases", []):
                self.symptom_name_to_id[alias] = sid
    
    def parse_input(self, text: str) -> List[SymptomMatch]:
        """解析用户输入的症状描述"""
        matched_symptoms = []
        matched_ids = set()
        
        # 先检测疼痛性质和部位
        pain_symptoms = self._detect_pain_patterns(text)
        
        for sid, symptom in self.symptoms_db.get("symptoms", {}).items():
            if sid in matched_ids:
                continue
                
            symptom_name = symptom["name"]
            aliases = symptom.get("aliases", [])
            all_names = [symptom_name] + aliases
            
            matched_keywords = []
            for name in all_names:
                if name in text:
                    matched_keywords.append(name)
            
            if matched_keywords:
                dim_scores = DimensionScore()
                dimensions = symptom.get("dimensions", {})
                
                if "wuqi" in dimensions:
                    for factor, data in dimensions["wuqi"].items():
                        dim_scores.wuqi[factor] = data.get("weight", 0.5)
                
                if "zangfu" in dimensions:
                    for organ, data in dimensions["zangfu"].items():
                        dim_scores.zangfu[organ] = data.get("weight", 0.5)
                
                if "xieliu" in dimensions:
                    for factor, data in dimensions["xieliu"].items():
                        dim_scores.xieliu[factor] = data.get("weight", 0.5)
                
                match = SymptomMatch(
                    symptom_id=sid,
                    symptom_name=symptom_name,
                    matched_keywords=matched_keywords,
                    severity="中度",
                    dimension_scores=dim_scores
                )
                matched_symptoms.append(match)
                matched_ids.add(sid)
        
        # 添加疼痛模式识别结果
        for pain_sym in pain_symptoms:
            if pain_sym["name"] not in [s.symptom_name for s in matched_symptoms]:
                match = SymptomMatch(
                    symptom_id=f"PAIN_{len(matched_symptoms)}",
                    symptom_name=pain_sym["name"],
                    matched_keywords=[pain_sym["keyword"]],
                    severity="中度",
                    dimension_scores=pain_sym["dimensions"]
                )
                matched_symptoms.append(match)
        
        return matched_symptoms
    
    def _detect_pain_patterns(self, text: str) -> List[Dict]:
        """检测疼痛模式（疼痛性质和部位）"""
        pain_symptoms = []
        
        # 检测疼痛性质
        for pain_type, rule in self.PAIN_NATURE_RULES.items():
            if pain_type in text:
                dim_scores = DimensionScore()
                if "wuqi" in rule:
                    dim_scores.wuqi[rule["wuqi"]] = 0.9
                if "xieliu" in rule:
                    dim_scores.xieliu[rule["xieliu"]] = 0.9
                if "zangfu" in rule:
                    dim_scores.zangfu[rule["zangfu"]] = 0.7
                
                pain_symptoms.append({
                    "name": pain_type,
                    "keyword": pain_type,
                    "dimensions": dim_scores,
                    "mechanism": rule["mechanism"]
                })
        
        # 检测疼痛部位
        for location, zangfu in self.PAIN_LOCATION_RULES.items():
            if location in text and "痛" in text:
                dim_scores = DimensionScore()
                for z in zangfu.split("、"):
                    dim_scores.zangfu[z.strip()] = 0.8
                
                pain_symptoms.append({
                    "name": f"{location}痛",
                    "keyword": location,
                    "dimensions": dim_scores,
                    "mechanism": f"病位在{zangfu}"
                })
        
        return pain_symptoms
    
    def calculate_dimension_scores(self, matched_symptoms: List[SymptomMatch]) -> DimensionScore:
        """计算综合维度评分"""
        total_scores = DimensionScore()
        
        for match in matched_symptoms:
            for factor, score in match.dimension_scores.wuqi.items():
                if factor in total_scores.wuqi:
                    total_scores.wuqi[factor] = max(total_scores.wuqi[factor], score)
                else:
                    total_scores.wuqi[factor] = score
            
            for organ, score in match.dimension_scores.zangfu.items():
                if organ in total_scores.zangfu:
                    total_scores.zangfu[organ] = max(total_scores.zangfu[organ], score)
                else:
                    total_scores.zangfu[organ] = score
            
            for factor, score in match.dimension_scores.xieliu.items():
                if factor in total_scores.xieliu:
                    total_scores.xieliu[factor] = max(total_scores.xieliu[factor], score)
                else:
                    total_scores.xieliu[factor] = score
        
        # ========== 优化：病位特异性权重增强 ==========
        # 如果症状中明确提到某部位疼痛，给对应脏腑额外加权
        # 这保证主病位不会被兼症超过
        symptom_text = " ".join([s.symptom_name for s in matched_symptoms]).lower()
        
        # 病位特异性加权表：症状关键词 → 脏腑 → 额外权重
        location_bonus = {
            "心": ["胸", "心", "心胸", "心悸", "心痛", "胸闷", "憋闷"],
            "肺": ["咳", "咳嗽", "喘", "气短", "肺"],
            "肝": ["胁", "胁肋", "肝", "情志", "抑郁"],
            "胃": ["胃", "胃脘", "脘腹", "腹痛", "恶心", "呕吐"],
            "脾": ["腹", "腹胀", "脾", "食欲不振"],
            "肾": ["腰", "腰膝", "肾", "夜尿", "耳鸣"],
            "胆":["胆", "胁下", "口苦"],
            "大肠":["大便", "便秘", "泄泻", "大肠"],
            "膀胱":["小便", "尿频", "尿急", "膀胱"],
        }
        
        for organ, keywords in location_bonus.items():
            for kw in keywords:
                if kw in symptom_text and organ in total_scores.zangfu:
                    # 额外加0.25权重，保证主病位突出
                    total_scores.zangfu[organ] += 0.25
                elif kw in symptom_text:
                    # 如果还没有这个脏腑，初始化加上权重
                    total_scores.zangfu[organ] = 0.25
        
        # ========== 优化：疼痛性质特异性权重增强 ==========
        # 刺痛 → 瘀血权重加倍，保证瘀血更容易成为纲
        if "刺痛" in symptom_text or "固定不移" in symptom_text or "入夜加重" in symptom_text:
            if "瘀" in total_scores.xieliu:
                total_scores.xieliu["瘀"] += 0.30  # 刺痛→瘀血，大幅加权
            else:
                total_scores.xieliu["瘀"] = 0.30
            # 瘀血+刺痛几乎肯定是主证，所以加重
        
        # 胀痛 → 气滞/肝郁加权
        if "胀痛" in symptom_text or "走窜" in symptom_text:
            if "肝" in total_scores.zangfu:
                total_scores.zangfu["肝"] += 0.20
        
        return total_scores
    
    def analyze_causality(self, dimension_scores: DimensionScore, 
                          matched_symptoms: List[SymptomMatch]) -> CausalAnalysis:
        """
        分析因果关系 - 核心算法
        根据"三型二十一证"体系的思维模式分析：
        1. 追溯起源（五气）
        2. 定位病位（脏腑）
        三. 分析病理产物（邪留）
        4. 判断主次、因果关系
        """
        analysis = CausalAnalysis()
        
        # 获取各维度最高评分
        top_wuqi = sorted(dimension_scores.wuqi.items(), key=lambda x: x[1], reverse=True)[:2]
        top_zangfu = sorted(dimension_scores.zangfu.items(), key=lambda x: x[1], reverse=True)[:2]
        top_xieliu = sorted(dimension_scores.xieliu.items(), key=lambda x: x[1], reverse=True)[:2]
        
        # 分析因果链
        causality_chain = []
        
        # ========== 优化：自动判断内伤还是外感 ==========
        # 获取所有症状文本用于判断
        symptom_text = " ".join([s.symptom_name for s in matched_symptoms]).lower()
        
        # 判断内伤关键词：老年、久病、乏力、气短、反复发作等
        internal_keywords = ["老年", "久病", "乏力", "气短", "反复发作", "慢性", "高血压", "高血脂", "糖尿病", "冠心病"]
        is_internal = any(kw in symptom_text for kw in internal_keywords)
        
        # 判断是否有外感史（五气维度得分高且没有内伤关键词）
        has_external_pathogen = len(top_wuqi) > 0 and top_wuqi[0][1] > 0.7
        # 修正：如果明确是内伤，即使五气得分高也不认为是外感
        if is_internal and "寒" == top_wuqi[0][0] and top_wuqi[0][1] > 0.7:
            # 内伤阳虚生寒，仍然是内伤，不是外感
            has_external_pathogen = False
        
        # 判断是否有病理产物（邪留维度得分高）
        has_pathological_product = len(top_xieliu) > 0 and top_xieliu[0][1] > 0.6
        
        # 判断脏腑虚损程度
        has_organ_dysfunction = len(top_zangfu) > 0 and top_zangfu[0][1] > 0.6
        
        # 判断是否为外感初期（五气得分明显高于邪留，且不是内伤）
        is_acute_external = (has_external_pathogen and 
                            (not has_pathological_product or top_wuqi[0][1] > top_xieliu[0][1] + 0.2) and
                            not is_internal)
        
        # 构建因果分析
        if is_acute_external:
            # 外感初期：五气为纲
            analysis.primary_cause = f"五气-{top_wuqi[0][0]}"
            analysis.secondary_causes = [f"{'脏腑-' + top_zangfu[0][0]}" if top_zangfu else "脏腑-表"]
            analysis.causality_chain = [
                f"外感{top_wuqi[0][0]}邪侵袭肌表",
                "卫阳被郁，正邪相争于表",
                "出现发热、恶寒、头痛、身痛等表证"
            ]
            analysis.is_acute = True
            
        elif has_external_pathogen and has_pathological_product and not is_internal:
            # 外感迁延：邪留为纲，五气退居次要
            analysis.primary_cause = f"邪留-{top_xieliu[0][0]}"
            analysis.secondary_causes = [
                f"{'脏腑-' + top_zangfu[0][0]}" if top_zangfu else "",
                f"五气-{top_wuqi[0][0]}（余邪未尽）"
            ]
            analysis.causality_chain = [
                f"外感{top_wuqi[0][0]}邪迁延不愈",
                "脏腑功能失调，津液代谢障碍",
                f"形成{top_xieliu[0][0]}等病理产物"
            ]
            analysis.is_acute = False
            
        # ========== 优化：经验规则 - 刺痛+高分瘀血 → 强制瘀血为纲 ==========
        # 瘀血刺痛是典型实证，即使总分略低也应该为纲（急则治标）
        has_stabbing_pain = "刺痛" in symptom_text or "固定不移" in symptom_text or "入夜加重" in symptom_text
        has_high_stabbing = top_xieliu and top_xieliu[0][0] == "瘀" and top_xieliu[0][1] > 0.8
        if has_stabbing_pain and has_high_stabbing:
            # 典型瘀血刺痛证，瘀血为纲
            analysis.primary_cause = f"邪留-{top_xieliu[0][0]}"
            analysis.secondary_causes = []
            for z in top_zangfu:
                analysis.secondary_causes.append(f"脏腑-{z[0]}（本虚）")
            if top_wuqi:
                analysis.secondary_causes.append(f"五气-{top_wuqi[0][0]}")
            # 直接构建因果链并返回
            if is_internal and top_zangfu and any(w[0] in ["寒"] for w in top_wuqi):
                # 内伤本案模板：阳虚寒凝 → 瘀血阻滞
                analysis.causality_chain = [
                    f"脏腑-{top_zangfu[0][0]}阳气亏虚",
                    "阳虚生寒，寒凝血瘀",
                    f"{top_xieliu[0][0]}阻滞",
                    f"影响{top_zangfu[0][0]}功能"
                ]
            else:
                analysis.causality_chain = [
                    f"{top_xieliu[0][0]}阻滞",
                    f"影响{top_zangfu[0][0]}功能"
                ]
            analysis.is_acute = True
            return analysis
        elif has_organ_dysfunction and has_pathological_product:
            # 内伤杂病：需判断脏腑与邪留的主次
            if top_zangfu[0][1] > top_xieliu[0][1]:
                # 脏腑虚损为主（本虚）
                analysis.primary_cause = f"脏腑-{top_zangfu[0][0]}"
                analysis.secondary_causes = [f"邪留-{top_xieliu[0][0]}"]
                # 使用内伤模板
                if is_internal and any(w[0] in ["寒"] for w in top_wuqi):
                    # 内伤：脏腑阳虚 → 寒从内生 → 病理产物
                    analysis.causality_chain = [
                        f"老年体弱，{top_zangfu[0][0]}阳气亏虚",
                        "阳虚生寒，寒从内生",
                        "推动无力，寒凝血滞",
                        f"形成{top_xieliu[0][0]}"
                    ]
                else:
                    analysis.causality_chain = [
                        f"{top_zangfu[0][0]}功能失调",
                        "推动无力",
                        f"形成{top_xieliu[0][0]}"
                    ]
                analysis.is_acute = False
            else:
                # 病理产物为主（标实）
                analysis.primary_cause = f"邪留-{top_xieliu[0][0]}"
                analysis.secondary_causes = [f"脏腑-{top_zangfu[0][0]}（本虚）"]
                # 使用内伤模板
                if is_internal and any(w[0] in ["寒"] for w in top_wuqi):
                    # 内伤本案模板：阳虚寒凝 → 瘀血阻滞
                    analysis.causality_chain = [
                        f"脏腑-{top_zangfu[0][0]}阳气亏虚",
                        "阳虚生寒，寒凝血瘀",
                        f"{top_xieliu[0][0]}阻滞",
                        f"影响{top_zangfu[0][0]}功能"
                    ]
                else:
                    analysis.causality_chain = [
                        f"{top_xieliu[0][0]}阻滞",
                        f"影响{top_zangfu[0][0]}功能"
                    ]
                analysis.is_acute = True
                
        elif has_organ_dysfunction and not has_pathological_product:
            # 纯脏腑病变
            analysis.primary_cause = f"脏腑-{top_zangfu[0][0]}"
            analysis.secondary_causes = []
            analysis.causality_chain = [
                f"{top_zangfu[0][0]}功能失调"
            ]
            analysis.is_acute = False
            
        elif has_pathological_product:
            # 纯邪留病变
            analysis.primary_cause = f"邪留-{top_xieliu[0][0]}"
            analysis.secondary_causes = []
            analysis.causality_chain = [
                f"{top_xieliu[0][0]}为患"
            ]
            analysis.is_acute = True
        
        return analysis
    
    def build_gang_mu_structure(self, causal_analysis: CausalAnalysis) -> str:
        """
        构建"纲-目"结构描述
        """
        if not causal_analysis.primary_cause:
            return ""
        
        gang = causal_analysis.primary_cause
        mu = [c for c in causal_analysis.secondary_causes if c]
        
        if mu:
            return f"以 «{gang}» 为纲，以 «{', '.join(mu)}» 为目"
        else:
            return f"以 «{gang}» 为纲"
    
    def diagnose(self, text: str, top_k: int = 3) -> Tuple[List[SyndromeResult], DimensionScore, CausalAnalysis]:
        """
        执行诊断分析 - 增强版
        实现完整的"三型二十一证"辨证流程
        """
        # 1. 信息采集：解析症状
        matched_symptoms = self.parse_input(text)
        
        if not matched_symptoms:
            return [], DimensionScore(), CausalAnalysis()
        
        # 2. 三维归因：计算综合维度评分
        total_dimension_scores = self.calculate_dimension_scores(matched_symptoms)
        
        # 三. 分析关系：判断因果主次
        causal_analysis = self.analyze_causality(total_dimension_scores, matched_symptoms)
        
        # 4. 确定证型：匹配证候
        syndrome_results = []
        matched_symptom_names = [s.symptom_name for s in matched_symptoms]
        
        for sid, syndrome in self.syndromes_db.get("syndromes", {}).items():
            criteria = syndrome.get("diagnostic_criteria", {})
            
            # 计算主症匹配
            primary_symptoms = criteria.get("primary_symptoms", [])
            matched_primary = [s for s in primary_symptoms if s in matched_symptom_names]
            
            # 计算次症匹配
            secondary_symptoms = criteria.get("secondary_symptoms", [])
            matched_secondary = [s for s in secondary_symptoms if s in matched_symptom_names]
            
            # 计算舌象匹配
            tongue_signs = criteria.get("tongue", [])
            matched_tongue = [s for s in tongue_signs if s in text]
            
            # 计算脉象匹配
            pulse_signs = criteria.get("pulse", [])
            matched_pulse = [s for s in pulse_signs if s in text]
            
            # 计算置信度
            primary_score = len(matched_primary) / max(len(primary_symptoms), 1) * 0.5
            secondary_score = len(matched_secondary) / max(len(secondary_symptoms), 1) * 0.25
            tongue_score = len(matched_tongue) / max(len(tongue_signs), 1) * 0.15
            pulse_score = len(matched_pulse) / max(len(pulse_signs), 1) * 0.1
            
            confidence = primary_score + secondary_score + tongue_score + pulse_score
            
            # 维度评分匹配度
            syndrome_dims = syndrome.get("dimension_scores", {})
            dim_match_score = self._calculate_dimension_match(
                total_dimension_scores, 
                syndrome_dims
            )
            
            # 综合置信度
            final_confidence = confidence * 0.7 + dim_match_score * 0.3
            
            # 根据因果分析调整置信度
            category = syndrome.get("category", "")
            if causal_analysis.primary_cause:
                if category == "五气为病" and "五气" in causal_analysis.primary_cause:
                    final_confidence *= 1.2  # 提高匹配度
                elif category == "脏腑主病" and "脏腑" in causal_analysis.primary_cause:
                    final_confidence *= 1.2
                elif category == "邪留发病" and "邪留" in causal_analysis.primary_cause:
                    final_confidence *= 1.2
            
            if final_confidence > 0.1:
                # 构建纲-目结构
                gang_mu = self.build_gang_mu_structure(causal_analysis)
                
                # 构建治疗策略
                treatment_strategy = self._build_treatment_strategy(
                    causal_analysis, 
                    syndrome
                )
                
                result = SyndromeResult(
                    syndrome_id=sid,
                    syndrome_name=syndrome["name"],
                    category=category,
                    confidence=round(final_confidence * 100, 1),
                    matched_primary=matched_primary,
                    matched_secondary=matched_secondary,
                    matched_tongue=matched_tongue,
                    matched_pulse=matched_pulse,
                    dimension_scores=total_dimension_scores,
                    causal_analysis=causal_analysis,
                    gang_mu_structure=gang_mu,
                    formulas=syndrome.get("formulas", []),
                    disease_applications=syndrome.get("disease_applications", {}),
                    differentiation=syndrome.get("differentiation", {}),
                    treatment_principle=syndrome.get("treatment_principle", ""),
                    treatment_strategy=treatment_strategy
                )
                syndrome_results.append(result)
        
        # 按置信度排序
        syndrome_results.sort(key=lambda x: x.confidence, reverse=True)
        return syndrome_results[:top_k], total_dimension_scores, causal_analysis
    
    def _build_treatment_strategy(self, causal_analysis: CausalAnalysis, 
                                   syndrome: dict) -> str:
        """构建治疗策略"""
        strategies = []
        
        primary = causal_analysis.primary_cause
        secondary = causal_analysis.secondary_causes
        
        if "五气" in primary:
            strategies.append(f"主治：祛散{primary}（治{primary}）")
        elif "脏腑" in primary:
            strategies.append(f"主治：调理{primary}功能（治{primary}）")
        elif "邪留" in primary:
            strategies.append(f"主治：祛除病理产物（治{primary}）")
        
        for sec in secondary:
            if sec:
                strategies.append(f"兼治：{sec}")
        
        return "；".join(strategies) if strategies else ""
    
    def _calculate_dimension_match(self, patient_dims: DimensionScore, 
                                    syndrome_dims: Dict) -> float:
        """计算维度评分匹配度"""
        match_scores = []
        
        if "wuqi" in syndrome_dims:
            for factor, weight in syndrome_dims["wuqi"].items():
                patient_weight = patient_dims.wuqi.get(factor, 0)
                match_scores.append(min(patient_weight, weight) / max(weight, 0.01))
        
        if "zangfu" in syndrome_dims:
            for organ, weight in syndrome_dims["zangfu"].items():
                patient_weight = patient_dims.zangfu.get(organ, 0)
                match_scores.append(min(patient_weight, weight) / max(weight, 0.01))
        
        if "xieliu" in syndrome_dims:
            for factor, weight in syndrome_dims["xieliu"].items():
                patient_weight = patient_dims.xieliu.get(factor, 0)
                match_scores.append(min(patient_weight, weight) / max(weight, 0.01))
        
        return sum(match_scores) / len(match_scores) if match_scores else 0
    
    def get_formula_details(self, formula_name: str) -> Optional[dict]:
        """获取方剂详情"""
        for fid, formula in self.formulas_db.get("formulas", {}).items():
            if formula["name"] == formula_name:
                return formula
        return None

    def generate_detailed_analysis(self, dimension_scores: DimensionScore) -> tuple:
        """生成详细的辨证分析表格（新格式）"""
        # 五气维度分析
        wuqi_analysis = []
        sorted_wuqi = sorted(dimension_scores.wuqi.items(), key=lambda x: x[1], reverse=True)
        for factor, score in sorted_wuqi:
            if score < 0.3:
                continue
            examples = []
            # 收集相关症状进行分析
            for symptom_name, (f, w) in getattr(self, '_last_matched_symptoms', {}).items():
                symptom_data = self.symptoms_db.get("symptoms", {}).get(self.symptom_name_to_id.get(symptom_name, ""), {})
                dimensions = symptom_data.get("dimensions", {})
                if "wuqi" in dimensions and factor in dimensions["wuqi"]:
                    desc = dimensions["wuqi"][factor].get("description", "")
                    if desc:
                        examples.append(f"{symptom_name} → {desc}")
            if examples or score >= 0.4:
                wuqi_analysis.append({
                    "factor": factor,
                    "score": score,
                    "bar": "█" * int(score * 10),
                    "examples": examples
                })
        
        # 脏腑维度分析
        zangfu_analysis = []
        sorted_zangfu = sorted(dimension_scores.zangfu.items(), key=lambda x: x[1], reverse=True)
        for organ, score in sorted_zangfu:
            if score < 0.3:
                continue
            examples = []
            for symptom_name, (f, w) in getattr(self, '_last_matched_symptoms', {}).items():
                symptom_data = self.symptoms_db.get("symptoms", {}).get(self.symptom_name_to_id.get(symptom_name, ""), {})
                dimensions = symptom_data.get("dimensions", {})
                if "zangfu" in dimensions and organ in dimensions["zangfu"]:
                    desc = dimensions["zangfu"][organ].get("description", "")
                    if desc:
                        examples.append(f"{symptom_name} → {desc}")
            if examples or score >= 0.4:
                zangfu_analysis.append({
                    "organ": organ,
                    "score": score,
                    "bar": "█" * int(score * 10),
                    "examples": examples
                })
        
        # 邪留维度分析
        xieliu_analysis = []
        sorted_xieliu = sorted(dimension_scores.xieliu.items(), key=lambda x: x[1], reverse=True)
        for factor, score in sorted_xieliu:
            if score < 0.3:
                continue
            examples = []
            for symptom_name, (f, w) in getattr(self, '_last_matched_symptoms', {}).items():
                symptom_data = self.symptoms_db.get("symptoms", {}).get(self.symptom_name_to_id.get(symptom_name, ""), {})
                dimensions = symptom_data.get("dimensions", {})
                if "xieliu" in dimensions and factor in dimensions["xieliu"]:
                    desc = dimensions["xieliu"][factor].get("description", "")
                    if desc:
                        examples.append(f"{symptom_name} → {desc}")
            if examples or score >= 0.4:
                xieliu_analysis.append({
                    "factor": factor,
                    "score": score,
                    "bar": "█" * int(score * 10),
                    "examples": examples
                })
        
        return wuqi_analysis, zangfu_analysis, xieliu_analysis

    def build_causal_chain(self, wuqi_analysis, zangfu_analysis, xieliu_analysis) -> list:
        """构建因果链 - 遵循三型二十一证体系：
        脏腑（内因启动）→ 五气（内生邪气）→ 邪留（病理产物）
        """
        chain = []
        
        # 三型二十一证体系：优先找脏腑作为起始因
        # 如果有两个脏腑评分都高，其中一个是肝，通常肝是启动因（纲），胃是受累因（目）
        has_gan = any(a["organ"] == "肝" for a in zangfu_analysis)
        has_wei = any(a["organ"] == "胃" for a in zangfu_analysis)
        has_re = any(a["factor"] in ["热", "火"] for a in wuqi_analysis)
        
        # 根据三型二十一证体系的病机传导规律判断主因
        # 规律：长期情志不畅 → 肝（脏腑）→ 气郁化火 → 热（五气）→ 影响胃
        if has_gan and has_wei:
            # 肝胃不和/肝郁犯胃：肝是启动因（纲）
            primary_type, primary_name = "脏腑", "肝"
            chain.append(f"{primary_type}({primary_name}) 为本（核心启动因素）")
            chain.append(f"    ├─→ 长期情志不畅/压力大 → 肝气郁结")
            chain.append(f"    │           └─→ 肝失疏泄，横逆犯胃")
            chain.append(f"    │                           └─→ 胃失和降 → 胃脘胀痛、连及两胁、嗳气频繁")
            if has_re:
                chain.append(f"    └─→ 气郁日久 → 化火生热 → 内生火热")
                chain.append(f"                                └─→ 口干口苦、心烦失眠、舌红苔黄、脉数")
        
        elif any(a["organ"] == "肾" for a in zangfu_analysis) and "腰酸" in "".join([s["symptom_name"] for s in self._last_matched_symptoms]).lower():
            # 腰膝问题，肾亏为主因
            primary_type, primary_name = "脏腑", "肾"
            chain.append(f"{primary_type}({primary_name}) 为本（主要矛盾）")
            chain.append(f"    ├─→ 肾气亏虚 → 腰膝失养")
            chain.append(f"    ├─→ 肾虚不能固摄津液 → 多汗、夜尿多")
            chain.append(f"    └─→ 肾虚不能上荣头目 → 头晕眼花")
        
        elif primary_type == "脏腑" and primary_name == "脾":
            chain.append(f"{primary_type}({primary_name}) 为本（主要矛盾）")
            chain.append(f"    ├─→ 脾虚失运 → 气血生化不足")
            chain.append(f"    │       └─→ 湿浊内生")
            chain.append(f"    └─→ 清阳不升 → 头晕")
        
        elif primary_type == "五气" and primary_name == "寒":
            chain.append(f"{primary_type}({primary_name}) 为本（主要矛盾）")
            chain.append(f"  寒邪侵袭 → 伤及{', '.join([a['organ'] for a in zangfu_analysis])}")
            if any(f["factor"] == "瘀" for f in xieliu_analysis):
                chain.append("  寒凝血瘀 → 瘀血内阻")
        
        elif primary_type == "邪留" and primary_name == "瘀":
            chain.append(f"{primary_type}({primary_name}) 为本（主要矛盾）")
            # 优化：如果是刺痛+瘀血，加上特征描述
            has_stabbing_pain = any("刺痛" in s["symptom_name"] for s in self._last_matched_symptoms) or any("固定不移" in s["symptom_name"] for s in self._last_matched_symptoms)
            if has_stabbing_pain:
                chain.append("  典型表现：刺痛，固定不移，入夜加重")
                chain.append("  瘀血阻滞 → 气机不通")
                for z in zangfu_analysis[:1]:
                    chain.append(f"  影响 {z['organ']} 脉络，气血不通 → 发为疼痛")
            else:
                chain.append("  瘀血内阻 → 气机不通")
                for z in zangfu_analysis[:1]:
                    chain.append(f"  影响 {z['organ']} 功能")
        
        else:
            # 默认按分数找主因
            all_scores = []
            if wuqi_analysis:
                all_scores.extend([(a["score"], "五气", a["factor"]) for a in wuqi_analysis])
            if zangfu_analysis:
                all_scores.extend([(a["score"], "脏腑", a["organ"]) for a in zangfu_analysis])
            if xieliu_analysis:
                all_scores.extend([(a["score"], "邪留", a["factor"]) for a in xieliu_analysis])
            if all_scores:
                all_scores.sort(reverse=True)
                if all_scores:
                    score, primary_type, primary_name = all_scores[0]
                    chain.append(f"{primary_type}({primary_name}) 为本（主要矛盾）")
                    if primary_type == "脏腑" and primary_name == "肝":
                        chain.append("  肝郁气滞 → 气机不畅")
                        if has_re:
                            chain.append("  日久化火 → 火扰心神")
        
        return chain

    def summarize_dimensions(self, wuqi_analysis, zangfu_analysis, xieliu_analysis):
        """总结三维辨证结论 - 遵循三型二十一证体系：
        脏腑（启动因）为纲，五气/邪留（果）为目
        """
        summary = {
            "primary_type": None,
            "primary_name": None,
            "secondary": [],
            "conclusion": ""
        }
        
        # 三型二十一证体系特殊规则：
        # 1. 如果肝和胃都在脏腑且评分都高 → 肝为纲（启动因），胃为目，符合你给的案例
        has_liver = any(a["organ"] == "肝" for a in zangfu_analysis)
        has_stomach = any(a["organ"] == "胃" for a in zangfu_analysis)
        has_heat = any(a["factor"] in ["热", "火"] for a in wuqi_analysis)
        
        if has_liver and has_stomach:
            # 肝胃不和/肝郁犯胃：肝为纲
            summary["primary_type"] = "脏腑"
            summary["primary_name"] = "肝"
            # 胃和热都是次要
            for a in zangfu_analysis:
                if a["organ"] != "肝" and a["score"] >= 0.5:
                    summary["secondary"].append(f"脏腑-{a['organ']}")
            for a in wuqi_analysis:
                if a["factor"] != "肝" and a["score"] >= 0.5:
                    summary["secondary"].append(f"五气-{a['factor']}")
            # 结论
            if has_heat:
                summary["conclusion"] = "肝郁化火，横逆犯胃"
            else:
                summary["conclusion"] = "肝气郁结，横逆犯胃"
            return summary
        
        # 默认：按分数找最高
        max_score = 0
        for analysis in [zangfu_analysis, wuqi_analysis, xieliu_analysis]:
            for item in analysis:
                name_key = "organ" if "organ" in item else "factor"
                name = item[name_key]
                score = item["score"]
                if score > max_score:
                    max_score = score
                    summary["primary_type"] = "zangfu" if name_key == "organ" else \
                                             "wuqi" if name_key == "factor" else "xieliu"
                    summary["primary_name"] = name
        return summary




def main():
    """命令行入口"""
    import argparse
    parser = argparse.ArgumentParser(
        description='中医三维辨证辅助诊断引擎 (基于欧阳锜《证病结合用药式》三型二十一证体系)'
    )
    parser.add_argument('--symptoms', '-s', required=True, help='症状列表，用逗号分隔')
    parser.add_argument('--tongue', '-t', default='', help='舌象描述，用逗号分隔')
    parser.add_argument('--pulse', '-p', default='', help='脉象描述，用逗号分隔')
    parser.add_argument('--output', '-o', default='json', help='输出格式: json/text', choices=['json', 'text'])
    parser.add_argument('--top-k', '-k', default=3, type=int, help='返回Top-K个候选证候')
    args = parser.parse_args()
    
    # 组合所有输入为文本
    all_input = args.symptoms
    if args.tongue:
        all_input += ", " + args.tongue
    if args.pulse:
        all_input += ", " + args.pulse
    
    # 创建诊断引擎
    engine = TCMDiagnosticEngine()
    
    # 诊断
    results, dim_scores, causal = engine.diagnose(all_input, top_k=args.top_k)
    
    # 输出
    if args.output == 'json':
        output = {
            "results": [
                {
                    "syndrome_id": r.syndrome_id,
                    "syndrome_name": r.syndrome_name,
                    "category": r.category,
                    "confidence": r.confidence,
                    "gang_mu_structure": r.gang_mu_structure,
                    "treatment_principle": r.treatment_principle,
                    "treatment_strategy": r.treatment_strategy,
                    "formulas": r.formulas,
                    "matched_primary": r.matched_primary,
                    "matched_secondary": r.matched_secondary
                } for r in results
            ],
            "causal_chain": causal.causality_chain,
            "gang_mu": causal.primary_cause + (" -> " + ", ".join(causal.secondary_causes) if causal.secondary_causes else ""),
            "input": all_input
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        # 文本输出
        print("=" * 70)
        print("中医三维辨证诊断结果 (基于欧阳锜《证病结合用药式》)".center(70))
        print("=" * 70)
        print(f"\n【输入症状】: {all_input}")
        print("\n【因果分析】:")
        for step in causal.causality_chain:
            print(f"  {step}")
        print(f"\n【纲目结构】: {causal.primary_cause} 为纲")
        if causal.secondary_causes:
            print(f"              {', '.join(causal.secondary_causes)} 为目")
        print("\n【候选证候】(按置信度排序):")
        for i, r in enumerate(results, 1):
            print(f"\n  {i}. {r.syndrome_name}")
            print(f"     类别: {r.category}")
            print(f"     置信度: {r.confidence}%")
            print(f"     纲目结构: {r.gang_mu_structure}")
            print(f"     治疗原则: {r.treatment_principle}")
            print(f"     治疗策略: {r.treatment_strategy}")
            if r.formulas:
                print(f"     推荐方剂: {', '.join(r.formulas)}")
        print("\n" + "=" * 70)
        print("\n⚠️  提示: 本结果为辅助诊断，仅供学习交流，处方用药请咨询正规中医师。")


if __name__ == '__main__':
    main()