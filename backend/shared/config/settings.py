"""공통 설정 모듈 - Vercel + Supabase 서버리스 환경"""
import os
from typing import List, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # Supabase Database
    # Supabase 연결 문자열 형식: postgresql://postgres:[password]@[host]:5432/postgres
    database_url: str = os.getenv(
        "DATABASE_URL",
        os.getenv(
            "SUPABASE_DB_URL",
            "postgresql://onmi:onmi_dev_password@localhost:5432/onmi_db"
        )
    )
    
    # Supabase 설정 (선택사항)
    supabase_url: Optional[str] = os.getenv("SUPABASE_URL")
    supabase_key: Optional[str] = os.getenv("SUPABASE_ANON_KEY")
    
    # JWT
    jwt_secret: str = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
    jwt_expires_in: str = os.getenv("JWT_EXPIRES_IN", "7d")
    
    # Scheduler (Vercel Cron Jobs)
    scheduler_interval_hours: int = int(os.getenv("SCHEDULER_INTERVAL_HOURS", "2"))
    
    # Rate Limiting (선택사항 - Vercel에서 제공하는 Rate Limiting 사용 가능)
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    rate_limit_per_hour: int = int(os.getenv("RATE_LIMIT_PER_HOUR", "1000"))
    
    # RSS Sources
    rss_sources: List[str] = os.getenv(
        "RSS_SOURCES",
        "https://rss.cnn.com/rss/edition.rss,https://feeds.bbci.co.uk/news/rss.xml"
    ).split(",")
    
    # Redis (선택사항 - 필요시 Upstash 사용)
    redis_url: Optional[str] = os.getenv("REDIS_URL")
    
    # MinIO/Storage (선택사항 - 필요시 Supabase Storage 또는 Cloudflare R2 사용)
    storage_type: str = os.getenv("STORAGE_TYPE", "none")  # 'supabase', 'r2', 'none'
    storage_bucket: Optional[str] = os.getenv("STORAGE_BUCKET")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

