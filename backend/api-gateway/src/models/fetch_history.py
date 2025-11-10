"""수집 이력 모델"""
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta


class DateRange:
    """날짜 범위 클래스"""
    
    def __init__(self, start: datetime, end: datetime):
        self.start = start
        self.end = end
    
    def overlaps(self, other: 'DateRange') -> bool:
        """다른 범위와 겹치는지 확인"""
        return self.start <= other.end and self.end >= other.start
    
    def exclude(self, other: 'DateRange') -> list:
        """다른 범위를 제외한 범위 리스트 반환"""
        if not self.overlaps(other):
            return [self]
        
        result = []
        if self.start < other.start:
            result.append(DateRange(self.start, other.start))
        if self.end > other.end:
            result.append(DateRange(other.end, self.end))
        
        return result
    
    def is_empty(self) -> bool:
        """빈 범위인지 확인"""
        return self.start >= self.end


class FetchHistory:
    """수집 이력 모델"""
    
    def __init__(
        self,
        id: UUID,
        keyword_id: UUID,
        requested_start: datetime,
        requested_end: datetime,
        actual_start: datetime,
        actual_end: datetime,
        articles_count: int,
        created_at: Optional[datetime] = None
    ):
        self.id = id
        self.keyword_id = keyword_id
        self.requested_start = requested_start
        self.requested_end = requested_end
        self.actual_start = actual_start
        self.actual_end = actual_end
        self.articles_count = articles_count
        self.created_at = created_at
    
    @property
    def actual_range(self) -> DateRange:
        """실제 수집 범위"""
        return DateRange(self.actual_start, self.actual_end)
    
    @classmethod
    def from_db_row(cls, row) -> 'FetchHistory':
        """데이터베이스 행으로부터 FetchHistory 객체 생성"""
        return cls(
            id=row['id'],
            keyword_id=row['keyword_id'],
            requested_start=row['requested_start'],
            requested_end=row['requested_end'],
            actual_start=row['actual_start'],
            actual_end=row['actual_end'],
            articles_count=row['articles_count'],
            created_at=row.get('created_at')
        )

