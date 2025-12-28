# 视频翻译系统 v1.0

一键翻译视频配音的自动化工具,支持B站视频URL和本地视频文件。

## 功能特性

✨ **核心功能**
- 🎥 B站视频自动下载 (支持BV号和短链接)
- 📁 本地视频文件支持 (.mp4, .avi, .mov, .mkv)
- 🎙️ 语音识别 (ASR) - 支持50+语言
- 🌐 文本翻译 - 支持92种语言互译
- 🗣️ 语音合成 (TTS) - 49种音色
- 🎬 自动替换配音并输出新视频

✅ **技术优势**
- 使用阿里云通义千问系列模型
- 高质量翻译和语音合成
- 自动选择最佳音色
- 保留原视频质量

## 安装指南

### 1. 环境要求

- Python 3.8+
- FFmpeg (用于视频处理)

### 2. 安装 FFmpeg

**Windows:**
1. 下载 FFmpeg: https://ffmpeg.org/download.html
2. 解压到 `C:\ffmpeg`
3. 添加 `C:\ffmpeg\bin` 到系统环境变量 PATH

**验证安装:**
```bash
ffmpeg -version
```

### 3. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 4. 配置 API Key

获取阿里云API Key:
1. 访问 https://dashscope.console.aliyun.com/
2. 登录并创建 API Key
3. 设置环境变量:

**Windows (PowerShell):**
```powershell
setx DASHSCOPE_API_KEY "your_api_key_here"
```

**验证配置:**
```bash
python -c "from config import validate_config; validate_config()"
```

## 使用方法

### 基本用法

```bash
# 翻译B站视频为英文
python main.py "https://www.bilibili.com/video/BVxxxxxxxxx" English

# 翻译本地视频为日文
python main.py "video.mp4" Japanese

# 指定源语言
python main.py "video.mp4" English Chinese
```

### 支持的语言

主要语言:
- `Chinese` - 中文
- `English` - 英语
- `Japanese` - 日语
- `Korean` - 韩语
- `Spanish` - 西班牙语
- `French` - 法语
- `German` - 德语
- `Russian` - 俄语
- `Italian` - 意大利语
- `Portuguese` - 葡萄牙语

更多语言请参考阿里云文档: https://help.aliyun.com/zh/model-studio/machine-translation

### 输出文件

所有输出文件位于 `output/` 目录:
- `{视频名}_translated.mp4` - 翻译后的视频
- `{视频名}_original.txt` - 原文文本
- `{视频名}_translated_{语言}.txt` - 译文文本

临时文件位于 `temp/` 目录,可定期清理。

## 项目结构

```
VideoTranslate_Rework/
├── main.py                          # 主程序入口
├── config.py                        # 配置管理
├── video_downloader.py             # 视频下载模块
├── audio_processor.py              # 音频处理模块
├── ai_services.py                  # AI服务集成
├── requirements.txt                # Python依赖
├── Prompt_Video_Translate.txt      # 翻译系统提示词
├── temp/                           # 临时文件目录
├── output/                         # 输出文件目录
└── README.md                       # 本文档
```

## 工作流程

```
输入视频 (URL/本地文件)
    ↓
1. 视频下载/验证
    ↓
2. 音频提取 (MP3)
    ↓
3. 语音识别 (ASR)
    ↓
4. 文本翻译 (MT)
    ↓
5. 语音合成 (TTS)
    ↓
6. 音频替换
    ↓
输出翻译后的视频
```

## 翻译提示词配置

系统提示词位于 `Prompt_Video_Translate.txt`,可自定义翻译规则:

```
##角色及任务
你是专业的中译英助手。你需要将用户的中文文本准确翻译成{target_language}。

##特殊需求
1.遇到有"负面"(粗俗/黄色)语义的语句时,应舍弃。
2.遇到"事实"类语句,应精准翻译。
```

## 常见问题

### Q: 下载B站视频失败（HTTP 412错误）?
A: 
1. **已修复**: 最新版本已添加正确的请求头,应该能正常下载
2. **更新yt-dlp**: 运行 `pip install -U yt-dlp`
3. **如果仍然失败**,可以使用B站Cookie：
   ```bash
   # 1. 在Chrome/Edge浏览器登录B站
   # 2. 安装扩展程序 "Get cookies.txt LOCALLY"
   # 3. 导出Cookie为 bilibili_cookies.txt 到项目目录
   # 4. 在 config.py 中取消注释 BILIBILI_COOKIE_FILE
   ```
4. **备用方案**: 先手动下载视频,然后使用本地文件模式

### Q: 下载B站视频失败（其他错误）?
A: 
1. 检查网络连接
2. 确认视频URL正确
3. 某些视频可能需要登录,暂不支持

### Q: 语音识别准确度低?
A: 
1. 确保音频清晰,无明显噪音
2. SenseVoice支持50+语言,会自动识别
3. 可以手动指定源语言提高准确度

### Q: TTS音色如何选择?
A: 
系统会根据目标语言自动选择合适音色,也可在 `config.py` 中自定义。

### Q: 视频处理时间长?
A: 
- 10分钟视频预计需要5-10分钟处理
- 主要耗时在ASR和视频合成
- 建议处理时保持网络畅通

## 注意事项

⚠️ **重要提示**
1. 需要稳定的网络连接 (调用云端API)
2. API调用会产生费用,请查看阿里云定价
3. 首次使用有免费额度
4. 建议先用短视频测试

🔒 **隐私安全**
- API Key 仅存储在本地环境变量
- 视频和音频仅用于转换,不会上传
- 临时文件可随时删除

## 技术支持

- 阿里云文档: https://help.aliyun.com/zh/model-studio/
- 项目仓库: (添加你的仓库地址)

## 许可证

MIT License

## 更新日志

### v1.0.0 (2025-12-10)
- ✅ 初始版本发布
- ✅ 支持B站视频下载
- ✅ 集成ASR、MT、TTS服务
- ✅ 自动化完整流程
