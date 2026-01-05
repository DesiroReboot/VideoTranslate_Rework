具体操作步骤：

  第1步：手动下载B站视频

  可以使用以下工具：
  - 浏览器插件：B站视频下载助手
  - IDM (Internet Download Manager)
  - you-get / yt-dlp命令行
  - 在线B站视频下载网站

  例如使用 yt-dlp 手动下载：
  yt-dlp -o video.mp4 https://www.bilibili.com/video/BV1xx411c7mD

  第2步：上传到云存储

  选择云存储服务（推荐方案）：

  选项1：阿里云OSS（推荐，你已经在使用）

  # 使用阿里云CLI上传
  ossutil cp video.mp4 oss://your-bucket/videos/video.mp4

  # 或者使用osscmd
  python osscmd put video.mp4 oss://your-bucket/videos/video.mp4

  设置文件为公共读（重要！否则无法直链访问）：
  - 在阿里云控制台，找到上传的文件
  - 设置权限为"公共读"
  - 或者配置Bucket为"公共读"（不推荐，有安全风险）

  获取直链URL：
  https://your-bucket.oss-cn-hangzhou.aliyuncs.com/videos/video.mp4

  选项2：腾讯云COS

  # 使用COSCLI上传
  coscli cp video.mp3 cos://your-bucket-1234567890/videos/video.mp4

  选项3：AWS S3

  # 使用AWS CLI上传
  aws s3 cp video.mp4 s3://your-bucket/videos/video.mp4

  # 设置为公共读
  aws s3api put-object-acl --bucket your-bucket --key videos/video.mp4 --acl public-read

  获取直链URL：
  https://your-bucket.s3.amazonaws.com/videos/video.mp4

  选项4：自建文件服务器

  如果你有自己的服务器或NAS：
  # 使用scp上传到服务器
  scp video.mp4 user@your-server.com:/var/www/html/videos/

  # 访问URL: https://your-server.com/videos/video.mp4

  第3步：配置域名白名单

  在 config.py 中添加你的云存储域名：

  # 直链下载配置
  # 允许直链下载的域名白名单（安全控制）
  DIRECT_DOWNLOAD_ALLOWED_DOMAINS = [
      # 添加你的云存储域名

      # 阿里云OSS示例
      "your-bucket.oss-cn-hangzhou.aliyuncs.com",

      # 腾讯云COS示例
      "your-bucket-1234567890.cos.ap-guangzhou.myqcloud.com",

      # AWS S3示例
      "your-bucket.s3.amazonaws.com",

      # 自建服务器示例
      "your-server.com",
      "cdn.your-server.com",
  ]

  # 直链下载文件大小限制（字节）
  DIRECT_DOWNLOAD_MAX_SIZE = 500 * 1024 * 1024  # 默认500MB

  # 直链下载超时时间（秒）
  DIRECT_DOWNLOAD_TIMEOUT = 300  # 默认5分钟

  第4步：使用直链URL进行翻译

  from video_downloader import VideoDownloader

  # 使用直链URL
  video_path, _ = VideoDownloader.prepare_video(
      "https://your-bucket.oss-cn-hangzhou.aliyuncs.com/videos/video.mp4"
  )

  # 继续后续的翻译流程...

  ---
  如何配置可信CDN的详细示例

  示例1：配置阿里云OSS直链

  步骤1：创建Bucket
  - 登录阿里云OSS控制台
  - 创建Bucket，选择"公共读"或"私有"
  - 记录Bucket名称和地域

  步骤2：获取域名
  标准格式: {bucket-name}.{region}.aliyuncs.com
  示例: my-videos.oss-cn-hangzhou.aliyuncs.com

  步骤3：配置白名单
  DIRECT_DOWNLOAD_ALLOWED_DOMAINS = [
      "my-videos.oss-cn-hangzhou.aliyuncs.com",
  ]

  步骤4：上传文件并设置权限
  import oss2

  # 配置认证信息
  auth = oss2.Auth('your-access-key-id', 'your-access-key-secret')
  bucket = oss2.Bucket(auth, 'https://oss-cn-hangzhou.aliyuncs.com', 'my-videos')

  # 上传文件
  bucket.put_object_from_file('videos/video.mp4', 'video.mp4')

  # 设置为公共读（重要！）
  bucket.put_object_acl('videos/video.mp4', oss2.OBJECT_ACL_PUBLIC_READ)

  步骤5：生成直链URL
  https://my-videos.oss-cn-hangzhou.aliyuncs.com/videos/video.mp4

  示例2：配置CDN加速（可选）

  如果你希望加速下载，可以配置CDN：

  阿里云CDN配置：
  1. 在CDN控制台添加加速域名
  2. 源站设置为你的OSS域名
  3. 配置CNAME

  # 配置CDN域名
  DIRECT_DOWNLOAD_ALLOWED_DOMAINS = [
      "my-videos.oss-cn-hangzhou.aliyuncs.com",  # OSS源站
      "cdn.my-videos.com",  # CDN加速域名
  ]

  使用时：
  # 使用CDN加速的直链（更快）
  video_path, _ = VideoDownloader.prepare_video(
      "https://cdn.my-videos.com/videos/video.mp4"
  )

  ---
  安全注意事项

  ⚠️ 安全风险

  1. 公共读权限：文件设置为公共读后，任何人都可以访问
  2. 费用问题：云存储和CDN会产生流量费用
  3. 带宽限制：注意云存储的带宽限制

  🔒 安全最佳实践

  方案1：使用临时签名URL（推荐）
  import oss2
  from datetime import datetime, timedelta

  # 生成临时签名URL（1小时有效）
  auth = oss2.Auth('your-access-key-id', 'your-access-key-secret')
  bucket = oss2.Bucket(auth, 'https://oss-cn-hangzhou.aliyuncs.com', 'my-videos')

  # 生成签名URL（1小时后过期）
  url = bucket.sign_url('GET', 'videos/video.mp4', 3600)
  # 示例: https://my-videos.oss-cn-hangzhou.aliyuncs.com/videos/video.mp4?Expires=xxx&OSSAccessKeyId=    
  xxx&Signature=xxx

  但是这种方式需要修改代码支持签名URL，暂时比较复杂。

  方案2：IP白名单
  在OSS Bucket设置中配置IP白名单，只允许你的服务器IP访问。

  方案3：定期清理
  设置Bucket生命周期规则，自动删除过期文件：
  # 在OSS控制台配置
  # 规则: 上传1天后自动删除

  ---
  成本估算

  以阿里云OSS为例：
  - 存储费用：约 ¥0.12/GB/月
  - 下行流量：约 ¥0.50/GB（外网）
  - 请求费用：¥0.01/万次

  示例：100个视频，每个500MB
  - 存储：50GB × ¥0.12 = ¥6/月
  - 流量：假设每个下载1次 = 50GB × ¥0.50 = ¥25

  ---
  推荐方案总结

  如果你是个人用户：

  1. 使用阿里云OSS（因为你已经有阿里云账号）
  2. 创建一个专门的Bucket用于视频文件
  3. 配置为"公共读"
  4. 在 config.py 中添加OSS域名
  5. 手动上传B站下载的视频文件
  6. 使用OSS直链URL进行翻译

  如果你是团队/企业用户：

  1. 配置CDN加速（提升下载速度）
  2. 使用临时签名URL（提升安全性）
  3. 设置访问日志（监控使用情况）
  4. 配置生命周期规则（自动清理）