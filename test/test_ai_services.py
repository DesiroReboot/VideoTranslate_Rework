"""
AI服务模块单元测试
测试AIServices类的各项功能 (ASR/翻译/TTS)
"""

import unittest
import os
import sys
import importlib
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
#from config import test_api_key

# 添加父目录到路径以导入模块
sys.path.insert(0, str(Path(__file__).parent.parent))

# 不在这里全局导入AIServices，避免提前初始化

class TestAIServicesInit(unittest.TestCase):
    """AIServices初始化测试"""
    
    # @classmethod
    # def setUpClass(cls):
    #     """在所有测试方法之前设置环境变量"""
    #     super().setUpClass()
    #     os.environ['DASHSCOPE_API_KEY'] = 'test_api_key'
    
    # @classmethod
    # def tearDownClass(cls):
    #     """在所有测试方法之后清理环境变量"""
    #     super().tearDownClass()
    #     if 'DASHSCOPE_API_KEY' in os.environ:
    #         del os.environ['DASHSCOPE_API_KEY']
    
    def test_init_success(self):
        """测试成功初始化"""
        # 先设置环境变量
        with patch.dict(os.environ, {'DASHSCOPE_API_KEY': 'test_api_key'}):
            # 在环境变量设置后重新导入相关模块
            import importlib
            import config
            importlib.reload(config)
            if 'ai_services' in sys.modules:
                importlib.reload(sys.modules['ai_services'])

            from ai_services import AIServices

            with patch('ai_services.dashscope') as mock_dashscope:
                with patch('ai_services.OpenAI') as mock_openai:
                    ai = AIServices()

                    # 验证DashScope配置
                    self.assertEqual(mock_dashscope.api_key, 'test_api_key')

                    # 验证OpenAI客户端创建
                    mock_openai.assert_called_once()
    
    def test_init_no_api_key(self):
        """测试缺少API Key"""
        # 临时保存并删除API key
        original_key = os.environ.pop('DASHSCOPE_API_KEY', None)
        try:
            # 在环境变量删除后重新导入模块
            import importlib
            import config
            importlib.reload(config)
            if 'ai_services' in sys.modules:
                importlib.reload(sys.modules['ai_services'])

            from ai_services import AIServices

            with self.assertRaises(ValueError) as context:
                AIServices()

            self.assertIn("未配置DASHSCOPE_API_KEY", str(context.exception))
        finally:
            # 恢复原始环境变量
            if original_key is not None:
                os.environ['DASHSCOPE_API_KEY'] = original_key


