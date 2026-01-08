#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分布式翻译模块
支持多模型共识机制的高质量翻译
"""

import sys
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from difflib import SequenceMatcher

from openai import OpenAI
from config import (
    DISTRIBUTED_TRANSLATION_MODELS,
    DISTRIBUTED_TRANSLATION_COEFFICIENT_THRESHOLD,
    ENABLE_DISTRIBUTED_TRANSLATION,
)
from scores.translation.translation_scores import TranslationScorer, TranslationScore
from translation_modes import get_translation_mode, mode_manager
from common.stop_flag import StopFlagHolder


@dataclass
class TranslationResult:
    """翻译结果"""

    text: str
    node_id: int
    model_name: str
    duration: float = 0.0


@dataclass
class TranslationConsensus:
    """翻译共识结果"""

    text: str
    selected_nodes: List[int]
    coefficient: float  # 最终选择的两个结果之间的相似度
    model_scores: Dict[int, float]  # 每个节点的模型评分
    eliminated_node: Optional[int] = None  # 被淘汰的节点
    warning: Optional[str] = None  # 警告信息


class DistributedTranslation(StopFlagHolder):
    """分布式翻译服务类（支持停止标志）"""

    def __init__(self, translation_style: str = "auto", stop_flag=None):
        """
        初始化分布式翻译服务

        Args:
            translation_style: 翻译风格
            stop_flag: 停止标志对象（可选），用于响应用户的停止请求
        """
        # 初始化停止标志持有者基类
        super().__init__(stop_flag)

        self.style_enum = get_translation_mode(translation_style)
        self.translation_style = mode_manager.get_mode(self.style_enum)
        self.translation_prompt = self._build_translation_prompt_template()

        # 初始化翻译质量评分器（传递停止标志）
        self.scorer = TranslationScorer(stop_flag=stop_flag)

        # 验证并初始化翻译模型
        self.available_models = self._initialize_models()

        if len(self.available_models) < 2:
            print(
                f"[警告] 只有{len(self.available_models)}个可用模型，"
                f"建议至少配置2个模型的API Key"
            )

    def _initialize_models(self) -> List[Dict[str, Any]]:
        """
        验证并初始化可用的翻译模型

        Returns:
            可用的模型列表
        """
        available = []

        for i, model_config in enumerate(DISTRIBUTED_TRANSLATION_MODELS):
            api_key = model_config.get("api_key")

            # 检查API Key是否配置
            if not api_key:
                print(f"[模型{i}] {model_config['name']}: API Key未配置，将跳过")
                continue

            # 验证API Key格式
            if model_config["provider"] == "dashscope":
                if not api_key.startswith("sk-"):
                    print(f"[模型{i}] {model_config['name']}: API Key格式无效，将跳过")
                    continue
            elif model_config["provider"] == "deepseek":
                if not api_key.startswith("sk-"):
                    print(f"[模型{i}] {model_config['name']}: API Key格式无效，将跳过")
                    continue
            elif model_config["provider"] == "zhipu":
                # 智谱API Key通常较长，不以sk-开头
                if len(api_key) < 20:
                    print(f"[模型{i}] {model_config['name']}: API Key长度异常，将跳过")
                    continue

            # 创建OpenAI客户端
            try:
                client = OpenAI(
                    api_key=api_key,
                    base_url=model_config["base_url"],
                    timeout=60.0,
                )
                available.append(
                    {
                        "node_id": i,
                        "name": model_config["name"],
                        "provider": model_config["provider"],
                        "model": model_config["model"],
                        "client": client,
                    }
                )
                print(f"[模型{i}] {model_config['name']}: 初始化成功")
            except Exception as e:
                print(f"[模型{i}] {model_config['name']}: 初始化失败 - {e}")

        return available

    def _build_translation_prompt_template(self) -> str:
        """构建翻译提示词模板"""
        mode = self.translation_style

        prompt = f"""请将以下文本翻译为目标语言，要求如下：

## 翻译风格
{mode.description}

