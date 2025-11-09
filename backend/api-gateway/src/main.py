"""API Gateway 메인 애플리케이션"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from contextlib import asynccontextmanager
import sys
import os
import logging
import time
import json

# 공통 모듈 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))

from src.routes import auth, keywords, feed, articles, stats, share, notifications
from database.connection import init_db_pool, close_db_pool

# 로깅 설정 - 콘솔 및 파일 출력
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
log_file = os.path.join(os.path.dirname(__file__), '../../logs', 'api-gateway.log')

# 로그 디렉토리 생성
os.makedirs(os.path.dirname(log_file), exist_ok=True)

# 파일 핸들러와 콘솔 핸들러 모두 추가
handlers = [
    logging.StreamHandler(sys.stdout),  # 콘솔 출력
    logging.FileHandler(log_file, encoding='utf-8')  # 파일 출력
]

logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=handlers,
    force=True  # 기존 핸들러 덮어쓰기
)

logger = logging.getLogger(__name__)
logger.info(f"로깅 초기화 완료 - 로그 파일: {log_file}")

# uvicorn 로거도 설정
uvicorn_logger = logging.getLogger("uvicorn")
uvicorn_logger.setLevel(logging.INFO)
uvicorn_access_logger = logging.getLogger("uvicorn.access")
uvicorn_access_logger.setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """서버 시작/종료 시 실행되는 lifespan 이벤트"""
    # 서버 시작 시
    logger.info("서버 시작 중...")
    try:
        await init_db_pool()
        logger.info("데이터베이스 연결 풀 초기화 완료")
    except Exception as e:
        logger.error(f"데이터베이스 연결 풀 초기화 실패: {e}")
        raise
    
    yield
    
    # 서버 종료 시
    logger.info("서버 종료 중...")
    try:
        await close_db_pool()
        logger.info("데이터베이스 연결 풀 종료 완료")
    except Exception as e:
        logger.error(f"데이터베이스 연결 풀 종료 중 오류: {e}")


app = FastAPI(
    title="#onmi API Gateway",
    description="키워드 기반 뉴스 트래킹 & 감성분석 API",
    version="1.0.0",
    lifespan=lifespan
)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """요청/응답 로깅 미들웨어"""
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # 요청 정보 로깅
        logger.info("=" * 80)
        logger.info(f"📥 요청 수신: {request.method} {request.url}")
        logger.info(f"   클라이언트: {request.client.host if request.client else 'N/A'}")
        
        # 헤더 로깅 (민감한 정보 제외)
        headers_dict = dict(request.headers)
        if 'authorization' in headers_dict:
            headers_dict['authorization'] = 'Bearer ***'
        logger.info(f"   헤더: {headers_dict}")
        
        # 요청 본문 읽기 (한 번만)
        body_bytes = b""
        body_str = None
        try:
            body_bytes = await request.body()
            if body_bytes:
                body_str = body_bytes.decode('utf-8')
                logger.info(f"   본문: {body_str[:500]}")  # 최대 500자만
        except Exception as e:
            logger.warning(f"   본문 읽기 실패: {e}")
        
        # 요청 본문을 다시 설정 (다음 핸들러가 읽을 수 있도록)
        async def receive():
            return {"type": "http.request", "body": body_bytes}
        request._receive = receive
        
        # 응답 처리
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            logger.info(f"📤 응답 전송: {request.method} {request.url}")
            logger.info(f"   상태 코드: {response.status_code}")
            logger.info(f"   처리 시간: {process_time:.3f}초")
            logger.info("=" * 80)
            return response
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(f"❌ 요청 처리 실패: {request.method} {request.url}")
            logger.error(f"   오류: {str(e)}")
            logger.error(f"   처리 시간: {process_time:.3f}초")
            logger.info("=" * 80)
            raise


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """요청 검증 오류 핸들러 - 422 오류 상세 정보 제공"""
    logger.error("=" * 80)
    logger.error(f"❌ 요청 검증 실패: {request.method} {request.url}")
    logger.error(f"   검증 오류 상세:")
    for error in exc.errors():
        logger.error(f"     - 필드: {error.get('loc', [])}")
        logger.error(f"       타입: {error.get('type', 'N/A')}")
        logger.error(f"       메시지: {error.get('msg', 'N/A')}")
    
    # 요청 본문 읽기 (한 번만)
    try:
        body = await request.body()
        body_str = body.decode('utf-8') if body else None
        logger.error(f"   요청 본문: {body_str}")
    except Exception as e:
        logger.error(f"   요청 본문 읽기 실패: {e}")
        body_str = None
    
    logger.error("=" * 80)
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "body": body_str
        }
    )

# 요청 로깅 미들웨어 추가 (CORS보다 먼저)
app.add_middleware(RequestLoggingMiddleware)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(auth.router, prefix="/auth", tags=["인증"])
app.include_router(keywords.router, prefix="/keywords", tags=["키워드"])
app.include_router(feed.router, prefix="/feed", tags=["피드"])
app.include_router(articles.router, prefix="/articles", tags=["기사"])
app.include_router(stats.router, prefix="/stats", tags=["통계"])
app.include_router(share.router, prefix="/share", tags=["공유"])
app.include_router(notifications.router, prefix="/notifications", tags=["알림"])


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

