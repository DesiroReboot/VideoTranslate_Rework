# 单元测试说明

本项目包含完整的单元测试套件,用于验证各个模块的功能正确性。

## 📋 测试概览

### 测试文件列表

| 文件 | 测试对象 | 测试数量 | 描述 |
|------|----------|----------|------|
| `test_video_downloader.py` | VideoDownloader | 20+ | 视频下载器测试 |
| `test_audio_processor.py` | AudioProcessor | 15+ | 音频处理器测试 |
| `test_ai_services.py` | AIServices | 25+ | AI服务测试(ASR/MT/TTS) |
| `__init__.py` | - | - | 测试包初始化 |
| `TESTING.md` | - | - | 本文档 |

## 🚀 快速开始

### 运行所有测试

**方式1: 使用批处理脚本 (Windows)**
```bash
# 双击运行
run_tests.bat

# 或在命令行运行
.\run_tests.bat
```

**方式2: 使用Python脚本 (推荐)**
```bash
# 从项目根目录运行所有测试
python run_tests.py

# 详细模式
python run_tests.py -v 2

# 静默模式
python run_tests.py -v 0
```

### 运行单个测试文件

```bash
# 从项目根目录运行
python -m pytest test/test_video_downloader.py

# 或直接运行
python test/test_video_downloader.py
python test/test_audio_processor.py
python test/test_ai_services.py
```

### 运行特定测试

```bash
# 运行特定测试类
python run_tests.py -t test_video_downloader.TestVideoDownloader

# 运行特定测试方法
python run_tests.py -t test_video_downloader.TestVideoDownloader.test_is_bilibili_url_valid_bv
```

### 运行集成测试

集成测试默认跳过,需要手动启用:

```bash
# 启用集成测试 (需要网络连接)
python run_tests.py -i

# 或设置环境变量
set RUN_INTEGRATION_TESTS=1
python run_tests.py
```

## 📦 测试详情

### 1. VideoDownloader 测试

**测试类:** `TestVideoDownloader`

#### URL验证测试
- ✅ `test_is_bilibili_url_valid_bv` - BV号URL识别
- ✅ `test_is_bilibili_url_valid_av` - AV号URL识别
- ✅ `test_is_bilibili_url_valid_short` - 短链接识别
- ✅ `test_is_bilibili_url_invalid` - 无效URL识别

#### 本地文件验证测试
- ✅ `test_is_local_file_valid_mp4` - MP4文件识别
- ✅ `test_is_local_file_supported_formats` - 支持的格式
- ✅ `test_is_local_file_nonexistent` - 不存在的文件
- ✅ `test_is_local_file_unsupported_format` - 不支持的格式
- ✅ `test_is_local_file_directory` - 目录路径处理

#### 视频准备功能测试
- ✅ `test_prepare_video_local_file` - 本地文件准备
- ✅ `test_prepare_video_invalid_input` - 无效输入处理

#### 边界情况测试
- ✅ `test_url_case_sensitivity` - 大小写敏感性
- ✅ `test_empty_string_handling` - 空字符串处理
- ✅ `test_whitespace_handling` - 空白字符处理
- ✅ `test_relative_path` - 相对路径处理
- ✅ `test_absolute_path` - 绝对路径处理

#### 集成测试
- 🔄 `test_download_bilibili_video` - 真实下载测试 (需启用)

### 2. AudioProcessor 测试

**测试类:** `TestAudioProcessor`

#### 音频提取测试
- ✅ `test_extract_audio_success` - 成功提取音频
- ✅ `test_extract_audio_custom_output` - 自定义输出路径
- ✅ `test_extract_audio_no_audio_track` - 无音频轨道处理
- ✅ `test_extract_audio_exception_handling` - 异常处理

#### 音频替换测试
- ✅ `test_replace_audio_success` - 成功替换音频
- ✅ `test_replace_audio_duration_mismatch_longer` - 音频过长处理
- ✅ `test_replace_audio_duration_mismatch_shorter` - 音频过短处理
- ✅ `test_replace_audio_custom_output` - 自定义输出
- ✅ `test_replace_audio_exception_handling` - 异常处理

#### 音频时长获取测试
- ✅ `test_get_audio_duration_success` - 成功获取时长
- ✅ `test_get_audio_duration_zero` - 零时长处理
- ✅ `test_get_audio_duration_exception` - 异常处理

#### 边界情况测试
- ✅ `test_extract_audio_empty_path` - 空路径处理
- ✅ `test_replace_audio_empty_paths` - 空路径处理

#### 集成测试
- 🔄 `test_extract_and_replace_real_video` - 真实视频处理 (需启用)

### 3. AIServices 测试 ⭐ NEW

**测试类:** `TestAIServicesInit`, `TestAIServicesTranslation`, `TestAIServicesTTS`, `TestAIServicesASR`

#### 初始化测试
- ✅ `test_init_success` - 成功初始化
- ✅ `test_init_no_api_key` - 缺少API Key处理

#### 翻译功能测试
- ✅ `test_translate_text_success` - 成功翻译
- ✅ `test_translate_text_with_source_language` - 指定源语言
- ✅ `test_translate_text_empty_input` - 空文本处理
- ✅ `test_translate_text_api_error` - API错误处理
- ✅ `test_translate_text_uses_prompt` - 使用自定义提示词

#### TTS功能测试
- ✅ `test_text_to_speech_success` - 成功合成语音
- ✅ `test_text_to_speech_custom_voice` - 自定义音色
- ✅ `test_text_to_speech_auto_voice_selection` - 自动选择音色
- ✅ `test_text_to_speech_api_error` - API错误处理

