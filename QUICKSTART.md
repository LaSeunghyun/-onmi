# 빠른 시작 가이드

#onmi 프로젝트를 빠르게 시작하는 방법입니다.

## 사전 요구사항

- Docker & Docker Compose
- Python 3.10+ (백엔드 개발 시)
- Flutter SDK 3.0+ (모바일 앱 개발 시)

## 1단계: 프로젝트 설정

### Windows
```powershell
.\setup.ps1
```

### Linux/Mac
```bash
chmod +x setup.sh
./setup.sh
```

또는 수동으로:

```bash
# 1. 환경 변수 파일 생성
cp .env.example .env

# 2. Docker 서비스 시작
docker-compose up -d

# 3. 데이터베이스 마이그레이션 (PostgreSQL 준비 후)
docker exec -i onmi-postgres psql -U onmi -d onmi_db < backend/shared/database/migrations/001_init_schema.sql
```

## 2단계: 백엔드 서비스 실행

### API Gateway 실행

```bash
cd backend/api-gateway
pip install -r requirements.txt
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

또는 Windows에서:
```powershell
cd backend\api-gateway
pip install -r requirements.txt
.\run.bat
```

API Gateway는 `http://localhost:8000`에서 실행됩니다.

API 문서는 `http://localhost:8000/docs`에서 확인할 수 있습니다.

### Scheduler 실행 (선택사항)

```bash
cd backend/scheduler
pip install -r requirements.txt
python src/scheduler.py
```

## 3단계: Flutter 앱 실행

```bash
cd mobile
flutter pub get
flutter run
```

## 4단계: 테스트

### API 테스트

1. 회원가입:
```bash
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "test1234"}'
```

2. 로그인:
```bash
curl -X POST http://localhost:8000/auth/signin \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=test1234"
```

3. 키워드 추가 (토큰 필요):
```bash
curl -X POST http://localhost:8000/keywords \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "AI"}'
```

## 문제 해결

### Docker 컨테이너가 시작되지 않는 경우

```bash
# 컨테이너 상태 확인
docker-compose ps

# 로그 확인
docker-compose logs

# 컨테이너 재시작
docker-compose restart
```

### 데이터베이스 연결 오류

`.env` 파일의 데이터베이스 설정을 확인하세요:
- `POSTGRES_HOST=postgres` (Docker 내부)
- `POSTGRES_HOST=localhost` (로컬 개발)

### Flutter 앱이 API에 연결되지 않는 경우

`mobile/lib/services/api_service.dart`의 `baseUrl`을 확인하세요:
- 개발: `http://localhost:8000`
- Android 에뮬레이터: `http://10.0.2.2:8000`
- iOS 시뮬레이터: `http://localhost:8000`
- 실제 기기: 컴퓨터의 IP 주소 사용

## 다음 단계

- [README.md](README.md) - 전체 문서
- [CHANGELOG.md](CHANGELOG.md) - 변경 이력
- [REMOVE_PROTOTYPE.md](REMOVE_PROTOTYPE.md) - 프로토타입 코드 제거 가이드




