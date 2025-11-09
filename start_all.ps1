# 서버와 Flutter 앱을 모두 실행하는 스크립트
Write-Host "=== #onmi 전체 시스템 시작 ===" -ForegroundColor Cyan

# 1. 백엔드 서버 시작 (새 창)
Write-Host "`n1. 백엔드 서버 시작 중..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-File", "$PWD\start_server.ps1" -WindowStyle Normal

# 2. 잠시 대기
Start-Sleep -Seconds 3

# 3. Flutter 앱 시작
Write-Host "`n2. Flutter 앱 시작 중..." -ForegroundColor Yellow
Set-Location mobile
C:\flutter\bin\flutter.bat run -d windows

