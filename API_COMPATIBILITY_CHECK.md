# API 호환성 검사 결과

## ✅ 수정 완료

### 1. 로그인 API (`/auth/signin`)
- **문제**: Dio가 JSON 형식으로 전송했지만 백엔드는 `application/x-www-form-urlencoded` 형식을 요구
- **해결**: `FormData.fromMap()` 사용하여 올바른 형식으로 전송하도록 수정

### 2. Import 경로 문제
- **문제**: `from routes.auth import` → 모듈을 찾을 수 없음
- **해결**: `from src.routes.auth import`로 수정

## 📋 API 엔드포인트 비교

### 인증 API

#### POST `/auth/signup`
- **백엔드**: `SignUpRequest` (email, password, locale)
- **프론트엔드**: `{email, password}` ✅
- **상태**: 호환됨 (locale은 기본값 사용)

#### POST `/auth/signin`
- **백엔드**: `OAuth2PasswordRequestForm` (username, password) - form-data 형식
- **프론트엔드**: `FormData.fromMap({username, password})` ✅
- **상태**: 수정 완료

#### GET `/auth/me`
- **백엔드**: `User` (id, email, locale)
- **프론트엔드**: `User.fromJson()` ✅
- **상태**: 호환됨

### 키워드 API

#### GET `/keywords`
- **백엔드**: `List[KeywordResponse]`
- **프론트엔드**: `List<Keyword>` ✅
- **상태**: 호환됨

#### POST `/keywords`
- **백엔드**: `KeywordCreate` (text) → `KeywordResponse`
- **프론트엔드**: `{text}` → `Keyword` ✅
- **상태**: 호환됨

#### DELETE `/keywords/{keyword_id}`
- **백엔드**: 204 No Content
- **프론트엔드**: `void` ✅
- **상태**: 호환됨

### 피드 API

#### GET `/feed`
- **백엔드**: `{items: List[ArticleFeedItem], total, page, page_size}`
- **프론트엔드**: `FeedResponse` ✅
- **상태**: 호환됨

### 기사 API

#### GET `/articles/{article_id}`
- **백엔드**: `ArticleDetail` (keywords: List[str])
- **프론트엔드**: `Article` (keywords: List<String>) ✅
- **상태**: 호환됨

#### POST `/articles/{article_id}/feedback`
- **백엔드**: `FeedbackRequest` (label, comment?)
- **프론트엔드**: `{label, comment?}` ✅
- **상태**: 호환됨

### 공유 API

#### POST `/share/articles/{article_id}`
- **백엔드**: `ShareRequest` (channel, recipient?)
- **프론트엔드**: `{channel, recipient?}` ✅
- **상태**: 호환됨

## 🔍 확인 필요 사항

1. **날짜 형식**: 백엔드는 `datetime` 객체를 반환하지만, Flutter에서 문자열로 파싱하는지 확인 필요
2. **에러 처리**: 422 에러 발생 시 상세 메시지 확인 필요


