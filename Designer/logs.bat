@echo off
pushd "%~dp0"
REM Usage: logs.bat            (default: backend)
REM        logs.bat frontend / sandbox / mysql / mongo / redis
set TARGET=%1
if "%TARGET%"=="" set TARGET=backend
docker compose logs -f --tail=200 %TARGET%
popd
