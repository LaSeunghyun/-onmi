"""Vercel Cron Job - Google CSE 크롤링 작업"""
import sys
import os
from pathlib import Path
import asyncio
from datetime import datetime
from uuid import UUID
import logging

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend" / "shared"))
sys.path.insert(0, str(project_root / "backend" / "ingestor" / "src"))
sys.path.insert(0, str(project_root / "backend" / "nlp-service" / "src"))
sys.path.insert(0, str(project_root / "backend" / "api-gateway" / "src"))

import asyncpg
from config.settings import settings
from services.crawl_service import CrawlService

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CrawlerWorker:
    """크롤러 워커 클래스"""
    
    def __init__(self):
        self.crawl_service = CrawlService()
    
    async def run_crawl_job(self):
        """크롤링 작업 실행"""
        logger.info(f"크롤링 작업 시작: {datetime.now()}")
        
        # 데이터베이스 연결
        conn = await asyncpg.connect(settings.database_url)
        
        try:
            # 활성 키워드 조회
            keywords = await conn.fetch(
                """
                SELECT id, user_id, text
                FROM keywords
                WHERE status = 'active'
                """
            )
            
            logger.info(f"수집 대상 키워드 수: {len(keywords)}")
            
            # 각 키워드별 수집
            for keyword in keywords:
                try:
                    keyword_id = keyword['id']
                    user_id = keyword['user_id']
                    keyword_text = keyword['text']
                    
                    await self.crawl_service.crawl_and_save_keyword(
                        keyword_id=keyword_id,
                        user_id=user_id,
                        keyword_text=keyword_text,
                        date_range=None  # 전체 기간 (또는 정책에 따라 설정)
                    )
                    
                except Exception as e:
                    logger.error(f"키워드 수집 오류 ({keyword['text']}): {e}")
                    continue
        
        finally:
            await conn.close()
        
        logger.info(f"크롤링 작업 완료: {datetime.now()}")


async def handler(request):
    """Vercel Cron Job 핸들러"""
    try:
        worker = CrawlerWorker()
        await worker.run_crawl_job()
        return {
            "statusCode": 200,
            "body": {
                "message": "크롤링 작업이 완료되었습니다",
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"크롤링 작업 오류: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        }
