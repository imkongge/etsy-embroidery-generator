@echo off
setlocal enabledelayedexpansion

title Etsy

echo ========================================
echo  Etsy
echo ========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [error] no python
    pause
    exit /b 1
)

pip install streamlit pillow openai --quiet 2>nul

echo.
echo starting...
python -m streamlit run main_app.py --server.port 8502

pause
