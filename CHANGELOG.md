# 변경 이력

## [Unreleased]

### 추가됨
- `backend/api-gateway/src/utils/pending_summary_registry.py` - 키워드 요약 생성 중복 요청을 차단하고 진행 상태를 추적하는 레지스트리 추가
- 키워드 요약 API가 요약 부재 시 `status: "pending"` 응답을 즉시 반환하고, FastAPI에서 비동기 태스크로 Gemini 요약 생성을 수행하도록 개선
- 모바일 `KeywordSummaryNotifier`가 서버의 `pending` 응답을 감지해 자동 폴링(최대 5회)으로 새 요약을 재요청하도록 로직 추가
- `api/cron/daily-report.py`가 사용자별 활성 키워드 요약을 사전 생성해 최초 요청에서도 빠르게 응답하도록 개선
- `docs/keyword_summary_timeout_analysis.md` - 키워드 요약 타임아웃 원인 및 대응 전략 문서화
- 모바일 요약 상태를 enum(`SummaryStatus`)으로 관리하여 `loading`(조회중), `pending`(조회전), `error`(에러), `success`(성공) 상태를 명확히 구분
- 모바일 홈 요약 카드에 "조회중" 및 "조회전" 안내 상태 카드를 추가하고 즉시 재시도 버튼을 제공
- 모바일 `summary_parser.dart` 유틸을 도입해 Gemini 요약 텍스트를 일관된 섹션 단위로 파싱하고 다중 화면에서 재사용
- 성능 계측 및 로딩 개선 도구
  - 모바일 앱에 `PerformanceMonitor`와 요약 스켈레톤 UI를 도입하여 상세 화면 진입 시 체감 속도를 향상
  - FastAPI 게이트웨이에 `utils.performance` 모듈을 추가해 SSR 파이프라인의 구간별 소요 시간을 로깅
  - 요약 데이터(Hive)와 API 응답 캐싱을 연동해 접근 즉시 콘텐츠를 노출
- 요약 데이터 과거일자 조회 개선
  - `summary_sessions` 테이블에 날짜 기반 인덱스 추가
  - `GET /summaries/daily`, `GET /summaries/keywords/{keyword_id}`에 날짜 쿼리 파라미터 및 `available_dates` 응답 필드 추가
  - 모바일 홈 화면 날짜 선택 위젯이 데이터가 있는 날짜만 선택 가능하도록 개선하고, 데이터 부재 시 안내 메시지 노출
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
- Flutter `ApiService`의 `connectTimeout`/`receiveTimeout`을 30초로 상향해 장시간 요약 생성 시 타임아웃을 완화
- 모바일 요약 캐시가 `status: "pending"` 응답은 저장하지 않도록 조정하고, 재시도 한도를 초과하면 명확한 에러 메시지를 노출
- 키워드 요약 API가 요약 부재 시 비동기 생성을 예약하고 202 응답을 반환하도록 변경
- 모바일 `DailySummaryState`가 `isLoading`, `isPending` boolean 필드 대신 `SummaryStatus` enum을 사용하여 상태 관리를 단순화하고 타입 안정성 향상
- 모바일 `InsightSummaryCard`가 `SummaryStatus` enum 기반으로 UI를 분기 처리하여 상태별 적절한 카드(조회중/조회전/에러/성공)를 표시
- FastAPI `GET /summaries/daily` 및 `GET /summaries/keywords/{keyword_id}`가 404 응답 시 `code`, `articles_count`, `available_dates`를 포함해 프론트엔드가 조회전 상태를 식별할 수 있도록 개선
- 모바일 홈 키워드 필터가 요약 응답의 `articlesCount`를 활용해 전체/키워드별 기사 수를 동적으로 표시하고 데이터 부재 시 0건으로 노출
- 모바일 홈 키워드 필터 숫자가 기사 수 대신 요약 섹션 개수를 표시하며 키워드 전환 시에도 값을 유지하도록 로직을 정비
- 모바일 홈 `InsightSummaryCard`가 요약을 전체·주제별 카드 섹션으로 시각화하고, 상세 화면이 섹션 제목(볼드)과 불릿 리스트로 내용을 재배치하도록 UX 개선
- `SummaryDetailScreen`이 기사 본문 링크 기능을 유지한 채 섹션 단위 레이아웃으로 재구성되어 가독성이 향상
- `SummaryService`의 Gemini 프롬프트가 `**제목**` + 불릿 형식으로 응답을 강제해 요약 구조가 일관되도록 개선
- 요약 API가 날짜 목록 조회와 요약 본문 조회를 병렬 처리하고, 기사 개수 산출을 경량화된 `COUNT` 쿼리로 대체하여 응답 시간을 단축
- `SummaryService`가 기사 조회와 피드백 집계를 `asyncio.gather`로 실행하고 토큰 사용량 기록을 비동기 태스크로 처리
- Vercel Python 함수 번들이 `backend/shared/**`, `backend/api-gateway/src/**`, `config/**`를 포함하고 불필요한 캐시·가상환경 파일을 제외하도록 `vercel.json`을 조정
- `api/index.py`가 경로 존재 여부를 검사하고 중복 삽입을 방지하는 로그를 출력하도록 개선
- 크롤러 워커가 `last_crawled_at`을 확인하여 증분 수집 수행
- RSS 수집기가 날짜 범위 필터링 지원
- 키워드 삭제 시 상태를 `archived`로 전환하도록 수정하여 데이터베이스 `keywords_status_check` 제약 조건과 일관성 유지
- 모바일 앱 설정 화면의 헤더 하단 여백을 축소하고 변경 사항 저장 버튼을 추가하여 가독성을 개선
- 키워드 및 알림 시간 선호도가 즉시 저장되던 플로우를 저장 버튼 클릭 시 일괄 반영되도록 변경하고 사용자별 시간 설정을 유지
- 일일 리포트 크론 작업이 실행 시점의 UTC와 한국시간을 모두 기록하고, KST 기준 알림 시간과 일치하는 사용자만 대상으로 요약을 생성하도록 로직을 조정
- 사용자 알림 시간 조회 쿼리가 JSONB 키 존재 여부와 정수 비교를 함께 수행하도록 개선하여 형식 편차에 안전하게 동작

### 문서화
- README.md - 비동기 요약 생성 흐름과 pending 상태 처리 절차 추가
- `docs/performance_optimization.md` - 성능 계측, 캐싱, 비동기 처리 전략 정리
- README.md - Vercel 배포 체크리스트 및 임포트 검증 절차 추가
- `docs/workflow.md` - 워크플로우 다이어그램 및 설명 추가
- `docs/fetch_feedback_logic.md` - 수집 및 피드백 로직 상세 문서 추가
- `README.md` - 새 기능 및 API 사용법 추가
- `README.md` - 설정 화면 저장 절차 안내 업데이트
- `docs/settings_persistence.md` - 설정 저장 및 동기화 흐름 정리
- `docs/cse_query_limit.md` - Google CSE 쿼리 분배 및 모니터링 정책 문서화
- README.md - 일일 리포트 스케줄이 한국시간 기준으로 동작하는 방식을 명시

## [1.0.0] - 초기 릴리스

### 추가됨
- 사용자 인증 및 관리
- 키워드 관리 (최대 3개)
- RSS 기반 뉴스 수집
- 감성 분석
- 피드 조회 및 필터링
- 기사 상세 조회
- 통계 API

