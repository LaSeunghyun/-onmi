"""크롤링 및 요약 통합 스크립트"""
import sys
import os
from pathlib import Path
import asyncio
from uuid import UUID
import logging
from datetime import datetime

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except AttributeError:
        pass

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend" / "shared"))
sys.path.insert(0, str(project_root / "backend" / "ingestor" / "src"))
sys.path.insert(0, str(project_root / "backend" / "nlp-service" / "src"))
sys.path.insert(0, str(project_root / "backend" / "api-gateway" / "src"))

import asyncpg
from config.settings import settings
from services.crawl_service import CrawlService
from services.summary_service import SummaryService

# 로깅 설정
log_dir = Path(__file__).parent / "backend" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "crawl_and_summarize.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


async def main():
    """메인 함수"""
    logger.info(f"{'='*80}")
    logger.info(f"admin@onmi.com 계정 키워드 기사 수집 및 요약 생성")
    logger.info(f"{'='*80}")
    logger.info(f"시작 시간: {datetime.now()}")
    
    # 서비스 초기화
    crawl_service = CrawlService()
    summary_service = SummaryService()
    
    # 데이터베이스 연결
    conn = await asyncpg.connect(settings.database_url)
    
    try:
        # 사용자 조회 (admin@onmi.com)
        user = await conn.fetchrow(
            "SELECT id, email FROM users WHERE email = $1",
            "admin@onmi.com"
        )
        
        if not user:
            logger.error("admin@onmi.com 계정을 찾을 수 없습니다.")
            return
        
        user_id = UUID(str(user['id']))
        logger.info(f"사용자 확인: {user['email']} (ID: {user_id})")
        
        # 활성 키워드 조회
        keywords = await conn.fetch(
            """
            SELECT id, text
            FROM keywords
            WHERE user_id = $1 AND status = 'active'
            ORDER BY created_at DESC
            """,
            user_id
        )
        
        if not keywords:
            logger.warning("등록된 활성 키워드가 없습니다.")
            return
            
        logger.info(f"{len(keywords)}개의 활성 키워드를 찾았습니다.")
        
        # 키워드별 크롤링 수행
        total_saved = 0
        for kw in keywords:
            try:
                saved = await crawl_service.crawl_and_save_keyword(
                    keyword_id=kw['id'],
                    user_id=user_id,
                    keyword_text=kw['text']
                )
                total_saved += saved
                
                # 키워드별 요약 생성 (기사가 있는 경우)
                if saved > 0:
                    logger.info(f"  -> 키워드 요약 생성: {kw['text']}")
                    await summary_service.generate_keyword_summary(kw['id'], user_id)
                    
            except Exception as e:
                logger.error(f"키워드 처리 중 오류 ({kw['text']}): {e}", exc_info=True)
                continue
        
        # 일일 요약 생성
        logger.info(f"{'='*80}")
        logger.info(f"일일 요약 생성")
        logger.info(f"{'='*80}")
        
        if total_saved > 0:
            try:
                daily_result = await summary_service.generate_daily_summary(user_id)
                logger.info(f"일일 요약 생성 완료 (세션: {daily_result.get('session_id')})")
            except Exception as e:
                logger.error(f"일일 요약 생성 실패: {e}", exc_info=True)
        else:
            logger.info("수집된 기사가 없어 일일 요약 생성을 건너뜁니다.")
            
        logger.info(f"작업 완료. 총 저장 기사: {total_saved}개")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    # Windows에서 asyncio 정책 설정
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n작업이 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n예상치 못한 오류: {e}")
