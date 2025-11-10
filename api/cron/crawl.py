"""Vercel Cron Job - Google CSE 크롤링 작업"""
import sys
import os
from pathlib import Path
import asyncio
from datetime import datetime
from uuid import UUID

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend" / "shared"))
sys.path.insert(0, str(project_root / "backend" / "ingestor" / "src"))
sys.path.insert(0, str(project_root / "backend" / "nlp-service" / "src"))
sys.path.insert(0, str(project_root / "backend" / "api-gateway" / "src"))

import asyncpg
from config.settings import settings
from collectors.google_cse_collector import (
    GoogleCSECollector,
    CSEQueryLimitExceededError,
)
from processors.deduplicator import Deduplicator
from sentiment.rule_based import RuleBasedSentimentAnalyzer
from services.cse_query_limit_service import CSEQueryLimitService


class CrawlerWorker:
    """크롤러 워커 클래스"""
    
    def __init__(self):
        self.cse_collector = GoogleCSECollector()
        self.deduplicator = Deduplicator()
        self.sentiment_analyzer = RuleBasedSentimentAnalyzer()
        self.quota_service = CSEQueryLimitService()
    
    async def crawl_keyword(self, keyword_id: UUID, user_id: UUID, keyword_text: str, db_conn):
        """키워드별 기사 수집 및 처리"""
        print(f"키워드 수집 시작: {keyword_text} (ID: {keyword_id})")
        
        # Google CSE로 키워드 검색
        try:
            all_articles = await self.cse_collector.search_by_keyword(
                keyword_text,
                date_range=None,  # Cron Job은 전체 기간 검색
                max_results=100,
                user_id=user_id,
                keyword_id=keyword_id,
                quota_manager=self.quota_service
            )
        except CSEQueryLimitExceededError as exc:
            detail = getattr(exc, "detail", {})
            print(f"쿼리 제한 초과: {keyword_text} - detail={detail}")
            return 0
        
        # 중복 제거
        unique_articles = self.deduplicator.filter_duplicates(all_articles)
        
        # 데이터베이스에 저장
        saved_count = 0
        for article in unique_articles:
            try:
                # 기사 저장 또는 조회
                article_id = await db_conn.fetchval(
                    """
                    INSERT INTO articles (url, title, snippet, source, published_at, lang)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (url) DO UPDATE SET title = EXCLUDED.title
                    RETURNING id
                    """,
                    article['url'],
                    article['title'],
                    article.get('snippet', ''),
                    article.get('source', ''),
                    article.get('published_at'),
                    article.get('lang', 'ko')
                )
                
                # 키워드-기사 매핑 저장
                await db_conn.execute(
                    """
                    INSERT INTO keyword_articles (keyword_id, article_id, match_score, match_type)
                    VALUES ($1, $2, 1.0, 'exact')
                    ON CONFLICT (keyword_id, article_id) DO NOTHING
                    """,
                    keyword_id, article_id
                )
                
                # 감성 분석 수행
                sentiment_result = self.sentiment_analyzer.analyze(
                    article['title'],
                    article.get('snippet', '')
                )
                
                # 감성 분석 결과 저장
                await db_conn.execute(
                    """
                    INSERT INTO sentiments (article_id, label, score, rationale, model_ver)
                    VALUES ($1, $2, $3, $4, 'rule-based-v1')
                    ON CONFLICT (article_id) DO UPDATE SET
                        label = EXCLUDED.label,
                        score = EXCLUDED.score,
                        rationale = EXCLUDED.rationale
                    """,
                    article_id,
                    sentiment_result['label'],
                    sentiment_result['score'],
                    sentiment_result['rationale']
                )
                
                saved_count += 1
            
            except Exception as e:
                print(f"기사 저장 오류: {e}")
                continue
        
        # 키워드의 last_crawled_at 업데이트
        await db_conn.execute(
            "UPDATE keywords SET last_crawled_at = NOW() WHERE id = $1",
            keyword_id
        )
        
        print(f"키워드 수집 완료: {keyword_text} - {saved_count}개 기사 저장")
        return saved_count
    
    async def run_crawl_job(self):
        """크롤링 작업 실행"""
        print(f"크롤링 작업 시작: {datetime.now()}")
        
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
            
            print(f"수집 대상 키워드 수: {len(keywords)}")
            
            # 각 키워드별 수집
            for keyword in keywords:
                try:
                    await self.crawl_keyword(
                        keyword['id'],
                        keyword['user_id'],
                        keyword['text'],
                        conn
                    )
                except Exception as e:
                    print(f"키워드 수집 오류 ({keyword['text']}): {e}")
                    continue
        
        finally:
            await conn.close()
        
        print(f"크롤링 작업 완료: {datetime.now()}")


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
        print(f"크롤링 작업 오류: {e}")
        return {
            "statusCode": 500,
            "body": {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        }



