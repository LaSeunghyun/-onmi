"""Vercel 서버리스 함수 진입점 - FastAPI 앱"""
import sys
import os
import traceback
from pathlib import Path

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Vercel 로깅을 위한 헬퍼 함수
def log(message, level="INFO"):
    """Vercel에서 보이는 로깅 함수"""
    msg = f"[{level}] {message}"
    # stdout과 stderr 모두에 출력 (Vercel이 둘 다 캡처)
    print(msg, file=sys.stdout, flush=True)
    print(msg, file=sys.stderr, flush=True)

# 프로젝트 루트 및 필수 서브 경로 등록
project_root = Path(__file__).parent.parent
paths_to_add = [
    (project_root, "프로젝트 루트"),
    (project_root / "backend" / "shared", "공유 모듈"),
    (project_root / "backend" / "api-gateway" / "src", "API Gateway 소스"),
]

for target_path, label in paths_to_add:
    path_str = str(target_path)
    if not target_path.exists():
        log(f"경로 추가 실패: {label} -> {target_path} (존재하지 않음)", "WARN")
        continue
    if path_str in sys.path:
        log(f"경로 이미 등록됨: {label} -> {target_path}")
        continue
    sys.path.insert(0, path_str)
    log(f"경로 추가 성공: {label} -> {target_path}")

# 디버깅을 위한 경로 출력
log(f"=== Vercel 서버리스 함수 시작 ===")
log(f"Python path: {sys.path}")
log(f"Project root: {project_root}")
log(f"Current working directory: {os.getcwd()}")
log(f"Python version: {sys.version}")

# 초기화 에러를 저장할 전역 변수
_init_error = None

# FastAPI 기본 import (이것은 반드시 성공해야 함)
try:
    log("FastAPI import 시도 중...")
    from fastapi import FastAPI, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    log("✓ FastAPI import 성공")
except Exception as e:
    log(f"✗ FastAPI import error: {e}", "ERROR")
    log(f"Traceback: {traceback.format_exc()}", "ERROR")
    _init_error = f"FastAPI import failed: {e}"
    # FastAPI가 없으면 앱을 생성할 수 없으므로 raise
    raise

# 나머지 모듈 import (실패해도 앱은 생성 가능)
settings = None
routes_modules = {}

try:
    log("Settings 모듈 import 시도 중...")
    from config.settings import settings
    log("✓ Settings import 성공")
    if settings:
        log(f"Database URL 설정됨: {bool(settings.database_url or settings.supabase_db_url)}")
except Exception as e:
    log(f"✗ Settings import error: {e}", "ERROR")
    log(f"Current sys.path: {sys.path}", "ERROR")
    log(f"Traceback: {traceback.format_exc()}", "ERROR")
    _init_error = f"Settings import failed: {e}"

try:
    log("Routes 모듈 import 시도 중...")
    from routes import auth, keywords, feed, articles, stats, share, notifications
    routes_modules = {
        'auth': auth,
        'keywords': keywords,
        'feed': feed,
        'articles': articles,
        'stats': stats,
        'share': share,
        'notifications': notifications
    }
    log("✓ Routes import 성공")
except Exception as e:
    log(f"✗ Routes import error: {e}", "ERROR")
    log(f"Trying to import from: backend/api-gateway/src/routes", "ERROR")
    log(f"Current sys.path: {sys.path}", "ERROR")
    log(f"Traceback: {traceback.format_exc()}", "ERROR")
    if not _init_error:
        _init_error = f"Routes import failed: {e}"

# FastAPI 앱 생성 (반드시 성공해야 함)
log("FastAPI 앱 생성 시도 중...")
app = FastAPI(
    title="#onmi API Gateway",
    description="키워드 기반 뉴스 트래킹 & 감성분석 API",
    version="1.0.0"
)
log("✓ FastAPI 앱 생성 성공")

# 초기화 에러가 있으면 에러 엔드포인트만 제공
if _init_error:
    log(f"⚠️ 초기화 에러로 인해 제한된 모드로 실행: {_init_error}", "WARN")
    
    @app.get("/")
    async def root_error():
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": "Application initialization failed",
                "details": _init_error,
                "message": "서버 초기화 중 오류가 발생했습니다. 로그를 확인하세요."
            }
        )
    
    @app.get("/health")
    async def health_error():
        return JSONResponse(
            status_code=500,
            content={
                "status": "unhealthy",
                "error": _init_error
            }
        )
    
    log("⚠️ 제한된 모드로 앱 실행 중 (에러 엔드포인트만 제공)")
