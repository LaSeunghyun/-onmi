"""토큰 사용량 리포지토리 (시스템 전체 공통)"""
from typing import Optional, Dict
from datetime import date, datetime
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../shared'))
from database.connection import get_db_connection


class TokenUsageRepository:
    """시스템 전체 토큰 사용량 데이터 접근 리포지토리"""
    
    @staticmethod
    async def increment_usage(
        tokens_used: int,
        input_tokens: int = 0,
        output_tokens: int = 0,
        usage_date: Optional[date] = None
    ) -> None:
        """토큰 사용량 증가 (시스템 전체)"""
        if usage_date is None:
            usage_date = date.today()
        
        async with get_db_connection() as conn:
            await conn.execute(
                """
                INSERT INTO token_usage (date, total_tokens_used, input_tokens, output_tokens)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (date) DO UPDATE SET
                    total_tokens_used = token_usage.total_tokens_used + EXCLUDED.total_tokens_used,
                    input_tokens = token_usage.input_tokens + EXCLUDED.input_tokens,
                    output_tokens = token_usage.output_tokens + EXCLUDED.output_tokens,
                    updated_at = NOW()
                """,
                usage_date, tokens_used, input_tokens, output_tokens
            )
    
    @staticmethod
    async def get_today_usage() -> Dict:
        """오늘의 토큰 사용량 조회"""
        today = date.today()
        try:
            async with get_db_connection() as conn:
                # 테이블 존재 여부 확인
                table_exists = await conn.fetchval(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'token_usage'
                    )
                    """
                )
                
                if not table_exists:
                    # 테이블이 없으면 기본값 반환
                    return {
                        'date': today,
                        'total_tokens_used': 0,
                        'input_tokens': 0,
                        'output_tokens': 0,
                        'updated_at': None
                    }
                
                row = await conn.fetchrow(
                    """
                    SELECT date, total_tokens_used, input_tokens, output_tokens, updated_at
                    FROM token_usage
                    WHERE date = $1
                    """,
                    today
                )
                if row:
                    return {
                        'date': row['date'],
                        'total_tokens_used': row['total_tokens_used'] or 0,
                        'input_tokens': row['input_tokens'] or 0,
                        'output_tokens': row['output_tokens'] or 0,
                        'updated_at': row['updated_at']
                    }
                return {
                    'date': today,
                    'total_tokens_used': 0,
                    'input_tokens': 0,
                    'output_tokens': 0,
                    'updated_at': None
                }
        except Exception:
            # 모든 예외를 잡아서 기본값 반환
            return {
                'date': today,
                'total_tokens_used': 0,
                'input_tokens': 0,
                'output_tokens': 0,
                'updated_at': None
            }
    
    @staticmethod
    async def get_hourly_average_for_today() -> float:
        """오늘의 시간당 평균 사용량 계산"""
        today = date.today()
        try:
            async with get_db_connection() as conn:
                # 테이블 존재 여부 확인
                table_exists = await conn.fetchval(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'token_usage'
                    )
                    """
                )
                
                if not table_exists:
                    return 0.0
                
                row = await conn.fetchrow(
                    """
                    SELECT total_tokens_used, updated_at
                    FROM token_usage
                    WHERE date = $1
                    """,
                    today
                )
                
                if not row or not row['total_tokens_used']:
                    return 0.0
                
                # 현재 시간까지의 시간당 평균 계산
                now = datetime.now()
                start_of_day = datetime.combine(today, datetime.min.time())
                hours_elapsed = max(1, (now - start_of_day).total_seconds() / 3600)
                
                return row['total_tokens_used'] / hours_elapsed
        except Exception:
            # 모든 예외를 잡아서 기본값 반환
            return 0.0
    
    @staticmethod
    async def get_recent_usage(days: int = 7) -> list:
        """최근 N일간의 토큰 사용량 조회"""
        async with get_db_connection() as conn:
            rows = await conn.fetch(
                """
                SELECT date, total_tokens_used, input_tokens, output_tokens, updated_at
                FROM token_usage
                WHERE date >= CURRENT_DATE - (CAST($1 AS TEXT) || ' days')::INTERVAL
                ORDER BY date DESC
                """,
                str(days)
            )
            return [dict(row) for row in rows]


