#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
带缓存的字典包装器
为高频查询的字典项添加内存缓存，减少重复计算
"""

from typing import Dict, Any, Union
from collections import OrderedDict
from .interfaces import IDictionary


class CachedDictionary(IDictionary):
    """带缓存的字典包装器

    包装一个IDictionary实例，为其添加LRU缓存功能
    减少对相同文本的重复处理
    """

    def __init__(self, dictionary: IDictionary, max_cache_size: int = 1000):
        """初始化缓存字典

        Args:
            dictionary: 被包装的字典实例
            max_cache_size: 最大缓存条目数，默认1000
        """
        if not isinstance(dictionary, IDictionary):
            raise TypeError("dictionary must implement IDictionary interface")

        self._dictionary = dictionary
        self._max_cache_size = max_cache_size
        self._cache = OrderedDict()  # LRU缓存
        self._hits = 0
        self._misses = 0

    def apply(
        self, text: str, source_language: str = "auto", target_language: str = "auto"
    ) -> str:
        """应用字典到文本（带缓存）

        Args:
            text: 待处理的文本
            source_language: 源语言 ('zh', 'en', 'auto')
            target_language: 目标语言 ('zh', 'en', 'auto')

        Returns:
            处理后的文本
        """
        # 生成缓存键
        cache_key = (text, source_language, target_language)

        # 检查缓存
        if cache_key in self._cache:
            self._hits += 1
            # 更新访问顺序（移动到最近使用）
            result = self._cache.pop(cache_key)
            self._cache[cache_key] = result
            return result

        # 缓存未命中
        self._misses += 1
        result = self._dictionary.apply(text, source_language, target_language)

        # 添加结果到缓存
        self._cache[cache_key] = result

        # 如果缓存超过最大大小，移除最久未使用的条目
        if len(self._cache) > self._max_cache_size:
            self._cache.popitem(last=False)  # FIFO (最久未使用)

        return result

    def add_entry(self, source: str, target: str, source_lang: str = "auto") -> None:
        """添加字典条目

        添加新条目时清空缓存，因为新条目可能影响处理结果
        """
        # 清空缓存，因为字典内容已变更
        self.clear_cache()
        self._dictionary.add_entry(source, target, source_lang)

    def remove_entry(self, source: str, source_lang: str = "auto") -> bool:
        """删除字典条目

        删除条目时清空缓存，因为字典内容已变更
        """
        # 清空缓存，因为字典内容已变更
        self.clear_cache()
        return self._dictionary.remove_entry(source, source_lang)

    def get_dictionary_stats(self) -> Dict[str, Union[int, float]]:
        """获取字典统计信息（包含缓存统计）

        Returns:
            包含字典条目和缓存统计的字典
        """
        stats = self._dictionary.get_dictionary_stats()
        stats.update(
            {
                "cache_hits": self._hits,
                "cache_misses": self._misses,
                "cache_size": len(self._cache),
                "cache_max_size": self._max_cache_size,
                "cache_hit_rate": self._hits / (self._hits + self._misses)
                if (self._hits + self._misses) > 0
                else 0.0,
            }
        )
        return stats

    def list_entries(
        self, lang_direction: str = "all"
    ) -> Union[Dict[str, str], Dict[str, Dict[str, str]]]:
        """列出字典条目

        Args:
            lang_direction: 语言方向 ('zh_to_en', 'en_to_zh', 'all')

        Returns:
            字典条目字典。当lang_direction为'zh_to_en'或'en_to_zh'时返回Dict[str, str]，
            当为'all'时返回Dict[str, Dict[str, str]]
        """
        return self._dictionary.list_entries(lang_direction)

    def clear_cache(self) -> None:
        """清空缓存"""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    def get_cache_info(self) -> Dict[str, Any]:
        """获取缓存统计信息

        Returns:
            缓存统计信息字典
        """
        return {
            "hits": self._hits,
            "misses": self._misses,
            "size": len(self._cache),
            "max_size": self._max_cache_size,
            "hit_rate": self._hits / (self._hits + self._misses)
            if (self._hits + self._misses) > 0
            else 0.0,
        }

    def _is_chinese_text(self, text: str) -> bool:
        """判断文本是否主要为中文（代理方法）"""
        # 代理到内部字典的方法
        return self._dictionary._is_chinese_text(text)

    def _is_english_text(self, text: str) -> bool:
        """判断文本是否主要为英文（代理方法）"""
        # 代理到内部字典的方法
        return self._dictionary._is_english_text(text)
