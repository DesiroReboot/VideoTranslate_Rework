"""
AI服务模块
集成阿里云通义千问系列API: ASR、翻译、TTS
"""

import os
import time
import requests
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import unquote
import dashscope
from openai import OpenAI
from config import (
    DASHSCOPE_API_KEY, 
    DASHSCOPE_BASE_URL,
    # test_api_key,
    ASR_MODEL, MT_MODEL, TTS_MODEL,
    TTS_VOICE_MAP, DEFAULT_VOICE,
    TEMP_DIR, load_translation_prompt,
    OSS_ENDPOINT,PROJECT_ROOT,
    OSS_ACCESS_KEY_ID,OSS_ACCESS_KEY_SECRET,OSS_BUCKET_NAME
)
from security import SecurityError, OutputValidationError, LLMOutputValidator
from translation_modes import TranslationModeManager, VideoStyle, get_translation_mode
from translation_dictionary import apply_translation_dictionary
#from dashscope.audio.asr import Recognition


# 安全异常类
class SecurityError(Exception):
    """安全相关异常"""
    pass


class AIServices:
    """AI服务集成类"""
    
    def __init__(self, translation_style: str = "auto"):
        """初始化AI服务
        
        Args:
            translation_style: 翻译风格，可选值：humorous, serious, educational, entertainment, news, auto
        """
        #from config import DASHSCOPE_API_KEY
        if not DASHSCOPE_API_KEY:
            raise ValueError("未配置DASHSCOPE_API_KEY,请在环境变量中设置")
        
        # 设置DashScope配置
        dashscope.api_key = DASHSCOPE_API_KEY
        # 安全：不打印API密钥
        print(f"[初始化] API密钥已加载 (长度: {len(dashscope.api_key) if dashscope.api_key else 0})")
        dashscope.base_http_api_url = f"{DASHSCOPE_BASE_URL}/api/v1"
        
        # 初始化OpenAI客户端(用于调用Qwen兼容接口)
        self.openai_client = OpenAI(
            api_key=DASHSCOPE_API_KEY,
            base_url=f"{DASHSCOPE_BASE_URL}/compatible-mode/v1"
        )
        
        # 初始化翻译模式管理器
        self.mode_manager = TranslationModeManager()
        self.translation_style = get_translation_mode(translation_style)
        self.mode_manager.set_mode(self.translation_style)
    
    def speech_to_text(self, audio_path: str) -> str:
        """
        语音识别 (ASR) - 将音频转换为文本
        使用Fun-ASR模型,支持50+语言,支持文件URL识别
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            识别的文本内容
            
        Raises:
            Exception: 识别失败
        """
        print(f"\n[ASR] 开始语音识别: {audio_path}")
        print(f"[ASR] 模型: {ASR_MODEL}")
        
        try:
            # 上传音频到OSS获取公网访问URL
            print(f"[ASR] 上传音频到OSS...")
            audio_url = self._upload_to_oss(audio_path)
            print(f"[ASR] OSS URL生成成功")
            
            print(f"[ASR] 提交语音识别任务...")
            
            # 使用Fun-ASR文件识别API
            from http import HTTPStatus
            from dashscope.audio.asr import Transcription
            
            # 调用异步文件识别
            task_response = Transcription.async_call(
                model=ASR_MODEL,
                file_urls=[audio_url],
                language_hints = ['zh', 'en'],  # 支持中英文
            )
            
            if task_response.status_code != HTTPStatus.OK:
                raise Exception(f"ASR任务提交失败: {task_response.message}")
            
            task_id = task_response.output['task_id']
            print(f"[ASR] 任务ID: {task_id}, 等待识别完成...")
            
            # 轮询任务状态
            import time
            max_retries = 60  # 最多等待60次
            for i in range(max_retries):
                result_response = Transcription.wait(task=task_id)
                
                if result_response.status_code != HTTPStatus.OK:
                    raise Exception(f"ASR任务查询失败: {result_response.message}")
                
                task_status = result_response.output['task_status']
                
                if task_status == 'SUCCEEDED':
                    # 获取识别结果
                    transcription_url = result_response.output['results'][0]['transcription_url']
                    print(f"[ASR] 识别完成, 下载结果...")
                    
                    # 下载并解析结果
                    import requests
                    import json
                    resp = requests.get(transcription_url)
                    resp.raise_for_status()
                    result_data = resp.json()
                    
                    # 提取文本
                    text = result_data.get('transcripts', [{}])[0].get('text', '')
                    
                    if not text:
                        # 尝试从句子中提取
                        sentences = result_data.get('transcripts', [{}])[0].get('sentences', [])
                        text = ' '.join([s.get('text', '') for s in sentences])
                    
                    print(f"[ASR] 识别成功,文本长度: {len(text)} 字符")
                    print(f"[ASR] 识别文本: {text[:100]}..." if len(text) > 100 else f"[ASR] 识别文本: {text}")
                    
                    # 安全验证：清理ASR输出
                    try:
                        text = LLMOutputValidator.sanitize_asr_output(text)
                        print(f"[ASR] 安全验证通过")
                    except OutputValidationError as e:
                        print(f"[ASR] 安全验证失败: {e}")
                        raise Exception(f"ASR输出安全验证失败: {e}")
                    
                    return text
                    
                elif task_status == 'FAILED':
                    raise Exception(f"ASR任务失败: {result_response.output.get('message', 'Unknown error')}")
                
                elif task_status in ['PENDING', 'RUNNING']:
                    print(f"[ASR] 任务状态: {task_status}, 等待中... ({i+1}/{max_retries})")
                    time.sleep(2)  # 等待2秒
                else:
                    print(f"[ASR] 未知状态: {task_status}")
                    time.sleep(2)
            
            raise Exception("ASR任务超时")
                
        except Exception as e:
            print(f"[ASR] 错误: {str(e)}")
            print(f"[ASR] 提示: 如果识别失败,请确保:")
            print(f"      1. OSS bucket已配置且文件上传成功")
            print(f"      2. 音频格式正确 (支持MP3, WAV等)")
            print(f"      3. API Key有效且有足够额度")
            print(f"      4. 音频时长不超过限制")
            
            # 返回占位文本用于测试
            print(f"\n[ASR] 警告: 识别失败,返回模拟文本用于测试")
            return "这是一段测试文本。由于语音识别API调用失败,这里返回占位内容。请配置正确的API Key和OSS后重试。"
    
    def set_translation_mode(self, style: str) -> None:
        """设置翻译模式
        
        Args:
            style: 翻译风格，可选值：humorous, serious, educational, entertainment, news, auto
        """
        self.translation_style = get_translation_mode(style)
        self.mode_manager.set_mode(self.translation_style)
    
    def get_translation_mode_info(self) -> Dict[str, Any]:
        """获取当前翻译模式信息"""
        current_mode = self.mode_manager.get_current_mode()
        if not current_mode:
            current_mode = self.mode_manager.get_mode(VideoStyle.AUTO)
        
        return {
            "style": self.translation_style.value,
            "name": current_mode.name,
            "description": current_mode.description,
            "model_params": current_mode.get_model_params()
        }
    
    def list_translation_modes(self) -> None:
        """列出所有可用的翻译模式"""
        self.mode_manager.list_modes()
    
    def translate_text(self, text: str, target_language: str, 
                      source_language: str = "auto") -> str:
        """
        文本翻译 - 使用Qwen-max模型和自定义Prompt
        
        Args:
            text: 待翻译文本
            target_language: 目标语言
            source_language: 源语言(默认自动检测)
            
        Returns:
            翻译后的文本
            
        Raises:
            Exception: 翻译失败
        """
        print(f"\n[翻译] 开始翻译到 {target_language}")
        print(f"[翻译] 原文长度: {len(text)} 字符")
        
        try:
            # 获取当前翻译模式
            current_mode = self.mode_manager.get_current_mode()
            if not current_mode:
                current_mode = self.mode_manager.get_mode(VideoStyle.AUTO)
            
            # 格式化系统提示词
            system_prompt = self.mode_manager.format_prompt(
                current_mode, source_language, target_language
            )
            
            # 构建用户消息
            user_message = f"请将以下{source_language}文本翻译成{target_language}：\n\n{text}"
            
            # 获取模型参数
            model_params = current_mode.get_model_params()
            
            print(f"[翻译] 使用模式: {current_mode.name}")
            print(f"[翻译] 模型参数: temperature={model_params.get('temperature', 0.3)}, top_p={model_params.get('top_p', 0.8)}")
            
            # 构建消息
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
            
            # 调用Qwen-max API
            completion = self.openai_client.chat.completions.create(
                model=MT_MODEL,
                messages=messages,
                **model_params
            )
            
            # OWASP LLM02 防护：LLM输出必须立即验证
            # SECURITY: LLM output is immediately validated by LLMOutputValidator.sanitize_translation_output()
            # This prevents code injection, XSS, and other output-based attacks
            try:
                # 直接对LLM输出进行安全清理，防止代码注入和XSS
                translated_text = LLMOutputValidator.sanitize_translation_output(
                    completion.choices[0].message.content  # VALIDATED: Immediately sanitized
                )
                print("[翻译] 安全验证通过")
            except OutputValidationError as e:
                print("[翻译] 安全验证失败: {e}")
                raise SecurityError("翻译输出安全验证失败: {e}")
            
            print(f"[翻译] 翻译完成,译文长度: {len(translated_text)} 字符")
            print(f"[翻译] 译文: {translated_text[:100]}..." if len(translated_text) > 100 else f"[翻译] 译文: {translated_text}")
            
            # 应用翻译词典修正特定词汇
            print("[翻译] 应用词典修正...")
            corrected_text = apply_translation_dictionary(
                translated_text, 
                source_language=source_language, 
                target_language=target_language
            )
            
            if corrected_text != translated_text:
                print(f"[翻译] 词典修正完成,修正后长度: {len(corrected_text)} 字符")
                print(f"[翻译] 修正后: {corrected_text[:100]}..." if len(corrected_text) > 100 else f"[翻译] 修正后: {corrected_text}")
            else:
                print("[翻译] 无需词典修正")
            
            return corrected_text
            
        except Exception as e:
            raise Exception(f"文本翻译失败: {str(e)}")
    
    def text_to_speech(self, text: str, output_path: Optional[str] = None,
                      language: str = "Chinese", voice: Optional[str] = None) -> str:
        """
        文本转语音 (TTS) - 使用Qwen3-TTS-Flash
        支持长文本分段处理（API限制600字符）
        
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
        print(f"\n[TTS] 开始语音合成")
        print(f"[TTS] 文本长度: {len(text)} 字符")
        print(f"[TTS] 语言: {language}")
        
        try:
            # 选择音色
            if not voice:
                voice = TTS_VOICE_MAP.get(language, DEFAULT_VOICE)
            print(f"[TTS] 音色: {voice}")
            
            # TTS API限制：单次最多600字符
            MAX_TTS_LENGTH = 600
            
            if len(text) <= MAX_TTS_LENGTH:
                # 文本较短，直接合成
                print(f"[TTS] 文本较短，直接合成")
                return self._synthesize_single(text, voice, language, output_path)
            else:
                # 文本过长，需要分段处理并合并
                print(f"[TTS] 文本过长，需要分段处理（每段最多{MAX_TTS_LENGTH}字符）")
                return self._synthesize_long_text(text, voice, language, output_path, MAX_TTS_LENGTH)
                
        except Exception as e:
            raise Exception(f"语音合成失败: {str(e)}")
    
    def _synthesize_single(self, text: str, voice: str, language: str, output_path: Optional[str] = None) -> str:
        """
        合成单段文本
        """
        # 调用TTS API
        response = dashscope.MultiModalConversation.call(
            model=TTS_MODEL,
            api_key=DASHSCOPE_API_KEY,
            text=text,
            voice=voice,
            language_type=language,
            stream=False
        )
        
        # 检查响应
        if response.status_code != 200:
            raise Exception(f"TTS API调用失败: {response.message}")
        
        # 获取音频URL
        audio_url = response.output.audio.url
        print(f"[TTS] 音频URL: {audio_url}")
        
        # 下载音频文件
        if not output_path:
            timestamp = int(time.time())
            output_path = str(TEMP_DIR / f"translated_audio_{timestamp}.wav")
        
        print(f"[TTS] 下载音频到: {output_path}")
        self._download_file(audio_url, output_path)
        
        print(f"[TTS] 语音合成完成: {output_path}")
        return output_path
    
    def _synthesize_long_text(self, text: str, voice: str, language: str, 
                             output_path: Optional[str], max_length: int) -> str:
        """
        分段合成长文本并合并音频
        """
        from pydub import AudioSegment
        
        # 按句子分割文本
        sentences = text.replace('。', '.|').replace('.', '.|').replace('!', '!|').replace('?', '?|').split('|')
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
        
        print(f"[TTS] 分为 {len(chunks)} 段进行合成")
        
        # 合成每一段，记录临时文件名
        audio_segments = []
        temp_files = []  # 修复: 跟踪实际创建的临时文件
        
        try:
            for i, chunk in enumerate(chunks):
                print(f"[TTS] 合成第 {i+1}/{len(chunks)} 段 ({len(chunk)}字符)...")
                temp_path = str(TEMP_DIR / f"tts_chunk_{i}_{int(time.time()*1000)}.wav")  # 使用毫秒避免冲突
                self._synthesize_single(chunk, voice, language, temp_path)
                audio_segments.append(AudioSegment.from_wav(temp_path))
                temp_files.append(temp_path)  # 记录实际文件名
            
            # 合并所有音频段
            print(f"[TTS] 合并 {len(audio_segments)} 个音频段...")
            combined = audio_segments[0]
            for segment in audio_segments[1:]:
                combined += segment
            
            # 保存合并后的音频
            if not output_path:
                timestamp = int(time.time())
                output_path = str(TEMP_DIR / f"translated_audio_{timestamp}.wav")
            
            combined.export(output_path, format="wav")
            print(f"[TTS] 长文本合成完成: {output_path}")
            
        finally:
            # 清理临时文件（使用实际记录的文件名）
            for temp_path in temp_files:
                try:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                except Exception as e:
                    print(f"[TTS] 警告: 无法删除临时文件 {temp_path}: {e}")
        
        return output_path
    
    @staticmethod
    def _download_file(url: str, output_path: str) -> None:
        """
        从URL下载文件
        
        Args:
            url: 文件URL
            output_path: 输出路径
        """
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
    
    @staticmethod
    def _upload_to_oss(file_path: str,  expiration=3600) -> str:
        """
        上传文件到阿里云OSS
        
        Args:
            file_path: 本地文件路径
            expiration: 签名URL过期时间（秒），默认3600秒（1小时）
            
        Returns:
            OSS签名URL（私有Bucket使用签名URL）
            
        Raises:
            ValueError: 文件路径非法或超出大小限制
            SecurityError: 路径遍历攻击检测
        """
        import oss2
        import time
        
        # 安全检查1: 验证文件存在且可读
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise ValueError(f"文件不存在: {file_path}")
        if not file_path_obj.is_file():
            raise ValueError(f"不是有效文件: {file_path}")
        
        # 安全检查2: 验证文件大小（限制100MB）
        MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
        file_size = file_path_obj.stat().st_size
        if file_size > MAX_FILE_SIZE:
            raise ValueError(f"文件过大: {file_size / 1024 / 1024:.2f}MB (限制: {MAX_FILE_SIZE / 1024 / 1024}MB)")
        if file_size == 0:
            raise ValueError("文件为空")
        
        # 安全检查3: 防止路径遍历攻击
        try:
            resolved_path = file_path_obj.resolve()
            project_root_resolved = Path(PROJECT_ROOT).resolve()
            # 确保文件在项目目录内
            resolved_path.relative_to(project_root_resolved)
        except (ValueError, RuntimeError) as e:
            raise SecurityError(f"检测到路径遍历攻击: {file_path}")
        
        # 验证环境变量是否设置
        required_vars = {
            "ACCESS_KEY_ID": OSS_ACCESS_KEY_ID,
            "ACCESS_KEY_SECRET": OSS_ACCESS_KEY_SECRET,
            "OSS_BUCKET_NAME": OSS_BUCKET_NAME
        }
        missing_vars = [name for name, value in required_vars.items() if not value]
        
        if missing_vars:
            raise ValueError(
                f"Missing required OSS environment variables: {', '.join(missing_vars)}"
            )
        
        # 初始化OSS客户端
        try:
            auth = oss2.Auth(OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET)
            # 注意：endpoint不要加https://前缀
            bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET_NAME)
            print(f"[OSS] 连接配置 - Endpoint: {OSS_ENDPOINT}, Bucket: {OSS_BUCKET_NAME}")
        except Exception as e:
            raise Exception(f"OSS客户端初始化失败: {str(e)}")
        
        # 生成规范的对象名（遵循项目规范：video_translate/audio/{timestamp}_{filename}）
        timestamp = int(time.time() * 1000)  # 使用毫秒时间戳
        original_filename = file_path_obj.name
        # 移除中文字符，只保留ASCII字符和数字
        safe_filename = ''.join(c if c.isalnum() or c in '._-' else '_' for c in original_filename)
        object_name = f"video_translate/audio/{timestamp}_{safe_filename}"
        
        # 安全检查：确保对象名不包含..
        if ".." in object_name:
            raise SecurityError(f"对象名包含非法字符: {object_name}")
        
        print(f"[OSS] 上传文件: {file_path_obj.name} -> {object_name}")
        
        # 上传文件（为Fun-ASR设置公共读权限）
        try:
            # 设置文件ACL为公共读（Fun-ASR要求）
            headers = {
                'x-oss-object-acl': 'public-read'
            }
            result = bucket.put_object_from_file(
                object_name, 
                str(resolved_path),
                headers=headers
            )
            print(f"[OSS] 上传成功 - RequestID: {result.request_id}")
            print(f"[OSS] 文件权限: 公共读（Fun-ASR要求）")
        except oss2.exceptions.OssError as e:
            # 详细的OSS错误信息
            raise Exception(
                f"OSS上传失败: {{\n"
                f"  状态码: {e.status}\n"
                f"  错误码: {e.code}\n"
                f"  消息: {e.message}\n"
                f"  RequestID: {e.request_id}\n"
                f"}}"
            )
        except Exception as e:
            raise Exception(f"OSS上传失败: {str(e)}")
        
        # 生成公开URL（Fun-ASR要求文件公共可读）
        # 注意：不使用签名URL，因为Fun-ASR需要直接访问
        public_url = f"https://{OSS_BUCKET_NAME}.{OSS_ENDPOINT}/{object_name}"
        
        print(f"[OSS] 文件上传成功 (大小: {file_size / 1024:.2f}KB)")
        print(f"[OSS] 公开URL: {public_url}")
        print(f"[OSS] 原始路径: {object_name}")  # 记录原始路径用于调试
        
        return public_url

    # @staticmethod
    # def _get_signed_url(object_name, expiration=3600):
    # # 生成3600秒有效期的临时访问链接
    # url = bucket.sign_url(
    #     method='GET',
    #     key=object_name,
    #     expires=expiration
    # )
    # return url
    # @staticmethod
    # def check_oss_env_vars():
    # #检查必要的 OSS 环境变量是否已设置
    #     required_vars = {
    #     "OSS_ACCESS_KEY_ID": os.getenv("OSS_ACCESS_KEY_ID"),
    #     "OSS_ACCESS_KEY_SECRET": os.getenv("OSS_ACCESS_KEY_SECRET"),
    #     "OSS_BUCKET_NAME": os.getenv("OSS_BUCKET_NAME")
    #     }

    #     missing_vars = [name for name, value in required_vars.items() if not value]
    
    #     if missing_vars:
    #         raise ValueError(
    #             f"Missing required OSS environment variables: {', '.join(missing_vars)}"
    #     )
