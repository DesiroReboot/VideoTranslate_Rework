#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频翻译系统UI入口
启动PyQt5图形界面
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
# app.py现在在项目根目录，所以parent就是项目根目录
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from ui.src.main_window import main

if __name__ == "__main__":
    main()
