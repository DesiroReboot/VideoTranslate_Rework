#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音识别模块
支持单节点和分布式ASR识别
"""

import sys
import time
import uuid
import json
from pathlib import Path
from typing import Optional, Tuple, List, Dict

import requests
from config import (
    DASHSCOPE_API_KEY,
    ASR_MODEL,
    ASR_LANGUAGE_HINTS,
    ASR_CUSTOM_VOCABULARY,
    ASR_MAX_RETRIES,
    ASR_SCORE_THRESHOLD,
    ASR_ENABLE_LLM_POSTPROCESS,
    ASR_LLM_POSTPROCESS_THRESHOLD,
    ENABLE_ASR_SCORING,
    ASR_SCORING_RESULTS_DIR,
    ASR_ENABLE_SCORE_COLLECTION,
    ASR_SCORE_HISTORY_FILE,
    ASR_ENABLE_ADAPTIVE_THRESHOLD,
    ASR_ADAPTIVE_THRESHOLD_METHOD,
    ASR_MOVING_AVG_WINDOW,
    ASR_PERCENTILE_THRESHOLD,
    OSS_ENDPOINT,
    OSS_ACCESS_KEY_ID,
    OSS_ACCESS_KEY_SECRET,
    OSS_BUCKET_NAME,
    OSS_ENABLE_UUID_FILENAME,
    OSS_AUTO_CLEANUP,
    OSS_LIFECYCLE_DAYS,
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
from common.stop_flag import StopFlagHolder
import oss2
import dashscope


class SpeechToText(StopFlagHolder):
    """语音识别服务类（支持停止标志）"""

    def __init__(self, stop_flag=None):
        """
        初始化语音识别服务

        Args:
            stop_flag: 停止标志对象（可选），用于响应用户的停止请求
        """
        # 初始化停止标志持有者基类
        super().__init__(stop_flag)

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

        # 初始化评分历史数据
        self.score_history: List[Dict] = []
        if ASR_ENABLE_SCORE_COLLECTION:
            self._load_score_history()
            print(f"[初始化] ASR评分数据收集已启用 (历史记录: {len(self.score_history)}条)")

    def _load_score_history(self) -> None:
        """加载ASR评分历史数据"""
        if not ASR_SCORE_HISTORY_FILE.exists():
            self.score_history = []
            return

        try:
            with open(ASR_SCORE_HISTORY_FILE, "r", encoding="utf-8") as f:
                self.score_history = json.load(f)
            print(f"[评分历史] 已加载 {len(self.score_history)} 条历史记录")
        except Exception as e:
            print(f"[评分历史] 加载失败: {e}")
            self.score_history = []

    def _save_score_history(self) -> None:
        """保存ASR评分历史数据"""
        if not ASR_ENABLE_SCORE_COLLECTION:
            return

        try:
            with open(ASR_SCORE_HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.score_history, f, ensure_ascii=False, indent=2)
            print(f"[评分历史] 已保存 {len(self.score_history)} 条记录")
        except Exception as e:
            print(f"[评分历史] 保存失败: {e}")

    def _add_score_record(self, score: float, audio_path: str, text_length: int) -> None:
        """
        添加评分记录到历史

        Args:
            score: ASR评分
            audio_path: 音频文件路径
            text_length: 识别文本长度
        """
        if not ASR_ENABLE_SCORE_COLLECTION:
            return

        record = {
            "timestamp": int(time.time()),
            "score": score,
            "audio_path": audio_path,
            "text_length": text_length,
        }

        self.score_history.append(record)
        self._save_score_history()

        # 如果启用了自适应阈值，计算并更新
        if ASR_ENABLE_ADAPTIVE_THRESHOLD and len(self.score_history) >= ASR_MOVING_AVG_WINDOW:
            self._calculate_and_update_threshold()

    def _calculate_and_update_threshold(self) -> None:
        """计算并更新自适应阈值"""
        if len(self.score_history) < ASR_MOVING_AVG_WINDOW:
            return

        # 获取最近N次评分
        recent_scores = [r["score"] for r in self.score_history[-ASR_MOVING_AVG_WINDOW:]]

        if ASR_ADAPTIVE_THRESHOLD_METHOD == "moving_avg":
            # 移动平均 - 最低80%的平均值作为阈值
            import statistics
            sorted_scores = sorted(recent_scores)
            # 取底部20%的分数
            bottom_percent_idx = max(1, len(sorted_scores) * ASR_PERCENTILE_THRESHOLD // 100)
            threshold = statistics.mean(sorted_scores[:bottom_percent_idx])
        else:  # percentile
            # 百分位数法
            sorted_scores = sorted(recent_scores)
            percentile_idx = len(sorted_scores) * ASR_PERCENTILE_THRESHOLD // 100
            threshold = sorted_scores[percentile_idx]

        print(f"[自适应阈值] 基于最近{len(recent_scores)}次评分，动态阈值更新为: {threshold:.2f}")
        # 注意：这里不修改全局配置，仅打印提示
        # 如需修改，可以传入全局变量或使用配置文件

    def _llm_postprocess_asr(self, text: str, score: float) -> str:
        """
        使用LLM后处理修复ASR识别错误

        Args:
            text: ASR识别的原始文本
            score: ASR评分

        Returns:
            修复后的文本
        """
        if not ASR_ENABLE_LLM_POSTPROCESS:
            return text

        if score >= ASR_LLM_POSTPROCESS_THRESHOLD:
            print("[LLM后处理] 评分达标，跳过后处理")
            return text

        print(f"[LLM后处理] 评分({score:.2f})低于阈值({ASR_LLM_POSTPROCESS_THRESHOLD})，开始修复...")

        # 构建修复prompt
        prompt = f"""请修复以下ASR语音识别文本中的错误。

