"""Google Custom Search API 수집기"""
import requests
from typing import List, Dict, Optional, Protocol
from datetime import datetime
from urllib.parse import urlparse, urlunparse
from uuid import UUID
import sys
import os

# 공통 설정 모듈 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../shared'))
from config.settings import settings


class CSEQueryLimitExceededError(Exception):
    """Google CSE 일일 쿼리 제한을 초과했을 때 발생하는 예외"""

    def __init__(self, message: str, detail: Optional[Dict] = None):
        super().__init__(message)
        self.detail = detail or {}


class CSEQuotaManager(Protocol):
    """Google CSE 쿼리 제한과 연동하기 위한 프로토콜"""

    async def can_make_query(
        self,
        user_id: UUID,
        keyword_id: Optional[UUID],
        required_queries: int = 1
    ) -> bool:
        ...

    async def get_remaining_queries(
        self,
        user_id: UUID,
        keyword_id: Optional[UUID]
    ) -> Dict[str, int]:
        ...

    async def record_usage(
        self,
        user_id: UUID,
        keyword_id: Optional[UUID],
        queries_used: int = 1
    ) -> None:
        ...


class GoogleCSECollector:
    """Google Custom Search API를 사용한 기사 수집 클래스"""
    
    API_ENDPOINT = "https://www.googleapis.com/customsearch/v1"
    MAX_RESULTS_PER_QUERY = 10  # Google CSE API는 한 번에 최대 10개 결과 반환
    MAX_TOTAL_RESULTS = 100  # 전체 최대 100개 결과 (10페이지)
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self._api_key = None
        self._cx = None
        self._initialized = False
    
    def _ensure_initialized(self):
        """초기화 확인 및 실행 (lazy initialization)"""
        if not self._initialized:
            self._api_key = settings.google_cse_api_key
            self._cx = settings.google_cse_cx
            
            if not self._api_key or not self._cx:
                raise ValueError("GOOGLE_CSE_API_KEY와 GOOGLE_CSE_CX가 설정되어 있어야 합니다.")
            
            self._initialized = True
    
    @property
    def api_key(self):
        """API 키 (lazy initialization)"""
        self._ensure_initialized()
        return self._api_key
    
    @property
    def cx(self):
        """Custom Search Engine ID (lazy initialization)"""
        self._ensure_initialized()
        return self._cx
    
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
    
    def _calculate_date_restrict(self, date_range: Optional[tuple[datetime, datetime]]) -> Optional[str]:
        """날짜 범위를 Google CSE의 dateRestrict 형식으로 변환"""
        if not date_range:
            return None
        
        start_date, end_date = date_range
        now = datetime.now()
        
        if end_date > now:
            end_date = now
        
        if start_date > end_date:
            return None
        
        days_from_now = (now - start_date).days
        
        if days_from_now > 365:
            return "d365"
        
        return f"d{days_from_now}"
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """날짜 문자열 파싱"""
        if not date_str:
            return None
        
        try:
            formats = [
                "%b %d, %Y",  # Jan 1, 2024
                "%B %d, %Y",  # January 1, 2024
                "%Y-%m-%d",   # 2024-01-01
                "%Y/%m/%d",   # 2024/01/01
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str.strip(), fmt)
                except ValueError:
                    continue
            
            return None
        except Exception:
            return None
    
    async def search_by_keyword(
        self,
        keyword: str,
        date_range: Optional[tuple[datetime, datetime]] = None,
        max_results: int = 100,
        user_id: Optional[UUID] = None,
        keyword_id: Optional[UUID] = None,
        quota_manager: Optional[CSEQuotaManager] = None
    ) -> List[Dict]:
        """키워드로 기사 검색"""
        if not keyword:
            return []
        
        articles: List[Dict] = []
        date_restrict = self._calculate_date_restrict(date_range)
        max_results = min(max_results, self.MAX_TOTAL_RESULTS)
        
        start_index = 1
        while len(articles) < max_results:
            try:
                self._ensure_initialized()

                if quota_manager and user_id:
                    can_query = await quota_manager.can_make_query(user_id, keyword_id)
                    if not can_query:
                        detail = await quota_manager.get_remaining_queries(user_id, keyword_id)
                        raise CSEQueryLimitExceededError(
                            "Google CSE 일일 쿼리 제한을 초과했습니다.",
                            detail=detail
                        )
                
                params = {
                    'key': self._api_key,
                    'cx': self._cx,
                    'q': keyword,
                    'num': self.MAX_RESULTS_PER_QUERY,
                    'start': start_index
                }
                
                if date_restrict:
                    params['dateRestrict'] = date_restrict
                
                response = requests.get(
                    self.API_ENDPOINT,
                    params=params,
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                if quota_manager and user_id:
                    await quota_manager.record_usage(user_id, keyword_id, queries_used=1)
                
                data = response.json()
                
                if 'items' not in data or not data['items']:
                    break
                
                for item in data['items']:
                    normalized_url = self.normalize_url(item.get('link', ''))
                    published_at = self._parse_date(item.get('formattedDate'))
                    
                    if date_range and published_at:
                        start_date, end_date = date_range
                        if not (start_date <= published_at <= end_date):
                            continue
                    
                    display_link = item.get('displayLink', '')
                    if isinstance(display_link, dict):
                        source = 'Unknown'
                    elif isinstance(display_link, str):
                        source = display_link or 'Unknown'
                    else:
                        source = str(display_link) if display_link else 'Unknown'
                    
                    article = {
                        'url': normalized_url,
                        'title': item.get('title', ''),
                        'snippet': item.get('snippet', '')[:500] if item.get('snippet') else '',
                        'source': source,
                        'published_at': published_at,
                        'lang': 'ko'
                    }
                    
                    articles.append(article)
                    
                    if len(articles) >= max_results:
                        break
                
                start_index += self.MAX_RESULTS_PER_QUERY
                
                total_results = data.get('queries', {}).get('request', [{}])[0].get('totalResults', 0)
                try:
                    total_results = int(total_results) if total_results else 0
                except (ValueError, TypeError):
                    total_results = 0
                
                if start_index > total_results:
                    break
                
            except CSEQueryLimitExceededError:
                raise
            except requests.exceptions.RequestException as e:
                print(f"Google CSE API 요청 오류: {e}")
                break
            except Exception as e:
                print(f"Google CSE 수집 오류: {e}")
                break
        
        return articles
