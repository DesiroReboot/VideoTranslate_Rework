# 翻译模式使用指南

## 概述

本项目新增了多风格翻译模式功能，支持根据不同视频类型选择最适合的翻译风格和模型参数，显著提升翻译质量和用户体验。

## 支持的翻译风格

### 1. 幽默风格 (humorous)
- **适用场景**: 搞笑视频、段子、轻松对话
- **特点**: 保留幽默感，使用口语化表达，文化适配
- **模型参数**: temperature=0.7, top_p=0.9, 较高创造性

### 2. 正经风格 (serious)
- **适用场景**: 教育、新闻、纪录片等严肃内容
- **特点**: 准确性优先，专业表达，逻辑清晰
- **模型参数**: temperature=0.2, top_p=0.8, 低温度确保准确性

### 3. 教育风格 (educational)
- **适用场景**: 教学、科普类视频
- **特点**: 清晰易懂，概念准确，循序渐进
- **模型参数**: temperature=0.4, top_p=0.85, 平衡准确性和易懂性

### 4. 娱乐风格 (entertainment)
- **适用场景**: 综艺、访谈等娱乐内容
- **特点**: 生动活泼，情感传递，节奏明快
- **模型参数**: temperature=0.6, top_p=0.9, 保持娱乐性

### 5. 新闻风格 (news)
- **适用场景**: 新闻报道、时事评论
- **特点**: 客观准确，简洁明了，标准规范
- **模型参数**: temperature=0.1, top_p=0.7, 最低温度确保客观性

### 6. 自动检测 (auto)
- **适用场景**: 自动识别内容类型
- **特点**: 智能识别，语境适配，质量平衡
- **模型参数**: temperature=0.5, top_p=0.85, 中等温度平衡性

## 使用方法

### 命令行使用

```bash
# 基本用法（自动风格）
python main.py "https://www.bilibili.com/video/BVxxxxxxxxx" English

# 指定幽默风格
python main.py "video.mp4" English Chinese humorous

# 教育视频使用教育风格
python main.py "education_video.mp4" English auto educational

# 新闻视频使用新闻风格
python main.py "news_report.mp4" English Chinese news
```

### 参数说明

- `视频URL或路径`: 支持B站视频链接或本地视频文件路径
- `目标语言`: 翻译目标语言（如：English, Japanese, Korean等）
- `源语言`: 可选，默认为auto自动检测
- `翻译风格`: 可选，默认为auto自动检测

## 代码集成使用

### 基本用法

```python
from ai_services import AIServices

# 创建AI服务实例，指定翻译风格
ai_service = AIServices("humorous")  # 幽默风格

# 获取当前模式信息
mode_info = ai_service.get_translation_mode_info()
print(f"当前模式: {mode_info['name']}")
print(f"描述: {mode_info['description']}")

# 执行翻译
translated_text = ai_service.translate_text(
    original_text, 
    source_language="Chinese", 
    target_language="English"
)
```

### 动态切换模式

```python
# 切换到教育风格
ai_service.set_translation_mode("educational")

# 列出所有可用模式
ai_service.list_translation_modes()

# 获取当前模式信息
current_mode = ai_service.get_translation_mode_info()
```

## 实际应用示例

### 示例1: 搞笑视频翻译

```bash
# 翻译搞笑视频，保留幽默感
python main.py "funny_video.mp4" English Chinese humorous
```

**效果**: 译文会保留原文的幽默元素，使用目标语言中相应的幽默表达方式。

### 示例2: 教育课程翻译

```bash
# 翻译教学视频，注重准确性
python main.py "python_course.mp4" English Chinese educational
```

**效果**: 译文会确保专业术语的准确性，同时保持清晰易懂。

### 示例3: 新闻报道翻译

```bash
# 翻译新闻视频，保持客观性
python main.py "news_report.mp4" English Chinese news
```

**效果**: 译文会保持客观准确的语调，确保事实信息的正确传达。

## 技术实现

### 模型参数调优

每种翻译风格都经过精心调优的模型参数：

- **Temperature**: 控制输出的创造性，幽默风格较高(0.7)，新闻风格较低(0.1)
- **Top P**: 控制词汇选择的多样性，通常在0.7-0.9之间
- **Presence Penalty**: 鼓励新话题，幽默风格设置为0.3
- **Frequency Penalty**: 减少重复，幽默风格设置为0.2

### 提示词工程

每种风格都有专门的系统提示词：
- 明确定义翻译角色和任务
- 详细的风格要求和处理规则
- 针对性的输出格式要求

## 测试验证

运行测试脚本验证功能：

```bash
python test_translation_modes.py
```

测试内容包括：
- 风格获取函数测试
- 模式管理器测试
- 所有翻译模式功能测试

## 注意事项

1. **风格选择**: 根据视频内容类型选择合适的翻译风格
2. **参数调优**: 不同风格的参数已经过优化，一般无需手动调整
3. **质量监控**: 建议在使用新风格时先进行小规模测试
4. **文化适配**: 系统会自动进行文化背景的转换和适配

## 更新日志

### v1.1.0
- 新增6种翻译风格支持
- 优化模型参数配置
- 增强提示词工程
- 添加命令行参数支持
- 完善测试覆盖

## 贡献指南

欢迎提交新的翻译风格建议和改进意见：
1. 分析目标视频类型的特点
2. 设计相应的翻译策略
3. 调优模型参数
4. 编写测试用例
5. 提交Pull Request