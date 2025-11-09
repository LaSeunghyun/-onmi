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

# PYTHONPATH 설정
$env:PYTHONPATH = "$PWD\..\shared"

Write-Host "`n서버 시작 중..." -ForegroundColor Yellow
Write-Host "서버 주소: http://localhost:8000" -ForegroundColor Green
Write-Host "API 문서: http://localhost:8000/docs" -ForegroundColor Green
Write-Host "`n종료하려면 Ctrl+C를 누르세요.`n" -ForegroundColor Yellow

# 서버 실행
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

