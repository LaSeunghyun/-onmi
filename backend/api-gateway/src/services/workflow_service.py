"""워크플로우 서비스 - 수집 및 요약 오케스트레이션"""
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime, timedelta, time
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../shared'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from repositories.keyword_repository import KeywordRepository
from repositories.article_repository import ArticleRepository
from repositories.keyword_article_mapper import KeywordArticleMapper
from repositories.fetch_history_repository import FetchHistoryRepository
from repositories.summary_session_repository import SummarySessionRepository
from repositories.feedback_repository import FeedbackRepository
from repositories.preference_repository import PreferenceRepository
from models.fetch_history import FetchHistory, DateRange
from services.crawl_service import ExternalNewsCollector

# timezone_utils는 shared/utils에 있으므로 직접 import
shared_utils_path = os.path.join(os.path.dirname(__file__), '../../../shared/utils')
if shared_utils_path not in sys.path:
    sys.path.insert(0, shared_utils_path)
from timezone_utils import now_kst


class WorkflowService:
    """워크플로우 오케스트레이션 서비스"""
    
    def __init__(self):
        self.collector = ExternalNewsCollector()
    
    def subtract_ranges(
        self,
        candidate_range: DateRange,
        covered_ranges: List[DateRange]
    ) -> List[DateRange]:
        """날짜 범위에서 이미 수집된 범위를 제외"""
        remaining = [candidate_range]
        
        for covered in covered_ranges:
            new_remaining = []
            for block in remaining:
                if not block.overlaps(covered):
                    new_remaining.append(block)
                else:
                    # 겹치는 부분 제외
                    excluded = block.exclude(covered)
                    new_remaining.extend(excluded)
            remaining = new_remaining
        
        # 인접한 범위 병합
        if remaining:
            merged = [remaining[0]]
            for current in remaining[1:]:
                last = merged[-1]
                if last.end >= current.start:
                    merged[-1] = DateRange(last.start, max(last.end, current.end))
                else:
                    merged.append(current)
            return merged
        
        return []
    
    async def collect_news(
        self,
        keyword_id: UUID,
        user_id: UUID,
        keyword_text: str,
        request_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """기간 계산 및 수집 오케스트레이션"""
        # 수집 이력 조회
        history_list = await FetchHistoryRepository.list_by_keyword(
            keyword_id, order_by="actual_start"
        )
        
        # 대상 날짜 범위 계산
        target_ranges: List[DateRange] = []
        
        if not history_list:
            # 첫 조회: 직전 하루만 수집 (한국 시간 기준)
            now_kst_dt = now_kst()
            yesterday_start = now_kst_dt.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
            yesterday_end = now_kst_dt.replace(hour=0, minute=0, second=0, microsecond=0)
            target_ranges = [DateRange(yesterday_start, yesterday_end)]
        elif request_context.get('range'):
            # 명시적 범위 요청
            requested_start = request_context['range']['start']
            requested_end = request_context['range']['end']
            candidate_range = DateRange(requested_start, requested_end)
            
            # 이미 수집된 범위 제외
            covered_ranges = [h.actual_range for h in history_list]
            target_ranges = self.subtract_ranges(candidate_range, covered_ranges)
        else:
            # 마지막 수집 이후부터 현재까지
            last_history = history_list[-1]
            last_end = last_history.actual_end
            
            # 마지막 수집일의 다음 날 시작 (한국 시간 기준)
            next_start = (last_end + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            now_kst_dt = now_kst()
            now_end = now_kst_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            if next_start <= now_end:
                target_ranges = [DateRange(next_start, now_end)]
        
        # 빈 범위인 경우 캐시된 결과 반환
        if not target_ranges or all(r.is_empty() for r in target_ranges):
            # 최신 수집 결과 반환 (실제로는 캐시 또는 최신 기사 조회)
            articles = await ArticleRepository.fetch_recent_by_keyword(keyword_id, limit=20)
            return {
                'articles': articles,
                'count': len(articles),
                'ranges_collected': [],
                'from_cache': True
            }
        
        # 각 범위별로 수집 수행
        all_articles = []
        collected_ranges = []
        
        for target_range in target_ranges:
            if target_range.is_empty():
                continue
            
            # 뉴스 수집
            crawl_result = await self.collector.fetch(
                keyword_text=keyword_text,
                user_id=user_id,
                keyword_id=keyword_id,
                date_range=(target_range.start, target_range.end)
            )
            
            if crawl_result['articles']:
                # 기사 저장
                article_ids = await ArticleRepository.upsert_batch(crawl_result['articles'])
                
                # 키워드-기사 매핑
                await KeywordArticleMapper.link(keyword_id, article_ids)
                
                # 감성 분석 결과 저장 (이미 crawl_result에 포함됨)
                # TODO: 감성 분석 결과를 sentiments 테이블에 저장하는 로직 추가 필요
                
                all_articles.extend(crawl_result['articles'])
                collected_ranges.append({
                    'start': target_range.start.isoformat(),
                    'end': target_range.end.isoformat()
                })
        
        # 수집 이력 저장
        if collected_ranges:
            for range_info in collected_ranges:
                await FetchHistoryRepository.insert(
                    keyword_id=keyword_id,
                    user_id=user_id,
                    actual_start=datetime.fromisoformat(range_info['start']),
                    actual_end=datetime.fromisoformat(range_info['end']),
                    trigger_type=request_context.get('trigger', 'manual'),
                    articles_count=len([a for a in all_articles 
                                       if datetime.fromisoformat(range_info['start']) <= a.get('published_at', datetime.min) <= datetime.fromisoformat(range_info['end'])]),
                    requested_start=request_context.get('range', {}).get('start') if request_context.get('range') else None,
                    requested_end=request_context.get('range', {}).get('end') if request_context.get('range') else None
                )
            
            # 키워드의 last_crawled_at 업데이트 (한국 시간 기준)
            await KeywordRepository.update_last_crawled_at(keyword_id, now_kst())
        
        return {
            'articles': all_articles,
            'count': len(all_articles),
            'ranges_collected': collected_ranges,
            'from_cache': False
        }
    
    async def generate_summary(
        self,
        keyword_id: Optional[UUID],
        user_id: UUID,
        summary_type: str
    ) -> Dict[str, Any]:
        """요약 생성 및 피드백 통계 반영"""
        # 피드백 통계 조회
        if keyword_id:
            feedback_stats = await FeedbackRepository.aggregate_by_keyword(keyword_id, user_id)
        else:
            feedback_stats = await FeedbackRepository.aggregate_by_user(user_id)
        
        # 요약 정책 조정 (피드백 기반)
        summarization_config = self._tune_summary_policy(feedback_stats)
        
        # 기사 조회
        if keyword_id:
            articles = await ArticleRepository.fetch_recent_by_keyword(keyword_id, limit=50)
        else:
            articles = await ArticleRepository.fetch_recent_by_user(user_id, limit=100)
        
        # 요약 생성
        summary_text = self._generate_summary_text(articles, summarization_config)
        
        # 요약 세션 저장
        summary_session = await SummarySessionRepository.create(
            keyword_id=keyword_id,
            user_id=user_id,
            summary_text=summary_text,
            summary_type=summary_type,
            summarization_config=summarization_config
        )
        
        return {
            'session_id': str(summary_session['id']),
            'summary_text': summary_text,
            'articles_count': len(articles),
            'config': summarization_config
        }
    
    def _tune_summary_policy(self, feedback_stats: Dict) -> Dict[str, Any]:
        """피드백 통계 기반 요약 정책 조정"""
        avg_rating = feedback_stats.get('avg_rating', 0.0)
        
        if avg_rating >= 4.0:
            # 높은 만족도: 현재 수준 유지
            return {
                'detail_level': 'maintain_current',
                'max_length': 500,
                'include_sentiment': True
            }
        elif avg_rating >= 3.0:
            # 중간 만족도: 더 많은 맥락 제공
            return {
                'detail_level': 'tweak_for_more_context',
                'max_length': 600,
                'include_sentiment': True,
                'include_keywords': True
            }
        else:
            # 낮은 만족도: 상세 정보 증가
            return {
                'detail_level': 'increase_detail',
                'max_length': 800,
                'include_sentiment': True,
                'include_keywords': True,
                'include_sources': True
            }
    
    def _generate_summary_text(self, articles: List[Dict], config: Dict[str, Any]) -> str:
        """요약 텍스트 생성"""
        if not articles:
            return "수집된 기사가 없습니다."
        
        # 감성별 기사 분류
        positive_count = sum(1 for a in articles if a.get('sentiment', {}).get('label') == 'positive')
        negative_count = sum(1 for a in articles if a.get('sentiment', {}).get('label') == 'negative')
        neutral_count = len(articles) - positive_count - negative_count
        
        summary_parts = []
        
        # 기본 통계
        summary_parts.append(f"총 {len(articles)}개의 기사가 수집되었습니다.")
        
        if config.get('include_sentiment'):
            summary_parts.append(f"긍정: {positive_count}개, 부정: {negative_count}개, 중립: {neutral_count}개")
        
        # 주요 기사 제목 (최대 5개)
        top_articles = articles[:5]
        if top_articles:
            summary_parts.append("\n주요 기사:")
            for i, article in enumerate(top_articles, 1):
                title = article.get('title', '제목 없음')
                summary_parts.append(f"{i}. {title}")
        
        summary_text = "\n".join(summary_parts)
        
        # 길이 제한
        max_length = config.get('max_length', 500)
        if len(summary_text) > max_length:
            summary_text = summary_text[:max_length] + "..."
        
        return summary_text
    
    async def record_feedback(
        self,
        summary_session_id: UUID,
        user_id: UUID,
        rating: int,
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """피드백 기록 및 선호도 업데이트"""
        # 세션 확인
        session = await SummarySessionRepository.get_by_id(summary_session_id, user_id)
        if not session:
            raise ValueError("요약 세션을 찾을 수 없습니다")
        
        # 피드백 저장
        feedback_id = await FeedbackRepository.insert(
            summary_session_id, user_id, rating, comment
        )
        
        # 세션에 피드백 수신 표시
        await SummarySessionRepository.mark_feedback_received(summary_session_id, rating)
        
        # 선호도 업데이트
        detail_level = self._derive_detail_level(rating)
        await PreferenceRepository.upsert(
            user_id=user_id,
            keyword_id=session.keyword_id,
            preferred_detail_level=detail_level
        )
        
        return {
            'feedback_id': str(feedback_id),
            'rating': rating,
            'detail_level': detail_level
        }
    
    def _derive_detail_level(self, rating: int) -> str:
        """평점 기반 상세 수준 결정"""
        if rating >= 4:
            return 'maintain_current_detail'
        elif rating == 3:
            return 'tweak_for_more_context'
        else:
            return 'increase_detail'
    
    async def handle_manual_fetch(
        self,
        keyword_id: UUID,
        user_id: UUID,
        requested_range: Optional[Dict[str, datetime]] = None
    ) -> Dict[str, Any]:
        """수동 수집 처리"""
        # 키워드 정보 조회
        keyword = await KeywordRepository.get_by_id(keyword_id, user_id)
        if not keyword:
            raise ValueError("키워드를 찾을 수 없습니다")
        
        keyword_text = keyword['text']
        
        # 요청 컨텍스트 구성
        request_context = {
            'trigger': 'manual',
            'range': requested_range
        }
        
        # 뉴스 수집
        result = await self.collect_news(
            keyword_id, user_id, keyword_text, request_context
        )
        
        # 요약 생성
        summary_result = await self.generate_summary(
            keyword_id, user_id, 'keyword'
        )
        
        return {
            'collection': result,
            'summary': summary_result
        }

