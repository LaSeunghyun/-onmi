# Python PATH 추가 스크립트
Write-Host "=== Python PATH 추가 ===" -ForegroundColor Cyan

$pythonPath = "C:\Users\$env:USERNAME\AppData\Local\Programs\Python\Python314"
$scriptsPath = "$pythonPath\Scripts"

# Python이 설치되어 있는지 확인
if (-not (Test-Path "$pythonPath\python.exe")) {
    Write-Host "❌ Python을 찾을 수 없습니다: $pythonPath" -ForegroundColor Red
    Write-Host "Python이 다른 경로에 설치되어 있을 수 있습니다." -ForegroundColor Yellow
    exit 1
}

Write-Host "`nPython 경로 발견:" -ForegroundColor Green
Write-Host "  Python: $pythonPath" -ForegroundColor White
Write-Host "  Scripts: $scriptsPath" -ForegroundColor White

# 현재 사용자 PATH 확인
$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")

if ($currentPath -like "*$pythonPath*") {
    Write-Host "`n✅ Python 경로가 이미 PATH에 있습니다." -ForegroundColor Green
} else {
    # PATH에 추가
    $newPath = $currentPath + ";$pythonPath;$scriptsPath"
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    Write-Host "`n✅ Python 경로를 사용자 PATH에 추가했습니다!" -ForegroundColor Green
    
    # 현재 세션에도 추가
    $env:Path += ";$pythonPath;$scriptsPath"
    Write-Host "✅ 현재 세션에도 PATH를 추가했습니다." -ForegroundColor Green
}

Write-Host "`nPython 및 pip 확인:" -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  ⚠️ python 명령어를 찾을 수 없습니다. PowerShell을 재시작하세요." -ForegroundColor Yellow
}

try {
    $pipVersion = pip --version 2>&1
    Write-Host "  pip: $pipVersion" -ForegroundColor Green
} catch {
    Write-Host "  ⚠️ pip 명령어를 찾을 수 없습니다. python -m pip을 사용하세요." -ForegroundColor Yellow
}

Write-Host "`n💡 중요: 변경사항을 적용하려면 PowerShell을 재시작하세요!" -ForegroundColor Cyan
Write-Host "   또는 다음 명령으로 현재 세션에서 사용할 수 있습니다:" -ForegroundColor Cyan
Write-Host "   `$env:Path += `";$pythonPath;$scriptsPath`"" -ForegroundColor White

