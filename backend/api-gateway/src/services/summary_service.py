"""요약 생성 서비스"""
from typing import Dict, Any, List, Optional
from uuid import UUID
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../shared'))
from ..repositories import (
    ArticleRepository,
    SummarySessionRepository,
    FeedbackRepository
)
from .token_tracker import TokenTracker


class Summarizer:
    """요약 생성 엔진"""
    
    def __init__(self):
        pass
    
    def generate(
        self,
        articles: List[Dict],
        config: Dict[str, Any]
    ) -> str:
        """기사 목록으로부터 요약 생성"""
        if not articles:
            return "수집된 기사가 없습니다."
        
        # 감성별 기사 분류
        positive_count = sum(1 for a in articles if self._get_sentiment_label(a) == 'positive')
        negative_count = sum(1 for a in articles if self._get_sentiment_label(a) == 'negative')
        neutral_count = len(articles) - positive_count - negative_count
        
        summary_parts = []
        
        # 기본 통계
        summary_parts.append(f"총 {len(articles)}개의 기사가 수집되었습니다.")
        
        if config.get('include_sentiment', True):
            summary_parts.append(f"긍정: {positive_count}개, 부정: {negative_count}개, 중립: {neutral_count}개")
        
        # 주요 기사 제목
        top_count = config.get('top_articles_count', 5)
        top_articles = articles[:top_count]
        if top_articles:
            summary_parts.append("\n주요 기사:")
            for i, article in enumerate(top_articles, 1):
                title = article.get('title', '제목 없음')
                source = article.get('source', '')
                if config.get('include_sources', False) and source:
                    summary_parts.append(f"{i}. [{source}] {title}")
                else:
                    summary_parts.append(f"{i}. {title}")
        
        # 키워드 포함
        if config.get('include_keywords', False):
            # 기사 제목에서 자주 나오는 단어 추출 (간단한 버전)
            pass
        
        summary_text = "\n".join(summary_parts)
        
        # 길이 제한
        max_length = config.get('max_length', 500)
        if len(summary_text) > max_length:
            summary_text = summary_text[:max_length] + "..."
        
        return summary_text
    
    def _get_sentiment_label(self, article: Dict) -> str:
        """기사의 감성 레이블 추출"""
        sentiment = article.get('sentiment', {})
        if isinstance(sentiment, dict):
            return sentiment.get('label', 'neutral')
        return 'neutral'


class SummaryPolicy:
    """피드백 기반 요약 정책 조정"""
    
    @staticmethod
    def tune(feedback_stats: Dict[str, Any]) -> Dict[str, Any]:
        """피드백 통계 기반 요약 정책 조정"""
        avg_rating = feedback_stats.get('avg_rating', 0.0)
        total_count = feedback_stats.get('total_count', 0)
        
        # 피드백이 없는 경우 기본 정책
        if total_count == 0:
            return {
                'detail_level': 'standard',
                'max_length': 500,
                'include_sentiment': True,
                'include_keywords': False,
                'include_sources': False,
                'top_articles_count': 5
            }
        
        if avg_rating >= 4.0:
            # 높은 만족도: 현재 수준 유지
            return {
                'detail_level': 'maintain_current',
                'max_length': 500,
                'include_sentiment': True,
                'include_keywords': False,
                'include_sources': False,
                'top_articles_count': 5
            }
        elif avg_rating >= 3.0:
            # 중간 만족도: 더 많은 맥락 제공
            return {
                'detail_level': 'tweak_for_more_context',
                'max_length': 600,
                'include_sentiment': True,
                'include_keywords': True,
                'include_sources': False,
                'top_articles_count': 7
            }
        else:
            # 낮은 만족도: 상세 정보 증가
            return {
                'detail_level': 'increase_detail',
                'max_length': 800,
                'include_sentiment': True,
                'include_keywords': True,
                'include_sources': True,
                'top_articles_count': 10
            }


