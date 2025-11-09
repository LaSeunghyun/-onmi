# 백엔드 서버 실행 스크립트
Write-Host "=== #onmi 백엔드 서버 시작 ===" -ForegroundColor Cyan

$apiGatewayPath = "backend\api-gateway"
$sharedPath = "backend\shared"

# PYTHONPATH 설정
$env:PYTHONPATH = "$PWD\$sharedPath"

Write-Host "`nPYTHONPATH 설정: $env:PYTHONPATH" -ForegroundColor Yellow

# API Gateway 디렉토리로 이동
Set-Location $apiGatewayPath

Write-Host "`n서버 시작 중..." -ForegroundColor Yellow
Write-Host "서버 주소: http://localhost:8000" -ForegroundColor Green
Write-Host "API 문서: http://localhost:8000/docs" -ForegroundColor Green
Write-Host "`n종료하려면 Ctrl+C를 누르세요.`n" -ForegroundColor Yellow

# uvicorn 실행
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

