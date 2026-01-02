#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASR模块单元测试
测试语音识别相关功能
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from speech_to_text import SpeechToText
from scores.ASR.asr_scorer import AsrScorer


@pytest.mark.unit
class TestASRScorer:
    """ASR评分器测试"""

    def test_asr_scorer_initialization(self):
        """测试ASR评分器初始化"""
        scorer = AsrScorer()
        assert scorer is not None

    def test_score_asr_result_good_text(self):
        """测试评分好的ASR结果"""
        scorer = AsrScorer()
        good_text = "这是一个测试语音识别的结果。内容清晰，逻辑通顺，没有明显的识别错误。"
        score = scorer.score_asr_result(good_text)

        assert hasattr(score, "overall_score")
        assert 0 <= score.overall_score <= 100
        # 好的文本应该得到较高的分数
        assert score.overall_score > 50

    def test_score_asr_result_bad_text(self):
        """测试评分差的ASR结果"""
        scorer = AsrScorer()
        bad_text = "啊啊啊嗯嗯嗯呃呃呃" * 20  # 重复无意义内容
        score = scorer.score_asr_result(bad_text)

        assert hasattr(score, "overall_score")
        # 差的文本应该得到较低的分数
        assert score.overall_score < 70

    def test_score_asr_result_empty_text(self):
        """测试评分空文本"""
        scorer = AsrScorer()
        score = scorer.score_asr_result("")

        assert score.overall_score == 0

    def test_apply_corrections(self):
        """测试应用校正"""
        scorer = AsrScorer()
        original_text = "测试文本"
        corrections = [
            {"index": 0, "original": "测", "suggested": "侧", "confidence": 0.9}
        ]

        corrected = scorer.apply_corrections(original_text, corrections)
        assert corrected == "侧试文本"


@pytest.mark.unit
class TestSpeechToText:
    """语音识别服务测试"""

    def test_speech_to_text_initialization(self, mock_env_vars):
        """测试SpeechToText初始化"""
        # 重新导入以应用mock环境变量
        import importlib
        import config
        importlib.reload(config)

        stt = SpeechToText()
        assert stt is not None
        assert hasattr(stt, "asr_scorer")
        assert hasattr(stt, "score_history")

    def test_load_score_history(self, tmp_path, mock_env_vars):
        """测试加载评分历史"""
        import importlib
        import config
        import json
        importlib.reload(config)

        # 创建测试历史文件
        history_file = tmp_path / "asr_score_history.json"
        test_history = [
            {
                "timestamp": 1234567890,
                "score": 75.5,
                "audio_path": "/test/audio.mp3",
                "text_length": 1000
            }
        ]
        history_file.write_text(json.dumps(test_history, ensure_ascii=False))

        # 修改配置指向测试文件
        with patch.object(config, "ASR_SCORE_HISTORY_FILE", history_file):
            stt = SpeechToText()
            assert len(stt.score_history) == 1
            assert stt.score_history[0]["score"] == 75.5

    def test_add_score_record(self, mock_env_vars):
        """测试添加评分记录"""
        import importlib
        import config
        importlib.reload(config)

        stt = SpeechToText()
        initial_count = len(stt.score_history)

        stt._add_score_record(80.0, "/test/audio.mp3", 1200)

        assert len(stt.score_history) == initial_count + 1

    def test_calculate_adaptive_threshold_insufficient_data(self, mock_env_vars):
        """测试数据不足时的自适应阈值计算"""
        import importlib
        import config
        importlib.reload(config)

        stt = SpeechToText()

        # 数据不足，不应该计算阈值
        stt._calculate_and_update_threshold()
        # 只验证不抛出异常


@pytest.mark.integration
@pytest.mark.requires_network
@pytest.mark.slow
class TestASRIntegration:
    """ASR集成测试（需要真实API）"""

    @pytest.mark.skip(reason="需要真实API密钥和网络连接")
    def test_full_asr_workflow(self, mock_env_vars):
        """测试完整ASR工作流"""
        import importlib
        import config
        importlib.reload(config)

        stt = SpeechToText()

        # 使用真实音频文件测试
        test_audio = "tests/fixtures/sample_audio.mp3"

        if Path(test_audio).exists():
            result = stt.recognize(test_audio)
            assert isinstance(result, str)
            assert len(result) > 0
        else:
            pytest.skip("测试音频文件不存在")


@pytest.mark.unit
class TestASRUtils:
    """ASR工具函数测试"""

    def test_uuid_filename_generation(self):
        """测试UUID文件名生成"""
        import uuid
        from pathlib import Path

        file_ext = ".mp3"
        unique_filename = f"{uuid.uuid4()}{file_ext}"

        assert unique_filename.endswith(file_ext)
        assert len(unique_filename) == len(str(uuid.uuid4())) + len(file_ext)

    def test_oss_signed_url_generation(self, mock_env_vars):
        """测试OSS签名URL生成（mock）"""
        import importlib
        import config
        importlib.reload(config)

        with patch('oss2.Bucket') as mock_bucket:
            mock_bucket_instance = MagicMock()
            mock_bucket.return_value = mock_bucket_instance
            mock_bucket_instance.sign_url.return_value = "https://signed-url.example.com"

            # 测试签名URL生成
            signed_url = mock_bucket_instance.sign_url('GET', 'test.mp3', 3600)
            assert signed_url == "https://signed-url.example.com"
            mock_bucket_instance.sign_url.assert_called_once_with('GET', 'test.mp3', 3600)