#### ASR功能测试
- ✅ `test_speech_to_text_success` - 成功识别语音
- ✅ `test_speech_to_text_with_results_array` - 仍results数组提取
- ✅ `test_speech_to_text_api_error` - API错误处理

#### 辅助方法测试
- ✅ `test_download_file_success` - 文件下载成功
- ✅ `test_download_file_http_error` - HTTP错误处理
- ✅ `test_upload_to_oss_not_implemented` - OSS上传未实现

#### 集成测试
- 🔄 `test_translate_real_text` - 真实翻译测试 (需启用)
- 🔄 `test_tts_real_synthesis` - 真实语音合成 (需启用)

## 🔧 测试技术

### 使用的测试框架

- **unittest** - Python标准测试框架
- **unittest.mock** - Mock对象模拟

### Mock对象使用

测试中大量使用Mock对象,避免真实的文件和API调用:

```python
@patch('audio_processor.VideoFileClip')
def test_extract_audio_success(self, mock_video_clip):
    # 模拟视频对象
    mock_video = MagicMock()
    mock_audio = MagicMock()
    mock_video.audio = mock_audio
    mock_video_clip.return_value = mock_video
    
    # 执行测试
    result = AudioProcessor.extract_audio("test.mp4")
    
    # 验证行为
    mock_video_clip.assert_called_once()
```

### 测试覆盖范围

- ✅ **正常流程** - 验证核心功能正确性
- ✅ **边界情况** - 空值、空字符串、特殊字符
- ✅ **异常处理** - 错误输入、异常情况
- ✅ **参数验证** - 各种输入组合
- 🔄 **集成测试** - 真实环境测试 (可选)

## 📊 测试输出示例

### 成功输出

```
======================================================================
视频翻译系统 - 单元测试套件
======================================================================

加载测试模块: test_video_downloader
加载测试模块: test_audio_processor

共加载 35 个测试用例
======================================================================

test_is_bilibili_url_valid_bv ... ok
test_is_bilibili_url_valid_av ... ok
test_is_bilibili_url_valid_short ... ok
...

----------------------------------------------------------------------
Ran 35 tests in 0.123s

OK

======================================================================
测试摘要
======================================================================
运行测试: 35
成功: 35
失败: 0
错误: 0
跳过: 2
======================================================================
✓ 所有测试通过!
```

### 失败输出

```
FAIL: test_is_bilibili_url_valid_bv
----------------------------------------------------------------------
Traceback (most recent call last):
  ...
AssertionError: False is not true : 应识别为有效B站URL

----------------------------------------------------------------------
Ran 35 tests in 0.145s

FAILED (failures=1)

======================================================================
测试摘要
======================================================================
运行测试: 35
成功: 34
失败: 1
错误: 0
跳过: 2
======================================================================
✗ 部分测试失败,请检查上述错误
```

## 🎯 最佳实践

### 编写新测试

1. **继承unittest.TestCase**
```python
class TestMyClass(unittest.TestCase):
    def test_my_feature(self):
        # 测试代码
        pass
```

2. **使用setUp和tearDown**
```python
def setUp(self):
    """每个测试前执行"""
    self.test_file = Path("test.mp4")
    self.test_file.touch()

def tearDown(self):
    """每个测试后执行"""
    if self.test_file.exists():
        self.test_file.unlink()
```

3. **使用Mock避免真实调用**
```python
@patch('module.ExternalClass')
def test_with_mock(self, mock_class):
    mock_instance = MagicMock()
    mock_class.return_value = mock_instance
    # 测试代码
```

4. **使用断言验证结果**
```python
self.assertEqual(result, expected)
self.assertTrue(condition)
self.assertRaises(Exception, function, args)
```

### 运行测试前

1. ✅ 确保所有依赖已安装
2. ✅ 清理测试临时文件
3. ✅ 关闭可能冲突的程序

### 测试失败时

1. 📝 查看详细错误信息
2. 🔍 检查测试代码逻辑
3. 🐛 调试具体的测试方法
4. 🔄 修复后重新运行

## 📈 测试覆盖率

要查看测试覆盖率,可以使用coverage工具:

```bash
# 安装coverage
pip install coverage

# 运行测试并生成覆盖率报告
coverage run -m unittest discover
coverage report
coverage html  # 生成HTML报告
```

## ⚠️ 注意事项

### 集成测试

- 集成测试默认跳过,避免不必要的网络请求和文件操作
- 仅在需要验证真实环境时启用
- 需要准备真实的测试文件和网络连接

### Mock对象

- 单元测试应使用Mock对象,不依赖外部资源
- Mock对象仅模拟接口行为,不测试实际功能
- 集成测试用于验证真实环境下的功能

### 临时文件

- 测试会创建临时文件,通过setUp/tearDown自动清理
- 如果测试中断,可能需要手动清理`test_*`文件
- 临时文件目录: `test_audio_temp/`

## 🔄 持续集成

可以将测试集成到CI/CD流程:

```yaml
# .github/workflows/test.yml 示例
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.8
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: python run_tests.py -v 1
```

## 📚 相关文档

- [Python unittest文档](https://docs.python.org/3/library/unittest.html)
- [unittest.mock文档](https://docs.python.org/3/library/unittest.mock.html)
- [项目README](README.md)

## 🎉 总结

- ✅ 完整的单元测试套件
- ✅ 使用Mock对象避免真实调用
- ✅ 覆盖正常流程和异常情况
- ✅ 支持单个和批量运行
- ✅ 清晰的测试输出和摘要

测试是保证代码质量的重要手段,建议在修改代码后及时运行测试!