## 质量要求
1. **准确性**: 忠实传达原文含义，不随意增减内容
2. **流畅性**: 译文通顺自然，符合目标语言表达习惯
3. **完整性**: 不遗漏关键信息
4. **一致性**: 术语使用前后一致，专有名词统一处理
5. **风格适配**: {mode.description}

## 输出要求
- 仅输出翻译后的文本
- 不要添加任何解释、注释或额外说明
- 保持原文的段落结构

## 原文
{{text}}

## 目标语言
{{target_language}}

请严格按照以上要求进行翻译。
"""
        return prompt

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        计算两个翻译结果的相似度

        Args:
            text1: 文本1
            text2: 文本2

        Returns:
            相似度系数 (0-1)
        """
        return SequenceMatcher(None, text1, text2).ratio()

    def calculate_model_scores(self, results: List[TranslationResult]) -> Dict[int, float]:
        """
        计算每个翻译结果的可信度分数

        基于该结果与其他结果的相似度

        Args:
            results: 翻译结果列表

        Returns:
            节点ID -> 可信度分数的映射
        """
        model_scores = {}

        for i, result_i in enumerate(results):
            total_similarity = 0.0
            comparisons = 0

            for j, result_j in enumerate(results):
                if i == j:
                    continue

                similarity = self.calculate_similarity(result_i.text, result_j.text)
                total_similarity += similarity
                comparisons += 1

            # 平均相似度作为模型可信度分数
            model_scores[result_i.node_id] = (
                total_similarity / comparisons if comparisons > 0 else 0.0
            )

        return model_scores

    def translate_with_model(
        self,
        text: str,
        target_language: str,
        model_config: Dict[str, Any],
        node_id: int,
    ) -> TranslationResult:
        """
        使用指定模型进行翻译

        Args:
            text: 源文本
            target_language: 目标语言
            model_config: 模型配置
            node_id: 节点ID

        Returns:
            翻译结果
        """
        start_time = time.time()
        print(f"[翻译节点{node_id}] 开始使用 {model_config['name']} 翻译...")

        try:
            # 构建提示词
            prompt = self.translation_prompt.format(
                text=text, target_language=target_language
            )

            # 调用模型
            response = model_config["client"].chat.completions.create(
                model=model_config["model"],
                messages=[
                    {
                        "role": "system",
                        "content": f"你是一个专业的{model_config['name']}翻译引擎。",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.translation_style.get_model_params().get(
                    "temperature", 0.5
                ),
                top_p=self.translation_style.get_model_params().get("top_p", 0.85),
                max_tokens=8000,
            )

            # 提取翻译结果
            translated_text = response.choices[0].message.content

            if not translated_text:
                raise ValueError("模型返回空结果")

            duration = time.time() - start_time
            print(
                f"[翻译节点{node_id}] 翻译完成，耗时: {duration:.2f}秒，"
                f"译文长度: {len(translated_text)} 字符"
            )

            return TranslationResult(
                text=translated_text,
                node_id=node_id,
                model_name=model_config["name"],
                duration=duration,
            )

        except Exception as e:
            print(f"[翻译节点{node_id}] 翻译失败: {e}")
            # 返回空文本作为失败标记
            return TranslationResult(
                text="", node_id=node_id, model_name=model_config["name"]
            )

    def reach_consensus(
        self, results: List[TranslationResult], source_text: str, target_language: str
    ) -> TranslationConsensus:
        """
        达成翻译共识，选择最佳翻译结果

        Args:
            results: 所有节点的翻译结果
            source_text: 源文本
            target_language: 目标语言

        Returns:
            共识结果
        """
        if len(results) < 2:
            raise ValueError(f"至少需要2个成功的翻译结果，当前只有{len(results)}个")

        # 1. 计算模型可信度分数
        model_scores = self.calculate_model_scores(results)

        # 2. 找出可信度最低的节点并淘汰
        sorted_by_score = sorted(results, key=lambda r: model_scores[r.node_id])
        eliminated_node = sorted_by_score[0].node_id
        remaining_results = [r for r in results if r.node_id != eliminated_node]

        # 3. 计算剩余两个结果的相似度
        if len(remaining_results) == 2:
            result1, result2 = remaining_results
            coefficient = self.calculate_similarity(result1.text, result2.text)
        else:
            # 如果只有1个结果成功
            result1 = remaining_results[0]
            coefficient = 1.0  # 单个结果默认为完全一致

        # 4. 使用 TranslationScorer 选择最佳结果
        selected_result: TranslationResult
        selected_score: TranslationScore | None

        if len(remaining_results) == 2:
            # 对两个结果进行评分
            scores: list[tuple[TranslationResult, TranslationScore | None]] = []
            for result in remaining_results:
                try:
                    score = self.scorer.score_translation(
                        source_text=source_text,
                        translated_text=result.text,
                        target_language=target_language,
                        source_language="auto",
                        translation_style=self.style_enum.value,
                    )
                    scores.append((result, score))
                except Exception as e:
                    print(f"[评分] 对节点{result.node_id}评分失败: {e}")
                    # 使用默认分数
                    scores.append((result, None))

            # 选择综合分数更高的
            if scores[0][1] and scores[1][1]:
                if scores[0][1].overall_score >= scores[1][1].overall_score:
                    selected_result = scores[0][0]
                    selected_score = scores[0][1]
                else:
                    selected_result = scores[1][0]
                    selected_score = scores[1][1]
            elif scores[0][1]:
                selected_result = scores[0][0]
                selected_score = scores[0][1]
            else:
                selected_result = scores[1][0]
                selected_score = scores[1][1]

            # 打印评分信息
            if selected_score:
                print(
                    f"[共识] 选择节点{selected_result.node_id}，"
                    f"综合得分: {selected_score.overall_score:.1f}/100"
                )
        else:
            # 只有1个结果
            selected_result = remaining_results[0]
            selected_score = None

        # 5. 生成提示信息
        warning = None
        if coefficient >= DISTRIBUTED_TRANSLATION_COEFFICIENT_THRESHOLD:
            if coefficient >= 0.99:
                print(f"匹配度极高({coefficient:.4f} >= 0.99)，已选择最优方案。")
            else:
                print(
                    f"匹配度良好({coefficient:.4f} >= {DISTRIBUTED_TRANSLATION_COEFFICIENT_THRESHOLD})，"
                    f"已选择最优方案。"
                )
        else:
            warning = (
                f"匹配度较低({coefficient:.4f} < {DISTRIBUTED_TRANSLATION_COEFFICIENT_THRESHOLD})，"
                f"已选择综合评分最高的结果。"
            )

        return TranslationConsensus(
            text=selected_result.text,
            selected_nodes=[r.node_id for r in remaining_results],
            coefficient=coefficient,
            model_scores=model_scores,
            eliminated_node=eliminated_node,
            warning=warning,
        )

    def translate(self, text: str, target_language: str) -> Tuple[str, Optional[TranslationScore]]:
        """
        翻译主入口 - 根据配置选择单模型或分布式翻译

        Args:
            text: 源文本
            target_language: 目标语言

        Returns:
            (翻译文本, 翻译评分)的元组

        Raises:
            Exception: 翻译失败或用户请求停止
        """
        # 检查停止标志（在开始处理前）
        if self._check_stop():
            print("[翻译] 检测到停止请求，终止翻译")
            raise Exception("翻译已取消：用户请求停止")

        if not text or not isinstance(text, str):
            raise ValueError("源文本参数无效")

        if not target_language or not isinstance(target_language, str):
            raise ValueError("目标语言参数无效")

        print(f"\n[翻译] 开始翻译: {target_language}")
        print(f"[翻译] 源文本长度: {len(text)} 字符")

        if ENABLE_DISTRIBUTED_TRANSLATION and len(self.available_models) >= 2:
            # 使用分布式翻译
            result = self._distributed_translate(text, target_language)
        else:
            # 使用单模型翻译
            result = self._single_model_translate(text, target_language)

        # 检查停止标志（在API返回后）
        if self._check_stop():
            print("[翻译] 检测到停止请求，丢弃翻译结果")
            raise Exception("翻译已取消：用户请求停止")

        return result

    def _single_model_translate(
        self, text: str, target_language: str
    ) -> Tuple[str, Optional[TranslationScore]]:
        """单模型翻译"""
        if not self.available_models:
            raise ValueError("没有可用的翻译模型，请检查API Key配置")

        # 使用第一个可用模型
        model_config = self.available_models[0]
        print(f"[翻译] 使用模型: {model_config['name']}")

        result = self.translate_with_model(text, target_language, model_config, 0)

        if not result.text:
            raise ValueError(f"翻译失败: 模型 {model_config['name']} 返回空结果")

        # 进行质量评分
        try:
            score = self.scorer.score_translation(
                source_text=text,
                translated_text=result.text,
                target_language=target_language,
                source_language="auto",
                translation_style=self.style_enum.value,
            )
            print(f"[评分] 综合得分: {score.overall_score:.1f}/100")
            return result.text, score
        except Exception as e:
            print(f"[评分] 评分失败: {e}")
            return result.text, None

    def _distributed_translate(
        self, text: str, target_language: str
    ) -> Tuple[str, Optional[TranslationScore]]:
        """分布式翻译（带共识机制）"""
        print(f"[分布式翻译] 启动{len(self.available_models)}个模型进行翻译...")

        import concurrent.futures

        results = []
        start_time = time.time()

        # 使用线程池并行执行翻译
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=len(self.available_models)
        ) as executor:
            future_to_model = {
                executor.submit(
                    self.translate_with_model, text, target_language, model, model["node_id"]
                ): model
                for model in self.available_models
            }

            for future in concurrent.futures.as_completed(future_to_model):
                model = future_to_model[future]
                try:
                    result = future.result()
                    if result.text:  # 只记录成功的结果
                        results.append(result)
                except Exception as e:
                    print(f"[分布式翻译] 模型 {model['name']} 执行失败: {e}")

        elapsed = time.time() - start_time
        print(f"[分布式翻译] 所有模型翻译完成，总耗时: {elapsed:.2f}秒")

        if len(results) < 2:
            print(f"[分布式翻译] 只有{len(results)}个模型成功，无法达成共识")
            if len(results) == 1:
                return results[0].text, None
            else:
                raise ValueError("所有翻译模型都失败")

        # 达成共识
        consensus = self.reach_consensus(results, text, target_language)

        # 打印详细信息
        print("\n[分布式翻译] 共识结果:")
        print(f"  被淘汰模型: {results[consensus.eliminated_node].model_name if consensus.eliminated_node is not None else 'N/A'}")
        print(f"  选中模型: {[results[i].model_name for i in consensus.selected_nodes]}")
        print(f"  相似度系数: {consensus.coefficient:.4f}")
        print(f"  最终译文长度: {len(consensus.text)}")

        if consensus.warning:
            print(f"  ⚠️  {consensus.warning}")
        else:
            print(f"  ✓ {message if (message := '匹配度符合预期') else ''}")

        # 可选：对最终结果进行评分
        try:
            score = self.scorer.score_translation(
                source_text=text,
                translated_text=consensus.text,
                target_language=target_language,
                source_language="auto",
                translation_style=self.style_enum.value,
            )
            print(f"[评分] 综合得分: {score.overall_score:.1f}/100")
            return consensus.text, score
        except Exception as e:
            print(f"[评分] 评分失败: {e}")
            return consensus.text, None


# 测试代码
if __name__ == "__main__":
    # 测试翻译
    translator = DistributedTranslation(translation_style="auto")

    # 测试文本
    test_text = "这是一个测试文本，用于验证分布式翻译功能。"
    target_lang = "English"

    try:
        translated, score = translator.translate(test_text, target_lang)
        print("\n翻译结果:")
        print(translated)
        if score:
            print(f"\n评分: {score.overall_score}/100")
    except Exception as e:
        print(f"\n翻译失败: {e}")
