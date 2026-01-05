"""
UI组件测试
测试人工校对接口和默认实现
"""

import pytest
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 直接导入模块文件，避免通过__init__.py导入PyQt5依赖
# 只导入不依赖PyQt5的核心模块
import importlib.util

# 加载human_review_interface模块
spec = importlib.util.spec_from_file_location(
    "human_review_interface",
    project_root / "ui" / "src" / "human_review_interface.py"
)
human_review_interface = importlib.util.module_from_spec(spec)
spec.loader.exec_module(human_review_interface)

DefaultHumanReviewCallback = human_review_interface.DefaultHumanReviewCallback
ReviewAction = human_review_interface.ReviewAction
ASRReviewResult = human_review_interface.ASRReviewResult
TranslationReviewResult = human_review_interface.TranslationReviewResult
ASRConsensusInfo = human_review_interface.ASRConsensusInfo
TranslationConsensusInfo = human_review_interface.TranslationConsensusInfo


class TestDefaultHumanReviewCallback:
    """测试默认人工校对回调实现"""

    def test_init(self):
        """测试初始化"""
        callback = DefaultHumanReviewCallback()
        assert callback is not None

    def test_review_asr_result_high_confidence(self, capsys):
        """测试ASR校对 - 高置信度"""
        callback = DefaultHumanReviewCallback()

        primary_text = "这是识别结果"
        consensus_info = ASRConsensusInfo(
            eliminated_node=2,
            selected_nodes=[0, 1],
            coefficient=0.98,
            threshold=0.95,
            warning=None,
        )

        result = callback.review_asr_result(
            primary_text=primary_text,
            consensus_info=consensus_info,
            alternative_texts=["版本1", "版本2"],
        )

        assert result.action == ReviewAction.ACCEPT
        assert result.text == primary_text

        captured = capsys.readouterr()
        assert "相似度" in captured.out
        assert "达标" in captured.out

    def test_review_asr_result_low_confidence(self, capsys):
        """测试ASR校对 - 低置信度"""
        callback = DefaultHumanReviewCallback()

        primary_text = "这是评分最高的结果"
        consensus_info = ASRConsensusInfo(
            eliminated_node=2,
            selected_nodes=[0, 1],
            coefficient=0.85,
            threshold=0.95,
            warning="匹配度较低",
        )

        result = callback.review_asr_result(
            primary_text=primary_text,
            consensus_info=consensus_info,
            alternative_texts=["版本1", "版本2"],
        )

        assert result.action == ReviewAction.ACCEPT
        assert result.text == primary_text

        captured = capsys.readouterr()
        assert "低于阈值" in captured.out
        assert "警告" in captured.out

    def test_review_translation_result(self, capsys):
        """测试翻译校对"""
        callback = DefaultHumanReviewCallback()

        translated_text = "This is the translation"
        consensus_info = TranslationConsensusInfo(
            model_scores={0: 0.95, 1: 0.92},
            overall_score=85.0,
            warning=None,
        )

        result = callback.review_translation_result(
            translated_text=translated_text,
            consensus_info=consensus_info,
        )

        assert result.action == ReviewAction.ACCEPT
        assert result.text == translated_text

        captured = capsys.readouterr()
        assert "综合得分" in captured.out
        assert "85.0" in captured.out

    def test_report_progress(self, capsys):
        """测试进度报告"""
        callback = DefaultHumanReviewCallback()

        callback.report_progress("处理中...", 50.0)

        captured = capsys.readouterr()
        assert "50.0%" in captured.out
        assert "处理中..." in captured.out

        callback.report_progress("完成")

        captured = capsys.readouterr()
        assert "完成" in captured.out


class TestDataClasses:
    """测试数据类"""

    def test_asr_consensus_info(self):
        """测试ASR共识信息数据类"""
        info = ASRConsensusInfo(
            eliminated_node=1,
            selected_nodes=[0, 2],
            coefficient=0.95,
            threshold=0.95,
            warning="测试警告",
        )

        assert info.eliminated_node == 1
        assert info.selected_nodes == [0, 2]
        assert info.coefficient == 0.95
        assert info.threshold == 0.95
        assert info.warning == "测试警告"

    def test_translation_consensus_info(self):
        """测试翻译共识信息数据类"""
        info = TranslationConsensusInfo(
            model_scores={0: 0.9, 1: 0.85},
            overall_score=88.0,
            warning="测试警告",
        )

        assert info.model_scores == {0: 0.9, 1: 0.85}
        assert info.overall_score == 88.0
        assert info.warning == "测试警告"

    def test_asr_review_result(self):
        """测试ASR校对结果数据类"""
        result = ASRReviewResult(
            action=ReviewAction.EDIT_AND_ACCEPT,
            text="编辑后的文本",
            alternative_index=0,
        )

        assert result.action == ReviewAction.EDIT_AND_ACCEPT
        assert result.text == "编辑后的文本"
        assert result.alternative_index == 0

    def test_translation_review_result(self):
        """测试翻译校对结果数据类"""
        result = TranslationReviewResult(
            action=ReviewAction.ACCEPT,
            text="原始翻译",
        )

        assert result.action == ReviewAction.ACCEPT
        assert result.text == "原始翻译"


class TestReviewAction:
    """测试校对操作枚举"""

    def test_action_values(self):
        """测试枚举值"""
        assert ReviewAction.ACCEPT.value == "accept"
        assert ReviewAction.EDIT_AND_ACCEPT.value == "edit_and_accept"
        assert ReviewAction.CHOOSE_ALTERNATIVE.value == "choose_alternative"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
