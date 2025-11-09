"""토큰 제한 확인 미들웨어"""
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))
from src.services.token_tracker import TokenTracker


class TokenLimitMiddleware(BaseHTTPMiddleware):
    """AI API 요청 전 토큰 제한 확인 미들웨어"""
    
    # 토큰 사용량을 확인해야 하는 경로 목록 (AI API 사용)
    PROTECTED_PATHS = [
        "/summaries/daily",
        "/summaries/keywords/",
    ]
    
    def __init__(self, app):
        super().__init__(app)
        self.token_tracker = TokenTracker()
    
    def _is_protected_path(self, path: str) -> bool:
        """보호된 경로인지 확인"""
        # 정확히 일치하거나 경로가 시작하는지 확인
        for protected in self.PROTECTED_PATHS:
            if path == protected or path.startswith(protected):
                return True
        return False
    
    async def dispatch(self, request: Request, call_next):
        """요청 처리 전 토큰 제한 확인"""
        # GET 요청 중 토큰 사용량 조회 API는 제외
        if request.url.path == "/stats/token-usage" and request.method == "GET":
            return await call_next(request)
        
        # 보호된 경로인 경우 토큰 제한 확인
        if self._is_protected_path(request.url.path):
            try:
                is_exceeded = await self.token_tracker.is_token_limit_exceeded()
                
                if is_exceeded:
                    # 토큰 제한 초과 시 상태 정보 조회
                    status_info = await self.token_tracker.get_usage_status()
                    
                    return JSONResponse(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        content={
                            "error": "시스템 일일 토큰 제한을 초과했습니다",
                            "today_usage": status_info['today_usage'],
                            "daily_limit": status_info['daily_limit'],
                            "predicted_daily_usage": status_info['predicted_daily_usage'],
                            "reset_at": status_info['reset_at'],
                            "message": "일일 토큰 제한이 초과되어 서비스를 일시 중단합니다. 자정에 자동으로 복구됩니다."
                        }
                    )
            except Exception as e:
                # 토큰 확인 중 오류 발생 시 로깅만 하고 요청 진행
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"토큰 제한 확인 중 오류 발생: {e}", exc_info=True)
                # 오류 발생 시 요청은 진행 (안전한 실패)
        
        return await call_next(request)

