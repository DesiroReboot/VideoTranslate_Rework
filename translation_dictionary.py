#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
翻译词典模块
用于处理特定词汇的精确翻译映射
解决模型翻译不准确的问题，如'阿SIR' -> 'police'
"""

from typing import Dict, List, Optional
import re


class TranslationDictionary:
    """翻译词典类
    
    提供中英文词汇的精确映射，用于修正模型翻译结果
    支持多种匹配模式：精确匹配、正则匹配、上下文匹配
    """
    
    def __init__(self):
        """初始化翻译词典"""
        # 精确匹配词典 - 中文到英文
        self.exact_dict_zh_to_en: Dict[str, str] = {
            # 警察相关
            '阿SIR': 'police',
            '阿sir': 'police',
            '阿Sir': 'police',
            '警察': 'police',
            '警官': 'officer',
            '警员': 'officer',
            
            # 常见误译词汇
            '大佬': 'boss',
            '大佬们': 'bosses',
            '小弟': 'underling',
            '马仔': 'henchman',
            
            # 网络用语
            '666': 'awesome',
            '牛逼': 'awesome',
            '厉害': 'amazing',
            '给力': 'great',
            
            # 称呼
            '兄弟': 'brother',
            '哥们': 'buddy',
            '姐妹': 'sisters',
            '闺蜜': 'bestie',
            
            # 职业相关
            '医生': 'doctor',
            '护士': 'nurse',
            '老师': 'teacher',
            '学生': 'student',
        }
        
        # 精确匹配词典 - 中文到英文
        self.exact_dict_zh_to_en: Dict[str, str] = {
            # 警察相关
            '阿SIR': 'police',
            '阿sir': 'police',
            '阿Sir': 'police',
            '警察': 'police',
            '警官': 'officer',
            '警员': 'officer',
            
            # 常见误译词汇
            '大佬': 'boss',
            '大佬们': 'bosses',
            '小弟': 'underling',
            '马仔': 'henchman',
            
            # 网络用语
            '666': 'awesome',
            '牛逼': 'awesome',
            '给力': 'great',
            
            # 称呼
            '兄弟': 'brother',
            '哥们': 'buddy',
            '姐妹': 'sisters',
            '闺蜜': 'bestie',
            
            # 职业相关
            '医生': 'doctor',
            '护士': 'nurse',
            '老师': 'teacher',
            '学生': 'student',
        }
        
        # 精确匹配词典 - 英文到中文
        self.exact_dict_en_to_zh: Dict[str, str] = {
            'police': '警察',
            'officer': '警官',
            'boss': '老板',
            'awesome': '厉害',
            'amazing': '惊人',
            'great': '很棒',
            'brother': '兄弟',
            'buddy': '哥们',
            'doctor': '医生',
            'nurse': '护士',
            'teacher': '老师',
            'student': '学生',
        }
        
        # 正则匹配词典 - 处理变体
        self.regex_dict: List[Dict[str, str]] = [
            # 处理阿SIR的各种变体
            {
                'pattern': r'阿[Ss][Ii][Rr]',
                'replacement': 'police',
                'description': '阿SIR的各种写法'
            },
            # 处理数字+6的组合（只在英文语境中）
            {
                'pattern': r'\b666\b',
                'replacement': 'awesome',
                'description': '单独的数字666'
            },
        ]
        
        # 上下文相关词典 - 根据上下文判断
        self.context_dict: List[Dict] = [
            {
                'keywords': ['阿SIR', '警察', '警官'],
                'context_patterns': [r'抓', r'追', r'查', r'办案'],
                'translation': 'police',
                'description': '执法相关语境'
            }
        ]
    
    def apply_dictionary(self, text: str, source_language: str = 'auto', target_language: str = 'auto') -> str:
        """应用词典到文本
        
        Args:
            text: 待处理的文本
            source_language: 源语言
            target_language: 目标语言
            
        Returns:
            处理后的文本
        """
        if not text:
            return text
        
        # 判断翻译方向
        if source_language in ['zh', 'chinese', '中文'] or self._is_chinese_text(text):
            # 中文到英文
            return self._apply_zh_to_en(text)
        elif source_language in ['en', 'english', '英文'] or self._is_english_text(text):
            # 英文到中文
            return self._apply_en_to_zh(text)
        else:
            # 自动检测
            if self._is_chinese_text(text):
                return self._apply_zh_to_en(text)
            else:
                return self._apply_en_to_zh(text)
    
    def _apply_zh_to_en(self, text: str) -> str:
        """应用中文到英文的词典映射"""
        result = text
        
        # 1. 先应用精确匹配词典（只替换指定的词汇）
        for chinese, english in self.exact_dict_zh_to_en.items():
            # 对于中文，使用字符串直接替换，避免词边界问题
            result = result.replace(chinese, english)
        
        # 2. 再应用正则匹配词典（处理变体）
        for rule in self.regex_dict:
            result = re.sub(rule['pattern'], rule['replacement'], result, flags=re.IGNORECASE)
        
        return result
    
    def _apply_en_to_zh(self, text: str) -> str:
        """应用英文到中文的词典映射"""
        result = text
        
        # 应用精确匹配词典
        for english, chinese in self.exact_dict_en_to_zh.items():
            # 使用词边界确保精确匹配英文单词
            pattern = r'\b' + re.escape(english) + r'\b'
            result = re.sub(pattern, chinese, result, flags=re.IGNORECASE)
        
        # 处理数字666的特殊情况
        result = re.sub(r'\b666\b', 'awesome', result)
        
        return result
    
    def _is_chinese_text(self, text: str) -> bool:
        """判断文本是否主要为中文"""
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        return chinese_chars > len(text) * 0.3
    
    def _is_english_text(self, text: str) -> bool:
        """判断文本是否主要为英文"""
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        return english_chars > len(text) * 0.6
    
    def add_entry(self, source: str, target: str, source_lang: str = 'auto') -> None:
        """添加词典条目
        
        Args:
            source: 源词汇
            target: 目标词汇
            source_lang: 源语言
        """
        if source_lang in ['zh', 'chinese', '中文'] or self._is_chinese_text(source):
            self.exact_dict_zh_to_en[source] = target
        else:
            self.exact_dict_en_to_zh[source] = target
    
    def remove_entry(self, source: str, source_lang: str = 'auto') -> bool:
        """删除词典条目
        
        Args:
            source: 源词汇
            source_lang: 源语言
            
        Returns:
            是否成功删除
        """
        if source_lang in ['zh', 'chinese', '中文'] or self._is_chinese_text(source):
            return self.exact_dict_zh_to_en.pop(source, None) is not None
        else:
            return self.exact_dict_en_to_zh.pop(source, None) is not None
    
    def get_dictionary_stats(self) -> Dict[str, int]:
        """获取词典统计信息"""
        return {
            'zh_to_en_entries': len(self.exact_dict_zh_to_en),
            'en_to_zh_entries': len(self.exact_dict_en_to_zh),
            'regex_rules': len(self.regex_dict),
            'context_rules': len(self.context_dict)
        }
    
    def list_entries(self, lang_direction: str = 'all') -> Dict[str, str]:
        """列出词典条目
        
        Args:
            lang_direction: 语言方向 ('zh_to_en', 'en_to_zh', 'all')
            
        Returns:
            词典条目字典
        """
        if lang_direction == 'zh_to_en':
            return self.exact_dict_zh_to_en.copy()
        elif lang_direction == 'en_to_zh':
            return self.exact_dict_en_to_zh.copy()
        else:
            return {
                'zh_to_en': self.exact_dict_zh_to_en.copy(),
                'en_to_zh': self.exact_dict_en_to_zh.copy()
            }


# 全局词典实例
_global_dictionary: Optional[TranslationDictionary] = None


def get_translation_dictionary() -> TranslationDictionary:
    """获取全局翻译词典实例"""
    global _global_dictionary
    if _global_dictionary is None:
        _global_dictionary = TranslationDictionary()
    return _global_dictionary


def apply_translation_dictionary(text: str, source_language: str = 'auto', target_language: str = 'auto') -> str:
    """应用翻译词典到文本
    
    Args:
        text: 待处理的文本
        source_language: 源语言 ('zh', 'en', 'auto')
        target_language: 目标语言 ('zh', 'en', 'auto')
        
    Returns:
        处理后的文本
    """
    dictionary = get_translation_dictionary()
    
    # 改进的语言判断逻辑
    if source_language == 'auto':
        # 使用词典实例的语言检测方法
        if dictionary._is_chinese_text(text):
            source_language = 'zh'
        elif dictionary._is_english_text(text):
            source_language = 'en'
        else:
            # 如果无法明确判断，默认按中文处理
            source_language = 'zh'
    
    if target_language == 'auto':
        # 如果源语言是中文，目标语言是英文，反之亦然
        target_language = 'en' if source_language == 'zh' else 'zh'
    
    print(f"[词典] 检测到源语言: {source_language}, 目标语言: {target_language}")
    
    return dictionary.apply_dictionary(text, source_language, target_language)


if __name__ == '__main__':
    # 测试词典功能
    dictionary = TranslationDictionary()
    
    # 测试用例
    test_cases = [
        '阿SIR来了',
        '这个阿sir很厉害',
        '警察正在追捕嫌疑人',
        '666太厉害了',
        'The police are coming',
        'This is awesome'
    ]
    
    print('翻译词典测试:')
    print('=' * 50)
    
    for test_text in test_cases:
        result = dictionary.apply_dictionary(test_text)
        print(f'原文: {test_text}')
        print(f'结果: {result}')
        print('-' * 30)
    
    # 显示统计信息
    stats = dictionary.get_dictionary_stats()
    print(f'\n词典统计: {stats}')