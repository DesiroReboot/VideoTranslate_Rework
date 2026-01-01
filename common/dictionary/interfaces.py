#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字典接口定义
支持不同实现的字典插件
"""

from abc import ABC, abstractmethod
from typing import Dict, Union


class IDictionary(ABC):
    """字典接口基类

    所有字典插件必须实现此接口
    """

    @abstractmethod
    def apply(
        self, text: str, source_language: str = "auto", target_language: str = "auto"
    ) -> str:
        """应用字典到文本

        Args:
            text: 待处理的文本
            source_language: 源语言 ('zh', 'en', 'auto')
            target_language: 目标语言 ('zh', 'en', 'auto')

        Returns:
            处理后的文本
        """
        pass

    @abstractmethod
    def add_entry(self, source: str, target: str, source_lang: str = "auto") -> None:
        """添加字典条目

        Args:
            source: 源词汇
            target: 目标词汇
            source_lang: 源语言
        """
        pass

    @abstractmethod
    def remove_entry(self, source: str, source_lang: str = "auto") -> bool:
        """删除字典条目

        Args:
            source: 源词汇
            source_lang: 源语言

        Returns:
            是否成功删除
        """
        pass

    @abstractmethod
    def get_dictionary_stats(self) -> Dict[str, Union[int, float]]:
        """获取字典统计信息

        Returns:
            包含各类条目数量的字典
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def _is_chinese_text(self, text: str) -> bool:
        """判断文本是否为中文"""
        pass

    @abstractmethod
    def _is_english_text(self, text: str) -> bool:
        """判断文本是否为英文"""
        pass
