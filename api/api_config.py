"""
API 配置文件
管理API服务器的参数配置，从环境变量读取
"""

import os
from typing import Optional

# ==================== 服务器配置 ====================
# API服务器主机地址 - 从环境变量读取，默认localhost
API_HOST = os.getenv("VIDEO_TRANSLATE_API_HOST", "127.0.0.1")

# API服务器端口 - 从环境变量读取，默认8000
API_PORT = int(os.getenv("VIDEO_TRANSLATE_API_PORT", "8000"))

# API服务器URL
API_BASE_URL = f"http://{API_HOST}:{API_PORT}"

# 调试模式
API_DEBUG = os.getenv("VIDEO_TRANSLATE_API_DEBUG", "false").lower() == "true"

# ==================== CORS配置 ====================
# 允许的源地址 - 从环境变量读取，逗号分隔
CORS_ORIGINS = os.getenv("VIDEO_TRANSLATE_CORS_ORIGINS", "*").split(",")

# ==================== 任务配置 ====================
# 任务会话超时时间（秒）
TASK_TIMEOUT = int(os.getenv("VIDEO_TRANSLATE_TASK_TIMEOUT", "3600"))

# 最大并发任务数
MAX_CONCURRENT_TASKS = int(os.getenv("VIDEO_TRANSLATE_MAX_CONCURRENT_TASKS", "1"))

# ==================== 日志配置 ====================
# 日志级别
LOG_LEVEL = os.getenv("VIDEO_TRANSLATE_LOG_LEVEL", "INFO")
