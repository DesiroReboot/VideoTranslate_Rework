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

# 向后兼容性：导入旧版完整的AIServices类
# 旧版类位于项目根目录的ai_services.py中，包含speech_to_text, translate_text, text_to_speech等方法
import sys
import importlib.util

# 加载项目根目录的ai_services.py模块
_spec = importlib.util.spec_from_file_location(
    "ai_services_legacy", 
    str(__file__).replace("ai_services\\__init__.py", "ai_services.py").replace("ai_services/__init__.py", "ai_services.py")
)
if _spec and _spec.loader:
    _legacy_module = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_legacy_module)
    AIServices = _legacy_module.AIServices  # 向后兼容性
else:
    # 如果加载失败，使用TranslationService作为后备
    AIServices = TranslationService

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
