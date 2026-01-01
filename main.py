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

from config import validate_config, OUTPUT_DIR
from video_downloader import VideoDownloader
from audio_processor import AudioProcessor
from ai_services import AIServices
from cleanup_temp import cleanup_temp_files
from common.security import InputValidator, SecurityError, RegexValidator

# 翻译风格常量定义
VALID_TRANSLATION_STYLES = [
    "humorous",
    "serious",
    "educational",
    "entertainment",
    "news",
    "auto",
]


class VideoTranslator:
    """视频翻译器主类"""

    def __init__(self, translation_style: str = "auto"):
        """初始化视频翻译器

        Args:
            translation_style: 翻译风格，可选值：humorous, serious, educational, entertainment, news, auto
        """
        # 验证配置
        validate_config()

        # 初始化AI服务
        self.ai_services = AIServices(translation_style)

        print("\n" + "=" * 60)
        print("视频翻译系统 v1.1")
        print("支持: B站视频下载 | 语音识别 | 机器翻译 | 语音合成")
        print("新增: 多风格翻译模式")
        print("=" * 60 + "\n")

        # 显示当前翻译模式信息
        mode_info = self.ai_services.get_translation_mode_info()
        print(f"当前翻译模式: {mode_info['name']} ({mode_info['style']})")
        print(f"模式描述: {mode_info['description']}")
        print(f"模型参数: {mode_info['model_params']}")
        print()

    def translate_video(
        self, url_or_path: str, target_language: str, source_language: str = "auto"
    ) -> str:
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
            original_text_file.write_text(original_text, encoding="utf-8")
            print(f"  原文已保存: {original_text_file}")

            # 步骤4: 文本翻译
            print(f"\n[步骤 4/6] 翻译文本 (目标语言: {target_language})...")

            # 使用带质量评价和重试的翻译方法
            translated_text, translation_score = self.ai_services.translate_with_retry(
                original_text, target_language, source_language
            )

            print(f"✓ 翻译完成,共 {len(translated_text)} 字符")

            # 如果有评分结果，显示评分信息
            if translation_score:
                print(f"✓ 翻译质量评分: {translation_score.overall_score:.1f}/100")
                if translation_score.suggestions:
                    print("✓ 改进建议:")
                    for i, suggestion in enumerate(
                        translation_score.suggestions[:3], 1
                    ):  # 只显示前3条建议
                        print(f"  {i}. {suggestion}")

            # 保存译文
            if bv_id:
                translated_text_file = OUTPUT_DIR / f"{bv_id}_{target_language}.txt"
            else:
                video_name = Path(video_path).stem
                translated_text_file = (
                    OUTPUT_DIR / f"{video_name}_translated_{target_language}.txt"
                )
            translated_text_file.write_text(translated_text, encoding="utf-8")
            print(f"  译文已保存: {translated_text_file}")

            # 如果有评分结果，保存评分报告
            if translation_score:
                from config import SCORING_RESULTS_DIR
                import json

                # 生成评分报告文件名
                if bv_id:
                    score_report_file = (
                        SCORING_RESULTS_DIR
                        / f"{bv_id}_{target_language}_score_report.json"
                    )
                else:
                    video_name = Path(video_path).stem
                    score_report_file = (
                        SCORING_RESULTS_DIR
                        / f"{video_name}_{target_language}_score_report.json"
                    )

                # 准备评分报告数据
                score_report = {
                    "video_info": {
                        "bv_id": bv_id,
                        "video_path": video_path,
                        "source_language": source_language,
                        "target_language": target_language,
                    },
                    "translation_score": {
                        "overall_score": translation_score.overall_score,
                        "fluency": translation_score.fluency,
                        "completeness": translation_score.completeness,
                        "consistency": translation_score.consistency,
                        "accuracy": translation_score.accuracy,
                        "style_adaptation": translation_score.style_adaptation,
                        "cultural_adaptation": translation_score.cultural_adaptation,
                        "suggestions": translation_score.suggestions,
                        "detailed_feedback": translation_score.detailed_feedback,
                    },
                    "timestamp": int(time.time()),
                }

                # 保存评分报告
                with open(score_report_file, "w", encoding="utf-8") as f:
                    json.dump(score_report, f, ensure_ascii=False, indent=2)
                print(f"  评分报告已保存: {score_report_file}")

            # 步骤5: 语音合成
            print("\n[步骤 5/6] 语音合成(TTS)...")
            print("提示: 正在生成新的配音...")
            new_audio = self.ai_services.text_to_speech(
                translated_text, language=target_language
            )
            print(f"✓ 语音合成完成: {new_audio}")

            # 步骤6: 替换音频
            print("\n[步骤 6/6] 合成最终视频...")
            print("提示: 正在合成视频,这可能需要几分钟...")
            output_video = AudioProcessor.replace_audio(
                video_path, new_audio, bv_id=bv_id, target_language=target_language
            )
            print("✓ 视频合成完成!")

            # 完成
            elapsed_time = time.time() - start_time
            print("\n" + "=" * 60)
            print("✓ 翻译完成!")
            print(f"  总耗时: {elapsed_time:.1f} 秒 ({elapsed_time / 60:.1f} 分钟)")
            print(f"  输出视频: {output_video}")
            print(f"  原文文本: {original_text_file}")
            print(f"  译文文本: {translated_text_file}")
            print("=" * 60 + "\n")

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
    python main.py <视频URL或路径> <目标语言> [翻译风格]

