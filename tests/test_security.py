#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全模块单元测试
测试common/security/模块的各项功能
"""

import pytest
from pathlib import Path

from common.security import (
    PathTraversalError,
    PathSecurityValidator,
    SSRFProtectionError,
    URLValidator,
    InputValidationError,
    InputValidator,
    RegexValidator,
    LLMOutputValidator,
)


class TestPathSecurityValidator:
    """路径安全验证器测试"""

    def test_validate_path_in_project_valid_path(self, tmp_path):
        """测试有效路径"""
        project_root = tmp_path
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        # 应该不抛出异常
        result = PathSecurityValidator.validate_path_in_project(
            str(test_file), str(project_root)
        )
        assert result == str(test_file)

    def test_validate_path_in_project_path_traversal_attack(self, tmp_path):
        """测试路径遍历攻击防护"""
        project_root = tmp_path

        with pytest.raises(PathTraversalError):
            PathSecurityValidator.validate_path_in_project(
                "../../../etc/passwd", str(project_root)
            )

    def test_validate_path_in_project_absolute_path_outside(self, tmp_path):
        """测试项目外绝对路径"""
        project_root = tmp_path
        outside_path = "/etc/passwd" if Path("/etc/passwd").exists() else "C:/Windows/system32"

        with pytest.raises(PathTraversalError):
            PathSecurityValidator.validate_path_in_project(outside_path, str(project_root))

    def test_is_safe_path_positive(self):
        """测试安全路径判断（正向）"""
        assert PathSecurityValidator.is_safe_path("video.mp4")
        assert PathSecurityValidator.is_safe_path("subdir/video.mp4")
        assert PathSecurityValidator.is_safe_path("../output/video.mp4")

    def test_is_safe_path_negative(self):
        """测试安全路径判断（负向）"""
        assert not PathSecurityValidator.is_safe_path("../../../etc/passwd")
        assert not PathSecurityValidator.is_safe_path("/etc/passwd")
        assert not PathSecurityValidator.is_safe_path("~/.ssh/id_rsa")

    def test_sanitize_filename(self):
        """测试文件名清理"""
        assert PathSecurityValidator.sanitize_filename("test/file.mp4") == "test_file.mp4"
        assert PathSecurityValidator.sanitize_filename("test:file.mp4") == "test_file.mp4"
        assert PathSecurityValidator.sanitize_filename("test??file.mp4") == "test__file.mp4"


class TestURLValidator:
    """URL验证器测试"""

    def test_validate_url_valid(self):
        """测试有效URL"""
        valid_urls = [
            "https://www.bilibili.com/video/BV1xx",
            "http://example.com/video.mp4",
            "https://youtube.com/watch?v=test",
        ]
        for url in valid_urls:
            result = URLValidator.validate_url(url)
            assert result == url

    def test_validate_url_invalid(self):
        """测试无效URL"""
        invalid_urls = [
            "not a url",
            "javascript:alert('xss')",
            "file:///etc/passwd",
            "//example.com",  # 协议相对URL
        ]
        for url in invalid_urls:
            with pytest.raises(SSRFProtectionError):
                URLValidator.validate_url(url)

    def test_validate_url_allowed_domains(self):
        """测试域名白名单"""
        url = "https://www.bilibili.com/video/BV1xx"
        allowed_domains = ["bilibili.com", "www.bilibili.com"]

        result = URLValidator.validate_url(url, allowed_domains=allowed_domains)
        assert result == url

    def test_validate_url_blocked_domain(self):
        """测试域名黑名单"""
        url = "https://evil.com/video.mp4"
        blocked_domains = ["evil.com", "malicious.com"]

        with pytest.raises(SSRFProtectionError):
            URLValidator.validate_url(url, blocked_domains=blocked_domains)

    def test_is_youtube_url(self):
        """测试YouTube URL识别"""
        assert URLValidator.is_youtube_url("https://youtube.com/watch?v=test")
        assert URLValidator.is_youtube_url("https://youtu.be/test")
        assert not URLValidator.is_youtube_url("https://bilibili.com/video/test")

    def test_is_bilibili_url(self):
        """测试B站URL识别"""
        assert URLValidator.is_bilibili_url("https://www.bilibili.com/video/BV1xx")
        assert URLValidator.is_bilibili_url("https://bilibili.com/video/BV1xx")
        assert not URLValidator.is_bilibili_url("https://youtube.com/watch?v=test")

    def test_extract_bv_number(self):
        """测试BV号提取"""
        url = "https://www.bilibili.com/video/BV1xx411c7mD"
        bv = URLValidator.extract_bv_number(url)
        assert bv == "BV1xx411c7mD"


class TestInputValidator:
    """输入验证器测试"""

    def test_validate_language_valid(self):
        """测试有效语言代码"""
        valid_languages = ["English", "Chinese", "Japanese", "Korean", "French", "German"]
        for lang in valid_languages:
            result = InputValidator.validate_language(lang)
            assert result == lang

    def test_validate_language_invalid(self):
        """测试无效语言代码"""
        with pytest.raises(InputValidationError):
            InputValidator.validate_language("InvalidLanguage")

    def test_validate_text_length_valid(self):
        """测试有效文本长度"""
        text = "a" * 1000
        result = InputValidator.validate_text_length(text, max_length=10000)
        assert result == text

    def test_validate_text_length_too_long(self):
        """测试文本过长"""
        text = "a" * 20000
        with pytest.raises(InputValidationError):
            InputValidator.validate_text_length(text, max_length=10000)

    def test_validate_text_length_too_short(self):
        """测试文本过短"""
        text = "a"
        with pytest.raises(InputValidationError):
            InputValidator.validate_text_length(text, min_length=10)

    def test sanitize_user_input(self):
        """测试用户输入清理"""
        dirty_input = "  <script>alert('xss')</script>  "
        clean = InputValidator.sanitize_user_input(dirty_input)
        assert "<script>" not in clean
        assert clean.strip() == clean


class TestRegexValidator:
    """正则表达式验证器测试"""

    def test_validate_regex_safe_patterns(self):
        """测试安全的正则表达式"""
        safe_patterns = [
            r"\d+",
            r"[a-zA-Z]+",
            r"test\s+pattern",
        ]
        for pattern in safe_patterns:
            result = RegexValidator.validate_regex(pattern)
            assert result == pattern

    def test_validate_regex_redos_attack(self):
        """测试ReDoS攻击防护"""
        malicious_patterns = [
            r"(a+)+",  # 可能导致ReDoS
            r"((a+)*)+",  # 嵌套量词
        ]
        for pattern in malicious_patterns:
            with pytest.raises(InputValidationError):
                RegexValidator.validate_regex(pattern, max_complexity=10)


class TestLLMOutputValidator:
    """LLM输出验证器测试"""

    def test_sanitize_llm_output_code_injection(self):
        """测试代码注入防护"""
        malicious_output = "正常文本 ```python\nimport os\nos.system('rm -rf /')\n```"
        clean = LLMOutputValidator.sanitize_llm_output(malicious_output)
        # 应该移除或转义代码块
        assert "import os" not in clean or "```" not in clean

    def test_sanitize_llm_output_xss(self):
        """测试XSS防护"""
        malicious_output = "点击<script>alert('xss')</script>这里"
        clean = LLMOutputValidator.sanitize_llm_output(malicious_output)
        assert "<script>" not in clean

    def test_sanitize_asr_output(self):
        """测试ASR输出清理"""
        asr_output = "识别结果 <special>特殊字符</special>"
        clean = LLMOutputValidator.sanitize_asr_output(asr_output)
        assert "<special>" not in clean or "&lt;" in clean

    def test_validate_translation_output_safe(self):
        """测试安全翻译输出"""
        safe_output = "这是一个安全的翻译结果。"
        result = LLMOutputValidator.validate_translation_output(safe_output)
        assert result == safe_output

    def test_validate_translation_output_malicious(self):
        """测试恶意翻译输出"""
        malicious_outputs = [
            "翻译<script>alert('xss')</script>结果",
            "翻译```python\nimport os\nos.system('rm -rf /')\n```结果",
        ]
        for output in malicious_outputs:
            with pytest.raises(Exception):  # SecurityError或类似
                LLMOutputValidator.validate_translation_output(output)


@pytest.mark.integration
class TestSecurityIntegration:
    """安全模块集成测试"""

    def test_full_validation_workflow(self, tmp_path, mock_env_vars):
        """测试完整验证流程"""
        # 创建测试文件
        test_file = tmp_path / "test_video.mp4"
        test_file.write_bytes(b"fake video content")

        # 验证路径
        safe_path = PathSecurityValidator.validate_path_in_project(
            str(test_file), str(tmp_path)
        )

        # 验证文件类型
        ext = Path(safe_path).suffix.lower()
        assert ext in [".mp4", ".mkv", ".avi"]

        print(f"✓ 完整验证流程通过: {safe_path}")
