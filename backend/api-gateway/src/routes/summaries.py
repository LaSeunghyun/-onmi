"""요약 관련 라우터"""
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
import sys
import os
import logging

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../shared'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.routes.auth import get_current_user
from services.summary_service import SummaryService
from services.feedback_service import FeedbackService
from services.workflow_service import WorkflowService
from repositories.summary_session_repository import SummarySessionRepository

logger = logging.getLogger(__name__)

router = APIRouter()


class SummaryResponse(BaseModel):
    session_id: str
    summary_text: str
    summary_type: str
    articles_count: int
    created_at: str


class FeedbackRequest(BaseModel):
    rating: int  # 1-5
    comment: Optional[str] = None


@router.get("/daily", response_model=SummaryResponse)
async def get_daily_summary(current_user: dict = Depends(get_current_user)):
    """일일 요약 조회
    
    사용자의 모든 키워드에 대한 통합 요약을 조회합니다.
    최신 요약이 없으면 새로 생성합니다.
    """
    try:
        summary_service = SummaryService()
        user_uuid = UUID(current_user["id"])
        
        # 최신 일일 요약 조회
        latest_summary = await SummarySessionRepository.get_latest_daily(user_uuid)
        
        if latest_summary:
            # 최신 요약 반환
            return SummaryResponse(
                session_id=str(latest_summary.id),
                summary_text=latest_summary.summary_text,
                summary_type=latest_summary.summary_type,
                articles_count=0,  # TODO: 실제 기사 개수 조회 필요
                created_at=latest_summary.created_at.isoformat()
            )
        else:
            # 새 요약 생성
            result = await summary_service.generate_daily_summary(user_uuid)
            return SummaryResponse(
                session_id=result['session_id'],
                summary_text=result['summary_text'],
                summary_type='daily',
                articles_count=result['articles_count'],
                created_at=""  # 생성 시간은 DB에서 조회 필요
            )
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
    current_user: dict = Depends(get_current_user)
):
    """키워드별 요약 조회
    
    특정 키워드에 대한 요약을 조회합니다.
    최신 요약이 없으면 새로 생성합니다.
    """
    try:
        summary_service = SummaryService()
        user_uuid = UUID(current_user["id"])
        keyword_uuid = UUID(keyword_id)
        
        # 소유권 확인
        from repositories.keyword_repository import KeywordRepository
        keyword = await KeywordRepository.get_by_id(keyword_uuid, user_uuid)
        if not keyword:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="키워드를 찾을 수 없습니다"
            )
        
        # 최신 키워드별 요약 조회
        latest_summary = await SummarySessionRepository.get_latest_by_keyword(
            keyword_uuid, user_uuid
        )
        
        if latest_summary:
            # 최신 요약 반환
            return SummaryResponse(
                session_id=str(latest_summary.id),
                summary_text=latest_summary.summary_text,
                summary_type=latest_summary.summary_type,
                articles_count=0,  # TODO: 실제 기사 개수 조회 필요
                created_at=latest_summary.created_at.isoformat()
            )
        else:
            # 새 요약 생성
            result = await summary_service.generate_keyword_summary(keyword_uuid, user_uuid)
            return SummaryResponse(
                session_id=result['session_id'],
                summary_text=result['summary_text'],
                summary_type='keyword',
                articles_count=result['articles_count'],
                created_at=""  # 생성 시간은 DB에서 조회 필요
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
        
        workflow_service = WorkflowService()
        user_uuid = UUID(current_user["id"])
        session_uuid = UUID(summary_session_id)
        
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

