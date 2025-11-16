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

# Windows 콘솔 인코딩 설정 (멀티프로세싱 환경에서도 적용)
if sys.platform == 'win32':
    # 환경 변수로 Python I/O 인코딩 설정 (자식 프로세스에도 전파)
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    # 멀티프로세싱 환경에서도 인코딩이 적용되도록 설정
    os.environ['PYTHONLEGACYWINDOWSSTDIO'] = '0'
    import codecs
    # 현재 프로세스의 stdout/stderr 인코딩 설정
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    if hasattr(sys.stderr, 'buffer'):
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# 현재 디렉토리(backend/api-gateway)를 sys.path에 추가
# 멀티프로세싱 환경에서도 자식 프로세스가 src 모듈을 찾을 수 있도록 함
# 절대 경로를 사용하여 Windows 멀티프로세싱 환경에서도 안정적으로 동작
current_file = os.path.abspath(__file__)
current_dir = os.path.dirname(os.path.dirname(current_file))
current_dir_abs = os.path.abspath(current_dir)

# sys.path에 추가 (중복 방지)
if current_dir_abs not in sys.path:
    sys.path.insert(0, current_dir_abs)

# 공통 모듈 경로 추가 (절대 경로 사용)
shared_path = os.path.abspath(os.path.join(current_dir, '../shared'))
if shared_path not in sys.path:
    sys.path.append(shared_path)

# 환경 변수에도 설정 (멀티프로세싱 자식 프로세스가 상속받을 수 있도록)
os.environ['PYTHONPATH'] = f"{current_dir_abs};{shared_path};{os.environ.get('PYTHONPATH', '')}"

from src.routes import auth, keywords, feed, articles, stats, share, notifications, summaries, preferences
from src.middleware.token_limit_middleware import TokenLimitMiddleware
from database.connection import init_db_pool, close_db_pool

# 로깅 설정 - 콘솔 및 파일 출력
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
log_file = os.path.join(os.path.dirname(__file__), '../../logs', 'api-gateway.log')

# 로그 디렉토리 생성
os.makedirs(os.path.dirname(log_file), exist_ok=True)

# UTF-8 인코딩을 보장하는 커스텀 StreamHandler
class UTF8StreamHandler(logging.StreamHandler):
    """UTF-8 인코딩을 보장하는 StreamHandler"""
    def __init__(self, stream=None):
        super().__init__(stream)
        if sys.platform == 'win32' and hasattr(stream, 'buffer'):
            # Windows에서 UTF-8 인코딩 강제
            import codecs
            self.stream = codecs.getwriter('utf-8')(stream.buffer, 'strict')
    
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            stream.write(msg + self.terminator)
            self.flush()
        except UnicodeEncodeError:
            # 인코딩 오류 발생 시 이모지를 제거하고 재시도
            try:
                record.msg = str(record.msg).encode('ascii', 'ignore').decode('ascii')
                msg = self.format(record)
                stream = self.stream
                stream.write(msg + self.terminator)
                self.flush()
            except Exception:
                self.handleError(record)
        except Exception:
            self.handleError(record)

