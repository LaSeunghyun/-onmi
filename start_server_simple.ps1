# 간단한 서버 실행 스크립트 (현재 세션용)
Write-Host "=== #onmi 백엔드 서버 시작 ===" -ForegroundColor Cyan

# Python 경로 추가
$pythonPath = "C:\Users\$env:USERNAME\AppData\Local\Programs\Python\Python314"
$scriptsPath = "$pythonPath\Scripts"
$env:Path = "$env:Path;$pythonPath;$scriptsPath"

# 프로젝트 디렉토리로 이동
Set-Location "backend\api-gateway"

# 작업 디렉토리 확인
if (-not (Test-Path "src\main.py")) {
    Write-Host "❌ 오류: src\main.py를 찾을 수 없습니다. 작업 디렉토리를 확인하세요." -ForegroundColor Red
    Write-Host "현재 디렉토리: $PWD" -ForegroundColor Yellow
    exit 1
}

# PYTHONPATH 설정 (현재 디렉토리와 shared 디렉토리 모두 포함)
$env:PYTHONPATH = "$PWD;$PWD\..\shared"

# Windows에서 UTF-8 인코딩 설정 (멀티프로세싱 환경에서도 적용)
$env:PYTHONIOENCODING = "utf-8"

Write-Host "`n작업 디렉토리: $PWD" -ForegroundColor Yellow
Write-Host "PYTHONPATH 설정: $env:PYTHONPATH" -ForegroundColor Yellow
Write-Host "`n서버 시작 중..." -ForegroundColor Yellow
Write-Host "서버 주소: http://localhost:8000" -ForegroundColor Green
Write-Host "API 문서: http://localhost:8000/docs" -ForegroundColor Green
Write-Host "`n종료하려면 Ctrl+C를 누르세요.`n" -ForegroundColor Yellow

# 서버 실행
# main.py를 직접 실행 (멀티프로세싱 문제 회피)
# main.py 내부에서 uvicorn을 실행하므로 경로 문제가 해결됨
$env:PYTHONPATH = "$PWD;$PWD\..\shared"
python src\main.py

