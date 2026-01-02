#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pytest配置文件
提供测试fixtures和配置
"""

import sys
import os
from pathlib import Path

# 将项目根目录添加到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest


@pytest.fixture(scope="session")
def test_data_dir():
    """测试数据目录"""
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def output_dir():
    """测试输出目录"""
    output = Path(__file__).parent.parent / "output" / "tests"
    output.mkdir(parents=True, exist_ok=True)
    return output


@pytest.fixture(scope="function")
def mock_env_vars(monkeypatch):
    """模拟环境变量"""
    env_vars = {
        "DASHSCOPE_API_KEY": "test_api_key_12345",
        "OSS_ACCESS_KEY_ID": "test_oss_key_id",
        "OSS_ACCESS_KEY_SECRET": "test_oss_secret",
        "OSS_BUCKET_NAME": "test-bucket",
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    return env_vars


@pytest.fixture(scope="function")
def temp_output_file(output_dir):
    """创建临时输出文件"""
    def _make_file(extension: str = "txt") -> Path:
        import tempfile
        import uuid
        filename = f"temp_{uuid.uuid4().hex[:8]}.{extension}"
        return output_dir / filename
    return _make_file
