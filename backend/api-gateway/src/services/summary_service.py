"""요약 생성 서비스"""
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID
import sys
import os
import asyncio
import logging

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../shared'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from repositories.article_repository import ArticleRepository
from repositories.summary_session_repository import SummarySessionRepository
from repositories.feedback_repository import FeedbackRepository
from repositories.keyword_repository import KeywordRepository
from services.token_tracker import TokenTracker
from config.settings import settings

# Gemini API 라이브러리 import (선택적)
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

logger = logging.getLogger(__name__)


class Summarizer:
    """요약 생성 엔진"""
    
    def __init__(self):
        self._gemini_available = GEMINI_AVAILABLE and bool(settings.gemini_api_key)
        self._gemini_model = None
        self._gemini_initialized = False
    
    def _ensure_gemini_initialized(self):
        """Gemini API 초기화 (lazy initialization)"""
        if self._gemini_initialized:
            return
        
        if not self._gemini_available:
            return
        
        try:
            gemini_api_key = settings.gemini_api_key
            gemini_model_raw = settings.gemini_model or 'models/gemini-2.5-flash'
            
            # 모델 이름 정규화
            gemini_model = gemini_model_raw.strip()
            if not gemini_model.startswith('models/'):
                gemini_model = f'models/{gemini_model}'
            
            # 기본값이 없거나 잘못된 경우 models/gemini-2.5-flash 사용
            if not gemini_model or gemini_model == 'models/':
                gemini_model = 'models/gemini-2.5-flash'
            
            genai.configure(api_key=gemini_api_key)
            self._gemini_model = genai.GenerativeModel(gemini_model)
            self._gemini_initialized = True
            logger.info(f"Gemini API 초기화 완료: {gemini_model}")
        except Exception as e:
            logger.error(f"Gemini API 초기화 실패: {e}")
            self._gemini_available = False
    
    async def generate(
        self,
        articles: List[Dict],
        config: Dict[str, Any],
        keyword_text: Optional[str] = None
    ) -> Tuple[str, Optional[Dict[str, int]]]:
        """기사 목록으로부터 요약 생성
        
        Returns:
            Tuple[str, Optional[Dict[str, int]]]: (요약 텍스트, 토큰 사용량 정보)
            토큰 사용량 정보는 {'input_tokens': int, 'output_tokens': int, 'total_tokens': int} 형식
        """
        if not articles:
            return "수집된 기사가 없습니다.", None
        
        # Gemini API 필수 사용
        if not self._gemini_available:
            raise ValueError("Gemini API를 사용할 수 없습니다. GEMINI_API_KEY가 설정되어 있는지 확인해주세요.")
        
        try:
            self._ensure_gemini_initialized()
            if not self._gemini_model:
                raise ValueError("Gemini 모델을 초기화할 수 없습니다.")
            return await self._generate_with_gemini(articles, config, keyword_text)
        except Exception as e:
            logger.error(f"Gemini API 요약 생성 실패: {e}")
            raise ValueError(f"요약을 생성할 수 없습니다: {str(e)}")
    
    async def _generate_with_gemini(
        self,
        articles: List[Dict],
        config: Dict[str, Any],
        keyword_text: Optional[str]
    ) -> Tuple[str, Dict[str, int]]:
        """Gemini API를 사용한 요약 생성"""
        # 키워드 텍스트 결정
        if not keyword_text:
            keyword_text = "일일 요약"
        
        # 기사 내용을 텍스트로 구성
        articles_text = []
        for i, article in enumerate(articles, 1):
            title = article.get('title', '제목 없음')
            snippet = article.get('snippet', '') or ''
            source = article.get('source', '') or ''
            
            article_text = f"기사 {i}:\n"
            article_text += f"제목: {title}\n"
            if snippet:
                article_text += f"내용: {snippet}\n"
            if source:
                article_text += f"출처: {source}\n"
            articles_text.append(article_text)
        
        all_articles_text = "\n\n".join(articles_text)
        
        # 프롬프트 작성
        max_length = config.get('max_length', 500)
        prompt = f"""안녕하세요! '{keyword_text}' 키워드와 관련된 {len(articles)}개의 뉴스 기사들을 읽어보았습니다. 
이 기사들을 바탕으로, '{keyword_text}'와 관련된 이슈가 무엇인지 한국어를 기준으로 친근하고 따뜻한 톤으로 설명해주세요.

중요한 원칙:
- 제공된 기사 내용에 대해서만 요약해주세요. 기사에 없는 정보나 학습 데이터의 일반적인 지식을 추가하지 마세요.
- 기사에서 명시적으로 언급된 사실과 내용만을 바탕으로 요약을 작성해주세요.
- 추측이나 일반적인 상식은 포함하지 말고, 오직 제공된 기사 내용만을 기반으로 작성해주세요.

요약 작성 가이드:
1. 마치 친한 친구에게 설명하듯이 따뜻하고 친근한 톤으로 작성해주세요.
2. '{keyword_text}' 키워드와 관련된 주요 이슈가 무엇인지 명확하게 설명해주세요.
3. 제공된 기사들에서 읽은 핵심 내용과 중요한 포인트들을 자연스럽게 전달해주세요.
4. 기사들 간의 공통점이나 연관성을 찾아서 통합적으로 설명해주세요.
5. 독자가 쉽게 이해할 수 있도록 구체적이고 명확하게 작성해주세요.
6. 반드시 한국어로 작성해주세요.
7. 적절한 길이로 작성해주세요 ({max_length}자 정도).
8. 독자가 생각해볼만한 포인트를 작성해주세요.
9. 각 기사의 감성(긍정/부정/중립)을 분석하여 요약에 포함해주세요.

기사 목록:
{all_articles_text}

위 기사들을 읽고, '{keyword_text}'와 관련된 이슈를 따뜻하고 친근한 톤으로 설명해주세요. 
반드시 제공된 기사 내용에 대해서만 요약하고, 기사에 없는 정보는 포함하지 마세요.
각 기사의 감성도 분석하여 요약에 포함해주세요:"""
        
        # GenerationConfig 설정 (temperature 0.5)
        generation_config = genai.types.GenerationConfig(
            temperature=0.5
        )
        
        # API 호출 (타임아웃 120초)
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self._gemini_model.generate_content,
                    prompt,
                    generation_config=generation_config
                ),
                timeout=120.0
            )
            
            if response and response.text:
                summary = response.text.strip()
                
                # 토큰 사용량 추출
                token_usage = None
                if hasattr(response, 'usage_metadata') and response.usage_metadata:
                    usage = response.usage_metadata
                    token_usage = {
                        'input_tokens': getattr(usage, 'prompt_token_count', 0) or 0,
                        'output_tokens': getattr(usage, 'candidates_token_count', 0) or 0,
                        'total_tokens': getattr(usage, 'total_token_count', 0) or 0
                    }
                
                return summary, token_usage
            else:
                raise ValueError("Gemini API가 응답을 반환하지 않았습니다.")
        except asyncio.TimeoutError:
            raise TimeoutError("Gemini API 호출이 120초 내에 완료되지 않았습니다.")


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
        
        # 키워드 텍스트 구성 (일일 요약의 경우 "일일 요약" 사용)
        keyword_text = "일일 요약"
        
        # 요약 생성 (async)
        summary_text, token_usage = await self.summarizer.generate(articles, config, keyword_text)
        
        # 토큰 사용량 처리 (Gemini API에서 실제 토큰 사용량 추출)
        if token_usage:
            input_tokens = token_usage.get('input_tokens', 0)
            output_tokens = token_usage.get('output_tokens', 0)
            total_tokens = token_usage.get('total_tokens', 0)
        else:
            # 토큰 사용량 정보가 없는 경우 추정
            input_text = "\n".join([a.get('title', '') + " " + a.get('snippet', '') for a in articles])
            input_tokens = self._estimate_tokens(input_text)
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
            'session_id': str(summary_session['id']),
            'summary_text': summary_text,
            'articles_count': len(articles),
            'config': config,
            'created_at': summary_session['created_at'].isoformat() if summary_session.get('created_at') else None
        }
    
    async def generate_keyword_summary(
        self,
        keyword_id: UUID,
        user_id: UUID
    ) -> Dict[str, Any]:
        """키워드별 요약 생성"""
        # 키워드 정보 조회
        keyword = await KeywordRepository.get_by_id(keyword_id, user_id)
        if not keyword:
            raise ValueError(f"키워드를 찾을 수 없습니다: {keyword_id}")
        
        keyword_text = keyword.get('text', '키워드')
        
        # 키워드별 최근 기사 조회
        articles = await ArticleRepository.fetch_recent_by_keyword(keyword_id, limit=50)
        
        # 피드백 통계 조회 (테이블이 없거나 오류가 발생하면 빈 통계 사용)
        try:
            feedback_stats = await FeedbackRepository.aggregate_by_keyword(keyword_id, user_id)
        except Exception as e:
            logger.warning(f"피드백 통계 조회 실패, 기본값 사용: {e}")
            feedback_stats = {}
        
        # 요약 정책 조정
        config = self.policy.tune(feedback_stats)
        
        # 요약 생성 (async)
        summary_text, token_usage = await self.summarizer.generate(articles, config, keyword_text)
        
        # 토큰 사용량 처리 (Gemini API에서 실제 토큰 사용량 추출)
        if token_usage:
            input_tokens = token_usage.get('input_tokens', 0)
            output_tokens = token_usage.get('output_tokens', 0)
            total_tokens = token_usage.get('total_tokens', 0)
        else:
            # 토큰 사용량 정보가 없는 경우 추정
            input_text = "\n".join([a.get('title', '') + " " + a.get('snippet', '') for a in articles])
            input_tokens = self._estimate_tokens(input_text)
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
            logger.warning(f"토큰 사용량 기록 실패: {e}")
        
        # 요약 세션 저장 (테이블이 없거나 오류가 발생하면 세션 ID 없이 반환)
        try:
            summary_session = await SummarySessionRepository.create(
                keyword_id=keyword_id,
                user_id=user_id,
                summary_text=summary_text,
                summary_type='keyword',
                summarization_config=config
            )
            session_id = str(summary_session['id'])
        except Exception as e:
            # 요약 세션 저장 실패해도 요약 텍스트는 반환
            logger.warning(f"요약 세션 저장 실패, 세션 ID 없이 반환: {e}")
            session_id = None
        
        return {
            'session_id': session_id,
            'summary_text': summary_text,
            'articles_count': len(articles),
            'config': config
        }