示例:
    # 翻译B站视频为英文（自动风格）
    python main.py "https://www.bilibili.com/video/BVxxxxxxxxx" English
    
    # 翻译本地视频为日文（幽默风格）
    python main.py "video.mp4" Japanese humorous
    
    # 翻译教育视频为英文（教育风格）
    python main.py "education_video.mp4" English educational
    
支持的语言:
    Chinese, English, Japanese, Korean, Spanish, French, 
    German, Russian, Italian, Portuguese 等92种语言
    
翻译风格:
    humorous    - 幽默风格，保留原视频的幽默感和轻松氛围
    serious     - 正经风格，适用于正式、严肃的内容
    educational - 教育风格，适用于教学、科普类内容
    entertainment- 娱乐风格，适用于娱乐、综艺类内容
    news        - 新闻风格，适用于新闻、资讯类内容
    auto        - 自动检测，根据内容自动选择最适合的风格（默认）
    
注意: 源语言将自动识别，无需手动指定
        """)
        sys.exit(1)

    url_or_path = sys.argv[1]
    target_language = sys.argv[2]
    source_language = "auto"  # 源语言固定为自动识别
    translation_style = sys.argv[3] if len(sys.argv) > 3 else "auto"

    # 使用InputValidator进行安全验证
    try:
        # 1. 参数数量验证
        if len(sys.argv) < 3 or len(sys.argv) > 4:
            raise ValueError(
                "参数数量错误。用法: python main.py <URL/文件路径> <目标语言> [翻译风格]\n"
                '示例: python main.py "https://www.bilibili.com/video/BVxxx" Japanese serious'
            )

        # 2. 编码格式验证 - 确保参数是有效的UTF-8字符串
        try:
            url_or_path.encode("utf-8")
            target_language.encode("utf-8")
            translation_style.encode("utf-8")
        except UnicodeEncodeError:
            raise ValueError("参数包含无效的字符编码，请使用UTF-8编码")

        # 3. 特殊字符过滤 - 防止命令注入
        dangerous_chars = ["|", "&", ";", "$", "`", "(", ")", "<", ">", '"', "'"]
        for char in dangerous_chars:
            if char in url_or_path:
                raise ValueError(f"URL/路径包含危险字符: {char}")

        # 4. URL/路径长度验证
        url_or_path = InputValidator.validate_url_length(url_or_path, max_length=1000)

        # 5. 语言参数验证
        target_language = InputValidator.validate_language(target_language)
        # source_language 固定为 "auto"，无需验证

        # 6. 翻译风格参数验证
        if translation_style not in VALID_TRANSLATION_STYLES:
            raise ValueError(
                f"无效的翻译风格: {translation_style}。可选值: {', '.join(VALID_TRANSLATION_STYLES)}"
            )

        # 7. 正则表达式输入长度验证（防止ReDoS）
        RegexValidator.validate_input_length_for_regex(url_or_path, max_length=500)

    except ValueError as e:
        print(f"参数验证失败: {e}")
        sys.exit(1)
    except SecurityError as e:
        print(f"安全检查失败: {e}")
        sys.exit(1)

    try:
        # 创建翻译器并执行
        translator = VideoTranslator(translation_style)
        output_video = translator.translate_video(
            url_or_path, target_language, source_language
        )

        print(f"\n成功! 翻译后的视频已保存到: {output_video}")

    except KeyboardInterrupt:
        print("\n\n用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n处理失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
