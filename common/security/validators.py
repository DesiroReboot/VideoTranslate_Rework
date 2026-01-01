"""
安全验证器模块
包含所有输入验证、路径安全、资源管理等安全机制
遵循 OWASP 安全规范和项目安全最佳实践
"""

import re
import os
import html
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

# 配置日志
logger = logging.getLogger(__name__)


# ==================== 异常类定义 ====================


class SecurityError(Exception):
    """安全相关异常"""

    pass


class OutputValidationError(Exception):
    """LLM输出验证异常"""

    pass


class PathTraversalError(SecurityError):
    """路径遍历攻击异常"""

    pass


class FileValidationError(SecurityError):
    """文件验证异常"""

    pass


# ==================== 路径安全验证器 ====================


class PathSecurityValidator:
    """路径安全验证器 - 防止路径遍历攻击"""

    @staticmethod
    def validate_path_in_project(
        file_path: str, project_root: str, allow_symlinks: bool = False
    ) -> Path:
        """
        验证文件路径在项目目录内（防止路径遍历攻击）

        Args:
            file_path: 待验证的文件路径
            project_root: 项目根目录
            allow_symlinks: 是否允许符号链接

        Returns:
            解析后的绝对路径

        Raises:
            PathTraversalError: 检测到路径遍历攻击
        """
        try:
            file_path_obj = Path(file_path)
            resolved_path = file_path_obj.resolve()
            project_root_resolved = Path(project_root).resolve()

            # 验证路径在项目目录内
            resolved_path.relative_to(project_root_resolved)

            # 检查符号链接
            if not allow_symlinks and file_path_obj.is_symlink():
                raise PathTraversalError(f"不允许符号链接: {file_path}")

            return resolved_path

        except (ValueError, RuntimeError):
            raise PathTraversalError(f"检测到路径遍历攻击: {file_path}")

    @staticmethod
    def validate_object_name(object_name: str) -> str:
        """
        验证对象名不包含危险字符

        Args:
            object_name: 对象名称

        Returns:
            验证后的对象名

        Raises:
            SecurityError: 对象名包含非法字符
        """
        # 禁止 ..
        if ".." in object_name:
            raise SecurityError(f"对象名包含非法字符 '..': {object_name}")

        # 禁止绝对路径
        if object_name.startswith("/") or (
            len(object_name) > 1 and object_name[1] == ":"
        ):
            raise SecurityError(f"对象名不能是绝对路径: {object_name}")

        return object_name

    @staticmethod
    def sanitize_filename(filename: str, max_length: int = 255) -> str:
        """
        清理文件名，移除危险字符

        Args:
            filename: 原始文件名
            max_length: 最大长度

        Returns:
            清理后的安全文件名
        """
        # 移除路径分隔符
        filename = filename.replace("/", "_").replace("\\", "_")

        # 移除危险字符，只保留字母数字和._-
        safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)

        # 限制长度
        if len(safe_name) > max_length:
            name, ext = os.path.splitext(safe_name)
            safe_name = name[: max_length - len(ext)] + ext

        return safe_name


# ==================== 文件验证器 ====================


