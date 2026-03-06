@echo off
setlocal

set "ROOT_DIR=%~dp0"
set "BACKEND_PORT=8000"
set "BACKEND_DIR=%ROOT_DIR%backend"
set "FRONTEND_DIR=%ROOT_DIR%frontend"
pushd "%ROOT_DIR%" >nul

set "SHOW_HELP=0"
:parse_args
if "%~1"=="" goto :after_args
if /I "%~1"=="-h" (
  set "SHOW_HELP=1"
  shift
  goto :parse_args
)
if /I "%~1"=="--help" (
  set "SHOW_HELP=1"
  shift
  goto :parse_args
)
rem 新增合法参数时，请在本行之前添加分支
goto :unknown

:after_args
if "%SHOW_HELP%"=="1" goto :help

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] 未检测到 Python，请先安装 Python。
  exit /b 1
)

where node >nul 2>nul
if errorlevel 1 (
  echo [ERROR] 未检测到 Node.js，请先安装 Node.js。
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo [ERROR] 未检测到 npm，请先安装 npm。
  exit /b 1
)

if not exist ".env" (
  if exist ".env.example" (
    copy /Y ".env.example" ".env" >nul
    echo [INFO] 未找到 .env，已从 .env.example 自动创建。
    echo [INFO] 请将 REDIS_URL 改为本机地址（localhost）后重新执行脚本。
    exit /b 0
  ) else (
    echo [ERROR] 未找到 .env 且不存在 .env.example。
    exit /b 1
  )
)

echo [INFO] 请确保本机 Redis 已启动（非 Docker）。
echo [INFO] 正在启动后端与前端（将打开两个新窗口）...

if not exist "%BACKEND_DIR%\" (
  echo [ERROR] 未找到后端目录: %BACKEND_DIR%
  exit /b 1
)
if not exist "%BACKEND_DIR%\main.py" (
  echo [ERROR] 未找到后端入口文件: %BACKEND_DIR%\main.py
  exit /b 1
)
if not exist "%FRONTEND_DIR%\" (
  echo [ERROR] 未找到前端目录: %FRONTEND_DIR%
  exit /b 1
)

set "BACKEND_CMD=cd /d \"%BACKEND_DIR%\" && python -m uvicorn main:app --host localhost --port %BACKEND_PORT% --reload"
set "FRONTEND_CMD=cd /d \"%FRONTEND_DIR%\" && set REACT_APP_API_BASE_URL=http://localhost:%BACKEND_PORT% && npm start"
start "Backend (FastAPI)" cmd /k "%BACKEND_CMD%"
start "Frontend (React)" cmd /k "%FRONTEND_CMD%"

echo [INFO] 启动命令已发送。
echo [INFO] 后端: http://localhost:%BACKEND_PORT%
echo [INFO] 前端: http://localhost:3000
exit /b 0

:help
echo 用法:
echo   start-windows.bat
echo.
echo 说明:
echo   在 Windows 本机环境启动后端+前端，不使用 Docker。
echo   依赖本机 Redis。
exit /b 0

:unknown
echo [ERROR] 未知参数: %~1
echo.
call :help
exit /b 1
