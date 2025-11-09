
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

## 주요 기능

### 뉴스 수집
- 키워드 기반 뉴스 자동 수집
- 중복 기간 제외: 기존에 조회한 일자는 제외하고 조회
- 첫 조회 시 직전 하루만 수집하여 효율성 향상
- 수동 수집 API 제공

### 요약 및 피드백
- 일일 요약: 사용자의 모든 키워드 통합 요약
- 키워드별 요약: 특정 키워드에 대한 요약
- 피드백 시스템: 좋아요/싫어요 (1-5점) 피드백 제출
- 피드백 기반 자동 개선: 사용자 피드백을 반영하여 요약 품질 지속 개선

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
- 리포지토리 패턴 및 계층형 아키텍처

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

## API 엔드포인트

### 키워드 관리
- `GET /keywords` - 키워드 목록 조회
- `POST /keywords` - 키워드 추가
- `DELETE /keywords/{keyword_id}` - 키워드 삭제
- `POST /keywords/{keyword_id}/collect` - 수동 수집 실행

### 요약 및 피드백
- `GET /summaries/daily` - 일일 요약 조회
- `GET /summaries/keywords/{keyword_id}` - 키워드별 요약 조회
- `POST /summaries/{summary_session_id}/feedback` - 피드백 제출

### 수동 수집 API 사용법

```bash
# 기본 수집 (마지막 수집 이후부터 현재까지)
POST /keywords/{keyword_id}/collect

# 특정 기간 수집
POST /keywords/{keyword_id}/collect
Content-Type: application/json

{
  "range": {
    "start": "2024-01-01T00:00:00",
    "end": "2024-01-02T00:00:00"
  }
}
```

### 피드백 API 사용법

```bash
POST /summaries/{summary_session_id}/feedback
Content-Type: application/json

{
  "rating": 4,
  "comment": "요약이 도움이 되었습니다"
}
```

- `rating`: 1-5점 (1=매우 불만족, 5=매우 만족)
- `comment`: 선택적 코멘트

## 초기 수집 정책

- 첫 조회 시 직전 하루만 수집하여 효율성을 높입니다
- 이후 수집은 마지막 수집 시간 이후부터 현재까지 자동으로 수집합니다
- 명시적 범위를 지정하면 해당 기간에서 이미 수집된 부분을 제외하고 수집합니다

## 데이터베이스 마이그레이션

새로운 기능을 사용하려면 데이터베이스 마이그레이션을 실행해야 합니다:

```bash
# 마이그레이션 실행
docker exec -i onmi-postgres psql -U onmi -d onmi_db < backend/shared/database/migrations/002_add_fetch_history_summary.sql
```

## 문서

- [워크플로우 문서](docs/workflow.md) - 시스템 워크플로우 상세 설명
- [수집 및 피드백 로직](docs/fetch_feedback_logic.md) - 기간 계산 및 피드백 기반 개선 메커니즘

## Vercel 배포 체크리스트

- `vercel.json`의 `functions.api/index.py.includeFiles` 및 `functions.api/cron/crawl.py.includeFiles`에 `backend/shared/**`, `backend/api-gateway/src/**`, `config/**`가 포함되어 있는지 확인합니다.
- 동일한 함수 설정에 `excludeFiles` 항목으로 `backend/**/venv/**`, `backend/**/__pycache__/**`가 선언되어 불필요한 파일이 번들되지 않도록 합니다.
- `vercel.json`의 `env.PYTHONPATH` 값이 `.`, `backend/shared`, `backend/api-gateway/src`를 모두 포함하는지 검증합니다.
- 배포 전에 로컬 PowerShell에서 아래 명령을 실행해 `backend` 네임스페이스가 정상적으로 탐지되는지 확인합니다.

```powershell
py -3 -c "import sys; sys.path.insert(0, r'C:\onmi'); import backend.shared.config.settings"
```

- 환경 변수를 갱신하거나 `vercel.json`을 수정했다면 Vercel 대시보드의 최근 배포에서 **Redeploy**를 수행해 변경 사항을 적용합니다.

## 추가 API 엔드포인트

### 인증
- `POST /auth/signup` - 회원가입
- `POST /auth/signin` - 로그인

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

## 개발 참고사항

**Flutter 앱 API 연결:**
- Android 에뮬레이터: `http://10.0.2.2:8000`
- iOS 시뮬레이터: `http://localhost:8000`
- 실제 기기: 컴퓨터의 IP 주소 사용

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