else:
    # 정상 초기화 - 환경 변수 검증
    def validate_environment():
        """필수 환경 변수 검증"""
        log("환경 변수 검증 시작...")
        missing_vars = []
        
        # DATABASE_URL 또는 SUPABASE_DB_URL 중 하나는 필수
        if not settings.database_url and not settings.supabase_db_url:
            missing_vars.append("DATABASE_URL 또는 SUPABASE_DB_URL")
        
        # JWT_SECRET은 필수 (기본값이 있지만 프로덕션에서는 변경 필요)
        if not settings.jwt_secret or settings.jwt_secret == "your-secret-key-change-in-production":
            log("경고: JWT_SECRET이 기본값으로 설정되어 있습니다. 프로덕션에서는 변경하세요.", "WARN")
        
        if missing_vars:
            error_msg = f"필수 환경 변수가 누락되었습니다: {', '.join(missing_vars)}"
            log(error_msg, "ERROR")
            raise ValueError(error_msg)
        
        log("✓ 환경 변수 검증 완료")

    try:
        validate_environment()
    except Exception as e:
        log(f"✗ 환경 변수 검증 실패: {e}", "ERROR")
        log(f"Traceback: {traceback.format_exc()}", "ERROR")
        _init_error = f"Environment validation failed: {e}"

    try:
        log("CORS 미들웨어 추가 시도 중...")
        # CORS 설정
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        log("✓ CORS 미들웨어 추가 성공")
    except Exception as e:
        log(f"✗ CORS 미들웨어 추가 실패: {e}", "ERROR")
        log(f"Traceback: {traceback.format_exc()}", "ERROR")

    try:
        log("라우터 등록 시도 중...")
        # 라우터 등록
        if routes_modules.get('auth'):
            app.include_router(routes_modules['auth'].router, prefix="/auth", tags=["인증"])
        if routes_modules.get('keywords'):
            app.include_router(routes_modules['keywords'].router, prefix="/keywords", tags=["키워드"])
        if routes_modules.get('feed'):
            app.include_router(routes_modules['feed'].router, prefix="/feed", tags=["피드"])
        if routes_modules.get('articles'):
            app.include_router(routes_modules['articles'].router, prefix="/articles", tags=["기사"])
        if routes_modules.get('stats'):
            app.include_router(routes_modules['stats'].router, prefix="/stats", tags=["통계"])
        if routes_modules.get('share'):
            app.include_router(routes_modules['share'].router, prefix="/share", tags=["공유"])
        if routes_modules.get('notifications'):
            app.include_router(routes_modules['notifications'].router, prefix="/notifications", tags=["알림"])
        log("✓ 라우터 등록 완료")
    except Exception as e:
        log(f"✗ 라우터 등록 실패: {e}", "ERROR")
        log(f"Traceback: {traceback.format_exc()}", "ERROR")


# 정상 초기화된 경우에만 기본 엔드포인트 제공
if not _init_error:
    @app.get("/")
    async def root():
        """헬스 체크 엔드포인트"""
        return {"status": "ok", "service": "onmi-api-gateway"}

    @app.get("/health")
    async def health():
        """상세 헬스 체크"""
        return {
            "status": "healthy",
            "service": "onmi-api-gateway",
            "version": "1.0.0"
        }


# Cron Job 엔드포인트 (정상 초기화된 경우에만)
if not _init_error and settings:
    @app.get("/api/cron/crawl")
    @app.post("/api/cron/crawl")
    async def cron_crawl(request: Request):
        """Vercel Cron Job - 크롤링 작업"""
        # Cron Job 인증 확인 (선택사항)
        # Vercel Cron은 자동으로 호출하지만, 추가 보안을 위해 CRON_SECRET 사용 가능
        cron_secret = settings.cron_secret
        if cron_secret:
            auth_header = request.headers.get("Authorization", "")
            if auth_header != f"Bearer {cron_secret}":
                return JSONResponse(
                    status_code=401,
                    content={"error": "Unauthorized"}
                )
        
        # 크롤링 작업 실행
        try:
            # 경로 조정: api/cron/crawl.py에서 import
            sys.path.insert(0, str(project_root / "api"))
            from cron.crawl import CrawlerWorker
            
            worker = CrawlerWorker()
            await worker.run_crawl_job()
            
            return {
                "status": "success",
                "message": "크롤링 작업이 완료되었습니다"
            }
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            log(f"✗ Cron job error: {error_trace}", "ERROR")
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "error": str(e)
                }
            )


# 전역 예외 핸들러 추가 (모든 미처리 예외를 잡기 위해)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """전역 예외 핸들러 - 모든 미처리 예외를 로깅하고 적절한 응답 반환"""
    error_trace = traceback.format_exc()
    log(f"✗ 전역 예외 발생: {type(exc).__name__}: {str(exc)}", "ERROR")
    log(f"Request: {request.method} {request.url}", "ERROR")
    log(f"Traceback: {error_trace}", "ERROR")
    
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "error": str(exc),
            "type": type(exc).__name__
        }
    )

# Vercel은 자동으로 ASGI 앱을 감지하므로 별도 핸들러 불필요
log("=== Vercel 서버리스 함수 초기화 완료 ===")

