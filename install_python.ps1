# Python 설치 안내 스크립트
Write-Host "=== Python 설치 안내 ===" -ForegroundColor Cyan
Write-Host ""

# Python 설치 여부 확인
$pythonInstalled = $false
$pythonPaths = @(
    "python",
    "python3",
    "py"
)

foreach ($cmd in $pythonPaths) {
    try {
        $version = & $cmd --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Python이 설치되어 있습니다: $version" -ForegroundColor Green
            $pythonInstalled = $true
            break
        }
    } catch {
        # 계속 확인
    }
}

if (-not $pythonInstalled) {
    Write-Host "❌ Python이 설치되어 있지 않습니다." -ForegroundColor Red
    Write-Host ""
    Write-Host "Python 설치 방법:" -ForegroundColor Yellow
    Write-Host "1. https://www.python.org/downloads/ 에서 Python 다운로드" -ForegroundColor White
    Write-Host "2. 설치 시 'Add Python to PATH' 옵션을 반드시 체크하세요!" -ForegroundColor Yellow
    Write-Host "3. 설치 완료 후 PowerShell을 재시작하세요" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Python 다운로드 페이지를 여시겠습니까? (Y/N)" -ForegroundColor Cyan
    $response = Read-Host
    if ($response -eq "Y" -or $response -eq "y") {
        Start-Process "https://www.python.org/downloads/"
    }
} else {
    Write-Host ""
    Write-Host "pip 설치 확인 중..." -ForegroundColor Yellow
    
    # pip 확인
    try {
        $pipVersion = & python -m pip --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ pip이 사용 가능합니다: $pipVersion" -ForegroundColor Green
            Write-Host ""
            Write-Host "다음 명령으로 서버를 실행할 수 있습니다:" -ForegroundColor Cyan
            Write-Host "cd C:\onmi\backend\api-gateway" -ForegroundColor White
            Write-Host '$env:PYTHONPATH = "$PWD\..\shared"' -ForegroundColor White
            Write-Host "python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000" -ForegroundColor White
        } else {
            Write-Host "⚠️ pip을 찾을 수 없습니다. python -m pip을 사용하세요." -ForegroundColor Yellow
        }
    } catch {
        Write-Host "⚠️ pip 확인 중 오류 발생" -ForegroundColor Yellow
    }
}

