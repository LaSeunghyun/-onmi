"""토큰 사용량 추적 및 예측 서비스 (시스템 전체 공통)"""
from typing import Dict, Optional
from datetime import datetime, date, timedelta
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../shared'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.settings import settings
from repositories.token_usage_repository import TokenUsageRepository


class TokenTracker:
    """시스템 전체 토큰 사용량 추적 및 예측"""
    
    async def record_usage(
        self,
        tokens_used: int,
        input_tokens: int = 0,
        output_tokens: int = 0
    ) -> None:
        """토큰 사용량 기록 (시스템 전체)"""
        await TokenUsageRepository.increment_usage(
            tokens_used=tokens_used,
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )
    
    async def get_daily_usage(self) -> int:
        """오늘의 시스템 전체 토큰 사용량 조회"""
        usage = await TokenUsageRepository.get_today_usage()
        return usage['total_tokens_used']
    
    async def predict_daily_usage(self) -> int:
        """일일 사용량 예측"""
        current_usage = await self.get_daily_usage()
        current_hour = datetime.now().hour
        
        # 오늘의 시간당 평균 사용량 조회
        hourly_avg = await TokenUsageRepository.get_hourly_average_for_today()
        
        # 현재 시간부터 자정까지 남은 시간 계산
        now = datetime.now()
        end_of_day = datetime.combine(date.today(), datetime.max.time())
        hours_remaining = max(0, (end_of_day - now).total_seconds() / 3600)
        
        # 예측: 현재 사용량 + (평균 시간당 사용량 × 남은 시간)
        predicted = int(current_usage + (hourly_avg * hours_remaining))
        
        return predicted
    
    async def is_token_limit_exceeded(self) -> bool:
        """토큰 제한 초과 여부 확인"""
        predicted = await self.predict_daily_usage()
        return predicted >= settings.daily_token_limit
    
    async def can_make_request(self) -> bool:
        """요청 가능 여부 확인"""
        return not await self.is_token_limit_exceeded()
    
    async def get_usage_status(self) -> Dict:
        """토큰 사용량 상태 조회 (API용)"""
        try:
            today_usage = await self.get_daily_usage()
            predicted = await self.predict_daily_usage()
            is_exceeded = await self.is_token_limit_exceeded()
            
            # 다음 일일 리셋 시간 계산 (자정)
            now = datetime.now()
            tomorrow = now + timedelta(days=1)
            reset_at = datetime.combine(tomorrow.date(), datetime.min.time())
            
            usage_percentage = today_usage / settings.daily_token_limit if settings.daily_token_limit > 0 else 0.0
            
            return {
                'today_usage': today_usage,
                'daily_limit': settings.daily_token_limit,
                'usage_percentage': min(1.0, usage_percentage),
                'predicted_daily_usage': predicted,
                'is_limit_exceeded': is_exceeded,
                'can_make_request': not is_exceeded,
                'reset_at': reset_at.isoformat(),
                'message': '시스템 일일 토큰 제한을 초과했습니다' if is_exceeded else '정상'
            }
        except Exception as e:
            # 예외 발생 시 기본값 반환
            now = datetime.now()
            tomorrow = now + timedelta(days=1)
            reset_at = datetime.combine(tomorrow.date(), datetime.min.time())
            
            return {
                'today_usage': 0,
                'daily_limit': settings.daily_token_limit,
                'usage_percentage': 0.0,
                'predicted_daily_usage': 0,
                'is_limit_exceeded': False,
                'can_make_request': True,
                'reset_at': reset_at.isoformat(),
                'message': '정상'
            }


