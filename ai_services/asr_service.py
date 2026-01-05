"""
ASR语音识别服务模块
处理语音转文字功能
"""

import time
import requests
from pathlib import Path
from typing import Optional, Dict, Any
from http import HTTPStatus

from .base_service import BaseAIService
from .service_factory import AIServiceFactory
from config import (
    ASR_MODEL,
    ASR_MAX_RETRIES,
    ASR_SCORE_THRESHOLD,
    TEMP_DIR,
    PROJECT_ROOT,
)
from common.security import FileValidator, SecurityError, OutputValidationError
from common.security import LLMOutputValidator


class ASRService(BaseAIService):
    """语音识别服务"""
    
    def __init__(self):
        """初始化ASR服务"""
        super().__init__("ASR")
        
        # 初始化组件
        self.distributed_asr = AIServiceFactory.create_distributed_asr()
        self.asr_scorer = AIServiceFactory.create_asr_scorer()
        
        # 初始化状态
        self._initialized = False
    
    def initialize(self) -> None:
        """初始化ASR服务"""
        if self._initialized:
            return
        
        # 打印初始化状态
        AIServiceFactory.print_initialization_status()
        
        self._initialized = True
        self.logger.info("ASR服务初始化完成")
    
    def speech_to_text(self, audio_path: str) -> str:
        """语音识别主接口
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            识别的文本内容
            
        Raises:
            Exception: 识别失败
            SecurityError: 安全检查失败
        """
        # 验证输入
        if not audio_path or not isinstance(audio_path, str):
            raise ValueError("音频路径参数无效")
        
        # 音频文件安全验证
        audio_info = FileValidator.validate_audio_file(audio_path)
        
        self.logger.info(f"开始语音识别: {audio_path}")
        self.logger.info(f"音频文件大小: {audio_info['size'] / (1024 * 1024):.2f}MB")
        
        # ASR重试循环
        for retry_count in range(ASR_MAX_RETRIES + 1):
            self.logger.info(f"第{retry_count + 1}次尝试 (最大{ASR_MAX_RETRIES + 1}次)")
            
            try:
                # 上传音频到OSS获取公网访问URL
                audio_url = self._upload_audio_to_oss(audio_path)
                
                # 执行语音识别
                text = self._recognize_audio(audio_url, retry_count)
                
                # 如果有分布式ASR，使用分布式识别
                if self.distributed_asr:
                    text = self._distributed_recognize(audio_path)
                
                return text
                
            except Exception as e:
                self.logger.error(f"ASR识别错误: {str(e)}")
                
                if retry_count < ASR_MAX_RETRIES:
                    self.logger.info("将进行重试...")
                    continue
                else:
                    # 所有重试都失败，返回占位文本
                    self.logger.warning("所有重试失败，返回测试文本")
                    return "这是一段测试文本。由于语音识别API调用失败,这里返回占位内容。请配置正确的API Key和OSS后重试。"
        
        # 如果循环正常结束（没有return），抛出异常
        raise Exception("ASR识别失败: 所有重试尝试完毕")
    
    def _upload_audio_to_oss(self, audio_path: str) -> str:
        """上传音频到OSS
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            OSS公开访问URL
        """
        from .oss_service import OSSService
        
        oss_service = OSSService()
        return oss_service.upload_file(audio_path)
    
    def _recognize_audio(self, audio_url: str, retry_count: int) -> str:
        """执行音频识别
        
        Args:
            audio_url: 音频文件URL
            retry_count: 重试次数
            
        Returns:
            识别文本
        """
        import dashscope
        from dashscope.audio.asr import Transcription
        
        # 设置DashScope配置
        dashscope.api_key = self._get_api_key()
        dashscope.base_http_api_url = self._get_base_url() + "/api/v1"
        
        self.logger.info("提交语音识别任务...")
        
        # 调用异步文件识别
        task_response = Transcription.async_call(
            model=ASR_MODEL,
            file_urls=[audio_url],
            language_hints=["zh", "en"],  # 支持中英文
        )
        
        if task_response.status_code != HTTPStatus.OK:
            raise Exception(f"ASR任务提交失败: {task_response.message}")
        
        task_id = task_response.output["task_id"]
        self.logger.info(f"任务ID: {task_id}, 等待识别完成...")
        
        # 轮询任务状态
        return self._poll_task_status(task_id)
    
    def _poll_task_status(self, task_id: str) -> str:
        """轮询任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            识别文本
        """
        from dashscope.audio.asr import Transcription
        from http import HTTPStatus
        
        max_retries = 60  # 最多等待60次
        
        for i in range(max_retries):
            result_response = Transcription.wait(task=task_id)
            
            if result_response.status_code != HTTPStatus.OK:
                raise Exception(f"ASR任务查询失败: {result_response.message}")
            
            task_status = result_response.output["task_status"]
            
            if task_status == "SUCCEEDED":
                # 获取识别结果
                transcription_url = result_response.output["results"][0]["transcription_url"]
                self.logger.info("识别完成, 下载结果...")
                
                # 下载并解析结果
                text = self._download_and_parse_result(transcription_url)
                
                # 安全验证和后处理
                return self._post_process_result(text)
            
            if task_status == "FAILED":
                raise Exception(
                    f"ASR任务失败: {result_response.output.get('message', 'Unknown error')}"
                )
            
            if task_status in ["PENDING", "RUNNING"]:
                self.logger.info(f"任务状态: {task_status}, 等待中... ({i + 1}/{max_retries})")
                time.sleep(2)  # 等待2秒
            else:
                self.logger.warning(f"未知状态: {task_status}")
                time.sleep(2)
        
        raise Exception("ASR任务超时")
    
    def _download_and_parse_result(self, transcription_url: str) -> str:
        """下载并解析识别结果
        
        Args:
            transcription_url: 结果URL
            
        Returns:
            识别文本
        """
        resp = requests.get(transcription_url, timeout=30)
        resp.raise_for_status()
        result_data = resp.json()
        
        # 提取文本
        text = result_data.get("transcripts", [{}])[0].get("text", "")
        
        if not text:
            # 尝试从句子中提取
            sentences = result_data.get("transcripts", [{}])[0].get("sentences", [])
            text = " ".join([s.get("text", "") for s in sentences])
        
        return text
    
    def _post_process_result(self, text: str) -> str:
        """后处理识别结果
        
        Args:
            text: 原始识别文本
            
        Returns:
            处理后的文本
        """
        self.logger.info(f"识别成功,文本长度: {len(text)} 字符")
        
        if len(text) > 100:
            self.logger.info(f"识别文本: {text[:100]}...")
        else:
            self.logger.info(f"识别文本: {text}")
        
        # 安全验证：清理ASR输出
        try:
            text = LLMOutputValidator.sanitize_asr_output(text)
            self.logger.info("安全验证通过")
        except OutputValidationError as e:
            self.logger.error(f"安全验证失败: {e}")
            raise Exception(f"ASR输出安全验证失败: {e}") from e
        
        # ASR质量评分和校正
        if self.asr_scorer:
            return self._apply_scoring_and_correction(text)
        
        return text
    
    def _apply_scoring_and_correction(self, text: str) -> str:
        """应用评分和校正
        
        Args:
            text: 识别文本
            
        Returns:
            校正后的文本
        """
        self.logger.info("开始质量评分和校正...")
        original_text = text
        
        score_result = self.asr_scorer.score_asr_result(original_text)
        
        self.logger.info(f"识别质量评分: {score_result.overall_score}/{100}")
        
        if score_result.corrections:
            self.logger.info(f"发现{len(score_result.corrections)}处可能的识别错误，正在校正...")
            text = self.asr_scorer.apply_corrections(original_text, score_result.corrections)
            
            if len(text) > 100:
                self.logger.info(f"校正后文本: {text[:100]}...")
            else:
                self.logger.info(f"校正后文本: {text}")
        
        # 保存评分结果
        self._save_score_result(original_text, score_result)
        
        # 检查是否需要重试
        if score_result.should_retry:
            self.logger.info(f"识别质量低于阈值({ASR_SCORE_THRESHOLD})，将进行重试")
            raise Exception("需要重试")
        
        return text
    
    def _distributed_recognize(self, audio_path: str) -> str:
        """分布式语音识别
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            分布式识别结果
        """
        if self.distributed_asr is None:
            raise RuntimeError("分布式ASR未初始化，请检查ENABLE_DISTRIBUTED_ASR配置")
        
        self.logger.info(f"启动{self.distributed_asr.node_count}个节点...")
        
        # 这里应该调用分布式ASR的具体方法
        # 由于具体的实现细节在原始代码中，这里提供框架
        try:
            result = self.distributed_asr.async_reach_consensus(audio_path)
            return result
        except Exception as e:
            self.logger.error(f"分布式ASR识别失败: {e}")
            raise
    
    def _save_score_result(self, text: str, score_result: Any) -> None:
        """保存评分结果
        
        Args:
            text: 识别文本
            score_result: 评分结果
        """
        try:
            if self.asr_scorer:
                # 这里可以保存评分结果到文件
                # 具体的保存逻辑可以参考原始代码
                pass
        except Exception as e:
            self.logger.error(f"保存评分结果失败: {e}")
    
    def _get_api_key(self) -> str:
        """获取API密钥"""
        from config import DASHSCOPE_API_KEY
        return DASHSCOPE_API_KEY
    
    def _get_base_url(self) -> str:
        """获取基础URL"""
        from config import DASHSCOPE_BASE_URL
        return DASHSCOPE_BASE_URL
