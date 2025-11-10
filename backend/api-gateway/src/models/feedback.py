"""피드백 모델"""
from typing import Optional
from uuid import UUID
from datetime import datetime


class Feedback:
    """피드백 모델"""
    
    def __init__(
        self,
        id: UUID,
        summary_session_id: UUID,
        user_id: UUID,
        rating: int,
        comment: Optional[str] = None,
        created_at: Optional[datetime] = None
    ):
        self.id = id
        self.summary_session_id = summary_session_id
        self.user_id = user_id
        self.rating = rating
        self.comment = comment
        self.created_at = created_at
    
    @classmethod
    def from_db_row(cls, row) -> 'Feedback':
        """데이터베이스 행으로부터 Feedback 객체 생성"""
        return cls(
            id=row['id'],
            summary_session_id=row['summary_session_id'],
            user_id=row['user_id'],
            rating=row['rating'],
            comment=row.get('comment'),
            created_at=row.get('created_at')
        )

