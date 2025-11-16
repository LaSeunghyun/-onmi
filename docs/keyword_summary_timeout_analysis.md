# 키워드 요약 타임아웃 문제 분석 및 개선 방안

## 문제 현상

메인 페이지 접속 시 키워드 요약 API가 10초 타임아웃으로 실패하는 문제가 발생합니다.

```
I/flutter (12609): [API Error] DioExceptionType.receiveTimeout 
http://10.0.2.2:8000/summaries/keywords/4021cbcc-fa9d-41bf-9643-f62f6c0d0122?date=2025-11-14 (10090.8 ms)
Message: The request took longer than 0:00:10.000000 to receive data.
```

## 원인 분석

### 1. 로그 분석 결과

#### 1.1 요약 생성 시간 분석
- **Gemini API 호출 시간**: 9.5초 ~ 22초
  - `Summarizer.generate.keyword` 구간이 가장 오래 걸림
  - 예시: 13.8초, 9.8초, 22초 등
- **데이터베이스 쿼리 시간**: 상대적으로 빠름 (200-400ms)
  - `ArticleRepository.fetch_recent_by_keyword`: 300ms
  - `SummarySessionRepository` 조회: 230-300ms
  - `FeedbackRepository.aggregate_by_keyword`: 220-230ms

#### 1.2 중복 호출 문제
같은 키워드에 대해 짧은 시간 내 여러 번 요약 생성이 시도됨:
- `4021cbcc-fa9d-41bf-9643-f62f6c0d0122`: 07:37:48, 07:37:58에 연속 호출
- `36963ab7-36b2-42fe-8bc6-583f8a8b6475`: 동시에 여러 요청 발생

#### 1.3 타임라인 분석 (예시)
```
07:37:48.722 - SummaryService.generate_keyword_summary 시작
07:37:48.964 - ArticleRepository.fetch_recent_by_keyword 시작 (307ms)
07:37:49.273 - Summarizer.generate.keyword 시작 (Gemini API 호출)
07:38:03.096 - Summarizer.generate.keyword 완료 (13.8초 소요)
07:38:03.501 - SummarySessionRepository.create 완료
총 소요 시간: 약 14.8초
```

### 2. 코드 분석

#### 2.1 클라이언트 측 (Flutter)
- **타임아웃 설정**: `receiveTimeout: 10초` (api_service.dart:34)
- **동작 방식**: 
  - `KeywordSummaryNotifier`가 생성자에서 `loadSummary()` 호출
  - API 응답을 기다리는 동안 로딩 상태 유지
  - 10초 내 응답이 없으면 타임아웃 발생

#### 2.2 서버 측 (FastAPI)
- **동작 흐름** (`summaries.py:289-480`):
  1. 요약 세션 조회 (DB)
  2. 요약이 없으면 즉시 `generate_keyword_summary()` 호출
  3. Gemini API 호출 완료까지 동기식 대기
  4. 완료 후 응답 반환

- **병목 구간**:
  - `Summarizer.generate()` → Gemini API 호출 (9-22초)
  - 동기식 처리로 인해 클라이언트가 전체 시간 동안 대기

## 개선 방안

### 방안 1: 비동기 워크플로우 전환 (권장)

**개요**: 요약이 없을 때 즉시 "생성 중" 상태를 반환하고, 백그라운드에서 생성

**구현 방법**:
1. **서버 측**:
   - 요약이 없으면 `202 Accepted` 상태와 함께 `status: "pending"` 반환
   - 백그라운드 태스크로 요약 생성 시작
   - 생성 완료 후 DB에 저장

2. **클라이언트 측**:
   - `pending` 상태일 때 폴링 또는 웹소켓으로 상태 확인
   - 또는 백그라운드에서 생성되면 자동으로 새로고침

**장점**:
- 클라이언트 타임아웃 문제 해결
- 사용자 경험 개선 (즉시 응답)
- 서버 리소스 효율적 사용

