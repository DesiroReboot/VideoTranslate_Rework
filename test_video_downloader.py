"""
视频下载模块单元测试
测试VideoDownloader类的各项功能
"""

import unittest
import os
from pathlib import Path
from video_downloader import VideoDownloader


class TestVideoDownloader(unittest.TestCase):
    """VideoDownloader单元测试类"""
    
    def setUp(self):
        """测试前准备"""
        # 创建测试用临时文件
        self.test_video_path = Path("test_sample.mp4")
        if not self.test_video_path.exists():
            # 创建一个空的测试文件
            self.test_video_path.touch()
    
    def tearDown(self):
        """测试后清理"""
        # 清理测试文件
        if self.test_video_path.exists():
            self.test_video_path.unlink()
    
    # ==================== URL验证测试 ====================
    
    def test_is_bilibili_url_valid_bv(self):
        """测试识别有效的BV号URL"""
        valid_urls = [
            "https://www.bilibili.com/video/BV1xx411c7mD",
            "https://bilibili.com/video/BV1234567890",
            "http://www.bilibili.com/video/BVabcdefghij",
        ]
        for url in valid_urls:
            with self.subTest(url=url):
                self.assertTrue(
                    VideoDownloader.is_bilibili_url(url),
                    f"应识别为有效B站URL: {url}"
                )
    
    def test_is_bilibili_url_valid_av(self):
        """测试识别有效的AV号URL"""
        valid_urls = [
            "https://www.bilibili.com/video/av12345678",
            "https://bilibili.com/video/av987654321",
        ]
        for url in valid_urls:
            with self.subTest(url=url):
                self.assertTrue(
                    VideoDownloader.is_bilibili_url(url),
                    f"应识别为有效B站URL: {url}"
                )
    
    def test_is_bilibili_url_valid_short(self):
        """测试识别有效的B站短链接"""
        valid_urls = [
            "https://b23.tv/abc123",
            "http://b23.tv/xyz789",
        ]
        for url in valid_urls:
            with self.subTest(url=url):
                self.assertTrue(
                    VideoDownloader.is_bilibili_url(url),
                    f"应识别为有效B站短链: {url}"
                )
    
    def test_is_bilibili_url_invalid(self):
        """测试识别无效的URL"""
        invalid_urls = [
            "https://www.youtube.com/watch?v=xxx",
            "https://www.douyin.com/video/xxx",
            "not_a_url",
            "",
            "bilibili.com/video/BV123",  # 缺少协议
        ]
        for url in invalid_urls:
            with self.subTest(url=url):
                self.assertFalse(
                    VideoDownloader.is_bilibili_url(url),
                    f"不应识别为B站URL: {url}"
                )
    
    # ==================== 本地文件验证测试 ====================
    
    def test_is_local_file_valid_mp4(self):
        """测试识别有效的本地MP4文件"""
        # 使用setUp中创建的测试文件
        self.assertTrue(
            VideoDownloader.is_local_file(str(self.test_video_path)),
            "应识别为有效的本地文件"
        )
    
    def test_is_local_file_supported_formats(self):
        """测试支持的各种视频格式"""
        formats = ['.mp4', '.avi', '.mov', '.mkv']
        for fmt in formats:
            test_file = Path(f"test_video{fmt}")
            try:
                test_file.touch()
                with self.subTest(format=fmt):
                    self.assertTrue(
                        VideoDownloader.is_local_file(str(test_file)),
                        f"应支持{fmt}格式"
                    )
            finally:
                if test_file.exists():
                    test_file.unlink()
    
    def test_is_local_file_nonexistent(self):
        """测试不存在的文件"""
        self.assertFalse(
            VideoDownloader.is_local_file("nonexistent_file.mp4"),
            "不存在的文件应返回False"
        )
    
    def test_is_local_file_unsupported_format(self):
        """测试不支持的文件格式"""
        unsupported_file = Path("test.txt")
        try:
            unsupported_file.touch()
            self.assertFalse(
                VideoDownloader.is_local_file(str(unsupported_file)),
                "不支持的格式应返回False"
            )
        finally:
            if unsupported_file.exists():
                unsupported_file.unlink()
    
    def test_is_local_file_directory(self):
        """测试目录路径"""
        test_dir = Path("test_dir")
        try:
            test_dir.mkdir(exist_ok=True)
            self.assertFalse(
                VideoDownloader.is_local_file(str(test_dir)),
                "目录路径应返回False"
            )
        finally:
            if test_dir.exists():
                test_dir.rmdir()
    
    # ==================== 视频准备功能测试 ====================
    
    def test_prepare_video_local_file(self):
        """测试准备本地视频文件"""
        result = VideoDownloader.prepare_video(str(self.test_video_path))
        self.assertTrue(Path(result).exists(), "应返回存在的文件路径")
        self.assertTrue(Path(result).is_absolute(), "应返回绝对路径")
    
    def test_prepare_video_invalid_input(self):
        """测试无效输入"""
        invalid_inputs = [
            "invalid_url",
            "nonexistent.mp4",
            "",
        ]
        for invalid_input in invalid_inputs:
            with self.subTest(input=invalid_input):
                with self.assertRaises(ValueError, msg=f"应抛出ValueError: {invalid_input}"):
                    VideoDownloader.prepare_video(invalid_input)
    
    # ==================== 边界情况测试 ====================
    
    def test_url_case_sensitivity(self):
        """测试URL大小写敏感性"""
        urls = [
            "https://www.bilibili.com/video/BV1xx411c7mD",  # 大写BV
            "https://www.bilibili.com/video/bv1xx411c7mD",  # 小写bv
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertTrue(
                    VideoDownloader.is_bilibili_url(url),
                    "应支持大小写BV号"
                )
    
    def test_empty_string_handling(self):
        """测试空字符串处理"""
        self.assertFalse(VideoDownloader.is_bilibili_url(""))
        self.assertFalse(VideoDownloader.is_local_file(""))
    
    def test_whitespace_handling(self):
        """测试空白字符处理"""
        self.assertFalse(VideoDownloader.is_bilibili_url("   "))
        self.assertFalse(VideoDownloader.is_local_file("   "))
    
    # ==================== 路径处理测试 ====================
    
    def test_relative_path(self):
        """测试相对路径"""
        relative_path = "test_sample.mp4"
        self.assertTrue(
            VideoDownloader.is_local_file(relative_path),
            "应支持相对路径"
        )
    
    def test_absolute_path(self):
        """测试绝对路径"""
        absolute_path = self.test_video_path.absolute()
        self.assertTrue(
            VideoDownloader.is_local_file(str(absolute_path)),
            "应支持绝对路径"
        )


class TestVideoDownloaderIntegration(unittest.TestCase):
    """VideoDownloader集成测试类"""
    
    @unittest.skipUnless(
        os.getenv("RUN_INTEGRATION_TESTS"),
        "跳过集成测试,设置RUN_INTEGRATION_TESTS=1启用"
    )
    def test_download_bilibili_video(self):
        """
        集成测试: 下载B站视频
        注意: 此测试需要网络连接,默认跳过
        设置环境变量 RUN_INTEGRATION_TESTS=1 启用
        """
        # 使用一个公开的B站测试视频
        test_url = "https://www.bilibili.com/video/BV1xx411c7mD"
        
        try:
            result = VideoDownloader.download_bilibili_video(test_url)
            self.assertTrue(Path(result).exists(), "下载的文件应存在")
            self.assertTrue(Path(result).stat().st_size > 0, "文件大小应大于0")
        except Exception as e:
            self.fail(f"下载失败: {str(e)}")


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试
    suite.addTests(loader.loadTestsFromTestCase(TestVideoDownloader))
    suite.addTests(loader.loadTestsFromTestCase(TestVideoDownloaderIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 返回结果
    return result.wasSuccessful()


if __name__ == '__main__':
    print("=" * 70)
    print("VideoDownloader 单元测试")
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
