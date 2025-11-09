"""Vercel 서버리스 함수 진입점 - FastAPI 앱"""
import sys
import os
import traceback
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend" / "shared"))
sys.path.insert(0, str(project_root / "backend" / "api-gateway" / "src"))

# 디버깅을 위한 경로 출력
print(f"Python path: {sys.path}", file=sys.stderr)
print(f"Project root: {project_root}", file=sys.stderr)
print(f"Current working directory: {os.getcwd()}", file=sys.stderr)

try:
    from fastapi import FastAPI, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    print("FastAPI import 성공", file=sys.stderr)
except Exception as e:
    print(f"FastAPI import error: {e}", file=sys.stderr)
    print(traceback.format_exc(), file=sys.stderr)
    raise

try:
    # 설정 모듈 import
    from config.settings import settings
    print("Settings import 성공", file=sys.stderr)
except Exception as e:
    print(f"Settings import error: {e}", file=sys.stderr)
    print(f"Current sys.path: {sys.path}", file=sys.stderr)
    print(traceback.format_exc(), file=sys.stderr)
    raise

try:
    # 라우터 import - 절대 경로 사용
    from src.routes import auth, keywords, feed, articles, stats, share, notifications
    print("Routes import 성공", file=sys.stderr)
except Exception as e:
    print(f"Routes import error: {e}", file=sys.stderr)
    print(f"Trying to import from: backend/api-gateway/src/routes", file=sys.stderr)
    print(f"Current sys.path: {sys.path}", file=sys.stderr)
    print(traceback.format_exc(), file=sys.stderr)
    raise

# 환경 변수 검증
def validate_environment():
    """필수 환경 변수 검증"""
    missing_vars = []
    
    # DATABASE_URL 또는 SUPABASE_DB_URL 중 하나는 필수
    if not settings.database_url and not settings.supabase_db_url:
        missing_vars.append("DATABASE_URL 또는 SUPABASE_DB_URL")
    
    # JWT_SECRET은 필수 (기본값이 있지만 프로덕션에서는 변경 필요)
    if not settings.jwt_secret or settings.jwt_secret == "your-secret-key-change-in-production":
        print("경고: JWT_SECRET이 기본값으로 설정되어 있습니다. 프로덕션에서는 변경하세요.", file=sys.stderr)
    
    if missing_vars:
        error_msg = f"필수 환경 변수가 누락되었습니다: {', '.join(missing_vars)}"
        print(error_msg, file=sys.stderr)
        raise ValueError(error_msg)
    
    print("환경 변수 검증 완료", file=sys.stderr)

try:
    validate_environment()
except Exception as e:
    print(f"환경 변수 검증 실패: {e}", file=sys.stderr)
    print(traceback.format_exc(), file=sys.stderr)
    raise

try:
    app = FastAPI(
        title="#onmi API Gateway",
        description="키워드 기반 뉴스 트래킹 & 감성분석 API",
        version="1.0.0"
    )
    print("FastAPI 앱 생성 성공", file=sys.stderr)
except Exception as e:
    print(f"FastAPI 앱 생성 실패: {e}", file=sys.stderr)
    print(traceback.format_exc(), file=sys.stderr)
    raise

try:
    # CORS 설정
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    print("CORS 미들웨어 추가 성공", file=sys.stderr)
except Exception as e:
    print(f"CORS 미들웨어 추가 실패: {e}", file=sys.stderr)
    print(traceback.format_exc(), file=sys.stderr)
    raise

try:
    # 라우터 등록
    app.include_router(auth.router, prefix="/auth", tags=["인증"])
    app.include_router(keywords.router, prefix="/keywords", tags=["키워드"])
    app.include_router(feed.router, prefix="/feed", tags=["피드"])
    app.include_router(articles.router, prefix="/articles", tags=["기사"])
    app.include_router(stats.router, prefix="/stats", tags=["통계"])
    app.include_router(share.router, prefix="/share", tags=["공유"])
    app.include_router(notifications.router, prefix="/notifications", tags=["알림"])
    print("라우터 등록 완료", file=sys.stderr)
except Exception as e:
    print(f"라우터 등록 실패: {e}", file=sys.stderr)
    print(traceback.format_exc(), file=sys.stderr)
    raise


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


# Cron Job 엔드포인트
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
        print(f"Cron job error: {error_trace}", file=sys.stderr)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": str(e)
            }
        )


# Vercel은 자동으로 ASGI 앱을 감지하므로 별도 핸들러 불필요
print("Vercel 서버리스 함수 초기화 완료", file=sys.stderr)

