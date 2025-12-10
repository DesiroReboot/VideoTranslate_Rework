"""
快速开始示例

演示如何使用视频翻译系统的核心功能
"""

from main import VideoTranslator

def example_1_translate_bilibili_video():
    """示例1: 翻译B站视频"""
    print("=" * 60)
    print("示例1: 翻译B站视频为英文")
    print("=" * 60)
    
    # 创建翻译器
    translator = VideoTranslator()
    
    # B站视频URL
    bilibili_url = "https://www.bilibili.com/video/BV1xx411c7mD"
    
    # 翻译为英文
    output_video = translator.translate_video(
        url_or_path=bilibili_url,
        target_language="English"
    )
    
    print(f"\n完成! 输出视频: {output_video}")


def example_2_translate_local_video():
    """示例2: 翻译本地视频"""
    print("=" * 60)
    print("示例2: 翻译本地视频为日文")
    print("=" * 60)
    
    translator = VideoTranslator()
    
    # 本地视频文件路径
    local_video = "your_video.mp4"  # 替换为实际路径
    
    # 翻译为日文,指定源语言为中文
    output_video = translator.translate_video(
        url_or_path=local_video,
        target_language="Japanese",
        source_language="Chinese"
    )
    
    print(f"\n完成! 输出视频: {output_video}")


def example_3_batch_translate():
    """示例3: 批量翻译多个视频"""
    print("=" * 60)
    print("示例3: 批量翻译多个视频")
    print("=" * 60)
    
    translator = VideoTranslator()
    
    # 视频列表
    videos = [
        "video1.mp4",
        "video2.mp4",
        "video3.mp4",
    ]
    
    # 目标语言列表
    target_languages = ["English", "Japanese", "Korean"]
    
    # 批量处理
    for video in videos:
        for lang in target_languages:
            print(f"\n处理: {video} -> {lang}")
            try:
                output = translator.translate_video(video, lang)
                print(f"✓ 成功: {output}")
            except Exception as e:
                print(f"✗ 失败: {str(e)}")


def example_4_custom_config():
    """示例4: 使用自定义配置"""
    print("=" * 60)
    print("示例4: 使用自定义配置")
    print("=" * 60)
    
    # 可以在调用前修改配置
    import config
    
    # 自定义TTS音色
    config.TTS_VOICE_MAP["English"] = "Matthew"  # 使用男声
    
    # 自定义输出目录
    custom_output = config.PROJECT_ROOT / "my_outputs"
    custom_output.mkdir(exist_ok=True)
    
    translator = VideoTranslator()
    output_video = translator.translate_video(
        "test.mp4",
        "English"
    )
    
    print(f"\n完成! 输出视频: {output_video}")


def main():
    """主函数 - 选择要运行的示例"""
    print("""
╔══════════════════════════════════════════════════════════╗
║          视频翻译系统 - 快速开始示例                      ║
╚══════════════════════════════════════════════════════════╝

请选择要运行的示例:

1. 翻译B站视频为英文
2. 翻译本地视频为日文
3. 批量翻译多个视频
4. 使用自定义配置
0. 退出

    """)
    
    choice = input("请输入选项 (0-4): ").strip()
    
    examples = {
        "1": example_1_translate_bilibili_video,
        "2": example_2_translate_local_video,
        "3": example_3_batch_translate,
        "4": example_4_custom_config,
    }
    
    if choice == "0":
        print("再见!")
        return
    
    example_func = examples.get(choice)
    if example_func:
        try:
            example_func()
        except Exception as e:
            print(f"\n错误: {str(e)}")
    else:
        print("无效的选项!")


if __name__ == "__main__":
    main()
