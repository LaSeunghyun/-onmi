# 변경 이력

## [Unreleased]

### 추가됨
- 키워드 조회 시 중복 기간 제외 기능
  - 기존에 조회한 일자는 제외하고 조회
  - 첫 조회인 경우 직전 하루만 수집
  - 수집 이력 추적을 위한 `fetch_history` 테이블 추가
- 요약 기능
  - 일일 요약: 사용자의 모든 키워드 통합 요약
  - 키워드별 요약: 특정 키워드에 대한 요약
  - 요약 세션 관리 (`summary_sessions` 테이블)
- 피드백 시스템
  - 좋아요/싫어요 피드백 제출 (1-5점 척도)
  - 피드백 통계 집계 및 분석
  - 피드백 기반 요약 품질 자동 개선
  - 사용자 선호도 관리 (`user_preferences` 테이블)
- 수동 수집 API
  - `POST /keywords/{keyword_id}/collect` 엔드포인트 추가
  - 명시적 날짜 범위 지정 지원
- 요약 API
  - `GET /summaries/daily` - 일일 요약 조회
  - `GET /summaries/keywords/{keyword_id}` - 키워드별 요약 조회
  - `POST /summaries/{summary_session_id}/feedback` - 피드백 제출
- 리포지토리 패턴 도입
  - `KeywordRepository`, `ArticleRepository`, `FetchHistoryRepository` 등
  - 데이터 접근 계층과 비즈니스 로직 분리
- 워크플로우 서비스 계층
  - `WorkflowService`: 수집 및 요약 오케스트레이션
  - `SummaryService`: 요약 생성 서비스
  - `FeedbackService`: 피드백 분석 서비스
- 도메인 모델
  - `FetchHistory`, `SummarySession`, `Feedback`, `DateRange`
- 크롤러 날짜 필터링
  - RSS 수집기에 날짜 범위 파라미터 추가
  - 크롤러 워커에 중복 기간 제외 로직 적용

### 변경됨
- 크롤러 워커가 `last_crawled_at`을 확인하여 증분 수집 수행
- RSS 수집기가 날짜 범위 필터링 지원

### 문서화
- `docs/workflow.md` - 워크플로우 다이어그램 및 설명 추가
- `docs/fetch_feedback_logic.md` - 수집 및 피드백 로직 상세 문서 추가
- `README.md` - 새 기능 및 API 사용법 추가

## [1.0.0] - 초기 릴리스

### 추가됨
- 사용자 인증 및 관리
- 키워드 관리 (최대 3개)
- RSS 기반 뉴스 수집
- 감성 분석
- 피드 조회 및 필터링
- 기사 상세 조회
- 통계 API

