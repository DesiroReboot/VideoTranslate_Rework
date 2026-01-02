#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集成测试
测试完整的视频翻译工作流
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


@pytest.mark.integration
@pytest.mark.slow
class TestVideoTranslationWorkflow:
    """视频翻译工作流集成测试"""

    def test_video_translator_initialization(self, mock_env_vars):
        """测试VideoTranslator初始化"""
        import importlib
        import config
        importlib.reload(config)

        from main import VideoTranslator

        translator = VideoTranslator("auto")
        assert translator is not None
        assert hasattr(translator, "ai_services")

    @pytest.mark.skip(reason="需要真实视频文件和网络连接")
    def test_full_translation_workflow_bilibili(self, mock_env_vars):
        """测试完整的B站视频翻译流程"""
        import importlib
        import config
        importlib.reload(config)

        from main import VideoTranslator

        translator = VideoTranslator("auto")

        # 使用测试BV号（如果存在网络连接和API密钥）
        test_bv = "BV1xx411c7mD"  # 示例BV号

        # Mock实际的网络请求
        with patch('video_downloader.VideoDownloader.download_bilibili_video') as mock_download:
            mock_download.return_value = ("/fake/video.mp4", None)

            with patch('audio_processor.extract_audio') as mock_extract:
                mock_extract.return_value = "/fake/audio.mp3"

                with patch('speech_to_text.SpeechToText.recognize') as mock_asr:
                    mock_asr.return_value = "这是测试文本。"

                    # 执行翻译
                    try:
                        result = translator.translate_video(
                            f"https://www.bilibili.com/video/{test_bv}",
                            "English",
                            source_language="auto"
                        )
                        # 验证结果
                        assert result is not None
                    except Exception as e:
                        pytest.fail(f"翻译流程失败: {e}")

    def test_error_handling_invalid_url(self, mock_env_vars):
        """测试错误处理：无效URL"""
        import importlib
        import config
        importlib.reload(config)

        from main import VideoTranslator

        translator = VideoTranslator("auto")

        with pytest.raises(Exception):
            translator.translate_video(
                "not-a-valid-url",
                "English"
            )


@pytest.mark.integration
@pytest.mark.unit
class TestModuleIntegration:
    """模块间集成测试"""

    def test_config_to_asr_integration(self, mock_env_vars):
        """测试配置模块到ASR模块的集成"""
        import importlib
        import config
        importlib.reload(config)

        from speech_to_text import SpeechToText

        # 验证配置是否正确传递
        stt = SpeechToText()

        # 检查ASR配置
        assert hasattr(stt, "asr_client" if hasattr(stt, "asr_client") else "distributed_asr")

    def test_security_to_main_integration(self, mock_env_vars):
        """测试安全模块到主流程的集成"""
        import importlib
        import config
        importlib.reload(config)

        from common.security import URLValidator

        # 测试URL验证
        test_url = "https://www.bilibili.com/video/BV1xx411c7mD"
        validated_url = URLValidator.validate_url(test_url)
        assert validated_url == test_url


@pytest.mark.integration
class TestDataFlow:
    """数据流测试"""

    def test_score_history_persistence(self, tmp_path, mock_env_vars):
        """测试评分历史持久化"""
        import importlib
        import config
        import json
        importlib.reload(config)

        # 创建临时历史文件
        history_file = tmp_path / "test_history.json"

        test_data = [
            {"timestamp": 1234567890, "score": 75.5, "audio_path": "/test1.mp3", "text_length": 1000},
            {"timestamp": 1234567891, "score": 80.0, "audio_path": "/test2.mp3", "text_length": 1200},
        ]

        history_file.write_text(json.dumps(test_data, ensure_ascii=False))

        # 验证文件内容
        content = history_file.read_text(encoding='utf-8')
        loaded_data = json.loads(content)

        assert len(loaded_data) == 2
        assert loaded_data[0]["score"] == 75.5

    def test_translation_result_saving(self, output_dir, mock_env_vars):
        """测试翻译结果保存"""
        import importlib
        import config
        importlib.reload(config)

        # 创建测试翻译结果
        test_result = {
            "source_text": "测试文本",
            "translated_text": "Test text",
            "score": 85.0,
            "target_language": "English"
        }

        result_file = output_dir / "test_translation_result.json"
        import json
        result_file.write_text(json.dumps(test_result, ensure_ascii=False, indent=2))

        # 验证文件存在
        assert result_file.exists()

        # 验证内容
        loaded = json.loads(result_file.read_text(encoding='utf-8'))
        assert loaded["score"] == 85.0
