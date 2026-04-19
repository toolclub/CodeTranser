@echo off
title Cascade - Start
pushd "%~dp0"

echo ============================================
echo   Cascade Start
echo ============================================
echo.

docker info > nul 2>&1
if %errorlevel% neq 0 goto err_no_docker

if not exist ".env" goto init_env

REM Detect sandbox image; decide whether to enable sandbox profile
REM Default: fullstack-dev:latest [already has sshd + /sandbox + root:sandbox123].
REM Override via SANDBOX_IMAGE in .env if you want a different tag.
set SANDBOX_PROFILE=
set SANDBOX_IMG=fullstack-dev:latest
echo [1/3] Checking sandbox image %SANDBOX_IMG% ...
docker image inspect %SANDBOX_IMG% > nul 2>&1
if %errorlevel% equ 0 goto sandbox_present
echo   [WARN] %SANDBOX_IMG% not found locally.
echo          Cascade will start without sandbox [Phase3 features unavailable].
echo          To build sandbox base [one-time, 15-30 min]:
echo            cd sandbox
echo            docker build -t fullstack-dev:latest -f Dockerfile.base .
echo            docker compose --profile sandbox up -d
goto stack_up

:sandbox_present
echo   [OK] Sandbox image present, will start sandbox container too.
set SANDBOX_PROFILE=--profile sandbox
goto stack_up

:stack_up
echo.
echo [2/3] Building and starting containers [first run takes 2-3 minutes] ...
docker compose %SANDBOX_PROFILE% up -d --build
if %errorlevel% neq 0 goto err_compose

echo.
echo [3/3] Waiting for backend healthy ...
set WAIT=0

:wait_loop
docker inspect -f "{{.State.Health.Status}}" cascade-backend 2>nul | findstr /i "healthy" > nul
if %errorlevel% equ 0 goto done
set /a WAIT+=1
if %WAIT% gtr 60 goto warn_slow
timeout /t 3 /nobreak > nul
goto wait_loop

:warn_slow
echo   [WARN] Still not healthy after 3 min. Check logs:
echo          logs.bat backend
goto done

:done
echo.
echo ============================================
echo   Started.
echo ============================================
echo.
echo   Frontend  nginx :       http://localhost:8080
echo   Backend   uvicorn :     http://localhost:8000/healthz
echo   API docs          :     http://localhost:8000/docs
if defined SANDBOX_PROFILE echo   Sandbox SSH       :     ssh root@127.0.0.1 -p 2222   password sandbox123
echo.
echo   After editing code, rebuild the changed service:
echo     docker compose up -d --build backend
echo     docker compose up -d --build frontend
echo.
echo   Logs:    logs.bat               [backend]
echo            logs.bat frontend / mysql / mongo / redis / sandbox
echo   Test:    test.bat
echo   Shell:   shell.bat              [into backend]
echo   Stop:    stop.bat
echo ============================================
goto end

:init_env
echo [INIT] No .env found. Copying .env.example to .env.
echo        Please edit LLM_API_KEY then re-run start.bat
copy /Y .env.example .env > nul
notepad .env
goto end

:err_no_docker
echo [ERROR] Docker is not running. Please start Docker Desktop first.
goto end

:err_compose
echo [ERROR] docker compose up failed.
goto end

:end
popd
pause
