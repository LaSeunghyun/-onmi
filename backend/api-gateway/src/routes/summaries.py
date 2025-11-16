"""요약 관련 라우터"""
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone, date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../shared'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.routes.auth import get_current_user
from services.summary_service import SummaryService
from services.feedback_service import FeedbackService
from services.workflow_service import WorkflowService
from repositories.summary_session_repository import SummarySessionRepository
from repositories.article_repository import ArticleRepository
from utils.performance import track_async_performance
from utils.pending_summary_registry import PendingSummaryRegistry

# timezone_utils는 shared/utils에 있으므로 직접 import
shared_utils_path = os.path.join(os.path.dirname(__file__), '../../../shared/utils')
if shared_utils_path not in sys.path:
    sys.path.insert(0, shared_utils_path)
from timezone_utils import utc_to_kst, kst_to_iso_string

logger = logging.getLogger(__name__)

router = APIRouter()


class SummaryResponse(BaseModel):
    session_id: str
    summary_text: str
    summary_type: str
    articles_count: int
    created_at: str
    available_dates: List[str]
    status: str = "ready"
    message: Optional[str] = None


class FeedbackRequest(BaseModel):
    rating: int  # 1-5
    comment: Optional[str] = None


def _format_created_at(created_at: Optional[datetime | str]) -> str:
    """created_at을 한국 시간(KST)으로 변환하여 ISO 문자열로 반환
    
    Args:
        created_at: UTC datetime 객체, ISO 형식 문자열, 또는 None
        
    Returns:
        KST로 변환된 ISO 8601 형식 문자열, 또는 빈 문자열
    """
    if not created_at:
        return ""
    
    # 문자열인 경우 datetime으로 변환
    if isinstance(created_at, str):
        try:
            # ISO 형식 문자열 파싱
            if '+' in created_at or created_at.endswith('Z'):
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            else:
                # 시간대 정보가 없으면 UTC로 가정
                dt = datetime.fromisoformat(created_at)
                dt = dt.replace(tzinfo=timezone.utc)
            created_at = dt
        except (ValueError, AttributeError) as e:
            logger.warning(f"created_at 문자열 파싱 실패: {created_at}, error: {e}")
            return str(created_at)  # 파싱 실패 시 원본 문자열 반환
    
    # datetime 객체인 경우에만 처리
    if isinstance(created_at, datetime):
        # UTC로 가정하고 KST로 변환
        if created_at.tzinfo is None:
            # 시간대 정보가 없으면 UTC로 가정
            utc_dt = created_at.replace(tzinfo=timezone.utc)
        else:
            utc_dt = created_at.astimezone(timezone.utc)
        
        kst_dt = utc_to_kst(utc_dt)
        return kst_to_iso_string(kst_dt)
    
    # 예상치 못한 타입인 경우 문자열로 변환
    return str(created_at)


async def _run_keyword_summary_task(
    keyword_uuid: UUID,
    user_uuid: UUID,
    pending_key: str,
    target_date: Optional[str] = None,
) -> None:
    """키워드 요약 생성을 백그라운드에서 수행한다."""
    summary_service = SummaryService()
    try:
        logger.info(
            "키워드 요약 비동기 생성 시작",
            extra={
                "keyword_id": str(keyword_uuid),
                "user_id": str(user_uuid),
                "target_date": target_date,
            },
        )
        await summary_service.generate_keyword_summary(keyword_uuid, user_uuid)
        logger.info(
            "키워드 요약 비동기 생성 완료",
            extra={
                "keyword_id": str(keyword_uuid),
                "user_id": str(user_uuid),
                "target_date": target_date,
            },
        )
    except Exception as exc:
        logger.error(
            "키워드 요약 비동기 생성 중 오류: %s", exc, exc_info=True
        )
    finally:
        await PendingSummaryRegistry.clear_pending(pending_key)


async def _enqueue_keyword_summary_generation(
    keyword_uuid: UUID,
    user_uuid: UUID,
    target_date: Optional[date],
) -> None:
    """중복 생성을 방지하며 요약 생성을 예약한다."""
    pending_key = PendingSummaryRegistry.build_key(
        str(keyword_uuid),
        str(user_uuid),
        target_date.isoformat() if target_date else None,
    )
    already_pending = await PendingSummaryRegistry.is_pending(pending_key)
    if already_pending:
        return
    await PendingSummaryRegistry.mark_pending(pending_key)
    asyncio.create_task(
        _run_keyword_summary_task(
            keyword_uuid,
            user_uuid,
            pending_key,
            target_date.isoformat() if target_date else None,
        )
    )


