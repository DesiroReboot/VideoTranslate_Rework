"""
临时文件清理脚本
清理temp和output目录中的所有文件，只保留最终翻译后的视频
"""

import os
import re
import shutil
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent
TEMP_DIR = PROJECT_ROOT / "temp"
OUTPUT_DIR = PROJECT_ROOT / "output"


def is_bv_video(filename: str) -> bool:
    """
    检查文件名是否为BV号命名的原视频文件
    匹配格式: BV + 字母数字.mp4
    例如: BV1vmmLBpEtz.mp4
    
    Args:
        filename: 文件名
        
    Returns:
        是否为BV号视频
    """
    if not filename.endswith('.mp4'):
        return False
    
    # 匹配BV号格式: BV + 字母数字.mp4 (不包含下划线)
    bv_pattern = r'^BV[a-zA-Z0-9]+\.mp4$'
    return bool(re.match(bv_pattern, filename))


def is_translated_video(filename: str) -> bool:
    """
    检查文件名是否为翻译后的视频文件
    匹配格式：
    - {BV号}_{target_language}.mp4
    - {BV号}_{target_language}_{count}.mp4
    - {any_name}_translated.mp4 (兼容本地文件)
    
    Args:
        filename: 文件名
        
    Returns:
        是否为翻译视频
    """
    if not filename.endswith('.mp4'):
        return False
    
    # 匹配BV号格式: BV + 字母数字 + _ + 语言 + (可选_数字).mp4
    # 例如: BV1vmmLBpEtz_English.mp4, BV1vmmLBpEtz_English_1.mp4
    bv_pattern = r'^BV[a-zA-Z0-9]+_[A-Za-z]+(_\d+)?\.mp4$'
    if re.match(bv_pattern, filename):
        return True
    
    # 兼容旧格式: 任意名称_translated.mp4
    if '_translated.mp4' in filename:
        return True
    
    return False


def cleanup_temp_files(keep_video_path=None):
    """
    清理临时文件
    
    Args:
        keep_video_path: 需要保留的视频文件路径（完整路径）
    """
    print("\n" + "="*60)
    print("开始清理临时文件...")
    print("="*60)
    
    # 安全检查: 验证目录存在且在项目内
    try:
        temp_dir_resolved = TEMP_DIR.resolve()
        output_dir_resolved = OUTPUT_DIR.resolve()
        project_root_resolved = PROJECT_ROOT.resolve()
        
        # 确保目录在项目范围内
        temp_dir_resolved.relative_to(project_root_resolved)
        output_dir_resolved.relative_to(project_root_resolved)
    except ValueError:
        print("错误: 检测到目录路径异常，中止清理")
        return
    
    # 清理temp目录
    if TEMP_DIR.exists():
        print(f"\n清理 {TEMP_DIR} 目录...")
        deleted_count = 0
        kept_count = 0
        
        for item in TEMP_DIR.iterdir():
            # 安全检查: 确保文件仍在temp目录内（防止符号链接攻击）
            try:
                item_resolved = item.resolve()
                item_resolved.relative_to(temp_dir_resolved)
            except ValueError:
                print(f"  ⚠ 警告: 跳过项目外路径: {item.name}")
                continue
            
            # 保留BV号命名的原视频文件
            if item.is_file() and is_bv_video(item.name):
                print(f"  ⊚ 保留: {item.name}")
                kept_count += 1
                continue
            
            # 删除其他文件
            try:
                if item.is_file():
                    item.unlink()
                    deleted_count += 1
                    print(f"  ✓ 删除: {item.name}")
                elif item.is_dir():
                    shutil.rmtree(item)
                    deleted_count += 1
                    print(f"  ✓ 删除目录: {item.name}")
            except Exception as e:
                print(f"  ✗ 无法删除 {item.name}: {e}")
        
        print(f"temp目录清理完成，删除 {deleted_count} 个，保留 {kept_count} 个文件/目录")
    
    # 清理output目录（保留指定的视频文件）
    if OUTPUT_DIR.exists():
        print(f"\n清理 {OUTPUT_DIR} 目录...")
        deleted_count = 0
        kept_count = 0
        
        for item in OUTPUT_DIR.iterdir():
            # 安全检查: 确保文件仍在output目录内
            try:
                item_resolved = item.resolve()
                item_resolved.relative_to(output_dir_resolved)
            except ValueError:
                print(f"  ⚠ 警告: 跳过项目外路径: {item.name}")
                continue
            
            # 如果指定了保留文件，且当前文件是要保留的
            if keep_video_path and item.resolve() == Path(keep_video_path).resolve():
                print(f"  ⊙ 保留: {item.name}")
                kept_count += 1
                continue
            
            # 保留所有翻译后的视频文件
            if item.is_file() and is_translated_video(item.name):
                print(f"  ⊙ 保留: {item.name}")
                kept_count += 1
                continue
            
            # 删除其他文件
            try:
                if item.is_file():
                    item.unlink()
                    deleted_count += 1
                    print(f"  ✓ 删除: {item.name}")
                elif item.is_dir():
                    shutil.rmtree(item)
                    deleted_count += 1
                    print(f"  ✓ 删除目录: {item.name}")
            except Exception as e:
                print(f"  ✗ 无法删除 {item.name}: {e}")
        
        print(f"output目录清理完成，删除 {deleted_count} 个，保留 {kept_count} 个文件")
    
    print("\n" + "="*60)
    print("✓ 临时文件清理完成！")
    print("="*60 + "\n")


if __name__ == "__main__":
    import sys
    
    # 如果传入了参数，作为要保留的视频路径
    keep_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    cleanup_temp_files(keep_path)

