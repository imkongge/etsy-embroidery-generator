@echo off
chcp 65001 >nul
title Etsy 刺绣预览工具

echo ========================================
echo   Etsy 刺绣名字预览工具 - 启动程序
echo ========================================
echo.

python --version >nul 2>&1
if %errorlevel% == 0 (
    echo [OK] 检测到 Python 已安装
    goto CHECK_PIP
)

py --version >nul 2>&1
if %errorlevel% == 0 (
    echo [OK] 检测到 Python Launcher
    set PYTHON_CMD=py
    goto CHECK_PIP
)

echo [!] 未检测到 Python，准备自动下载安装...
echo.

set "PYTHON_INSTALLER=%TEMP%\python_installer.exe"

if exist "%ProgramFiles(x86)%" (
    set "PYTHON_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
) else (
    set "PYTHON_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9.exe"
)

echo [下载] 正在下载 Python 3.11.9...
echo 请稍候，这可能需要几分钟...
echo.

powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('%PYTHON_URL%', '%PYTHON_INSTALLER%')"

if not exist "%PYTHON_INSTALLER%" (
    echo [错误] Python 下载失败！
    echo 请手动访问 https://www.python.org/downloads/ 下载安装 Python 3.11
    pause
    exit /b 1
)

echo [安装] 正在安装 Python...
"%PYTHON_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_launcher=1

if %errorlevel% neq 0 (
    echo [错误] Python 安装失败！
    pause
    exit /b 1
)

del "%PYTHON_INSTALLER%" >nul 2>&1

powershell -Command "[System.Environment]::SetEnvironmentVariable('PATH', [System.Environment]::GetEnvironmentVariable('PATH','Machine') + ';' + [System.Environment]::GetEnvironmentVariable('PATH','User'), 'Process')"

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [提示] Python 安装完成，请关闭此窗口后重新双击启动.bat
    pause
    exit /b 1
)

echo [OK] Python 安装成功！
echo.

:CHECK_PIP
if not defined PYTHON_CMD set PYTHON_CMD=python

echo [检查] 正在检查依赖包...
%PYTHON_CMD% -c "import streamlit" >nul 2>&1
if %errorlevel% neq 0 (
    echo [安装] 正在安装依赖包，首次安装需要几分钟...
    echo.
    %PYTHON_CMD% -m pip install -r "%~dp0requirements.txt" --quiet
    if %errorlevel% neq 0 (
        echo [错误] 依赖安装失败！请检查网络连接。
        pause
        exit /b 1
    )
    echo [OK] 依赖安装完成！
) else (
    echo [OK] 依赖包已就绪
)

echo.
echo [启动] 正在启动应用...
echo 应用启动后会自动在浏览器中打开
echo 关闭此窗口即可停止应用
echo.

cd /d "%~dp0"
%PYTHON_CMD% -m streamlit run main_app.py --server.headless false

if %errorlevel% neq 0 (
    echo.
    echo [错误] 应用启动失败！
    pause
)
