"""크롤링 서비스"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../ingestor/src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../shared'))
from collectors.rss_collector import RSSCollector
from processors.deduplicator import Deduplicator
from sentiment.rule_based import RuleBasedSentimentAnalyzer
from config.settings import settings


class ExternalNewsCollector:
    """외부 뉴스 수집 클래스"""
    
    def __init__(self):
        self.rss_collector = RSSCollector()
        self.deduplicator = Deduplicator()
        self.sentiment_analyzer = RuleBasedSentimentAnalyzer()
    
    async def fetch(
        self,
        keyword_text: str,
        date_range: Optional[tuple[datetime, datetime]] = None
    ) -> Dict:
        """키워드로 뉴스 수집"""
        all_articles = []
        
        # RSS 소스에서 기사 수집
        for rss_url in settings.rss_sources_list:
            articles = self.rss_collector.collect_from_rss(rss_url)
            
            # 날짜 범위 필터링
            if date_range:
                start_date, end_date = date_range
                articles = [
                    article for article in articles
                    if article.get('published_at') and 
                       start_date <= article['published_at'] <= end_date
                ]
            
            # 키워드 매칭 필터링
            matched_articles = [
                article for article in articles
                if keyword_text.lower() in article['title'].lower() or
                   keyword_text.lower() in article.get('snippet', '').lower()
            ]
            all_articles.extend(matched_articles)
        
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

