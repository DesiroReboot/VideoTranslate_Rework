"""
视频翻译主程序
支持B站视频URL或本地视频文件,自动完成:
1. 视频下载(如果是URL)
2. 音频提取
3. 语音识别(ASR)
4. 文本翻译
5. 语音合成(TTS)
6. 音频替换
7. 输出翻译后的视频
"""

import sys
import time
from pathlib import Path
from typing import Optional

from config import validate_config, OUTPUT_DIR
from video_downloader import VideoDownloader
from audio_processor import AudioProcessor
from ai_services import AIServices
from cleanup_temp import cleanup_temp_files


class VideoTranslator:
    """视频翻译器主类"""
    
    def __init__(self):
        """初始化视频翻译器"""
        # 验证配置
        validate_config()
        
        # 初始化AI服务
        self.ai_services = AIServices()
        
        print("\n" + "="*60)
        print("视频翻译系统 v1.0")
        print("支持: B站视频下载 | 语音识别 | 机器翻译 | 语音合成")
        print("="*60 + "\n")
    
    def translate_video(self, url_or_path: str, target_language: str,
                       source_language: str = "auto") -> str:
        """
        翻译视频的完整流程
        
        Args:
            url_or_path: B站视频URL或本地视频文件路径
            target_language: 目标语言 (如: English, Japanese, Korean等)
            source_language: 源语言 (默认自动检测)
            
        Returns:
            翻译后的视频文件路径
            
        Raises:
            Exception: 处理过程中的任何错误
        """
        start_time = time.time()
        
        try:
            # 步骤1: 准备视频文件
            print("\n[步骤 1/6] 准备视频文件...")
            video_path, bv_id = VideoDownloader.prepare_video(url_or_path)
            if bv_id:
                print(f"✓ 视频就绪: {video_path} (BV号: {bv_id})")
            else:
                print(f"✓ 视频就绪: {video_path}")
            
            # 步骤2: 提取音频
            print("\n[步骤 2/6] 提取原始音频...")
            original_audio = AudioProcessor.extract_audio(video_path)
            print(f"✓ 音频提取完成: {original_audio}")
            
            # 步骤3: 语音识别
            print("\n[步骤 3/6] 语音识别(ASR)...")
            print("提示: 这可能需要几分钟,请耐心等待...")
            original_text = self.ai_services.speech_to_text(original_audio)
            print(f"✓ 识别完成,共 {len(original_text)} 字符")
            
            # 保存原文
            if bv_id:
                original_text_file = OUTPUT_DIR / f"{bv_id}_original.txt"
            else:
                video_name = Path(video_path).stem
                original_text_file = OUTPUT_DIR / f"{video_name}_original.txt"
            original_text_file.write_text(original_text, encoding='utf-8')
            print(f"  原文已保存: {original_text_file}")
            
            # 步骤4: 文本翻译
            print(f"\n[步骤 4/6] 翻译文本 (目标语言: {target_language})...")
            translated_text = self.ai_services.translate_text(
                original_text, 
                target_language, 
                source_language
            )
            print(f"✓ 翻译完成,共 {len(translated_text)} 字符")
            
            # 保存译文
            if bv_id:
                translated_text_file = OUTPUT_DIR / f"{bv_id}_{target_language}.txt"
            else:
                video_name = Path(video_path).stem
                translated_text_file = OUTPUT_DIR / f"{video_name}_translated_{target_language}.txt"
            translated_text_file.write_text(translated_text, encoding='utf-8')
            print(f"  译文已保存: {translated_text_file}")
            
            # 步骤5: 语音合成
            print("\n[步骤 5/6] 语音合成(TTS)...")
            print("提示: 正在生成新的配音...")
            new_audio = self.ai_services.text_to_speech(
                translated_text,
                language=target_language
            )
            print(f"✓ 语音合成完成: {new_audio}")
            
            # 步骤6: 替换音频
            print("\n[步骤 6/6] 合成最终视频...")
            print("提示: 正在合成视频,这可能需要几分钟...")
            output_video = AudioProcessor.replace_audio(
                video_path,
                new_audio,
                bv_id=bv_id,
                target_language=target_language
            )
            print(f"✓ 视频合成完成!")
            
            # 完成
            elapsed_time = time.time() - start_time
            print("\n" + "="*60)
            print("✓ 翻译完成!")
            print(f"  总耗时: {elapsed_time:.1f} 秒 ({elapsed_time/60:.1f} 分钟)")
            print(f"  输出视频: {output_video}")
            print(f"  原文文本: {original_text_file}")
            print(f"  译文文本: {translated_text_file}")
            print("="*60 + "\n")
            
            # 自动清理临时文件
            print("\n[清理临时文件]")
            try:
                cleanup_temp_files(keep_video_path=str(output_video))
            except Exception as e:
                print(f"警告: 临时文件清理失败: {e}")
            
            return output_video
            
        except Exception as e:
            print(f"\n✗ 错误: {str(e)}")
            raise


def main():
    """主函数 - 命令行接口"""
    
    # 解析命令行参数
    if len(sys.argv) < 3:
        print("""
使用方法:
    python main.py <视频URL或路径> <目标语言> [源语言]

示例:
    # 翻译B站视频为英文
    python main.py "https://www.bilibili.com/video/BVxxxxxxxxx" English
    
    # 翻译本地视频为日文
    python main.py "video.mp4" Japanese Chinese
    
支持的语言:
    Chinese, English, Japanese, Korean, Spanish, French, 
    German, Russian, Italian, Portuguese 等92种语言
        """)
        sys.exit(1)
    
    url_or_path = sys.argv[1]
    target_language = sys.argv[2]
    source_language = sys.argv[3] if len(sys.argv) > 3 else "auto"
    
    # 安全验证: 限制输入长度
    if len(url_or_path) > 1000:
        print("错误: URL或路径过长")
        sys.exit(1)
    
    # 安全验证: 语言参数白名单
    allowed_languages = [
        "Chinese", "English", "Japanese", "Korean", "Spanish", "French",
        "German", "Russian", "Italian", "Portuguese", "Arabic", "Hindi",
        "auto"  # 自动检测
    ]
    
    if target_language not in allowed_languages:
        print(f"错误: 不支持的目标语言 '{target_language}'")
        print(f"支持的语言: {', '.join(allowed_languages)}")
        sys.exit(1)
    
    if source_language not in allowed_languages:
        print(f"错误: 不支持的源语言 '{source_language}'")
        print(f"支持的语言: {', '.join(allowed_languages)}")
        sys.exit(1)
    
    try:
        # 创建翻译器并执行
        translator = VideoTranslator()
        output_video = translator.translate_video(
            url_or_path,
            target_language,
            source_language
        )
        
        print(f"\n成功! 翻译后的视频已保存到: {output_video}")
        
    except KeyboardInterrupt:
        print("\n\n用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n处理失败: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
