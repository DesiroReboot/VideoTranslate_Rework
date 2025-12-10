"""
视频下载模块
支持B站视频URL下载和本地文件处理
"""

import re
from pathlib import Path
from typing import Optional
import yt_dlp
from config import YT_DLP_OPTIONS, TEMP_DIR


class VideoDownloader:
    """视频下载器,支持B站URL和本地文件"""
    
    # B站URL正则表达式
    BILIBILI_PATTERNS = [
        r'https?://(?:www\.)?bilibili\.com/video/[Bb][Vv][\w]+',
        r'https?://(?:www\.)?bilibili\.com/video/av[\d]+',
        r'https?://b23\.tv/[\w]+',
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
        检查是否为本地文件路径
        
        Args:
            path: 文件路径
            
        Returns:
            是否为有效的本地MP4文件
        """
        p = Path(path)
        return p.exists() and p.is_file() and p.suffix.lower() in ['.mp4', '.avi', '.mov', '.mkv']
    
    @staticmethod
    def download_bilibili_video(url: str, output_path: Optional[str] = None) -> str:
        """
        从B站下载视频
        
        Args:
            url: B站视频URL
            output_path: 可选的输出路径,不指定则使用默认临时目录
            
        Returns:
            下载后的视频文件路径
            
        Raises:
            ValueError: URL无效或下载失败
        """
        if not VideoDownloader.is_bilibili_url(url):
            raise ValueError(f"无效的B站URL: {url}")
        
        print(f"开始下载B站视频: {url}")
        
        # 配置下载选项
        ydl_opts = YT_DLP_OPTIONS.copy()
        if output_path:
            ydl_opts['outtmpl'] = str(output_path)
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # 获取视频信息
                info = ydl.extract_info(url, download=True)
                
                # 获取实际下载的文件路径
                if 'requested_downloads' in info and info['requested_downloads']:
                    downloaded_file = info['requested_downloads'][0]['filepath']
                else:
                    # 备用方案:根据模板构建文件路径
                    title = info.get('title', 'video')
                    ext = info.get('ext', 'mp4')
                    downloaded_file = str(TEMP_DIR / f"{title}.{ext}")
                
                print(f"视频下载完成: {downloaded_file}")
                return downloaded_file
                
        except Exception as e:
            raise ValueError(f"下载B站视频失败: {str(e)}")
    
    @staticmethod
    def prepare_video(url_or_path: str) -> str:
        """
        准备视频文件(下载或验证本地文件)
        
        Args:
            url_or_path: B站URL或本地文件路径
            
        Returns:
            可用的视频文件路径
            
        Raises:
            ValueError: 输入无效
        """
        # 判断是URL还是本地文件
        if VideoDownloader.is_bilibili_url(url_or_path):
            # 下载B站视频
            return VideoDownloader.download_bilibili_video(url_or_path)
        
        elif VideoDownloader.is_local_file(url_or_path):
            # 本地文件,直接返回
            print(f"使用本地视频文件: {url_or_path}")
            return str(Path(url_or_path).absolute())
        
        else:
            raise ValueError(
                f"无效的输入: {url_or_path}\n"
                "请提供:\n"
                "1. B站视频URL (如: https://www.bilibili.com/video/BVxxxxxxxxx)\n"
                "2. 本地视频文件路径 (支持格式: .mp4, .avi, .mov, .mkv)"
            )


# 测试代码
if __name__ == "__main__":
    # 测试URL验证
    test_urls = [
        "https://www.bilibili.com/video/BV1xx411c7mD",
        "https://b23.tv/abc123",
        "https://www.youtube.com/watch?v=xxx",  # 非B站URL
        "test.mp4",  # 本地文件
    ]
    
    for url in test_urls:
        print(f"\n测试: {url}")
        print(f"是B站URL: {VideoDownloader.is_bilibili_url(url)}")
        print(f"是本地文件: {VideoDownloader.is_local_file(url)}")
