# Vercel + Supabase 배포 가이드

이 문서는 #onmi 프로젝트를 Vercel과 Supabase를 사용하여 서버리스 환경에 배포하는 방법을 설명합니다.

## 목차

1. [사전 요구사항](#사전-요구사항)
2. [Supabase 설정](#supabase-설정)
3. [Vercel 배포](#vercel-배포)
4. [환경 변수 설정](#환경-변수-설정)
5. [데이터베이스 마이그레이션](#데이터베이스-마이그레이션)
6. [테스트 및 검증](#테스트-및-검증)
7. [문제 해결](#문제-해결)

## 사전 요구사항

- GitHub 계정
- Vercel 계정 (무료 플랜 가능)
- Supabase 계정 (무료 플랜 가능)

## Supabase 설정

### 1. Supabase 프로젝트 생성

1. [Supabase](https://supabase.com)에 로그인
2. "New Project" 클릭
3. 프로젝트 정보 입력:
   - **Name**: onmi (또는 원하는 이름)
   - **Database Password**: 강력한 비밀번호 설정 (나중에 필요)
   - **Region**: 가장 가까운 리전 선택
4. 프로젝트 생성 완료 대기 (약 2분)

### 2. 데이터베이스 연결 정보 확인

1. Supabase 대시보드에서 프로젝트 선택
2. **Settings** > **Database** 이동
3. **Connection string** 섹션에서 다음 정보 확인:
   - **Connection pooling** 모드의 URI (포트 6543)
   - 또는 **Direct connection** 모드의 URI (포트 5432)

   예시:
   ```
   postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
   ```

### 3. 데이터베이스 스키마 생성

1. Supabase 대시보드에서 **SQL Editor** 열기
2. 다음 SQL 스크립트 실행:

```sql
-- #onmi 데이터베이스 스키마 초기화

-- users 테이블
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    locale VARCHAR(10) DEFAULT 'ko-KR',
    created_at TIMESTAMP DEFAULT NOW()
);

-- keywords 테이블
CREATE TABLE IF NOT EXISTS keywords (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    text VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    notify_level VARCHAR(20) DEFAULT 'standard',
    auto_share_enabled BOOLEAN DEFAULT FALSE,
    auto_share_channels JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP DEFAULT NOW(),
    last_crawled_at TIMESTAMP
);

-- articles 테이블
CREATE TABLE IF NOT EXISTS articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url TEXT UNIQUE NOT NULL,
    source VARCHAR(255),
    title TEXT NOT NULL,
    snippet TEXT,
    published_at TIMESTAMP,
    thumbnail_url_hash VARCHAR(64),
    lang VARCHAR(10) DEFAULT 'ko',
    created_at TIMESTAMP DEFAULT NOW()
);

-- keyword_articles 매핑 테이블
CREATE TABLE IF NOT EXISTS keyword_articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    keyword_id UUID REFERENCES keywords(id) ON DELETE CASCADE,
    article_id UUID REFERENCES articles(id) ON DELETE CASCADE,
    match_score FLOAT DEFAULT 1.0,
    match_type VARCHAR(20) DEFAULT 'exact',
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(keyword_id, article_id)
);

-- sentiments 테이블
CREATE TABLE IF NOT EXISTS sentiments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id UUID REFERENCES articles(id) ON DELETE CASCADE,
    label VARCHAR(10) CHECK (label IN ('positive', 'negative', 'neutral')),
    score FLOAT NOT NULL,
    rationale JSONB,
    model_ver VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(article_id)
);

-- user_actions 테이블
CREATE TABLE IF NOT EXISTS user_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    article_id UUID REFERENCES articles(id) ON DELETE CASCADE,
    action VARCHAR(20) CHECK (action IN ('save', 'share', 'feedback')),
    payload JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- share_history 테이블
CREATE TABLE IF NOT EXISTS share_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    article_id UUID REFERENCES articles(id) ON DELETE CASCADE,
    keyword_id UUID REFERENCES keywords(id) ON DELETE SET NULL,
    channel VARCHAR(50) NOT NULL,
    recipient VARCHAR(255),
    shared_at TIMESTAMP DEFAULT NOW()
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_articles_url ON articles(url);
CREATE INDEX IF NOT EXISTS idx_articles_published_at ON articles(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_sentiments_article_id ON sentiments(article_id);
CREATE INDEX IF NOT EXISTS idx_keyword_articles_keyword_id ON keyword_articles(keyword_id);
CREATE INDEX IF NOT EXISTS idx_keywords_user_id ON keywords(user_id);
CREATE INDEX IF NOT EXISTS idx_user_actions_user_article ON user_actions(user_id, article_id);
CREATE INDEX IF NOT EXISTS idx_share_history_user_keyword ON share_history(user_id, keyword_id);
CREATE INDEX IF NOT EXISTS idx_share_history_shared_at ON share_history(shared_at DESC);
CREATE INDEX IF NOT EXISTS idx_keyword_articles_created_at ON keyword_articles(created_at DESC);
```

3. **Run** 버튼 클릭하여 스크립트 실행

## Vercel 배포

### 1. GitHub 저장소 준비

1. 프로젝트를 GitHub에 푸시 (아직 안 했다면):
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/[username]/onmi.git
   git push -u origin main
   ```

### 2. Vercel 프로젝트 생성

1. [Vercel](https://vercel.com)에 로그인
2. **Add New** > **Project** 클릭
3. GitHub 저장소 선택 또는 import
4. 프로젝트 설정:
   - **Framework Preset**: Other
   - **Root Directory**: `./` (루트 디렉토리)
   - **Build Command**: (비워둠 - Vercel이 자동 감지)
   - **Output Directory**: (비워둠)
   - **Install Command**: `pip install -r requirements.txt`
5. **Deploy** 클릭

### 3. 환경 변수 설정

배포 후 **Settings** > **Environment Variables**에서 다음 변수 추가:

#### 필수 변수

```
DATABASE_URL=postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
JWT_SECRET=your-strong-random-secret-key-here
```

#### 선택 변수

```
SCHEDULER_INTERVAL_HOURS=2
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000
RSS_SOURCES=https://rss.cnn.com/rss/edition.rss,https://feeds.bbci.co.uk/news/rss.xml
CRON_SECRET=your-cron-secret-key
```

**주의사항:**
- `JWT_SECRET`은 강력한 랜덤 문자열로 설정 (예: `openssl rand -hex 32`)
- `DATABASE_URL`은 Supabase의 Connection pooling URI 사용 권장
- 환경 변수 추가 후 **Redeploy** 필요

### 4. Vercel Cron Jobs 확인

1. **Settings** > **Cron Jobs** 확인
2. `vercel.json`에 정의된 Cron Job이 자동으로 등록됨:
   - **Path**: `/api/cron/crawl`
   - **Schedule**: `0 */2 * * *` (2시간마다)

## 환경 변수 설정

### 로컬 개발 환경

1. `env.example` 파일을 `.env`로 복사:
   ```bash
   cp env.example .env
   ```

2. `.env` 파일 편집하여 실제 값 입력:
   ```env
   DATABASE_URL=postgresql://postgres:[password]@[host]:5432/postgres
   JWT_SECRET=your-secret-key
   ```

### Vercel 환경 변수

Vercel 대시보드에서 환경 변수를 설정하면:
- **Production**: 프로덕션 배포에 사용
- **Preview**: PR 미리보기에 사용
- **Development**: 로컬 개발에 사용 (`vercel dev`)

## 데이터베이스 마이그레이션

스키마는 Supabase SQL Editor에서 이미 생성했지만, 추가 마이그레이션이 필요한 경우:

1. Supabase SQL Editor에서 마이그레이션 스크립트 실행
2. 또는 Supabase CLI 사용:
   ```bash
   npm install -g supabase
   supabase db push
   ```

## 테스트 및 검증

### 1. API 엔드포인트 테스트

배포 완료 후 Vercel에서 제공하는 URL로 테스트:

```bash
# 헬스 체크
curl https://your-project.vercel.app/health

# API 문서 확인
# 브라우저에서 https://your-project.vercel.app/docs 접속
```

### 2. 회원가입 테스트

```bash
curl -X POST https://your-project.vercel.app/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "test1234"
  }'
```

### 3. Cron Job 테스트

```bash
curl https://your-project.vercel.app/api/cron/crawl \
  -H "Authorization: Bearer your-cron-secret"
```

또는 Vercel 대시보드에서 **Cron Jobs** 섹션에서 수동 실행 가능.

## 문제 해결

### 데이터베이스 연결 오류

**증상**: `Connection refused` 또는 `timeout` 오류

**해결 방법:**
1. `DATABASE_URL`이 올바른지 확인
2. Supabase의 **Connection pooling** URI 사용 (포트 6543)
3. Supabase 대시보드에서 데이터베이스가 활성 상태인지 확인
4. IP 화이트리스트 확인 (Supabase는 기본적으로 모든 IP 허용)

### Vercel 배포 실패

**증상**: 빌드 실패 또는 런타임 오류

**해결 방법:**
1. Vercel 로그 확인: **Deployments** > 해당 배포 > **Logs**
2. `requirements.txt`에 모든 의존성이 포함되어 있는지 확인
3. Python 버전 확인 (Vercel은 Python 3.9+ 지원)
4. 환경 변수가 올바르게 설정되었는지 확인

### Cron Job이 실행되지 않음

**증상**: 크롤링이 자동으로 실행되지 않음

**해결 방법:**
1. Vercel **Cron Jobs** 섹션에서 상태 확인
2. Cron Job 로그 확인
3. `vercel.json`의 Cron 설정 확인
4. Pro 플랜 필요 여부 확인 (Hobby 플랜은 제한적)

### 타임아웃 오류

**증상**: 요청이 10초(Hobby) 또는 60초(Pro) 후 타임아웃

**해결 방법:**
1. Vercel Pro 플랜으로 업그레이드 (60초 타임아웃)
2. 작업을 비동기로 처리하도록 리팩토링
3. 데이터베이스 쿼리 최적화
4. 불필요한 작업 제거

### Cold Start 지연

**증상**: 첫 요청이 느림

**해결 방법:**
1. Vercel Pro 플랜 사용 (더 빠른 Cold Start)
2. 데이터베이스 연결 풀 최적화 (이미 적용됨)
3. 자주 사용되는 엔드포인트에 Keep-alive 요청 설정

## 추가 최적화

### 1. Redis 캐싱 (선택사항)

Upstash Redis를 사용하여 캐싱 추가:

1. [Upstash](https://upstash.com)에서 Redis 생성
2. `REDIS_URL` 환경 변수 설정
3. 코드에서 Redis 사용 (현재는 선택사항)

### 2. Supabase Storage (선택사항)

썸네일 이미지 저장용:

1. Supabase 대시보드에서 **Storage** 생성
2. 버킷 생성
3. `STORAGE_TYPE=supabase` 및 `STORAGE_BUCKET` 설정

### 3. 모니터링

- Vercel Analytics 사용
- Supabase 대시보드에서 데이터베이스 모니터링
- Sentry 등 에러 추적 도구 통합

## 참고 자료

- [Vercel 문서](https://vercel.com/docs)
- [Supabase 문서](https://supabase.com/docs)
- [FastAPI 문서](https://fastapi.tiangolo.com)
- [Vercel Cron Jobs](https://vercel.com/docs/cron-jobs)

## 지원

문제가 발생하면:
1. 이 가이드의 문제 해결 섹션 확인
2. Vercel/Supabase 공식 문서 확인
3. GitHub Issues에 문제 보고









