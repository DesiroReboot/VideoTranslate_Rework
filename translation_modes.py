"""
翻译模式配置模块
支持不同视频类型的翻译风格和参数调优
"""

from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass


class VideoStyle(Enum):
    """视频风格枚举"""

    HUMOROUS = "humorous"  # 幽默风格
    SERIOUS = "serious"  # 正经风格
    EDUCATIONAL = "educational"  # 教育风格
    ENTERTAINMENT = "entertainment"  # 娱乐风格
    NEWS = "news"  # 新闻风格
    AUTO = "auto"  # 自动检测


@dataclass
class TranslationMode:
    """翻译模式配置"""

    name: str
    description: str
    system_prompt: str
    temperature: float
    top_p: float
    max_tokens: Optional[int] = None
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0

    def get_model_params(self) -> Dict[str, Any]:
        """获取模型参数"""
        params = {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "presence_penalty": self.presence_penalty,
            "frequency_penalty": self.frequency_penalty,
        }
        if self.max_tokens:
            params["max_tokens"] = self.max_tokens
        return params


class TranslationModeManager:
    """翻译模式管理器"""

    def __init__(self):
        self.modes = self._initialize_modes()
        self.current_mode = None

    def _initialize_modes(self) -> Dict[VideoStyle, TranslationMode]:
        """初始化所有翻译模式"""
        return {
            VideoStyle.HUMOROUS: TranslationMode(
                name="幽默风格",
                description="适用于搞笑、娱乐类视频，保留幽默感和轻松氛围",
                system_prompt="""##角色及任务
你是专业的视频翻译助手，擅长翻译幽默风趣的内容。你需要将用户的{source_language}文本准确翻译成{target_language}。

##翻译风格要求
1. **保留幽默感**：译文要体现原文的幽默风格，使用目标语言中相应的幽默表达方式
2. **口语化表达**：使用自然、生动的口语化表达，避免过于正式
3. **文化适配**：将幽默元素适配到目标语言的文化背景中
4. **节奏感**：保持原文的节奏感和韵律

##特殊处理规则
1. **适当简洁**：译文要比原文更简洁一些，适合视频配音
2. **过滤不当内容**：遇到粗俗、黄色等不当语义时，应舍弃或委婉表达
3. **事实精准**：遇到事实性语句（如新闻、数据等），必须精准翻译
4. **网络用语**：适当使用目标语言的流行网络用语，增强代入感

##输出要求
- 只输出翻译后的{target_language}文本
- 不要添加任何解释或注释
- 保持原文的段落结构""",
                temperature=0.7,  # 较高温度，增加创造性
                top_p=0.9,
                presence_penalty=0.3,
                frequency_penalty=0.2,
            ),
            VideoStyle.SERIOUS: TranslationMode(
                name="正经风格",
                description="适用于教育、新闻、纪录片等严肃内容，注重准确性和专业性",
                system_prompt="""##角色及任务
你是专业的学术和技术翻译专家。你需要将用户的{source_language}文本准确、专业地翻译成{target_language}。

##翻译风格要求
1. **准确性优先**：确保术语、概念、数据的准确翻译
2. **专业表达**：使用目标语言的专业术语和正式表达方式
3. **逻辑清晰**：保持原文的逻辑结构和论证关系
4. **客观中立**：保持客观、中立的语调

##特殊处理规则
1. **术语一致性**：同一术语在全文中保持一致
2. **数据精准**：数字、日期、单位等必须精确翻译
3. **引用规范**：保持引用格式和标注的规范性
4. **文化中性**：避免文化偏见，保持内容的普适性

##输出要求
- 只输出翻译后的{target_language}文本
- 不要添加任何解释或注释
- 保持原文的段落结构和格式""",
                temperature=0.2,  # 较低温度，确保准确性
                top_p=0.8,
                presence_penalty=0.0,
                frequency_penalty=0.1,
            ),
            VideoStyle.EDUCATIONAL: TranslationMode(
                name="教育风格",
                description="适用于教学、科普类视频，平衡准确性和易懂性",
                system_prompt="""##角色及任务
你是专业的教育内容翻译专家。你需要将用户的{source_language}教育内容清晰、易懂地翻译成{target_language}。

##翻译风格要求
1. **清晰易懂**：使用简单明了的语言，便于学习者理解
2. **概念准确**：确保教育概念和术语的准确翻译
3. **循序渐进**：保持教学内容的逻辑递进关系
4. **互动友好**：使用友好、鼓励性的表达方式

##特殊处理规则
1. **术语解释**：对专业术语可适当添加简短解释
2. **例句适配**：将例句适配到目标语言的文化背景
3. **保持互动**：保留原文中的提问、互动元素
4. **视觉提示**：保留对视觉内容的提示性语言

##输出要求
- 只输出翻译后的{target_language}文本
- 不要添加任何解释或注释
- 保持原文的段落结构""",
                temperature=0.4,
                top_p=0.85,
                presence_penalty=0.1,
                frequency_penalty=0.1,
            ),
            VideoStyle.ENTERTAINMENT: TranslationMode(
                name="娱乐风格",
                description="适用于综艺、访谈等娱乐内容，保持轻松活泼的氛围",
                system_prompt="""##角色及任务
你是专业的娱乐内容翻译专家。你需要将用户的{source_language}娱乐内容生动、有趣地翻译成{target_language}。

##翻译风格要求
1. **生动活泼**：使用富有表现力的语言，保持娱乐性
2. **情感传递**：准确传达原文的情感色彩和氛围
3. **节奏明快**：保持娱乐内容的快节奏和活力
4. **口语化**：使用自然的口语表达，贴近日常交流

##特殊处理规则
1. **笑点保留**：努力保留原文的笑点和幽默元素
2. **情绪词汇**：使用丰富的情绪词汇增强表现力
3. **流行元素**：适当融入目标语言的流行文化元素
4. **互动感**：保持与观众的互动感和参与感

##输出要求
- 只输出翻译后的{target_language}文本
- 不要添加任何解释或注释
- 保持原文的段落结构""",
                temperature=0.6,
                top_p=0.9,
                presence_penalty=0.2,
                frequency_penalty=0.2,
            ),
            VideoStyle.NEWS: TranslationMode(
                name="新闻风格",
                description="适用于新闻报道、时事评论等内容，注重客观性和时效性",
                system_prompt="""##角色及任务
你是专业的新闻翻译专家。你需要将用户的{source_language}新闻内容客观、准确地翻译成{target_language}。

##翻译风格要求
1. **客观准确**：确保新闻事实的准确性和客观性
2. **简洁明了**：使用简洁、清晰的语言表达
3. **时效性强**：保持新闻的时效性和紧迫感
4. **标准规范**：使用标准的新闻写作规范

##特殊处理规则
1. **人名地名**：人名、地名使用标准译法
2. **机构名称**：政府机构、组织名称使用官方译名
3. **数据时间**：数字、日期、时间必须精确
4. **引语处理**：直接引语和间接引语要明确区分

##输出要求
- 只输出翻译后的{target_language}文本
- 不要添加任何解释或注释
- 保持原文的段落结构""",
                temperature=0.1,  # 最低温度，确保客观性
                top_p=0.7,
                presence_penalty=0.0,
                frequency_penalty=0.0,
            ),
            VideoStyle.AUTO: TranslationMode(
                name="自动检测",
                description="自动检测视频风格并选择最适合的翻译模式",
                system_prompt="""##角色及任务
你是智能翻译助手，能够自动识别文本风格并采用相应的翻译策略。你需要将用户的{source_language}文本智能地翻译成{target_language}。

##风格识别与翻译策略
1. **幽默内容**：识别笑话、段子、轻松对话，采用幽默翻译策略
2. **严肃内容**：识别学术、技术、新闻内容，采用准确翻译策略
3. **教育内容**：识别教学、科普内容，采用清晰易懂策略
4. **娱乐内容**：识别综艺、访谈内容，采用生动活泼策略

##通用翻译原则
1. **语境适配**：根据内容类型调整翻译风格
2. **文化转换**：适当进行文化背景的转换和适配
3. **质量平衡**：在准确性和自然性之间找到最佳平衡
4. **用户友好**：确保译文易于理解和接受

##输出要求
- 只输出翻译后的{target_language}文本
- 不要添加任何解释或注释
- 保持原文的段落结构""",
                temperature=0.5,  # 中等温度，平衡准确性和创造性
                top_p=0.85,
                presence_penalty=0.1,
                frequency_penalty=0.1,
            ),
        }

    def get_mode(self, style: VideoStyle) -> TranslationMode:
        """获取指定风格的翻译模式"""
        return self.modes.get(style, self.modes[VideoStyle.AUTO])

    def set_mode(self, style: VideoStyle) -> None:
        """设置当前翻译模式"""
        self.current_mode = self.get_mode(style)
        if self.current_mode:
            print(f"[翻译模式] 切换到: {self.current_mode.name}")
            print(f"[翻译模式] {self.current_mode.description}")
        else:
            print(f"[翻译模式] 警告: 无法找到风格 {style.value} 的模式")

    def get_current_mode(self) -> Optional[TranslationMode]:
        """获取当前翻译模式"""
        return self.current_mode

    def list_modes(self) -> None:
        """列出所有可用的翻译模式"""
        print("\n=== 可用翻译模式 ===")
        for style, mode in self.modes.items():
            print(f"{style.value}: {mode.name} - {mode.description}")
        print("===================\n")

    def format_prompt(
        self, mode: TranslationMode, source_language: str, target_language: str
    ) -> str:
        """格式化系统提示词"""
        return mode.system_prompt.format(
            source_language=source_language, target_language=target_language
        )


# 全局模式管理器实例
mode_manager = TranslationModeManager()


def get_translation_mode(style: str) -> VideoStyle:
    """根据字符串获取视频风格枚举"""
    style_map = {
        "humorous": VideoStyle.HUMOROUS,
        "serious": VideoStyle.SERIOUS,
        "educational": VideoStyle.EDUCATIONAL,
        "entertainment": VideoStyle.ENTERTAINMENT,
        "news": VideoStyle.NEWS,
        "auto": VideoStyle.AUTO,
        "幽默": VideoStyle.HUMOROUS,
        "正经": VideoStyle.SERIOUS,
        "教育": VideoStyle.EDUCATIONAL,
        "娱乐": VideoStyle.ENTERTAINMENT,
        "新闻": VideoStyle.NEWS,
        "自动": VideoStyle.AUTO,
    }
    return style_map.get(style.lower(), VideoStyle.AUTO)
