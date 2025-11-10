# 백엔드 서버 실행 스크립트 (Python 3.12 가상환경 사용)
Write-Host "=== #onmi 백엔드 서버 시작 ===" -ForegroundColor Cyan

# 가상환경 활성화
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "`n가상환경 활성화 중..." -ForegroundColor Yellow
    .\venv\Scripts\Activate.ps1
} else {
    Write-Host "`n⚠️ 가상환경이 없습니다. 생성 중..." -ForegroundColor Yellow
    $python312Path = "C:\Users\$env:USERNAME\AppData\Local\Programs\Python\Python312"
    if (Test-Path "$python312Path\python.exe") {
        & "$python312Path\python.exe" -m venv venv
        .\venv\Scripts\Activate.ps1
        pip install -r requirements.txt
    } else {
        Write-Host "❌ Python 3.12를 찾을 수 없습니다." -ForegroundColor Red
        exit 1
    }
}

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
# Windows 멀티프로세싱 환경에서 인코딩 문제 방지
$env:PYTHONLEGACYWINDOWSSTDIO = "0"

# 현재 디렉토리 경로 (reload-dir 옵션용)
$currentDir = $PWD.Path

Write-Host "`n작업 디렉토리: $PWD" -ForegroundColor Yellow
Write-Host "PYTHONPATH 설정: $env:PYTHONPATH" -ForegroundColor Yellow
Write-Host "`n서버 시작 중..." -ForegroundColor Yellow
Write-Host "서버 주소: http://localhost:8000" -ForegroundColor Green
Write-Host "API 문서: http://localhost:8000/docs" -ForegroundColor Green
Write-Host "`n종료하려면 Ctrl+C를 누르세요.`n" -ForegroundColor Yellow

# 서버 실행
# main.py를 직접 실행 (멀티프로세싱 문제 회피)
# main.py 내부에서 uvicorn을 실행하므로 경로 문제가 해결됨
$env:PYTHONPATH = "$currentDir;$currentDir\..\shared"
python src\main.py

