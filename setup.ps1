# #onmi 프로젝트 초기 설정 스크립트 (Windows PowerShell)

Write-Host "=== #onmi 프로젝트 초기 설정 ===" -ForegroundColor Cyan

# 1. .env 파일 생성
Write-Host "`n1. 환경 변수 파일 생성 중..." -ForegroundColor Yellow
if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host "   .env 파일이 생성되었습니다." -ForegroundColor Green
    Write-Host "   .env 파일을 편집하여 필요한 값들을 설정해주세요." -ForegroundColor Yellow
} else {
    Write-Host "   .env 파일이 이미 존재합니다." -ForegroundColor Gray
}

# 2. Docker 서비스 시작
Write-Host "`n2. Docker 서비스 시작 중..." -ForegroundColor Yellow
docker-compose up -d
if ($LASTEXITCODE -eq 0) {
    Write-Host "   Docker 서비스가 시작되었습니다." -ForegroundColor Green
} else {
    Write-Host "   Docker 서비스 시작 실패. Docker가 설치되어 있고 실행 중인지 확인해주세요." -ForegroundColor Red
    exit 1
}

# 3. 데이터베이스 초기화 대기
Write-Host "`n3. 데이터베이스 준비 대기 중 (10초)..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# 4. 데이터베이스 마이그레이션 실행
Write-Host "`n4. 데이터베이스 마이그레이션 실행 중..." -ForegroundColor Yellow
$migrationFile = "backend\shared\database\migrations\001_init_schema.sql"
if (Test-Path $migrationFile) {
    docker exec -i onmi-postgres psql -U onmi -d onmi_db < $migrationFile
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   데이터베이스 마이그레이션이 완료되었습니다." -ForegroundColor Green
    } else {
        Write-Host "   데이터베이스 마이그레이션 실패. PostgreSQL 컨테이너가 준비될 때까지 기다린 후 다시 시도해주세요." -ForegroundColor Red
    }
} else {
    Write-Host "   마이그레이션 파일을 찾을 수 없습니다: $migrationFile" -ForegroundColor Red
}

# 5. Python 가상환경 설정 안내
Write-Host "`n5. Python 백엔드 설정 안내" -ForegroundColor Yellow
Write-Host "   백엔드 서비스를 실행하려면:" -ForegroundColor Gray
Write-Host "   - API Gateway: cd backend\api-gateway && pip install -r requirements.txt && python -m uvicorn src.main:app --reload" -ForegroundColor Gray
Write-Host "   - Scheduler: cd backend\scheduler && pip install -r requirements.txt && python src\scheduler.py" -ForegroundColor Gray

# 6. Flutter 앱 설정 안내
Write-Host "`n6. Flutter 앱 설정 안내" -ForegroundColor Yellow
Write-Host "   Flutter 앱을 실행하려면:" -ForegroundColor Gray
Write-Host "   - cd mobile && flutter pub get && flutter run" -ForegroundColor Gray

Write-Host "`n=== 설정 완료! ===" -ForegroundColor Green
Write-Host "다음 단계:" -ForegroundColor Cyan
Write-Host "1. .env 파일을 편집하여 필요한 값들을 설정하세요" -ForegroundColor White
Write-Host "2. 백엔드 서비스를 시작하세요" -ForegroundColor White
Write-Host "3. Flutter 앱을 실행하세요" -ForegroundColor White











