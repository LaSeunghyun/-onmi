# #onmi - 모듈화 앱

키워드 기반 뉴스 트래킹 & 감성분석 모듈화 앱

## 프로젝트 구조

```
onmi/
├── mobile/                    # Flutter 모바일 앱
├── backend/                   # 백엔드 서비스
│   ├── api-gateway/          # FastAPI Gateway
│   ├── ingestor/             # RSS 수집 서비스
│   ├── nlp-service/          # NLP 감성 분석 서비스
│   ├── scheduler/            # 스케줄러/워커
│   └── shared/               # 공통 모듈
├── docker-compose.yml        # 로컬 개발 환경
└── README.md
```

## 기술 스택

### 프론트엔드
- Flutter 3.x
- Riverpod (상태 관리)
- Hive (로컬 캐시)
- Dio (HTTP 클라이언트)

### 백엔드
- FastAPI (API Gateway)
- PostgreSQL 15+
- Redis
- Python (Ingestor, NLP Service)

## 시작하기

### 빠른 시작

자세한 내용은 [QUICKSTART.md](QUICKSTART.md)를 참고하세요.

**Windows:**
```powershell
.\setup.ps1
```

**Linux/Mac:**
```bash
chmod +x setup.sh
./setup.sh
```

### 사전 요구사항
- Docker & Docker Compose
- Flutter SDK 3.0+ (모바일 앱 개발 시)
- Python 3.10+ (백엔드 개발 시)

### 백엔드 실행

1. 환경 변수 설정
```bash
cp .env.example .env
# .env 파일을 편집하여 필요한 값 설정
```

2. Docker Compose로 서비스 시작
```bash
docker-compose up -d
```

3. 데이터베이스 마이그레이션 실행
```bash
# PostgreSQL 컨테이너에 접속하여 스키마 생성
docker exec -i onmi-postgres psql -U onmi -d onmi_db < backend/shared/database/migrations/001_init_schema.sql
```

4. API Gateway 실행
```bash
cd backend/api-gateway
pip install -r requirements.txt
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

API 문서: http://localhost:8000/docs

### 모바일 앱 실행

1. Flutter 의존성 설치
```bash
cd mobile
flutter pub get
```

2. 앱 실행
```bash
flutter run
```

**참고:** Flutter 앱에서 API에 연결하려면 `mobile/lib/services/api_service.dart`의 `baseUrl`을 확인하세요.
- Android 에뮬레이터: `http://10.0.2.2:8000`
- iOS 시뮬레이터: `http://localhost:8000`
- 실제 기기: 컴퓨터의 IP 주소 사용

## API 엔드포인트

### 인증
- `POST /auth/signup` - 회원가입
- `POST /auth/signin` - 로그인

### 키워드
- `GET /keywords` - 키워드 목록
- `POST /keywords` - 키워드 추가
- `DELETE /keywords/:id` - 키워드 삭제

### 피드
- `GET /feed` - 피드 조회 (필터, 정렬, 페이지네이션)

### 기사
- `GET /articles/:id` - 기사 상세
- `POST /articles/:id/feedback` - 감성 피드백

### 통계
- `GET /stats/keywords/:id` - 키워드별 통계

### 공유
- `POST /share/articles/:id` - 기사 공유
- `GET /share/history` - 공유 히스토리

### 알림
- `POST /notifications/detect-negative-surge` - 부정 급증 감지

## 개발 가이드

### 기존 프로토타입 코드 제거

프로토타입 React/TypeScript 코드는 `src/` 디렉토리에 있습니다. Flutter 앱이 완성되었으므로 다음 파일들을 제거할 수 있습니다:

**제거할 파일/디렉토리:**
- `src/` 디렉토리 전체
- `package.json`
- `vite.config.ts`
- `index.html`
- `node_modules/` (있는 경우)

**보존할 파일:**
- `README.md` (이 파일)
- `CHANGELOG.md`
- `docker-compose.yml`
- `.env.example`
- `.gitignore`

프로토타입 코드는 Flutter 앱으로 완전히 전환되었으며, 모든 기능이 모바일 앱에 구현되었습니다.

## 라이선스

MIT
