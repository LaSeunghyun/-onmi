@echo off
REM API Gateway 실행 스크립트 (Windows)

REM 작업 디렉토리 확인
if not exist "src\main.py" (
    echo ❌ 오류: src\main.py를 찾을 수 없습니다. 작업 디렉토리를 확인하세요.
    echo 현재 디렉토리: %CD%
    exit /b 1
)

REM PYTHONPATH 설정 (현재 디렉토리와 shared 디렉토리 모두 포함)
set PYTHONPATH=%CD%;%CD%\..\shared

REM Windows에서 UTF-8 인코딩 설정
set PYTHONIOENCODING=utf-8

echo 작업 디렉토리: %CD%
echo PYTHONPATH 설정: %PYTHONPATH%
echo.
echo 서버 시작 중...
echo 서버 주소: http://localhost:8000
echo API 문서: http://localhost:8000/docs
echo.
echo 종료하려면 Ctrl+C를 누르세요.
echo.

REM main.py를 직접 실행 (멀티프로세싱 문제 회피)
REM main.py 내부에서 uvicorn을 실행하므로 경로 문제가 해결됨
set PYTHONPATH=%CD%;%CD%\..\shared
python src\main.py




