"""크롤링 서비스"""
from typing import Dict, Optional
from datetime import datetime
from uuid import UUID
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../ingestor/src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../nlp-service/src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../shared'))
from collectors.google_cse_collector import GoogleCSECollector  # noqa: E402
from processors.deduplicator import Deduplicator  # noqa: E402
from sentiment.rule_based import RuleBasedSentimentAnalyzer  # noqa: E402
from services.cse_query_limit_service import CSEQueryLimitService  # noqa: E402


class ExternalNewsCollector:
    """외부 뉴스 수집 클래스"""
    
    def __init__(self):
        self.cse_collector = GoogleCSECollector()
        self.deduplicator = Deduplicator()
        self.sentiment_analyzer = RuleBasedSentimentAnalyzer()
        self.quota_service = CSEQueryLimitService()
    
    async def fetch(
        self,
        keyword_text: str,
        user_id: Optional[UUID] = None,
        keyword_id: Optional[UUID] = None,
        date_range: Optional[tuple[datetime, datetime]] = None
    ) -> Dict:
        """키워드로 뉴스 수집"""
        # Google CSE로 키워드 검색
        all_articles = await self.cse_collector.search_by_keyword(
            keyword_text,
            date_range=date_range,
            max_results=100,
            user_id=user_id,
            keyword_id=keyword_id,
            quota_manager=self.quota_service if user_id else None
        )
        
        # 중복 제거
        unique_articles = self.deduplicator.filter_duplicates(all_articles)
        
        # 감성 분석 수행
        analyzed_articles = []
        for article in unique_articles:
            sentiment_result = self.sentiment_analyzer.analyze(
                article['title'],
                article.get('snippet', '')
            )
            article['sentiment'] = sentiment_result
            analyzed_articles.append(article)
        
        return {
            'articles': analyzed_articles,
            'count': len(analyzed_articles)
        }

