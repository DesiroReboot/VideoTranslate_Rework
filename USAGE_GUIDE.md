# 使用指南

## 快速开始 (5分钟)

### 第一步: 安装

**Windows用户:**
```bash
# 双击运行
install.bat

# 或在命令行运行
.\install.bat
```

**手动安装:**
```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置API Key (PowerShell)
setx DASHSCOPE_API_KEY "your_api_key_here"

# 3. 重启终端
```

### 第二步: 测试

```bash
# 查看帮助
python main.py

# 翻译本地视频
python main.py "test.mp4" English

# 翻译B站视频
python main.py "https://www.bilibili.com/video/BVxxx" Japanese
```

## 详细使用说明

### 1. 命令行模式

**基本语法:**
```bash
python main.py <视频路径或URL> <目标语言> [源语言]
```

**参数说明:**
- `视频路径或URL`: 
  - 本地文件: `video.mp4`, `C:\Videos\test.mp4`
  - B站URL: `https://www.bilibili.com/video/BVxxxxxxxxx`
  - B站短链: `https://b23.tv/xxxxxx`

- `目标语言`: 英文名称,如 `English`, `Japanese`, `Korean`

- `源语言`: (可选) 默认自动检测,也可指定如 `Chinese`

**示例:**

```bash
# 中文视频翻译为英文
python main.py "chinese_video.mp4" English

# 指定源语言为中文,翻译为日文
python main.py "video.mp4" Japanese Chinese

# 翻译B站视频
python main.py "https://www.bilibili.com/video/BV1xx411c7mD" English

# 韩语翻译为中文
python main.py "korean.mp4" Chinese Korean
```

### 2. Python代码调用

```python
from main import VideoTranslator

# 创建翻译器
translator = VideoTranslator()

# 翻译视频
output_video = translator.translate_video(
    url_or_path="video.mp4",
    target_language="English",
    source_language="Chinese"  # 可选
)

print(f"完成! 输出: {output_video}")
```

### 3. 批量处理

```python
from main import VideoTranslator

translator = VideoTranslator()

videos = ["video1.mp4", "video2.mp4", "video3.mp4"]
languages = ["English", "Japanese"]

for video in videos:
    for lang in languages:
        try:
            output = translator.translate_video(video, lang)
            print(f"✓ {video} -> {lang}: {output}")
        except Exception as e:
            print(f"✗ {video} -> {lang}: {e}")
```

## 支持的语言

### 主要语言 (完整支持)

| 语言 | 代码 | TTS支持 |
|------|------|---------|
| 中文 | Chinese | ✓ |
| 英语 | English | ✓ |
| 日语 | Japanese | ✓ |
| 韩语 | Korean | ✓ |
| 西班牙语 | Spanish | ✓ |
| 法语 | French | ✓ |
| 德语 | German | ✓ |
| 俄语 | Russian | ✓ |
| 意大利语 | Italian | ✓ |
| 葡萄牙语 | Portuguese | ✓ |

### 其他支持的语言

阿拉伯语(Arabic)、荷兰语(Dutch)、波兰语(Polish)、土耳其语(Turkish)、
越南语(Vietnamese)、泰语(Thai)、印地语(Hindi) 等92种语言。

翻译支持所有92种语言,但TTS仅支持上表中的10种主要语言。

## 输出文件说明

### 自动生成的文件

执行翻译后,会在 `output/` 目录生成以下文件:

```
output/
├── {视频名}_translated.mp4          # 翻译后的视频
├── {视频名}_original.txt            # 原文文本
└── {视频名}_translated_{语言}.txt   # 译文文本
```

### 临时文件

临时文件保存在 `temp/` 目录:

```
temp/
├── {视频名}.mp4                     # 下载的视频(如果是URL)
├── {视频名}_original.mp3           # 提取的原音频
└── translated_audio_xxxxx.wav      # 合成的新音频
```

**注意:** 临时文件可以定期清理以释放空间。

## 配置说明

### 系统配置文件: config.py

```python
# 修改模型
ASR_MODEL = "sensevoice-v1"      # 语音识别模型
MT_MODEL = "qwen-mt-plus"        # 翻译模型 (可改为 qwen-mt-turbo)
TTS_MODEL = "qwen3-tts-flash"    # 语音合成模型

# 修改TTS音色
TTS_VOICE_MAP = {
    "English": "Emily",    # 改为其他音色如 "Matthew" (男声)
    "Chinese": "Cherry",
    # ... 其他语言
}

# 修改输出目录
OUTPUT_DIR = Path("./my_output")  # 自定义输出目录
```

### 翻译提示词: Prompt_Video_Translate.txt

自定义翻译规则和风格:

```
##角色及任务
你是专业的翻译助手。你需要将用户的文本准确翻译成{target_language}。

##特殊需求
1. 保持原意,语言地道
2. 专业术语保持准确
3. [添加你的自定义规则]
```

