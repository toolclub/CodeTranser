@echo off
title Cascade - Stop
pushd "%~dp0"

docker info > nul 2>&1
if %errorlevel% neq 0 goto err_no_docker

echo Stopping Cascade containers [data preserved in .data\] ...
docker compose down 2>nul
echo [OK] Stopped.
echo.
echo To wipe all data:
echo   rmdir /s /q .data
echo   rmdir /s /q .logs
echo.
goto end

:err_no_docker
echo [ERROR] Docker is not running.
goto end

:end
popd
pause
