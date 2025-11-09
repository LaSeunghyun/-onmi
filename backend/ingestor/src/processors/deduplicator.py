"""중복 제거 프로세서"""
from simhash import Simhash
from typing import List, Dict
import hashlib


class Deduplicator:
    """기사 중복 제거 클래스"""
    
    def __init__(self):
        self.seen_urls = set()
        self.seen_hashes = set()
    
    def compute_simhash(self, text: str) -> int:
        """텍스트의 SimHash 계산"""
        return Simhash(text).value
    
    def compute_url_hash(self, url: str) -> str:
        """URL 해시 계산"""
        return hashlib.md5(url.encode()).hexdigest()
    
    def is_duplicate(self, article: Dict) -> bool:
        """기사가 중복인지 확인"""
        url = article.get('url', '')
        title = article.get('title', '')
        
        # URL 기반 중복 확인
        url_hash = self.compute_url_hash(url)
        if url_hash in self.seen_urls:
            return True
        
        # 제목 기반 SimHash 중복 확인
        title_hash = self.compute_simhash(title)
        if title_hash in self.seen_hashes:
            return True
        
        # 새로운 기사로 기록
        self.seen_urls.add(url_hash)
        self.seen_hashes.add(title_hash)
        
        return False
    
    def filter_duplicates(self, articles: List[Dict]) -> List[Dict]:
        """중복 기사 필터링"""
        unique_articles = []
        for article in articles:
            if not self.is_duplicate(article):
                unique_articles.append(article)
        return unique_articles