class TestAIServicesTranslation(unittest.TestCase):
    """文本翻译功能测试"""
    
    def setUp(self):
        """测试前准备"""
        # Mock环境变量和依赖
        self.env_patcher = patch.dict(os.environ, {'DASHSCOPE_API_KEY': 'test_key'})
        self.env_patcher.start()
        
        self.dashscope_patcher = patch('ai_services.dashscope')
        self.openai_patcher = patch('ai_services.OpenAI')
        
        self.mock_dashscope = self.dashscope_patcher.start()
        self.mock_openai = self.openai_patcher.start()

        # 在mock之后导入并创建AIServices实例
        from ai_services import AIServices
        self.ai_services = AIServices()
    
    def tearDown(self):
        """测试后清理"""
        self.env_patcher.stop()
        self.dashscope_patcher.stop()
        self.openai_patcher.stop()
    
    def test_translate_text_success(self):
        """测试成功翻译文本"""
        # Mock翻译响应
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = "The weather is nice today, let's go for a walk in the park."
        
        self.ai_services.openai_client.chat.completions.create = MagicMock(
            return_value=mock_completion
        )
        
        # 执行翻译
        result = self.ai_services.translate_text(
            "今天天气真好,我们一起去公园散步吧。",
            "English"
        )
        
        # 验证
        self.assertIsNotNone(result)
        self.assertIn("weather", result.lower())
        self.assertIn("park", result.lower())
    
    def test_translate_text_with_source_language(self):
        """测试指定源语言的翻译"""
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = "今日は天気がいいですね"
        
        self.ai_services.openai_client.chat.completions.create = MagicMock(
            return_value=mock_completion
        )
        
        # 执行翻译
        result = self.ai_services.translate_text(
            "The weather is nice today",
            "Japanese",
            "English"
        )
        
        # 验证调用参数
        call_args = self.ai_services.openai_client.chat.completions.create.call_args
        self.assertIn('extra_body', call_args[1])
        self.assertEqual(
            call_args[1]['extra_body']['translation_options']['source_lang'],
            'English'
        )
    
    def test_translate_text_empty_input(self):
        """测试空文本输入"""
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = ""
        
        self.ai_services.openai_client.chat.completions.create = MagicMock(
            return_value=mock_completion
        )
        
        result = self.ai_services.translate_text("", "English")
        self.assertEqual(result, "")
    
    def test_translate_text_api_error(self):
        """测试API错误处理"""
        self.ai_services.openai_client.chat.completions.create = MagicMock(
            side_effect=Exception("API错误")
        )
        
        with self.assertRaises(Exception) as context:
            self.ai_services.translate_text("测试", "English")
        
        self.assertIn("文本翻译失败", str(context.exception))
    
    @patch('ai_services.load_translation_prompt')
    def test_translate_text_uses_prompt(self, mock_load_prompt):
        """测试使用自定义提示词"""
        mock_load_prompt.return_value = "Custom prompt for English"
        
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = "Translation"
        
        self.ai_services.openai_client.chat.completions.create = MagicMock(
            return_value=mock_completion
        )
        
        self.ai_services.translate_text("测试", "English")
        
        # 验证加载了提示词
        mock_load_prompt.assert_called_once_with("English")
        
        # 验证system消息包含提示词
        call_args = self.ai_services.openai_client.chat.completions.create.call_args
        messages = call_args[1]['messages']
        self.assertEqual(messages[0]['role'], 'system')
        self.assertEqual(messages[0]['content'], "Custom prompt for English")


