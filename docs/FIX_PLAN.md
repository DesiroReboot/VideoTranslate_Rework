# 代码修复计划 (Fix Plan)

**生成日期:** 2026-01-02
**基于:** CODE_REVIEW_REPORT.md
**优先级:** P0全部 + P1的1/2/3 + P2全部

---

## 修复统计

| 优先级 | 问题数 | 涉及文件 | 预计工作量 |
|--------|--------|----------|------------|
| P0 | 3 | 2 | 30分钟 |
| P1 | 4 | 5 | 1.5小时 |
| P2 | 5 | 8 | 2小时 |
| **合计** | **12** | **15** | **~4小时** |

---

## P0 - 严重问题 (立即修复)

### P0-1: API密钥管理不安全

**文件:** `config.py`
**行号:** 12-13, 28-31

#### 修改内容:

```diff
--- a/config.py
+++ b/config.py
@@ -9,15 +9,29 @@
 from pathlib import Path
 import os

+# ==================== 环境变量管理 ====================
+from dotenv import load_dotenv
+
+# 自动加载.env文件（如果存在）
+load_dotenv()
+
+
+def _get_required_env(key: str) -> str:
+    """
+    获取必需的环境变量
+
+    Args:
+        key: 环境变量名称
+
+    Returns:
+        环境变量的值
+
+    Raises:
+        ValueError: 环境变量未设置
+    """
+    value = os.getenv(key)
+    if not value:
+        raise ValueError(f"必须设置环境变量: {key}\n请通过以下方式设置:\n  1. 在.env文件中添加: {key}=your_value\n  2. 或在系统环境变量中设置")
+    return value
+
+
 # 阿里云API密钥
-DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_KEY")
+DASHSCOPE_API_KEY = _get_required_env("DASHSCOPE_API_KEY")

 # 阿里云API基础URL (北京地域)
 DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com"
@@ -27,10 +41,10 @@ OSS_ENDPOINT = "oss-cn-hangzhou.aliyuncs.com"
-OSS_ACCESS_KEY_ID = os.getenv("OSS_ACCESS_KEY_ID")
-OSS_ACCESS_KEY_SECRET = os.getenv("OSS_ACCESS_KEY_SECRET")
-OSS_BUCKET_NAME = os.getenv("OSS_BUCKET_NAME")
+OSS_ACCESS_KEY_ID = _get_required_env("OSS_ACCESS_KEY_ID")
+OSS_ACCESS_KEY_SECRET = _get_required_env("OSS_ACCESS_KEY_SECRET")
+OSS_BUCKET_NAME = _get_required_env("OSS_BUCKET_NAME")
```

**验证方法:**
```bash
# 测试环境变量未设置的情况
unset DASHSCOPE_API_KEY
python -c "from config import DASHSCOPE_API_KEY"  # 应该抛出ValueError
```

---

### P0-2: 敏感信息泄露风险

**文件:** `ai_services.py`
**行号:** 99-101

#### 修改内容:

```diff
--- a/ai_services.py
+++ b/ai_services.py
@@ -96,9 +96,8 @@ class AIServices:
         # 设置API密钥
         dashscope.api_key = DASHSCOPE_API_KEY

-        print(
-            f"[初始化] API密钥已加载 (长度: {len(dashscope.api_key) if dashscope.api_key else 0})"
-        )
+        # 移除敏感信息打印
+        print("[初始化] API密钥已配置")
```

---

### P0-3: OSS签名URL与公开URL混用

**文件:** `ai_services.py`
**行号:** 249-277

#### 修改内容:

