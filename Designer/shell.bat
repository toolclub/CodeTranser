@echo off
pushd "%~dp0"
REM Open a shell inside a container; default backend.
set TARGET=%1
if "%TARGET%"=="" set TARGET=backend
docker compose exec %TARGET% sh
popd
