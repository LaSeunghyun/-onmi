"""스케줄러 워커"""
import asyncio
import asyncpg
import sys
import os
from datetime import datetime, timedelta
from typing import List

# 공통 모듈 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))
from config.settings import settings

# 서비스 모듈 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '../../ingestor/src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../../nlp-service/src'))

from collectors.google_cse_collector import GoogleCSECollector
from processors.deduplicator import Deduplicator
from sentiment.rule_based import RuleBasedSentimentAnalyzer


class CrawlerWorker:
    """크롤러 워커 클래스"""
    
    def __init__(self):
        self.cse_collector = GoogleCSECollector()
        self.deduplicator = Deduplicator()
        self.sentiment_analyzer = RuleBasedSentimentAnalyzer()
    
    async def crawl_keyword(self, keyword_id: str, keyword_text: str, db_conn):
        """키워드별 기사 수집 및 처리"""
        print(f"키워드 수집 시작: {keyword_text} (ID: {keyword_id})")
        
        # Google CSE로 키워드 검색
        all_articles = self.cse_collector.search_by_keyword(
            keyword_text,
            date_range=None,  # 스케줄러는 전체 기간 검색
            max_results=100
        )
        
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
                SELECT id, text FROM keywords WHERE status = 'active'
                """
            )
            
            print(f"수집 대상 키워드 수: {len(keywords)}")
            
            # 각 키워드별 수집
            for keyword in keywords:
                try:
                    await self.crawl_keyword(
                        str(keyword['id']),
                        keyword['text'],
                        conn
                    )
                except Exception as e:
                    print(f"키워드 수집 오류 ({keyword['text']}): {e}")
                    continue
        
        finally:
            await conn.close()
        
        print(f"크롤링 작업 완료: {datetime.now()}")


async def main():
    """메인 함수"""
    worker = CrawlerWorker()
    await worker.run_crawl_job()


if __name__ == "__main__":
    asyncio.run(main())