```diff
--- a/ai_services.py
+++ b/ai_services.py
@@ -246,9 +246,7 @@ class AIServices:
         """
         上传文件到OSS供Fun-ASR访问
         """
-        # 设置公共读权限，方便Fun-ASR访问
-        headers = {"x-oss-object-acl": "public-read"}
-
         # 生成唯一文件名（时间戳 + 随机数）
         import time
         import random
@@ -258,7 +256,9 @@ class AIServices:
         # 上传文件
         result = bucket.put_object_from_file(object_name, str(resolved_path))

-        # 生成公开URL
+        # 生成签名URL（1小时有效期）
+        # Fun-ASR识别通常需要几分钟，1小时足够
+        signed_url = bucket.sign_url('GET', object_name, 3600)
+
         return f"https://{OSS_BUCKET_NAME}.{OSS_ENDPOINT}/{object_name}", object_name
```

**注意:** 此修改与`speech_to_text.py`保持一致，统一使用签名URL方案。

---

## P1 - 重要问题 (近期修复)

### P1-1: 资源泄漏风险 - audio_processor.py

**文件:** `audio_processor.py`
**行号:** 128-158

#### 修改内容:

```diff
--- a/audio_processor.py
+++ b/audio_processor.py
@@ -125,10 +125,16 @@ def replace_audio(
     print(f"正在替换视频音频...")
     print(f"视频: {video_path}")
     print(f"新音频: {new_audio_path}")
-    video = VideoFileClip(video_path)
-    new_audio = AudioFileClip(new_audio_path)
+
+    video = None
+    new_audio = None
+    try:
+        video = VideoFileClip(video_path)
+        new_audio = AudioFileClip(new_audio_path)

-    final_video = video.set_audio(new_audio)
+        final_video = video.set_audio(new_audio)
+
         # 如果新音频时长超过视频，裁剪音频
         if new_audio.duration > video.duration:
             print(
@@ -138,14 +144,20 @@ def replace_audio(
             )
             # 从新音频中裁剪与视频时长相同的片段
             new_audio = new_audio.subclip(0, video.duration)
-            final_video = video.set_audio(new_audio)
-        # 写入输出文件
-        final_video.write_videofile(
-            output_path,
-            codec="libx264",
-            audio_codec="aac",
-            temp_audiofile="temp-audio.m4a",
-            remove_temp=True,
-        )
+            final_video = video.set_audio(new_audio)
+
+        # 写入输出文件
+        final_video.write_videofile(
+            output_path,
+            codec="libx264",
+            audio_codec="aac",
+            temp_audiofile="temp-audio.m4a",
+            remove_temp=True,
+        )
+
+    finally:
+        # 确保资源被释放
+        if video is not None:
+            video.close()
+        if new_audio is not None:
+            new_audio.close()
```

---

### P1-2: 并发安全问题 - speech_to_text.py

**文件:** `speech_to_text.py`
**行号:** 11, 88-91, 107-117, 139

#### 修改内容:

```diff
--- a/speech_to_text.py
+++ b/speech_to_text.py
@@ -8,7 +8,7 @@

 import sys
 import time
-import uuid
 import json
+import uuid
+import threading
 from pathlib import Path
 from typing import Optional, Tuple, List, Dict

@@ -85,6 +85,9 @@ class SpeechToText:
         # 初始化评分历史数据
         self.score_history: List[Dict] = []
         if ASR_ENABLE_SCORE_COLLECTION:
+            # 初始化线程锁，保护评分历史数据
+            self.score_lock = threading.Lock()
             self._load_score_history()
             print(f"[初始化] ASR评分数据收集已启用 (历史记录: {len(self.score_history)}条)")

@@ -104,9 +107,11 @@ class SpeechToText:

     def _save_score_history(self) -> None:
         """保存ASR评分历史数据"""
+        if not ASR_ENABLE_SCORE_COLLECTION:
+            return

         try:
-            with open(ASR_SCORE_HISTORY_FILE, "w", encoding="utf-8") as f:
+            with self.score_lock, open(ASR_SCORE_HISTORY_FILE, "w", encoding="utf-8") as f:
                 json.dump(self.score_history, f, ensure_ascii=False, indent=2)
             print(f"[评分历史] 已保存 {len(self.score_history)} 条记录")
         except Exception as e:
@@ -119,9 +124,11 @@ class SpeechToText:

     def _add_score_record(self, score: float, audio_path: str, text_length: int) -> None:
         """添加评分记录到历史"""
+        if not ASR_ENABLE_SCORE_COLLECTION:
+            return

         record = {
@@ -132,7 +139,9 @@ class SpeechToText:
             "text_length": text_length,
         }

-        self.score_history.append(record)
+        with self.score_lock:
+            self.score_history.append(record)
         self._save_score_history()
```