**修复要求**：
1. 修正同音字错误（如"发型社" → "发现"）
2. 修正成语/固定搭配错误（如"勿谓言者不欲也" → "勿谓言之不预也"）
3. 保持原文的语言风格（中文、英文、法文混合）
4. 不要改变原意，只修复明显的识别错误
5. 专有名词要特别注意（如"法新社"、"小鹿绅士"等）

**原始文本**：
{text}

**请直接输出修复后的文本，不要添加任何解释或说明。**
"""

        try:
            # 使用dashscope调用qwen模型
            import dashscope
            from dashscope import Generation

            response = Generation.call(
                model="qwen-max",
                prompt=prompt,
                max_tokens=4000,
                temperature=0.1,  # 低温度保证稳定性
            )

            if response.status_code == 200:
                corrected_text = response.output.text.strip()
                print(f"[LLM后处理] 修复完成，原文长度: {len(text)}, 修复后长度: {len(corrected_text)}")
                return corrected_text
            else:
                print(f"[LLM后处理] 调用失败: {response.message}")
                return text

        except Exception as e:
            print(f"[LLM后处理] 异常: {e}")
            return text

    def _upload_to_oss(self, audio_path: str) -> Tuple[str, str]:
        """
        上传音频文件到OSS（安全加固版本 - 使用签名URL）

        安全措施：
        1. UUID文件名混淆
        2. 使用签名URL（带时效性访问凭证）
        3. 识别完成后自动删除

        Args:
            audio_path: 音频文件路径

        Returns:
            (OSS签名URL, 对象名称)

        Raises:
            ValueError: OSS配置未设置或不完整
        """
        # 验证OSS配置
        if not OSS_ACCESS_KEY_ID or not OSS_ACCESS_KEY_SECRET or not OSS_BUCKET_NAME:
            missing_vars = []
            if not OSS_ACCESS_KEY_ID:
                missing_vars.append("OSS_ACCESS_KEY_ID")
            if not OSS_ACCESS_KEY_SECRET:
                missing_vars.append("OSS_ACCESS_KEY_SECRET")
            if not OSS_BUCKET_NAME:
                missing_vars.append("OSS_BUCKET_NAME")

            import sys
            error_msg = f"\n{'='*60}\n"
            error_msg += f"错误: OSS功能需要设置以下环境变量:\n"
            for var in missing_vars:
                error_msg += f"  - {var}\n"
            error_msg += f"\n"

            if sys.platform == "win32":
                error_msg += f"Windows 设置方式:\n"
                for var in missing_vars:
                    error_msg += f"  setx {var} \"your_value_here\"\n"
            else:
                error_msg += f"Linux/Mac 设置方式:\n"
                error_msg += f"  在 ~/.bashrc 或 ~/.zshrc 中添加:\n"
                for var in missing_vars:
                    error_msg += f"  export {var}=your_value_here\n"

            error_msg += f"\n设置后需要重启终端或应用程序\n"
            error_msg += f"{'='*60}\n"
            raise ValueError(error_msg)

        # 创建OSS客户端
        auth = oss2.Auth(OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET)
        bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET_NAME)

        # 生成文件扩展名
        file_ext = Path(audio_path).suffix

        # 生成UUID文件名（安全加固）
        if OSS_ENABLE_UUID_FILENAME:
            # 使用UUID v4随机生成文件名
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            object_name = f"video_translate/audio/{unique_filename}"
        else:
            # 回退到时间戳方案
            timestamp = int(time.time() * 1000)
            object_name = f"video_translate/audio/{timestamp}_{Path(audio_path).name}"

        # 上传文件（私有权限）
        print(f"[OSS] 上传文件: {Path(audio_path).name} -> {object_name}")
        bucket.put_object_from_file(object_name, audio_path)

        # 生成签名URL（1小时有效期）
        # Fun-ASR识别通常需要几分钟，1小时足够
        signed_url = bucket.sign_url('GET', object_name, 3600)

        # 获取文件大小
        file_size = Path(audio_path).stat().st_size

        print(f"[OSS] 文件上传成功 (大小: {file_size / 1024:.2f}KB)")
        print(f"[OSS] 原始路径: {object_name}")
        print(f"[OSS] 安全措施: UUID混淆 + 签名URL(1小时有效) + 自动清理")

        return signed_url, object_name

    def _cleanup_oss_file(self, object_name: str) -> None:
        """
        清理OSS文件（识别完成后调用）

        Args:
            object_name: OSS对象名称
        """
        if not OSS_AUTO_CLEANUP:
            print(f"[OSS] 自动清理已禁用，保留文件: {object_name}")
            return

        # 验证OSS配置（清理时如果配置缺失，静默失败）
        if not OSS_ACCESS_KEY_ID or not OSS_ACCESS_KEY_SECRET or not OSS_BUCKET_NAME:
            print(f"[OSS] 警告: OSS配置不完整，无法清理文件: {object_name}")
            return

        try:
            auth = oss2.Auth(OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET)
            bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET_NAME)

            # 删除文件
            bucket.delete_object(object_name)
            print(f"[OSS] 已删除临时文件: {object_name}")

        except Exception as e:
            print(f"[OSS] 删除文件失败（非致命错误）: {e}")

    def _single_node_recognize(self, audio_path: str, node_id: int = 0) -> str:
        """
        单节点ASR识别（带OSS自动清理）

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

        # 上传音频到OSS（安全加固版本）
        audio_url, object_name = self._upload_to_oss(audio_path)

        try:
            # 使用Fun-ASR文件识别API
            from http import HTTPStatus
            from dashscope.audio.asr import Transcription

            # 调用异步文件识别
            task_response = Transcription.async_call(
                model=ASR_MODEL,
                file_urls=[audio_url],
                language_hints=ASR_LANGUAGE_HINTS,  # 优化的语言提示（中英法混合）
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

                    # 识别完成后清理OSS文件
                    self._cleanup_oss_file(object_name)

                    return text

                elif task_status in ["PENDING", "RUNNING"]:
                    if i % 10 == 0:  # 每20秒打印一次
                        print(f"[ASR节点{node_id}] 任务状态: {task_status}, 等待中... ({i + 1}/{max_retries})")
                    time.sleep(2)
                else:
                    raise Exception(f"ASR任务状态异常: {task_status}")

            raise Exception(f"[ASR节点{node_id}] 任务超时")

        except Exception as e:
            # 发生异常时也尝试清理OSS文件
            print(f"[ASR节点{node_id}] 识别失败: {e}")
            self._cleanup_oss_file(object_name)
            raise

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
        # 检查停止标志（在开始处理前）
        if self._check_stop():
            print("[ASR] 检测到停止请求，终止识别")
            raise Exception("ASR识别已取消：用户请求停止")

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
            result = self._distributed_recognize(audio_path)
        else:
            # 使用单节点ASR（带重试）
            result = self._single_node_with_retry(audio_path)

        # 检查停止标志（在API返回后）
        if self._check_stop():
            print("[ASR] 检测到停止请求，丢弃识别结果")
            raise Exception("ASR识别已取消：用户请求停止")

        return result

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
        if self.distributed_asr is None:
            raise RuntimeError("分布式ASR未初始化，请检查ENABLE_DISTRIBUTED_ASR配置")

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
        应用ASR质量评分和校正（增强版：LLM后处理 + 评分数据收集）

        Args:
            text: 识别的文本
            audio_path: 音频文件路径
            retry_count: 当前重试次数

        Returns:
            可能经过校正的文本
        """
        if self.asr_scorer is None:
            return text

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

        # 添加评分记录到历史（用于建立基线和自适应阈值）
        self._add_score_record(score_result.overall_score, audio_path, len(text))

        # LLM后处理修复（针对低分文本）
        if score_result.overall_score < ASR_LLM_POSTPROCESS_THRESHOLD:
            text = self._llm_postprocess_asr(text, score_result.overall_score)

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
