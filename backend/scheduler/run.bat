@echo off
REM Scheduler 실행 스크립트 (Windows)

set PYTHONPATH=%PYTHONPATH%;%CD%\..\shared;%CD%\..\ingestor\src;%CD%\..\nlp-service\src

python src/scheduler.py











