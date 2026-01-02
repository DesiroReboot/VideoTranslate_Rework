#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置模块单元测试
测试config.py的各项功能
"""

import pytest
import os
from pathlib import Path


class TestConfigModule:
    """配置模块测试"""

    def test_load_config_with_env_vars(self, mock_env_vars):
        """测试使用环境变量加载配置"""
        # 重新导入config模块以应用新的环境变量
        import importlib
        import config
        importlib.reload(config)

        assert config.DASHSCOPE_API_KEY == "test_api_key_12345"
        assert config.OSS_ACCESS_KEY_ID == "test_oss_key_id"
        assert config.OSS_BUCKET_NAME == "test-bucket"

    def test_missing_required_env_var(self, monkeypatch):
        """测试缺失必需环境变量"""
        # 移除必需的环境变量
        monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)

        # 重新导入config应该抛出异常
        import importlib
        import config

        with pytest.raises(ValueError, match="必须设置环境变量"):
            importlib.reload(config)

    def test_output_dirs_exist(self):
        """测试输出目录是否创建"""
        import config

        assert config.OUTPUT_DIR.exists()
        assert config.TEMP_DIR.exists()
        assert config.SCORING_RESULTS_DIR.exists()

    def test_asr_language_hints(self):
        """测试ASR语言提示配置"""
        import config

        assert hasattr(config, "ASR_LANGUAGE_HINTS")
        assert isinstance(config.ASR_LANGUAGE_HINTS, list)
        assert "zh" in config.ASR_LANGUAGE_HINTS
        assert "en" in config.ASR_LANGUAGE_HINTS

    def test_asr_custom_vocabulary(self):
        """测试ASR自定义词典配置"""
        import config

        assert hasattr(config, "ASR_CUSTOM_VOCABULARY")
        assert isinstance(config.ASR_CUSTOM_VOCABULARY, list)
        assert len(config.ASR_CUSTOM_VOCABULARY) > 0

    def test_llm_postprocess_config(self):
        """测试LLM后处理配置"""
        import config

        assert hasattr(config, "ASR_ENABLE_LLM_POSTPROCESS")
        assert hasattr(config, "ASR_LLM_POSTPROCESS_THRESHOLD")
        assert isinstance(config.ASR_LLM_POSTPROCESS_THRESHOLD, (int, float))

    def test_adaptive_threshold_config(self):
        """测试自适应阈值配置"""
        import config

        assert hasattr(config, "ASR_ENABLE_ADAPTIVE_THRESHOLD")
        assert hasattr(config, "ASR_ADAPTIVE_THRESHOLD_METHOD")
        assert config.ASR_ADAPTIVE_THRESHOLD_METHOD in ["moving_avg", "percentile"]


@pytest.mark.unit
class TestConfigConstants:
    """配置常量测试"""

    def test_model_configs(self):
        """测试模型配置常量"""
        import config

        assert config.ASR_MODEL == "fun-asr"
        assert config.MT_MODEL == "qwen-max"
        assert config.TTS_MODEL == "qwen3-tts-flash"

    def test_threshold_configs(self):
        """测试阈值配置"""
        import config

        assert 0 <= config.ASR_SCORE_THRESHOLD <= 100
        assert config.ASR_MAX_RETRIES >= 0
        assert 0 <= config.ASR_LLM_POSTPROCESS_THRESHOLD <= 100
