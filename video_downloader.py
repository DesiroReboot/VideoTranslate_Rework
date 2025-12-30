"""
视频下载模块
支持B站视频URL下载和本地文件处理
"""

import os
import re
from pathlib import Path
from typing import Optional, Tuple
import yt_dlp
from config import YT_DLP_OPTIONS, TEMP_DIR
from bv_utils import normalize_bilibili_url, extract_bv_from_url
from security import PathSecurityValidator, URLValidator, FileValidator, SecurityError


class VideoDownloader:
    """视频下载器,支持B站URL和本地文件"""
    
    # B站URL正则表达式
    BILIBILI_PATTERNS = [
        r'https?://(?:www\.)?bilibili\.com/video/[Bb][Vv][\w]+',
        r'https?://(?:www\.)?bilibili\.com/video/av[\d]+',
        r'https?://b23\.tv/[\w]+',
        r'^[Bb][Vv][\w]+$',  # 纯BV号格式
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
    def is_local_file(path: str) -> bool:
        """
        检查是否为本地视频文件
        
        Args:
            path: 文件路径
            
        Returns:
            是否为有效的本地视频文件
            
        Raises:
            SecurityError: 安全检查失败
        """
        # 1. 基础参数验证
        if not path or not isinstance(path, str):
            return False
        
        try:
            # 2. 路径安全验证
            project_root = os.getcwd()
            PathSecurityValidator.validate_path_in_project(path, project_root)
            
            # 3. 文件安全验证
            file_info = FileValidator.validate_video_file(path)
            
            # 4. 符号链接安全检查
            p = Path(path)
            if p.is_symlink():
                # 检查符号链接目标是否在项目范围内
                target = p.resolve()
                if not str(target).startswith(str(Path.cwd())):
                    raise SecurityError("符号链接指向项目目录外部")
            
            # 5. 文件权限检查
            if not os.access(path, os.R_OK):
                raise SecurityError("文件不可读")
            
            return True
            
        except (SecurityError, ValueError, OSError):
            return False
    
    @staticmethod
    def download_bilibili_video(url: str, output_path: Optional[str] = None) -> Tuple[str, Optional[str]]:
        """
        从B站下载视频
        
        Args:
            url: B站视频URL
            output_path: 可选的输出路径,不指定则使用BV号命名
            
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
        
        # 3. 输出路径安全验证
        if output_path:
            project_root = os.getcwd()
            PathSecurityValidator.validate_path_in_project(output_path, project_root)
            # 确保输出目录存在
            output_dir = Path(output_path).parent
            output_dir.mkdir(parents=True, exist_ok=True)
        
        # 提取BV号
        bv_id, normalized_url = normalize_bilibili_url(url)
        if bv_id:
            print(f"识别BV号: {bv_id}")
            url = normalized_url  # 使用规范化的URL
        
        # 检查是否已存在该BV号的视频（复用机制）
        if bv_id:
            existing_file = TEMP_DIR / f"{bv_id}.mp4"
            if existing_file.exists():
                print(f"✓ 检测到已下载的视频，直接复用: {existing_file}")
                return str(existing_file), bv_id
        
        print(f"开始下载B站视频: {url}")
        
        # 配置下载选项
        ydl_opts = YT_DLP_OPTIONS.copy()
        if output_path:
            ydl_opts['outtmpl'] = str(output_path)
        elif bv_id:
            # 使用BV号命名
            ydl_opts['outtmpl'] = str(TEMP_DIR / f"{bv_id}.%(ext)s")
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # 获取视频信息
                info = ydl.extract_info(url, download=True)
                
                # 获取实际下载的文件路径
                if 'requested_downloads' in info and info['requested_downloads']:
                    downloaded_file = info['requested_downloads'][0]['filepath']
                else:
                    # 备用方案:根据BV号或标题构建文件路径
                    ext = info.get('ext', 'mp4')
                    if bv_id:
                        downloaded_file = str(TEMP_DIR / f"{bv_id}.{ext}")
                    else:
                        title = info.get('title', 'video')
                        downloaded_file = str(TEMP_DIR / f"{title}.{ext}")
                
                print(f"视频下载完成: {downloaded_file}")
                return downloaded_file, bv_id
                
        except Exception as e:
            raise ValueError(f"下载B站视频失败: {str(e)}")
    
    @staticmethod
    def prepare_video(url_or_path: str) -> Tuple[str, Optional[str]]:
        """
        准备视频文件(下载或验证本地文件)
        
        Args:
            url_or_path: B站URL或本地文件路径
            
        Returns:
            (可用的视频文件路径, BV号) 的元组，本地文件BV号为None
            
        Raises:
            ValueError: 输入无效
        """
        # 判断是URL还是本地文件
        if VideoDownloader.is_bilibili_url(url_or_path):
            # 检查是否为纯BV号，如果是则转换为完整URL
            if re.match(r'^[Bb][Vv][\w]+$', url_or_path):
                full_url = f"https://www.bilibili.com/video/{url_or_path}"
                print(f"检测到纯BV号，转换为完整URL: {full_url}")
                return VideoDownloader.download_bilibili_video(full_url)
            else:
                # 下载B站视频
                return VideoDownloader.download_bilibili_video(url_or_path)
        
        elif VideoDownloader.is_local_file(url_or_path):
            # 本地文件,直接返回
            print(f"使用本地视频文件: {url_or_path}")
            return str(Path(url_or_path).absolute()), None
        
        else:
            raise ValueError(
                f"无效的输入: {url_or_path}\n"
                "请提供:\n"
                "1. B站视频URL (支持BV号、AV号、b23.tv短链)\n"
                "2. 本地视频文件路径 (支持格式: .mp4, .avi, .mov, .mkv)"
            )


# 测试代码
if __name__ == "__main__":
    # 测试URL验证
    test_urls = [
        "https://www.bilibili.com/video/BV1xx411c7mD",
#"https://b23.tv/abc123",
        #"https://www.youtube.com/watch?v=xxx",  # 非B站URL
        #"test.mp4",  # 本地文件
    ]
    
    for url in test_urls:
        print(f"\n测试: {url}")
        print(f"是B站URL: {VideoDownloader.is_bilibili_url(url)}")
        print(f"是本地文件: {VideoDownloader.is_local_file(url)}")