class FileValidator:
    """文件验证器 - 验证文件类型、大小等"""

    # 允许的文件扩展名
    ALLOWED_VIDEO_EXTENSIONS = [".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv"]
    ALLOWED_AUDIO_EXTENSIONS = [".mp3", ".wav", ".m4a", ".flac", ".aac"]

    # 文件大小限制
    MAX_VIDEO_SIZE = 500 * 1024 * 1024  # 500MB
    MAX_AUDIO_SIZE = 100 * 1024 * 1024  # 100MB

    @staticmethod
    def validate_file_exists(file_path: str) -> Path:
        """验证文件存在"""
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise FileValidationError(f"文件不存在: {file_path}")
        if not file_path_obj.is_file():
            raise FileValidationError(f"不是有效文件: {file_path}")
        return file_path_obj

    @staticmethod
    def validate_file_extension(file_path: str, allowed_extensions: List[str]) -> str:
        """
        验证文件扩展名

        Args:
            file_path: 文件路径
            allowed_extensions: 允许的扩展名列表

        Returns:
            文件扩展名

        Raises:
            FileValidationError: 扩展名不在白名单中
        """
        file_path_obj = Path(file_path)
        ext = file_path_obj.suffix.lower()

        if ext not in allowed_extensions:
            raise FileValidationError(
                f"不支持的文件格式: {ext}\n允许的格式: {', '.join(allowed_extensions)}"
            )

        return ext

    @staticmethod
    def validate_file_size(file_path: str, max_size: int, min_size: int = 1) -> int:
        """
        验证文件大小

        Args:
            file_path: 文件路径
            max_size: 最大大小（字节）
            min_size: 最小大小（字节）

        Returns:
            文件大小

        Raises:
            FileValidationError: 文件大小不符合要求
        """
        file_path_obj = Path(file_path)
        file_size = file_path_obj.stat().st_size

        if file_size == 0 or file_size < min_size:
            raise FileValidationError(f"文件为空或过小: {file_size} bytes")

        if file_size > max_size:
            raise FileValidationError(
                f"文件过大: {file_size / 1024 / 1024:.2f}MB "
                f"(限制: {max_size / 1024 / 1024:.0f}MB)"
            )

        return file_size

    @staticmethod
    def validate_video_file(file_path: str) -> Dict[str, Any]:
        """
        验证视频文件（综合验证）

        Returns:
            包含文件信息的字典
        """
        # 验证存在性
        file_path_obj = FileValidator.validate_file_exists(file_path)

        # 验证扩展名
        ext = FileValidator.validate_file_extension(
            file_path, FileValidator.ALLOWED_VIDEO_EXTENSIONS
        )

        # 验证文件大小
        file_size = FileValidator.validate_file_size(
            file_path, FileValidator.MAX_VIDEO_SIZE
        )

        return {"path": file_path_obj, "extension": ext, "size": file_size}

    @staticmethod
    def validate_audio_file(file_path: str) -> Dict[str, Any]:
        """
        验证音频文件（综合验证）

        Returns:
            包含文件信息的字典
        """
        # 验证存在性
        file_path_obj = FileValidator.validate_file_exists(file_path)

        # 验证扩展名
        ext = FileValidator.validate_file_extension(
            file_path, FileValidator.ALLOWED_AUDIO_EXTENSIONS
        )

        # 验证文件大小
        file_size = FileValidator.validate_file_size(
            file_path, FileValidator.MAX_AUDIO_SIZE
        )

        return {"path": file_path_obj, "extension": ext, "size": file_size}


# ==================== 输入验证器 ====================


class InputValidator:
    """输入验证器 - 验证用户输入"""

    # 允许的语言列表
    ALLOWED_LANGUAGES = [
        "Chinese",
        "English",
        "Japanese",
        "Korean",
        "Spanish",
        "French",
        "German",
        "Russian",
        "Italian",
        "Portuguese",
        "Arabic",
        "Hindi",
        "auto",
    ]

    @staticmethod
    def validate_text_input(
        text: str, max_length: int = 10000, min_length: int = 1, context: str = "输入"
    ) -> str:
        """
        验证文本输入

        Args:
            text: 输入文本
            max_length: 最大长度
            min_length: 最小长度
            context: 上下文信息

        Returns:
            验证后的文本
        """
        if not isinstance(text, str):
            raise ValueError(f"{context}: 类型错误，期望str")

        text = text.strip()

        if len(text) < min_length:
            raise ValueError(f"{context}: 长度不足（最小{min_length}）")

        if len(text) > max_length:
            raise ValueError(f"{context}: 长度超限（最大{max_length}）")

        return text

    @staticmethod
    def validate_language(lang: str) -> str:
        """
        验证语言代码

        Args:
            lang: 语言代码

        Returns:
            验证后的语言代码
        """
        if lang not in InputValidator.ALLOWED_LANGUAGES:
            raise ValueError(
                f"不支持的语言: {lang}\n"
                f"支持的语言: {', '.join(InputValidator.ALLOWED_LANGUAGES)}"
            )

        return lang

    @staticmethod
    def validate_url_length(url: str, max_length: int = 1000) -> str:
        """验证URL长度"""
        if len(url) > max_length:
            raise ValueError(f"URL过长: {len(url)} > {max_length}")
        return url


# ==================== URL验证器 ====================


class URLValidator:
    """URL验证器 - 防止SSRF攻击"""

    # 允许的域名白名单
    ALLOWED_DOMAINS = [
        "bilibili.com",
        "b23.tv",
        "hdslb.com",  # B站CDN
    ]

    @staticmethod
    def validate_url_domain(
        url: str, allowed_domains: Optional[List[str]] = None
    ) -> bool:
        """
        验证URL域名在白名单中（防止SSRF）

        Args:
            url: 待验证的URL
            allowed_domains: 允许的域名列表

        Returns:
            是否合法
        """
        if allowed_domains is None:
            allowed_domains = URLValidator.ALLOWED_DOMAINS

        # 检查是否包含允许的域名
        for domain in allowed_domains:
            if domain in url:
                return True

        return False

    @staticmethod
    def validate_short_link(short_url: str) -> str:
        """
        验证短链接（防止SSRF）

        Args:
            short_url: 短链接URL

        Returns:
            验证后的URL

        Raises:
            SecurityError: URL不在白名单中
        """
        if "b23.tv" not in short_url:
            raise SecurityError("短链接必须是b23.tv域名")

        return short_url


