"""데이터베이스 연결 관리 모듈 - Supabase PostgreSQL"""
import os
from typing import Optional
from contextlib import asynccontextmanager

try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False
    asyncpg = None

# 전역 연결 풀
_pool: Optional[asyncpg.Pool] = None


async def init_db_pool():
    """데이터베이스 연결 풀 초기화 (서버리스 환경 최적화)"""
    global _pool
    if not ASYNCPG_AVAILABLE:
        raise RuntimeError(
            "asyncpg 모듈이 설치되지 않았습니다. "
            "Visual C++ Build Tools를 설치한 후 'pip install asyncpg'를 실행하세요. "
            "또는 https://visualstudio.microsoft.com/visual-cpp-build-tools/ 에서 다운로드하세요."
        )
    if _pool is None:
        # Supabase 연결 문자열 사용
        # 형식: postgresql://postgres:[password]@[host]:5432/postgres
        database_url = os.getenv(
            "DATABASE_URL",
            os.getenv(
                "SUPABASE_DB_URL",
                "postgresql://onmi:onmi_dev_password@localhost:5432/onmi_db"
            )
        )
        
        try:
            # 서버리스 환경에 맞게 연결 풀 최적화
            # - min_size: 1 (최소 연결 유지로 빠른 응답)
            # - max_size: 5 (서버리스 환경에서는 작은 풀 사용)
            # - command_timeout: 30초 (Vercel 타임아웃 고려)
            _pool = await asyncpg.create_pool(
                database_url,
                min_size=1,  # 최소 연결 유지
                max_size=5,  # 서버리스 환경: 작은 풀 크기
                command_timeout=30,  # Vercel 타임아웃 고려
                server_settings={
                    "application_name": "onmi-api"
                }
            )
            # 연결 테스트
            async with _pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
        except Exception as e:
            _pool = None
            raise RuntimeError(
                f"데이터베이스 연결 실패: {str(e)}\n"
                f"연결 문자열: {database_url.split('@')[1] if '@' in database_url else 'N/A'}"
            ) from e
    return _pool


async def close_db_pool():
    """데이터베이스 연결 풀 종료"""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


@asynccontextmanager
async def get_db_connection():
    """데이터베이스 연결 컨텍스트 매니저"""
    if _pool is None:
        await init_db_pool()
    
    if _pool is None:
        raise RuntimeError("데이터베이스 연결 풀이 초기화되지 않았습니다.")
    
    try:
        async with _pool.acquire() as connection:
            yield connection
    except Exception as e:
        raise RuntimeError(f"데이터베이스 연결 획득 실패: {str(e)}") from e