def _pending_summary_response(
    summary_type: str,
    available_dates: List[str],
    message: str,
) -> JSONResponse:
    """요약 생성 대기 상태 응답을 반환한다."""
    response_body = SummaryResponse(
        session_id="",
        summary_text="",
        summary_type=summary_type,
        articles_count=0,
        created_at="",
        available_dates=available_dates,
        status="pending",
        message=message,
    )
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content=response_body.dict(),
    )


@router.get("/daily", response_model=SummaryResponse)
async def get_daily_summary(
    date: Optional[str] = Query(None, description="조회할 날짜 (YYYY-MM-DD)"),
    current_user: dict = Depends(get_current_user)
):
    """일일 요약 조회
    
    사용자의 모든 키워드에 대한 통합 요약을 조회합니다.
    최신 요약이 없으면 새로 생성합니다.
    """
    try:
        target_date = None
        if date:
            try:
                target_date = datetime.strptime(date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="유효한 날짜 형식이 아닙니다. YYYY-MM-DD 형식을 사용하세요."
                )

        summary_service = SummaryService()
        user_uuid = UUID(str(current_user["id"]))

        async with track_async_performance(
            "SummarySessionRepository.prefetch_daily_metadata",
            logger,
            metadata={"user_id": str(user_uuid), "date": date},
        ):
            available_dates_task = asyncio.create_task(
                SummarySessionRepository.list_daily_dates(user_uuid)
            )
            summary_task: asyncio.Task
            if target_date:
                summary_task = asyncio.create_task(
                    SummarySessionRepository.get_daily_by_date(user_uuid, target_date)
                )
            else:
                summary_task = asyncio.create_task(
                    SummarySessionRepository.get_latest_daily(user_uuid)
                )
            available_dates_raw, summary_candidate = await asyncio.gather(
                available_dates_task,
                summary_task,
            )
        available_dates = [
            d.isoformat() if hasattr(d, "isoformat") else str(d)
            for d in available_dates_raw
        ]

        if target_date:
            summary = summary_candidate
            if not summary:
                # 날짜가 지정되었지만 요약이 없으면 새로 생성
                logger.info(f"날짜 지정 요약 없음, 새 일일 요약 생성 시작: user_id={user_uuid}, date={target_date}")
                try:
                    async with track_async_performance(
                        "SummaryService.generate_daily_summary",
                        logger,
                        metadata={"user_id": str(user_uuid), "target_date": str(target_date)},
                        threshold_ms=500,
                    ):
                        result = await summary_service.generate_daily_summary(user_uuid)
                    logger.info(f"일일 요약 생성 완료: session_id={result.get('session_id')}")
                    created_at_raw = result.get('created_at')
                    created_at_str = _format_created_at(created_at_raw) if created_at_raw else ''
                    if created_at_str:
                        try:
                            # KST ISO 문자열에서 날짜 추출
                            if '+' in created_at_str:
                                kst_dt = datetime.fromisoformat(created_at_str)
                            else:
                                kst_dt = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                            new_date = kst_dt.date()
                            new_date_str = new_date.isoformat()
                            if new_date_str not in available_dates:
                                available_dates.insert(0, new_date_str)
                        except (ValueError, AttributeError):
                            pass
                    async with track_async_performance(
                        "ArticleRepository.count_recent_by_user",
                        logger,
                        metadata={"user_id": str(user_uuid), "limit": 100},
                    ):
                        articles_count = await ArticleRepository.count_recent_by_user(user_uuid, include_archived=False)
                    return SummaryResponse(
                        session_id=result['session_id'],
                        summary_text=result['summary_text'],
                        summary_type='daily',
                        articles_count=articles_count,
                        created_at=created_at_str,
                        available_dates=available_dates
                    )
                except Exception as e:
                    logger.error(f"일일 요약 생성 실패: user_id={user_uuid}, date={target_date}, error={e}", exc_info=True)
                    raise

            created_at_str = _format_created_at(summary["created_at"])
            async with track_async_performance(
                "ArticleRepository.count_recent_by_user",
                logger,
                metadata={"user_id": str(user_uuid), "limit": 100},
            ):
                articles_count = await ArticleRepository.count_recent_by_user(user_uuid, include_archived=False)
            return SummaryResponse(
                session_id=str(summary["id"]),
                summary_text=summary["summary_text"],
                summary_type=summary["summary_type"],
                articles_count=articles_count,
                created_at=created_at_str,
                available_dates=available_dates
            )
        
        # 최신 일일 요약 조회
        logger.info(f"일일 요약 조회 시작: user_id={user_uuid}, date={date}")
        latest_summary = summary_candidate
        logger.info(f"최신 일일 요약 조회 결과: {latest_summary is not None}")
        
        if latest_summary:
            # 최신 요약 반환 - 실제 기사 개수 조회
            logger.info(f"기존 요약 반환: session_id={latest_summary.get('id')}")
            async with track_async_performance(
                "ArticleRepository.count_recent_by_user",
                logger,
                metadata={"user_id": str(user_uuid), "limit": 100},
            ):
                articles_count = await ArticleRepository.count_recent_by_user(user_uuid, include_archived=False)
            
            # created_at을 한국 시간으로 변환
            created_at_str = _format_created_at(latest_summary["created_at"])
            
            return SummaryResponse(
                session_id=str(latest_summary["id"]),
                summary_text=latest_summary["summary_text"],
                summary_type=latest_summary["summary_type"],
                articles_count=articles_count,
                created_at=created_at_str,
                available_dates=available_dates
            )
        else:
            # 새 요약 생성
            logger.info(f"새 일일 요약 생성 시작: user_id={user_uuid}")
            try:
                async with track_async_performance(
                    "SummaryService.generate_daily_summary",
                    logger,
                    metadata={"user_id": str(user_uuid)},
                    threshold_ms=500,
                ):
                    result = await summary_service.generate_daily_summary(user_uuid)
                logger.info(f"일일 요약 생성 완료: session_id={result.get('session_id')}")
                created_at_raw = result.get('created_at')
                created_at_str = _format_created_at(created_at_raw) if created_at_raw else ''
                if created_at_str:
                    try:
                        # KST ISO 문자열에서 날짜 추출
                        # ISO 형식: "2024-01-01T12:00:00+09:00"
                        if '+' in created_at_str:
                            kst_dt = datetime.fromisoformat(created_at_str)
                        else:
                            kst_dt = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                        new_date = kst_dt.date()
                        new_date_str = new_date.isoformat()
                        if new_date_str not in available_dates:
                            available_dates.insert(0, new_date_str)
                    except (ValueError, AttributeError):
                        pass
                return SummaryResponse(
                    session_id=result['session_id'],
                    summary_text=result['summary_text'],
                    summary_type='daily',
                    articles_count=result['articles_count'],
                    created_at=created_at_str,
                    available_dates=available_dates
                )
            except Exception as e:
                logger.error(f"일일 요약 생성 실패: user_id={user_uuid}, error={e}", exc_info=True)
                raise
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"일일 요약 조회 중 오류 발생: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="일일 요약을 불러오는 중 오류가 발생했습니다"
        )


