"""
临时文件清理脚本
清理temp和output目录中的所有文件，只保留最终翻译后的视频
"""

import os
import shutil
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent
TEMP_DIR = PROJECT_ROOT / "temp"
OUTPUT_DIR = PROJECT_ROOT / "output"


def cleanup_temp_files(keep_video_path=None):
    """
    清理临时文件
    
    Args:
        keep_video_path: 需要保留的视频文件路径（完整路径）
    """
    print("\n" + "="*60)
    print("开始清理临时文件...")
    print("="*60)
    
    # 清理temp目录
    if TEMP_DIR.exists():
        print(f"\n清理 {TEMP_DIR} 目录...")
        deleted_count = 0
        for item in TEMP_DIR.iterdir():
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
        print(f"temp目录清理完成，共删除 {deleted_count} 个文件/目录")
    
    # 清理output目录（保留指定的视频文件）
    if OUTPUT_DIR.exists():
        print(f"\n清理 {OUTPUT_DIR} 目录...")
        deleted_count = 0
        kept_count = 0
        
        for item in OUTPUT_DIR.iterdir():
            # 如果指定了保留文件，且当前文件是要保留的
            if keep_video_path and item.resolve() == Path(keep_video_path).resolve():
                print(f"  ⊙ 保留: {item.name}")
                kept_count += 1
                continue
            
            # 只保留最终翻译后的视频文件（文件名包含_translated）
            if item.is_file() and "_translated" in item.name and item.suffix == ".mp4":
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

