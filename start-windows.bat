@echo off
setlocal

set "ROOT_DIR=%~dp0"
pushd "%ROOT_DIR%" >nul

if /I "%~1"=="-h" goto :help
if /I "%~1"=="--help" goto :help
if not "%~2"=="" goto :unknown
if not "%~1"=="" goto :unknown

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] 未检测到 Python，请先安装 Python 3.12+。
  exit /b 1
)

where node >nul 2>nul
if errorlevel 1 (
  echo [ERROR] 未检测到 Node.js，请先安装 Node.js 18+。
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
    echo [INFO] 请将 DATABASE_URL 和 REDIS_URL 改为本机地址（localhost）后重新执行脚本。
    exit /b 0
  ) else (
    echo [ERROR] 未找到 .env 且不存在 .env.example。
    exit /b 1
  )
)

echo [INFO] 请确保本机 PostgreSQL 与 Redis 已启动（非 Docker）。
echo [INFO] 正在启动后端与前端（将打开两个新窗口）...

start "Backend (FastAPI)" cmd /k "cd /d \"%ROOT_DIR%backend\" && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
start "Frontend (React)" cmd /k "cd /d \"%ROOT_DIR%frontend\" && set REACT_APP_API_BASE_URL=http://localhost:8000 && npm start"

echo [INFO] 启动命令已发送。
echo [INFO] 后端: http://localhost:8000
echo [INFO] 前端: http://localhost:3000
exit /b 0

:help
echo 用法:
echo   start-windows.bat
echo.
echo 说明:
echo   在 Windows 本机环境启动后端^+前端，不使用 Docker。
echo   依赖本机 PostgreSQL 和 Redis。
exit /b 0

:unknown
echo [ERROR] 未知参数: %~1
echo.
goto :help
