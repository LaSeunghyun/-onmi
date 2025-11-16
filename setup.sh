#!/bin/bash
# #onmi 프로젝트 초기 설정 스크립트 (Linux/Mac)

echo "=== #onmi 프로젝트 초기 설정 ==="

# 1. .env 파일 생성
echo ""
echo "1. 환경 변수 파일 생성 중..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "   .env 파일이 생성되었습니다."
    echo "   .env 파일을 편집하여 필요한 값들을 설정해주세요."
else
    echo "   .env 파일이 이미 존재합니다."
fi

# 2. Docker 서비스 시작
echo ""
echo "2. Docker 서비스 시작 중..."
docker-compose up -d
if [ $? -eq 0 ]; then
    echo "   Docker 서비스가 시작되었습니다."
else
    echo "   Docker 서비스 시작 실패. Docker가 설치되어 있고 실행 중인지 확인해주세요."
    exit 1
fi

# 3. 데이터베이스 초기화 대기
echo ""
echo "3. 데이터베이스 준비 대기 중 (10초)..."
sleep 10

# 4. 데이터베이스 마이그레이션 실행
echo ""
echo "4. 데이터베이스 마이그레이션 실행 중..."
MIGRATION_FILE="backend/shared/database/migrations/001_init_schema.sql"
if [ -f "$MIGRATION_FILE" ]; then
    docker exec -i onmi-postgres psql -U onmi -d onmi_db < "$MIGRATION_FILE"
    if [ $? -eq 0 ]; then
        echo "   데이터베이스 마이그레이션이 완료되었습니다."
    else
        echo "   데이터베이스 마이그레이션 실패. PostgreSQL 컨테이너가 준비될 때까지 기다린 후 다시 시도해주세요."
    fi
else
    echo "   마이그레이션 파일을 찾을 수 없습니다: $MIGRATION_FILE"
fi

# 5. Python 가상환경 설정 안내
echo ""
echo "5. Python 백엔드 설정 안내"
echo "   백엔드 서비스를 실행하려면:"
echo "   - API Gateway: cd backend/api-gateway && pip install -r requirements.txt && uvicorn src.main:app --reload"
echo "   - Scheduler: cd backend/scheduler && pip install -r requirements.txt && python src/scheduler.py"

# 6. Flutter 앱 설정 안내
echo ""
echo "6. Flutter 앱 설정 안내"
echo "   Flutter 앱을 실행하려면:"
echo "   - cd mobile && flutter pub get && flutter run"

echo ""
echo "=== 설정 완료! ==="
echo "다음 단계:"
echo "1. .env 파일을 편집하여 필요한 값들을 설정하세요"
echo "2. 백엔드 서비스를 시작하세요"
echo "3. Flutter 앱을 실행하세요"











