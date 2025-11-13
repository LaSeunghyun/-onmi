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
from utils.performance import track_async_performance

# Gemini API 라이브러리 import (선택적)
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

logger = logging.getLogger(__name__)


def _filter_articles_with_url(articles: List[Dict]) -> List[Dict]:
    """URL이 존재하고 공백이 아닌 기사만 필터링하여 반환합니다."""
    return [
        article
        for article in articles
        if isinstance(article.get('url'), str) and article.get('url').strip()
    ]


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
        keyword_text: Optional[str] = None,
        keyword_summaries: Optional[List[Dict[str, Any]]] = None,
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
            return await self._generate_with_gemini(
                articles,
                config,
                keyword_text,
                keyword_summaries=keyword_summaries,
            )
        except Exception as e:
            logger.error(f"Gemini API 요약 생성 실패: {e}")
            raise ValueError(f"요약을 생성할 수 없습니다: {str(e)}")
    
    async def _generate_with_gemini(
        self,
        articles: List[Dict],
        config: Dict[str, Any],
        keyword_text: Optional[str],
        keyword_summaries: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[str, Optional[Dict[str, int]]]:
        """Gemini API를 사용한 요약 생성"""
        # 키워드 텍스트 결정
        if not keyword_text:
            keyword_text = "일일 요약"
        keyword_summaries = keyword_summaries or []
        
        articles_with_url = _filter_articles_with_url(articles)

        if not articles_with_url:
            return "유효한 URL을 가진 기사가 없습니다.", None
        
        # 기사 내용을 텍스트로 구성
        articles_text = []
        for i, article in enumerate(articles_with_url, 1):
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
        
        # 참고용 키워드 요약 구성
        reference_section = ""
        if keyword_summaries:
            reference_lines: List[str] = []
            for index, summary in enumerate(keyword_summaries, start=1):
                label = summary.get("keyword_text") or f"키워드 {index}"
                articles_count = summary.get("articles_count")
                summary_body = (summary.get("summary_text") or "").strip()
                entry_lines = [
                    f"{index}. {label}"
                    + (f" (기사 {articles_count}건)" if articles_count is not None else "")
                ]
                if summary_body:
                    entry_lines.append(f"   요약: {summary_body}")
                reference_lines.append("\n".join(entry_lines))
            reference_section = (
                "아래는 각각의 키워드에 대해 이미 생성된 요약입니다. "
                "전체 관점에서 통합 요약을 작성할 때 참고하되, 그대로 반복하지 말고 교차 분석된 통찰을 도출하세요.\n"
                + "\n".join(reference_lines)
            )

        # 프롬프트 작성
        max_length = config.get('max_length', 500)
        overview_heading = "전체 요약" if keyword_text == "일일 요약" else f"{keyword_text} 핵심 요약"
        prompt = f"""'{keyword_text}' 키워드와 관련된 {len(articles_with_url)}개의 뉴스 기사들을 바탕으로, '{keyword_text}'와 관련된 이슈를 요약해주세요.

중요한 원칙:
- 제공된 기사 내용에 대해서만 요약해주세요. 기사에 없는 정보나 학습 데이터의 일반적인 지식을 추가하지 마세요.
- 기사에서 명시적으로 언급된 사실과 내용만을 바탕으로 요약을 작성해주세요.
- 추측이나 일반적인 상식은 포함하지 말고, 오직 제공된 기사 내용만을 기반으로 작성해주세요.
- 반드시 한국어로 작성해주세요.

출력 형식 규칙:
1. 인삿말 없이 바로 제목부터 작성합니다.
2. 가장 먼저 '**{overview_heading}**' 제목을 작성한 뒤, 2개 이상 bullet('- ')으로 전체 요약을 제공합니다.
3. 이후 주요 이슈마다 '**[주요 주제명]**' 형태의 제목을 작성하고, 각 제목 아래에 최소 2개의 bullet('- ')을 작성합니다.
4. bullet 하나당 한 문장으로 작성하고, 필요할 때 기사 번호(예: 기사 1)와 감성(긍정/부정/중립)을 괄호로 명시합니다.
5. 제목과 본문 사이, 섹션 사이에는 빈 줄을 정확히 한 줄씩 넣습니다.
6. 모든 제목은 반드시 **로 감싸 굵게 표기합니다.
7. 전체 글 길이는 약 {max_length}자 이내로 유지합니다.

기사 목록:
{all_articles_text}

참고 자료:
{reference_section if reference_section else "현재 참고할 키워드별 요약은 제공되지 않습니다."}

위 기사들을 읽고, 위 형식을 지키며 '{keyword_text}'와 관련된 이슈를 요약해주세요. 
기사에 없는 정보는 포함하지 말고, 제공된 기사 내용만 사용하세요."""
        
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

    async def _ensure_keyword_summary(
        self,
        keyword_id: UUID,
        keyword_text: str,
        user_id: UUID,
        include_archived: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """키워드별 요약을 확보하고 요약 메타데이터를 반환"""
        latest_summary: Optional[Dict[str, Any]] = None
        try:
            async with track_async_performance(
                "SummarySessionRepository.get_latest_by_keyword",
                logger,
                metadata={
                    "keyword_id": str(keyword_id),
                    "user_id": str(user_id),
                },
            ):
                latest_summary = await SummarySessionRepository.get_latest_by_keyword(
                    keyword_id, user_id
                )
        except Exception as exc:
            logger.warning(
                "키워드 최신 요약 조회 실패: %s (keyword_id=%s, user_id=%s)",
                exc,
                keyword_id,
                user_id,
            )
            latest_summary = None

        summary_text = (latest_summary or {}).get("summary_text")
        if latest_summary and summary_text:
            created_at = latest_summary.get("created_at")
            async with track_async_performance(
                "ArticleRepository.count_recent_by_keyword",
                logger,
                metadata={
                    "keyword_id": str(keyword_id),
                    "include_archived": include_archived,
                },
            ):
                articles_count = await ArticleRepository.count_recent_by_keyword(
                    keyword_id, include_archived=include_archived
                )
            return {
                "keyword_id": str(keyword_id),
                "keyword_text": keyword_text,
                "summary_text": summary_text,
                "articles_count": articles_count,
                "created_at": created_at.isoformat()
                if hasattr(created_at, "isoformat")
                else created_at,
            }

        try:
            logger.info(
                "키워드 요약 생성 시도 (keyword_id=%s, user_id=%s)",
                keyword_id,
                user_id,
            )
            result = await self.generate_keyword_summary(
                keyword_id, user_id, include_archived=include_archived
            )
            return {
                "keyword_id": str(keyword_id),
                "keyword_text": keyword_text,
                "summary_text": result.get("summary_text", ""),
                "articles_count": result.get("articles_count", 0),
                "created_at": result.get("created_at"),
            }
        except Exception as exc:
            logger.error(
                "키워드 요약 생성 실패: %s (keyword_id=%s, user_id=%s)",
                exc,
                keyword_id,
                user_id,
            )
            return None

    async def generate_daily_summary(self, user_id: UUID, include_archived: bool = False) -> Dict[str, Any]:
        """일일 요약 생성
        
        Args:
            user_id (UUID): 사용자 ID
            include_archived (bool): 소프트 삭제된 키워드 포함 여부
        """
        async def _fetch_articles():
            async with track_async_performance(
                "ArticleRepository.fetch_recent_by_user",
                logger,
                metadata={
                    "user_id": str(user_id),
                    "limit": 100,
                    "include_archived": include_archived,
                },
            ):
                return await ArticleRepository.fetch_recent_by_user(
                    user_id, limit=100, include_archived=include_archived
                )

        async def _fetch_feedback():
            async with track_async_performance(
                "FeedbackRepository.aggregate_by_user",
                logger,
                metadata={"user_id": str(user_id)},
            ):
                return await FeedbackRepository.aggregate_by_user(user_id)

        async def _fetch_keywords():
            async with track_async_performance(
                "KeywordRepository.list_active_by_user",
                logger,
                metadata={"user_id": str(user_id)},
            ):
                return await KeywordRepository.list_active_by_user(user_id)

        articles, feedback_stats, keywords = await asyncio.gather(
            _fetch_articles(),
            _fetch_feedback(),
            _fetch_keywords(),
        )
        
        valid_articles = _filter_articles_with_url(articles)

        keyword_summaries: List[Dict[str, Any]] = []
        for keyword in keywords:
            keyword_id = keyword.get("id")
            keyword_text = keyword.get("text")
            if not keyword_id or not keyword_text:
                continue
            summary_meta = await self._ensure_keyword_summary(
                keyword_id=keyword_id,
                keyword_text=keyword_text,
                user_id=user_id,
                include_archived=include_archived,
            )
            if summary_meta:
                keyword_summaries.append(summary_meta)

        # 요약 정책 조정
        config = self.policy.tune(feedback_stats)
        
        # 키워드 텍스트 구성 (일일 요약의 경우 "일일 요약" 사용)
        keyword_text = "일일 요약"
        
        # 요약 생성 (async)
        async with track_async_performance(
            "Summarizer.generate.daily",
            logger,
            metadata={
                "user_id": str(user_id),
                "article_count": len(valid_articles),
                "raw_article_count": len(articles),
                "keyword_summary_count": len(keyword_summaries),
            },
            threshold_ms=1000,
        ):
            summary_text, token_usage = await self.summarizer.generate(
                articles,
                config,
                keyword_text,
                keyword_summaries=keyword_summaries or None,
            )
        
        # 토큰 사용량 처리 (Gemini API에서 실제 토큰 사용량 추출)
        if token_usage:
            input_tokens = token_usage.get('input_tokens', 0)
            output_tokens = token_usage.get('output_tokens', 0)
            total_tokens = token_usage.get('total_tokens', 0)
        else:
            # 토큰 사용량 정보가 없는 경우 추정
            input_text = "\n".join(
                [a.get('title', '') + " " + a.get('snippet', '') for a in valid_articles]
            )
            input_tokens = self._estimate_tokens(input_text)
            output_tokens = self._estimate_tokens(summary_text)
            total_tokens = input_tokens + output_tokens
        
        # 토큰 사용량 기록 (시스템 전체)
        record_task: Optional[asyncio.Task] = None
        try:
            record_task = asyncio.create_task(
                self.token_tracker.record_usage(
                    tokens_used=total_tokens,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens
                )
            )
        except Exception as e:
            logger.warning(f"토큰 사용량 기록 실패: {e}")
            record_task = None
        
        # 요약 세션 저장
        async with track_async_performance(
            "SummarySessionRepository.create.daily",
            logger,
            metadata={"user_id": str(user_id)},
        ):
            summary_session = await SummarySessionRepository.create(
                keyword_id=None,
                user_id=user_id,
                summary_text=summary_text,
                summary_type='daily',
                summarization_config=config
            )
        if record_task:
            try:
                await record_task
            except Exception as record_error:
                logger.warning(f"토큰 사용량 기록 대기 중 오류: {record_error}")
        
        return {
            'session_id': str(summary_session['id']),
            'summary_text': summary_text,
            'articles_count': len(valid_articles),
            'config': config,
            'created_at': summary_session['created_at'].isoformat() if summary_session.get('created_at') else None
        }
    
    async def generate_keyword_summary(
        self,
        keyword_id: UUID,
        user_id: UUID,
        include_archived: bool = False
    ) -> Dict[str, Any]:
        """키워드별 요약 생성
        
        Args:
            keyword_id (UUID): 키워드 ID
            user_id (UUID): 사용자 ID
            include_archived (bool): 소프트 삭제된 키워드 포함 여부
        """
        # 키워드 정보 조회
        async with track_async_performance(
            "KeywordRepository.get_by_id",
            logger,
            metadata={"keyword_id": str(keyword_id), "user_id": str(user_id)},
        ):
            keyword = await KeywordRepository.get_by_id(keyword_id, user_id)
        if not keyword:
            raise ValueError(f"키워드를 찾을 수 없습니다: {keyword_id}")
        
        keyword_text = keyword.get('text', '키워드')
        
        # 키워드별 최근 기사 조회
        async def _fetch_keyword_articles():
            async with track_async_performance(
                "ArticleRepository.fetch_recent_by_keyword",
                logger,
                metadata={
                    "keyword_id": str(keyword_id),
                    "user_id": str(user_id),
                    "limit": 50,
                    "include_archived": include_archived,
                },
            ):
                return await ArticleRepository.fetch_recent_by_keyword(
                    keyword_id, limit=50, include_archived=include_archived
                )

        async def _fetch_keyword_feedback():
            async with track_async_performance(
                "FeedbackRepository.aggregate_by_keyword",
                logger,
                metadata={"keyword_id": str(keyword_id), "user_id": str(user_id)},
            ):
                return await FeedbackRepository.aggregate_by_keyword(keyword_id, user_id)

        try:
            articles, feedback_stats = await asyncio.gather(
                _fetch_keyword_articles(),
                _fetch_keyword_feedback(),
            )
        except Exception as e:
            logger.warning(f"피드백 통계 조회 실패, 기본값 사용: {e}")
            articles = await _fetch_keyword_articles()
            feedback_stats = {}

        valid_articles = _filter_articles_with_url(articles)
        
        # 요약 정책 조정
        config = self.policy.tune(feedback_stats)
        
        # 요약 생성 (async)
        async with track_async_performance(
            "Summarizer.generate.keyword",
            logger,
            metadata={
                "keyword_id": str(keyword_id),
                "user_id": str(user_id),
                "article_count": len(valid_articles),
                "raw_article_count": len(articles),
            },
            threshold_ms=1000,
        ):
            summary_text, token_usage = await self.summarizer.generate(articles, config, keyword_text)
        
        # 토큰 사용량 처리 (Gemini API에서 실제 토큰 사용량 추출)
        if token_usage:
            input_tokens = token_usage.get('input_tokens', 0)
            output_tokens = token_usage.get('output_tokens', 0)
            total_tokens = token_usage.get('total_tokens', 0)
        else:
            # 토큰 사용량 정보가 없는 경우 추정
            input_text = "\n".join(
                [a.get('title', '') + " " + a.get('snippet', '') for a in valid_articles]
            )
            input_tokens = self._estimate_tokens(input_text)
            output_tokens = self._estimate_tokens(summary_text)
            total_tokens = input_tokens + output_tokens
        
        # 토큰 사용량 기록 (시스템 전체)
        record_task: Optional[asyncio.Task] = None
        try:
            record_task = asyncio.create_task(
                self.token_tracker.record_usage(
                    tokens_used=total_tokens,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens
                )
            )
        except Exception as e:
            logger.warning(f"토큰 사용량 기록 실패: {e}")
            record_task = None
        
        # 요약 세션 저장 (테이블이 없거나 오류가 발생하면 세션 ID 없이 반환)
        try:
            async with track_async_performance(
                "SummarySessionRepository.create.keyword",
                logger,
                metadata={
                    "keyword_id": str(keyword_id),
                    "user_id": str(user_id),
                },
            ):
                summary_session = await SummarySessionRepository.create(
                    keyword_id=keyword_id,
                    user_id=user_id,
                    summary_text=summary_text,
                    summary_type='keyword',
                    summarization_config=config
                )
            session_id = str(summary_session['id'])
            if record_task:
                try:
                    await record_task
                except Exception as record_error:
                    logger.warning(f"토큰 사용량 기록 대기 중 오류: {record_error}")
        except Exception as e:
            # 요약 세션 저장 실패해도 요약 텍스트는 반환
            logger.warning(f"요약 세션 저장 실패, 세션 ID 없이 반환: {e}")
            session_id = None
        
        return {
            'session_id': session_id,
            'summary_text': summary_text,
            'articles_count': len(valid_articles),
            'config': config
        }

