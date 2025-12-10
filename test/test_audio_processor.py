"""
音频处理模块单元测试
测试AudioProcessor类的各项功能
"""

import unittest
import os
import sys
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 添加父目录到路径以导入模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from audio_processor import AudioProcessor


class TestAudioProcessor(unittest.TestCase):
    """AudioProcessor单元测试类"""
    
    @classmethod
    def setUpClass(cls):
        """测试类初始化 - 创建测试目录"""
        cls.test_dir = Path("test_audio_temp")
        cls.test_dir.mkdir(exist_ok=True)
    
    @classmethod
    def tearDownClass(cls):
        """测试类清理 - 删除测试目录"""
        if cls.test_dir.exists():
            shutil.rmtree(cls.test_dir)
    
    def setUp(self):
        """每个测试前准备"""
        # 创建模拟的视频文件路径
        self.test_video = self.test_dir / "test_video.mp4"
        self.test_audio = self.test_dir / "test_audio.mp3"
        self.test_output = self.test_dir / "test_output.mp4"
    
    def tearDown(self):
        """每个测试后清理"""
        # 清理测试文件
        for file in [self.test_video, self.test_audio, self.test_output]:
            if file.exists():
                file.unlink()
    
    # ==================== 音频提取测试 ====================
    
    @patch('audio_processor.VideoFileClip')
    def test_extract_audio_success(self, mock_video_clip):
        """测试成功提取音频"""
        # 模拟视频对象
        mock_video = MagicMock()
        mock_audio = MagicMock()
        mock_audio.write_audiofile = MagicMock()
        mock_video.audio = mock_audio
        mock_video_clip.return_value = mock_video
        
        # 执行提取
        result = AudioProcessor.extract_audio(str(self.test_video))
        
        # 验证
        self.assertIsNotNone(result, "应返回音频文件路径")
        self.assertTrue(result.endswith('.mp3'), "应返回MP3文件")
        mock_video_clip.assert_called_once_with(str(self.test_video))
        mock_audio.write_audiofile.assert_called_once()
        mock_video.close.assert_called_once()
    
    @patch('audio_processor.VideoFileClip')
    def test_extract_audio_custom_output(self, mock_video_clip):
        """测试自定义输出路径"""
        # 模拟视频对象
        mock_video = MagicMock()
        mock_audio = MagicMock()
        mock_video.audio = mock_audio
        mock_video_clip.return_value = mock_video
        
        custom_output = str(self.test_audio)
        
        # 执行提取
        result = AudioProcessor.extract_audio(str(self.test_video), custom_output)
        
        # 验证
        self.assertEqual(result, custom_output, "应返回指定的输出路径")
    
    @patch('audio_processor.VideoFileClip')
    def test_extract_audio_no_audio_track(self, mock_video_clip):
        """测试视频没有音频轨道"""
        # 模拟没有音频的视频
        mock_video = MagicMock()
        mock_video.audio = None
        mock_video_clip.return_value = mock_video
        
        # 验证抛出异常
        with self.assertRaises(ValueError) as context:
            AudioProcessor.extract_audio(str(self.test_video))
        
        self.assertIn("没有音频", str(context.exception))
        mock_video.close.assert_called_once()
    
    @patch('audio_processor.VideoFileClip')
    def test_extract_audio_exception_handling(self, mock_video_clip):
        """测试异常处理"""
        # 模拟抛出异常
        mock_video_clip.side_effect = Exception("测试异常")
        
        # 验证异常被正确处理
        with self.assertRaises(Exception) as context:
            AudioProcessor.extract_audio(str(self.test_video))
        
        self.assertIn("音频提取失败", str(context.exception))
    
    # ==================== 音频替换测试 ====================
    
    @patch('audio_processor.VideoFileClip')
    @patch('audio_processor.AudioFileClip')
    def test_replace_audio_success(self, mock_audio_clip, mock_video_clip):
        """测试成功替换音频"""
        # 模拟视频和音频对象
        mock_video = MagicMock()
        mock_video.duration = 100.0
        mock_audio = MagicMock()
        mock_audio.duration = 100.0
        mock_final = MagicMock()
        
        mock_video_clip.return_value = mock_video
        mock_audio_clip.return_value = mock_audio
        mock_video.set_audio.return_value = mock_final
        
        # 执行替换
        result = AudioProcessor.replace_audio(
            str(self.test_video),
            str(self.test_audio)
        )
        
        # 验证
        self.assertIsNotNone(result, "应返回输出视频路径")
        mock_video_clip.assert_called_once_with(str(self.test_video))
        mock_audio_clip.assert_called_once_with(str(self.test_audio))
        mock_video.set_audio.assert_called_once_with(mock_audio)
        mock_final.write_videofile.assert_called_once()
    
    @patch('audio_processor.VideoFileClip')
    @patch('audio_processor.AudioFileClip')
    def test_replace_audio_duration_mismatch_longer(self, mock_audio_clip, mock_video_clip):
        """测试音频比视频长"""
        # 模拟音频比视频长
        mock_video = MagicMock()
        mock_video.duration = 100.0
        mock_audio = MagicMock()
        mock_audio.duration = 150.0
        mock_audio_short = MagicMock()
        mock_audio.subclip.return_value = mock_audio_short
        mock_final = MagicMock()
        
        mock_video_clip.return_value = mock_video
        mock_audio_clip.return_value = mock_audio
        mock_video.set_audio.return_value = mock_final
        
        # 执行替换
        AudioProcessor.replace_audio(str(self.test_video), str(self.test_audio))
        
        # 验证音频被裁剪
        mock_audio.subclip.assert_called_once_with(0, 100.0)
        mock_video.set_audio.assert_called_once_with(mock_audio_short)
    
    @patch('audio_processor.VideoFileClip')
    @patch('audio_processor.AudioFileClip')
    def test_replace_audio_duration_mismatch_shorter(self, mock_audio_clip, mock_video_clip):
        """测试音频比视频短"""
        # 模拟音频比视频短
        mock_video = MagicMock()
        mock_video.duration = 100.0
        mock_audio = MagicMock()
        mock_audio.duration = 50.0
        mock_final = MagicMock()
        
        mock_video_clip.return_value = mock_video
        mock_audio_clip.return_value = mock_audio
        mock_video.set_audio.return_value = mock_final
        
        # 执行替换 (应该有警告但不报错)
        result = AudioProcessor.replace_audio(str(self.test_video), str(self.test_audio))
        
        # 验证仍然继续处理
        self.assertIsNotNone(result)
        mock_video.set_audio.assert_called_once()
    
    @patch('audio_processor.VideoFileClip')
    @patch('audio_processor.AudioFileClip')
    def test_replace_audio_custom_output(self, mock_audio_clip, mock_video_clip):
        """测试自定义输出路径"""
        mock_video = MagicMock()
        mock_video.duration = 100.0
        mock_audio = MagicMock()
        mock_audio.duration = 100.0
        mock_final = MagicMock()
        
        mock_video_clip.return_value = mock_video
        mock_audio_clip.return_value = mock_audio
        mock_video.set_audio.return_value = mock_final
        
        custom_output = str(self.test_output)
        
        # 执行替换
        result = AudioProcessor.replace_audio(
            str(self.test_video),
            str(self.test_audio),
            custom_output
        )
        
        # 验证使用了自定义路径
        self.assertEqual(result, custom_output)
    
    @patch('audio_processor.VideoFileClip')
    @patch('audio_processor.AudioFileClip')
    def test_replace_audio_exception_handling(self, mock_audio_clip, mock_video_clip):
        """测试异常处理"""
        # 模拟异常
        mock_video_clip.side_effect = Exception("测试异常")
        
        # 验证异常被正确处理
        with self.assertRaises(Exception) as context:
            AudioProcessor.replace_audio(str(self.test_video), str(self.test_audio))
        
        self.assertIn("音频替换失败", str(context.exception))
    
    # ==================== 音频时长获取测试 ====================
    
    @patch('audio_processor.AudioFileClip')
    def test_get_audio_duration_success(self, mock_audio_clip):
        """测试成功获取音频时长"""
        # 模拟音频对象
        mock_audio = MagicMock()
        mock_audio.duration = 123.45
        mock_audio_clip.return_value = mock_audio
        
        # 执行获取时长
        duration = AudioProcessor.get_audio_duration(str(self.test_audio))
        
        # 验证
        self.assertEqual(duration, 123.45, "应返回正确的时长")
        mock_audio_clip.assert_called_once_with(str(self.test_audio))
        mock_audio.close.assert_called_once()
    
    @patch('audio_processor.AudioFileClip')
    def test_get_audio_duration_zero(self, mock_audio_clip):
        """测试时长为0的音频"""
        mock_audio = MagicMock()
        mock_audio.duration = 0.0
        mock_audio_clip.return_value = mock_audio
        
        duration = AudioProcessor.get_audio_duration(str(self.test_audio))
        
        self.assertEqual(duration, 0.0)
    
    @patch('audio_processor.AudioFileClip')
    def test_get_audio_duration_exception(self, mock_audio_clip):
        """测试获取时长异常"""
        mock_audio_clip.side_effect = Exception("测试异常")
        
        with self.assertRaises(Exception) as context:
            AudioProcessor.get_audio_duration(str(self.test_audio))
        
        self.assertIn("获取音频时长失败", str(context.exception))
    
    # ==================== 边界情况测试 ====================
    
    @patch('audio_processor.VideoFileClip')
    def test_extract_audio_empty_path(self, mock_video_clip):
        """测试空路径"""
        with self.assertRaises(Exception):
            AudioProcessor.extract_audio("")
    
    @patch('audio_processor.VideoFileClip')
    @patch('audio_processor.AudioFileClip')
    def test_replace_audio_empty_paths(self, mock_audio_clip, mock_video_clip):
        """测试空路径"""
        with self.assertRaises(Exception):
            AudioProcessor.replace_audio("", "")


