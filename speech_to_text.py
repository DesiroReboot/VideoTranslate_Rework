#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音识别模块
支持单节点和分布式ASR识别
"""

import sys
import time
from pathlib import Path
from typing import Optional

import requests
from config import (
    DASHSCOPE_API_KEY,
    ASR_MODEL,
    ASR_MAX_RETRIES,
    ASR_SCORE_THRESHOLD,
    ENABLE_ASR_SCORING,
    ASR_SCORING_RESULTS_DIR,
    OSS_ENDPOINT,
    OSS_ACCESS_KEY_ID,
    OSS_ACCESS_KEY_SECRET,
    OSS_BUCKET_NAME,
    ENABLE_DISTRIBUTED_ASR,
    DISTRIBUTED_ASR_NODE_COUNT,
    DISTRIBUTED_ASR_COEFFICIENT_THRESHOLD,
    DISTRIBUTED_ASR_ENABLE_QUALITY_EVAL,
)
from common.security import (
    LLMOutputValidator,
    FileValidator,
)
from scores.ASR.asr_scorer import AsrScorer, AsrScore
from common.consensus import DistributedASRConsensus
import oss2
import dashscope


class SpeechToText:
    """语音识别服务类"""

    def __init__(self):
        """初始化语音识别服务"""
        # 验证API密钥
        if not DASHSCOPE_API_KEY:
            raise ValueError("未配置DASHSCOPE_API_KEY")

        # 设置DashScope配置
        dashscope.api_key = DASHSCOPE_API_KEY

        # 初始化ASR质量评分器
        self.asr_scorer: Optional[AsrScorer] = None
        if ENABLE_ASR_SCORING:
            self.asr_scorer = AsrScorer()
            print("[初始化] ASR质量评分器已启用")
        else:
            print("[初始化] ASR质量评分器已禁用")

        # 初始化分布式ASR共识机制
        self.distributed_asr: Optional[DistributedASRConsensus] = None
        if ENABLE_DISTRIBUTED_ASR:
            self.distributed_asr = DistributedASRConsensus(
                node_count=DISTRIBUTED_ASR_NODE_COUNT,
                coefficient_threshold=DISTRIBUTED_ASR_COEFFICIENT_THRESHOLD,
                enable_quality_eval=DISTRIBUTED_ASR_ENABLE_QUALITY_EVAL,
            )
            print(f"[初始化] 分布式ASR共识机制已启用 ({DISTRIBUTED_ASR_NODE_COUNT}节点)")
        else:
            print("[初始化] 分布式ASR共识机制已禁用")

    def _upload_to_oss(self, audio_path: str) -> str:
        """
        上传音频文件到OSS

        Args:
            audio_path: 音频文件路径

        Returns:
            OSS公开访问URL
        """
        # 创建OSS客户端
        auth = oss2.Auth(OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET)
        bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET_NAME)

        # 生成唯一文件名
        import time
        timestamp = int(time.time() * 1000)
        object_name = f"video_translate/audio/{timestamp}_{Path(audio_path).name}"

        # 上传文件
        print(f"[OSS] 上传文件: {Path(audio_path).name} -> {object_name}")
        bucket.put_object_from_file(object_name, audio_path)

        # 设置文件权限为公共读（Fun-ASR需要直接访问）
        bucket.put_object_acl(object_name, oss2.OBJECT_ACL_PUBLIC_READ)

        # 获取文件大小
        file_size = Path(audio_path).stat().st_size

        # 生成公开URL
        # 注意：不使用签名URL，因为Fun-ASR需要直接访问
        public_url = f"https://{OSS_BUCKET_NAME}.{OSS_ENDPOINT}/{object_name}"

        print(f"[OSS] 文件上传成功 (大小: {file_size / 1024:.2f}KB)")
        print(f"[OSS] 公开URL: {public_url}")
        print(f"[OSS] 原始路径: {object_name}")

        return public_url

    def _single_node_recognize(self, audio_path: str, node_id: int = 0) -> str:
        """
        单节点ASR识别

        Args:
            audio_path: 音频文件路径
            node_id: 节点ID（用于分布式ASR）

        Returns:
            识别的文本内容

        Raises:
            Exception: 识别失败
            SecurityError: 安全检查失败
        """
        print(f"[ASR节点{node_id}] 开始识别...")

        # 上传音频到OSS
        audio_url = self._upload_to_oss(audio_path)

        # 使用Fun-ASR文件识别API
        from http import HTTPStatus
        from dashscope.audio.asr import Transcription

        # 调用异步文件识别
        task_response = Transcription.async_call(
            model=ASR_MODEL,
            file_urls=[audio_url],
            language_hints=["zh", "en"],  # 支持中英文
        )

        if task_response.status_code != HTTPStatus.OK:
            raise Exception(f"ASR任务提交失败: {task_response.message}")

        task_id = task_response.output["task_id"]
        print(f"[ASR节点{node_id}] 任务ID: {task_id}, 等待识别完成...")

        # 轮询任务状态
        max_retries = 60  # 最多等待60次
        for i in range(max_retries):
            result_response = Transcription.wait(task=task_id)

            if result_response.status_code != HTTPStatus.OK:
                raise Exception(f"ASR任务查询失败: {result_response.message}")

            task_status = result_response.output["task_status"]

            if task_status == "SUCCEEDED":
                # 获取识别结果
                transcription_url = result_response.output["results"][0]["transcription_url"]
                print(f"[ASR节点{node_id}] 识别完成, 下载结果...")

                # 下载并解析结果
                resp = requests.get(transcription_url, timeout=30)
                resp.raise_for_status()
                result_data = resp.json()

                # 提取文本
                text = result_data.get("transcripts", [{}])[0].get("text", "")

                if not text:
                    # 尝试从句子中提取
                    sentences = result_data.get("transcripts", [{}])[0].get("sentences", [])
                    text = " ".join([s.get("text", "") for s in sentences])

                print(f"[ASR节点{node_id}] 识别成功,文本长度: {len(text)} 字符")
                return text

            elif task_status in ["PENDING", "RUNNING"]:
                if i % 10 == 0:  # 每20秒打印一次
                    print(f"[ASR节点{node_id}] 任务状态: {task_status}, 等待中... ({i + 1}/{max_retries})")
                time.sleep(2)
            else:
                raise Exception(f"ASR任务状态异常: {task_status}")

        raise Exception(f"[ASR节点{node_id}] 任务超时")

    def recognize(self, audio_path: str) -> str:
        """
        语音识别主入口 - 根据配置选择单节点或分布式ASR

        Args:
            audio_path: 音频文件路径

        Returns:
            识别的文本内容

        Raises:
            Exception: 识别失败
            SecurityError: 安全检查失败
        """
        # 1. 参数验证
        if not audio_path or not isinstance(audio_path, str):
            raise ValueError("音频路径参数无效")

        # 2. 音频文件安全验证
        audio_info = FileValidator.validate_audio_file(audio_path)

        print(f"\n[ASR] 开始语音识别: {audio_path}")
        print(f"[ASR] 模型: {ASR_MODEL}")
        print(f"[ASR] 音频文件大小: {audio_info['size'] / (1024 * 1024):.2f}MB")

        # 3. 根据配置选择识别方式
        if self.distributed_asr:
            # 使用分布式ASR
            return self._distributed_recognize(audio_path)
        else:
            # 使用单节点ASR（带重试）
            return self._single_node_with_retry(audio_path)

    def _single_node_with_retry(self, audio_path: str) -> str:
        """
        单节点ASR识别（带重试机制）

        Args:
            audio_path: 音频文件路径

        Returns:
            识别的文本内容
        """
        for retry_count in range(ASR_MAX_RETRIES + 1):
            print(f"[ASR] 第{retry_count + 1}次尝试 (最大{ASR_MAX_RETRIES + 1}次)")
            try:
                # 执行识别
                text = self._single_node_recognize(audio_path)

                # 打印识别文本预览
                print(
                    f"[ASR] 识别文本: {text[:100]}..."
                    if len(text) > 100
                    else f"[ASR] 识别文本: {text}"
                )

                # 安全验证：清理ASR输出
                text = LLMOutputValidator.sanitize_asr_output(text)
                print("[ASR] 安全验证通过")

                # ASR质量评分和校正
                if self.asr_scorer:
                    text = self._apply_asr_scoring(text, audio_path, retry_count)

                return text

            except Exception as e:
                print(f"[ASR] 错误: {str(e)}")
                if retry_count < ASR_MAX_RETRIES:
                    print("[ASR] 准备重试...")
                    time.sleep(2)
                else:
                    raise

        raise Exception("ASR识别失败: 所有重试尝试完毕")

    def _distributed_recognize(self, audio_path: str) -> str:
        """
        分布式ASR识别（带共识机制）

        Args:
            audio_path: 音频文件路径

        Returns:
            识别的文本内容
        """
        print(f"\n[分布式ASR] 启动{self.distributed_asr.node_count}个节点进行识别...")

        # 定义ASR函数
        def asr_function(audio_path: str, node_id: int) -> str:
            text = self._single_node_recognize(audio_path, node_id)
            # 安全验证
            text = LLMOutputValidator.sanitize_asr_output(text)
            return text

        # 使用分布式共识
        consensus = self.distributed_asr.async_reach_consensus(asr_function, audio_path)

        # 打印详细结果
        print("\n[分布式ASR] 共识结果:")
        print(f"  被淘汰节点: 节点{consensus.eliminated_node}")
        print(f"  选中节点: {consensus.selected_nodes}")
        print(f"  相似度系数: {consensus.coefficient:.4f}")
        print(f"  最终文本长度: {len(consensus.text)}")

        if consensus.warning:
            print(f"  ⚠️  {consensus.warning}")
        else:
            print("  ✓ 匹配度符合预期")

        # 可选：ASR质量评分
        final_text = consensus.text
        if self.asr_scorer:
            final_text = self._apply_asr_scoring(consensus.text, audio_path, 0)

        return final_text

    def _apply_asr_scoring(self, text: str, audio_path: str, retry_count: int) -> str:
        """
        应用ASR质量评分和校正

        Args:
            text: 识别的文本
            audio_path: 音频文件路径
            retry_count: 当前重试次数

        Returns:
            可能经过校正的文本
        """
        print("[ASR] 开始质量评分和校正...")
        original_text = text
        score_result = self.asr_scorer.score_asr_result(original_text)

        print(f"[ASR] 识别质量评分: {score_result.overall_score}/{100}")

        if score_result.corrections:
            print(f"[ASR] 发现{len(score_result.corrections)}处可能的识别错误，正在校正...")
            text = self.asr_scorer.apply_corrections(original_text, score_result.corrections)
            print(
                f"[ASR] 校正后文本: {text[:100]}..."
                if len(text) > 100
                else f"[ASR] 校正后文本: {text}"
            )

        # 保存评分结果
        self._save_asr_score_result(original_text, score_result, audio_path)

        # 检查是否需要重试
        if score_result.should_retry and retry_count < ASR_MAX_RETRIES:
            print(f"[ASR] 识别质量低于阈值({ASR_SCORE_THRESHOLD})，建议重试")

        return text

    def _save_asr_score_result(
        self, original_text: str, score_result: AsrScore, audio_path: str
    ):
        """
        保存ASR评分结果到JSON文件

        Args:
            original_text: 原始识别文本
            score_result: ASR评分结果
            audio_path: 音频文件路径
        """
        import json

        timestamp = int(time.time())

        score_data = {
            "timestamp": timestamp,
            "audio_path": audio_path,
            "original_text": original_text,
            "scores": {
                "logic_score": score_result.logic_score,
                "semantic_coherence": score_result.semantic_coherence,
                "context_consistency": score_result.context_consistency,
                "error_detection_score": score_result.error_detection_score,
                "overall_score": score_result.overall_score,
            },
            "suggestions": score_result.suggestions,
            "corrections": score_result.corrections,
            "detailed_feedback": score_result.detailed_feedback,
            "should_retry": score_result.should_retry,
        }

        score_file = ASR_SCORING_RESULTS_DIR / f"asr_score_{timestamp}.json"

        with open(score_file, "w", encoding="utf-8") as f:
            json.dump(score_data, f, ensure_ascii=False, indent=2)

        print(f"[ASR评分] 评分结果已保存: {score_file}")


# 测试代码
if __name__ == "__main__":
    # 测试语音识别
    stt = SpeechToText()

    # 检查命令行参数
    if len(sys.argv) < 2:
        print("使用方法: python speech_to_text.py <音频文件路径>")
        sys.exit(1)

    audio_file = sys.argv[1]
    if not Path(audio_file).exists():
        print(f"错误: 音频文件不存在: {audio_file}")
        sys.exit(1)

    try:
        text = stt.recognize(audio_file)
        print("\n识别结果:")
        print(text)
    except Exception as e:
        print(f"\n识别失败: {e}")
        sys.exit(1)
