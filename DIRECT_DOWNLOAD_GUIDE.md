# 视频下载功能使用说明

## 概述

系统现在支持两种视频获取方式：
1. **B站视频下载**（原功能）
2. **直链视频下载**（新增功能）

**注意**：本地上传功能已暂时禁用以提升安全性。

---

## 功能1：B站视频下载

### 支持的格式
- 完整URL: `https://www.bilibili.com/video/BVxxxxxx`
- BV号: `BVxxxxxx`
- AV号: `av123456`
- 短链: `https://b23.tv/xxxxxx`

### 使用示例
```python
from video_downloader import VideoDownloader

# 使用完整URL
video_path, bv_id = VideoDownloader.prepare_video(
    "https://www.bilibili.com/video/BV1xx411c7mD"
)

# 使用BV号
video_path, bv_id = VideoDownloader.prepare_video("BV1xx411c7mD")
```

### 错误处理
如果B站下载失败，系统会提供详细的错误信息和恢复建议：
```
B站视频下载失败: [错误详情]

建议解决方案:
1. 检查网络连接是否正常
2. 确认视频链接是否有效（尝试在浏览器中打开）
3. 如果B站视频无法下载，可以:
   - 使用其他B站视频链接
   - 将视频上传到可信存储后使用直链下载
   - 联系管理员获取其他视频来源支持
4. 技术详情: [异常类型]
```

---

## 功能2：直链视频下载

### 安全特性
直链下载功能包含多层安全保护：
- ✅ **域名白名单验证**：只允许配置的域名
- ✅ **内网地址防护**：禁止访问localhost和内网IP
- ✅ **文件大小限制**：默认最大500MB
- ✅ **超时控制**：默认300秒超时
- ✅ **流式下载**：实时监控文件大小
- ✅ **URL复用机制**：已下载的文件自动复用

### 配置方法

在 `config.py` 中配置域名白名单：

```python
# 直链下载配置
# 允许直链下载的域名白名单（安全控制）
DIRECT_DOWNLOAD_ALLOWED_DOMAINS = [
    # 示例可信域名（请根据实际需求修改）
    "your-cdn.com",
    "your-storage.s3.amazonaws.com",
    "your-oss.oss-cn-hangzhou.aliyuncs.com",
]

# 直链下载文件大小限制（字节）
DIRECT_DOWNLOAD_MAX_SIZE = 500 * 1024 * 1024  # 默认500MB

# 直链下载超时时间（秒）
DIRECT_DOWNLOAD_TIMEOUT = 300  # 默认5分钟
```

### 使用示例

```python
from video_downloader import VideoDownloader

# 直链下载
video_path, _ = VideoDownloader.prepare_video(
    "https://your-cdn.com/videos/sample.mp4"
)
```

### URL检测逻辑
系统会自动识别以下类型的直链：
1. URL包含视频文件扩展名（.mp4, .avi, .mov, .mkv等）
2. URL包含配置的白名单域名

### 错误处理

**域名未在白名单中**：
```
直链URL安全验证失败: URL域名不在白名单中: https://example.com/video.mp4
允许的域名: your-cdn.com, your-storage.com
如需添加新域名，请联系管理员
```

**文件过大**：
```
文件过大: 600.00MB (限制: 500MB)
```

**下载失败**：
```
直链视频下载失败: [错误详情]

建议解决方案:
1. 检查URL是否有效（尝试在浏览器中打开）
2. 确认URL域名在白名单中
3. 检查网络连接是否正常
4. 联系管理员添加新的域名到白名单
5. 技术详情: [异常类型]
```

---

## 使用建议

### 当B站下载失效时的解决方案

1. **尝试其他B站链接**
   - 有时特定视频下载失败，换个视频可能成功

2. **使用直链下载（推荐）**
   - 将视频上传到已配置的可信存储
   - 获取直链URL后使用
   - 需要管理员先配置域名白名单

3. **联系管理员**
   - 报告无法下载的B站链接
   - 请求添加新的可信域名到白名单
   - 获取其他视频来源支持

### 域名白名单配置建议

**推荐的存储服务**：
- 阿里云OSS: `your-bucket.oss-cn-hangzhou.aliyuncs.com`
- AWS S3: `your-bucket.s3.amazonaws.com`
- 腾讯云COS: `your-bucket.cos.ap-guangzhou.myqcloud.com`
- 自建CDN: `your-cdn.com`

**安全性考虑**：
- 只添加你信任的域名
- 定期审查白名单列表
- 避免添加过于泛泛的域名（如 `*.com`）
- 优先使用HTTPS协议

---

## 测试

运行测试脚本验证功能：

```bash
python test_direct_download.py
```

测试脚本会检查：
- URL检测逻辑（B站URL vs 直链URL）
- 错误消息显示
- 当前配置状态

---

## 技术细节

### 文件命名规则
- B站视频: `{BV号}.mp4`
- 直链视频: `direct_{URL哈希值}.mp4`

### 文件存储位置
所有下载的视频都保存在 `temp/` 目录下。

### 复用机制
系统会检查已下载的文件，避免重复下载：
- B站：根据BV号判断
- 直链：根据URL的MD5哈希值判断

---

## 常见问题

### Q: 为什么直链下载不工作？
A: 检查 `config.py` 中的 `DIRECT_DOWNLOAD_ALLOWED_DOMAINS` 是否配置了域名。如果为空列表，直链下载功能不会启用。

### Q: 如何添加新的可信域名？
A: 编辑 `config.py`，在 `DIRECT_DOWNLOAD_ALLOWED_DOMAINS` 列表中添加新域名，然后重启系统。

### Q: 文件大小限制可以调整吗？
A: 可以。在 `config.py` 中修改 `DIRECT_DOWNLOAD_MAX_SIZE` 的值（单位：字节）。

### Q: 本地上传功能什么时候恢复？
A: 本地上传功能暂时禁用以提升安全性。如需恢复，需要实现更严格的文件验证机制（病毒扫描、文件指纹验证等）。

---

## 安全说明

直链下载功能实现了以下安全措施：

1. **SSRF防护**
   - 域名白名单验证
   - 禁止访问内网地址（localhost, 127.0.0.1, 192.168.x.x等）
   - URL格式验证

2. **资源限制**
   - 文件大小限制
   - 下载超时控制
   - 实时流量监控

3. **错误处理**
   - 清理部分下载的文件
   - 详细的错误日志
   - 友好的用户提示

4. **代码位置**
   - URL验证: `common/security/validators.py:399-462`
   - 下载实现: `video_downloader.py:235-341`