@router.get("/keywords/{keyword_id}", response_model=SummaryResponse)
async def get_keyword_summary(
    keyword_id: str,
    date: Optional[str] = Query(None, description="조회할 날짜 (YYYY-MM-DD)"),
    current_user: dict = Depends(get_current_user)
):
    """키워드별 요약 조회
    
    특정 키워드에 대한 요약을 조회합니다.
    최신 요약이 없으면 새로 생성합니다.
    """
    try:
        # UUID 변환 오류 처리
        try:
            user_uuid = UUID(str(current_user["id"]))
            keyword_uuid = UUID(keyword_id)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"유효하지 않은 UUID 형식입니다: {str(e)}"
            )
        target_date = None
        if date:
            try:
                target_date = datetime.strptime(date, "%Y-%m-%d").date()
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"유효하지 않은 날짜 형식입니다: {str(e)}"
                )

        # 소유권 확인
        from repositories.keyword_repository import KeywordRepository
        keyword = await KeywordRepository.get_by_id(keyword_uuid, user_uuid)
        if not keyword:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="키워드를 찾을 수 없습니다"
            )
        
        async with track_async_performance(
            "SummarySessionRepository.prefetch_keyword_metadata",
            logger,
            metadata={"user_id": str(user_uuid), "keyword_id": keyword_id, "date": date},
        ):
            available_dates_task = asyncio.create_task(
                SummarySessionRepository.list_keyword_dates(keyword_uuid, user_uuid)
            )
            summary_task: asyncio.Task
            if target_date:
                summary_task = asyncio.create_task(
                    SummarySessionRepository.get_keyword_by_date(keyword_uuid, user_uuid, target_date)
                )
            else:
                summary_task = asyncio.create_task(
                    SummarySessionRepository.get_latest_by_keyword(
                        keyword_uuid, user_uuid
                    )
                )
            available_dates_raw, summary_candidate = await asyncio.gather(
                available_dates_task,
                summary_task,
            )
        available_dates = [
            d.isoformat() if hasattr(d, "isoformat") else str(d) for d in available_dates_raw
        ]

        if target_date:
            summary = summary_candidate
            if not summary:
                await _enqueue_keyword_summary_generation(
                    keyword_uuid, user_uuid, target_date
                )
                pending_message = (
                    f"{target_date.isoformat()} 키워드 요약을 생성 중입니다. "
                    "잠시 후 다시 확인해주세요."
                )
                return _pending_summary_response(
                    "keyword",
                    available_dates,
                    pending_message,
                )

            created_at_str = _format_created_at(summary["created_at"])
            async with track_async_performance(
                "ArticleRepository.count_recent_by_keyword",
                logger,
                metadata={"keyword_id": keyword_id},
            ):
                articles_count = await ArticleRepository.count_recent_by_keyword(keyword_uuid, include_archived=False)

            return SummaryResponse(
                session_id=str(summary["id"]),
                summary_text=summary["summary_text"],
                summary_type=summary["summary_type"],
                articles_count=articles_count,
                created_at=created_at_str,
                available_dates=available_dates
            )

        latest_summary = summary_candidate
        
        if latest_summary:
            created_at_str = _format_created_at(latest_summary["created_at"])
            async with track_async_performance(
                "ArticleRepository.count_recent_by_keyword",
                logger,
                metadata={"keyword_id": keyword_id},
            ):
                articles_count = await ArticleRepository.count_recent_by_keyword(keyword_uuid, include_archived=False)
            return SummaryResponse(
                session_id=str(latest_summary["id"]),
                summary_text=latest_summary["summary_text"],
                summary_type=latest_summary["summary_type"],
                articles_count=articles_count,
                created_at=created_at_str,
                available_dates=available_dates
            )
        else:
            await _enqueue_keyword_summary_generation(
                keyword_uuid, user_uuid, None
            )
            pending_message = "최신 키워드 요약을 생성 중입니다. 잠시 후 다시 확인해주세요."
            return _pending_summary_response(
                "keyword",
                available_dates,
                pending_message,
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"키워드별 요약 조회 중 오류 발생: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="키워드별 요약을 불러오는 중 오류가 발생했습니다"
        )


