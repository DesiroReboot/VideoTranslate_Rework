"""
AI服务工厂模块
统一管理所有AI服务的创建和初始化
"""

from typing import Optional
from config import (
    ENABLE_DISTRIBUTED_ASR,
    DISTRIBUTED_ASR_NODE_COUNT,
    DISTRIBUTED_ASR_COEFFICIENT_THRESHOLD,
    DISTRIBUTED_ASR_ENABLE_QUALITY_EVAL,
    ENABLE_ASR_SCORING,
    ENABLE_TRANSLATION_SCORING,
)
from scores.ASR.asr_scorer import AsrScorer
from scores.translation.translation_scores import TranslationScorer


class AIServiceFactory:
    """AI服务工厂类 - 统一管理所有服务的创建"""
    
    @staticmethod
    def create_distributed_asr() -> Optional[object]:
        """创建分布式ASR共识机制
        
        Returns:
            分布式ASR实例，如果禁用则返回None
        """
        if ENABLE_DISTRIBUTED_ASR:
            from common.consensus import DistributedASRConsensus
            
            return DistributedASRConsensus(
                node_count=DISTRIBUTED_ASR_NODE_COUNT,
                coefficient_threshold=DISTRIBUTED_ASR_COEFFICIENT_THRESHOLD,
                enable_quality_eval=DISTRIBUTED_ASR_ENABLE_QUALITY_EVAL,
            )
        return None
    
    @staticmethod
    def create_asr_scorer() -> Optional[AsrScorer]:
        """创建ASR评分器
        
        Returns:
            ASR评分器实例，如果禁用则返回None
        """
        if ENABLE_ASR_SCORING:
            return AsrScorer()
        return None
    
    @staticmethod
    def create_translation_scorer() -> Optional[TranslationScorer]:
        """创建翻译评分器
        
        Returns:
            翻译评分器实例，如果禁用则返回None
        """
        if ENABLE_TRANSLATION_SCORING:
            return TranslationScorer()
        return None
    
    @staticmethod
    def print_initialization_status():
        """打印所有服务的初始化状态"""
        print("[初始化] AI服务工厂状态检查:")
        
        # ASR相关
        if ENABLE_DISTRIBUTED_ASR:
            print(f"[初始化] 分布式ASR已启用 ({DISTRIBUTED_ASR_NODE_COUNT}节点)")
        else:
            print("[初始化] 分布式ASR已禁用")
        
        if ENABLE_ASR_SCORING:
            print("[初始化] ASR质量评分器已启用")
        else:
            print("[初始化] ASR质量评分器已禁用")
        
        # 翻译相关
        if ENABLE_TRANSLATION_SCORING:
            print("[初始化] 翻译质量评分器已启用")
        else:
            print("[初始化] 翻译质量评分器已禁用")
