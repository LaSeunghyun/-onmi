"""Google Custom Search API 수집기"""
import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from urllib.parse import urlparse, urlunparse
import sys
import os

# 공통 설정 모듈 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../shared'))
from config.settings import settings


class GoogleCSECollector:
    """Google Custom Search API를 사용한 기사 수집 클래스"""
    
    API_ENDPOINT = "https://www.googleapis.com/customsearch/v1"
    MAX_RESULTS_PER_QUERY = 10  # Google CSE API는 한 번에 최대 10개 결과 반환
    MAX_TOTAL_RESULTS = 100  # 전체 최대 100개 결과 (10페이지)
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.api_key = settings.google_cse_api_key
        self.cx = settings.google_cse_cx
        
        if not self.api_key or not self.cx:
            raise ValueError("GOOGLE_CSE_API_KEY와 GOOGLE_CSE_CX가 설정되어 있어야 합니다.")
    
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
        """날짜 범위를 Google CSE의 dateRestrict 형식으로 변환
        
        Args:
            date_range: (시작일, 종료일) 튜플
            
        Returns:
            dateRestrict 문자열 (예: "d7" = 최근 7일) 또는 None
        """
        if not date_range:
            return None
        
        start_date, end_date = date_range
        now = datetime.now()
        
        # 종료일이 현재보다 미래인 경우 현재로 제한
        if end_date > now:
            end_date = now
        
        # 시작일이 종료일보다 미래인 경우 None 반환
        if start_date > end_date:
            return None
        
        # 날짜 차이 계산
        days_diff = (end_date - start_date).days
        
        # Google CSE는 최근 날짜만 지원하므로, 시작일이 현재로부터 며칠 전인지 계산
        days_from_now = (now - start_date).days
        
        # 최대 365일까지만 지원
        if days_from_now > 365:
            return "d365"
        
        # dateRestrict 형식: "dN" (N일 전부터)
        return f"d{days_from_now}"
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """날짜 문자열 파싱
        
        Google CSE API의 formattedDate 형식: "Jan 1, 2024"
        """
        if not date_str:
            return None
        
        try:
            # 여러 날짜 형식 시도
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
    
    def search_by_keyword(
        self,
        keyword: str,
        date_range: Optional[tuple[datetime, datetime]] = None,
        max_results: int = 100
    ) -> List[Dict]:
        """키워드로 기사 검색
        
        Args:
            keyword: 검색할 키워드
            date_range: (시작일, 종료일) 튜플, None이면 필터링 안 함
            max_results: 최대 결과 개수 (기본값: 100)
            
        Returns:
            기사 정보 리스트
        """
        if not keyword:
            return []
        
        articles = []
        date_restrict = self._calculate_date_restrict(date_range)
        max_results = min(max_results, self.MAX_TOTAL_RESULTS)
        
        # 페이지네이션 처리
        start_index = 1
        while len(articles) < max_results:
            try:
                # API 요청 파라미터
                params = {
                    'key': self.api_key,
                    'cx': self.cx,
                    'q': keyword,
                    'num': self.MAX_RESULTS_PER_QUERY,
                    'start': start_index
                }
                
                # 날짜 범위가 있으면 추가
                if date_restrict:
                    params['dateRestrict'] = date_restrict
                
                # API 호출
                response = requests.get(
                    self.API_ENDPOINT,
                    params=params,
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                data = response.json()
                
                # 결과가 없으면 종료
                if 'items' not in data or not data['items']:
                    break
                
                # 기사 정보 추출
                for item in data['items']:
                    # URL 정규화
                    normalized_url = self.normalize_url(item.get('link', ''))
                    
                    # 날짜 파싱
                    published_at = self._parse_date(item.get('formattedDate'))
                    
                    # 날짜 범위 필터링 (API의 dateRestrict가 정확하지 않을 수 있으므로 추가 필터링)
                    if date_range and published_at:
                        start_date, end_date = date_range
                        if not (start_date <= published_at <= end_date):
                            continue
                    
                    # 기사 정보 구성
                    article = {
                        'url': normalized_url,
                        'title': item.get('title', ''),
                        'snippet': item.get('snippet', '')[:500],  # 최대 500자
                        'source': item.get('displayLink', 'Unknown'),
                        'published_at': published_at,
                        'lang': 'ko'  # 기본값, 실제로는 언어 감지 필요
                    }
                    
                    articles.append(article)
                    
                    # 최대 결과 개수 도달 시 종료
                    if len(articles) >= max_results:
                        break
                
                # 다음 페이지로
                start_index += self.MAX_RESULTS_PER_QUERY
                
                # 더 이상 결과가 없으면 종료
                if start_index > data.get('queries', {}).get('request', [{}])[0].get('totalResults', 0):
                    break
                
            except requests.exceptions.RequestException as e:
                print(f"Google CSE API 요청 오류: {e}")
                break
            except Exception as e:
                print(f"Google CSE 수집 오류: {e}")
                break
        
        return articles

