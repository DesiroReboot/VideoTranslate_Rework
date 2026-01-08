"""
视频下载模块
支持B站视频URL下载、直链下载和本地文件处理
"""

import os
import sys
import re
import hashlib
from pathlib import Path
from typing import Optional, Tuple
import yt_dlp
import requests

from config import (
    YT_DLP_OPTIONS,
    TEMP_DIR,
    DIRECT_DOWNLOAD_ALLOWED_DOMAINS,
    DIRECT_DOWNLOAD_MAX_SIZE,
    DIRECT_DOWNLOAD_TIMEOUT,
)
from bv_utils import normalize_bilibili_url
from common.security import (
    PathSecurityValidator,
    URLValidator,
    FileValidator,
    SecurityError,
)


class VideoDownloader:
    """视频下载器，支持B站URL和本地文件"""

    # B站URL正则表达式
    BILIBILI_PATTERNS = [
        r"https?://(?:www\.)?bilibili\.com/video/[Bb][Vv][\w]+",
        r"https?://(?:www\.)?bilibili\.com/video/av[\d]+",
        r"https?://b23\.tv/[\w]+",
        r"^[Bb][Vv][\w]+$",  # 纯BV号格式
    ]

    @staticmethod
    def is_bilibili_url(url: str) -> bool:
        """
        检查是否为B站视频URL

        Args:
            url: 待检查的URL字符串

        Returns:
            是否为B站URL
        """
        for pattern in VideoDownloader.BILIBILI_PATTERNS:
            if re.match(pattern, url):
                return True
        return False

    @staticmethod
    def is_direct_download_url(url: str) -> bool:
        """
        检查是否为直链下载URL

        Args:
            url: 待检查的URL字符串

        Returns:
            是否为直链URL
        """
        if not url or not isinstance(url, str):
            return False

        # 必须是http/https开头
        if not url.startswith(("http://", "https://")):
            return False

        # 排除B站URL（B站URL由download_bilibili_video处理）
        if VideoDownloader.is_bilibili_url(url):
            return False

        # 检查URL是否包含常见的视频文件扩展名
        video_extensions = [
            ".mp4", ".avi", ".mov", ".mkv", ".flv",
            ".wmv", ".webm", ".m4v", ".mp3", ".wav"
        ]
        url_lower = url.lower()
        for ext in video_extensions:
            if ext in url_lower:
                return True

        # 如果配置了域名白名单，检查是否包含白名单域名
        if DIRECT_DOWNLOAD_ALLOWED_DOMAINS:
            for domain in DIRECT_DOWNLOAD_ALLOWED_DOMAINS:
                if domain in url:
                    return True

        return False

    @staticmethod
    def is_local_file(path: str) -> bool:
        """
        检查是否为本地视频文件

        Args:
            path: 文件路径

        Returns:
            是否为有效的本地视频文件
        """
        if not path or not isinstance(path, str):
            return False

        try:
            # 路径安全验证
            project_root = PathSecurityValidator.get_project_root()
            PathSecurityValidator.validate_path_in_project(path, project_root)

            # 文件安全验证
            FileValidator.validate_video_file(path)

            # 符号链接安全检查
            p = Path(path)
            if p.is_symlink():
                target = p.resolve()
                if not str(target).startswith(str(Path.cwd())):
                    raise SecurityError("符号链接指向项目目录外部")

            # 文件权限检查
            if not os.access(path, os.R_OK):
                raise SecurityError("文件不可读")

            return True

        except (SecurityError, ValueError, OSError):
            return False

    @staticmethod
    def download_bilibili_video(
        url: str, output_path: Optional[str] = None
    ) -> Tuple[str, Optional[str]]:
        """
        从B站下载视频

        Args:
            url: B站视频URL
            output_path: 可选的输出路径，不指定则使用BV号命名

        Returns:
            (下载后的视频文件路径, BV号) 的元组

        Raises:
            ValueError: URL无效或下载失败
            SecurityError: 安全检查失败
        """
        # 1. URL参数验证
        if not url or not isinstance(url, str):
            raise ValueError("URL参数无效")

        # 2. URL安全验证
        if not URLValidator.validate_url_domain(url):
            raise SecurityError(f"URL域名不在白名单中: {url}")

        if not VideoDownloader.is_bilibili_url(url):
            raise ValueError(f"无效的B站URL: {url}")

        # 3. 提取BV号并规范化URL
        bv_id, normalized_url = normalize_bilibili_url(url)
        if bv_id and normalized_url:
            print(f"识别BV号: {bv_id}")
            url = normalized_url
        elif bv_id:
            print(f"识别BV号: {bv_id}")
            url = f"https://www.bilibili.com/video/{bv_id}"

        # 4. 检查是否已存在该BV号的视频（复用机制）
        if bv_id:
            existing_file = TEMP_DIR / f"{bv_id}.mp4"
            if existing_file.exists():
                print(f"✓ 检测到已下载的视频，直接复用: {existing_file}")
                return str(existing_file), bv_id

        # 5. 输出路径安全验证
        if output_path:
            project_root = PathSecurityValidator.get_project_root()
            PathSecurityValidator.validate_path_in_project(output_path, project_root)
            output_dir = Path(output_path).parent
            output_dir.mkdir(parents=True, exist_ok=True)

        print(f"开始下载B站视频: {url}")

        # 6. 配置下载选项
        ydl_opts = YT_DLP_OPTIONS.copy()

        # 简化但稳定的配置
        ydl_opts.update({
            "quiet": False,  # 显示进度
            "no_warnings": False,  # 显示警告
            "progress": True,  # 显示下载进度
        })

        if output_path:
            ydl_opts["outtmpl"] = str(output_path)
        elif bv_id:
            ydl_opts["outtmpl"] = str(TEMP_DIR / f"{bv_id}.%(ext)s")

        # 7. 下载视频
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore
                info = ydl.extract_info(url, download=True)

                # 获取实际下载的文件路径
                if "requested_downloads" in info and info["requested_downloads"]:
                    downloaded_file = info["requested_downloads"][0]["filepath"]
                else:
                    # 备用方案：根据BV号或标题构建文件路径
                    ext = info.get("ext", "mp4")
                    if bv_id:
                        downloaded_file = str(TEMP_DIR / f"{bv_id}.{ext}")
                    else:
                        title = info.get("title", "video")
                        downloaded_file = str(TEMP_DIR / f"{title}.{ext}")

                print(f"✓ 视频下载完成: {downloaded_file}")
                return downloaded_file, bv_id

        except Exception as e:
            error_msg = f"B站视频下载失败: {str(e)}\n\n"
            error_msg += "建议解决方案:\n"
            error_msg += "1. 检查网络连接是否正常\n"
            error_msg += "2. 确认视频链接是否有效（尝试在浏览器中打开）\n"
            error_msg += "3. 如果B站视频无法下载，可以:\n"
            error_msg += "   - 使用其他B站视频链接\n"
            error_msg += "   - 将视频上传到可信存储后使用直链下载\n"
            error_msg += "   - 联系管理员获取其他视频来源支持\n"
            error_msg += f"4. 技术详情: {type(e).__name__}"
            raise ValueError(error_msg)

    @staticmethod
    def download_direct_url(url: str) -> Tuple[str, None]:
        """
        从直链URL下载视频

        Args:
            url: 直链URL

        Returns:
            (下载后的视频文件路径, None) 的元组

        Raises:
            ValueError: URL无效或下载失败
            SecurityError: 安全检查失败
        """
        # 1. URL参数验证
        if not url or not isinstance(url, str):
            raise ValueError("URL参数无效")

        # 2. URL安全验证
        try:
            validated_url = URLValidator.validate_direct_download_url(
                url, DIRECT_DOWNLOAD_ALLOWED_DOMAINS
            )
        except SecurityError as e:
            raise ValueError(f"直链URL安全验证失败: {str(e)}")

        print(f"开始下载直链视频: {validated_url}")

        # 3. 生成文件名（使用URL的哈希值）
        url_hash = hashlib.md5(validated_url.encode()).hexdigest()[:12]
        filename = f"direct_{url_hash}.mp4"
        output_path = TEMP_DIR / filename

        # 4. 检查是否已存在（复用机制）
        if output_path.exists():
            file_size = output_path.stat().st_size
            if file_size > 0:
                print(f"✓ 检测到已下载的视频，直接复用: {output_path}")
                return str(output_path), None

        # 5. 下载文件
        try:
            # 流式下载，支持大文件
            response = requests.get(
                validated_url,
                stream=True,
                timeout=DIRECT_DOWNLOAD_TIMEOUT,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    )
                }
            )

            # 检查响应状态
            response.raise_for_status()

            # 获取文件大小
            content_length = response.headers.get("content-length")
            if content_length:
                content_length = int(content_length)
                if content_length > DIRECT_DOWNLOAD_MAX_SIZE:
                    raise ValueError(
                        f"文件过大: {content_length / 1024 / 1024:.2f}MB "
                        f"(限制: {DIRECT_DOWNLOAD_MAX_SIZE / 1024 / 1024:.0f}MB)"
                    )

            # 写入文件
            downloaded_size = 0
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)

                        # 实时检查文件大小
                        if downloaded_size > DIRECT_DOWNLOAD_MAX_SIZE:
                            output_path.unlink()  # 删除已下载的部分文件
                            raise ValueError(
                                f"下载过程中文件超过大小限制: "
                                f"{downloaded_size / 1024 / 1024:.2f}MB"
                            )

            print(f"✓ 直链视频下载完成: {output_path} ({downloaded_size / 1024 / 1024:.2f}MB)")
            return str(output_path), None

        except requests.exceptions.RequestException as e:
            # 清理可能的部分下载文件
            if output_path.exists():
                output_path.unlink()

            error_msg = f"直链视频下载失败: {str(e)}\n\n"
            error_msg += "建议解决方案:\n"
            error_msg += "1. 检查URL是否有效（尝试在浏览器中打开）\n"
            error_msg += "2. 确认URL域名在白名单中\n"
            error_msg += "3. 检查网络连接是否正常\n"
            error_msg += "4. 联系管理员添加新的域名到白名单\n"
            error_msg += f"5. 技术详情: {type(e).__name__}"
            raise ValueError(error_msg)

        except Exception as e:
            # 清理可能的部分下载文件
            if output_path.exists():
                output_path.unlink()
            raise ValueError(f"下载直链视频时发生错误: {str(e)}")


    @staticmethod
    def prepare_video(url_or_path: str) -> Tuple[str, Optional[str]]:
        """
        准备视频文件（支持B站URL和直链下载）

        Args:
            url_or_path: B站URL、BV号或直链URL

        Returns:
            (可用的视频文件路径, BV号) 的元组，直链下载BV号为None

        Raises:
            ValueError: 输入无效
        """
        # 1. 判断是否为B站URL
        if VideoDownloader.is_bilibili_url(url_or_path):
            # 检查是否为纯BV号，如果是则转换为完整URL
            if re.match(r"^[Bb][Vv][\w]+$", url_or_path):
                full_url = f"https://www.bilibili.com/video/{url_or_path}"
                print(f"检测到纯BV号，转换为完整URL: {full_url}")
                return VideoDownloader.download_bilibili_video(full_url)
            else:
                return VideoDownloader.download_bilibili_video(url_or_path)

        # 2. 判断是否为直链URL
        elif VideoDownloader.is_direct_download_url(url_or_path):
            print(f"检测到直链URL，开始下载...")
            return VideoDownloader.download_direct_url(url_or_path)

        # 3. 无效输入
        else:
            error_msg = f"无效的输入: {url_or_path}\n\n"
            error_msg += "支持的输入格式:\n\n"

            error_msg += "1. B站视频URL:\n"
            error_msg += "   - 完整URL: https://www.bilibili.com/video/BVxxxxxx\n"
            error_msg += "   - BV号: BVxxxxxx\n"
            error_msg += "   - AV号: av123456\n"
            error_msg += "   - 短链: https://b23.tv/xxxxxx\n\n"

            if DIRECT_DOWNLOAD_ALLOWED_DOMAINS:
                error_msg += "2. 直链下载URL:\n"
                error_msg += f"   - 可信域名: {', '.join(DIRECT_DOWNLOAD_ALLOWED_DOMAINS)}\n"
                error_msg += f"   - 文件大小限制: {DIRECT_DOWNLOAD_MAX_SIZE / 1024 / 1024:.0f}MB\n\n"
            else:
                error_msg += "2. 直链下载: 当前未配置可信域名白名单\n"
                error_msg += "   如需使用直链下载，请联系管理员配置\n\n"

            error_msg += "注意: 本地上传功能已暂时禁用"
            raise ValueError(error_msg)


# 测试代码
if __name__ == "__main__":
    # 测试URL验证
    test_urls = [
        "https://www.bilibili.com/video/BV1xx411c7mD",
        "BV1rbvZBHEbx",
    ]

    for url in test_urls:
        print(f"\n测试: {url}")
        print(f"是B站URL: {VideoDownloader.is_bilibili_url(url)}")
        print(f"是本地文件: {VideoDownloader.is_local_file(url)}")
