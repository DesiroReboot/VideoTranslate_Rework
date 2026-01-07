"""
统一日志模块
提供格式化的日志输出，同时支持终端显示、文件持久化和UI回调
"""

import sys
import logging
import time
from datetime import datetime
from typing import Optional, Callable, List


class LogCallback:
    """日志回调处理器，用于将日志同步到UI"""

    def __init__(self):
        self._callbacks: List[Callable[[str], None]] = []

    def register(self, callback: Callable[[str], None]) -> None:
        """注册日志回调函数"""
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def unregister(self, callback: Callable[[str], None]) -> None:
        """注销日志回调函数"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def emit(self, message: str) -> None:
        """触发所有注册的回调"""
        for callback in self._callbacks:
            try:
                callback(message)
            except Exception:
                pass  # 回调失败不中断日志


# 全局日志回调实例
log_callback = LogCallback()

# 日志级别映射
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

# 默认日志格式
DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def setup_logger(
    name: str = "VideoTranslate",
    level: str = "INFO",
    log_file: Optional[str] = "video_translate.log",
    format_str: Optional[str] = None,
    enable_console: bool = True,
) -> logging.Logger:
    """
    设置日志系统

    Args:
        name: 日志名称
        level: 日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
        log_file: 日志文件路径，None表示不写入文件
        format_str: 日志格式字符串
        enable_console: 是否输出到控制台

    Returns:
        配置好的Logger实例
    """
    # 获取或创建logger
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVELS.get(level.upper(), logging.INFO))

    # 清除已有的处理器（避免重复）
    logger.handlers.clear()

    # 设置日志格式
    if format_str is None:
        format_str = DEFAULT_FORMAT
    formatter = logging.Formatter(format_str)

    # 控制台处理器 - 禁用缓冲区实现实时输出
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(LOG_LEVELS.get(level.upper(), logging.INFO))
        console_handler.setFormatter(formatter)
        # 强制刷新每个日志消息
        console_handler.flush = sys.stdout.flush
        logger.addHandler(console_handler)

    # 文件处理器
    if log_file:
        try:
            # 确保目录存在
            import os
            os.makedirs(os.path.dirname(log_file) if os.path.dirname(log_file) else ".", exist_ok=True)

            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(LOG_LEVELS.get(level.upper(), logging.INFO))
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception:
            pass  # 文件写入失败不影响日志输出

    return logger


def log_message(
    tag: str,
    content: str,
    level: str = "INFO",
    logger: Optional[logging.Logger] = None,
    file_only: bool = False,
) -> str:
    """
    统一的日志消息输出

    Args:
        tag: 标签，如 [初始化], [翻译], [模型] 等
        content: 消息内容
        level: 日志级别
        logger: 使用的logger实例，None则使用默认logger
        file_only: 是否只写入文件（不打印到控制台）

    Returns:
        格式化后的完整消息字符串
    """
    # 格式化消息
    timestamp = datetime.now().strftime("%H:%M:%S")
    full_message = f"[{timestamp}] [{tag}] {content}"

    # 获取logger
    if logger is None:
        logger = logging.getLogger("VideoTranslate")

    # 根据级别输出
    if level.upper() == "DEBUG":
        logger.debug(full_message)
    elif level.upper() == "INFO":
        if file_only:
            # 临时禁用控制台处理器，只写入文件
            for handler in logger.handlers:
                if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
                    handler.setLevel(logging.CRITICAL + 1)  # 临时禁用
            logger.info(full_message)
            # 恢复控制台处理器
            for handler in logger.handlers:
                if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
                    handler.setLevel(logging.INFO)
        else:
            logger.info(full_message)
    elif level.upper() == "WARNING":
        logger.warning(full_message)
    elif level.upper() == "ERROR":
        logger.error(full_message)
    elif level.upper() == "CRITICAL":
        logger.critical(full_message)

    # 同步到UI回调
    log_callback.emit(full_message)

    return full_message


def log_api_call(
    api_name: str,
    status: str,
    details: Optional[str] = None,
    duration: Optional[float] = None,
    logger: Optional[logging.Logger] = None,
) -> None:
    """
    记录API调用日志

    Args:
        api_name: API名称
        status: 状态 (成功/失败/重试)
        details: 详细信息
        duration: 耗时（秒）
        logger: 使用的logger实例
    """
    content = f"{api_name}: {status}"
    if details:
        content += f" | {details}"
    if duration is not None:
        content += f" | 耗时: {duration:.2f}秒"

    log_message("API调用", content, level="INFO", logger=logger)


def log_step(
    step: int,
    total: int,
    name: str,
    status: str = "进行中",
    logger: Optional[logging.Logger] = None,
) -> None:
    """
    记录步骤进度日志

    Args:
        step: 当前步骤
        total: 总步骤数
        name: 步骤名称
        status: 状态
        logger: 使用的logger实例
    """
    content = f"[{step}/{total}] {name} - {status}"
    log_message("步骤进度", content, level="INFO", logger=logger)


def log_consensus(
    method: str,
    result: str,
    coefficient: Optional[float] = None,
    logger: Optional[logging.Logger] = None,
) -> None:
    """
    记录共识机制结果日志

    Args:
        method: 共识方法
        result: 结果描述
        coefficient: 相似度系数
        logger: 使用的logger实例
    """
    content = f"{method}: {result}"
    if coefficient is not None:
        content += f" | 相似度: {coefficient:.4f}"
    log_message("共识系统", content, level="INFO", logger=logger)


# 便捷函数
def info(tag: str, content: str) -> str:
    """输出INFO级别日志"""
    return log_message(tag, content, level="INFO")


def warning(tag: str, content: str) -> str:
    """输出WARNING级别日志"""
    return log_message(tag, content, level="WARNING")


def error(tag: str, content: str) -> str:
    """输出ERROR级别日志"""
    return log_message(tag, content, level="ERROR")


def debug(tag: str, content: str) -> str:
    """输出DEBUG级别日志"""
    return log_message(tag, content, level="DEBUG")


# 初始化默认logger
_default_logger = setup_logger()
