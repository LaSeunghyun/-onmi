# Vercel 배포 설정 가이드

이 문서는 #onmi 프로젝트를 Vercel에 배포하는 방법을 단계별로 안내합니다.

## 목차

1. [사전 요구사항](#사전-요구사항)
2. [GitHub 저장소 준비](#github-저장소-준비)
3. [Vercel 프로젝트 생성](#vercel-프로젝트-생성)
4. [환경 변수 설정](#환경-변수-설정)
5. [배포 확인](#배포-확인)
6. [Cron Job 설정 확인](#cron-job-설정-확인)
7. [문제 해결](#문제-해결)

## 사전 요구사항

- GitHub 계정
- Vercel 계정 (무료 플랜 가능)
- Supabase 계정 (데이터베이스용)

## GitHub 저장소 준비

### 1. 프로젝트를 GitHub에 푸시

아직 GitHub에 푸시하지 않았다면:

```bash
# Git 초기화 (이미 초기화되어 있다면 생략)
git init

# 파일 추가
git add .

# 커밋
git commit -m "Initial commit: Vercel 배포 준비"

# GitHub 저장소 생성 후 원격 저장소 추가
git remote add origin https://github.com/[username]/onmi.git

# 푸시
git push -u origin main
```

**중요**: `.env` 파일은 절대 커밋하지 마세요. `.gitignore`에 이미 포함되어 있습니다.

## Vercel 프로젝트 생성

### 1. Vercel에 로그인

1. [Vercel](https://vercel.com)에 접속
2. GitHub 계정으로 로그인 (또는 회원가입)

### 2. 새 프로젝트 생성

1. Vercel 대시보드에서 **Add New** > **Project** 클릭
2. GitHub 저장소 목록에서 `onmi` 프로젝트 선택
3. 프로젝트 설정:

   - **Framework Preset**: `Other`
   - **Root Directory**: `./` (루트 디렉토리)
   - **Build Command**: (비워둠 - Vercel이 자동 감지)
   - **Output Directory**: (비워둠)
   - **Install Command**: `pip install -r requirements.txt`

4. **Deploy** 클릭

### 3. 배포 완료 대기

배포가 완료되면 Vercel이 자동으로 URL을 생성합니다:
- 프로덕션: `https://your-project.vercel.app`
- 미리보기: 각 커밋마다 고유한 URL 생성

## 환경 변수 설정

### 필수 환경 변수

Vercel 대시보드에서 **Settings** > **Environment Variables**로 이동하여 다음 변수들을 추가하세요:

#### 데이터베이스 설정

```
DATABASE_URL=postgresql://postgres:[password]@[host]:5432/postgres
```

또는 Supabase를 사용하는 경우:

```
SUPABASE_DB_URL=postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
SUPABASE_URL=https://[project-ref].supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
```

#### JWT 설정

```
JWT_SECRET=your-strong-random-secret-key-here
JWT_EXPIRES_IN=7d
```

**보안 주의사항**: `JWT_SECRET`은 강력한 랜덤 문자열로 설정하세요:
```bash
# Linux/Mac
openssl rand -hex 32

# Windows PowerShell
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_})
```

### 선택적 환경 변수

```
# 스케줄러 설정
SCHEDULER_INTERVAL_HOURS=2

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000

# RSS 소스
RSS_SOURCES=https://rss.cnn.com/rss/edition.rss,https://feeds.bbci.co.uk/news/rss.xml

# Cron Job 보안
CRON_SECRET=your-cron-secret-key

# 토큰 사용량 제한
DAILY_TOKEN_LIMIT=1000000
TOKEN_WARNING_THRESHOLD=0.9

# Google OAuth
GOOGLE_OAUTH_CLIENT_ID_ANDROID=your-android-client-id
GOOGLE_OAUTH_CLIENT_ID_IOS=your-ios-client-id

# External APIs
GOOGLE_CSE_API_KEY=your-google-cse-api-key
GOOGLE_CSE_CX=your-google-cse-cx
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=models/gemini-1.5-flash-latest
```

### 환경 변수 적용 범위

각 환경 변수에 대해 적용 범위를 선택할 수 있습니다:
- **Production**: 프로덕션 배포에만 적용
- **Preview**: PR 미리보기 배포에 적용
- **Development**: 로컬 개발 환경 (`vercel dev`)에 적용

**권장**: 필수 변수는 세 가지 환경 모두에 설정하고, API 키 등은 Production과 Preview에만 설정하세요.

### 환경 변수 적용

환경 변수를 추가한 후:
1. **Save** 클릭
2. **Deployments** 탭으로 이동
3. 최신 배포의 **...** 메뉴에서 **Redeploy** 선택

## 배포 확인

### 1. 헬스 체크

배포 완료 후 브라우저에서 다음 URL을 확인:

```
https://your-project.vercel.app/health
```

예상 응답:
```json
{
  "status": "healthy",
  "service": "onmi-api-gateway",
  "version": "1.0.0"
}
```

### 2. API 문서 확인

FastAPI가 자동으로 생성한 API 문서 확인:

- Swagger UI: `https://your-project.vercel.app/docs`
- ReDoc: `https://your-project.vercel.app/redoc`

### 3. API 엔드포인트 테스트

```bash
# 루트 엔드포인트
curl https://your-project.vercel.app/

# 헬스 체크
curl https://your-project.vercel.app/health

# 회원가입 테스트 (예시)
curl -X POST https://your-project.vercel.app/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "test1234"
  }'
```

## Cron Job 설정 확인

### 1. Cron Job 상태 확인

1. Vercel 대시보드에서 **Settings** > **Cron Jobs** 이동
2. 다음 Cron Job이 자동으로 등록되어 있어야 합니다:
   - **Path**: `/api/cron/crawl`
   - **Schedule**: `0 */2 * * *` (2시간마다 실행)

### 2. Cron Job 수동 실행 (테스트)

Vercel 대시보드에서:
1. **Cron Jobs** 섹션에서 해당 Cron Job 선택
2. **Run Now** 버튼 클릭
3. 실행 로그 확인

또는 API로 직접 호출:

```bash
curl https://your-project.vercel.app/api/cron/crawl \
  -H "Authorization: Bearer your-cron-secret"
```

**참고**: `CRON_SECRET`을 설정한 경우에만 Authorization 헤더가 필요합니다.

### 3. Cron Job 로그 확인

1. Vercel 대시보드에서 **Deployments** 이동
2. Cron Job 실행 시 생성된 배포 선택
3. **Logs** 탭에서 실행 로그 확인

## 문제 해결

### 배포 실패

**증상**: 빌드 실패 또는 런타임 오류

**해결 방법**:
1. Vercel 대시보드의 **Deployments** > 해당 배포 > **Logs** 확인
2. `requirements.txt`에 모든 의존성이 포함되어 있는지 확인
3. Python 버전 확인 (Vercel은 Python 3.9+ 지원)
4. 환경 변수가 올바르게 설정되었는지 확인
5. `vercel.json` 설정이 올바른지 확인

### 데이터베이스 연결 오류

**증상**: `Connection refused` 또는 `timeout` 오류

**해결 방법**:
1. `DATABASE_URL` 또는 `SUPABASE_DB_URL`이 올바른지 확인
2. Supabase의 **Connection pooling** URI 사용 권장 (포트 6543)
3. Supabase 대시보드에서 데이터베이스가 활성 상태인지 확인
4. IP 화이트리스트 확인 (Supabase는 기본적으로 모든 IP 허용)

### 모듈을 찾을 수 없음 (ModuleNotFoundError)

**증상**: `ModuleNotFoundError: No module named 'xxx'`

**해결 방법**:
1. `requirements.txt`에 해당 모듈이 포함되어 있는지 확인
2. 루트 디렉토리의 `requirements.txt`를 사용하는지 확인
3. `PYTHONPATH` 환경 변수가 올바르게 설정되었는지 확인 (`vercel.json`에 이미 설정됨)

### 타임아웃 오류

**증상**: 요청이 10초(Hobby 플랜) 또는 60초(Pro 플랜) 후 타임아웃

**해결 방법**:
1. Vercel Pro 플랜으로 업그레이드 (60초 타임아웃)
2. 작업을 비동기로 처리하도록 리팩토링
3. 데이터베이스 쿼리 최적화
4. 불필요한 작업 제거
5. `vercel.json`의 `maxDuration` 설정 확인

### Cold Start 지연

**증상**: 첫 요청이 느림 (수 초 소요)

**해결 방법**:
1. Vercel Pro 플랜 사용 (더 빠른 Cold Start)
2. 데이터베이스 연결 풀 최적화
3. 자주 사용되는 엔드포인트에 Keep-alive 요청 설정
4. Vercel의 Edge Functions 고려 (가능한 경우)

### Cron Job이 실행되지 않음

**증상**: 크롤링이 자동으로 실행되지 않음

**해결 방법**:
1. Vercel **Cron Jobs** 섹션에서 상태 확인
2. Cron Job 로그 확인
3. `vercel.json`의 Cron 설정 확인
4. Vercel Pro 플랜 필요 여부 확인 (Hobby 플랜은 제한적)
5. Cron Job 엔드포인트가 올바르게 구현되었는지 확인

## 추가 최적화

### 1. 지역 설정

`vercel.json`에 `regions` 설정을 추가하여 배포 지역을 지정할 수 있습니다:

```json
{
  "regions": ["icn1"]
}
```

지원되는 지역:
- `icn1`: 서울, 대한민국
- `hnd1`: 도쿄, 일본
- `sin1`: 싱가포르
- `syd1`: 시드니, 호주

### 2. 모니터링 설정

- **Vercel Analytics**: 대시보드에서 활성화
- **Supabase 대시보드**: 데이터베이스 모니터링
- **Sentry**: 에러 추적 도구 통합 (선택사항)

### 3. 성능 최적화

- 데이터베이스 쿼리 최적화
- Redis 캐싱 추가 (Upstash 사용)
- CDN 활용 (Vercel이 자동 제공)

## 참고 자료

- [Vercel 공식 문서](https://vercel.com/docs)
- [Vercel Python 런타임](https://vercel.com/docs/functions/runtimes/python)
- [Vercel Cron Jobs](https://vercel.com/docs/cron-jobs)
- [Supabase 문서](https://supabase.com/docs)
- [FastAPI 문서](https://fastapi.tiangolo.com)

## 지원

문제가 발생하면:
1. 이 가이드의 문제 해결 섹션 확인
2. Vercel/Supabase 공식 문서 확인
3. GitHub Issues에 문제 보고