class TestAIServicesTTS(unittest.TestCase):
    """语音合成功能测试"""
    
    def setUp(self):
        """测试前准备"""
        self.env_patcher = patch.dict(os.environ, {'DASHSCOPE_API_KEY': 'test_key'})
        self.env_patcher.start()
        
        self.dashscope_patcher = patch('ai_services.dashscope')
        self.openai_patcher = patch('ai_services.OpenAI')
        
        self.mock_dashscope = self.dashscope_patcher.start()
        self.mock_openai = self.openai_patcher.start()

        # 在mock之后导入并创建AIServices实例
        from ai_services import AIServices
        self.ai_services = AIServices()
    
    def tearDown(self):
        """测试后清理"""
        self.env_patcher.stop()
        self.dashscope_patcher.stop()
        self.openai_patcher.stop()
    
    @patch('ai_services.AIServices._download_file')
    def test_text_to_speech_success(self, mock_download):
        """测试成功合成语音"""
        mock_download.return_value = None
        # Mock TTS响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.output.audio.url = "https://example.com/audio.wav"
        
        self.mock_dashscope.MultiModalConversation.call = MagicMock(
            return_value=mock_response
        )
        
        # 执行TTS
        result = self.ai_services.text_to_speech(
            "Hello, world!",
            language="English"
        )
        
        # 验证
        self.assertIsNotNone(result)
        self.assertTrue(result.endswith('.wav'))
        mock_download.assert_called_once()
    
    @patch('ai_services.AIServices._download_file')
    def test_text_to_speech_custom_voice(self, mock_download):
        """测试自定义音色"""
        mock_download.return_value = None
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.output.audio.url = "https://example.com/audio.wav"
        
        self.mock_dashscope.MultiModalConversation.call = MagicMock(
            return_value=mock_response
        )
        
        # 使用自定义音色
        self.ai_services.text_to_speech(
            "Test",
            language="English",
            voice="Matthew"
        )
        
        # 验证使用了指定音色
        call_args = self.mock_dashscope.MultiModalConversation.call.call_args
        self.assertEqual(call_args[1]['voice'], 'Matthew')
    
    @patch('ai_services.TTS_VOICE_MAP', {'English': 'Emily'})
    @patch('ai_services.AIServices._download_file')
    def test_text_to_speech_auto_voice_selection(self, mock_download):
        mock_download.return_value = None
        """测试自动选择音色"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.output.audio.url = "https://example.com/audio.wav"
        
        self.mock_dashscope.MultiModalConversation.call = MagicMock(
            return_value=mock_response
        )
        
        # 不指定音色,应自动选择
        self.ai_services.text_to_speech(
            "Test",
            language="English"
        )
        
        # 验证使用了默认音色
        call_args = self.mock_dashscope.MultiModalConversation.call.call_args
        self.assertEqual(call_args[1]['voice'], 'Emily')
    
    def test_text_to_speech_api_error(self):
        """测试API错误"""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.message = "TTS失败"
        
        self.mock_dashscope.MultiModalConversation.call = MagicMock(
            return_value=mock_response
        )
        
        with self.assertRaises(Exception) as context:
            self.ai_services.text_to_speech("Test", "English")
        
        self.assertIn("语音合成失败", str(context.exception))


class TestAIServicesASR(unittest.TestCase):
    """语音识别功能测试"""
    
    def setUp(self):
        """测试前准备"""
        self.env_patcher = patch.dict(os.environ, {'DASHSCOPE_API_KEY': 'test_key'})
        self.env_patcher.start()
        
        self.dashscope_patcher = patch('ai_services.dashscope')
        self.openai_patcher = patch('ai_services.OpenAI')
        
        self.mock_dashscope = self.dashscope_patcher.start()
        self.mock_openai = self.openai_patcher.start()

        # 在mock之后导入并创建AIServices实例
        from ai_services import AIServices
        self.ai_services = AIServices()
    
    def tearDown(self):
        """测试后清理"""
        self.env_patcher.stop()
        self.dashscope_patcher.stop()
        self.openai_patcher.stop()
    
    @patch('builtins.open', new_callable=mock_open, read_data=b'fake_audio_data')
    @patch('dashscope.audio.asr.Recognition')
    def test_speech_to_text_success(self, mock_recognition, mock_file):
        """测试成功识别语音"""
        # Mock识别响应
        mock_result = MagicMock()
        mock_result.status_code = 200
        mock_result.output = {'text': '今天天气真好'}
        
        mock_recognition_instance = MagicMock()
        mock_recognition_instance.call = MagicMock(return_value=mock_result)
        mock_recognition.return_value = mock_recognition_instance
        
        # 执行识别
        result = self.ai_services.speech_to_text("test_audio.mp3")
        
        # 验证
        self.assertEqual(result, '今天天气真好')
    
    @patch('builtins.open', new_callable=mock_open, read_data=b'fake_audio_data')
    @patch('dashscope.audio.asr.Recognition')
    def test_speech_to_text_with_results_array(self, mock_recognition, mock_file):
        """测试从results数组提取文本"""
        # Mock识别响应 (文本在results中)
        mock_result = MagicMock()
        mock_result.status_code = 200
        mock_result.output = {
            'text': '',
            'results': [
                {'text': '今天'},
                {'text': '天气'},
                {'text': '真好'}
            ]
        }
        
        mock_recognition_instance = MagicMock()
        mock_recognition_instance.call = MagicMock(return_value=mock_result)
        mock_recognition.return_value = mock_recognition_instance
        
        # 执行识别
        result = self.ai_services.speech_to_text("test_audio.mp3")
        
        # 验证拼接结果
        self.assertEqual(result, '今天 天气 真好')
    
    @patch('builtins.open', new_callable=mock_open, read_data=b'fake_audio_data')
    @patch('dashscope.audio.asr.Recognition')
    def test_speech_to_text_api_error(self, mock_recognition, mock_file):
        """测试API错误返回测试文本"""
        # Mock识别失败
        mock_recognition_instance = MagicMock()
        mock_recognition_instance.call = MagicMock(
            side_effect=Exception("API错误")
        )
        mock_recognition.return_value = mock_recognition_instance
        
        # 执行识别 (应返回测试文本而不是抛出异常)
        result = self.ai_services.speech_to_text("test_audio.mp3")
        
        # 验证返回了占位文本
        self.assertIn("测试文本", result)


class TestAIServicesHelpers(unittest.TestCase):
    """辅助方法测试"""
    
    @patch('ai_services.requests.get')
    def test_download_file_success(self, mock_get):
        """测试文件下载成功"""
        from ai_services import AIServices

        # Mock HTTP响应
        mock_response = MagicMock()
        mock_response.iter_content = MagicMock(
            return_value=[b'chunk1', b'chunk2']
        )
        mock_get.return_value = mock_response

        # 创建临时输出路径
        output_path = "test_download.wav"

        try:
            # 执行下载
            with patch('builtins.open', mock_open()) as mock_file:
                AIServices._download_file("https://example.com/audio.wav", output_path)
                
                # 验证写入
                mock_file.assert_called_once_with(output_path, 'wb')
        finally:
            # 清理
            if Path(output_path).exists():
                Path(output_path).unlink()
    
    @patch('ai_services.requests.get')
    def test_download_file_http_error(self, mock_get):
        """测试HTTP错误"""
        # Mock HTTP错误
        mock_get.side_effect = Exception("HTTP错误")
        
        with self.assertRaises(Exception):
            AIServices._download_file("https://example.com/audio.wav", "output.wav")
    
    def test_upload_to_oss_not_implemented(self):
        """测试OSS上传未实现"""
        from ai_services import AIServices

        with self.assertRaises(NotImplementedError) as context:
            AIServices._upload_to_oss("test.mp3")
        
        self.assertIn("配置阿里云OSS", str(context.exception))


class TestAIServicesIntegration(unittest.TestCase):
    """AIServices集成测试"""
    
    @unittest.skipUnless(
        os.getenv("RUN_INTEGRATION_TESTS") and os.getenv("DASHSCOPE_API_KEY"),
        "跳过集成测试,需要设置RUN_INTEGRATION_TESTS=1和DASHSCOPE_API_KEY"
    )
    def test_translate_real_text(self):
        """
        集成测试: 真实翻译
        需要: RUN_INTEGRATION_TESTS=1 和有效的 DASHSCOPE_API_KEY
        """
        ai = AIServices()
        
        test_text = "今天天气真好,我们一起去公园散步吧。"
        print(f"\n原文: {test_text}")
        
        try:
            translated = ai.translate_text(test_text, "English")
            print(f"译文: {translated}")
            
            # 基本验证
            self.assertIsNotNone(translated)
            self.assertTrue(len(translated) > 0)
            self.assertIn("weather", translated.lower())
            
        except Exception as e:
            self.fail(f"翻译失败: {str(e)}")
    
    @unittest.skipUnless(
        os.getenv("RUN_INTEGRATION_TESTS") and os.getenv("DASHSCOPE_API_KEY"),
        "跳过集成测试,需要设置RUN_INTEGRATION_TESTS=1和DASHSCOPE_API_KEY"
    )
    def test_tts_real_synthesis(self):
        """
        集成测试: 真实语音合成
        需要: RUN_INTEGRATION_TESTS=1 和有效的 DASHSCOPE_API_KEY
        """
        ai = AIServices()
        
        test_text = "Hello, this is a test."
        print(f"\n合成文本: {test_text}")
        
        try:
            output_path = ai.text_to_speech(test_text, language="English")
            print(f"输出音频: {output_path}")
            
            # 验证文件存在
            self.assertTrue(Path(output_path).exists())
            self.assertTrue(Path(output_path).stat().st_size > 0)
            
            # 清理
            Path(output_path).unlink()
            
        except Exception as e:
            self.fail(f"TTS失败: {str(e)}")


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试
    suite.addTests(loader.loadTestsFromTestCase(TestAIServicesInit))
    suite.addTests(loader.loadTestsFromTestCase(TestAIServicesTranslation))
    suite.addTests(loader.loadTestsFromTestCase(TestAIServicesTTS))
    suite.addTests(loader.loadTestsFromTestCase(TestAIServicesASR))
    suite.addTests(loader.loadTestsFromTestCase(TestAIServicesHelpers))
    suite.addTests(loader.loadTestsFromTestCase(TestAIServicesIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 返回结果
    return result.wasSuccessful()


if __name__ == '__main__':
    print("=" * 70)
    print("AIServices 单元测试")
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
