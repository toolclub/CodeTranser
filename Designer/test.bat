@echo off
pushd "%~dp0"
REM Run pytest inside backend container; args pass through.
REM Example: test.bat tests/unit/sandbox -v
docker compose exec backend pytest tests/unit %*
popd
