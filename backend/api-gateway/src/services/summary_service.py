"""요약 생성 서비스"""
from typing import Dict, Any, List, Optional, Tuple, Set
from uuid import UUID
import sys
import os
import asyncio
import logging
import re

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../shared'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from repositories.article_repository import ArticleRepository
from repositories.summary_session_repository import SummarySessionRepository
from repositories.feedback_repository import FeedbackRepository
from repositories.keyword_repository import KeywordRepository
from repositories.fetch_history_repository import FetchHistoryRepository
from services.token_tracker import TokenTracker
from config.settings import settings
from utils.performance import track_async_performance

# timezone_utils는 shared/utils에 있으므로 직접 import
shared_utils_path = os.path.join(os.path.dirname(__file__), '../../../shared/utils')
if shared_utils_path not in sys.path:
    sys.path.insert(0, shared_utils_path)
from timezone_utils import utc_to_kst, now_kst

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
        previous_summaries: Optional[List[str]] = None,
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
                previous_summaries=previous_summaries,
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
        previous_summaries: Optional[List[str]] = None,
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
                "이 키워드별 요약들을 반드시 참고하여 전체 요약을 작성하세요:\n"
                "- 각 키워드별 요약의 핵심 내용을 파악하고, 키워드 간 연관성과 공통 주제를 찾아 통합하세요.\n"
                "- 키워드별 요약을 단순히 나열하거나 반복하지 말고, 교차 분석을 통해 새로운 통찰을 도출하세요.\n"
                "- 전체 요약 섹션에서는 이러한 통합된 관점을 바탕으로 한눈에 읽기 쉬운 형태로 핵심을 요약하세요.\n"
                + "\n".join(reference_lines)
            )

        history_section = self._build_history_prompt(previous_summaries)
        history_sentences = self._build_history_sentences(previous_summaries)

        # 프롬프트 작성
        max_length = config.get('max_length', 1000)
        overview_heading = "전체 요약" if keyword_text == "일일 요약" else f"{keyword_text} 핵심 요약"
        
        prompt = f"""
역할: 당신은 '{keyword_text}' 관련 뉴스를 전문적으로 분석하고 요약하는 AI 분석가입니다.
목표: 제공된 {len(articles_with_url)}개의 뉴스 기사를 바탕으로, 사용자가 핵심 이슈를 빠르고 정확하게 파악할 수 있도록 요약 리포트를 작성하세요.

[제약 사항]
1. **사실 기반**: 반드시 제공된 기사 내용에만 기반하여 작성하세요. 기사에 없는 내용, 외부 지식, 추측은 절대 포함하지 마세요.
2. **한국어 작성**: 모든 내용은 자연스러운 한국어로 작성하세요.
3. **객관성 유지**: 감정적인 표현을 배제하고 객관적인 사실 위주로 서술하세요.

[출력 형식]
아래 마크다운 형식을 정확히 준수하세요.

**{overview_heading}**
- (전체적인 흐름과 핵심 이슈를 아우르는 종합 요약 1)
- (전체적인 흐름과 핵심 이슈를 아우르는 종합 요약 2)
- (전체적인 흐름과 핵심 이슈를 아우르는 종합 요약 3)
- (전체적인 흐름과 핵심 이슈를 아우르는 종합 요약 4)
- (전체적인 흐름과 핵심 이슈를 아우르는 종합 요약 5)

(빈 줄)

**[주요 주제 1]**
- (해당 주제와 관련된 상세 내용 1) (감성: 긍정/부정/중립)
- (해당 주제와 관련된 상세 내용 2) (감성: 긍정/부정/중립)
- (해당 주제와 관련된 상세 내용 3) (감성: 긍정/부정/중립)

(빈 줄)

**[주요 주제 2]**
- (해당 주제와 관련된 상세 내용 1) (감성: 긍정/부정/중립)
- (해당 주제와 관련된 상세 내용 2) (감성: 긍정/부정/중립)
- (해당 주제와 관련된 상세 내용 3) (감성: 긍정/부정/중립)

(빈 줄)

**생각해볼 포인트**
- (이 이슈와 관련하여 사용자가 고민해보거나 주목해야 할 통찰 1)
- (이 이슈와 관련하여 사용자가 고민해보거나 주목해야 할 통찰 2)

[입력 데이터]
기사 목록:
{all_articles_text}

참고 자료(키워드별 요약):
{reference_section if reference_section else "없음"}

이전 요약 기록(참고용):
{history_section if history_section else "없음"}

[작성 지침]
- 전체 길이는 공백 포함 약 {max_length}자 내외로 작성하세요.
- 각 bullet point는 명확하고 구체적인 문장으로 작성하세요.
- 중복된 내용은 통합하고, 상충되는 내용은 대조하여 서술하세요.
- 이전 요약 기록과 중복되는 문장은 피해서 작성하세요.
"""
        
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
                
                # 기사 번호 참조 제거 (예: "기사 9, 10, 11" 또는 "(기사 1, 2)" 등)
                # 괄호 안의 기사 번호 패턴 제거: (기사 9, 10, 11) 또는 (기사 1, 2-3)
                summary = re.sub(r'\(기사\s+\d+(?:\s*[,\-]\s*\d+)*\)', '', summary)
                # 괄호 없는 기사 번호 패턴 제거: 기사 9, 10, 11 또는 기사 1-3
                summary = re.sub(r'기사\s+\d+(?:\s*[,\-]\s*\d+)*', '', summary)
                # "기사 N에 따르면" 같은 패턴도 제거
                summary = re.sub(r'기사\s+\d+에\s+따르면', '', summary)
                # 연속된 쉼표나 괄호 정리
                summary = re.sub(r'\s*,\s*,+', '', summary)  # 연속된 쉼표 제거
                summary = re.sub(r'\(\s*\)', '', summary)  # 빈 괄호 제거
                summary = re.sub(r'\s*\(\s*\)\s*', '', summary)  # 빈 괄호와 주변 공백 제거
                summary = re.sub(r'\s+', ' ', summary)  # 연속된 공백을 하나로
                summary = re.sub(r'\s*,\s*$', '', summary)  # 문장 끝의 쉼표 제거
                summary = summary.strip()

                summary = self._apply_bullet_spacing(summary)
                if history_sentences:
                    summary = self._remove_duplicate_points(summary, history_sentences)
                
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

    def _build_history_prompt(self, previous_summaries: Optional[List[str]]) -> str:
        if not previous_summaries:
            return ""
        max_entries = 5
        snippets: List[str] = []
        for index, text in enumerate(previous_summaries[:max_entries], 1):
            if not isinstance(text, str):
                continue
            normalized = re.sub(r'\s+', ' ', text.strip())
            if not normalized:
                continue
            if len(normalized) > 500:
                normalized = normalized[:500].rstrip() + "..."
            snippets.append(f"{index}. {normalized}")
        return "\n".join(snippets)

    def _build_history_sentences(
        self,
        previous_summaries: Optional[List[str]],
    ) -> Set[str]:
        sentences: Set[str] = set()
        if not previous_summaries:
            return sentences
        for text in previous_summaries:
            if not isinstance(text, str):
                continue
            for line in text.splitlines():
                normalized = self._normalize_line_for_dedup(line)
                if normalized:
                    sentences.add(normalized)
        return sentences

    def _normalize_line_for_dedup(self, line: str) -> str:
        stripped = line.strip()
        if not stripped:
            return ""
        stripped = re.sub(r'^[\-\•\·\s]+', '', stripped)
        stripped = re.sub(r'\s+', ' ', stripped)
        return stripped.lower()

    def _cleanup_blank_lines(self, lines: List[str]) -> List[str]:
        cleaned: List[str] = []
        for line in lines:
            if not line.strip():
                if cleaned and cleaned[-1] == '':
                    continue
                if cleaned:
                    cleaned.append('')
                continue
            cleaned.append(line.rstrip())
        while cleaned and cleaned[-1] == '':
            cleaned.pop()
        return cleaned

    def _apply_bullet_spacing(self, text: str) -> str:
        if not text:
            return text
        lines = [line.rstrip() for line in text.splitlines()]
        spaced: List[str] = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                spaced.append('')
                continue
            spaced.append(line.rstrip())
            if stripped.startswith('- '):
                spaced.append('')
        cleaned = self._cleanup_blank_lines(spaced)
        return "\n".join(cleaned)

    def _remove_duplicate_points(self, summary: str, seen_sentences: Set[str]) -> str:
        lines = summary.splitlines()
        filtered: List[str] = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                filtered.append('')
                continue
            is_heading = stripped.startswith('**') and stripped.endswith('**')
            if is_heading:
                filtered.append(line.rstrip())
                continue
            normalized = self._normalize_line_for_dedup(stripped)
            if not normalized:
                filtered.append(line.rstrip())
                continue
            if normalized in seen_sentences:
                continue
            seen_sentences.add(normalized)
            filtered.append(line.rstrip())
        cleaned = self._cleanup_blank_lines(filtered)
        return "\n".join(cleaned)


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
                'max_length': 1000,
                'include_sentiment': True,
                'include_keywords': False,
                'include_sources': False,
                'top_articles_count': 5
            }
        
        if avg_rating >= 4.0:
            # 높은 만족도: 현재 수준 유지
            return {
                'detail_level': 'maintain_current',
                'max_length': 1000,
                'include_sentiment': True,
                'include_keywords': False,
                'include_sources': False,
                'top_articles_count': 5
            }
        elif avg_rating >= 3.0:
            # 중간 만족도: 더 많은 맥락 제공
            return {
                'detail_level': 'tweak_for_more_context',
                'max_length': 1200,
                'include_sentiment': True,
                'include_keywords': True,
                'include_sources': False,
                'top_articles_count': 7
            }
        else:
            # 낮은 만족도: 상세 정보 증가
            return {
                'detail_level': 'increase_detail',
                'max_length': 1500,
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
            
            # 마지막 수집 시간 조회
            last_fetch_end_utc = None
            try:
                last_fetch_end_utc = await FetchHistoryRepository.get_latest_fetch_end_by_keyword(keyword_id)
            except Exception as e:
                logger.warning(f"마지막 수집 시간 조회 실패: {e}")
                last_fetch_end_utc = None
            
            # 기사 개수 조회 (날짜 필터 적용)
            if last_fetch_end_utc:
                async with track_async_performance(
                    "ArticleRepository.count_recent_by_keyword_since",
                    logger,
                    metadata={
                        "keyword_id": str(keyword_id),
                        "since_datetime": str(last_fetch_end_utc),
                        "include_archived": include_archived,
                    },
                ):
                    articles_count = await ArticleRepository.count_recent_by_keyword_since(
                        keyword_id, 
                        since_datetime=last_fetch_end_utc, 
                        include_archived=include_archived
                    )
            else:
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
        # 마지막 수집 시간 조회 (사용자 전체)
        last_fetch_end_utc = None
        try:
            async with track_async_performance(
                "FetchHistoryRepository.get_latest_fetch_end_by_user",
                logger,
                metadata={"user_id": str(user_id)},
            ):
                last_fetch_end_utc = await FetchHistoryRepository.get_latest_fetch_end_by_user(user_id)
        except Exception as e:
            logger.warning(f"마지막 수집 시간 조회 실패: {e}")
            last_fetch_end_utc = None
        
        async def _fetch_articles():
            if last_fetch_end_utc is None:
                # 첫 수집인 경우: 전체 기사 조회 (기존 동작)
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
            else:
                # 마지막 수집 이후 기사만 조회
                async with track_async_performance(
                    "ArticleRepository.fetch_recent_by_user_since",
                    logger,
                    metadata={
                        "user_id": str(user_id),
                        "since_datetime": str(last_fetch_end_utc),
                        "limit": 100,
                        "include_archived": include_archived,
                    },
                ):
                    return await ArticleRepository.fetch_recent_by_user_since(
                        user_id,
                        since_datetime=last_fetch_end_utc,
                        limit=100,
                        include_archived=include_archived
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

        async def _fetch_previous_summaries():
            try:
                return await SummarySessionRepository.list_summary_texts(
                    user_id=user_id,
                    summary_type='daily',
                )
            except Exception as exc:
                logger.warning(
                    "이전 일일 요약 조회 실패: %s (user_id=%s)",
                    exc,
                    user_id,
                )
                return []

        articles, feedback_stats, keywords, previous_summaries = await asyncio.gather(
            _fetch_articles(),
            _fetch_feedback(),
            _fetch_keywords(),
            _fetch_previous_summaries(),
        )
        
        valid_articles = _filter_articles_with_url(articles)
        
        # 기사가 없으면 요약 생성하지 않고 반환
        if not valid_articles:
            config = self.policy.tune(feedback_stats)
            return {
                'session_id': None,
                'summary_text': '수집된 기사가 없습니다.',
                'articles_count': 0,
                'config': config,
                'created_at': None
            }

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
                previous_summaries=previous_summaries,
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
        
        # 마지막 수집 시간 조회
        last_fetch_end_utc = None
        try:
            async with track_async_performance(
                "FetchHistoryRepository.get_latest_fetch_end_by_keyword",
                logger,
                metadata={"keyword_id": str(keyword_id)},
            ):
                last_fetch_end_utc = await FetchHistoryRepository.get_latest_fetch_end_by_keyword(keyword_id)
        except Exception as e:
            logger.warning(f"마지막 수집 시간 조회 실패: {e}")
            last_fetch_end_utc = None
        
        # 키워드별 최근 기사 조회
        async def _fetch_keyword_articles():
            if last_fetch_end_utc is None:
                # 첫 수집인 경우: 전체 기사 조회 (기존 동작)
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
            else:
                # 마지막 수집 이후 기사만 조회
                async with track_async_performance(
                    "ArticleRepository.fetch_recent_by_keyword_since",
                    logger,
                    metadata={
                        "keyword_id": str(keyword_id),
                        "user_id": str(user_id),
                        "since_datetime": str(last_fetch_end_utc),
                        "limit": 50,
                        "include_archived": include_archived,
                    },
                ):
                    return await ArticleRepository.fetch_recent_by_keyword_since(
                        keyword_id,
                        since_datetime=last_fetch_end_utc,
                        limit=50,
                        include_archived=include_archived
                    )

        async def _fetch_keyword_feedback():
            async with track_async_performance(
                "FeedbackRepository.aggregate_by_keyword",
                logger,
                metadata={"keyword_id": str(keyword_id), "user_id": str(user_id)},
            ):
                return await FeedbackRepository.aggregate_by_keyword(keyword_id, user_id)

        async def _fetch_previous_keyword_summaries():
            try:
                return await SummarySessionRepository.list_summary_texts(
                    user_id=user_id,
                    keyword_id=keyword_id,
                    summary_type='keyword',
                )
            except Exception as exc:
                logger.warning(
                    "이전 키워드 요약 조회 실패: %s (keyword_id=%s, user_id=%s)",
                    exc,
                    keyword_id,
                    user_id,
                )
                return []

        try:
            articles, feedback_stats, previous_summaries = await asyncio.gather(
                _fetch_keyword_articles(),
                _fetch_keyword_feedback(),
                _fetch_previous_keyword_summaries(),
            )
        except Exception as e:
            logger.warning(f"피드백 통계 조회 실패, 기본값 사용: {e}")
            articles = await _fetch_keyword_articles()
            feedback_stats = {}
            previous_summaries = await _fetch_previous_keyword_summaries()

        valid_articles = _filter_articles_with_url(articles)
        
        # 기사가 없으면 요약 생성하지 않고 반환
        if not valid_articles:
            config = self.policy.tune(feedback_stats)
            return {
                'session_id': None,
                'summary_text': '수집된 기사가 없습니다.',
                'articles_count': 0,
                'config': config
            }
        
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
            summary_text, token_usage = await self.summarizer.generate(
                articles,
                config,
                keyword_text,
                previous_summaries=previous_summaries,
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