# 파일 핸들러와 콘솔 핸들러 모두 추가
handlers = [
    UTF8StreamHandler(sys.stdout),  # UTF-8 보장 콘솔 출력
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

# uvicorn 로거도 UTF-8 핸들러 사용하도록 설정
uvicorn_logger = logging.getLogger("uvicorn")
uvicorn_logger.setLevel(logging.INFO)
uvicorn_logger.handlers = []  # 기존 핸들러 제거
uvicorn_logger.addHandler(UTF8StreamHandler(sys.stdout))
uvicorn_logger.propagate = False  # 루트 로거로 전파 방지

uvicorn_access_logger = logging.getLogger("uvicorn.access")
uvicorn_access_logger.setLevel(logging.INFO)
uvicorn_access_logger.handlers = []  # 기존 핸들러 제거
uvicorn_access_logger.addHandler(UTF8StreamHandler(sys.stdout))  # 콘솔 출력
uvicorn_access_logger.addHandler(logging.FileHandler(log_file, encoding='utf-8'))  # 파일 출력
uvicorn_access_logger.propagate = False  # 루트 로거로 전파 방지


@asynccontextmanager
async def lifespan(app: FastAPI):
    """서버 시작/종료 시 실행되는 lifespan 이벤트"""
    from datetime import datetime, timezone, timedelta
    
    # 한국 시간대 (KST = UTC+9)
    KST = timezone(timedelta(hours=9))
    
    # 서버 시작 시
    now_utc = datetime.now(timezone.utc)
    now_kst = now_utc.astimezone(KST)
    logger.info("=" * 80)
    logger.info("서버 시작 중...")
    logger.info(f"현재 시간 (UTC): {now_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    logger.info(f"현재 시간 (KST): {now_kst.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    logger.info("=" * 80)
    
    db_initialized = False
    try:
        logger.info("데이터베이스 연결 풀 초기화 시도 중...")
        await init_db_pool()
        db_initialized = True
        logger.info("✅ 데이터베이스 연결 풀 초기화 완료")
    except RuntimeError as e:
        # 데이터베이스 연결 관련 오류
        error_msg = str(e)
        logger.error("=" * 80)
        logger.error("❌ 데이터베이스 연결 풀 초기화 실패")
        logger.error(f"오류 유형: RuntimeError")
        logger.error(f"오류 메시지: {error_msg}")
        logger.error("")
        logger.error("가능한 원인:")
        logger.error("  1. DATABASE_URL 또는 SUPABASE_DB_URL 환경변수가 설정되지 않음")
        logger.error("  2. 데이터베이스 연결 문자열이 잘못됨")
        logger.error("  3. 데이터베이스 서버에 연결할 수 없음 (네트워크 문제)")
        logger.error("  4. 인증 정보가 잘못됨 (사용자명/비밀번호)")
        logger.error("")
        logger.error("해결 방법:")
        logger.error("  1. 프로젝트 루트의 .env 파일에 DATABASE_URL을 설정하세요")
        logger.error("  2. check_environment.ps1 스크립트를 실행하여 환경을 확인하세요")
        logger.error("=" * 80)
        # 서버 시작 실패를 명확히 알리기 위해 예외 재발생
        raise RuntimeError(
            f"서버 시작 실패: 데이터베이스 연결을 초기화할 수 없습니다.\n"
            f"상세 오류: {error_msg}\n"
            f"로그 파일을 확인하거나 check_environment.ps1을 실행하여 환경을 확인하세요."
        ) from e
    except ImportError as e:
        # 모듈 import 오류
        logger.error("=" * 80)
        logger.error("❌ 필수 모듈 import 실패")
        logger.error(f"오류 유형: ImportError")
        logger.error(f"오류 메시지: {str(e)}")
        logger.error("")
        logger.error("해결 방법:")
        logger.error("  1. 가상환경이 활성화되어 있는지 확인하세요")
        logger.error("  2. 'pip install -r requirements.txt'를 실행하여 의존성을 설치하세요")
        logger.error("=" * 80)
        raise
    except Exception as e:
        # 기타 예상치 못한 오류
        import traceback
        logger.error("=" * 80)
        logger.error("❌ 서버 시작 중 예상치 못한 오류 발생")
        logger.error(f"오류 유형: {type(e).__name__}")
        logger.error(f"오류 메시지: {str(e)}")
        logger.error("")
        logger.error("상세 스택 트레이스:")
        logger.error(traceback.format_exc())
        logger.error("=" * 80)
        raise RuntimeError(
            f"서버 시작 실패: 예상치 못한 오류가 발생했습니다.\n"
            f"오류 유형: {type(e).__name__}\n"
            f"오류 메시지: {str(e)}\n"
            f"로그 파일을 확인하세요: {log_file}"
        ) from e
    
    try:
        yield
    finally:
        # 서버 종료 시
        logger.info("=" * 80)
        logger.info("서버 종료 중...")
        logger.info("=" * 80)
        
        if db_initialized:
            try:
                await close_db_pool()
                logger.info("✅ 데이터베이스 연결 풀 종료 완료")
            except Exception as e:
                logger.error(f"⚠️ 데이터베이스 연결 풀 종료 중 오류: {e}")
                # 종료 중 오류는 서버 종료를 막지 않음


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
        
        # 요청 정보 로깅 (간소화)
        method = request.method
        url = str(request.url)
        client_host = request.client.host if request.client else 'N/A'
        
        # URL에서 쿼리 파라미터 제거 (가독성 향상)
        url_path = url.split('?')[0] if '?' in url else url
        
        logger.info("=" * 80)
        logger.info(f"[REQUEST] {method} {url_path}")
        logger.info(f"  Client: {client_host}")
        
        # 헤더 로깅 (민감한 정보 제외, 간소화)
        headers_dict = dict(request.headers)
        if 'authorization' in headers_dict:
            headers_dict['authorization'] = 'Bearer ***'
        # 주요 헤더만 로깅
        important_headers = {k: v for k, v in headers_dict.items() 
                           if k.lower() in ['user-agent', 'content-type', 'accept', 'host']}
        if important_headers:
            logger.info(f"  Headers: {important_headers}")
        
        # 요청 본문 읽기 (한 번만)
        body_bytes = b""
        body_str = None
        try:
            body_bytes = await request.body()
            if body_bytes:
                body_str = body_bytes.decode('utf-8')
                if len(body_str) > 0:
                    logger.info(f"  Body: {body_str[:200]}")  # 최대 200자만
        except Exception as e:
            logger.warning(f"  Body read failed: {e}")
        
        # 요청 본문을 다시 설정 (다음 핸들러가 읽을 수 있도록)
        async def receive():
            return {"type": "http.request", "body": body_bytes}
        request._receive = receive
        
        # 응답 처리
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            logger.info(f"[RESPONSE] {method} {url_path}")
            logger.info(f"  Status: {response.status_code}")
            logger.info(f"  Time: {process_time:.3f}s")
            logger.info("=" * 80)
            return response
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(f"[ERROR] {method} {url_path}")
            logger.error(f"  Error: {str(e)}")
            logger.error(f"  Time: {process_time:.3f}s")
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

# 토큰 제한 확인 미들웨어 추가 (가장 먼저)
app.add_middleware(TokenLimitMiddleware)

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
app.include_router(summaries.router, prefix="/summaries", tags=["요약"])
app.include_router(preferences.router, prefix="/preferences", tags=["선호도"])


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


# 직접 실행 시 uvicorn 서버 시작
if __name__ == "__main__":
    import uvicorn
    from datetime import datetime, timezone, timedelta
    
    # 한국 시간대 (KST = UTC+9)
    KST = timezone(timedelta(hours=9))
    
    # 현재 시간을 한국 시간으로 변환하여 로그 출력
    now_utc = datetime.now(timezone.utc)
    now_kst = now_utc.astimezone(KST)
    logger.info("=" * 80)
    logger.info(f"서버 시작 시간 (UTC): {now_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    logger.info(f"서버 시작 시간 (KST): {now_kst.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    logger.info("=" * 80)
    
    # 현재 파일의 디렉토리를 기준으로 작업 디렉토리 설정
    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(app_dir)
    # uvicorn 실행
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[app_dir],
        access_log=True  # HTTP 요청/응답 로깅 활성화
    )

