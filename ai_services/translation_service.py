"""
翻译服务模块
处理文本翻译功能
"""

import time
from typing import Optional, Tuple, List
from openai import OpenAI
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)

from .base_service import BaseAIService
from .service_factory import AIServiceFactory
from config import (
    MT_MODEL,
    MAX_RETRIES,
    SCORING_RESULTS_DIR,
)
from translation_modes import TranslationModeManager, VideoStyle, get_translation_mode
from common.dictionary.translation_dictionary import apply_translation_dictionary
from scores.translation.translation_scores import TranslationScore


class TranslationService(BaseAIService):
    """翻译服务"""
    
    def __init__(self, translation_style: str = "auto"):
        """初始化翻译服务
        
        Args:
            translation_style: 翻译风格
        """
        super().__init__("Translation")
        
        # 验证翻译风格参数
        self.translation_style = self.validate_input(
            translation_style, max_length=50, context="翻译风格"
        )
        
        # 初始化组件
        self.scorer = AIServiceFactory.create_translation_scorer()
        
        # 初始化翻译模式管理器
        self.mode_manager = TranslationModeManager()
        self.mode = get_translation_mode(self.translation_style)
        self.mode_manager.set_mode(self.mode)
        
        # 初始化OpenAI客户端
        self.openai_client = self._init_openai_client()
        
        # 初始化状态
        self._initialized = False
    
    def initialize(self) -> None:
        """初始化翻译服务"""
        if self._initialized:
            return
        
        # 打印初始化状态
        AIServiceFactory.print_initialization_status()
        
        self._initialized = True
        self.logger.info("翻译服务初始化完成")
    
    def _init_openai_client(self) -> OpenAI:
        """初始化OpenAI客户端"""
        from config import DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL
        
        return OpenAI(
            api_key=DASHSCOPE_API_KEY,
            base_url=f"{DASHSCOPE_BASE_URL}/compatible-mode/v1",
            timeout=120.0,  # 120秒超时
        )
    
    def translate_text(
        self, text: str, target_language: str, source_language: str = "auto"
    ) -> str:
        """文本翻译主接口
        
        Args:
            text: 待翻译文本
            target_language: 目标语言
            source_language: 源语言(默认自动检测)
            
        Returns:
            翻译后的文本
            
        Raises:
            Exception: 翻译失败
        """
        # 验证输入
        if not text or not isinstance(text, str):
            raise ValueError("翻译文本参数无效")
        
        if not target_language or not isinstance(target_language, str):
            raise ValueError("目标语言参数无效")
        
        self.logger.info(f"开始翻译到 {target_language}")
        self.logger.info(f"原文长度: {len(text)} 字符")
        
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
            user_message = (
                f"请将以下{source_language}文本翻译成{target_language}：\n\n{text}"
            )
            
            # 获取模型参数
            model_params = current_mode.get_model_params()
            
            self.logger.info(f"使用模式: {current_mode.name}")
            self.logger.info(
                f"模型参数: temperature={model_params.get('temperature', 0.3)}, "
                f"top_p={model_params.get('top_p', 0.8)}"
            )
            
            # 执行翻译
            translated_text = self._call_translation_api(
                system_prompt, user_message, model_params
            )
            
            # 应用翻译词典修正
            corrected_text = self._apply_dictionary_correction(
                translated_text, source_language, target_language
            )
            
            return corrected_text
            
        except Exception as e:
            raise Exception(f"文本翻译失败: {str(e)}") from e
    
    def _call_translation_api(
        self, system_prompt: str, user_message: str, model_params: dict
    ) -> str:
        """调用翻译API
        
        Args:
            system_prompt: 系统提示词
            user_message: 用户消息
            model_params: 模型参数
            
        Returns:
            翻译结果
        """
        # 构建消息（使用正确的OpenAI类型）
        messages: List[ChatCompletionMessageParam] = [
            ChatCompletionSystemMessageParam(role="system", content=system_prompt),
            ChatCompletionUserMessageParam(role="user", content=user_message),
        ]
        
        # 调用Qwen-max API，添加重试机制
        max_retries = 3
        retry_delay = 2  # 秒
        completion = None
        
        for attempt in range(max_retries):
            try:
                completion = self.openai_client.chat.completions.create(
                    model=MT_MODEL, messages=messages, **model_params
                )
                break  # 成功则跳出重试循环
            except Exception as e:
                if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                    if attempt < max_retries - 1:
                        self.logger.warning(
                            f"请求超时，{retry_delay}秒后重试 ({attempt + 1}/{max_retries})"
                        )
                        time.sleep(retry_delay)
                        retry_delay *= 2  # 指数退避
                        continue
                    else:
                        raise Exception(
                            f"翻译请求超时，已重试{max_retries}次: {str(e)}"
                        ) from e
                else:
                    raise  # 非超时错误直接抛出
        
        # 检查completion是否成功获取
        if completion is None:
            raise Exception("翻译API调用失败，未获得响应")
        
        # 安全验证：LLM输出必须立即验证
        try:
            translated_text = self.validate_llm_output(
                completion.choices[0].message.content, "翻译输出"
            )
            self.logger.info("安全验证通过")
        except Exception as e:
            self.logger.error(f"安全验证失败: {e}")
            raise
        
        return translated_text
    
    def _apply_dictionary_correction(
        self, text: str, source_language: str, target_language: str
    ) -> str:
        """应用翻译词典修正
        
        Args:
            text: 翻译文本
            source_language: 源语言
            target_language: 目标语言
            
        Returns:
            修正后的文本
        """
        self.logger.info("应用词典修正...")
        corrected_text = apply_translation_dictionary(
            text,
            source_language=source_language,
            target_language=target_language,
        )
        
        if corrected_text != text:
            self.logger.info(f"词典修正完成,修正后长度: {len(corrected_text)} 字符")
            if len(corrected_text) > 100:
                self.logger.info(f"修正后: {corrected_text[:100]}...")
            else:
                self.logger.info(f"修正后: {corrected_text}")
        else:
            self.logger.info("无需词典修正")
        
        return corrected_text
    
    def evaluate_translation(
        self,
        source_text: str,
        translated_text: str,
        source_language: str,
        target_language: str,
        translation_style: str = "auto",
    ) -> Optional[TranslationScore]:
        """评价翻译质量
        
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
            self.logger.info("翻译质量评分器未启用，跳过评分")
            return None
        
        try:
            score = self.scorer.score_translation(
                source_text,
                translated_text,
                source_language,
                target_language,
                translation_style,
            )
            
            # 保存评分结果
            self._save_score_result(
                source_text,
                translated_text,
                score,
                source_language,
                target_language,
                translation_style,
            )
            
            return score
            
        except Exception as e:
            self.logger.error(f"评价翻译质量失败: {str(e)}")
            return None
    
    def translate_with_retry(
        self,
        text: str,
        target_language: str,
        source_language: str = "auto",
        max_retries: Optional[int] = None,
    ) -> Tuple[str, Optional[TranslationScore]]:
        """带质量评价和重试的翻译方法
        
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
            translated_text = self.translate_text(
                text, target_language, source_language
            )
            return translated_text, None
        
        # 设置最大重试次数
        if max_retries is None:
            max_retries = MAX_RETRIES
        
        best_translation = ""
        best_score = None
        retry_count = 0
        translated_text = ""
        score = None
        
        while retry_count <= max_retries:
            self.logger.info(f"\n[翻译重试] 第 {retry_count + 1} 次尝试...")
            
            # 执行翻译
            if retry_count == 0:
                # 第一次尝试使用正常参数
                translated_text = self.translate_text(
                    text, target_language, source_language
                )
            else:
                # 后续尝试调整参数
                translated_text = self._translate_with_adjusted_params(
                    text, target_language, source_language, retry_count
                )
            
            # 评价翻译质量
            score = self.evaluate_translation(
                text,
                translated_text,
                source_language,
                target_language,
                self.translation_style,
            )
            
            if score is None:
                # 评分失败，但翻译成功
                self.logger.info("评分失败，使用翻译结果")
                return translated_text, None
            
            # 检查是否需要重试
            if not self.scorer.should_retry(score, retry_count):
                self.logger.info("翻译质量达标，无需重试")
                return translated_text, score
            
            # 保存最佳翻译
            if best_score is None or score.overall_score > best_score.overall_score:
                best_translation = translated_text
                best_score = score
            
            # 提供改进建议
            suggestions = self.scorer.provide_improvement_suggestions(score)
            if suggestions:
                self.logger.info("改进建议:")
                for i, suggestion in enumerate(suggestions, 1):
                    self.logger.info(f"  {i}. {suggestion}")
            
            retry_count += 1
        
        # 所有重试都完成，使用最佳结果
        self.logger.info("已达到最大重试次数，使用最佳结果")
        if best_score:
            return best_translation, best_score
        return translated_text, score
    
    def _translate_with_adjusted_params(
        self, text: str, target_language: str, source_language: str, retry_count: int
    ) -> str:
        """使用调整后的参数进行翻译
        
        Args:
            text: 待翻译文本
            target_language: 目标语言
            source_language: 源语言
            retry_count: 重试次数
            
        Returns:
            翻译结果
        """
        self.logger.info("根据重试次数调整翻译参数...")
        
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
            adjusted_params["temperature"] = max(
                0.1, base_params.get("temperature", 0.5) - 0.2
            )
            self.logger.info(f"降低temperature至 {adjusted_params['temperature']:.2f}")
        elif retry_count == 2:
            # 第二次重试，提高temperature，增加创造性
            adjusted_params = base_params.copy()
            adjusted_params["temperature"] = min(
                1.0, base_params.get("temperature", 0.5) + 0.2
            )
            self.logger.info(f"提高temperature至 {adjusted_params['temperature']:.2f}")
        else:
            # 更多重试，使用中等temperature
            adjusted_params = base_params.copy()
            adjusted_params["temperature"] = 0.5
            self.logger.info("设置temperature为 0.5")
        
        # 格式化系统提示词
        system_prompt = self.mode_manager.format_prompt(
            current_mode, source_language, target_language
        )
        
        # 构建用户消息
        user_message = (
            f"请将以下{source_language}文本翻译成{target_language}：\n\n{text}"
        )
        
        # 执行翻译
        translated_text = self._call_translation_api(
            system_prompt, user_message, adjusted_params
        )
        
        # 应用翻译词典修正
        corrected_text = apply_translation_dictionary(
            translated_text,
            source_language=source_language,
            target_language=target_language,
        )
        
        return corrected_text
    
    def _save_score_result(
        self,
        source_text: str,
        translated_text: str,
        score: TranslationScore,
        source_language: str,
        target_language: str,
        translation_style: str,
    ) -> None:
        """保存评分结果
        
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
                    "overall_score": score.overall_score,
                },
                "suggestions": score.suggestions,
                "detailed_feedback": score.detailed_feedback,
                "should_retry": score.should_retry,
            }
            
            # 保存到文件
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(score_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"评分结果已保存: {filepath}")
            
        except Exception as e:
            self.logger.error(f"保存评分结果失败: {str(e)}")
    
    def set_translation_mode(self, style: str) -> None:
        """设置翻译模式
        
        Args:
            style: 翻译风格
        """
        self.translation_style = self.validate_input(
            style, max_length=50, context="翻译风格"
        )
        self.mode = get_translation_mode(self.translation_style)
        self.mode_manager.set_mode(self.mode)
    
    def get_translation_mode_info(self) -> dict:
        """获取当前翻译模式信息"""
        current_mode = self.mode_manager.get_current_mode()
        if not current_mode:
            current_mode = self.mode_manager.get_mode(VideoStyle.AUTO)
        
        return {
            "style": self.translation_style,
            "name": current_mode.name,
            "description": current_mode.description,
            "model_params": current_mode.get_model_params(),
        }
