@echo off
REM API Gateway 실행 스크립트 (Windows)

set PYTHONPATH=%PYTHONPATH%;%CD%\..\shared

uvicorn src.main:app --reload --host 0.0.0.0 --port 8000




