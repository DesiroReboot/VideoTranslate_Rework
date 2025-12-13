"""
AI服务模块
集成阿里云通义千问系列API: ASR、翻译、TTS
"""

import os
import time
import requests
from pathlib import Path
from typing import Optional, Dict, Any
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
#from dashscope.audio.asr import Recognition


class AIServices:
    """AI服务集成类"""
    
    def __init__(self):
        """初始化AI服务"""
        #from config import DASHSCOPE_API_KEY
        if not DASHSCOPE_API_KEY:
            raise ValueError("未配置DASHSCOPE_API_KEY,请在环境变量中设置")
        
        # 设置DashScope配置
        dashscope.api_key = DASHSCOPE_API_KEY
        print(f"DEBUG: DASHSCOPE_API_KEY = {repr(dashscope.api_key)}")
        dashscope.base_http_api_url = f"{DASHSCOPE_BASE_URL}/api/v1"
        
        # 初始化OpenAI客户端(用于调用Qwen兼容接口)
        self.openai_client = OpenAI(
            api_key=DASHSCOPE_API_KEY,
            base_url=f"{DASHSCOPE_BASE_URL}/compatible-mode/v1"
        )
    
    def speech_to_text(self, audio_path: str) -> str:
        """
        语音识别 (ASR) - 将音频转换为文本
        使用SenseVoice模型,支持50+语言
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            识别的文本内容
            
        Raises:
            Exception: 识别失败
        """
        print(f"\n[ASR] 开始语音识别: {audio_path}")
        print(f"[ASR] 注意: 需要先上传音频到可访问的URL")
        
        try:
            # SenseVoice需要文件通过公网URL访问
            # 这里提供两种方案:
            
            # 方案1: 使用文件URL (需要先上传到OSS等云存储)
            # 由于本地文件无法直接访问,这里使用异步任务API
            
            print(f"[ASR] 提交语音识别任务...")
            
            # 使用异步任务API提交识别
            from dashscope.audio.asr import Recognition
            
            # 注意: 实际使用时需要将音频上传到OSS获取公网URL
            # 这里简化处理,使用同步API (仅支持较短音频)
            recognition = Recognition(model=ASR_MODEL, api_key=DASHSCOPE_API_KEY)
            
            # 读取音频文件
            with open(audio_path, 'rb') as f:
                audio_data = f.read()
            
            # 调用识别API (使用文件内容)
            result = recognition.call(
                format='mp3',
                sample_rate=16000,
                audio=audio_data
            )
            
            if result.status_code == 200:
                # 解析结果
                text = result.output.get('text', '')
                if not text and 'results' in result.output:
                    # 尝试从results中提取文本
                    results = result.output.get('results', [])
                    text = ' '.join([r.get('text', '') for r in results])
                
                print(f"[ASR] 识别成功,文本长度: {len(text)} 字符")
                print(f"[ASR] 识别文本: {text[:100]}..." if len(text) > 100 else f"[ASR] 识别文本: {text}")
                return text
            else:
                raise Exception(f"ASR识别失败: {result.message}")
                
        except Exception as e:
            print(f"[ASR] 错误: {str(e)}")
            print(f"[ASR] 提示: 如果识别失败,请确保:")
            print(f"      1. 音频格式正确 (支持MP3, WAV等)")
            print(f"      2. API Key有效且有足够额度")
            print(f"      3. 音频时长不超过限制")
            
            # 返回占位文本用于测试
            print(f"\n[ASR] 警告: 识别失败,返回模拟文本用于测试")
            return "这是一段测试文本。由于语音识别API调用失败,这里返回占位内容。请配置正确的API Key和上传音频到OSS后重试。"
    
    def translate_text(self, text: str, target_language: str, 
                      source_language: str = "auto") -> str:
        """
        文本翻译 - 使用Qwen-MT模型
        
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
        #print(f"[翻译]原文：{text}")
        
        try:
            # 加载系统提示词
            system_prompt = load_translation_prompt(target_language)
            #print(f"[翻译]system prompt:{system_prompt}")
            user_content = f"{system_prompt}\n\n{text}"
            #print(f"[翻译]user context:{user_content}")
            
            # 构建消息
            messages = [
                # {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
                #{"role": "user", "content": user_content}
            ]
            
            # 调用Qwen-MT API
            completion = self.openai_client.chat.completions.create(
                model=MT_MODEL,
                messages=messages,
                extra_body={
                    "translation_options": {
                        "source_lang": source_language,
                        "target_lang": target_language,
                    }
                }
            )
            
            translated_text = completion.choices[0].message.content
            print(f"[翻译] 翻译完成,译文长度: {len(translated_text)} 字符")
            print(f"[翻译] 译文: {translated_text[:100]}..." if len(translated_text) > 100 else f"[翻译] 译文: {translated_text}")
            
            return translated_text
            
        except Exception as e:
            raise Exception(f"文本翻译失败: {str(e)}")
    
    def text_to_speech(self, text: str, output_path: Optional[str] = None,
                      language: str = "Chinese", voice: Optional[str] = None) -> str:
        """
        文本转语音 (TTS) - 使用Qwen3-TTS-Flash
        
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
            
        except Exception as e:
            raise Exception(f"语音合成失败: {str(e)}")
    
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
        上传文件到阿里云OSS (待实现)
        
        Args:
            file_path: 本地文件路径
            
        Returns:
            OSS公网URL
            
        注意:
            实际使用时需要:
            1. pip install oss2
            2. 配置OSS bucket和credentials
            3. 上传文件并返回公网URL
        """
        # TODO: 实现OSS上传
        import oss2
        # auth = oss2.Auth(access_key_id, access_key_secret)
        # bucket = oss2.Bucket(auth, endpoint, bucket_name)
        # result = bucket.put_object_from_file(object_name, file_path)
        # return f"https://{bucket_name}.{endpoint}/{object_name}"
        # 从环境变量获取安全凭证（推荐！）   
        # access_key_id = os.getenv("OSS_ACCESS_KEY_ID")
        # access_key_secret = os.getenv("OSS_ACCESS_KEY_SECRET")
        # oss_bucket_name = os.getenv("OSS_BUCKET_NAME")
        #endpoint = os.getenv("OSS_ENDPOINT", "oss-cn-hangzhou.aliyuncs.com")  # 默认杭州
        #endpoint = os.getenv("OSS_ENDPOINT")
        # endpoint = OSS_ENDPOINT

    # 验证环境变量是否设置
        required_vars={
            "ACCESS_KEY_ID": OSS_ACCESS_KEY_ID,
            "ACCESS_KEY_SECRET": OSS_ACCESS_KEY_SECRET,
            "OSS_BUCKET_NAME": OSS_BUCKET_NAME
            #OSS_ACCESS_KEY_ID,OSS_ACCESS_KEY_SECRET,OSS_BUCKET_NAME,OSS_ENDPOINT
        }
        missing_vars = [name for name, value in required_vars.items() if not value]
    
        if missing_vars:
            raise ValueError(
                f"Missing required OSS environment variables: {', '.join(missing_vars)}"
        )

    # 初始化OSS客户端
        auth = oss2.Auth(OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET)
        bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET_NAME)

    # 上传文件
        if file_path:
            relative_path = os.path.relpath(file_path, PROJECT_ROOT)
            object_name = relative_path.replace("\\", "/")
        bucket.put_object_from_file(object_name, file_path)
    
    # 返回可公开访问的URL（注意：Bucket必须是Public Read才能直接访问）
    # 如果Bucket是Private，需生成签名URL（见下文）
        #return f"https://{bucket_name}.{endpoint}/{object_name}"
        return bucket.sign_url(
        method='GET',
        key=object_name,
        expires=expiration
    )
        
        # raise NotImplementedError(
        #     "需要配置阿里云OSS用于音频上传\n"
        #     "请参考文档: https://help.aliyun.com/document_detail/32026.html"
        # )

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
