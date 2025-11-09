# 수집 및 피드백 로직 상세 문서

## 1. 기간 계산 알고리즘

### 1.1 목적
중복된 기간을 조회하지 않도록 하여 불필요한 API 호출과 데이터 처리를 방지합니다.

### 1.2 알고리즘 상세

#### 입력
- `keyword_id`: 키워드 ID
- `user_id`: 사용자 ID
- `request_context`: 요청 컨텍스트
  - `trigger`: 'manual' | 'scheduled'
  - `range`: 선택적 날짜 범위 `{start: datetime, end: datetime}`

#### 처리 과정

**1단계: 수집 이력 조회**
```python
history_list = FetchHistoryRepository.list_by_keyword(keyword_id, order_by="actual_start")
```

**2단계: 대상 날짜 범위 계산**

케이스 1: 첫 조회 (history_list가 비어있음)
```python
yesterday_start = NOW() - 1 day (00:00:00)
yesterday_end = NOW() (00:00:00)
target_ranges = [DateRange(yesterday_start, yesterday_end)]
```

케이스 2: 명시적 범위 요청
```python
candidate_range = DateRange(request_context.range.start, request_context.range.end)
covered_ranges = [h.actual_range for h in history_list]
target_ranges = subtract_ranges(candidate_range, covered_ranges)
```

케이스 3: 기본 수집 (마지막 수집 이후)
```python
last_history = history_list[-1]
next_start = last_history.actual_end + 1 day (00:00:00)
now_end = NOW() (23:59:59)
target_ranges = [DateRange(next_start, now_end)]
```

**3단계: 빈 범위 확인**
```python
if not target_ranges or all(r.is_empty() for r in target_ranges):
    return cached_result
```

### 1.3 subtract_ranges 알고리즘

#### 목적
요청 범위에서 이미 수집된 범위를 제외하여 중복을 방지합니다.

#### 알고리즘

```python
def subtract_ranges(candidate_range, covered_ranges):
    remaining = [candidate_range]
    
    for covered in covered_ranges:
        new_remaining = []
        for block in remaining:
            if not block.overlaps(covered):
                # 겹치지 않으면 그대로 유지
                new_remaining.append(block)
            else:
                # 겹치는 부분 제외
                excluded = block.exclude(covered)
                new_remaining.extend(excluded)
        remaining = new_remaining
    
    # 인접한 범위 병합
    return merge_adjacent(remaining)
```

#### DateRange.exclude() 메서드

```python
def exclude(self, other: DateRange) -> List[DateRange]:
    if not self.overlaps(other):
        return [self]
    
    result = []
    
    # 시작 부분이 남는 경우
    if self.start < other.start:
        result.append(DateRange(self.start, other.start))
    
    # 종료 부분이 남는 경우
    if self.end > other.end:
        result.append(DateRange(other.end, self.end))
    
    return result
```

#### 예시

**예시 1: 단순 겹침**
```
candidate: [2024-01-01, 2024-01-10]
covered:   [2024-01-05, 2024-01-07]
결과:      [2024-01-01, 2024-01-05], [2024-01-07, 2024-01-10]
```

**예시 2: 완전 포함**
```
candidate: [2024-01-01, 2024-01-10]
covered:   [2024-01-03, 2024-01-08]
결과:      [2024-01-01, 2024-01-03], [2024-01-08, 2024-01-10]
```

**예시 3: 여러 범위 제외**
```
candidate: [2024-01-01, 2024-01-10]
covered:   [2024-01-02, 2024-01-03], [2024-01-05, 2024-01-07]
결과:      [2024-01-01, 2024-01-02], [2024-01-03, 2024-01-05], [2024-01-07, 2024-01-10]
```

## 2. 피드백 기반 개선 메커니즘

### 2.1 피드백 수집

사용자는 요약에 대해 1-5점 척도로 평가할 수 있습니다:
- 5점: 매우 만족
- 4점: 만족
- 3점: 보통
- 2점: 불만족
- 1점: 매우 불만족

### 2.2 피드백 통계 집계