**단점**:
- 폴링 구현 필요
- 상태 관리 복잡도 증가

**우선순위**: 높음

### 방안 2: 중복 요청 방지

**개요**: 같은 키워드에 대한 동시 요청을 하나로 통합

**구현 방법**:
1. **서버 측**:
   - 요약 생성 중인 키워드 추적 (in-memory cache 또는 Redis)
   - 동일 키워드 요청 시 기존 태스크 반환 또는 대기

2. **클라이언트 측**:
   - 요청 중인 키워드 추적
   - 중복 요청 방지

**장점**:
- 불필요한 Gemini API 호출 감소
- 서버 부하 감소

**단점**:
- 상태 관리 로직 필요

**우선순위**: 중간

### 방안 3: 클라이언트 타임아웃 증가

**개요**: `receiveTimeout`을 30초 이상으로 증가

**구현 방법**:
```dart
// mobile/lib/services/api_service.dart
receiveTimeout: const Duration(seconds: 30),
```

**장점**:
- 구현 간단
- 즉시 적용 가능

**단점**:
- 근본적인 해결책 아님
- 사용자 대기 시간 증가
- 네트워크 불안정 시 여전히 실패 가능

**우선순위**: 낮음 (임시 조치용)

### 방안 4: 요약 사전 생성 (Cron Job)

**개요**: 사용자가 요청하기 전에 미리 요약 생성

**구현 방법**:
- 기존 `daily-report.py` 크론 작업 활용
- 키워드별 요약도 함께 생성

**장점**:
- 사용자 요청 시 즉시 응답 가능
- 타임아웃 문제 완전 해결

**단점**:
- 사용하지 않는 키워드도 생성 (리소스 낭비)
- 실시간성 저하

**우선순위**: 중간

### 방안 5: 요약 생성 최적화

**개요**: Gemini API 호출 시간 단축

**구현 방법**:
1. 프롬프트 최적화
2. 기사 수 제한 (현재 50개 → 30개)
3. 모델 변경 (더 빠른 모델 사용)

**장점**:
- 근본적인 성능 개선

**단점**:
- 요약 품질 저하 가능성
- 효과 제한적 (여전히 5-10초 소요 가능)

**우선순위**: 낮음

## 권장 구현 순서

1. **1단계 (즉시 적용)**: 방안 3 - 클라이언트 타임아웃 증가
   - 빠른 임시 조치
   - 사용자 경험 개선

2. **2단계 (단기)**: 방안 2 - 중복 요청 방지
   - 서버 부하 감소
   - 불필요한 API 호출 방지

3. **3단계 (중기)**: 방안 1 - 비동기 워크플로우
   - 근본적인 해결
   - 최적의 사용자 경험

4. **4단계 (장기)**: 방안 4 - 요약 사전 생성
   - 완벽한 사용자 경험
   - 리소스 최적화 필요

## 참고 파일

- `backend/api-gateway/src/routes/summaries.py`: 키워드 요약 API 엔드포인트
- `backend/api-gateway/src/services/summary_service.py`: 요약 생성 서비스
- `mobile/lib/services/api_service.dart`: 클라이언트 API 서비스
- `mobile/lib/providers/summary_provider.dart`: 요약 상태 관리
- `backend/logs/api-gateway.log`: 성능 로그

## 적용 내역 (2025-11-14)

- 키워드 요약 API는 요약 부재 시 `202 Accepted`와 `status: "pending"` 응답을 반환하고, `PendingSummaryRegistry`로 비동기 생성을 관리함.
- 모바일 `KeywordSummaryNotifier`는 `pending` 응답을 감지해 최대 5회까지 자동 폴링하며, 성공 시 캐시를 갱신하고 실패 시 에러를 노출함.
- `ApiService` 타임아웃을 30초로 상향해 생성 지연 동안 클라이언트 타임아웃을 완화함.
- `api/cron/daily-report.py`는 활성 키워드 요약을 사전 생성해 첫 요청에서도 즉시 응답 가능성을 높임.

