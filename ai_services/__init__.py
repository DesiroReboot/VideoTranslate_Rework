"""
AI服务模块 - 重构后的模块化版本
提供语音识别、翻译、语音合成等功能
"""

from .base_service import BaseAIService
from .service_factory import AIServiceFactory
from .asr_service import ASRService
from .translation_service import TranslationService
from .tts_service import TTSService
from .oss_service import OSSService

# 向后兼容性别名
AIServices = TranslationService  # 为了保持向后兼容性

__all__ = [
    "BaseAIService",
    "AIServiceFactory", 
    "ASRService",
    "TranslationService",
    "TTSService", 
    "OSSService",
    "AIServices",  # 向后兼容性
]

# 版本信息
__version__ = "2.0.0"
__author__ = "VideoTranslate Team"
