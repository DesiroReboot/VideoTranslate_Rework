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
# 语音识别模型 (ASR) - 使用Fun-ASR支持文件URL识别
ASR_MODEL = "fun-asr"  # 支持50+语言,适合多语言视频,支持文件URL识别

# 机器翻译模型 (MT)
MT_MODEL = "qwen-max"  # 使用Qwen3-max，支持自定义prompt

# 语音合成模型 (TTS)
TTS_MODEL = "qwen3-tts-flash"  # 49种音色,支持多语言

# OSS
OSS_ENDPOINT = "oss-cn-hangzhou.aliyuncs.com"
OSS_ACCESS_KEY_ID = os.getenv("OSS_ACCESS_KEY_ID")
OSS_ACCESS_KEY_SECRET = os.getenv("OSS_ACCESS_KEY_SECRET")
OSS_BUCKET_NAME = os.getenv("OSS_BUCKET_NAME")

# ==================== TTS音色配置 ====================
# 根据目标语言自动选择合适音色
TTS_VOICE_MAP = {
    "Chinese": "Cherry",        # ✅ 阿里云标准名称（中文女声）
    "English": "Cherry",           # ✅ 阿里云标准名称（英文女声）
    "Japanese": "Cherry",        # ✅ 阿里云标准名称（日文女声）
    "Korean": "Cherry",          # ✅ 阿里云标准名称（韩文女声）
    "Spanish": "Cherry",         # ✅ 阿里云标准名称（西班牙语女声）
    "French": "Cherry",          # ✅ 阿里云标准名称（法语女声）
    "German": "Cherry",           # ✅ 阿里云标准名称（德文女声）
    "Russian": "Cherry",          # ✅ 阿里云标准名称（俄文女声）
    "Italian": "Cherry",         # ✅ 阿里云标准名称（意大利语女声）
    "Portuguese": "Cherry",      # ✅ 阿里云标准名称（葡萄牙语女声）
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
    # 修复HTTP 412 - 使用更通用的格式选择
    # 优先选择720P，如果失败则自动降级
    'format': 'bestvideo[height<=720]+bestaudio/best[height<=720]/bestvideo+bestaudio/best',
    'outtmpl': str(TEMP_DIR / '%(epoch)s.%(ext)s'),  # 使用时间戳避免中文文件名
    'merge_output_format': 'mp4',  # 合并为mp4格式
    'quiet': False,
    'no_warnings': False,
    # 修复HTTP 412错误 - 添加B站需要的请求头
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.bilibili.com/',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Origin': 'https://www.bilibili.com',
    },
    # 添加Cookie支持（如果需要登录观看的视频）
    # 'cookiefile': str(PROJECT_ROOT / 'bilibili_cookies.txt'),  # 如果有cookie文件再启用
    # 其他重要选项
    'nocheckcertificate': True,  # 忽略SSL证书验证问题
    'geo_bypass': True,  # 绕过地理限制
}

# B站Cookie配置（可选 - 用于下载需要登录的视频）
# 设置方式：
# 1. 在浏览器登录B站
# 2. 导出Cookie到文件
# 3. 取消下面的注释并设置路径
# BILIBILI_COOKIE_FILE = PROJECT_ROOT / "bilibili_cookies.txt"

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

# ==================== 翻译质量评分配置 ====================
# 评分使用的模型
SCORING_MODEL = "qwen-max"

# 评分阈值 - 低于此分数将触发重试
SCORE_THRESHOLD = 70

# 最大重试次数
MAX_RETRIES = 2

# 是否启用翻译质量评分
ENABLE_TRANSLATION_SCORING = True

# 评分结果保存目录
SCORING_RESULTS_DIR = OUTPUT_DIR / "scoring_results"
SCORING_RESULTS_DIR.mkdir(exist_ok=True)

# ==================== ASR质量评分配置 ====================
# ASR评分阈值 - 低于此分数将触发重试
ASR_SCORE_THRESHOLD = 60

# ASR最大重试次数
ASR_MAX_RETRIES = 1

# 是否启用ASR质量评分
ENABLE_ASR_SCORING = True

# ASR评分结果保存目录
ASR_SCORING_RESULTS_DIR = OUTPUT_DIR / "asr_scoring_results"
ASR_SCORING_RESULTS_DIR.mkdir(exist_ok=True)

# ASR常见错误映射 - 用于校正识别结果
ASR_ERROR_MAPPINGS = {
    "阿萨": {
        "corrected": "阿SIR",
        "context_keywords": ["警察", "抓", "追", "查", "办案", "执法", "嫌疑", "罪犯"],
        "description": "ASR将'阿SIR'错误识别为'阿萨'"
    },
    # 可以添加更多ASR错误映射
}

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
