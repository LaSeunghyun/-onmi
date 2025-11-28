"""크롤링 서비스"""
from typing import Dict, Optional, List, Any
from datetime import datetime
from uuid import UUID
import sys
import os
import logging

# 리포지토리 및 모델 import
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../ingestor/src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../nlp-service/src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../shared'))

from collectors.google_cse_collector import GoogleCSECollector, CSEQueryLimitExceededError
from processors.deduplicator import Deduplicator
from sentiment.rule_based import RuleBasedSentimentAnalyzer
from services.cse_query_limit_service import CSEQueryLimitService
from repositories.article_repository import ArticleRepository
from database.connection import get_db_connection

logger = logging.getLogger(__name__)


class CrawlService:
    """크롤링 및 기사 처리 통합 서비스"""
    
    def __init__(self):
        self.cse_collector = GoogleCSECollector()
        self.deduplicator = Deduplicator()
        self.sentiment_analyzer = RuleBasedSentimentAnalyzer()
        self.quota_service = CSEQueryLimitService()
    
    async def crawl_and_save_keyword(
        self,
        keyword_id: UUID,
        user_id: UUID,
        keyword_text: str,
        date_range: Optional[tuple[datetime, datetime]] = None
    ) -> int:
        """
        키워드별 기사 수집, 중복 제거, 저장, 감성 분석을 수행합니다.
        
        Args:
            keyword_id: 키워드 ID
            user_id: 사용자 ID
            keyword_text: 검색할 키워드 텍스트
            date_range: (시작일, 종료일) 튜플, None이면 전체 기간
            
        Returns:
            저장된 기사 수
        """
        logger.info(f"키워드 수집 시작: {keyword_text} (ID: {keyword_id})")
        
        # 1. Google CSE로 키워드 검색
        try:
            all_articles = await self.cse_collector.search_by_keyword(
                keyword_text,
                date_range=date_range,
                max_results=100,
                user_id=user_id,
                keyword_id=keyword_id,
                quota_manager=self.quota_service
            )
        except CSEQueryLimitExceededError as exc:
            detail = getattr(exc, "detail", {})
            logger.warning(f"쿼리 제한 초과: {keyword_text} - detail={detail}")
            return 0
        except Exception as e:
            logger.error(f"크롤링 중 오류 발생 ({keyword_text}): {e}")
            return 0
            
        if not all_articles:
            logger.info(f"검색 결과 없음: {keyword_text}")
            return 0
            
        # 2. 중복 제거
        unique_articles = self.deduplicator.filter_duplicates(all_articles)
        logger.info(f"중복 제거: {len(all_articles)} -> {len(unique_articles)}개 기사")
        
        if not unique_articles:
            return 0
            
        # 3. 저장 및 감성 분석
        saved_count = 0
        
        # 트랜잭션보다는 개별 처리가 긴 작업에 유리할 수 있으나, 
        # ArticleRepository.upsert_batch를 활용하면 효율적임.
        # 하지만 현재 upsert_batch는 ID만 반환하고 sentiment 처리는 별도이므로 반복문 사용.
        
        for article in unique_articles:
            try:
                # 기사 저장 (URL 충돌 시 기존 기사 ID 반환)
                # ArticleRepository의 upsert_batch는 리스트를 받으므로 단건 리스트로 호출하거나
                # upsert_batch 로직을 활용해 단건 처리
                article_ids = await ArticleRepository.upsert_batch([article])
                if not article_ids:
                    continue
                    
                article_id = article_ids[0]
                
                # 키워드-기사 매핑 저장
                await ArticleRepository.link_keyword_article(keyword_id, article_id)
                
                # 감성 분석 수행
                sentiment_result = self.sentiment_analyzer.analyze(
                    article.get('title', ''),
                    article.get('snippet', '')
                )
                
                # 감성 분석 결과 저장
                await ArticleRepository.save_sentiment(article_id, sentiment_result)
                
                saved_count += 1
                
            except Exception as e:
                logger.warning(f"기사 저장 처리 중 오류 (url={article.get('url')}): {e}")
                continue
        
        # 4. 키워드 last_crawled_at 업데이트
        # TODO: KeywordRepository에 메서드 추가하거나 직접 실행
        try:
            async with get_db_connection() as conn:
                await conn.execute(
                    "UPDATE keywords SET last_crawled_at = NOW() WHERE id = $1",
                    keyword_id
                )
        except Exception as e:
            logger.warning(f"키워드 last_crawled_at 업데이트 실패: {e}")
            
        logger.info(f"키워드 수집 완료: {keyword_text} - {saved_count}개 기사 저장")
        return saved_count

    async def fetch_preview(
        self,
        keyword_text: str,
        date_range: Optional[tuple[datetime, datetime]] = None
    ) -> Dict[str, Any]:
        """
        미리보기용 크롤링 (DB 저장 없음)
        """
        # Google CSE 검색 (quota 체크 없이 수행하거나 별도 정책 적용 가능)
        # 여기서는 단순히 검색만 수행
        all_articles = await self.cse_collector.search_by_keyword(
            keyword_text,
            date_range=date_range,
            max_results=20  # 미리보기는 적게
        )
        
        unique_articles = self.deduplicator.filter_duplicates(all_articles)
        
        analyzed_articles = []
        for article in unique_articles:
            sentiment_result = self.sentiment_analyzer.analyze(
                article.get('title', ''),
                article.get('snippet', '')
            )
            article['sentiment'] = sentiment_result
            analyzed_articles.append(article)
            
        return {
            'articles': analyzed_articles,
            'count': len(analyzed_articles)
        }