class SummaryService:
    """요약 생성 서비스"""
    
    def __init__(self):
        self.summarizer = Summarizer()
        self.policy = SummaryPolicy()
        self.token_tracker = TokenTracker()
    
    def _estimate_tokens(self, text: str) -> int:
        """텍스트 길이를 기반으로 토큰 수 추정 (한글 기준 대략 1자 = 0.5토큰)"""
        # 간단한 추정: 한글/영문 혼합 기준 대략 1자 = 0.5토큰
        # 실제 AI API 사용 시 정확한 토큰 수를 반환받아 사용
        return int(len(text) * 0.5)
    
    async def generate_daily_summary(self, user_id: UUID) -> Dict[str, Any]:
        """일일 요약 생성"""
        # 사용자의 모든 키워드에 대한 최근 기사 조회
        articles = await ArticleRepository.fetch_recent_by_user(user_id, limit=100)
        
        # 피드백 통계 조회
        feedback_stats = await FeedbackRepository.aggregate_by_user(user_id)
        
        # 요약 정책 조정
        config = self.policy.tune(feedback_stats)
        
        # 요약 생성
        summary_text = self.summarizer.generate(articles, config)
        
        # 입력 토큰 추정 (기사 내용)
        input_text = "\n".join([a.get('title', '') + " " + a.get('snippet', '') for a in articles])
        input_tokens = self._estimate_tokens(input_text)
        
        # 출력 토큰 추정 (요약 텍스트)
        output_tokens = self._estimate_tokens(summary_text)
        total_tokens = input_tokens + output_tokens
        
        # 토큰 사용량 기록 (시스템 전체)
        try:
            await self.token_tracker.record_usage(
                tokens_used=total_tokens,
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )
        except Exception as e:
            # 토큰 기록 실패해도 요약 생성은 진행
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"토큰 사용량 기록 실패: {e}")
        
        # 요약 세션 저장
        summary_session = await SummarySessionRepository.create(
            keyword_id=None,
            user_id=user_id,
            summary_text=summary_text,
            summary_type='daily',
            summarization_config=config
        )
        
        return {
            'session_id': str(summary_session.id),
            'summary_text': summary_text,
            'articles_count': len(articles),
            'config': config
        }
    
    async def generate_keyword_summary(
        self,
        keyword_id: UUID,
        user_id: UUID
    ) -> Dict[str, Any]:
        """키워드별 요약 생성"""
        # 키워드별 최근 기사 조회
        articles = await ArticleRepository.fetch_recent_by_keyword(keyword_id, limit=50)
        
        # 피드백 통계 조회
        feedback_stats = await FeedbackRepository.aggregate_by_keyword(keyword_id, user_id)
        
        # 요약 정책 조정
        config = self.policy.tune(feedback_stats)
        
        # 요약 생성
        summary_text = self.summarizer.generate(articles, config)
        
        # 입력 토큰 추정 (기사 내용)
        input_text = "\n".join([a.get('title', '') + " " + a.get('snippet', '') for a in articles])
        input_tokens = self._estimate_tokens(input_text)
        
        # 출력 토큰 추정 (요약 텍스트)
        output_tokens = self._estimate_tokens(summary_text)
        total_tokens = input_tokens + output_tokens
        
        # 토큰 사용량 기록 (시스템 전체)
        try:
            await self.token_tracker.record_usage(
                tokens_used=total_tokens,
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )
        except Exception as e:
            # 토큰 기록 실패해도 요약 생성은 진행
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"토큰 사용량 기록 실패: {e}")
        
        # 요약 세션 저장
        summary_session = await SummarySessionRepository.create(
            keyword_id=keyword_id,
            user_id=user_id,
            summary_text=summary_text,
            summary_type='keyword',
            summarization_config=config
        )
        
        return {
            'session_id': str(summary_session.id),
            'summary_text': summary_text,
            'articles_count': len(articles),
            'config': config
        }

