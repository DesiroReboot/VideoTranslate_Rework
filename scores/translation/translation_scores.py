"""
翻译质量评价模块
提供多维度翻译质量评分和改进建议
"""

import json
import time
import re
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from openai import OpenAI
from config import (
    DASHSCOPE_API_KEY, 
    DASHSCOPE_BASE_URL,
    SCORING_MODEL,
    SCORE_THRESHOLD,
    MAX_RETRIES
)
from translation_modes import VideoStyle, get_translation_mode
from common.security import LLMOutputValidator, OutputValidationError


@dataclass
class TranslationScore:
    """翻译评分结果"""
    fluency: float  # 流畅度 (0-100)
    completeness: float  # 完整性 (0-100)
    consistency: float  # 一致性 (0-100)
    accuracy: float  # 准确性 (0-100)
    style_adaptation: float  # 风格适配 (0-100)
    cultural_adaptation: float  # 文化适配 (0-100)
    overall_score: float  # 综合得分 (0-100)
    suggestions: List[str]  # 改进建议
    should_retry: bool  # 是否需要重试
    detailed_feedback: str  # 详细反馈


class TranslationScorer:
    """翻译质量评分器"""
    
    def __init__(self):
        """初始化评分器"""
        # 初始化OpenAI客户端
        self.client = OpenAI(
            api_key=DASHSCOPE_API_KEY,
            base_url=f"{DASHSCOPE_BASE_URL}/compatible-mode/v1",
            timeout=60.0
        )
        
        # 定义不同翻译模式的评分权重
        self.style_weights = {
            VideoStyle.HUMOROUS: {
                "fluency": 0.15,
                "completeness": 0.15,
                "consistency": 0.10,
                "accuracy": 0.20,
                "style_adaptation": 0.25,
                "cultural_adaptation": 0.15
            },
            VideoStyle.SERIOUS: {
                "fluency": 0.15,
                "completeness": 0.15,
                "consistency": 0.25,
                "accuracy": 0.30,
                "style_adaptation": 0.10,
                "cultural_adaptation": 0.05
            },
            VideoStyle.EDUCATIONAL: {
                "fluency": 0.25,
                "completeness": 0.20,
                "consistency": 0.15,
                "accuracy": 0.20,
                "style_adaptation": 0.10,
                "cultural_adaptation": 0.10
            },
            VideoStyle.ENTERTAINMENT: {
                "fluency": 0.20,
                "completeness": 0.15,
                "consistency": 0.10,
                "accuracy": 0.15,
                "style_adaptation": 0.25,
                "cultural_adaptation": 0.15
            },
            VideoStyle.NEWS: {
                "fluency": 0.15,
                "completeness": 0.20,
                "consistency": 0.25,
                "accuracy": 0.30,
                "style_adaptation": 0.05,
                "cultural_adaptation": 0.05
            },
            VideoStyle.AUTO: {
                "fluency": 0.20,
                "completeness": 0.15,
                "consistency": 0.15,
                "accuracy": 0.25,
                "style_adaptation": 0.15,
                "cultural_adaptation": 0.10
            }
        }
    
    def score_translation(
        self, 
        source_text: str, 
        translated_text: str, 
        source_language: str, 
        target_language: str,
        translation_style: str = "auto"
    ) -> TranslationScore:
        """
        评价翻译质量
        
        Args:
            source_text: 原文
            translated_text: 译文
            source_language: 源语言
            target_language: 目标语言
            translation_style: 翻译风格
            
        Returns:
            TranslationScore: 评分结果
        """
        print(f"\n[评分] 开始评价翻译质量...")
        print(f"[评分] 源语言: {source_language}, 目标语言: {target_language}")
        print(f"[评分] 翻译风格: {translation_style}")
        
        # 获取翻译风格枚举
        style_enum = get_translation_mode(translation_style)
        weights = self.style_weights.get(style_enum, self.style_weights[VideoStyle.AUTO])
        
        # 构建评分提示词
        scoring_prompt = self._build_scoring_prompt(
            source_text, translated_text, source_language, 
            target_language, translation_style
        )
        
        try:
            # 调用LLM进行评分
            response = self.client.chat.completions.create(
                model=SCORING_MODEL,
                messages=[
                    {
                        "role": "system", 
                        "content": "你是一个专业的翻译质量评价专家。请根据提供的标准对翻译结果进行客观、准确的评分。"
                    },
                    {
                        "role": "user", 
                        "content": scoring_prompt
                    }
                ],
                temperature=0.2,  # 低温度确保评分一致性
                top_p=0.8
            )
            
            # 解析评分结果
            raw_response = response.choices[0].message.content
            
            # 先尝试解析JSON，再进行安全验证
            try:
                # 尝试直接解析JSON
                score_data = json.loads(raw_response)
                
                # 对JSON中的每个字段进行安全验证
                sanitized_score_data = self._sanitize_score_data(score_data)
                return self._parse_score_data(sanitized_score_data, weights)
                
            except json.JSONDecodeError:
                # 如果直接解析失败，尝试提取JSON部分
                try:
                    # 查找JSON开始和结束位置
                    start_idx = raw_response.find('{')
                    end_idx = raw_response.rfind('}') + 1
                    
                    if start_idx != -1 and end_idx != 0:
                        json_str = raw_response[start_idx:end_idx]
                        score_data = json.loads(json_str)
                        
                        # 对JSON中的每个字段进行安全验证
                        sanitized_score_data = self._sanitize_score_data(score_data)
                        return self._parse_score_data(sanitized_score_data, weights)
                    else:
                        raise ValueError("无法找到有效的JSON格式")
                except (json.JSONDecodeError, ValueError):
                    # 如果JSON解析仍然失败，对整个响应进行安全验证
                    try:
                        sanitized_response = LLMOutputValidator.sanitize_translation_output(raw_response)
                        return self._parse_text_response(sanitized_response, weights)
                    except OutputValidationError as e:
                        print(f"[评分] 安全验证失败: {e}")
                        # 使用默认评分
                        return self._get_default_score(weights)
                
        except Exception as e:
            print(f"[评分] 评分过程出错: {str(e)}")
            # 返回默认评分
            return self._get_default_score(weights)
    
    def _sanitize_score_data(self, score_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        对评分数据进行安全验证
        
        Args:
            score_data: 原始评分数据
            
        Returns:
            安全验证后的评分数据
        """
        try:
            sanitized_data = {}
            
            # 处理数值字段
            numeric_fields = [
                "fluency", "completeness", "consistency", 
                "accuracy", "style_adaptation", "cultural_adaptation"
            ]
            
            for field in numeric_fields:
                if field in score_data:
                    value = score_data[field]
                    # 确保是数字且在合理范围内
                    if isinstance(value, (int, float)):
                        sanitized_value = max(0, min(100, float(value)))
                        sanitized_data[field] = int(sanitized_value)
                    else:
                        sanitized_data[field] = 65  # 默认值
                else:
                    sanitized_data[field] = 65  # 默认值
            
            # 处理suggestions字段
            if "suggestions" in score_data and isinstance(score_data["suggestions"], list):
                # 对每个建议进行安全验证
                sanitized_suggestions = []
                for suggestion in score_data["suggestions"]:
                    if isinstance(suggestion, str):
                        # 使用LLMOutputValidator进行安全验证，但不转义HTML
                        try:
                            # 使用自定义的安全验证，不转义HTML
                            safe_suggestion = self._safe_text_clean(suggestion)
                            sanitized_suggestions.append(safe_suggestion)
                        except:
                            # 如果验证失败，使用默认建议
                            sanitized_suggestions.append("建议检查翻译质量")
                    else:
                        sanitized_suggestions.append("建议检查翻译质量")
                sanitized_data["suggestions"] = sanitized_suggestions
            else:
                sanitized_data["suggestions"] = ["建议检查翻译质量"]
            
            # 处理detailed_feedback字段
            if "detailed_feedback" in score_data and isinstance(score_data["detailed_feedback"], str):
                try:
                    # 使用自定义的安全验证，不转义HTML
                    safe_feedback = self._safe_text_clean(score_data["detailed_feedback"])
                    sanitized_data["detailed_feedback"] = safe_feedback
                except:
                    sanitized_data["detailed_feedback"] = "无详细反馈"
            else:
                sanitized_data["detailed_feedback"] = "无详细反馈"
            
            return sanitized_data
            
        except Exception as e:
            print(f"[评分] 安全验证评分数据时出错: {str(e)}")
            # 返回默认评分数据
            return {
                "fluency": 65,
                "completeness": 65,
                "consistency": 65,
                "accuracy": 65,
                "style_adaptation": 65,
                "cultural_adaptation": 65,
                "suggestions": ["建议检查翻译质量"],
                "detailed_feedback": "无详细反馈"
            }
    
    def _safe_text_clean(self, text: str) -> str:
        """
        安全清理文本，但不进行HTML转义
        
        Args:
            text: 待清理的文本
            
        Returns:
            清理后的安全文本
        """
        if not isinstance(text, str):
            return ""
        
        # 移除危险的控制字符
        text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)
        
        # 检测危险模式
        dangerous_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
            r'<iframe[^>]*>',
            r'eval\s*\(',
            r'exec\s*\(',
            r'__import__\s*\(',
            r'os\.system\s*\(',
            r'subprocess\.',
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
                return "检测到潜在不安全内容"
        
        # 限制长度
        if len(text) > 1000:
            text = text[:1000] + "..."
        
        return text.strip()
    
    def _build_scoring_prompt(
        self, 
        source_text: str, 
        translated_text: str, 
        source_language: str, 
        target_language: str,
        translation_style: str
    ) -> str:
        """构建评分提示词"""
        
        # 截断过长的文本
        max_length = 2000
        if len(source_text) > max_length:
            source_text = source_text[:max_length] + "..."
        if len(translated_text) > max_length:
            translated_text = translated_text[:max_length] + "..."
        
        return f"""请对以下翻译结果进行多维度评分。

## 翻译信息
- 源语言: {source_language}
- 目标语言: {target_language}
- 翻译风格: {translation_style}

## 原文
{source_text}

## 译文
{translated_text}

## 评分维度 (每个维度0-100分)
1. **流畅度(Fluency)**: 译文是否符合目标语言的表达习惯，语法是否正确
2. **完整性(Completeness)**: 是否完整翻译了原文的所有内容，没有遗漏
3. **一致性(Consistency)**: 同一术语在全文中翻译是否一致
4. **准确性(Accuracy)**: 是否准确传达了原文的含义
5. **风格适配(Style Adaptation)**: 是否符合设定的翻译风格({translation_style})
6. **文化适配(Cultural Adaptation)**: 是否适当进行了文化转换

## 输出要求
请严格按照以下JSON格式输出评分结果，不要添加任何其他文字或解释：

{{
    "fluency": 分数,
    "completeness": 分数,
    "consistency": 分数,
    "accuracy": 分数,
    "style_adaptation": 分数,
    "cultural_adaptation": 分数,
    "suggestions": ["建议1", "建议2", "建议3"],
    "detailed_feedback": "详细反馈说明"
}}

重要提示：
1. 必须输出有效的JSON格式
2. 每个分数都是0-100之间的整数
3. suggestions必须是字符串数组
4. detailed_feedback必须是字符串
5. 不要在JSON前后添加任何其他文字或标记"""
    
    def _parse_score_data(self, score_data: Dict[str, Any], weights: Dict[str, float]) -> TranslationScore:
        """解析评分数据"""
        
        # 提取各维度分数，默认为60分
        fluency = min(100, max(0, int(score_data.get("fluency", 60))))
        completeness = min(100, max(0, int(score_data.get("completeness", 60))))
        consistency = min(100, max(0, int(score_data.get("consistency", 60))))
        accuracy = min(100, max(0, int(score_data.get("accuracy", 60))))
        style_adaptation = min(100, max(0, int(score_data.get("style_adaptation", 60))))
        cultural_adaptation = min(100, max(0, int(score_data.get("cultural_adaptation", 60))))
        
        # 计算加权总分
        overall_score = (
            fluency * weights["fluency"] +
            completeness * weights["completeness"] +
            consistency * weights["consistency"] +
            accuracy * weights["accuracy"] +
            style_adaptation * weights["style_adaptation"] +
            cultural_adaptation * weights["cultural_adaptation"]
        )
        
        # 提取建议
        suggestions = score_data.get("suggestions", [])
        if not isinstance(suggestions, list):
            suggestions = [str(suggestions)]
        
        # 详细反馈
        detailed_feedback = score_data.get("detailed_feedback", "无详细反馈")
        
        # 判断是否需要重试
        should_retry = overall_score < SCORE_THRESHOLD
        
        print(f"[评分] 流畅度: {fluency}, 完整性: {completeness}, 一致性: {consistency}")
        print(f"[评分] 准确性: {accuracy}, 风格适配: {style_adaptation}, 文化适配: {cultural_adaptation}")
        print(f"[评分] 综合得分: {overall_score:.1f}, 阈值: {SCORE_THRESHOLD}, 是否重试: {should_retry}")
        
        return TranslationScore(
            fluency=fluency,
            completeness=completeness,
            consistency=consistency,
            accuracy=accuracy,
            style_adaptation=style_adaptation,
            cultural_adaptation=cultural_adaptation,
            overall_score=overall_score,
            suggestions=suggestions,
            should_retry=should_retry,
            detailed_feedback=detailed_feedback
        )
    
    def _parse_text_response(self, response: str, weights: Dict[str, float]) -> TranslationScore:
        """解析文本格式的响应"""
        print("[评分] JSON解析失败，尝试文本解析")
        
        # 使用简单的文本解析作为后备方案
        # 这里可以添加更复杂的文本解析逻辑
        return self._get_default_score(weights)
    
    def _get_default_score(self, weights: Dict[str, float]) -> TranslationScore:
        """获取默认评分"""
        default_score = 65  # 默认中等分数
        
        overall_score = default_score
        should_retry = overall_score < SCORE_THRESHOLD
        
        return TranslationScore(
            fluency=default_score,
            completeness=default_score,
            consistency=default_score,
            accuracy=default_score,
            style_adaptation=default_score,
            cultural_adaptation=default_score,
            overall_score=overall_score,
            suggestions=["评分系统出错，请检查翻译质量"],
            should_retry=should_retry,
            detailed_feedback="评分系统出现错误，无法提供详细反馈"
        )
    
    def generate_reference(
        self, 
        source_text: str, 
        source_language: str, 
        target_language: str,
        translation_style: str = "auto"
    ) -> str:
        """
        生成参考译文
        
        Args:
            source_text: 原文
            source_language: 源语言
            target_language: 目标语言
            translation_style: 翻译风格
            
        Returns:
            参考译文
        """
        print(f"[参考译文] 生成参考译文...")
        
        # 获取翻译风格枚举
        style_enum = get_translation_mode(translation_style)
        
        # 构建参考译文提示词
        reference_prompt = f"""请将以下{source_language}文本翻译成{target_language}，要求翻译风格为{translation_style}。

请提供高质量的参考译文，作为评价其他翻译的基准。

原文：
{source_text}

参考译文："""
        
        try:
            response = self.client.chat.completions.create(
                model=SCORING_MODEL,
                messages=[
                    {
                        "role": "system", 
                        "content": f"你是一个专业的翻译专家，擅长{translation_style}风格的翻译。请提供高质量的参考译文。"
                    },
                    {
                        "role": "user", 
                        "content": reference_prompt
                    }
                ],
                temperature=0.3,  # 较低温度确保质量
                top_p=0.8
            )
            
            # 安全验证
            try:
                reference_text = LLMOutputValidator.sanitize_translation_output(
                    response.choices[0].message.content
                )
                print(f"[参考译文] 参考译文生成成功")
                return reference_text
            except OutputValidationError as e:
                print(f"[参考译文] 安全验证失败: {e}")
                return ""
                
        except Exception as e:
            print(f"[参考译文] 生成参考译文出错: {str(e)}")
            return ""
    
    def provide_improvement_suggestions(self, score: TranslationScore) -> List[str]:
        """
        根据评分提供改进建议
        
        Args:
            score: 评分结果
            
        Returns:
            改进建议列表
        """
        suggestions = []
        
        # 根据各维度分数提供针对性建议
        if score.fluency < 70:
            suggestions.append("流畅度较低，建议调整句式结构，使其更符合目标语言表达习惯")
        
        if score.completeness < 70:
            suggestions.append("完整性不足，建议检查是否有遗漏的内容")
        
        if score.consistency < 70:
            suggestions.append("一致性较差，建议确保同一术语在全文中翻译一致")
        
        if score.accuracy < 70:
            suggestions.append("准确性不足，建议重新核对原文含义，确保准确传达")
        
        if score.style_adaptation < 70:
            suggestions.append("风格适配不佳，建议调整表达方式以符合设定的翻译风格")
        
        if score.cultural_adaptation < 70:
            suggestions.append("文化适配不足，建议适当进行文化背景的转换和适配")
        
        # 添加模型返回的建议
        if score.suggestions:
            suggestions.extend(score.suggestions)
        
        # 去重
        suggestions = list(set(suggestions))
        
        return suggestions
    
    def should_retry(self, score: TranslationScore, retry_count: int = 0) -> bool:
        """
        判断是否需要重试
        
        Args:
            score: 评分结果
            retry_count: 当前重试次数
            
        Returns:
            是否需要重试
        """
        # 如果分数高于阈值，不需要重试
        if not score.should_retry:
            return False
        
        # 如果已达到最大重试次数，不再重试
        if retry_count >= MAX_RETRIES:
            return False
        
        return True