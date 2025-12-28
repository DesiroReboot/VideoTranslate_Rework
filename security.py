"""
安全验证模块
用于验证和清理AI服务输出，防止注入攻击和XSS
遵循 OWASP LLM02: Insecure Output Handling 安全规范
"""

import re
import html
import logging
from typing import Optional, Dict, Any

# 配置日志
logger = logging.getLogger(__name__)


class OutputValidationError(Exception):
    """LLM输出验证异常"""
    pass


class SecurityValidator:
    """安全验证器 - 用于验证和清理LLM输出"""
    
    # 默认配置
    DEFAULT_MAX_LENGTH = 50000  # 最大文本长度（约50KB）
    DEFAULT_MAX_LINE_LENGTH = 10000  # 单行最大长度
    
    # 危险模式检测
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # Script标签
        r'javascript:',  # JavaScript协议
        r'on\w+\s*=',  # 事件处理器 (onclick, onerror等)
        r'<iframe[^>]*>',  # iframe标签
        r'eval\s*\(',  # eval函数
        r'exec\s*\(',  # exec函数
        r'__import__\s*\(',  # Python导入
        r'os\.system\s*\(',  # 系统命令
        r'subprocess\.',  # subprocess模块
    ]
    
    @staticmethod
    def sanitize_llm_output(
        text: str,
        max_length: Optional[int] = None,
        allow_html: bool = False,
        strict_mode: bool = True,
        context: str = "LLM输出"
    ) -> str:
        """
        清理和验证LLM输出文本
        
        Args:
            text: 待验证的文本
            max_length: 最大长度限制（None使用默认值）
            allow_html: 是否允许HTML标签（False时会转义）
            strict_mode: 严格模式（检测危险模式）
            context: 上下文信息（用于日志）
            
        Returns:
            清理后的安全文本
            
        Raises:
            OutputValidationError: 验证失败
        """
        if text is None:
            raise OutputValidationError(f"{context}: 输出为None")
        
        if not isinstance(text, str):
            raise OutputValidationError(f"{context}: 输出类型错误，期望str，实际{type(text)}")
        
        # 1. 长度验证
        max_len = max_length or SecurityValidator.DEFAULT_MAX_LENGTH
        if len(text) > max_len:
            logger.warning(f"{context}: 输出超长 ({len(text)} > {max_len})，截断处理")
            text = text[:max_len]
        
        if len(text) == 0:
            logger.warning(f"{context}: 输出为空字符串")
            return ""
        
        # 2. 检测危险模式（严格模式）
        if strict_mode:
            for pattern in SecurityValidator.DANGEROUS_PATTERNS:
                matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
                if matches:
                    logger.error(f"{context}: 检测到危险模式 '{pattern}': {matches[:3]}")
                    raise OutputValidationError(
                        f"{context}: 检测到潜在恶意代码模式"
                    )
        
        # 3. 移除控制字符（保留常用的换行、制表符）
        text = SecurityValidator._remove_control_chars(text)
        
        # 4. HTML转义（如果不允许HTML）
        if not allow_html:
            text = html.escape(text)
        
        # 5. 单行长度检查（防止畸形输出）
        lines = text.split('\n')
        if any(len(line) > SecurityValidator.DEFAULT_MAX_LINE_LENGTH for line in lines):
            logger.warning(f"{context}: 检测到超长行（>{SecurityValidator.DEFAULT_MAX_LINE_LENGTH}字符）")
        
        logger.info(f"{context}: 验证通过 (长度: {len(text)})")
        return text
    
    @staticmethod
    def sanitize_translation_output(text: str) -> str:
        """
        专用于翻译输出的清理
        - 不允许HTML
        - 严格模式检测
        - 限制长度
        """
        return SecurityValidator.sanitize_llm_output(
            text=text,
            max_length=100000,  # 翻译可能较长
            allow_html=False,
            strict_mode=True,
            context="翻译输出"
        )
    
    @staticmethod
    def sanitize_asr_output(text: str) -> str:
        """
        专用于ASR识别输出的清理
        - 不允许HTML
        - 严格模式检测
        - 限制长度
        """
        return SecurityValidator.sanitize_llm_output(
            text=text,
            max_length=200000,  # ASR可能较长
            allow_html=False,
            strict_mode=True,
            context="ASR输出"
        )
    
    @staticmethod
    def _remove_control_chars(text: str) -> str:
        """
        移除危险的控制字符，保留常用的空白字符
        
        保留：
        - \n (换行)
        - \r (回车)
        - \t (制表符)
        - 空格
        
        移除：
        - NULL (\x00)
        - 其他控制字符 (\x01-\x08, \x0B-\x0C, \x0E-\x1F)
        """
        # 保留常用空白字符，移除其他控制字符
        cleaned = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)
        return cleaned
    
    @staticmethod
    def validate_file_path(file_path: str, allowed_extensions: Optional[list] = None) -> bool:
        """
        验证文件路径安全性
        
        Args:
            file_path: 文件路径
            allowed_extensions: 允许的扩展名列表（如 ['.txt', '.wav']）
            
        Returns:
            是否安全
        """
        # 检测路径遍历攻击
        if '..' in file_path or file_path.startswith('/') or ':' in file_path[1:]:
            logger.error(f"检测到路径遍历攻击: {file_path}")
            return False
        
        # 检查扩展名
        if allowed_extensions:
            import os
            _, ext = os.path.splitext(file_path)
            if ext.lower() not in allowed_extensions:
                logger.warning(f"文件扩展名不允许: {ext}")
                return False
        
        return True
    
    @staticmethod
    def log_suspicious_output(text: str, reason: str, context: str = ""):
        """
        记录可疑输出到日志
        
        Args:
            text: 可疑文本
            reason: 可疑原因
            context: 上下文信息
        """
        preview = text[:200] + "..." if len(text) > 200 else text
        logger.warning(
            f"可疑输出 [{context}]: {reason}\n"
            f"预览: {preview}"
        )


class InputValidator:
    """输入验证器 - 用于验证用户输入"""
    
    @staticmethod
    def validate_text_input(
        text: str,
        max_length: int = 10000,
        min_length: int = 1,
        context: str = "输入"
    ) -> str:
        """
        验证用户文本输入
        
        Args:
            text: 输入文本
            max_length: 最大长度
            min_length: 最小长度
            context: 上下文
            
        Returns:
            验证后的文本
            
        Raises:
            ValueError: 验证失败
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
    def validate_language_code(lang: str) -> str:
        """
        验证语言代码
        
        Args:
            lang: 语言代码
            
        Returns:
            验证后的语言代码
        """
        # 允许的语言代码模式
        if not re.match(r'^[a-z]{2,3}(-[A-Z]{2})?$', lang):
            raise ValueError(f"语言代码格式错误: {lang}")
        
        return lang
