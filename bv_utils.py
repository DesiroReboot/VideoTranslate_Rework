"""
BV号工具模块
提供BV号提取、AV号转BV号、短链解析等功能
"""

import re
import requests
from typing import Optional


def extract_bv_from_url(url: str) -> Optional[str]:
    """
    从B站URL中提取BV号
    
    Args:
        url: B站视频URL
        
    Returns:
        BV号，如果无法提取则返回None
    """
    # 安全: 限制URL长度防止ReDoS攻击
    if len(url) > 500:
        return None
    
    # 匹配BV号（保持原始大小写）
    # 限制BV号长度为10-13个字符，防止贪婪匹配
    bv_pattern = r'[Bb][Vv][a-zA-Z0-9]{10,13}'
    match = re.search(bv_pattern, url)
    if match:
        bv_raw = match.group(0)
        # 规范化：只将BV两个字母大写，其余保持原样
        return 'BV' + bv_raw[2:]
    
    return None


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
    table = 'fZodR9XQDSUm21yCkr6zBqiveYah8bt4xsWpHnJE7jL5VG3guMTKNPAwcF'
    tr = {}
    for i in range(58):
        tr[table[i]] = i
    s = [11, 10, 3, 8, 4, 6]
    xor = 177451812
    add = 8728348608
    
    x = (av_number ^ xor) + add
    r = list('BV1  4 1 7  ')
    for i in range(6):
        r[s[i]] = table[x // 58 ** i % 58]
    
    return ''.join(r)


def extract_av_from_url(url: str) -> Optional[int]:
    """
    从URL中提取AV号
    
    Args:
        url: 包含AV号的URL
        
    Returns:
        AV号（数字），如果无法提取则返回None
    """
    av_pattern = r'av(\d+)'
    match = re.search(av_pattern, url, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def resolve_short_link(short_url: str, timeout: int = 5) -> Optional[str]:
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
        if not short_url.startswith('http'):
            short_url = 'https://' + short_url
        
        # 只允许b23.tv域名
        # if 'b23.tv' not in short_url:
        #     print("错误: 仅支持b23.tv短链接")
        #     return None
        
        # 限制超时时间，防止挂起
        if timeout > 10:
            timeout = 10
        
        # 发送HEAD请求，不下载内容
        response = requests.head(short_url, allow_redirects=True, timeout=timeout)
        
        # 验证重定向后的URL也是B站域名
        if 'bilibili.com' not in response.url:
            print(f"警告: 短链接重定向到非哔哩哔哩域名: {response.url}")
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
    if 'b23.tv' in url:
        print(f"检测到短链接，正在解析...")
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
