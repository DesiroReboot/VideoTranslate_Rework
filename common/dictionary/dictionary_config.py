#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
词典配置文件
存放所有词典的配置数据，不包含任何业务逻辑
"""

from typing import Dict, List, Any


class DictionaryConfig:
    """词典配置类

    包含所有词典的配置数据：
    - 精确匹配词典（中文到英文，英文到中文）
    - 正则匹配词典
    - 上下文匹配词典
    - 过滤词典
    - 不翻译列表

    注意：此类只包含数据，不包含任何业务逻辑
    """

    # 精确匹配词典 - 中文到英文
    exact_dict_zh_to_en: Dict[str, str] = {
        "阿SIR": "police",
        "阿sir": "police",
        "阿Sir": "police",
        "警察": "police",
        "警官": "officer",
        "警员": "officer",
        "大佬": "boss",
        "大佬们": "bosses",
        "小弟": "underling",
        "马仔": "henchman",
        "666": "awesome",
        "牛逼": "awesome",
        "厉害": "amazing",
        "给力": "great",
        "兄弟": "brother",
        "哥们": "buddy",
        "姐妹": "sisters",
        "闺蜜": "bestie",
        "医生": "doctor",
        "护士": "nurse",
        "老师": "teacher",
        "学生": "student",
    }

    # 精确匹配词典 - 英文到中文
    exact_dict_en_to_zh: Dict[str, str] = {
        "police": "警察",
        "officer": "警官",
        "boss": "老板",
        "awesome": "厉害",
        "amazing": "惊人",
        "great": "很棒",
        "brother": "兄弟",
        "buddy": "哥们",
        "doctor": "医生",
        "nurse": "护士",
        "teacher": "老师",
        "student": "学生",
    }

    # 正则匹配词典 - 处理变体
    regex_dict: List[Dict[str, str]] = [
        {
            "pattern": "阿[Ss][Ii][Rr]",
            "replacement": "police",
            "description": "阿SIR的各种写法",
        },
        {
            "pattern": "\\b666\\b",
            "replacement": "awesome",
            "description": "单独的数字666",
        },
    ]

    # 上下文相关词典 - 根据上下文判断
    context_dict: List[Dict[str, Any]] = [
        {
            "keywords": ["阿SIR", "警察", "警官"],
            "context_patterns": ["抓", "追", "查", "办案"],
            "translation": "police",
            "description": "执法相关语境",
        }
    ]

    # 过滤词典 - 过滤敏感或不合适的内容，目标语言为空
    filter_dict: Dict[str, str] = {
        "嗯嗯": "",
        "啊啊啊": "",
        "呃呃": "",
        "赶快去拿纸，蹲下就开始": "",
    }

    # 不翻译列表 - 保留原样不翻译
    no_translate_list: List[str] = [
        "iPhone",
        "iPad",
        "MacBook",
        "Windows",
        "QQ",
        "GitHub",
        "emoji",
        "meme",
        "API",
        "URL",
        "HTTP",
        "JSON",
        "CSS",
        "HTML",
        "JavaScript",
        "Python",
        "Java",
        "C++",
        "SQL",
    ]

    # ASR专有名词词典（针对常见识别错误）
    # 用于Fun-ASR的language_hints参数，提高识别准确率
    asr_custom_vocabulary: List[str] = [
        # 媒体/机构名称
        "法新社",
        "新华社",
        "CNN",
        "BBC",
        # 网络用语/梗
        "说唱battle",
        "rap battle",
        "百年战争",
        "fish and chips",
        # 人名/称呼
        "小鹿绅士",
        "法兰西",
        "英格兰",
        # 成语/固定搭配
        "勿谓言之不预也",
        "丢盔弃甲",
        "满地找牙",
        # 可根据需要添加更多专有名词
    ]


# 提供全局配置实例
config = DictionaryConfig()