# ==================== 正则表达式验证器 ====================


class RegexValidator:
    """正则表达式验证器 - 防止ReDoS攻击"""

    @staticmethod
    def validate_input_length_for_regex(input_str: str, max_length: int = 500) -> str:
        """
        验证正则表达式输入长度（防止ReDoS）

        Args:
            input_str: 输入字符串
            max_length: 最大长度

        Returns:
            验证后的字符串
        """
        if len(input_str) > max_length:
            raise ValueError(
                f"输入过长，可能导致ReDoS: {len(input_str)} > {max_length}"
            )

        return input_str

    @staticmethod
    def extract_bv_safe(url: str) -> Optional[str]:
        """
        安全地提取BV号（防止ReDoS）

        Args:
            url: URL字符串

        Returns:
            BV号或None
        """
        # 限制URL长度
        if len(url) > 500:
            return None

        # 使用精确匹配，防止贪婪匹配
        bv_pattern = r"[Bb][Vv][a-zA-Z0-9]{10,13}"
        match = re.search(bv_pattern, url)

        return match.group(0) if match else None


# ==================== LLM输出验证器 ====================


class LLMOutputValidator:
    """LLM输出验证器 - 防止代码注入和XSS"""

    # 默认配置
    DEFAULT_MAX_LENGTH = 50000
    DEFAULT_MAX_LINE_LENGTH = 10000

    # 危险模式检测
    DANGEROUS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>",
        r"eval\s*\(",
        r"exec\s*\(",
        r"__import__\s*\(",
        r"os\.system\s*\(",
        r"subprocess\.",
    ]

    @staticmethod
    def sanitize_llm_output(
        text: str,
        max_length: Optional[int] = None,
        allow_html: bool = False,
        strict_mode: bool = True,
        context: str = "LLM输出",
    ) -> str:
        """
        清理和验证LLM输出文本

        Args:
            text: 待验证的文本
            max_length: 最大长度限制
            allow_html: 是否允许HTML标签
            strict_mode: 严格模式
            context: 上下文信息

        Returns:
            清理后的安全文本
        """
        if text is None:
            raise OutputValidationError(f"{context}: 输出为None")

        if not isinstance(text, str):
            raise OutputValidationError(f"{context}: 输出类型错误")

        # 长度验证
        max_len = max_length or LLMOutputValidator.DEFAULT_MAX_LENGTH
        if len(text) > max_len:
            logger.warning(f"{context}: 输出超长，截断处理")
            text = text[:max_len]

        # 检测危险模式
        if strict_mode:
            for pattern in LLMOutputValidator.DANGEROUS_PATTERNS:
                if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
                    raise OutputValidationError(f"{context}: 检测到潜在恶意代码模式")

        # 移除控制字符
        text = LLMOutputValidator._remove_control_chars(text)

        # HTML转义
        if not allow_html:
            text = html.escape(text)

        logger.info(f"{context}: 验证通过 (长度: {len(text)})")
        return text

    @staticmethod
    def _remove_control_chars(text: str) -> str:
        """移除危险的控制字符"""
        return re.sub(r"[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]", "", text)

    @staticmethod
    def sanitize_translation_output(text: str) -> str:
        """专用于翻译输出的清理"""
        return LLMOutputValidator.sanitize_llm_output(
            text=text,
            max_length=100000,
            allow_html=False,
            strict_mode=True,
            context="翻译输出",
        )

    @staticmethod
    def sanitize_asr_output(text: str) -> str:
        """专用于ASR识别输出的清理"""
        return LLMOutputValidator.sanitize_llm_output(
            text=text,
            max_length=200000,
            allow_html=False,
            strict_mode=True,
            context="ASR输出",
        )


# ==================== 资源管理验证器 ====================


class ResourceValidator:
    """资源管理验证器 - 防止资源泄露"""

    @staticmethod
    def validate_timeout(timeout: float, max_timeout: float = 10.0) -> float:
        """
        验证超时时间

        Args:
            timeout: 超时时间（秒）
            max_timeout: 最大超时时间

        Returns:
            验证后的超时时间
        """
        if timeout > max_timeout:
            logger.warning(f"超时时间过长，调整为: {max_timeout}秒")
            return max_timeout

        if timeout <= 0:
            raise ValueError("超时时间必须大于0")

        return timeout
