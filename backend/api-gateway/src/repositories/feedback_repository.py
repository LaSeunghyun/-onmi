"""피드백 리포지토리"""
from typing import Dict, List, Optional
from uuid import UUID
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../shared'))
from database.connection import get_db_connection
from ..models.feedback import Feedback


class FeedbackRepository:
    """피드백 데이터 접근 리포지토리"""
    
    @staticmethod
    async def insert(
        summary_session_id: UUID,
        user_id: UUID,
        rating: int,
        comment: Optional[str] = None
    ) -> UUID:
        """피드백 저장"""
        async with get_db_connection() as conn:
            feedback_id = await conn.fetchval(
                """
                INSERT INTO summary_feedback (summary_session_id, user_id, rating, comment)
                VALUES ($1, $2, $3, $4)
                RETURNING id
                """,
                summary_session_id, user_id, rating, comment
            )
            return feedback_id
    
    @staticmethod
    async def get_by_session(session_id: UUID) -> List[Feedback]:
        """세션별 피드백 조회"""
        async with get_db_connection() as conn:
            rows = await conn.fetch(
                """
                SELECT id, summary_session_id, user_id, rating, comment, created_at
                FROM summary_feedback
                WHERE summary_session_id = $1
                ORDER BY created_at DESC
                """,
                session_id
            )
            return [Feedback.from_db_row(row) for row in rows]
    
    @staticmethod
    async def aggregate_by_keyword(keyword_id: UUID, user_id: UUID) -> Dict:
        """키워드별 피드백 통계 집계"""
        async with get_db_connection() as conn:
            stats = await conn.fetchrow(
                """
                SELECT 
                    COUNT(*) as total_count,
                    AVG(rating) as avg_rating,
                    COUNT(CASE WHEN rating >= 4 THEN 1 END) as positive_count,
                    COUNT(CASE WHEN rating = 3 THEN 1 END) as neutral_count,
                    COUNT(CASE WHEN rating <= 2 THEN 1 END) as negative_count
                FROM summary_feedback sf
                INNER JOIN summary_sessions ss ON sf.summary_session_id = ss.id
                WHERE ss.keyword_id = $1 AND sf.user_id = $2
                """,
                keyword_id, user_id
            )
            return {
                'total_count': stats['total_count'] or 0,
                'avg_rating': float(stats['avg_rating']) if stats['avg_rating'] else 0.0,
                'positive_count': stats['positive_count'] or 0,
                'neutral_count': stats['neutral_count'] or 0,
                'negative_count': stats['negative_count'] or 0
            }
    
    @staticmethod
    async def aggregate_by_user(user_id: UUID) -> Dict:
        """사용자별 피드백 통계 집계"""
        async with get_db_connection() as conn:
            stats = await conn.fetchrow(
                """
                SELECT 
                    COUNT(*) as total_count,
                    AVG(rating) as avg_rating,
                    COUNT(CASE WHEN rating >= 4 THEN 1 END) as positive_count,
                    COUNT(CASE WHEN rating = 3 THEN 1 END) as neutral_count,
                    COUNT(CASE WHEN rating <= 2 THEN 1 END) as negative_count
                FROM summary_feedback
                WHERE user_id = $1
                """,
                user_id
            )
            return {
                'total_count': stats['total_count'] or 0,
                'avg_rating': float(stats['avg_rating']) if stats['avg_rating'] else 0.0,
                'positive_count': stats['positive_count'] or 0,
                'neutral_count': stats['neutral_count'] or 0,
                'negative_count': stats['negative_count'] or 0
            }

