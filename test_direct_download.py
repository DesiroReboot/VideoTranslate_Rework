"""
测试直链下载功能
"""

from video_downloader import VideoDownloader
from config import (
    DIRECT_DOWNLOAD_ALLOWED_DOMAINS,
    DIRECT_DOWNLOAD_MAX_SIZE,
    DIRECT_DOWNLOAD_TIMEOUT,
)

def test_url_detection():
    """测试URL检测功能"""
    print("=" * 60)
    print("测试URL检测功能")
    print("=" * 60)

    test_cases = [
        ("https://www.bilibili.com/video/BV1xx411c7mD", "B站URL", True, False),
        ("BV1rbvZBHEbx", "纯BV号", True, False),
        ("https://b23.tv/abc123", "B站短链", True, False),
        ("https://example.com/video.mp4", "直链(未配置域名)", False, False),
        ("/path/to/local/video.mp4", "本地路径", False, False),
        ("invalid-input", "无效输入", False, False),
    ]

    for url, desc, expected_bilibili, expected_direct in test_cases:
        is_bilibili = VideoDownloader.is_bilibili_url(url)
        is_direct = VideoDownloader.is_direct_download_url(url)

        status_bilibili = "[OK]" if is_bilibili == expected_bilibili else "[FAIL]"
        status_direct = "[OK]" if is_direct == expected_direct else "[FAIL]"

        print(f"\n{status_bilibili} {status_direct} 测试: {desc}")
        print(f"  输入: {url}")
        print(f"  是B站URL: {is_bilibili} (期望: {expected_bilibili})")
        print(f"  是直链URL: {is_direct} (期望: {expected_direct})")

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)

def test_error_messages():
    """测试错误消息"""
    print("\n" + "=" * 60)
    print("测试错误消息")
    print("=" * 60)

    # 测试无效输入的错误消息
    try:
        VideoDownloader.prepare_video("invalid-input")
    except ValueError as e:
        print("\n[OK] 无效输入错误消息:")
        print(str(e))

    # 测试直链下载（未配置域名时的错误）
    if not DIRECT_DOWNLOAD_ALLOWED_DOMAINS:
        print("\n[OK] 直链下载未配置域名:")
        print("  当前域名白名单为空，直链下载功能不会启用")

    print("\n" + "=" * 60)

def print_config_info():
    """打印配置信息"""
    print("\n" + "=" * 60)
    print("当前配置")
    print("=" * 60)

    print(f"\n直链下载配置:")
    print(f"  域名白名单: {DIRECT_DOWNLOAD_ALLOWED_DOMAINS if DIRECT_DOWNLOAD_ALLOWED_DOMAINS else '未配置'}")
    print(f"  文件大小限制: {DIRECT_DOWNLOAD_MAX_SIZE / 1024 / 1024:.0f}MB")
    print(f"  下载超时: {DIRECT_DOWNLOAD_TIMEOUT}秒")

    if not DIRECT_DOWNLOAD_ALLOWED_DOMAINS:
        print("\n[!] 注意: 直链下载功能未启用")
        print("   如需使用，请在 config.py 中配置 DIRECT_DOWNLOAD_ALLOWED_DOMAINS")
        print("   示例:")
        print('     DIRECT_DOWNLOAD_ALLOWED_DOMAINS = ["your-cdn.com", "your-storage.com"]')

    print("\n" + "=" * 60)

if __name__ == "__main__":
    print_config_info()
    test_url_detection()
    test_error_messages()
