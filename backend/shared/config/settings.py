"""공통 설정 모듈 - Vercel + Supabase 서버리스 환경"""
from typing import List, Optional
from pydantic import Field, FieldValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from pathlib import Path


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    model_config = SettingsConfigDict(
        # 프로젝트 루트의 .env 파일 찾기 (현재 파일 기준으로 상위 디렉토리 탐색)
        env_file=os.path.join(
            Path(__file__).parent.parent.parent.parent,  # backend/shared/config -> backend/shared -> backend -> 루트
            ".env"
        ),
        case_sensitive=False,
        env_file_encoding="utf-8"
    )
    
    # Supabase Database
    # Supabase 연결 문자열 형식: postgresql://postgres:[password]@[host]:5432/postgres
    # 우선순위: DATABASE_URL → SUPABASE_DB_URL → 기본값
    database_url: Optional[str] = Field(
        default=None,
        description="데이터베이스 연결 URL (DATABASE_URL 또는 SUPABASE_DB_URL 환경 변수 사용)"
    )
    supabase_db_url: Optional[str] = Field(
        default=None,
        alias="SUPABASE_DB_URL",
        description="Supabase 데이터베이스 연결 URL (DATABASE_URL이 없을 때 사용)"
    )
    # Supabase 설정 (선택사항)
    supabase_url: Optional[str] = Field(
        default=None,
        description="Supabase 프로젝트 URL"
    )
    supabase_key: Optional[str] = Field(
        default=None,
        alias="SUPABASE_ANON_KEY",
        description="Supabase Anon Key"
    )
    
    # JWT
    jwt_secret: str = Field(
        default="your-secret-key-change-in-production",
        description="JWT 서명에 사용할 비밀 키"
    )
    jwt_expires_in: str = Field(
        default="7d",
        description="JWT 토큰 만료 시간"
    )
    
    # Scheduler (Vercel Cron Jobs)
    scheduler_interval_hours: int = Field(
        default=2,
        description="스케줄러 실행 간격 (시간)"
    )
    
    # Rate Limiting (선택사항 - Vercel에서 제공하는 Rate Limiting 사용 가능)
    rate_limit_per_minute: int = Field(
        default=60,
        description="분당 요청 제한"
    )
    rate_limit_per_hour: int = Field(
        default=1000,
        description="시간당 요청 제한"
    )
    
    # Redis (선택사항 - 필요시 Upstash 사용)
    redis_url: Optional[str] = Field(
        default=None,
        description="Redis 연결 URL"
    )
    
    # Token Usage (시스템 전체 공통)
    daily_token_limit: int = Field(
        default=1000000,
        description="일일 토큰 제한"
    )
    token_warning_threshold: float = Field(
        default=0.9,
        description="토큰 사용량 경고 임계값 (0.0 ~ 1.0)"
    )
    daily_cse_query_limit: int = Field(
        default=100,
        description="Google CSE 일일 총 쿼리 제한 (무료 플랜 기준 100)"
    )
    cse_query_reset_hour_utc: int = Field(
        default=16,
        description="Google CSE 쿼리 사용량 리셋 시간 (UTC 기준, PST 자정=16, PDT 자정=17)"
    )
    
    # External APIs
    google_cse_api_key: Optional[str] = Field(
        default=None,
        alias="GOOGLE_CSE_API_KEY",
        description="Google Custom Search API 키"
    )
    google_cse_cx: Optional[str] = Field(
        default=None,
        alias="GOOGLE_CSE_CX",
        description="Google Custom Search 엔진 ID"
    )
    gemini_api_key: Optional[str] = Field(
        default=None,
        alias="GEMINI_API_KEY",
        description="Google Gemini API 키"
    )
    gemini_model: str = Field(
        default="models/gemini-1.5-flash-latest",
        alias="GEMINI_MODEL",
        description="사용할 Gemini 모델"
    )
    
    # Google OAuth 2.0
    google_oauth_client_id: Optional[str] = Field(
        default=None,
        alias="GOOGLE_OAUTH_CLIENT_ID",
        description="Google OAuth 클라이언트 ID (웹용, 선택사항)"
    )
    google_oauth_client_secret: Optional[str] = Field(
        default=None,
        alias="GOOGLE_OAUTH_CLIENT_SECRET",
        description="Google OAuth 클라이언트 시크릿 (웹용, 선택사항)"
    )
    google_oauth_client_id_android: Optional[str] = Field(
        default=None,
        alias="GOOGLE_OAUTH_CLIENT_ID_ANDROID",
        description="Google OAuth 클라이언트 ID (Android용)"
    )
    google_oauth_client_id_ios: Optional[str] = Field(
        default=None,
        alias="GOOGLE_OAUTH_CLIENT_ID_IOS",
        description="Google OAuth 클라이언트 ID (iOS용)"
    )
    
    # Vercel Cron Job 보안
    cron_secret: Optional[str] = Field(
        default=None,
        description="Vercel Cron Job 인증을 위한 시크릿 키"
    )
    
    @field_validator("database_url", mode="after")
    @classmethod
    def resolve_database_url(cls, v: Optional[str], info: FieldValidationInfo) -> str:
        """DATABASE_URL 우선순위 처리: DATABASE_URL → SUPABASE_DB_URL (환경변수 필수)"""
        # pydantic-settings가 이미 .env 파일을 로드했으므로 v에 값이 있을 수 있음
        # 1) DATABASE_URL 확인 (이미 v에 설정되어 있을 수 있음)
        if v:
            return v

        # 2) SUPABASE_DB_URL 확인 (info.data에서 확인)
        supabase_db_url = info.data.get("supabase_db_url")
        if supabase_db_url:
            return supabase_db_url

        # 3) 환경변수가 없으면 에러 발생
        env_file_path = cls.model_config.get("env_file", "N/A")
        raise ValueError(
            "DATABASE_URL 또는 SUPABASE_DB_URL 환경변수가 설정되지 않았습니다.\n"
            f"프로젝트 루트의 .env 파일 ({env_file_path})에 다음 중 하나를 설정하세요:\n"
            "  DATABASE_URL=postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres\n"
            "또는\n"
            "  SUPABASE_DB_URL=postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres"
        )


settings = Settings()

