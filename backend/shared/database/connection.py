"""데이터베이스 연결 관리 모듈 - Supabase PostgreSQL"""
from typing import Optional
from contextlib import asynccontextmanager
import logging

# Windows 콘솔 인코딩 설정
import sys
if sys.platform == 'win32':
    import codecs
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    if hasattr(sys.stderr, 'buffer'):
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False
    asyncpg = None

# 설정 모듈 import
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))
from config.settings import settings

# 로거 설정
logger = logging.getLogger(__name__)

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
        # settings에서 데이터베이스 URL 가져오기
        try:
            database_url = settings.database_url
        except ValueError as e:
            # settings에서 환경변수 검증 실패
            logger.error("=" * 80)
            logger.error("❌ 데이터베이스 연결 URL 검증 실패")
            logger.error(f"오류 메시지: {str(e)}")
            logger.error("=" * 80)
            raise RuntimeError(
                f"데이터베이스 연결 URL 검증 실패: {str(e)}"
            ) from e
        
        # 연결 정보 추출 및 로깅
        if database_url:
            try:
                # URL에서 호스트 정보 추출
                if '@' in database_url:
                    host_part = database_url.split('@')[1].split('/')[0]
                    host = host_part.split(':')[0] if ':' in host_part else host_part
                    logger.info(f"데이터베이스 연결 시도: {host}")
                else:
                    logger.warning(f"데이터베이스 URL 형식이 올바르지 않습니다: {database_url[:50]}...")
            except Exception:
                pass
        
        if not database_url or 'localhost' in database_url or '127.0.0.1' in database_url:
            logger.error("⚠️ 경고: 로컬 데이터베이스에 연결하려고 시도하고 있습니다!")
            logger.error("Supabase를 사용하려면 DATABASE_URL 또는 SUPABASE_DB_URL 환경변수를 설정하세요.")
        
        try:
            # 연결 문자열 파싱
            import urllib.parse
            parsed = urllib.parse.urlparse(database_url)
            
            # 사용자 이름 처리
            # Supabase pooler 호스트를 사용할 때는 원래 사용자명 유지
            # 직접 연결(db.giqqhzonfruynokwbguv.supabase.co)일 때만 사용자명 변경 시도
            username = parsed.username
            hostname = parsed.hostname or ""
            
            # Supabase 연결 문자열 처리
            # Pooler: postgres.[project-ref]@pooler.supabase.com:6543
            # Direct: postgres@db.[project-ref].supabase.co:5432
            
            if 'pooler.supabase.com' in hostname:
                # Pooler 연결: 사용자명에 프로젝트 ref가 포함되어야 함
                # 형식: postgres.[project-ref] 또는 postgres
                if username and '.' not in username:
                    # 사용자명에 프로젝트 ref가 없으면 경고
                    logger.warning(f"Pooler 연결에서 사용자명에 프로젝트 ref가 없습니다: {username}")
                else:
                    logger.info(f"Pooler 호스트 사용: 사용자명 {username}")
                
                # Pooler는 포트 6543을 사용해야 함 (포트가 5432인 경우 경고)
                if parsed.port == 5432:
                    logger.warning(f"Pooler 연결에서 포트 5432 사용 중. 포트 6543 사용을 권장합니다.")
                
                database_url_to_use = database_url
            elif 'supabase.co' in hostname and 'pooler' not in hostname:
                # 직접 연결: 사용자명은 postgres (프로젝트 ref 없음)
                if username and '.' in username:
                    # 사용자명에서 프로젝트 ref 제거
                    base_username = username.split('.')[0]
                    logger.info(f"직접 연결: 사용자명 형식 변경 {username} -> {base_username}")
                    # URL 재구성
                    netloc = f"{base_username}:{parsed.password}@{hostname}"
                    if parsed.port:
                        netloc += f":{parsed.port}"
                    database_url_modified = urllib.parse.urlunparse((
                        parsed.scheme,
                        netloc,
                        parsed.path,
                        parsed.params,
                        parsed.query,
                        parsed.fragment
                    ))
                    database_url_to_use = database_url_modified
                else:
                    database_url_to_use = database_url
            else:
                # 기타 연결 (로컬 등)
                database_url_to_use = database_url
            
            # 서버리스 환경에 맞게 연결 풀 최적화
            # - min_size: 1 (최소 연결 유지로 빠른 응답)
            # - max_size: 5 (서버리스 환경에서는 작은 풀 사용)
            # - command_timeout: 30초 (Vercel 타임아웃 고려)
            # - statement_cache_size: 0 (pgbouncer와 호환성을 위해 필요)
            _pool = await asyncpg.create_pool(
                database_url_to_use,
                min_size=1,  # 최소 연결 유지
                max_size=5,  # 서버리스 환경: 작은 풀 크기
                command_timeout=30,  # Vercel 타임아웃 고려
                statement_cache_size=0,  # pgbouncer와 호환성을 위해 필요
                server_settings={
                    "application_name": "onmi-api"
                }
            )
            # 연결 테스트
            async with _pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            
            # 연결 성공 시 호스트 정보 로깅
            if '@' in database_url:
                host_part = database_url.split('@')[1].split('/')[0]
                host = host_part.split(':')[0] if ':' in host_part else host_part
                logger.info(f"✅ 데이터베이스 연결 성공: {host}")
        except asyncpg.InvalidPasswordError as e:
            # 비밀번호 오류
            _pool = None
            logger.error("=" * 80)
            logger.error("❌ 데이터베이스 인증 실패: 비밀번호가 잘못되었습니다")
            logger.error(f"오류 메시지: {str(e)}")
            logger.error("")
            logger.error("해결 방법:")
            logger.error("  1. .env 파일의 DATABASE_URL에서 비밀번호를 확인하세요")
            logger.error("  2. Supabase 대시보드에서 데이터베이스 비밀번호를 확인하세요")
            logger.error("=" * 80)
            raise RuntimeError(
                "데이터베이스 인증 실패: 비밀번호가 잘못되었습니다.\n"
                f"상세 오류: {str(e)}\n"
                ".env 파일의 DATABASE_URL에서 비밀번호를 확인하세요."
            ) from e
        except asyncpg.InvalidCatalogNameError as e:
            # 데이터베이스 이름 오류
            _pool = None
            logger.error("=" * 80)
            logger.error("❌ 데이터베이스 연결 실패: 데이터베이스 이름이 잘못되었습니다")
            logger.error(f"오류 메시지: {str(e)}")
            logger.error("")
            logger.error("해결 방법:")
            logger.error("  1. .env 파일의 DATABASE_URL에서 데이터베이스 이름을 확인하세요")
            logger.error("  2. 일반적으로 'postgres'를 사용합니다")
            logger.error("=" * 80)
            raise RuntimeError(
                "데이터베이스 연결 실패: 데이터베이스 이름이 잘못되었습니다.\n"
                f"상세 오류: {str(e)}\n"
                ".env 파일의 DATABASE_URL에서 데이터베이스 이름을 확인하세요."
            ) from e
        except (asyncpg.PostgresConnectionError, asyncpg.PostgresError, OSError) as e:
            # 네트워크 연결 오류 또는 PostgreSQL 오류
            _pool = None
            error_type = type(e).__name__
            logger.error("=" * 80)
            logger.error(f"❌ 데이터베이스 연결 실패: {error_type}")
            logger.error(f"오류 메시지: {str(e)}")
            logger.error("")
            
            # 연결 정보 추출 (민감한 정보 제외)
            try:
                import urllib.parse
                parsed = urllib.parse.urlparse(database_url)
                host = parsed.hostname or "N/A"
                port = parsed.port or "N/A"
                database = parsed.path.lstrip('/') or "N/A"
                logger.error(f"연결 정보:")
                logger.error(f"  호스트: {host}")
                logger.error(f"  포트: {port}")
                logger.error(f"  데이터베이스: {database}")
            except Exception:
                pass
            
            logger.error("")
            logger.error("가능한 원인:")
            logger.error("  1. 네트워크 연결 문제 (인터넷 연결 확인)")
            logger.error("  2. 데이터베이스 서버가 다운되었거나 접근할 수 없음")
            logger.error("  3. 방화벽 또는 보안 그룹 설정 문제")
            logger.error("  4. 호스트 주소 또는 포트가 잘못됨")
            logger.error("")
            logger.error("해결 방법:")
            logger.error("  1. 인터넷 연결을 확인하세요")
            logger.error("  2. Supabase 대시보드에서 데이터베이스 상태를 확인하세요")
            logger.error("  3. .env 파일의 DATABASE_URL 형식을 확인하세요")
            logger.error("=" * 80)
            raise RuntimeError(
                f"데이터베이스 연결 실패 ({error_type}): {str(e)}\n"
                f"호스트: {host if 'host' in locals() else 'N/A'}, "
                f"포트: {port if 'port' in locals() else 'N/A'}\n"
                "네트워크 연결 및 데이터베이스 서버 상태를 확인하세요."
            ) from e
        except Exception as e:
            # 기타 예상치 못한 오류
            _pool = None
            import traceback
            error_type = type(e).__name__
            logger.error("=" * 80)
            logger.error(f"❌ 데이터베이스 연결 실패: 예상치 못한 오류 ({error_type})")
            logger.error(f"오류 메시지: {str(e)}")
            logger.error("")
            logger.error("상세 스택 트레이스:")
            logger.error(traceback.format_exc())
            logger.error("=" * 80)
            raise RuntimeError(
                f"데이터베이스 연결 실패: 예상치 못한 오류가 발생했습니다.\n"
                f"오류 유형: {error_type}\n"
                f"오류 메시지: {str(e)}\n"
                "로그 파일을 확인하거나 check_environment.ps1을 실행하여 환경을 확인하세요."
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

