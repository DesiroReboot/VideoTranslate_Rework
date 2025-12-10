@echo off
chcp 65001 >nul
echo ========================================
echo 视频翻译系统 - 快速安装脚本
echo ========================================
echo.

echo [1/4] 检查 Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ✗ 未找到 Python! 请先安装 Python 3.8+
    echo   下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)
python --version
echo ✓ Python 已安装
echo.

echo [2/4] 检查 FFmpeg...
ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    echo ✗ 未找到 FFmpeg!
    echo   请下载并安装: https://ffmpeg.org/download.html
    echo   并添加到系统 PATH 环境变量
    pause
    exit /b 1
)
echo ✓ FFmpeg 已安装
echo.

echo [3/4] 安装 Python 依赖...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ✗ 依赖安装失败!
    pause
    exit /b 1
)
echo ✓ 依赖安装完成
echo.

echo [4/4] 检查配置...
if not defined DASHSCOPE_API_KEY (
    echo ⚠ 警告: 未配置 DASHSCOPE_API_KEY!
    echo.
    echo 请按以下步骤配置:
    echo 1. 访问 https://dashscope.console.aliyun.com/
    echo 2. 获取 API Key
    echo 3. 在 PowerShell 中运行:
    echo    setx DASHSCOPE_API_KEY "your_api_key_here"
    echo 4. 重启命令提示符
    echo.
) else (
    echo ✓ API Key 已配置
)

echo.
echo ========================================
echo ✓ 安装完成!
echo ========================================
echo.
echo 使用方法:
echo   python main.py "视频URL或路径" 目标语言
echo.
echo 示例:
echo   python main.py test.mp4 English
echo   python main.py "https://www.bilibili.com/video/BVxxx" Japanese
echo.
echo 更多示例请运行:
echo   python examples.py
echo.
pause
