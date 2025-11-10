## Google CSE 쿼리 제한 정책

일일 100건 무료 쿼리를 여러 사용자가 공유하는 환경에서 공정한 분배와 모니터링을 위해 다음 전략을 적용합니다.

### 1. 기본 용어
- **일일 전체 한도**: `settings.daily_cse_query_limit` (기본 100건)
- **리셋 시각**: `settings.cse_query_reset_hour_utc` (기본 UTC 16시 = PST 자정)
- **활성 사용자**: `keywords` 테이블에서 `status = 'active'`인 키워드를 보유한 사용자
- **활성 키워드**: 특정 사용자가 활성 상태로 등록한 키워드 수

### 2. 할당 공식
1. **사용자별 할당량**
   ```
   user_quota = max(1, floor(daily_limit / max(1, active_user_count)))
   ```
2. **키워드별 할당량**
   ```
   keyword_quota = 
     user_quota               (활성 키워드가 0개인 경우)
     max(1, floor(user_quota / active_keyword_count))  (그 외)
   ```

### 3. 사용량 기록
- `cse_query_usage` 테이블에 일자(`date`), 사용자 ID, 키워드 ID 단위로 누적
- Google CSE API 호출 시, 실제 요청이 전송되면 `queries_used`를 +1
- 날짜 키는 UTC 리셋 시각을 고려해 `CSEQueryUsageRepository.get_effective_date()`로 계산

### 4. 제한 체크 흐름
1. API 호출 전 `CSEQueryLimitService.can_make_query()`로 사용자/키워드 잔여량 확인
2. 잔여량이 없으면 `CSEQueryLimitExceededError`를 발생시켜 429 에러를 반환
3. 정상 호출 후 `record_usage()`로 사용량을 증가시킴

### 5. 프론트엔드 표시
- `/stats/cse-query-usage` 엔드포인트로 사용자/키워드별 잔여 쿼리 수 조회
- 홈 화면 "오늘의 요약" 영역에 `조회 가능 쿼리수 : n` 형식으로 표시
- 요약이 갱신되면 쿼리 사용량도 자동으로 새로고침

### 6. 운영 팁
- 유료 플랜으로 업그레이드하면 `daily_cse_query_limit` 값을 환경 변수를 통해 조정
- 리셋 시각 변경은 `cse_query_reset_hour_utc`로 관리 (PDT 전환 시 17로 설정)
- 비정상 호출이나 오류가 발생하면 `cse_query_usage` 테이블을 참고하여 추적


