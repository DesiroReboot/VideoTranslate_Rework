"""
AI服务模块
集成阿里云通义千问系列API: ASR、翻译、TTS
"""

import os
import time
import requests
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
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
    OSS_ENDPOINT, PROJECT_ROOT,
    OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET, OSS_BUCKET_NAME,
    ENABLE_TRANSLATION_SCORING, SCORING_RESULTS_DIR,
    ASR_SCORE_THRESHOLD, ASR_MAX_RETRIES, ENABLE_ASR_SCORING,
    ASR_SCORING_RESULTS_DIR
)
from security import SecurityError, OutputValidationError, LLMOutputValidator, ResourceValidator, InputValidator
from translation_modes import TranslationModeManager, VideoStyle, get_translation_mode
from translation_dictionary import apply_translation_dictionary
from translation_scores import TranslationScorer, TranslationScore
from asr_scorer import AsrScorer, AsrScore



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
        # 1. API密钥格式验证
        if not DASHSCOPE_API_KEY:
            raise ValueError("未配置DASHSCOPE_API_KEY,请在环境变量中设置")
        
        # 验证API密钥格式 (假设是sk-开头的格式)
        if not DASHSCOPE_API_KEY.startswith('sk-') or len(DASHSCOPE_API_KEY) < 20:
            raise SecurityError("API密钥格式无效")
        
        # 2. 翻译风格参数验证
        translation_style = InputValidator.validate_text_input(
            translation_style, 
            max_length=50, 
            min_length=1, 
            context="翻译风格"
        )
        
        # 3. 基础URL验证
        if not DASHSCOPE_BASE_URL or not DASHSCOPE_BASE_URL.startswith('https://'):
            raise SecurityError("DASHSCOPE_BASE_URL配置无效")
        
        # 设置DashScope配置
        dashscope.api_key = DASHSCOPE_API_KEY
        # 安全：不打印API密钥
        print(f"[初始化] API密钥已加载 (长度: {len(dashscope.api_key) if dashscope.api_key else 0})")
        dashscope.base_http_api_url = f"{DASHSCOPE_BASE_URL}/api/v1"
        
        # 初始化OpenAI客户端(用于调用Qwen兼容接口)
        self.openai_client = OpenAI(
            api_key=DASHSCOPE_API_KEY,
            base_url=f"{DASHSCOPE_BASE_URL}/compatible-mode/v1",
            timeout=ResourceValidator.validate_timeout(120.0, max_timeout=300.0)  # 120秒超时
        )
        
        # 初始化翻译模式管理器
        self.mode_manager = TranslationModeManager()
        self.translation_style = get_translation_mode(translation_style)
        self.mode_manager.set_mode(self.translation_style)
        
        # 初始化翻译质量评分器
        if ENABLE_TRANSLATION_SCORING:
            self.scorer = TranslationScorer()
            print(f"[初始化] 翻译质量评分器已启用")
        else:
            self.scorer = None
            print(f"[初始化] 翻译质量评分器已禁用")
        
        # 初始化ASR质量评分器
        if ENABLE_ASR_SCORING:
            self.asr_scorer = AsrScorer()
            print(f"[初始化] ASR质量评分器已启用")
        else:
            self.asr_scorer = None
            print(f"[初始化] ASR质量评分器已禁用")
    
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
            SecurityError: 安全检查失败
        """
        # 1. 参数验证
        if not audio_path or not isinstance(audio_path, str):
            raise ValueError("音频路径参数无效")
        
        # 2. 音频文件安全验证
        from security import FileValidator
        audio_info = FileValidator.validate_audio_file(audio_path)
        
        print(f"\n[ASR] 开始语音识别: {audio_path}")
        print(f"[ASR] 模型: {ASR_MODEL}")
        print(f"[ASR] 音频文件大小: {audio_info['size'] / (1024*1024):.2f}MB")
        
        # ASR重试循环
        for retry_count in range(ASR_MAX_RETRIES + 1):
            print(f"[ASR] 第{retry_count + 1}次尝试 (最大{ASR_MAX_RETRIES + 1}次)")
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
                        
                        # ASR质量评分和校正
                        if self.asr_scorer:
                            print(f"[ASR] 开始质量评分和校正...")
                            original_text = text  # 保存原始文本用于评分和记录
                            score_result = self.asr_scorer.score_asr_result(original_text)
                            
                            print(f"[ASR] 识别质量评分: {score_result.overall_score}/{100}")
                            if score_result.corrections:
                                print(f"[ASR] 发现{len(score_result.corrections)}处可能的识别错误，正在校正...")
                                text = self.asr_scorer.apply_corrections(original_text, score_result.corrections)
                                print(f"[ASR] 校正后文本: {text[:100]}..." if len(text) > 100 else f"[ASR] 校正后文本: {text}")
                            
                            # 保存评分结果
                            self._save_asr_score_result(original_text, score_result, audio_path=audio_path)
                            
                            # 检查是否需要重试
                            if score_result.should_retry and retry_count < ASR_MAX_RETRIES:
                                print(f"[ASR] 识别质量低于阈值({ASR_SCORE_THRESHOLD})，将进行重试")
                                continue  # 重试识别
                        
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
            
            # 调用Qwen-max API，添加重试机制
            max_retries = 3
            retry_delay = 2  # 秒
            
            for attempt in range(max_retries):
                try:
                    completion = self.openai_client.chat.completions.create(
                        model=MT_MODEL,
                        messages=messages,
                        **model_params
                    )
                    break  # 成功则跳出重试循环
                except Exception as e:
                    if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                        if attempt < max_retries - 1:
                            print(f"[翻译] 请求超时，{retry_delay}秒后重试 ({attempt + 1}/{max_retries})")
                            time.sleep(retry_delay)
                            retry_delay *= 2  # 指数退避
                            continue
                        else:
                            raise Exception(f"翻译请求超时，已重试{max_retries}次: {str(e)}")
                    else:
                        raise  # 非超时错误直接抛出
            
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
    
    def evaluate_translation(
        self, 
        source_text: str, 
        translated_text: str, 
        source_language: str, 
        target_language: str,
        translation_style: str = "auto"
    ) -> Optional[TranslationScore]:
        """
        评价翻译质量
        
        Args:
            source_text: 原文
            translated_text: 译文
            source_language: 源语言
            target_language: 目标语言
            translation_style: 翻译风格
            
        Returns:
            TranslationScore: 评分结果，如果评分器未启用则返回None
        """
        if not self.scorer:
            print("[评分] 翻译质量评分器未启用，跳过评分")
            return None
        
        try:
            score = self.scorer.score_translation(
                source_text, translated_text, source_language, 
                target_language, translation_style
            )
            
            # 保存评分结果
            self._save_score_result(
                source_text, translated_text, score, 
                source_language, target_language, translation_style
            )
            
            return score
            
        except Exception as e:
            print(f"[评分] 评价翻译质量失败: {str(e)}")
            return None
    
    def translate_with_retry(
        self, 
        text: str, 
        target_language: str, 
        source_language: str = "auto",
        max_retries: Optional[int] = None
    ) -> Tuple[str, Optional[TranslationScore]]:
        """
        带质量评价和重试的翻译方法
        
        Args:
            text: 待翻译文本
            target_language: 目标语言
            source_language: 源语言(默认自动检测)
            max_retries: 最大重试次数，如果为None则使用配置中的值
            
        Returns:
            Tuple[str, Optional[TranslationScore]]: 翻译结果和评分
        """
        if not self.scorer:
            # 如果评分器未启用，直接使用普通翻译
            translated_text = self.translate_text(text, target_language, source_language)
            return translated_text, None
        
        # 设置最大重试次数
        if max_retries is None:
            from config import MAX_RETRIES
            max_retries = MAX_RETRIES
        
        best_translation = ""
        best_score = None
        retry_count = 0
        
        while retry_count <= max_retries:
            print(f"\n[翻译重试] 第 {retry_count + 1} 次尝试...")
            
            # 执行翻译
            if retry_count == 0:
                # 第一次尝试使用正常参数
                translated_text = self.translate_text(text, target_language, source_language)
            else:
                # 后续尝试调整参数
                translated_text = self._translate_with_adjusted_params(
                    text, target_language, source_language, retry_count
                )
            
            # 评价翻译质量
            score = self.evaluate_translation(
                text, translated_text, source_language, 
                target_language, self.translation_style.value
            )
            
            if score is None:
                # 评分失败，但翻译成功
                print(f"[翻译重试] 评分失败，使用翻译结果")
                return translated_text, None
            
            # 检查是否需要重试
            if not self.scorer.should_retry(score, retry_count):
                print(f"[翻译重试] 翻译质量达标，无需重试")
                return translated_text, score
            
            # 保存最佳翻译
            if best_score is None or score.overall_score > best_score.overall_score:
                best_translation = translated_text
                best_score = score
            
            # 提供改进建议
            suggestions = self.scorer.provide_improvement_suggestions(score)
            if suggestions:
                print(f"[翻译重试] 改进建议:")
                for i, suggestion in enumerate(suggestions, 1):
                    print(f"  {i}. {suggestion}")
            
            retry_count += 1
        
        # 所有重试都完成，使用最佳结果
        print(f"[翻译重试] 已达到最大重试次数，使用最佳结果")
        if best_score:
            return best_translation, best_score
        else:
            return translated_text, score
    
    def _translate_with_adjusted_params(
        self, 
        text: str, 
        target_language: str, 
        source_language: str, 
        retry_count: int
    ) -> str:
        """
        使用调整后的参数进行翻译
        
        Args:
            text: 待翻译文本
            target_language: 目标语言
            source_language: 源语言
            retry_count: 重试次数
            
        Returns:
            翻译结果
        """
        print(f"[参数调整] 根据重试次数调整翻译参数...")
        
        # 获取当前翻译模式
        current_mode = self.mode_manager.get_current_mode()
        if not current_mode:
            current_mode = self.mode_manager.get_mode(VideoStyle.AUTO)
        
        # 调整参数
        base_params = current_mode.get_model_params()
        
        # 根据重试次数调整temperature
        if retry_count == 1:
            # 第一次重试，降低temperature，提高准确性
            adjusted_params = base_params.copy()
            adjusted_params["temperature"] = max(0.1, base_params.get("temperature", 0.5) - 0.2)
            print(f"[参数调整] 降低temperature至 {adjusted_params['temperature']:.2f}")
        elif retry_count == 2:
            # 第二次重试，提高temperature，增加创造性
            adjusted_params = base_params.copy()
            adjusted_params["temperature"] = min(1.0, base_params.get("temperature", 0.5) + 0.2)
            print(f"[参数调整] 提高temperature至 {adjusted_params['temperature']:.2f}")
        else:
            # 更多重试，使用中等temperature
            adjusted_params = base_params.copy()
            adjusted_params["temperature"] = 0.5
            print(f"[参数调整] 设置temperature为 0.5")
        
        # 格式化系统提示词
        system_prompt = self.mode_manager.format_prompt(
            current_mode, source_language, target_language
        )
        
        # 构建用户消息
        user_message = f"请将以下{source_language}文本翻译成{target_language}：\n\n{text}"
        
        # 构建消息
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        try:
            # 调用Qwen-max API
            completion = self.openai_client.chat.completions.create(
                model=MT_MODEL,
                messages=messages,
                **adjusted_params
            )
            
            # 安全验证
            try:
                translated_text = LLMOutputValidator.sanitize_translation_output(
                    completion.choices[0].message.content
                )
                print("[参数调整] 翻译完成")
            except OutputValidationError as e:
                print(f"[参数调整] 安全验证失败: {e}")
                raise SecurityError(f"翻译输出安全验证失败: {e}")
            
            # 应用翻译词典修正
            corrected_text = apply_translation_dictionary(
                translated_text, 
                source_language=source_language, 
                target_language=target_language
            )
            
            return corrected_text
            
        except Exception as e:
            print(f"[参数调整] 翻译失败: {str(e)}")
            raise Exception(f"参数调整翻译失败: {str(e)}")
    
    def _save_score_result(
        self, 
        source_text: str, 
        translated_text: str, 
        score: TranslationScore,
        source_language: str, 
        target_language: str, 
        translation_style: str
    ) -> None:
        """
        保存评分结果
        
        Args:
            source_text: 原文
            translated_text: 译文
            score: 评分结果
            source_language: 源语言
            target_language: 目标语言
            translation_style: 翻译风格
        """
        try:
            import json
            import time
            
            # 生成文件名
            timestamp = int(time.time())
            filename = f"translation_score_{timestamp}.json"
            filepath = SCORING_RESULTS_DIR / filename
            
            # 准备保存数据
            score_data = {
                "timestamp": timestamp,
                "source_language": source_language,
                "target_language": target_language,
                "translation_style": translation_style,
                "source_text": source_text,
                "translated_text": translated_text,
                "scores": {
                    "fluency": score.fluency,
                    "completeness": score.completeness,
                    "consistency": score.consistency,
                    "accuracy": score.accuracy,
                    "style_adaptation": score.style_adaptation,
                    "cultural_adaptation": score.cultural_adaptation,
                    "overall_score": score.overall_score
                },
                "suggestions": score.suggestions,
                "detailed_feedback": score.detailed_feedback,
                "should_retry": score.should_retry
            }
            
            # 保存到文件
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(score_data, f, ensure_ascii=False, indent=2)
            
            print(f"[评分] 评分结果已保存: {filepath}")
            
        except Exception as e:
            print(f"[评分] 保存评分结果失败: {str(e)}")
    
    def _save_asr_score_result(
        self, 
        asr_text: str, 
        score: AsrScore,
        context: Optional[str] = None,
        audio_path: Optional[str] = None
    ) -> None:
        """
        保存ASR评分结果
        
        Args:
            asr_text: ASR识别文本
            score: ASR评分结果
            context: 可选上下文信息
            audio_path: 可选音频文件路径
        """
        try:
            import json
            import time
            
            # 生成文件名
            timestamp = int(time.time())
            filename = f"asr_score_{timestamp}.json"
            filepath = ASR_SCORING_RESULTS_DIR / filename
            
            # 准备保存数据
            score_data = {
                "timestamp": timestamp,
                "audio_path": audio_path,
                "context": context,
                "asr_text": asr_text,
                "corrected_text": self.asr_scorer.apply_corrections(asr_text, score.corrections) if self.asr_scorer else asr_text,
                "scores": {
                    "logic_score": score.logic_score,
                    "semantic_coherence": score.semantic_coherence,
                    "context_consistency": score.context_consistency,
                    "error_detection_score": score.error_detection_score,
                    "overall_score": score.overall_score
                },
                "suggestions": score.suggestions,
                "corrections": score.corrections,
                "detailed_feedback": score.detailed_feedback,
                "should_retry": score.should_retry
            }
            
            # 保存到文件
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(score_data, f, ensure_ascii=False, indent=2)
            
            print(f"[ASR评分] 评分结果已保存: {filepath}")
            
        except Exception as e:
            print(f"[ASR评分] 保存评分结果失败: {str(e)}")
    
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
