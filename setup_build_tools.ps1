# Microsoft Visual C++ Build Tools 설치 안내
Write-Host "=== asyncpg 설치를 위한 빌드 도구 필요 ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "asyncpg 패키지를 빌드하려면 Microsoft Visual C++ Build Tools가 필요합니다." -ForegroundColor Yellow
Write-Host ""
Write-Host "해결 방법:" -ForegroundColor Green
Write-Host "1. Visual Studio Build Tools 다운로드:" -ForegroundColor White
Write-Host "   https://visualstudio.microsoft.com/visual-cpp-build-tools/" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. 설치 시 'C++ build tools' 워크로드를 선택하세요." -ForegroundColor White
Write-Host ""
Write-Host "3. 또는 사전 빌드된 wheel 파일 사용 (권장):" -ForegroundColor White
Write-Host "   python -m pip install asyncpg --only-binary :all:" -ForegroundColor Cyan
Write-Host ""
Write-Host "Visual Studio Build Tools 다운로드 페이지를 여시겠습니까? (Y/N)" -ForegroundColor Yellow
$response = Read-Host
if ($response -eq "Y" -or $response -eq "y") {
    Start-Process "https://visualstudio.microsoft.com/visual-cpp-build-tools/"
}