---

### P1-3: 异常处理过于宽泛 - main.py

**文件:** `main.py`
**行号:** 236-238

#### 修改内容:

```diff
--- a/main.py
+++ b/main.py
@@ -233,7 +233,17 @@ class VideoTranslator:
             print(f"\n✗ 错误: {str(e)}")

-        except Exception as e:
-            print(f"\n✗ 错误: {str(e)}")
-            raise
+        except (ValueError, SecurityError) as e:
+            print(f"\n✗ 参数或安全错误: {str(e)}")
+            logging.exception("详细错误信息:")
+            raise
+        except (IOError, OSError) as e:
+            print(f"\n✗ 文件操作失败: {str(e)}")
+            logging.exception("详细错误信息:")
+            raise
+        except requests.exceptions.RequestException as e:
+            print(f"\n✗ 网络请求失败: {str(e)}")
+            logging.exception("详细错误信息:")
+            raise
+        except Exception as e:
+            print(f"\n✗ 未知错误: {str(e)}")
+            logging.exception("详细错误信息:")
+            raise
```

**同时需要添加logging导入:**

```diff
--- a/main.py
+++ b/main.py
@@ -1,3 +1,4 @@
+import logging
 import sys
 from pathlib import Path
```

---

## P2 - 次要问题 (优化)

### P2-1: 消除代码重复 - 提取公共ASR逻辑

**新建文件:** `asr_client.py`

