"""
AI服务基础模块
提供所有AI服务的共同功能
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from config import (
    DASHSCOPE_API_KEY,
    DASHSCOPE_BASE_URL,
    ENABLE_ASR_SCORING,
    ENABLE_TRANSLATION_SCORING,
    ENABLE_DISTRIBUTED_ASR,
    DISTRIBUTED_ASR_NODE_COUNT,
    DISTRIBUTED_ASR_COEFFICIENT_THRESHOLD,
    DISTRIBUTED_ASR_ENABLE_QUALITY_EVAL,
)
from common.security import (
    SecurityError,
    InputValidator,
    LLMOutputValidator,
    OutputValidationError,
)


class BaseAIService(ABC):
    """AI服务基础类"""
    
    def __init__(self, service_name: str):
        """初始化基础服务
        
        Args:
            service_name: 服务名称，用于日志和错误追踪
        """
        self.service_name = service_name
        self.logger = logging.getLogger(f"AI.{service_name}")
        self._validate_api_config()
    
    def _validate_api_config(self) -> None:
        """验证API配置"""
        if not DASHSCOPE_API_KEY:
            raise ValueError("未配置DASHSCOPE_API_KEY,请在环境变量中设置")
        
        # 验证API密钥格式 (假设是sk-开头的格式)
        if not DASHSCOPE_API_KEY.startswith("sk-") or len(DASHSCOPE_API_KEY) < 20:
            raise SecurityError("API密钥格式无效")
        
        # 验证基础URL
        if not DASHSCOPE_BASE_URL or not DASHSCOPE_BASE_URL.startswith("https://"):
            raise SecurityError("DASHSCOPE_BASE_URL配置无效")
    
    @abstractmethod
    def initialize(self) -> None:
        """初始化服务，具体实现由子类完成"""
        pass
    
    def validate_input(self, text: str, max_length: int = 10000, 
                      context: str = "输入验证") -> str:
        """验证输入文本
        
        Args:
            text: 待验证文本
            max_length: 最大长度限制
            context: 验证上下文
            
        Returns:
            验证后的文本
            
        Raises:
            ValueError: 输入无效
        """
        return InputValidator.validate_text_input(
            text, max_length=max_length, min_length=1, context=context
        )
    
    def validate_llm_output(self, output: str, context: str = "LLM输出") -> str:
        """验证LLM输出
        
        Args:
            output: LLM输出文本
            context: 验证上下文
            
        Returns:
            验证后的文本
            
        Raises:
            OutputValidationError: 输出验证失败
        """
        try:
            return LLMOutputValidator.sanitize_translation_output(output)
        except OutputValidationError as e:
            self.logger.error(f"{context}安全验证失败: {e}")
            raise SecurityError(f"{context}安全验证失败: {e}") from e
    
    def get_service_info(self) -> Dict[str, Any]:
        """获取服务信息
        
        Returns:
            服务基本信息字典
        """
        return {
            "service_name": self.service_name,
            "class_name": self.__class__.__name__,
            "api_configured": bool(DASHSCOPE_API_KEY),
            "base_url": DASHSCOPE_BASE_URL,
        }
