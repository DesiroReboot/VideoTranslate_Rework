"""
音频处理模块
负责音频提取、替换等操作
"""

from pathlib import Path
from typing import Optional
from moviepy import VideoFileClip, AudioFileClip
from config import TEMP_DIR, OUTPUT_DIR, AUDIO_FORMAT, VIDEO_CODEC, AUDIO_CODEC


class AudioProcessor:
    """音频处理器,负责视频音频的提取和替换"""
    
    @staticmethod
    def extract_audio(video_path: str, output_audio_path: Optional[str] = None) -> str:
        """
        从视频中提取音频

        Args:
            video_path: 视频文件路径
            output_audio_path: 输出音频路径,不指定则自动生成

        Returns:
            提取的音频文件路径

        Raises:
            Exception: 提取失败
        """
        print(f"正在从视频中提取音频: {video_path}")

        try:
            # 检查输入参数
            if not video_path or not video_path.strip():
                raise ValueError("视频文件路径不能为空")
            # 加载视频
            video = VideoFileClip(video_path)
            
            # 检查是否有音频
            if video.audio is None:
                video.close()
                raise ValueError("视频中没有音频轨道")
            
            # 生成输出路径
            if not output_audio_path:
                video_name = Path(video_path).stem
                output_audio_path = str(TEMP_DIR / f"{video_name}_original.{AUDIO_FORMAT}")
            
            # 提取音频
            video.audio.write_audiofile(
                output_audio_path,
                codec='libmp3lame' if AUDIO_FORMAT == 'mp3' else None,
                #verbose=False,
                logger=None
            )
            
            # 关闭视频文件
            video.close()
            
            print(f"音频提取完成: {output_audio_path}")
            return output_audio_path
            
        except Exception as e:
            raise Exception(f"音频提取失败: {str(e)}")
    
    @staticmethod
    def replace_audio(video_path: str, new_audio_path: str, 
                      output_video_path: Optional[str] = None) -> str:
        """
        替换视频中的音频
        
        Args:
            video_path: 原视频文件路径
            new_audio_path: 新音频文件路径
            output_video_path: 输出视频路径,不指定则自动生成
            
        Returns:
            输出的视频文件路径
            
        Raises:
            Exception: 替换失败
        """
        print(f"正在替换视频音频...")
        print(f"视频: {video_path}")
        print(f"新音频: {new_audio_path}")
        
        try:
            # 加载视频和新音频
            video = VideoFileClip(video_path)
            new_audio = AudioFileClip(new_audio_path)
            
            # 检查音频长度,如果音频比视频短,需要处理
            if new_audio.duration < video.duration:
                print(f"警告: 音频时长({new_audio.duration:.2f}s) 短于视频时长({video.duration:.2f}s)")
                # 可以选择循环音频或保持原样
            elif new_audio.duration > video.duration:
                print(f"提示: 音频时长({new_audio.duration:.2f}s) 长于视频时长({video.duration:.2f}s),将自动裁剪")
                # 使用pydub裁剪音频
                from pydub import AudioSegment
                import tempfile
                
                # 读取音频文件
                audio_segment = AudioSegment.from_wav(new_audio_path)
                # 裁剪到视频长度(毫秒)
                trimmed_audio = audio_segment[:int(video.duration * 1000)]
                # 保存为临时文件
                temp_audio_path = tempfile.mktemp(suffix=".wav")
                trimmed_audio.export(temp_audio_path, format="wav")
                
                # 重新加载裁剪后的音频
                new_audio.close()
                new_audio = AudioFileClip(temp_audio_path)
            
            # 替换音频
            final_video = video.with_audio(new_audio)
            
            # 生成输出路径
            if not output_video_path:
                video_name = Path(video_path).stem
                output_video_path = str(OUTPUT_DIR / f"{video_name}_translated.mp4")
            
            # 输出视频
            final_video.write_videofile(
                output_video_path,
                codec=VIDEO_CODEC,
                audio_codec=AUDIO_CODEC,
                logger=None
            )
            
            # 关闭所有文件
            video.close()
            new_audio.close()
            final_video.close()
            
            print(f"视频生成完成: {output_video_path}")
            return output_video_path
            
        except Exception as e:
            raise Exception(f"音频替换失败: {str(e)}")
    
    @staticmethod
    def get_audio_duration(audio_path: str) -> float:
        """
        获取音频时长
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            音频时长(秒)
        """
        try:
            audio = AudioFileClip(audio_path)
            duration = audio.duration
            audio.close()
            return duration
        except Exception as e:
            raise Exception(f"获取音频时长失败: {str(e)}")


# 测试代码
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
        
        # 测试音频提取
        print("\n=== 测试音频提取 ===")
        audio_path = AudioProcessor.extract_audio(video_path)
        print(f"提取的音频: {audio_path}")
        
        # 获取音频时长
        duration = AudioProcessor.get_audio_duration(audio_path)
        print(f"音频时长: {duration:.2f}秒")
    else:
        print("用法: python audio_processor.py <视频文件路径>")