#### 文件内容:

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASR客户端模块
统一的语音识别接口，消除代码重复
"""

import time
from typing import Tuple
from pathlib import Path

import requests
import oss2
import dashscope
from http import HTTPStatus
from dashscope.audio.asr import Transcription

from config import (
    DASHSCOPE_API_KEY,
    ASR_MODEL,
    ASR_LANGUAGE_HINTS,
    OSS_ENDPOINT,
    OSS_ACCESS_KEY_ID,
    OSS_ACCESS_KEY_SECRET,
    OSS_BUCKET_NAME,
    OSS_ENABLE_UUID_FILENAME,
    OSS_AUTO_CLEANUP,
)


class ASRClient:
    """统一的ASR客户端"""

    def __init__(self):
        """初始化ASR客户端"""
        dashscope.api_key = DASHSCOPE_API_KEY

    def upload_audio_to_oss(self, audio_path: str) -> Tuple[str, str]:
        """
        上传音频文件到OSS

        Args:
            audio_path: 音频文件路径

        Returns:
            (签名URL, 对象名称)
        """
        auth = oss2.Auth(OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET)
        bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET_NAME)

        # 生成UUID文件名
        import uuid
        file_ext = Path(audio_path).suffix
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        object_name = f"video_translate/audio/{unique_filename}"

        # 上传文件
        print(f"[OSS] 上传文件: {Path(audio_path).name} -> {object_name}")
        bucket.put_object_from_file(object_name, audio_path)

        # 生成签名URL
        signed_url = bucket.sign_url('GET', object_name, 3600)

        print(f"[OSS] 文件上传成功 (大小: {Path(audio_path).stat().st_size / 1024:.2f}KB)")
        print(f"[OSS] 安全措施: 签名URL(1小时有效) + 自动清理")

        return signed_url, object_name

    def cleanup_oss_file(self, object_name: str) -> None:
        """
        清理OSS文件

        Args:
            object_name: OSS对象名称
        """
        if not OSS_AUTO_CLEANUP:
            return

        try:
            auth = oss2.Auth(OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET)
            bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET_NAME)
            bucket.delete_object(object_name)
            print(f"[OSS] 已删除临时文件: {object_name}")
        except Exception as e:
            print(f"[OSS] 删除文件失败（非致命错误）: {e}")

    def recognize_audio(
        self,
        audio_path: str,
        node_id: int = 0
    ) -> str:
        """
        识别音频文件

        Args:
            audio_path: 音频文件路径
            node_id: 节点ID（用于分布式ASR）

        Returns:
            识别的文本内容
        """
        print(f"[ASR节点{node_id}] 开始识别...")

        # 上传音频到OSS
        audio_url, object_name = self.upload_audio_to_oss(audio_path)

        try:
            # 调用Fun-ASR
            task_response = Transcription.async_call(
                model=ASR_MODEL,
                file_urls=[audio_url],
                language_hints=ASR_LANGUAGE_HINTS,
            )

            if task_response.status_code != HTTPStatus.OK:
                raise Exception(f"ASR任务提交失败: {task_response.message}")

            task_id = task_response.output["task_id"]
            print(f"[ASR节点{node_id}] 任务ID: {task_id}, 等待识别完成...")

            # 轮询任务状态
            max_retries = 60
            for i in range(max_retries):
                result_response = Transcription.wait(task=task_id)

                if result_response.status_code != HTTPStatus.OK:
                    raise Exception(f"ASR任务查询失败: {result_response.message}")

                task_status = result_response.output["task_status"]

                if task_status == "SUCCEEDED":
                    # 获取识别结果
                    transcription_url = result_response.output["results"][0]["transcription_url"]
                    print(f"[ASR节点{node_id}] 识别完成, 下载结果...")

                    # 下载并解析结果
                    resp = requests.get(transcription_url, timeout=30)
                    resp.raise_for_status()
                    result_data = resp.json()

                    # 提取文本
                    text = result_data.get("transcripts", [{}])[0].get("text", "")

                    if not text:
                        sentences = result_data.get("transcripts", [{}])[0].get("sentences", [])
                        text = " ".join([s.get("text", "") for s in sentences])

                    print(f"[ASR节点{node_id}] 识别成功,文本长度: {len(text)} 字符")

                    # 清理OSS文件
                    self.cleanup_oss_file(object_name)

                    return text

                elif task_status in ["PENDING", "RUNNING"]:
                    if i % 10 == 0:
                        print(f"[ASR节点{node_id}] 任务状态: {task_status}, 等待中... ({i + 1}/{max_retries})")
                    time.sleep(2)
                else:
                    raise Exception(f"ASR任务状态异常: {task_status}")

            raise Exception(f"[ASR节点{node_id}] 任务超时")

        except Exception as e:
            print(f"[ASR节点{node_id}] 识别失败: {e}")
            self.cleanup_oss_file(object_name)
            raise
```

**然后修改 `speech_to_text.py` 使用新模块:**

```diff
--- a/speech_to_text.py
+++ b/speech_to_text.py
@@ -1,5 +1,7 @@
 #!/usr/bin/env python3
 # -*- coding: utf-8 -*-
+"""
+语音识别模块
+支持单节点和分布式ASR识别
+"""
+
 import sys
 import time
 import uuid
 import json
 import threading
 from pathlib import Path
 from typing import Optional, Tuple, List, Dict

 import requests
-from config import (
-    DASHSCOPE_API_KEY,
-    ASR_MODEL,
-    ASR_LANGUAGE_HINTS,
-    ASR_CUSTOM_VOCABULARY,
-    ASR_MAX_RETRIES,
-    ASR_SCORE_THRESHOLD,
-    ASR_ENABLE_LLM_POSTPROCESS,
-    ASR_LLM_POSTPROCESS_THRESHOLD,
-    ENABLE_ASR_SCORING,
-    ASR_SCORING_RESULTS_DIR,
-    ASR_ENABLE_SCORE_COLLECTION,
-    ASR_SCORE_HISTORY_FILE,
-    ASR_ENABLE_ADAPTIVE_THRESHOLD,
-    ASR_ADAPTIVE_THRESHOLD_METHOD,
-    ASR_MOVING_AVG_WINDOW,
-    ASR_PERCENTILE_THRESHOLD,
-    OSS_ENDPOINT,
-    OSS_ACCESS_KEY_ID,
-    OSS_ACCESS_KEY_SECRET,
-    OSS_BUCKET_NAME,
-    OSS_ENABLE_UUID_FILENAME,
-    OSS_AUTO_CLEANUP,
-    OSS_LIFECYCLE_DAYS,
-    ENABLE_DISTRIBUTED_ASR,
-    DISTRIBUTED_ASR_NODE_COUNT,
-    DISTRIBUTED_ASR_COEFFICIENT_THRESHOLD,
-    DISTRIBUTED_ASR_ENABLE_QUALITY_EVAL,
-)
 from common.security import (
     LLMOutputValidator,
     FileValidator,
 )
 from scores.ASR.asr_scorer import AsrScorer, AsrScore
 from common.consensus import DistributedASRConsensus
-import oss2
-import dashscope
+from asr_client import ASRClient


 class SpeechToText:
@@ -54,9 +33,7 @@ class SpeechToText:
         """初始化语音识别服务"""
         # 验证API密钥
-        if not DASHSCOPE_API_KEY:
-            raise ValueError("未配置DASHSCOPE_API_KEY")
-
-        # 设置DashScope配置
-        dashscope.api_key = DASHSCOPE_API_KEY
+        # 初始化ASR客户端
+        self.asr_client = ASRClient()

         # 初始化ASR质量评分器
         self.asr_scorer: Optional[AsrScorer] = None
```

---

### P2-2: 消除魔法数字

**新建文件:** `constants.py`

#### 文件内容:

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全局常量定义
消除代码中的魔法数字
"""

