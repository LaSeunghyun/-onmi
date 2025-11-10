# 변경 이력

## [Unreleased]

### 추가됨
- `backend/shared/__init__.py` - 공유 모듈 네임스페이스를 명시적으로 선언
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
- Google CSE 쿼리 제한 관리
  - `cse_query_usage` 테이블 및 마이그레이션 추가
  - `CSEQueryLimitService`로 유저/키워드별 일일 쿼리 제한 계산
  - `/stats/cse-query-usage` API로 잔여 쿼리 수 제공
  - 모바일 홈 화면에 "조회 가능 쿼리수" 표시 및 자동 갱신

### 변경됨
- Vercel Python 함수 번들이 `backend/shared/**`, `backend/api-gateway/src/**`, `config/**`를 포함하고 불필요한 캐시·가상환경 파일을 제외하도록 `vercel.json`을 조정
- `api/index.py`가 경로 존재 여부를 검사하고 중복 삽입을 방지하는 로그를 출력하도록 개선
- 크롤러 워커가 `last_crawled_at`을 확인하여 증분 수집 수행
- RSS 수집기가 날짜 범위 필터링 지원
- 키워드 삭제 시 상태를 `archived`로 전환하도록 수정하여 데이터베이스 `keywords_status_check` 제약 조건과 일관성 유지
- 모바일 앱 설정 화면의 헤더 하단 여백을 축소하고 변경 사항 저장 버튼을 추가하여 가독성을 개선
- 키워드 및 알림 시간 선호도가 즉시 저장되던 플로우를 저장 버튼 클릭 시 일괄 반영되도록 변경하고 사용자별 시간 설정을 유지

### 문서화
- README.md - Vercel 배포 체크리스트 및 임포트 검증 절차 추가
- `docs/workflow.md` - 워크플로우 다이어그램 및 설명 추가
- `docs/fetch_feedback_logic.md` - 수집 및 피드백 로직 상세 문서 추가
- `README.md` - 새 기능 및 API 사용법 추가
- `README.md` - 설정 화면 저장 절차 안내 업데이트
- `docs/settings_persistence.md` - 설정 저장 및 동기화 흐름 정리
- `docs/cse_query_limit.md` - Google CSE 쿼리 분배 및 모니터링 정책 문서화

## [1.0.0] - 초기 릴리스

### 추가됨
- 사용자 인증 및 관리
- 키워드 관리 (최대 3개)
- RSS 기반 뉴스 수집
- 감성 분석
- 피드 조회 및 필터링
- 기사 상세 조회
- 통계 API

