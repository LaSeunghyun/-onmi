# 데이터베이스 연결 문제 해결

## 문제
백엔드 서버가 Supabase에 연결하려고 하지만, 로컬 Docker PostgreSQL을 사용해야 합니다.

## 해결 방법

### 1. .env 파일 수정

`.env` 파일을 열어서 다음 줄을 수정하세요:

**변경 전:**
```
DATABASE_URL=postgresql://postgres:ra89092..@db.giqqhzonfruynokwbguv.supabase.co:5432/postgres
```

**변경 후:**
```
DATABASE_URL=postgresql://onmi:onmi_dev_password@localhost:5432/onmi_db
```

### 2. 백엔드 서버 재시작

.env 파일을 수정한 후 백엔드 서버를 재시작하세요:

```powershell
cd backend\api-gateway
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

또는 제공된 스크립트 사용:
```powershell
cd C:\onmi
.\start_server_simple.ps1
```

### 3. API 테스트

서버가 재시작된 후 다음 명령어로 테스트하세요:

```powershell
# 회원가입 테스트
curl -X POST http://localhost:8000/auth/signup -H "Content-Type: application/json" -d '{\"email\": \"test@example.com\", \"password\": \"test1234\"}'

# 로그인 테스트
curl -X POST http://localhost:8000/auth/signin-json -H "Content-Type: application/json" -d '{\"email\": \"test@example.com\", \"password\": \"test1234\"}'
```

## 확인 사항

- ✅ PostgreSQL Docker 컨테이너가 실행 중입니다
- ✅ 데이터베이스 마이그레이션이 완료되었습니다
- ✅ users 테이블이 정상적으로 생성되었습니다
- ⚠️ .env 파일의 DATABASE_URL을 로컬로 변경해야 합니다

