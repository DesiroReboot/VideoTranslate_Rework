# 测试目录

本目录包含视频翻译系统的所有单元测试。

## 📁 文件结构

```
test/
├── __init__.py                  # 测试包初始化
├── test_video_downloader.py    # VideoDownloader 测试 (20+ 测试)
├── test_audio_processor.py     # AudioProcessor 测试 (15+ 测试)
├── test_ai_services.py          # AIServices 测试 (25+ 测试) ⭐ NEW
├── TESTING.md                   # 详细测试文档
└── README.md                    # 本文档
```

## 🚀 快速开始

### 运行所有测试

从**项目根目录**运行:

```bash
# 使用批处理脚本 (Windows)
.\run_tests.bat

# 使用Python脚本
python run_tests.py

# 详细输出
python run_tests.py -v 2
```

### 运行单个测试文件

```bash
# 从项目根目录运行
python test/test_video_downloader.py
python test/test_audio_processor.py  
python test/test_ai_services.py
```

### 前置条件

确保已安装所有依赖:

```bash
pip install -r requirements.txt
```

## 📦 测试覆盖

| 模块 | 测试数 | 状态 |
|------|--------|------|
| VideoDownloader | 20+ | ✅ 完成 |
| AudioProcessor | 15+ | ✅ 完成 |
| AIServices | 25+ | ✅ 完成 |

**总计: 60+ 个测试用例**

## 🔧 测试特性

- ✅ 使用 **unittest** 框架
- ✅ 使用 **Mock** 对象避免真实API调用
- ✅ 覆盖正常流程和异常情况
- ✅ 支持集成测试 (可选)

## 📝 主要测试类

### test_video_downloader.py

- `TestVideoDownloader` - URL验证、文件验证、边界情况
- `TestVideoDownloaderIntegration` - 真实下载测试

### test_audio_processor.py

- `TestAudioProcessor` - 音频提取、替换、时长获取
- `TestAudioProcessorIntegration` - 真实音视频处理

### test_ai_services.py ⭐ NEW

- `TestAIServicesInit` - 初始化测试
- `TestAIServicesTranslation` - 翻译功能测试
- `TestAIServicesTTS` - 语音合成测试
- `TestAIServicesASR` - 语音识别测试
- `TestAIServicesHelpers` - 辅助方法测试
- `TestAIServicesIntegration` - 集成测试

## 🎯 注意事项

1. **集成测试默认跳过** - 使用 `python run_tests.py -i` 启用
2. **Mock对象** - 单元测试使用Mock避免真实文件和API操作
3. **导入路径** - 测试文件通过 `sys.path` 添加父目录以导入模块
4. **临时文件** - 测试会创建临时文件,通过 setUp/tearDown 自动清理

## 📚 详细文档

查看 [TESTING.md](TESTING.md) 获取完整的测试说明、示例和最佳实践。

## 🔄 最近更新

- **2025-12-10**: 添加 `test_ai_services.py`,包含25+个AIServices测试
- 所有测试文件已迁移到 `test/` 目录
- 删除 `ai_services.py` 中的测试代码
