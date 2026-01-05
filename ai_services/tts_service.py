"""
TTS文本转语音服务模块
处理文本转语音功能
"""

import os
import time
from pathlib import Path
from typing import Optional
from pydub import AudioSegment

from .base_service import BaseAIService
from config import (
    TTS_MODEL,
    TTS_VOICE_MAP,
    DEFAULT_VOICE,
    TEMP_DIR,
)


class TTSService(BaseAIService):
    """文本转语音服务"""
    
    def __init__(self):
        """初始化TTS服务"""
        super().__init__("TTS")
        
        # 初始化状态
        self._initialized = False
    
    def initialize(self) -> None:
        """初始化TTS服务"""
        if self._initialized:
            return
        
        self._initialized = True
        self.logger.info("TTS服务初始化完成")
    
    def text_to_speech(
        self,
        text: str,
        output_path: Optional[str] = None,
        language: str = "Chinese",
        voice: Optional[str] = None,
    ) -> str:
        """文本转语音主接口
        
        Args:
            text: 待合成的文本
            output_path: 输出音频路径,不指定则自动生成
            language: 语言类型
            voice: 音色,不指定则根据语言自动选择
            
        Returns:
            生成的音频文件路径
            
        Raises:
            Exception: 合成失败
        """
        # 验证输入
        if not text or not isinstance(text, str):
            raise ValueError("TTS文本参数无效")
        
        self.logger.info("开始语音合成")
        self.logger.info(f"文本长度: {len(text)} 字符")
        self.logger.info(f"语言: {language}")
        
        # 选择音色
        if not voice:
            voice = TTS_VOICE_MAP.get(language, DEFAULT_VOICE)
        self.logger.info(f"音色: {voice}")
        
        try:
            # TTS API限制：单次最多600字符
            max_tts_length = 600
            
            if len(text) <= max_tts_length:
                # 文本较短，直接合成
                self.logger.info("文本较短，直接合成")
                return self._synthesize_single(text, voice, language, output_path)
            else:
                # 文本过长，需要分段处理并合并
                self.logger.info(f"文本过长，需要分段处理（每段最多{max_tts_length}字符）")
                return self._synthesize_long_text(
                    text, voice, language, output_path, max_tts_length
                )
                
        except Exception as e:
            raise Exception(f"语音合成失败: {str(e)}") from e
    
    def _synthesize_single(
        self, text: str, voice: str, language: str, output_path: Optional[str] = None
    ) -> str:
        """合成单段文本
        
        Args:
            text: 待合成文本
            voice: 音色
            language: 语言类型
            output_path: 输出路径
            
        Returns:
            生成的音频文件路径
        """
        import dashscope
        from config import DASHSCOPE_API_KEY
        
        # 检查API密钥是否配置
        if not DASHSCOPE_API_KEY:
            raise ValueError(
                'DASHSCOPE_API_KEY未配置，请在环境变量中设置。使用命令: setx DASHSCOPE_API_KEY "your_api_key_here"'
            )
        
        # 调用TTS API
        response = dashscope.MultiModalConversation.call(
            model=TTS_MODEL,
            api_key=DASHSCOPE_API_KEY,
            text=text,
            voice=voice,
            language_type=language,
            stream=False,
        )
        
        # 检查响应
        if response.status_code != 200:  # type: ignore
            raise Exception(f"TTS API调用失败: {response.message}")  # type: ignore
        
        # 获取音频URL
        audio_url = response.output.audio.url  # type: ignore
        self.logger.info(f"音频URL: {audio_url}")
        
        # 下载音频文件
        if not output_path:
            timestamp = int(time.time())
            output_path = str(TEMP_DIR / f"translated_audio_{timestamp}.wav")
        
        self.logger.info(f"下载音频到: {output_path}")
        self._download_file(audio_url, output_path)
        
        self.logger.info(f"语音合成完成: {output_path}")
        return output_path
    
    def _synthesize_long_text(
        self,
        text: str,
        voice: str,
        language: str,
        output_path: Optional[str],
        max_length: int,
    ) -> str:
        """分段合成长文本并合并音频
        
        Args:
            text: 待合成文本
            voice: 音色
            language: 语言类型
            output_path: 输出路径
            max_length: 最大分段长度
            
        Returns:
            合并后的音频文件路径
        """
        # 按句子分割文本
        sentences = (
            text.replace("。", ".|")
            .replace(".", ".|")
            .replace("!", "!|")
            .replace("?", "?|")
            .split("|")
        )
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # 将句子组合成不超过max_length的段落
        chunks = []
        current_chunk = ""
        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= max_length:
                current_chunk += sentence + " "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + " "
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        self.logger.info(f"分为 {len(chunks)} 段进行合成")
        
        # 合成每一段，记录临时文件名
        audio_segments = []
        temp_files = []  # 跟踪实际创建的临时文件
        
        try:
            for i, chunk in enumerate(chunks):
                self.logger.info(f"合成第 {i + 1}/{len(chunks)} 段 ({len(chunk)}字符)...")
                temp_path = str(
                    TEMP_DIR / f"tts_chunk_{i}_{int(time.time() * 1000)}.wav"
                )  # 使用毫秒避免冲突
                self._synthesize_single(chunk, voice, language, temp_path)
                audio_segments.append(AudioSegment.from_wav(temp_path))
                temp_files.append(temp_path)  # 记录实际文件名
            
            # 合并所有音频段
            self.logger.info(f"合并 {len(audio_segments)} 个音频段...")
            combined = audio_segments[0]
            for segment in audio_segments[1:]:
                combined += segment
            
            # 保存合并后的音频
            if not output_path:
                timestamp = int(time.time())
                output_path = str(TEMP_DIR / f"translated_audio_{timestamp}.wav")
            
            combined.export(output_path, format="wav")
            self.logger.info(f"长文本合成完成: {output_path}")
            
        finally:
            # 清理临时文件（使用实际记录的文件名）
            for temp_path in temp_files:
                try:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                        self.logger.debug(f"清理临时文件: {temp_path}")
                except Exception as e:
                    self.logger.warning(f"无法删除临时文件 {temp_path}: {e}")
        
        return output_path
    
    def _download_file(self, url: str, output_path: str) -> None:
        """从URL下载文件
        
        Args:
            url: 文件URL
            output_path: 输出路径
        """
        import requests
        
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
    
    def synthesize_batch(self, texts: list, output_dir: Optional[str] = None) -> list:
        """批量文本转语音
        
        Args:
            texts: 待合成的文本列表
            output_dir: 输出目录
            
        Returns:
            生成的音频文件路径列表
        """
        if not output_dir:
            output_dir = str(TEMP_DIR)
        
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        results = []
        for i, text in enumerate(texts):
            try:
                self.logger.info(f"合成第 {i + 1}/{len(texts)} 个音频...")
                output_path = str(Path(output_dir) / f"batch_audio_{i}_{int(time.time() * 1000)}.wav")
                
                result_path = self.text_to_speech(text, output_path)
                results.append(result_path)
                
            except Exception as e:
                self.logger.error(f"批量合成第 {i + 1} 个音频失败: {e}")
                results.append(None)
        
        return results
    
    def get_audio_info(self, audio_path: str) -> Optional[dict]:
        """获取音频文件信息
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            音频信息字典，如果获取失败则返回None
        """
        try:
            audio = AudioSegment.from_file(audio_path)
            return {
                "duration": len(audio) / 1000.0,  # 秒
                "sample_rate": audio.frame_rate,
                "channels": audio.channels,
                "frame_count": audio.frame_count(),
                "max_dbfs": audio.max_dBFS,
            }
        except Exception as e:
            self.logger.error(f"获取音频信息失败: {e}")
            return None
    
    def convert_audio_format(self, input_path: str, output_path: str, format: str = "wav") -> bool:
        """转换音频格式
        
        Args:
            input_path: 输入音频路径
            output_path: 输出音频路径
            format: 输出格式 (wav, mp3, flac等)
            
        Returns:
            转换是否成功
        """
        try:
            audio = AudioSegment.from_file(input_path)
            audio.export(output_path, format=format)
            self.logger.info(f"音频格式转换完成: {input_path} -> {output_path}")
            return True
        except Exception as e:
            self.logger.error(f"音频格式转换失败: {e}")
            return False