class TestAudioProcessorIntegration(unittest.TestCase):
    """AudioProcessor集成测试类"""
    
    @unittest.skipUnless(
        os.getenv("RUN_INTEGRATION_TESTS"),
        "跳过集成测试,设置RUN_INTEGRATION_TESTS=1启用"
    )
    def test_extract_and_replace_real_video(self):
        """
        集成测试: 提取和替换真实视频音频
        注意: 需要真实的测试视频文件,默认跳过
        """
        # 这里需要真实的测试视频
        test_video = "real_test_video.mp4"
        
        if not Path(test_video).exists():
            self.skipTest("未找到测试视频文件")
        
        try:
            # 提取音频
            audio_path = AudioProcessor.extract_audio(test_video)
            self.assertTrue(Path(audio_path).exists(), "音频文件应存在")
            
            # 获取时长
            duration = AudioProcessor.get_audio_duration(audio_path)
            self.assertGreater(duration, 0, "时长应大于0")
            
            # 替换音频
            output_video = AudioProcessor.replace_audio(
                test_video,
                audio_path,
                "test_output.mp4"
            )
            self.assertTrue(Path(output_video).exists(), "输出视频应存在")
            
        except Exception as e:
            self.fail(f"集成测试失败: {str(e)}")


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试
    suite.addTests(loader.loadTestsFromTestCase(TestAudioProcessor))
    suite.addTests(loader.loadTestsFromTestCase(TestAudioProcessorIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 返回结果
    return result.wasSuccessful()


if __name__ == '__main__':
    print("=" * 70)
    print("AudioProcessor 单元测试")
    print("=" * 70)
    print()
    
    # 运行测试
    success = run_tests()
    
    print()
    print("=" * 70)
    if success:
        print("✓ 所有测试通过!")
    else:
        print("✗ 部分测试失败,请检查上述错误")
    print("=" * 70)
    
    # 退出码
    exit(0 if success else 1)