```python
stats = {
    'total_count': 총 피드백 개수,
    'avg_rating': 평균 평점,
    'positive_count': 평점 >= 4인 개수,
    'neutral_count': 평점 == 3인 개수,
    'negative_count': 평점 <= 2인 개수
}
```

### 2.3 요약 정책 조정

#### 정책 결정 로직

```python
if avg_rating >= 4.0:
    # 높은 만족도: 현재 수준 유지
    config = {
        'detail_level': 'maintain_current',
        'max_length': 500,
        'include_sentiment': True,
        'include_keywords': False,
        'include_sources': False,
        'top_articles_count': 5
    }
elif avg_rating >= 3.0:
    # 중간 만족도: 더 많은 맥락 제공
    config = {
        'detail_level': 'tweak_for_more_context',
        'max_length': 600,
        'include_sentiment': True,
        'include_keywords': True,
        'include_sources': False,
        'top_articles_count': 7
    }
else:
    # 낮은 만족도: 상세 정보 증가
    config = {
        'detail_level': 'increase_detail',
        'max_length': 800,
        'include_sentiment': True,
        'include_keywords': True,
        'include_sources': True,
        'top_articles_count': 10
    }
```

### 2.4 선호도 업데이트

개별 피드백에 따라 사용자 선호도가 업데이트됩니다:

```python
def derive_detail_level(rating: int) -> str:
    if rating >= 4:
        return 'maintain_current_detail'
    elif rating == 3:
        return 'tweak_for_more_context'
    else:
        return 'increase_detail'
```

## 3. 요약 생성 로직

### 3.1 요약 생성 과정

**1단계: 기사 조회**
- 일일 요약: 사용자의 모든 키워드에 대한 최근 100개 기사
- 키워드별 요약: 해당 키워드의 최근 50개 기사

**2단계: 감성 분석 결과 집계**
```python
positive_count = sum(1 for a in articles if sentiment_label == 'positive')
negative_count = sum(1 for a in articles if sentiment_label == 'negative')
neutral_count = len(articles) - positive_count - negative_count
```

**3단계: 요약 텍스트 생성**
```python
summary_parts = [
    f"총 {len(articles)}개의 기사가 수집되었습니다.",
    f"긍정: {positive_count}개, 부정: {negative_count}개, 중립: {neutral_count}개",
    "\n주요 기사:",
    ... (상위 N개 기사 제목)
]
summary_text = "\n".join(summary_parts)
```

**4단계: 길이 제한 적용**
```python
if len(summary_text) > config['max_length']:
    summary_text = summary_text[:config['max_length']] + "..."
```

### 3.2 요약 품질 개선

피드백이 누적되면 다음 요약 생성 시 더 나은 품질의 요약을 제공합니다:

1. **더 많은 맥락 제공**: 평점이 중간인 경우 키워드 정보 추가
2. **상세 정보 증가**: 평점이 낮은 경우 출처 정보 포함, 더 많은 기사 제목 표시
3. **현재 수준 유지**: 평점이 높은 경우 사용자가 만족하는 형식 유지

## 4. 성능 최적화

### 4.1 캐싱 전략

- 빈 범위인 경우 캐시된 결과 반환
- 최신 요약이 있으면 재생성하지 않고 반환

### 4.2 데이터베이스 최적화

- 인덱스 활용:
  - `fetch_history`: keyword_id, actual_start, actual_end
  - `summary_sessions`: user_id, keyword_id, created_at
  - `summary_feedback`: summary_session_id, user_id

### 4.3 배치 처리

- 기사 저장 시 `upsert_batch` 사용
- 여러 범위 수집 시 순차 처리 (병렬 처리 가능하나 구현 단순화를 위해 순차 처리)

## 5. 에러 처리

### 5.1 수집 실패

- 개별 기사 저장 실패 시 로그 기록 후 계속 진행
- 전체 수집 실패 시 부분 결과 반환

### 5.2 요약 생성 실패

- 기사가 없는 경우 기본 메시지 반환
- 피드백 통계가 없는 경우 기본 정책 사용

### 5.3 피드백 제출 실패

- 세션 확인 실패 시 404 에러
- 평점 범위 오류 시 400 에러

