#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分布式共识模块
"""

from .distributed_asr import (
    DistributedASRConsensus,
    ASRResult,
    ConsensusResult,
    TextQualityEvaluator,
)

__all__ = [
    "DistributedASRConsensus",
    "ASRResult",
    "ConsensusResult",
    "TextQualityEvaluator",
]
