#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字典模块
提供翻译词典接口、缓存和插件支持
"""

from .interfaces import IDictionary
from .translation_dictionary import TranslationDictionary, get_translation_dictionary, apply_translation_dictionary
from .cached_dictionary import CachedDictionary
from .plugin_manager import DictionaryPluginManager, get_plugin_manager, register_dictionary_plugin, get_dictionary_plugin, get_default_dictionary
from .dictionary_config import DictionaryConfig, config

__all__ = [
    'IDictionary',
    'TranslationDictionary',
    'CachedDictionary',
    'DictionaryPluginManager',
    'DictionaryConfig',
    'config',
    'get_translation_dictionary',
    'apply_translation_dictionary',
    'get_plugin_manager',
    'register_dictionary_plugin',
    'get_dictionary_plugin',
    'get_default_dictionary'
]