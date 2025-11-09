"""RSS 피드 수집기"""
import feedparser
import requests
from typing import List, Dict, Optional
from datetime import datetime
import hashlib
from urllib.parse import urlparse, urlunparse


class RSSCollector:
    """RSS 피드 수집 클래스"""
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
    
    def normalize_url(self, url: str) -> str:
        """URL 정규화"""
        parsed = urlparse(url)
        # 쿼리 파라미터 제거, 프래그먼트 제거
        normalized = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            '',
            '',
            ''
        ))
        return normalized.rstrip('/')
    
    def collect_from_rss(self, rss_url: str) -> List[Dict]:
        """RSS 피드에서 기사 수집"""
        try:
            feed = feedparser.parse(rss_url)
            articles = []
            
            for entry in feed.entries:
                # 필수 필드 확인
                if not entry.get('title') or not entry.get('link'):
                    continue
                
                # URL 정규화
                normalized_url = self.normalize_url(entry.link)
                
                # 기사 정보 추출
                article = {
                    'url': normalized_url,
                    'title': entry.title,
                    'snippet': entry.get('summary', '')[:500],  # 최대 500자
                    'source': feed.feed.get('title', 'Unknown'),
                    'published_at': self._parse_date(entry.get('published')),
                    'lang': 'ko'  # 기본값, 실제로는 언어 감지 필요
                }
                
                articles.append(article)
            
            return articles
        
        except Exception as e:
            print(f"RSS 수집 오류 ({rss_url}): {e}")
            return []
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """날짜 문자열 파싱"""
        if not date_str:
            return None
        
        try:
            # feedparser의 날짜 파싱 활용
            import time
            if hasattr(date_str, 'parsed'):
                return datetime.fromtimestamp(time.mktime(date_str.parsed))
            return None
        except:
            return None