**{target_language}** 会自动替换为目标语言。

## 常见问题排查

### Q1: 提示 "未配置DASHSCOPE_API_KEY"

**解决方法:**
```bash
# PowerShell
setx DASHSCOPE_API_KEY "your_api_key_here"

# 然后重启终端
```

### Q2: FFmpeg 错误

**症状:**
```
FFmpeg not found
```

**解决方法:**
1. 下载 FFmpeg: https://ffmpeg.org/download.html
2. 解压到 `C:\ffmpeg`
3. 添加 `C:\ffmpeg\bin` 到系统 PATH
4. 重启终端,运行 `ffmpeg -version` 验证

### Q3: 下载B站视频失败

**可能原因:**
1. URL格式不正确
2. 视频需要登录/大会员
3. 网络问题

**解决方法:**
1. 确认URL格式: `https://www.bilibili.com/video/BVxxxxxxxxx`
2. 先下载视频到本地再翻译
3. 检查网络连接

### Q4: 语音识别失败

**症状:**
```
[ASR] 警告: 识别失败,返回模拟文本用于测试
```

**原因:**
当前版本的ASR需要音频上传到云端,本地直接识别可能失败。

**临时解决:**
系统会返回测试文本继续流程,用于测试翻译和TTS功能。

**完整解决:**
需要配置阿里云OSS上传音频,详见高级配置。

### Q5: TTS音质不满意

**调整方法:**

在 `config.py` 中修改音色:

```python
TTS_VOICE_MAP = {
    "English": "Matthew",  # 尝试不同音色
    # 可用音色见文档
}
```

### Q6: 视频太长,处理时间久

**优化建议:**
1. 使用更快的模型: `MT_MODEL = "qwen-mt-turbo"`
2. 分段处理长视频
3. 云端处理器性能更好

**预估时间:**
- 5分钟视频: ~3-5分钟
- 10分钟视频: ~8-12分钟
- 30分钟视频: ~20-30分钟

## 高级用法

### 自定义音色

编辑 `config.py`:

```python
TTS_VOICE_MAP = {
    "English": "Matthew",  # 男声
    "Chinese": "Cherry",   # 女声
    # 完整音色列表见阿里云文档
}
```

### 使用不同模型

```python
# 更快但质量略低
MT_MODEL = "qwen-mt-turbo"

# 更高质量但较慢
MT_MODEL = "qwen-mt-plus"
```

### 批量翻译脚本

创建 `batch_translate.py`:

```python
from main import VideoTranslator
import os

translator = VideoTranslator()

# 扫描文件夹
video_dir = "videos/"
for filename in os.listdir(video_dir):
    if filename.endswith(".mp4"):
        video_path = os.path.join(video_dir, filename)
        
        # 翻译为英文和日文
        for lang in ["English", "Japanese"]:
            try:
                output = translator.translate_video(video_path, lang)
                print(f"✓ {filename} -> {lang}")
            except Exception as e:
                print(f"✗ {filename} -> {lang}: {e}")
```

### 配置OSS (高级)

对于ASR功能,需要配置阿里云OSS:

1. 安装 OSS SDK:
```bash
pip install oss2
```

2. 在 `ai_services.py` 中实现 `_upload_to_oss()`:
```python
import oss2

def _upload_to_oss(file_path: str) -> str:
    auth = oss2.Auth('AccessKeyId', 'AccessKeySecret')
    bucket = oss2.Bucket(auth, 'oss-cn-beijing.aliyuncs.com', 'bucket-name')
    
    object_name = f"audio/{Path(file_path).name}"
    bucket.put_object_from_file(object_name, file_path)
    
    return f"https://bucket-name.oss-cn-beijing.aliyuncs.com/{object_name}"
```

详细文档: https://help.aliyun.com/document_detail/32026.html

## 费用说明

### 免费额度

阿里云百炼开通后90天内提供免费额度:
- ASR (SenseVoice): 36,000秒
- TTS (Qwen3-TTS): 10,000字符
- 翻译 (Qwen-MT): 部分免费额度

### 收费标准 (超过免费额度后)

- **语音识别**: ¥0.00033/秒 (~¥2/小时)
- **语音合成**: ¥0.8/万字符
- **机器翻译**: 按token计费

**预估成本:**
- 10分钟视频翻译: ~¥1-3
- 建议先测试短视频,确认效果后再处理长视频

## 技术支持

- **项目问题**: 提交 GitHub Issue
- **API问题**: https://help.aliyun.com/zh/model-studio/
- **更新日志**: 查看 README.md

## 下一步

1. 运行示例: `python examples.py`
2. 阅读完整文档: `README.md`
3. 自定义配置: 修改 `config.py`
4. 批量处理: 参考高级用法

祝使用愉快! 🎉
