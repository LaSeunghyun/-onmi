# 백엔드 로그 실시간 확인 스크립트
Write-Host "=== 백엔드 로그 실시간 확인 ===" -ForegroundColor Cyan
Write-Host "종료하려면 Ctrl+C를 누르세요.`n" -ForegroundColor Yellow

$logFile = "backend\logs\api-gateway.log"

if (-not (Test-Path $logFile)) {
    Write-Host "❌ 로그 파일을 찾을 수 없습니다: $logFile" -ForegroundColor Red
    exit 1
}

Write-Host "로그 파일: $logFile" -ForegroundColor Green
Write-Host "최근 20줄을 표시한 후 실시간으로 업데이트합니다.`n" -ForegroundColor Yellow

# 최근 20줄 표시
Get-Content $logFile -Tail 20 -Encoding UTF8

Write-Host "`n" + ("=" * 80) -ForegroundColor Cyan
Write-Host "실시간 로그 대기 중...`n" -ForegroundColor Green

# 실시간 로그 확인
Get-Content $logFile -Wait -Tail 0 -Encoding UTF8






