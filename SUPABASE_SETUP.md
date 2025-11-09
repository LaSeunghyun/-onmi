# Supabase 데이터베이스 테이블 생성 가이드

이 문서는 #onmi 프로젝트의 데이터베이스 테이블을 Supabase에 생성하는 방법을 설명합니다.

## 사전 요구사항

- Supabase 계정 (무료 플랜 가능)
- Supabase 프로젝트 생성 완료

## 방법 1: Supabase 대시보드에서 실행 (권장)

### 1단계: Supabase 프로젝트 접속

1. [Supabase](https://supabase.com)에 로그인
2. 프로젝트 선택 또는 새 프로젝트 생성

### 2단계: SQL Editor 열기

1. 왼쪽 사이드바에서 **SQL Editor** 클릭
2. **New Query** 버튼 클릭

### 3단계: SQL 스크립트 실행

1. `supabase_migration.sql` 파일의 내용을 복사
2. SQL Editor에 붙여넣기
3. **Run** 버튼 클릭 (또는 `Ctrl+Enter`)

### 4단계: 실행 결과 확인

성공 메시지가 표시되면 테이블이 생성된 것입니다:
```
✅ #onmi 데이터베이스 스키마가 성공적으로 생성되었습니다!
```

### 5단계: 테이블 확인

1. 왼쪽 사이드바에서 **Table Editor** 클릭
2. 다음 테이블들이 생성되었는지 확인:
   - `users`
   - `keywords`
   - `articles`
   - `keyword_articles`
   - `sentiments`
   - `user_actions`
   - `share_history`

## 방법 2: Supabase CLI 사용 (고급)

### 1단계: Supabase CLI 설치

```powershell
# Windows (PowerShell)
npm install -g supabase
```

또는

```powershell
# Scoop 사용
scoop bucket add supabase https://github.com/supabase/scoop-bucket.git
scoop install supabase
```

### 2단계: Supabase 로그인

```powershell
supabase login
```

### 3단계: 프로젝트 연결

```powershell
# 프로젝트 ID 확인 (Supabase 대시보드 > Settings > General > Reference ID)
supabase link --project-ref your-project-ref
```

### 4단계: 마이그레이션 실행

```powershell
# SQL 파일 직접 실행
supabase db execute -f supabase_migration.sql
```

## 생성되는 테이블 구조

### 1. users
- 사용자 정보 저장
- 필드: id, email, password_hash, locale, created_at, updated_at

### 2. keywords
- 사용자별 키워드 저장
- 필드: id, user_id, text, status, notify_level, auto_share_enabled, auto_share_channels, created_at, updated_at, last_crawled_at

### 3. articles
- 수집된 기사 정보 저장
- 필드: id, url, source, title, snippet, published_at, thumbnail_url_hash, lang, created_at, updated_at

### 4. keyword_articles
- 키워드와 기사의 매핑 관계 저장
- 필드: id, keyword_id, article_id, match_score, match_type, created_at

### 5. sentiments
- 기사의 감정 분석 결과 저장
- 필드: id, article_id, label, score, rationale, model_ver, created_at, updated_at

### 6. user_actions
- 사용자 액션 (저장, 공유, 피드백) 저장
- 필드: id, user_id, article_id, action, payload, created_at

### 7. share_history
- 공유 히스토리 저장 (통계 최적화)
- 필드: id, user_id, article_id, keyword_id, channel, recipient, shared_at

## 주요 기능

### 자동 업데이트 타임스탬프
- `updated_at` 필드가 자동으로 갱신됩니다
- 트리거 함수를 통해 자동 관리됩니다

### 인덱스 최적화
- 자주 조회되는 필드에 인덱스가 생성되어 있습니다
- 쿼리 성능이 최적화되어 있습니다

### 데이터 무결성
- 외래 키 제약 조건으로 데이터 일관성 보장
- CHECK 제약 조건으로 데이터 유효성 검증

## 문제 해결

### 오류: "relation already exists"
- 테이블이 이미 존재하는 경우 발생
- `CREATE TABLE IF NOT EXISTS` 구문을 사용하므로 안전하게 재실행 가능
- 기존 데이터는 유지됩니다

### 오류: "permission denied"
- 데이터베이스 권한이 부족한 경우
- Supabase 프로젝트의 Owner 권한이 필요합니다

### 테이블이 보이지 않음
- **Table Editor**에서 새로고침 (F5)
- 또는 **Database** > **Tables**에서 확인

## 다음 단계

1. **환경 변수 설정**: `.env` 파일에 `DATABASE_URL` 설정
2. **연결 테스트**: 백엔드 애플리케이션에서 데이터베이스 연결 확인
3. **데이터 입력**: 테스트 데이터로 기능 확인

## 참고 자료

- [Supabase 공식 문서](https://supabase.com/docs)
- [PostgreSQL 문서](https://www.postgresql.org/docs/)
- [프로젝트 배포 가이드](./DEPLOYMENT.md)

