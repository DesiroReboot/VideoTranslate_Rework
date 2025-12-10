"""
配置文件 - 视频翻译系统
管理所有API密钥和系统参数
"""

import os
from pathlib import Path

# ==================== API配置 ====================
# 阿里云API Key - 请在环境变量中配置 DASHSCOPE_API_KEY
# Windows设置方式: setx DASHSCOPE_API_KEY "your_api_key_here"
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")

# 阿里云API基础URL (北京地域)
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com"

# ==================== 模型配置 ====================
# 语音识别模型 (ASR)
ASR_MODEL = "sensevoice-v1"  # 支持50+语言,适合多语言视频

# 机器翻译模型 (MT)
MT_MODEL = "qwen-mt-plus"  # 高质量翻译,支持92种语言

# 语音合成模型 (TTS)
TTS_MODEL = "qwen3-tts-flash"  # 49种音色,支持多语言

# ==================== TTS音色配置 ====================
# 根据目标语言自动选择合适音色
TTS_VOICE_MAP = {
    "Chinese": "Cherry",        # 中文女声
    "English": "Emily",         # 英文女声
    "Japanese": "Yuki",         # 日文女声
    "Korean": "Seoyeon",        # 韩文女声
    "Spanish": "Sofia",         # 西班牙文女声
    "French": "Amelie",         # 法文女声
    "German": "Hanna",          # 德文女声
    "Russian": "Daria",         # 俄文女声
    "Italian": "Giulia",        # 意大利文女声
    "Portuguese": "Camila",     # 葡萄牙文女声
}

DEFAULT_VOICE = "Cherry"  # 默认音色

# ==================== 文件路径配置 ====================
# 项目根目录
PROJECT_ROOT = Path(__file__).parent

# 临时文件目录
TEMP_DIR = PROJECT_ROOT / "temp"
TEMP_DIR.mkdir(exist_ok=True)

# 输出文件目录
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# ==================== 下载配置 ====================
# yt-dlp下载参数
YT_DLP_OPTIONS = {
    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
    'outtmpl': str(TEMP_DIR / '%(title)s.%(ext)s'),
    'quiet': False,
    'no_warnings': False,
}

# ==================== 音视频参数 ====================
# 音频采样率
AUDIO_SAMPLE_RATE = 24000

# 音频格式
AUDIO_FORMAT = "mp3"

# 视频编码参数
VIDEO_CODEC = "libx264"
AUDIO_CODEC = "aac"

# ==================== 翻译参数配置 ====================
# 从Prompt_Video_Translate.txt读取系统提示词
TRANSLATION_SYSTEM_PROMPT_FILE = PROJECT_ROOT / "Prompt_Video_Translate.txt"

def load_translation_prompt(target_language: str) -> str:
    """
    加载翻译系统提示词并替换目标语言
    
    Args:
        target_language: 目标语言
        
    Returns:
        格式化后的系统提示词
    """
    if TRANSLATION_SYSTEM_PROMPT_FILE.exists():
        content = TRANSLATION_SYSTEM_PROMPT_FILE.read_text(encoding='utf-8')
        return content.replace("{target_language}", target_language)
    else:
        return f"You are a professional translator. Translate the following text to {target_language}."

# ==================== 验证函数 ====================
def validate_config():
    """验证配置是否正确"""
    if not DASHSCOPE_API_KEY:
        raise ValueError(
            "未配置DASHSCOPE_API_KEY!\n"
            "请在环境变量中设置: setx DASHSCOPE_API_KEY \"your_api_key_here\""
        )
    
    if not TRANSLATION_SYSTEM_PROMPT_FILE.exists():
        print(f"警告: 未找到翻译提示词文件 {TRANSLATION_SYSTEM_PROMPT_FILE}")
    
    return True
