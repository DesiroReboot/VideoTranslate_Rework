"""
API 数据模型
定义API请求和响应的数据结构
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime


class TranslationMode(str, Enum):
    """翻译模式枚举"""
    AUTO = "auto"
    HUMOROUS = "humorous"
    SERIOUS = "serious"
    EDUCATIONAL = "educational"
    ENTERTAINMENT = "entertainment"
    NEWS = "news"


class TranslationStatusEnum(str, Enum):
    """翻译状态枚举"""
    IDLE = "idle"
    READY = "ready"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"
    STOPPED = "stopped"


class EventTypeEnum(str, Enum):
    """事件类型枚举 - 用于SSE推送"""
    PROGRESS = "progress"
    LOG = "log"
    STATUS = "status"
    ASR_CONFIRM_REQUIRED = "asr_confirm_required"
    TRANSLATION_CONFIRM_REQUIRED = "translation_confirm_required"
    COMPLETED = "completed"
    ERROR = "error"
    STOPPED = "stopped"


# ==================== 请求模型 ====================

class StartTranslationRequest(BaseModel):
    """开始翻译请求"""
    input_value: str = Field(..., description="视频输入 - BV号、URL或本地文件路径")
    target_language_code: str = Field(default="zh", description="目标语言显示名称")
    mode: TranslationMode = Field(default=TranslationMode.AUTO, description="翻译模式")


class ConfirmAsrRequest(BaseModel):
    """确认ASR结果请求"""
    task_id: str = Field(..., description="任务ID")
    confirmed_text: str = Field(..., description="用户确认的文本")


class ConfirmTranslationRequest(BaseModel):
    """确认翻译结果请求"""
    task_id: str = Field(..., description="任务ID")
    confirmed_text: str = Field(..., description="用户确认的文本")


class StopTranslationRequest(BaseModel):
    """停止翻译请求"""
    task_id: str = Field(..., description="任务ID")


# ==================== 响应模型 ====================

class StartTranslationResponse(BaseModel):
    """开始翻译响应"""
    success: bool
    task_id: str
    message: str


class TranslationStatusResponse(BaseModel):
    """翻译状态响应"""
    task_id: str
    status: TranslationStatusEnum
    message: str
    current_step: int
    total_steps: int
    progress: float


class LogResponse(BaseModel):
    """日志条目响应"""
    timestamp: str
    message: str


class TranslationResultResponse(BaseModel):
    """翻译完成结果响应"""
    task_id: str
    success: bool
    output_file: Optional[str] = None
    error_message: Optional[str] = None


# ==================== 事件模型 (用于SSE) ====================

class TranslationProgressEvent(BaseModel):
    """进度更新事件"""
    event_type: EventTypeEnum = EventTypeEnum.PROGRESS
    current_step: int
    total_steps: int
    message: str
    progress: float


class LogEvent(BaseModel):
    """日志事件"""
    event_type: EventTypeEnum = EventTypeEnum.LOG
    timestamp: str
    message: str


class AsrConfirmRequiredEvent(BaseModel):
    """ASR确认请求事件"""
    event_type: EventTypeEnum = EventTypeEnum.ASR_CONFIRM_REQUIRED
    task_id: str
    text: str
    alternative_text: Optional[str] = None
    coefficient: float
    threshold: float


class TranslationConfirmRequiredEvent(BaseModel):
    """翻译确认请求事件"""
    event_type: EventTypeEnum = EventTypeEnum.TRANSLATION_CONFIRM_REQUIRED
    task_id: str
    text: str
    score: Optional[float] = None
    suggestions: Optional[List[str]] = None


class CompletedEvent(BaseModel):
    """完成事件"""
    event_type: EventTypeEnum = EventTypeEnum.COMPLETED
    task_id: str
    output_file: str


class ErrorEvent(BaseModel):
    """错误事件"""
    event_type: EventTypeEnum = EventTypeEnum.ERROR
    task_id: str
    message: str


class StoppedEvent(BaseModel):
    """停止事件"""
    event_type: EventTypeEnum = EventTypeEnum.STOPPED
    task_id: str
    message: str


class StatusEvent(BaseModel):
    """状态更新事件"""
    event_type: EventTypeEnum = EventTypeEnum.STATUS
    task_id: str
    status: TranslationStatusEnum
    message: str


# ==================== 任务状态模型 ====================

class TaskState(BaseModel):
    """任务状态"""
    task_id: str
    status: TranslationStatusEnum
    input_value: str
    target_language_code: str
    mode: TranslationMode
    current_step: int
    total_steps: int
    progress: float
    message: str
    created_at: datetime
    logs: List[str] = []
    
    # 确认相关数据
    asr_data: Optional[Dict[str, Any]] = None
    asr_confirmed: bool = False
    translation_text: Optional[str] = None
    translation_confirmed: bool = False
    output_file: Optional[str] = None
    error_message: Optional[str] = None
