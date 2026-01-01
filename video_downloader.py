"""
视频下载模块
支持B站视频URL下载和本地文件处理
"""

import os
import re
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import yt_dlp
from config import YT_DLP_OPTIONS, TEMP_DIR, OUTPUT_DIR, BILIBILI_COOKIE_FILE
from bv_utils import normalize_bilibili_url, extract_bv_from_url, download_bilibili_via_api
from common.security import PathSecurityValidator, URLValidator, FileValidator, SecurityError


class BilibiliDebugLogger:
    """B站调试日志记录器，用于捕获yt-dlp原始响应"""
    
    def __init__(self, bv_id: Optional[str] = None):
        self.bv_id = bv_id or "unknown"
        self.log_dir = OUTPUT_DIR / "debug_logs"
        self.log_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"{self.bv_id}_{timestamp}.log"
        
        # 设置logging
        self.logger = logging.getLogger(f"bilibili_debug_{bv_id}")
        self.logger.setLevel(logging.DEBUG)
        
        # 移除现有处理器
        self.logger.handlers.clear()
        
        # 文件处理器
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        # 控制台处理器（仅显示WARNING及以上）
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        self.logger.info(f"B站调试日志初始化完成 - BV: {self.bv_id}")
    
    def debug(self, msg: str):
        self.logger.debug(msg)
    
    def info(self, msg: str):
        self.logger.info(msg)
    
    def warning(self, msg: str):
        self.logger.warning(msg)
    
    def error(self, msg: str):
        self.logger.error(msg)
    
    def save_raw_response(self, url: str, response_text: str, error: Exception = None):
        """保存原始响应数据"""
        raw_data = {
            "timestamp": datetime.now().isoformat(),
            "bv_id": self.bv_id,
            "url": url,
            "response_preview": response_text[:1000] if response_text else "空响应",
            "response_length": len(response_text) if response_text else 0,
            "error": str(error) if error else None,
            "error_type": error.__class__.__name__ if error else None
        }
        
        raw_file = self.log_dir / f"{self.bv_id}_raw_response.json"
        try:
            with open(raw_file, 'w', encoding='utf-8') as f:
                json.dump(raw_data, f, ensure_ascii=False, indent=2)
            self.logger.info(f"原始响应已保存到: {raw_file}")
        except Exception as e:
            self.logger.error(f"保存原始响应失败: {e}")
    
    def log_yt_dlp_debug(self, msg: Dict[str, Any]):
        """记录yt-dlp调试信息"""
        if isinstance(msg, dict) and msg.get('url') and msg.get('downloader'):
            self.logger.debug(f"yt-dlp下载器: {msg.get('downloader')} - URL: {msg.get('url')}")
        
        # 如果消息包含响应信息，尝试提取
        if isinstance(msg, dict) and 'response' in msg:
            response = msg['response']
            if isinstance(response, dict) and 'text' in response:
                self.save_raw_response(
                    msg.get('url', 'unknown'),
                    response['text'][:5000] if response['text'] else "空响应",
                    None
                )


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
        
        # 初始化调试日志记录器
        debug_logger = BilibiliDebugLogger(bv_id)
        debug_logger.info(f"开始下载B站视频: {url}")
        debug_logger.info(f"BV号: {bv_id or '未知'}")
        
        # 配置下载选项（基于YT_DLP_OPTIONS并增强调试选项）
        ydl_opts = YT_DLP_OPTIONS.copy()
        
        # 增强调试选项
        ydl_opts.update({
            'verbose': True,  # 启用详细输出
            'dump_intermediate_pages': False,  # 不再转储中间页面
            'write_pages': False,  # 不再写入页面到文件
            'load_pages': False,  # 不再加载页面
            'no_color': True,  # 禁用颜色输出
            'progress_hooks': [],  # 进度钩子（可添加自定义钩子）
            'logger': debug_logger,  # 使用自定义logger
            'debug_printtraffic': True,  # 打印网络流量（详细调试）
        })
        
        if output_path:
            ydl_opts['outtmpl'] = str(output_path)
        elif bv_id:
            # 使用BV号命名
            ydl_opts['outtmpl'] = str(TEMP_DIR / f"{bv_id}.%(ext)s")
        
        try:
            debug_logger.info("创建yt-dlp下载器实例")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                debug_logger.info(f"开始提取视频信息: {url}")
                
                # 获取视频信息
                info = ydl.extract_info(url, download=True)
                debug_logger.info(f"视频信息提取成功，标题: {info.get('title', '未知')}")
                
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
                
                debug_logger.info(f"视频下载完成: {downloaded_file}")
                print(f"视频下载完成: {downloaded_file}")
                return downloaded_file, bv_id
                
        except json.JSONDecodeError as json_err:
            # JSON解析错误 - 捕获原始响应
            debug_logger.error(f"JSON解析错误: {json_err}")
            debug_logger.error(f"原始错误: {str(json_err)}")
            
            # 尝试从异常中提取更多信息
            import traceback
            error_trace = traceback.format_exc()
            debug_logger.error(f"错误追踪:\n{error_trace}")
            
            # 尝试手动获取原始响应
            try:
                import urllib.request
                import urllib.error
                debug_logger.info("尝试手动获取页面内容...")
                req = urllib.request.Request(
                    url,
                    headers=ydl_opts.get('http_headers', {})
                )
                with urllib.request.urlopen(req, timeout=30) as response:
                    raw_html = response.read().decode('utf-8', errors='ignore')
                    debug_logger.save_raw_response(url, raw_html, json_err)
                    debug_logger.error(f"手动获取页面成功，长度: {len(raw_html)}")
                    debug_logger.error(f"页面预览: {raw_html[:500]}")
            except Exception as manual_err:
                debug_logger.error(f"手动获取页面失败: {manual_err}")
            
            # 尝试备用下载策略
            debug_logger.info("JSON解析错误，尝试备用下载策略...")
            try:
                return VideoDownloader._try_backup_download_strategy(url, bv_id, debug_logger, output_path)
            except Exception as backup_err:
                debug_logger.error(f"备用下载策略也失败: {backup_err}")
                raise ValueError(f"下载B站视频失败: JSON解析错误 - {str(json_err)}")
                
        except Exception as e:
            debug_logger.error(f"下载过程发生异常: {e}")
            import traceback
            error_trace = traceback.format_exc()
            debug_logger.error(f"完整错误追踪:\n{error_trace}")
            
            # 检查是否是网络错误
            if "Failed to parse JSON" in str(e):
                debug_logger.error("检测到'Failed to parse JSON'错误，可能是B站API响应格式问题")
                debug_logger.error("建议检查: 1. Cookie设置 2. 请求头 3. 网络代理")
            
            # 保存原始响应数据以便调试
            try:
                debug_logger.save_raw_response(url, f"异常信息: {str(e)}", e)
                debug_logger.error(f"已保存异常信息到原始响应文件")
            except Exception as save_err:
                debug_logger.error(f"保存原始响应失败: {save_err}")
            
            # 尝试备用下载策略
            debug_logger.info("主下载失败，尝试备用下载策略...")
            try:
                return VideoDownloader._try_backup_download_strategy(url, bv_id, debug_logger, output_path)
            except Exception as backup_err:
                debug_logger.error(f"备用下载策略也失败: {backup_err}")
                raise ValueError(f"下载B站视频失败: {str(e)}")
    
    @staticmethod
    def _try_backup_download_strategy(url: str, bv_id: Optional[str], debug_logger: BilibiliDebugLogger, output_path: Optional[str] = None) -> Tuple[str, Optional[str]]:
        """
        尝试备用下载策略
        
        Args:
            url: B站视频URL
            bv_id: BV号
            debug_logger: 调试日志记录器
            output_path: 可选的输出路径
            
        Returns:
            (下载后的视频文件路径, BV号) 的元组
            
        Raises:
            ValueError: 所有备用策略都失败
        """
        debug_logger.info("尝试备用下载策略...")
        
        backup_strategies = [
            {
                'name': '简化配置策略',
                'opts': {
                    'format': 'best',
                    'quiet': True,
                    'no_warnings': True,
                    'http_headers': {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Referer': 'https://www.bilibili.com/',
                    },
                    'extractor_args': {
                        'bilibili': {
                            'skip_wbi': True,
                            'use_bilibili_h5_api': True,
                        }
                    }
                }
            },
            {
                'name': '通用提取器策略',
                'opts': {
                    'format': 'best',
                    'force_generic_extractor': True,
                    'http_headers': {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Referer': 'https://www.bilibili.com/',
                    }
                }
            },
            {
                'name': '最小化配置策略',
                'opts': {
                    'format': 'best',
                    'quiet': True,
                    'http_headers': {
                        'User-Agent': 'Mozilla/5.0',
                        'Referer': 'https://www.bilibili.com/',
                    },
                    'extractor_args': {
                        'bilibili': {
                            'skip_wbi': True,
                            'skip_api_wbi': True,
                        }
                    }
                }
            },
            {
                'name': '激进配置策略',
                'opts': {
                    'format': 'best',
                    'quiet': False,
                    'no_warnings': False,
                    'http_headers': {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                        'Referer': 'https://www.bilibili.com/',
                        'Accept': 'application/json, text/plain, */*',
                        'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Origin': 'https://www.bilibili.com',
                    },
                    'extractor_args': {
                        'bilibili': {
                            'skip_wbi': True,
                            'skip_api_wbi': True,
                            'use_bilibili_app_api': False,
                            'use_bilibili_h5_api': True,
                            'prefer_bvid': True,
                            'disable_bili_live_api': True,
                        }
                    },
                    'force_generic_extractor': False,
                    'ignoreerrors': True,
                    'retries': 15,
                    'fragment_retries': 15,
                    'skip_unavailable_fragments': True,
                    'nocheckcertificate': True,
                    'geo_bypass': True,
                    'cookiefile': str(BILIBILI_COOKIE_FILE) if BILIBILI_COOKIE_FILE.exists() else None,
                }
            }
        ]
        
        for i, strategy in enumerate(backup_strategies):
            debug_logger.info(f"尝试备用策略 {i+1}: {strategy['name']}")
            try:
                ydl_opts = YT_DLP_OPTIONS.copy()
                ydl_opts.update(strategy['opts'])
                
                # 设置输出模板
                if output_path:
                    ydl_opts['outtmpl'] = str(output_path)
                elif bv_id:
                    ydl_opts['outtmpl'] = str(TEMP_DIR / f"{bv_id}.%(ext)s")
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    
                    if 'requested_downloads' in info and info['requested_downloads']:
                        downloaded_file = info['requested_downloads'][0]['filepath']
                    else:
                        ext = info.get('ext', 'mp4')
                        if bv_id:
                            downloaded_file = str(TEMP_DIR / f"{bv_id}.{ext}")
                        else:
                            title = info.get('title', 'video')
                            downloaded_file = str(TEMP_DIR / f"{title}.{ext}")
                    
                    debug_logger.info(f"备用策略 {strategy['name']} 成功: {downloaded_file}")
                    return downloaded_file, bv_id
                    
            except Exception as e:
                debug_logger.warning(f"备用策略 {strategy['name']} 失败: {e}")
                continue
        
        # 如果所有yt-dlp备用策略都失败，尝试B站API直接下载
        debug_logger.info("所有yt-dlp备用策略都失败，尝试B站API直接下载...")
        if bv_id:
            try:
                # 构建输出路径
                if output_path:
                    api_output_path = output_path
                else:
                    api_output_path = str(TEMP_DIR / f"{bv_id}_api_download.mp4")
                
                debug_logger.info(f"使用B站API直接下载视频: {bv_id}")
                debug_logger.info(f"输出路径: {api_output_path}")
                
                # 使用API下载
                success = download_bilibili_via_api(bv_id, api_output_path)
                
                if success and os.path.exists(api_output_path) and os.path.getsize(api_output_path) > 0:
                    debug_logger.info(f"B站API直接下载成功: {api_output_path}")
                    return api_output_path, bv_id
                else:
                    debug_logger.warning(f"B站API直接下载失败或文件无效")
            except Exception as api_err:
                debug_logger.error(f"B站API直接下载异常: {api_err}")
                import traceback
                debug_logger.error(f"API错误追踪: {traceback.format_exc()}")
        
        raise ValueError("所有备用下载策略都失败，包括B站API直接下载")
    
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
