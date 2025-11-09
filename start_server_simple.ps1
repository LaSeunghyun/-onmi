# 간단한 서버 실행 스크립트 (현재 세션용)
Write-Host "=== #onmi 백엔드 서버 시작 ===" -ForegroundColor Cyan

# Python 경로 추가
$pythonPath = "C:\Users\$env:USERNAME\AppData\Local\Programs\Python\Python314"
$scriptsPath = "$pythonPath\Scripts"
$env:Path = "$env:Path;$pythonPath;$scriptsPath"

# 프로젝트 디렉토리로 이동
Set-Location "backend\api-gateway"

# PYTHONPATH 설정
$env:PYTHONPATH = "$PWD\..\shared"

Write-Host "`n서버 시작 중..." -ForegroundColor Yellow
Write-Host "서버 주소: http://localhost:8000" -ForegroundColor Green
Write-Host "API 문서: http://localhost:8000/docs" -ForegroundColor Green
Write-Host "`n종료하려면 Ctrl+C를 누르세요.`n" -ForegroundColor Yellow

# 서버 실행
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

