# 데이터베이스 연결 문제 해결 가이드

## 현재 상황

모든 연결 테스트가 실패했습니다:
- ❌ Pooler 연결 (포트 5432, 6543): "Tenant or user not found"
- ❌ 직접 연결: "getaddrinfo failed" (DNS 조회 실패)

## 문제 원인 분석

### 1. "Tenant or user not found" 오류
이 오류는 다음 중 하나일 수 있습니다:
- Supabase 프로젝트가 비활성화되었거나 삭제됨
- 프로젝트 ref가 잘못됨
- 비밀번호가 잘못됨
- 사용자명 형식이 잘못됨

### 2. "getaddrinfo failed" 오류
이 오류는 다음 중 하나일 수 있습니다:
- 프로젝트가 삭제되어 호스트명이 더 이상 유효하지 않음
- 네트워크/DNS 문제
- 프로젝트 ref가 잘못됨

## 해결 방법

### 1단계: Supabase 프로젝트 상태 확인

1. [Supabase 대시보드](https://app.supabase.com)에 로그인
2. 프로젝트 목록에서 `giqqhzonfruynokwbguv` 프로젝트 확인
3. 프로젝트 상태 확인:
   - 프로젝트가 **활성화**되어 있는지 확인
   - 프로젝트가 **일시 중지**되지 않았는지 확인
   - 프로젝트가 **삭제**되지 않았는지 확인

### 2단계: 정확한 연결 문자열 확인

1. Supabase 대시보드에서 프로젝트 선택
2. **Settings** > **Database** 이동
3. **Connection string** 섹션에서 다음 확인:

#### Connection pooling (권장)
```
postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
```

#### Direct connection
```
postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres
```

**중요**: 대시보드에서 제공하는 연결 문자열을 **그대로 복사**하여 사용하세요.

### 3단계: .env 파일 업데이트

Supabase 대시보드에서 확인한 정확한 연결 문자열로 `.env` 파일을 업데이트하세요:

```env
# Connection pooling 사용 (권장)
DATABASE_URL=postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres

# 또는 Direct connection 사용
DATABASE_URL=postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres
```

**주의사항**:
- `[project-ref]`를 실제 프로젝트 ref로 교체
- `[password]`를 실제 데이터베이스 비밀번호로 교체
- `[region]`을 실제 리전으로 교체 (예: `ap-northeast-2`)

### 4단계: 연결 테스트

업데이트 후 연결 테스트 스크립트 실행:

```powershell
python test_db_connection.py
```

### 5단계: 프로젝트가 없는 경우

만약 Supabase 프로젝트가 삭제되었거나 더 이상 사용할 수 없다면:

#### 옵션 1: 새 Supabase 프로젝트 생성
1. [Supabase](https://supabase.com)에서 새 프로젝트 생성
2. 새 프로젝트의 연결 문자열로 `.env` 파일 업데이트
3. 데이터베이스 마이그레이션 실행

#### 옵션 2: 로컬 PostgreSQL 사용
`FIX_DATABASE.md` 파일을 참고하여 로컬 PostgreSQL을 사용할 수 있습니다.

## 연결 문자열 형식 가이드

### Pooler 연결 (서버리스 환경 권장)
```
postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
```

특징:
- 포트: **6543** (고정)
- 사용자명: `postgres.[project-ref]` 형식
- 연결 풀링 지원 (서버리스 환경에 적합)

### 직접 연결
```
postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres
```

특징:
- 포트: **5432** (고정)
- 사용자명: `postgres` (프로젝트 ref 없음)
- 직접 데이터베이스 연결

## 추가 확인 사항

### 비밀번호 특수문자 처리
비밀번호에 특수문자가 포함된 경우 URL 인코딩이 필요할 수 있습니다:
- `@` → `%40`
- `#` → `%23`
- `$` → `%24`
- `%` → `%25`

### 네트워크 확인
- 인터넷 연결 상태 확인
- 방화벽/프록시 설정 확인
- 회사 네트워크에서 Supabase 접근이 차단되지 않았는지 확인

### Supabase 무료 플랜 제한
- 무료 플랜은 일정 기간 비활성화 후 프로젝트가 일시 중지될 수 있습니다
- 프로젝트가 일시 중지된 경우 대시보드에서 재활성화 필요

## 문제가 계속되는 경우

1. **Supabase 지원팀에 문의**
   - 프로젝트 상태 확인
   - 연결 문제 진단

2. **새 프로젝트 생성**
   - 기존 프로젝트 대신 새 프로젝트 생성
   - 새 연결 문자열로 업데이트

3. **로컬 개발 환경 사용**
   - Docker Compose를 사용한 로컬 PostgreSQL
   - `FIX_DATABASE.md` 참고

## 참고 자료

- [Supabase 공식 문서 - 연결 문자열](https://supabase.com/docs/guides/database/connecting-to-postgres)
- [프로젝트 배포 가이드](./DEPLOYMENT.md)
- [Supabase 설정 가이드](./SUPABASE_SETUP.md)

