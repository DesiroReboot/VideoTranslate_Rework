"""
BV号工具模块
提供BV号提取、AV号转BV号、短链解析等功能
"""

import re
import os
import json
from typing import Optional, Dict, Any
import requests

# from typing import Optional, Dict, Any, Tuple
from common.security import RegexValidator, URLValidator, ResourceValidator


def extract_bv_from_url(url: str) -> Optional[str]:
    """
    从B站URL中提取BV号

    Args:
        url: B站视频URL

    Returns:
        BV号，如果无法提取则返回None
    """
    # 使用RegexValidator防止ReDoS攻击
    return RegexValidator.extract_bv_safe(url)


def av_to_bv(av_number: int) -> str:
    """
    将AV号转换为BV号
    使用B站的AV-BV转换算法

    Args:
        av_number: AV号（数字）

    Returns:
        对应的BV号
    """
    # B站AV-BV转换表
    table = "fZodR9XQDSUm21yCkr6zBqiveYah8bt4xsWpHnJE7jL5VG3guMTKNPAwcF"
    tr = {}
    for i in range(58):
        tr[table[i]] = i
    s = [11, 10, 3, 8, 4, 6]
    xor = 177451812
    add = 8728348608

    x = (av_number ^ xor) + add
    r = list("BV1  4 1 7  ")
    for i in range(6):
        r[s[i]] = table[x // 58**i % 58]

    return "".join(r)


def extract_av_from_url(url: str) -> Optional[int]:
    """
    从URL中提取AV号

    Args:
        url: 包含AV号的URL

    Returns:
        AV号（数字），如果无法提取则返回None
    """
    av_pattern = r"av(\d+)"
    match = re.search(av_pattern, url, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def resolve_short_link(short_url: str, timeout: float = 5.0) -> Optional[str]:
    """
    解析b23.tv短链接，获取真实URL

    Args:
        short_url: b23.tv短链接
        timeout: 请求超时时间（秒）

    Returns:
        真实URL，如果解析失败则返回None
    """
    try:
        # 安全: 验证URL格式，防止SSRF攻击
        if not short_url.startswith("http"):
            short_url = "https://" + short_url

        # 使用URLValidator验证短链接
        URLValidator.validate_short_link(short_url)

        # 使用ResourceValidator限制超时时间
        timeout = ResourceValidator.validate_timeout(timeout, max_timeout=10.0)

        # 发送HEAD请求，不下载内容
        response = requests.head(short_url, allow_redirects=True, timeout=timeout)

        # 验证重定向后的URL也是B站域名
        if not URLValidator.validate_url_domain(response.url):
            print(f"警告: 短链接重定向到非B站域名: {response.url}")
            return None

        return response.url
    except Exception as e:
        print(f"解析短链接失败: {e}")
        return None


def normalize_bilibili_url(url: str) -> tuple[Optional[str], Optional[str]]:
    """
    规范化B站URL，提取BV号
    支持：
    - 标准BV号URL
    - AV号URL（自动转换为BV号）
    - b23.tv短链接（自动解析）

    Args:
        url: 各种格式的B站URL

    Returns:
        (BV号, 规范化后的URL) 的元组，如果失败则返回 (None, None)
    """
    # 1. 先尝试直接提取BV号
    bv_id = extract_bv_from_url(url)
    if bv_id:
        normalized_url = f"https://www.bilibili.com/video/{bv_id}"
        return bv_id, normalized_url

    # 2. 尝试解析短链接
    if "b23.tv" in url:
        print("检测到短链接，正在解析...")
        real_url = resolve_short_link(url)
        if real_url:
            print(f"解析结果: {real_url}")
            bv_id = extract_bv_from_url(real_url)
            if bv_id:
                normalized_url = f"https://www.bilibili.com/video/{bv_id}"
                return bv_id, normalized_url

    # 3. 尝试提取AV号并转换
    av_number = extract_av_from_url(url)
    if av_number:
        print(f"检测到AV号: av{av_number}，正在转换为BV号...")
        bv_id = av_to_bv(av_number)
        print(f"转换结果: {bv_id}")
        normalized_url = f"https://www.bilibili.com/video/{bv_id}"
        return bv_id, normalized_url

    return None, None


def get_bilibili_video_info_api(
    bv_id: str, timeout: float = 10.0
) -> Optional[Dict[str, Any]]:
    """
    通过B站API获取视频信息

    Args:
        bv_id: BV号
        timeout: 请求超时时间（秒）

    Returns:
        API返回的JSON数据，失败返回None
    """
    try:
        # API端点: https://api.bilibili.com/x/web-interface/view
        api_url = f"https://api.bilibili.com/x/web-interface/view?bvid={bv_id}"

        # 使用安全验证
        timeout = ResourceValidator.validate_timeout(timeout, max_timeout=30.0)

        # 设置请求头模拟浏览器
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Referer": "https://www.bilibili.com/",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "Origin": "https://www.bilibili.com",
        }

        print(f"请求B站API: {api_url}")
        response = requests.get(api_url, headers=headers, timeout=timeout)
        response.raise_for_status()

        data = response.json()

        if data.get("code") == 0:
            print(f"API请求成功，视频标题: {data['data'].get('title', '未知')}")
            return data["data"]
        else:
            print(f"API返回错误: {data.get('message', '未知错误')}")
            return None

    except requests.RequestException as e:
        print(f"请求B站API失败: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"解析API响应JSON失败: {e}")
        return None
    except Exception as e:
        print(f"获取视频信息异常: {e}")
        return None


def get_bilibili_video_streams_api(
    bv_id: str, cid: int, timeout: float = 10.0
) -> Optional[Dict[str, Any]]:
    """
    通过B站API获取视频流信息

    Args:
        bv_id: BV号
        cid: 视频CID（内容ID）
        timeout: 请求超时时间（秒）

    Returns:
        视频流信息JSON数据，失败返回None
    """
    try:
        # API端点: https://api.bilibili.com/x/player/playurl
        api_url = f"https://api.bilibili.com/x/player/playurl?bvid={bv_id}&cid={cid}&qn=120&fnval=16"

        # 使用安全验证
        timeout = ResourceValidator.validate_timeout(timeout, max_timeout=30.0)

        # 设置请求头
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Referer": "https://www.bilibili.com/",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "Origin": "https://www.bilibili.com",
        }

        print(f"请求视频流API: {api_url}")
        response = requests.get(api_url, headers=headers, timeout=timeout)
        response.raise_for_status()

        data = response.json()

        if data.get("code") == 0:
            print("视频流API请求成功")
            return data["data"]
        else:
            print(f"视频流API返回错误: {data.get('message', '未知错误')}")
            return None

    except requests.RequestException as e:
        print(f"请求视频流API失败: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"解析视频流API响应JSON失败: {e}")
        return None
    except Exception as e:
        print(f"获取视频流信息异常: {e}")
        return None


def get_best_video_stream_from_api(
    video_stream_data: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
    从API返回的视频流数据中选择最佳视频流

    Args:
        video_stream_data: API返回的视频流数据

    Returns:
        最佳视频流信息，失败返回None
    """
    try:
        if not video_stream_data:
            return None

        # 检查是否有dash视频流
        dash_info = video_stream_data.get("dash", {})
        if dash_info:
            video_streams = dash_info.get("video", [])
            audio_streams = dash_info.get("audio", [])

            if video_streams:
                # 按画质排序，选择最高的画质
                sorted_videos = sorted(
                    video_streams,
                    key=lambda x: x.get("bandwidth", 0) or x.get("id", 0),
                    reverse=True,
                )

                # 选择720P左右的画质（id=80或bandwidth适中）
                best_video = None
                for video in sorted_videos:
                    video_id = video.get("id")
                    if video_id == 80:  # 720P
                        best_video = video
                        break

                # 如果没有720P，选择第一个（最高画质）
                if not best_video and sorted_videos:
                    best_video = sorted_videos[0]

                if best_video and audio_streams:
                    # 选择最佳音频流
                    best_audio = audio_streams[0] if audio_streams else None

                    return {
                        "video_url": best_video.get("baseUrl")
                        or best_video.get("backupUrl", [None])[0],
                        "audio_url": best_audio.get("baseUrl") if best_audio else None,
                        "video_quality": best_video.get("id"),
                        "video_bandwidth": best_video.get("bandwidth"),
                        "video_codec": best_video.get("codecid"),
                        "audio_bandwidth": best_audio.get("bandwidth")
                        if best_audio
                        else None,
                        "has_audio": bool(best_audio),
                    }

        # 检查是否有flv格式
        accept_quality = video_stream_data.get("accept_quality", [])
        durl = video_stream_data.get("durl", [])

        if durl:
            # 选择第一个视频流
            first_stream = durl[0]
            return {
                "video_url": first_stream.get("url"),
                "audio_url": None,  # flv通常包含音视频
                "video_quality": accept_quality[0] if accept_quality else None,
                "video_bandwidth": first_stream.get("size"),
                "has_audio": True,  # flv格式包含音频
                "format": "flv",
            }

        return None

    except Exception as e:
        print(f"选择最佳视频流失败: {e}")
        return None


def download_video_directly(
    video_stream_info: Dict[str, Any], output_path: str, timeout: float = 30.0
) -> bool:
    """
    直接下载视频文件

    Args:
        video_stream_info: 视频流信息
        output_path: 输出文件路径
        timeout: 下载超时时间（秒）

    Returns:
        下载是否成功
    """
    try:
        video_url = video_stream_info.get("video_url")
        if not video_url:
            print("视频URL为空")
            return False

        # 安全验证URL
        if not URLValidator.validate_url_domain(video_url):
            print(f"视频URL不在白名单中: {video_url}")
            return False

        # 使用安全验证
        timeout = ResourceValidator.validate_timeout(timeout, max_timeout=120.0)

        print(f"开始直接下载视频: {video_url}")
        print(f"输出路径: {output_path}")

        # 设置请求头
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Referer": "https://www.bilibili.com/",
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q0=.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Origin": "https://www.bilibili.com",
        }

        # 下载视频
        response = requests.get(
            video_url, headers=headers, stream=True, timeout=timeout
        )
        response.raise_for_status()

        # 获取文件大小
        total_size = int(response.headers.get("content-length", 0))

        # 写入文件
        with open(output_path, "wb") as f:
            if total_size == 0:
                f.write(response.content)
            else:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        # 显示进度
                        if total_size > 0:
                            percent = downloaded / total_size * 100
                            print(
                                f"下载进度: {percent:.1f}% ({downloaded}/{total_size} bytes)",
                                end="\r",
                            )

        print(f"\n视频下载完成: {output_path}")

        # 检查文件是否有效
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return True
        else:
            print("下载无效的文件或为空")
            return False

    except requests.RequestException as e:
        print(f"下载视频失败: {e}")
        return False
    except Exception as e:
        print(f"下载视频异常: {e}")
        return False


def download_bilibili_via_api(bv_id: str, output_path: str) -> bool:
    """
    通过B站API直接下载视频

    Args:
        bv_id: BV号
        output_path: 输出文件路径

    Returns:
        下载是否成功
    """
    print(f"尝试通过B站API直接下载视频: {bv_id}")

    # 1. 获取视频基本信息
    video_info = get_bilibili_video_info_api(bv_id)
    if not video_info:
        print("获取视频信息失败")
        return False

    # 获取CID（内容ID）
    cid = video_info.get("cid")
    if not cid:
        print("无法获取视频CID")
        return False

    print(f"视频标题: {video_info.get('title', '未知')}")
    print(f"视频CID: {cid}")

    # 2. 获取视频流信息
    video_stream_data = get_bilibili_video_streams_api(bv_id, cid)
    if not video_stream_data:
        print("获取视频流信息失败")
        return False

    # 3. 选择最佳视频流
    best_stream = get_best_video_stream_from_api(video_stream_data)
    if not best_stream:
        print("无法选择最佳视频流")
        return False

    print(f"找到视频流，画质: {best_stream.get('video_quality', '未知')}")

    # 4. 下载视频
    return download_video_directly(best_stream, output_path)


# 测试代码
if __name__ == "__main__":
    test_cases = [
        "https://www.bilibili.com/video/BV1vmmLBpEtz",
        "https://www.bilibili.com/video/av170001",
        "https://b23.tv/abc123",
    ]

    for url in test_cases:
        print(f"\n测试: {url}")
        bv_id, normalized = normalize_bilibili_url(url)
        print(f"BV号: {bv_id}")
        print(f"规范化URL: {normalized}")

        # 测试API下载
        if bv_id:
            print("测试API下载功能...")
            test_output = f"test_{bv_id}.mp4"
            success = download_bilibili_via_api(bv_id, test_output)
            print(f"API下载结果: {'成功' if success else '失败'}")
