#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASR结果质量评价模块
提供ASR识别结果的语义分析和评分，支持错误校正
"""

import json
import re
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from openai import OpenAI
from config import (
    DASHSCOPE_API_KEY,
    DASHSCOPE_BASE_URL,
    ASR_SCORE_THRESHOLD,
    ENABLE_ASR_SCORING,
    ASR_ERROR_MAPPINGS,
)


@dataclass
class AsrScore:
    """ASR评分结果"""

    logic_score: float  # 逻辑性评分 (0-100)
    semantic_coherence: float  # 语义通顺度评分 (0-100)
    context_consistency: float  # 上下文一致性评分 (0-100)
    error_detection_score: float  # 错误检测评分 (0-100)
    overall_score: float  # 综合得分 (0-100)
    suggestions: List[str]  # 改进建议
    should_retry: bool  # 是否需要重试ASR
    corrections: List[Dict[str, str]]  # 建议的校正项
    detailed_feedback: str  # 详细反馈


class AsrScorer:
    """ASR结果质量评分器"""

    def __init__(self, enable_ai_scoring: bool = True):
        """初始化ASR评分器

        Args:
            enable_ai_scoring: 是否启用AI评分（使用大语言模型）
        """
        self.enable_ai_scoring = enable_ai_scoring and ENABLE_ASR_SCORING

        if self.enable_ai_scoring:
            # 初始化OpenAI客户端用于AI评分
            self.client = OpenAI(
                api_key=DASHSCOPE_API_KEY,
                base_url=f"{DASHSCOPE_BASE_URL}/compatible-mode/v1",
                timeout=60.0,
            )

        # 加载ASR错误映射配置
        self.error_mappings = ASR_ERROR_MAPPINGS

        # 定义评分权重
        self.scoring_weights = {
            "logic_score": 0.30,
            "semantic_coherence": 0.30,
            "context_consistency": 0.20,
            "error_detection_score": 0.20,
        }

    def score_asr_result(
        self, asr_text: str, context: Optional[str] = None
    ) -> AsrScore:
        """对ASR识别结果进行评分

        Args:
            asr_text: ASR识别文本
            context: 可选上下文信息（如视频标题、描述等）

        Returns:
            AsrScore: 评分结果
        """
        if not asr_text or not asr_text.strip():
            return self._create_empty_score()

        try:
            # 1. 基于规则的评分
            rule_based_scores = self._rule_based_scoring(asr_text, context)

            # 2. AI评分（如果启用）
            ai_scores = None
            if self.enable_ai_scoring:
                ai_scores = self._ai_based_scoring(asr_text, context)

            # 3. 错误检测和校正建议
            error_detection = self._detect_errors(asr_text, context)

            # 4. 合并评分
            final_scores = self._combine_scores(rule_based_scores, ai_scores)

            # 5. 计算综合得分
            overall_score = self._calculate_overall_score(final_scores)

            # 6. 判断是否需要重试
            should_retry = overall_score < ASR_SCORE_THRESHOLD

            # 7. 生成建议
            suggestions = self._generate_suggestions(final_scores, error_detection)

            return AsrScore(
                logic_score=final_scores["logic_score"],
                semantic_coherence=final_scores["semantic_coherence"],
                context_consistency=final_scores["context_consistency"],
                error_detection_score=error_detection["score"],
                overall_score=overall_score,
                suggestions=suggestions,
                should_retry=should_retry,
                corrections=error_detection["corrections"],
                detailed_feedback=error_detection.get("feedback", ""),
            )

        except Exception as e:
            print(f"[ASR评分] 评分失败: {str(e)}")
            # 返回默认评分
            return AsrScore(
                logic_score=50.0,
                semantic_coherence=50.0,
                context_consistency=50.0,
                error_detection_score=0.0,
                overall_score=50.0,
                suggestions=["ASR评分过程发生错误"],
                should_retry=False,
                corrections=[],
                detailed_feedback=f"评分错误: {str(e)}",
            )

    def _rule_based_scoring(
        self, text: str, context: Optional[str] = None
    ) -> Dict[str, float]:
        """基于规则的评分

        使用简单的启发式规则评估ASR结果质量
        """
        scores = {
            "logic_score": 50.0,  # 基础分
            "semantic_coherence": 50.0,
            "context_consistency": 50.0,
        }

        # 1. 逻辑性评分
        # 检查句子结构
        sentence_count = len(re.split(r"[。！？.!?]", text))
        if sentence_count > 0:
            # 简单的逻辑性检查：是否有常见逻辑连接词
            logic_indicators = ["因为", "所以", "但是", "然而", "而且", "然后", "接着"]
            logic_count = sum(1 for indicator in logic_indicators if indicator in text)
            logic_ratio = min(
                logic_count / sentence_count * 10, 1.0
            )  # 每句最多0.1个逻辑词
            scores["logic_score"] += logic_ratio * 20  # 最多加20分

        # 2. 语义通顺度评分
        # 检查常见搭配和词频
        common_words = [
            "的",
            "了",
            "在",
            "是",
            "我",
            "有",
            "和",
            "就",
            "人",
            "都",
            "也",
            "很",
            "到",
            "说",
            "要",
        ]
        word_count = len(text)
        if word_count > 0:
            common_word_count = sum(1 for word in common_words if word in text)
            common_ratio = common_word_count / len(common_words)
            scores["semantic_coherence"] += common_ratio * 30  # 最多加30分

            # 检查是否有明显不合理的词组合
            weird_patterns = ["啊啊啊", "呃呃呃", "嗯嗯嗯"]
            for pattern in weird_patterns:
                if pattern in text:
                    scores["semantic_coherence"] -= 15

        # 3. 上下文一致性评分（如果有上下文）
        if context:
            # 简单的关键词匹配
            context_words = set(re.findall(r"[\u4e00-\u9fff]+", context))
            text_words = set(re.findall(r"[\u4e00-\u9fff]+", text))

            if context_words:
                overlap = len(context_words & text_words) / len(context_words)
                scores["context_consistency"] += overlap * 40  # 最多加40分

        # 确保分数在0-100范围内
        for key in scores:
            scores[key] = max(0, min(100, scores[key]))

        return scores

    def _ai_based_scoring(
        self, text: str, context: Optional[str] = None
    ) -> Optional[Dict[str, float]]:
        """基于AI的评分（使用大语言模型）"""
        try:
            # 构建评分提示词
            scoring_prompt = self._build_scoring_prompt(text, context)

            response = self.client.chat.completions.create(
                model="qwen-max",
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的语音识别质量评估专家。",
                    },
                    {"role": "user", "content": scoring_prompt},
                ],
                temperature=0.1,
                max_tokens=500,
            )

            result_text = response.choices[0].message.content

            # 检查响应内容是否为None
            if result_text is None:
                print("[ASR评分] LLM返回空响应，返回None")
                return None

            # 解析AI返回的评分
            return self._parse_ai_score(result_text)

        except Exception as e:
            print(f"[ASR评分] AI评分失败: {str(e)}")
            return None

    def _build_scoring_prompt(self, text: str, context: Optional[str] = None) -> str:
        """构建评分提示词"""
        prompt = f"""请对以下语音识别(ASR)结果进行多维度质量评分。

