#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分布式ASR共识模块
基于多节点投票机制的ASR结果质量保证
"""

import time
import math
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from difflib import SequenceMatcher
import statistics


@dataclass
class ASRResult:
    """ASR识别结果"""

    text: str
    node_id: int
    confidence: float = 0.0  # ASR置信度
    duration: float = 0.0  # 识别耗时


@dataclass
class ConsensusResult:
    """共识结果"""

    text: str
    selected_nodes: List[int]
    coefficient: float  # 最终选择的两个结果之间的相似度
    confidence_scores: Dict[int, float]  # 每个节点的可信度分数
    quality_scores: Dict[int, float]  # 每个节点的质量分数
    eliminated_node: Optional[int] = None  # 被淘汰的节点
    warning: Optional[str] = None  # 警告信息


class TextQualityEvaluator:
    """文本质量评估器"""

    @staticmethod
    def evaluate(text: str) -> float:
        """
        评估文本质量

        考虑因素：
        1. 长度适中性（100-1000字符最佳）
        2. 字符多样性（熵）
        3. 重复字符比例（越低越好）
        4. 空白比例

        Returns:
            质量分数 (0-100)
        """
        if not text:
            return 0.0

        score = 0.0

        # 1. 长度适中性 (30分)
        length = len(text)
        if 100 <= length <= 1000:
            score += 30
        elif 50 <= length < 100:
            score += 20
        elif 1000 < length <= 2000:
            score += 20
        elif length < 50:
            score += max(0, 10 - (50 - length) / 5)
        else:  # > 2000
            score += max(0, 10 - (length - 2000) / 200)

        # 2. 字符多样性 - 熵 (40分)
        char_freq: dict[str, int] = {}
        for char in text:
            char_freq[char] = char_freq.get(char, 0) + 1

        total = len(text)
        entropy = 0.0
        for count in char_freq.values():
            p = count / total
            # 使用 log2 代替 bit_length
            entropy -= p * math.log2(p) if p > 0 else 0

        # 熵越高，多样性越好（归一化到0-40）
        # 假设最大熵约为 log2(字符集大小)，对于中文+英文约为12-15
        normalized_entropy = min(entropy / 12.0, 1.0)
        score += normalized_entropy * 40

        # 3. 重复字符比例 (20分，越低越好)
        repeat_penalty = 0
        for char, count in char_freq.items():
            if char in "啊啊啊嗯嗯嗯呃呃呃" and count > 3:
                repeat_penalty += count
        repeat_score = max(0, 20 - repeat_penalty)
        score += repeat_score

        # 4. 空白比例合理性 (10分)
        whitespace_ratio = text.count(" ") / max(length, 1)
        if 0.05 <= whitespace_ratio <= 0.2:
            score += 10
        elif whitespace_ratio < 0.05:
            score += 5
        else:
            score += max(0, 10 - (whitespace_ratio - 0.2) * 50)

        return min(score, 100.0)


class DistributedASRConsensus:
    """分布式ASR共识算法"""

    def __init__(
        self,
        node_count: int = 3,
        coefficient_threshold: float = 0.95,
        enable_quality_eval: bool = True,
    ):
        """
        初始化分布式ASR共识算法

        Args:
            node_count: 节点数量（建议3-5个）
            coefficient_threshold: 相似度阈值
            enable_quality_eval: 是否启用质量评估
        """
        if node_count < 3:
            raise ValueError("节点数量至少为3个")

        self.node_count = node_count
        self.coefficient_threshold = coefficient_threshold
        self.enable_quality_eval = enable_quality_eval
        self.quality_evaluator = TextQualityEvaluator()

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        计算两个文本的相似度系数

        使用SequenceMatcher计算相似度

        Args:
            text1: 文本1
            text2: 文本2

        Returns:
            相似度系数 (0-1)，越接近1越相似
        """
        return SequenceMatcher(None, text1, text2).ratio()

    def calculate_confidence_scores(
        self, results: List[ASRResult]
    ) -> Dict[int, float]:
        """
        计算每个节点的可信度分数

        基于该节点结果与其他所有节点结果的相似度

        Args:
            results: ASR结果列表

        Returns:
            节点ID -> 可信度分数的映射
        """
        confidence_scores = {}

        for i, result_i in enumerate(results):
            total_similarity = 0.0
            comparisons = 0

            for j, result_j in enumerate(results):
                if i == j:
                    continue

                similarity = self.calculate_similarity(result_i.text, result_j.text)
                total_similarity += similarity
                comparisons += 1

            # 平均相似度作为可信度分数
            confidence_scores[result_i.node_id] = (
                total_similarity / comparisons if comparisons > 0 else 0.0
            )

        return confidence_scores

    def calculate_quality_scores(
        self, results: List[ASRResult]
    ) -> Dict[int, float]:
        """
        计算每个节点的文本质量分数

        Args:
            results: ASR结果列表

        Returns:
            节点ID -> 质量分数的映射
        """
        quality_scores = {}

        for result in results:
            if self.enable_quality_eval:
                quality_scores[result.node_id] = self.quality_evaluator.evaluate(
                    result.text
                )
            else:
                # 如果不启用质量评估，使用文本长度作为简单指标
                quality_scores[result.node_id] = float(len(result.text))

        return quality_scores

    def select_best_result(
        self,
        remaining_results: List[ASRResult],
        confidence_scores: Dict[int, float],
        quality_scores: Dict[int, float],
    ) -> ASRResult:
        """
        从剩余结果中选择最佳结果

        综合考虑可信度和质量分数

        Args:
            remaining_results: 剩余的ASR结果
            confidence_scores: 可信度分数
            quality_scores: 质量分数

        Returns:
            最佳ASR结果
        """
        if not remaining_results:
            raise ValueError("没有可用的ASR结果")

        if len(remaining_results) == 1:
            return remaining_results[0]

        # 计算综合分数（可信度权重0.6，质量权重0.4）
        best_result: Optional[ASRResult] = None
        best_score = -1.0

        for result in remaining_results:
            confidence = confidence_scores.get(result.node_id, 0.0)
            quality = quality_scores.get(result.node_id, 0.0)

            # 归一化到0-1
            normalized_confidence = confidence / self.node_count
            normalized_quality = quality / 100.0 if self.enable_quality_eval else 1.0

            combined_score = (
                normalized_confidence * 0.6 + normalized_quality * 0.4
            )

            if combined_score > best_score:
                best_score = combined_score
                best_result = result

        if best_result is None:
            raise ValueError("未能选择最佳ASR结果")

        return best_result

    def reach_consensus(self, results: List[ASRResult]) -> ConsensusResult:
        """
        达成共识，选择最佳ASR结果

        Args:
            results: 所有节点的ASR结果

        Returns:
            共识结果

        Raises:
            ValueError: 结果数量不足或无效
        """
        if len(results) < 3:
            raise ValueError(f"至少需要3个节点的结果，当前只有{len(results)}个")

        if len(results) != self.node_count:
            raise ValueError(
                f"结果数量({len(results)})与节点数量({self.node_count})不匹配"
            )

        # 1. 计算可信度分数
        confidence_scores = self.calculate_confidence_scores(results)

        # 2. 计算质量分数
        quality_scores = self.calculate_quality_scores(results)

        # 3. 找出可信度最低的节点并淘汰
        sorted_by_confidence = sorted(
            results, key=lambda r: confidence_scores[r.node_id]
        )
        eliminated_node = sorted_by_confidence[0].node_id
        remaining_results = [r for r in results if r.node_id != eliminated_node]

        # 4. 计算剩余两个结果的相似度
        if len(remaining_results) != 2:
            raise ValueError("淘汰后应该剩余2个结果")

        result1, result2 = remaining_results
        coefficient = self.calculate_similarity(result1.text, result2.text)

        # 5. 根据相似度阈值选择策略
        warning = None
        selected_result = self.select_best_result(
            remaining_results, confidence_scores, quality_scores
        )

        # 生成提示信息
        if coefficient >= self.coefficient_threshold:
            if coefficient >= 0.99:
                message = f"匹配度极高({coefficient:.4f} >= 0.99)，已选择最优方案。"
            else:
                message = (
                    f"匹配度良好({coefficient:.4f} >= {self.coefficient_threshold})，"
                    f"已选择最优方案。"
                )
        else:
            warning = (
                f"匹配度较低({coefficient:.4f} < {self.coefficient_threshold})，"
                f"可能存在识别差异，已选择综合评分最高的结果。"
            )
            message = warning

        return ConsensusResult(
            text=selected_result.text,
            selected_nodes=[r.node_id for r in remaining_results],
            coefficient=coefficient,
            confidence_scores=confidence_scores,
            quality_scores=quality_scores,
            eliminated_node=eliminated_node,
            warning=warning,
        )

    def async_reach_consensus(
        self, asr_function, audio_path: str, **kwargs
    ) -> ConsensusResult:
        """
        异步执行多节点ASR并达成共识

        Args:
            asr_function: ASR函数，签名为 (audio_path, node_id, **kwargs) -> str
            audio_path: 音频文件路径
            **kwargs: 传递给ASR函数的额外参数

        Returns:
            共识结果
        """
        import concurrent.futures

        results = []
        start_time = time.time()

        print(f"[分布式ASR] 启动{self.node_count}个节点进行识别...")

        # 使用线程池并行执行ASR
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.node_count
        ) as executor:
            future_to_node = {
                executor.submit(asr_function, audio_path, node_id, **kwargs): node_id
                for node_id in range(self.node_count)
            }

            for future in concurrent.futures.as_completed(future_to_node):
                node_id = future_to_node[future]
                try:
                    text = future.result()
                    results.append(ASRResult(text=text, node_id=node_id))
                    print(f"[分布式ASR] 节点{node_id}识别完成，文本长度: {len(text)}")
                except Exception as e:
                    print(f"[分布式ASR] 节点{node_id}识别失败: {e}")
                    # 使用空文本作为失败结果
                    results.append(ASRResult(text="", node_id=node_id))

        elapsed = time.time() - start_time
        print(f"[分布式ASR] 所有节点识别完成，总耗时: {elapsed:.2f}秒")

        # 达成共识
        consensus = self.reach_consensus(results)

        # 打印详细信息
        print(f"\n[分布式ASR] 共识结果:")
        print(f"  被淘汰节点: 节点{consensus.eliminated_node}")
        print(f"  选中节点: 节点{consensus.selected_nodes}")
        print(f"  相似度系数: {consensus.coefficient:.4f}")
        print(f"  最终文本长度: {len(consensus.text)}")
        if message := (warning := consensus.warning):
            print(f"  ⚠️  {message}")
        else:
            print(f"  ✓ {message if (message := '匹配度符合预期') else ''}")

        return consensus


# 测试代码
if __name__ == "__main__":
    # 模拟测试
    def mock_asr(audio_path: str, node_id: int) -> str:
        """模拟ASR函数"""
        time.sleep(0.5)  # 模拟网络延迟

        # 模拟不同质量的识别结果
        base_text = "这是一个测试视频的语音识别结果"
        if node_id == 0:
            return base_text + "，节点0的识别非常准确"
        elif node_id == 1:
            return base_text + "，节点1的识别很准确"
        else:  # node_id == 2
            return base_text + "，节点2的识别有误差啊啊啊"

    # 创建共识实例
    consensus = DistributedASRConsensus(
        node_count=3, coefficient_threshold=0.95
    )

    # 测试同步版本
    print("=== 测试同步共识 ===")
    results = [
        ASRResult(text="这是原始文本", node_id=0),
        ASRResult(text="这是原始文本", node_id=1),
        ASRResult(text="这是有差异的文本", node_id=2),
    ]

    consensus_result = consensus.reach_consensus(results)
    print(f"选中结果: {consensus_result.text}")
    print(f"相似度: {consensus_result.coefficient:.4f}")