@router.post("/{summary_session_id}/feedback", status_code=status.HTTP_201_CREATED)
async def submit_summary_feedback(
    summary_session_id: str,
    feedback: FeedbackRequest,
    current_user: dict = Depends(get_current_user)
):
    """요약 피드백 제출
    
    좋아요/싫어요 피드백을 제출합니다.
    피드백은 요약 품질 개선에 활용됩니다.
    
    - rating: 1-5점 (1=매우 불만족, 5=매우 만족)
    - comment: 선택적 코멘트
    """
    try:
        if feedback.rating < 1 or feedback.rating > 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="평점은 1-5 사이의 값이어야 합니다"
            )
        
        # UUID 변환 오류 처리
        try:
            user_uuid = UUID(str(current_user["id"]))
            session_uuid = UUID(summary_session_id)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"유효하지 않은 UUID 형식입니다: {str(e)}"
            )
        
        workflow_service = WorkflowService()
        
        # 피드백 기록
        result = await workflow_service.record_feedback(
            session_uuid,
            user_uuid,
            feedback.rating,
            feedback.comment
        )
        
        return {
            "message": "피드백이 제출되었습니다",
            "feedback_id": result['feedback_id'],
            "rating": result['rating'],
            "detail_level": result['detail_level']
        }
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"피드백 제출 중 오류 발생: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"피드백 제출 중 오류 발생: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="피드백 제출 중 오류가 발생했습니다"
        )