## ASR识别文本
{text}

"""

        if context:
            prompt += f"""## 上下文信息（视频标题/描述）
{context}

"""

        prompt += """## 评分维度 (每个维度0-100分)
1. **逻辑性(Logic)**: 文本是否合乎逻辑，句子之间是否有合理的逻辑关系
2. **语义通顺度(Semantic Coherence)**: 词语搭配是否合理，表达是否通顺自然
3. **上下文一致性(Context Consistency)**: 识别内容是否与上下文相关（如果有上下文）

## 输出要求
请严格按照以下JSON格式输出评分结果，不要添加任何其他文字或解释：

{
    "logic_score": 分数,
    "semantic_coherence": 分数,
    "context_consistency": 分数
}"""

        return prompt

    def _parse_ai_score(self, result_text: str) -> Dict[str, float]:
        """解析AI返回的评分"""
        try:
            # 提取JSON部分
            json_match = re.search(r"\{.*\}", result_text, re.DOTALL)
            if json_match:
                score_data = json.loads(json_match.group())
                return {
                    "logic_score": float(score_data.get("logic_score", 50.0)),
                    "semantic_coherence": float(
                        score_data.get("semantic_coherence", 50.0)
                    ),
                    "context_consistency": float(
                        score_data.get("context_consistency", 50.0)
                    ),
                }
        except Exception as e:
            print(f"[ASR评分] 解析AI评分失败: {str(e)}")

        # 解析失败时返回默认值
        return {
            "logic_score": 50.0,
            "semantic_coherence": 50.0,
            "context_consistency": 50.0,
        }

    def _detect_errors(
        self, text: str, context: Optional[str] = None
    ) -> Dict[str, Any]:
        """检测ASR识别错误并提供校正建议"""
        corrections = []
        error_score = 100.0  # 初始满分

        # 检查每个配置的错误映射
        for error_text, mapping in self.error_mappings.items():
            if error_text in text:
                # 检查上下文是否匹配
                should_correct = self._check_context_match(
                    text, context, mapping.get("context_keywords", [])
                )

                if should_correct:
                    corrections.append(
                        {
                            "error": error_text,
                            "corrected": mapping["corrected"],
                            "confidence": 0.8,  # 置信度
                            "reason": mapping.get("description", "ASR常见识别错误"),
                        }
                    )
                    error_score -= 20  # 每检测到一个错误扣20分

        # 检查其他常见问题
        # 1. 检查是否有大量重复字符
        repeat_patterns = re.findall(r"(.)\1{2,}", text)  # 连续重复3次以上的字符
        if repeat_patterns:
            error_score -= len(repeat_patterns) * 5

        # 2. 检查是否有明显的中英文混合错误（如"阿SIR"被识别为其他形式）
        # 这里可以添加更多错误检测逻辑

        return {
            "score": max(0, error_score),
            "corrections": corrections,
            "feedback": f"检测到{len(corrections)}处可能的ASR识别错误",
        }

    def _check_context_match(
        self, text: str, context: Optional[str], keywords: List[str]
    ) -> bool:
        """检查上下文是否匹配关键词"""
        if not keywords:
            return True  # 如果没有关键词要求，默认匹配

        # 检查文本中是否包含关键词
        for keyword in keywords:
            if keyword in text:
                return True

        # 检查上下文是否包含关键词
        if context:
            for keyword in keywords:
                if keyword in context:
                    return True

        return False

    def _combine_scores(
        self, rule_scores: Dict[str, float], ai_scores: Optional[Dict[str, float]]
    ) -> Dict[str, float]:
        """合并规则评分和AI评分"""
        if ai_scores is None:
            return rule_scores

        # 加权平均：AI评分权重0.7，规则评分权重0.3
        combined = {}
        for key in rule_scores.keys():
            combined[key] = (
                ai_scores.get(key, rule_scores[key]) * 0.7 + rule_scores[key] * 0.3
            )

        return combined

    def _calculate_overall_score(self, scores: Dict[str, float]) -> float:
        """计算综合得分"""
        overall = 0.0
        for key, weight in self.scoring_weights.items():
            overall += scores.get(key, 50.0) * weight
        return min(100, max(0, overall))

    def _generate_suggestions(
        self, scores: Dict[str, float], error_detection: Dict[str, Any]
    ) -> List[str]:
        """生成改进建议"""
        suggestions = []

        # 基于评分生成建议
        if scores.get("logic_score", 100) < 60:
            suggestions.append("识别文本逻辑性较弱，建议检查音频质量或尝试重新识别")

        if scores.get("semantic_coherence", 100) < 60:
            suggestions.append("识别文本语义通顺度较低，可能存在识别错误")

        if scores.get("context_consistency", 100) < 50:
            suggestions.append("识别内容与上下文相关性较低，建议检查音频内容是否匹配")

        # 基于错误检测生成建议
        corrections = error_detection.get("corrections", [])
        for correction in corrections:
            suggestions.append(
                f"建议将 '{correction['error']}' 校正为 '{correction['corrected']}'"
            )

        if not suggestions:
            suggestions.append("ASR识别质量良好")

        return suggestions

    def _create_empty_score(self) -> AsrScore:
        """创建空文本的评分结果"""
        return AsrScore(
            logic_score=0.0,
            semantic_coherence=0.0,
            context_consistency=0.0,
            error_detection_score=0.0,
            overall_score=0.0,
            suggestions=["ASR识别结果为空"],
            should_retry=True,
            corrections=[],
            detailed_feedback="ASR识别结果为空文本",
        )

    def apply_corrections(self, text: str, corrections: List[Dict[str, str]]) -> str:
        """应用校正建议到文本

        Args:
            text: 原始文本
            corrections: 校正建议列表

        Returns:
            校正后的文本
        """
        if not text or not corrections:
            return text

        result = text
        for correction in corrections:
            error = correction.get("error")
            corrected = correction.get("corrected")
            confidence_raw = correction.get("confidence", 0.5)

            # 确保confidence是float类型
            try:
                confidence = float(confidence_raw)
            except (ValueError, TypeError):
                confidence = 0.5

            if error and corrected and confidence > 0.6:  # 置信度阈值
                result = result.replace(error, corrected)

        return result
