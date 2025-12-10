@echo off
chcp 65001 >nul
echo ========================================
echo 视频翻译系统 - 单元测试运行器
echo ========================================
echo.

REM 检查Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ✗ 未找到 Python!
    pause
    exit /b 1
)

REM 运行测试
echo 开始运行测试...
echo.

python run_tests.py %*

echo.
pause
