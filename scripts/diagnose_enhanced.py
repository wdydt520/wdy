#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中医三型辨证诊断引擎 - 增强版
TCM Three-Type Pattern Differentiation Diagnostic Engine - Enhanced

基于"五气-脏腑-邪留"三型辨证框架的辅助诊断算法
实现"三型二十一证"体系的完整辨证流程：
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
    """中医三型辨证诊断引擎 - 增强版"""
    
    def __init__(self):
        """初始化诊断引擎"""
        self.symptoms_db = self._load_json(SYMPTOMS_DB_PATH)
        self.syndromes_db = self._load_json(SYNDROMES_DB_PATH)
        self.formulas_db = self._load_json(FORMULAS_DB_PATH)
        
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
        
        return matched_symptoms
    
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
        
        return total_scores
    
    def analyze_causality(self, dimension_scores: DimensionScore, 
                          matched_symptoms: List[SymptomMatch]) -> CausalAnalysis:
        """
        分析因果关系 - 核心算法
        根据"三型二十一证"体系的思维模式分析：
        1. 追溯起源（五气）
        2. 定位病位（脏腑）
        3. 分析病理产物（邪留）
        4. 判断主次、因果关系
        """
        analysis = CausalAnalysis()
        
        # 获取各维度最高评分
        top_wuqi = sorted(dimension_scores.wuqi.items(), key=lambda x: x[1], reverse=True)[:2]
        top_zangfu = sorted(dimension_scores.zangfu.items(), key=lambda x: x[1], reverse=True)[:2]
        top_xieliu = sorted(dimension_scores.xieliu.items(), key=lambda x: x[1], reverse=True)[:2]
        
        # 分析因果链
        causality_chain = []
        
        # 判断是否有外感史（五气维度得分高）
        has_external_pathogen = len(top_wuqi) > 0 and top_wuqi[0][1] > 0.7
        
        # 判断是否有病理产物（邪留维度得分高）
        has_pathological_product = len(top_xieliu) > 0 and top_xieliu[0][1] > 0.6
        
        # 判断脏腑虚损程度
        has_organ_dysfunction = len(top_zangfu) > 0 and top_zangfu[0][1] > 0.6
        
        # 判断是否为外感初期（五气得分明显高于邪留）
        is_acute_external = (has_external_pathogen and 
                            (not has_pathological_product or top_wuqi[0][1] > top_xieliu[0][1] + 0.2))
        
        # 构建因果分析
        if is_acute_external:
            # 外感初期：五气为纲
            analysis.primary_cause = f"五气-{top_wuqi[0][0]}"
            analysis.secondary_causes = [f"脏腑-{top_zangfu[0][0]}" if top_zangfu else "脏腑-表"]
            analysis.causality_chain = [
                f"外感{top_wuqi[0][0]}邪侵袭肌表",
                "卫阳被郁，正邪相争于表",
                "出现发热、恶寒、头痛、身痛等表证"
            ]
            analysis.is_acute = True
            
        elif has_external_pathogen and has_pathological_product:
            # 外感迁延：邪留为纲，五气退居次要
            analysis.primary_cause = f"邪留-{top_xieliu[0][0]}"
            analysis.secondary_causes = [
                f"脏腑-{top_zangfu[0][0]}" if top_zangfu else "",
                f"五气-{top_wuqi[0][0]}（余邪未尽）"
            ]
            analysis.causality_chain = [
                f"外感{top_wuqi[0][0]}邪迁延不愈",
                "脏腑功能失调，津液代谢障碍",
                f"形成{top_xieliu[0][0]}等病理产物"
            ]
            analysis.is_acute = False
            
        elif has_organ_dysfunction and has_pathological_product:
            # 内伤杂病：需判断脏腑与邪留的主次
            if top_zangfu[0][1] > top_xieliu[0][1]:
                # 脏腑虚损为主（本虚）
                analysis.primary_cause = f"脏腑-{top_zangfu[0][0]}"
                analysis.secondary_causes = [f"邪留-{top_xieliu[0][0]}"]
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
            return f"以「{gang}」为纲，以「{', '.join(mu)}」为目"
        else:
            return f"以「{gang}」为纲"
    
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
        
        # 3. 分析关系：判断因果主次
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
            strategies.append(f"主治：祛除外感邪气（治{primary}）")
        elif "脏腑" in primary:
            strategies.append(f"主治：调理脏腑功能（治{primary}）")
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
    
    def generate_diagnostic_report(self, text: str) -> str:
        """生成诊断报告 - 增强版"""
        syndrome_results, dimension_scores, causal_analysis = self.diagnose(text)
        
        if not syndrome_results:
            return "未能识别到明确的证候，请提供更详细的症状描述。"
        
        report_lines = []
        report_lines.append("=" * 60)
        report_lines.append("中医三型辨证辅助诊断报告")
        report_lines.append("（基于「三型二十一证」辨证体系）")
        report_lines.append("=" * 60)
        report_lines.append("")
        
        # 步骤1：信息采集
        report_lines.append("【步骤一：信息采集】")
        matched_symptoms = self.parse_input(text)
        for match in matched_symptoms:
            report_lines.append(f"  • {match.symptom_name}")
        report_lines.append("")
        
        # 步骤2：三维归因
        report_lines.append("【步骤二：三维归因】")
        
        if dimension_scores.wuqi:
            report_lines.append("  五气维度（外感/内生邪气）：")
            sorted_wuqi = sorted(dimension_scores.wuqi.items(), key=lambda x: x[1], reverse=True)
            for factor, score in sorted_wuqi[:3]:
                bar = "█" * int(score * 10)
                report_lines.append(f"    {factor}: {bar} {score:.1%}")
        
        if dimension_scores.zangfu:
            report_lines.append("  脏腑维度（病位）：")
            sorted_zangfu = sorted(dimension_scores.zangfu.items(), key=lambda x: x[1], reverse=True)
            for organ, score in sorted_zangfu[:3]:
                bar = "█" * int(score * 10)
                report_lines.append(f"    {organ}: {bar} {score:.1%}")
        
        if dimension_scores.xieliu:
            report_lines.append("  邪留维度（病理产物）：")
            sorted_xieliu = sorted(dimension_scores.xieliu.items(), key=lambda x: x[1], reverse=True)
            for factor, score in sorted_xieliu[:3]:
                bar = "█" * int(score * 10)
                report_lines.append(f"    {factor}: {bar} {score:.1%}")
        
        report_lines.append("")
        
        # 步骤3：分析关系
        report_lines.append("【步骤三：分析关系（因果链）】")
        if causal_analysis.causality_chain:
            for i, step in enumerate(causal_analysis.causality_chain, 1):
                report_lines.append(f"  {i}. {step}")
        report_lines.append("")
        
        # 步骤4：确定证型
        report_lines.append("【步骤四：确定证型】")
        top_result = syndrome_results[0]
        
        report_lines.append(f"  辨证结论：{top_result.syndrome_name}")
        report_lines.append(f"  证候分类：{top_result.category}")
        report_lines.append(f"  纲-目结构：{top_result.gang_mu_structure}")
        report_lines.append(f"  置信度：{top_result.confidence}%")
        
        if top_result.matched_primary:
            report_lines.append(f"  主症匹配：{', '.join(top_result.matched_primary)}")
        if top_result.matched_secondary:
            report_lines.append(f"  次症匹配：{', '.join(top_result.matched_secondary)}")
        if top_result.matched_tongue:
            report_lines.append(f"  舌象符合：{', '.join(top_result.matched_tongue)}")
        if top_result.matched_pulse:
            report_lines.append(f"  脉象符合：{', '.join(top_result.matched_pulse)}")
        
        report_lines.append("")
        
        # 步骤5：指导治疗
        report_lines.append("【步骤五：指导治疗】")
        
        # 治疗策略
        if top_result.treatment_strategy:
            report_lines.append(f"  治疗策略：{top_result.treatment_strategy}")
        
        # 方药建议
        for formula_name in top_result.formulas[:2]:
            formula = self.get_formula_details(formula_name)
            if formula:
                report_lines.append(f"")
                report_lines.append(f"  ▶ {formula_name}")
                composition = "、".join([f"{h['herb']}{h['dose']}" for h in formula.get("composition", [])])
                if composition:
                    report_lines.append(f"    组成：{composition}")
                if formula.get("actions"):
                    report_lines.append(f"    功效：{formula.get('actions')}")
                
                mods = formula.get("modifications", {})
                if mods:
                    report_lines.append("    加减：")
                    for condition, addition in list(mods.items())[:3]:
                        report_lines.append(f"      若{condition}，{addition}")
                
                if formula.get("cautions"):
                    report_lines.append(f"    注意：{formula.get('cautions')}")
        
        # 疾病应用（如有）
        if top_result.disease_applications:
            report_lines.append("")
            report_lines.append("【疾病辨证应用】")
            count = 0
            for disease, app in top_result.disease_applications.items():
                if count < 3:
                    report_lines.append(f"  • {disease}：{app.get('辨证要点', '')[:30]}...")
                    count += 1
        
        # 鉴别诊断
        if top_result.differentiation:
            report_lines.append("")
            report_lines.append("【鉴别要点】")
            for key, diff in list(top_result.differentiation.items())[:2]:
                report_lines.append(f"  与{key}鉴别：{diff}")
        
        report_lines.append("")
        report_lines.append("=" * 60)
        report_lines.append("注意：本诊断结果仅供参考，请结合临床实际综合判断")
        report_lines.append("=" * 60)
        
        return "\n".join(report_lines)


def main():
    """主函数 - 命令行入口"""
    import sys
    
    engine = TCMDiagnosticEngine()
    
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
    else:
        print("中医三型辨证辅助诊断系统（增强版）")
        print("-" * 40)
        text = input("请输入患者症状描述: ")
    
    report = engine.generate_diagnostic_report(text)
    print(report)


if __name__ == "__main__":
    main()
