#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字典插件管理器
支持不同实现的字典插件注册和获取
"""

from typing import Dict, Optional, Type, Any
from .interfaces import IDictionary


class DictionaryPluginManager:
    """字典插件管理器
    
    管理所有注册的字典插件实例，支持按名称获取
    """
    
    _instance: Optional['DictionaryPluginManager'] = None
    _plugins: Dict[str, IDictionary]
    
    def __new__(cls) -> 'DictionaryPluginManager':
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._plugins = {}
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> 'DictionaryPluginManager':
        """获取插件管理器实例"""
        return cls()
    
    def register_plugin(self, name: str, plugin: IDictionary) -> None:
        """注册字典插件
        
        Args:
            name: 插件名称
            plugin: 字典插件实例
        """
        if not isinstance(plugin, IDictionary):
            raise TypeError(f"插件必须实现IDictionary接口: {name}")
        
        self._plugins[name] = plugin
        print(f"[字典插件] 已注册插件: {name}")
    
    def unregister_plugin(self, name: str) -> bool:
        """注销字典插件
        
        Args:
            name: 插件名称
            
        Returns:
            是否成功注销
        """
        if name in self._plugins:
            del self._plugins[name]
            print(f"[字典插件] 已注销插件: {name}")
            return True
        return False
    
    def get_plugin(self, name: str) -> Optional[IDictionary]:
        """获取字典插件
        
        Args:
            name: 插件名称
            
        Returns:
            字典插件实例，如果不存在则返回None
        """
        return self._plugins.get(name)
    
    def get_default_plugin(self) -> IDictionary:
        """获取默认字典插件
        
        如果没有注册任何插件，则创建一个默认的TranslationDictionary实例
        
        Returns:
            默认字典插件实例
        """
        if not self._plugins:
            from .translation_dictionary import TranslationDictionary
            default_plugin = TranslationDictionary()
            self.register_plugin('default', default_plugin)
            return default_plugin
        
        # 优先返回名为'default'的插件，否则返回第一个插件
        if 'default' in self._plugins:
            return self._plugins['default']
        
        # 返回第一个插件
        first_name = next(iter(self._plugins))
        return self._plugins[first_name]
    
    def list_plugins(self) -> Dict[str, str]:
        """列出所有注册的插件
        
        Returns:
            插件名称到类型名称的映射
        """
        return {name: type(plugin).__name__ for name, plugin in self._plugins.items()}
    
    def clear_plugins(self) -> None:
        """清空所有插件"""
        self._plugins.clear()
        print("[字典插件] 已清空所有插件")


# 全局插件管理器实例
_plugin_manager: Optional[DictionaryPluginManager] = None


def get_plugin_manager() -> DictionaryPluginManager:
    """获取全局插件管理器实例"""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = DictionaryPluginManager()
    return _plugin_manager


def register_dictionary_plugin(name: str, plugin: IDictionary) -> None:
    """注册字典插件（全局函数）
    
    Args:
        name: 插件名称
        plugin: 字典插件实例
    """
    get_plugin_manager().register_plugin(name, plugin)


def get_dictionary_plugin(name: str = 'default') -> Optional[IDictionary]:
    """获取字典插件（全局函数）
    
    Args:
        name: 插件名称，默认为'default'
        
    Returns:
        字典插件实例
    """
    return get_plugin_manager().get_plugin(name)


def get_default_dictionary() -> IDictionary:
    """获取默认字典实例（全局函数）
    
    如果没有注册任何插件，则返回一个默认的TranslationDictionary实例
    
    Returns:
        默认字典实例
    """
    return get_plugin_manager().get_default_plugin()