# ==================== ASR相关常量 ====================
# ASR轮询最大次数
MAX_ASR_POLLING_COUNT = 60

# ASR轮询间隔（秒）
ASR_POLLING_INTERVAL = 2

# ASR签名URL有效期（秒）
ASR_SIGNED_URL_EXPIRATION = 3600  # 1小时

# ==================== TTS相关常量 ====================
# TTS分段最大长度
TTS_MAX_SEGMENT_LENGTH = 600

# ==================== 文件大小限制 ====================
# 最大音频文件大小（字节）
MAX_AUDIO_FILE_SIZE = 100 * 1024 * 1024  # 100MB

# 最大视频文件大小（字节）
MAX_VIDEO_FILE_SIZE = 500 * 1024 * 1024  # 500MB

# ==================== 超时设置 ====================
# HTTP请求超时（秒）
HTTP_REQUEST_TIMEOUT = 30

# 文件下载超时（秒）
FILE_DOWNLOAD_TIMEOUT = 300  # 5分钟

# ==================== 并发设置 ====================
# 分布式任务最大工作线程数
MAX_CONCURRENT_WORKERS = 10
```

**然后修改相关文件导入使用:**

```diff
--- a/speech_to_text.py
+++ b/speech_to_text.py
@@ -15,6 +15,7 @@ from typing import Optional, Tuple, List, Dict

 import requests
 from config import (
+from constants import (
+    MAX_ASR_POLLING_COUNT,
+    ASR_POLLING_INTERVAL,
+    ASR_SIGNED_URL_EXPIRATION,
 )
```

---

### P2-3: 添加完整类型提示

**示例文件:** `video_downloader.py`

#### 修改内容:

```diff
--- a/video_downloader.py
+++ b/video_downloader.py
@@ -88,10 +88,15 @@ class VideoDownloader:
         # 下载并返回视频信息
         info_dict = self._ydl.extract_info(url, download=False)

-        # 检查是否是播放列表
+        # 检查是否是播放列表
         if "entries" in info_dict:
             return self._download_from_playlist(info_dict)

-        # 单个视频下载
+        # 单个视频下载
         return self._download_single_video(info_dict)

-    def _download_from_playlist(self, info_dict: dict) -> tuple[str, str | None]:
+    def _download_from_playlist(
+        self,
+        info_dict: dict[str, Any]
+    ) -> tuple[str, str | None]:
         """下载播放列表中的所有视频"""
         # ... 实现保持不变 ...
```

---

### P2-4: 统一日志管理

**新建文件:** `logger_config.py`

#### 文件内容:

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志配置模块
统一管理项目日志
"""

import logging
import sys
from pathlib import Path


def setup_logger(
    name: str = "VideoTranslate",
    level: int = logging.INFO,
    log_file: Path = None
) -> logging.Logger:
    """
    配置并返回logger实例

    Args:
        name: logger名称
        level: 日志级别
        log_file: 日志文件路径（可选）

    Returns:
        配置好的logger实例
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 清除已有的handlers
    logger.handlers.clear()

    # 日志格式
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 控制台handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件handler（如果指定）
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# 默认logger实例
logger = setup_logger()
```

**然后修改各模块使用logger:**

```diff
--- a/main.py
+++ b/main.py
@@ -1,6 +1,8 @@
+import logging
+from logger_config import logger
 import sys
 from pathlib import Path

@@ -233,7 +235,7 @@ class VideoTranslator:

         except (ValueError, SecurityError) as e:
             print(f"\n✗ 参数或安全错误: {str(e)}")
-            logging.exception("详细错误信息:")
+            logger.exception("详细错误信息:")
             raise
         except (IOError, OSError) as e:
             print(f"\n✗ 文件操作失败: {str(e)}")
-            logging.exception("详细错误信息:")
+            logger.exception("详细错误信息:")
             raise
```

---

### P2-5: 测试框架 (任务C)

**创建测试目录结构:**

```
tests/
├── __init__.py
├── conftest.py                 # pytest配置
├── test_security.py            # 安全模块测试
├── test_asr.py                 # ASR模块测试
├── test_translation.py         # 翻译模块测试
├── test_config.py              # 配置模块测试
├── integration/
│   ├── __init__.py
│   └── test_workflow.py        # 集成测试
└── fixtures/
    ├── __init__.py
    ├── sample_audio.mp3        # 测试音频
    └── sample_video.mp4        # 测试视频
```

**配置文件:** `pytest.ini`

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --tb=short
    --strict-markers
    --disable-warnings
markers =
    unit: Unit tests
    integration: Integration tests
    security: Security tests
    slow: Slow running tests
```

---

## 修复顺序建议

### 第一批 (立即执行，30分钟)
1. P0-1: API密钥管理 - config.py
2. P0-2: 敏感信息打印 - ai_services.py
3. P0-3: OSS签名URL统一 - ai_services.py

### 第二批 (本周内，1.5小时)
4. P1-1: 资源泄漏 - audio_processor.py
5. P1-2: 并发安全 - speech_to_text.py
6. P1-3: 异常处理 - main.py

### 第三批 (下周，2小时)
7. P2-1: 代码重复 - 创建asr_client.py
8. P2-2: 魔法数字 - 创建constants.py
9. P2-3: 类型提示 - 逐步添加
10. P2-4: 日志统一 - 创建logger_config.py
11. P2-5: 测试框架 - 任务C

---

## 验证清单

每个修复完成后，请验证：

- [ ] 代码运行无错误
- [ ] 功能测试通过
- [ ] 无新增lint警告
- [ ] 相关文档已更新

---

**计划生成时间:** 2026-01-02
**预计完成时间:** 2026-01-09
**下次审查:** 所有修复完成后
