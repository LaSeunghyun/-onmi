"""사용자 선호도 관련 라우터"""
import logging
import sys
import os
from typing import Dict, Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../shared'))
from src.routes.auth import get_current_user
from src.repositories.preference_repository import PreferenceRepository

logger = logging.getLogger(__name__)

router = APIRouter()


class PreferencesUpdate(BaseModel):
    """사용자 선호도 업데이트 요청 모델"""
    notification_time_hour: Optional[int] = None  # 0-23


class PreferencesResponse(BaseModel):
    """사용자 선호도 응답 모델"""
    notification_time_hour: Optional[int] = None


@router.get("", response_model=PreferencesResponse)
async def get_preferences(current_user: dict = Depends(get_current_user)):
    """사용자 선호도 조회"""
    try:
        user_id = UUID(str(current_user["id"]))
        logger.debug(f"사용자 선호도 조회 시작: user_id={user_id}")
        preferences = await PreferenceRepository.get(user_id)
        logger.debug(f"선호도 조회 완료: preferences={preferences}")
        
        return PreferencesResponse(
            notification_time_hour=preferences.get("notification_time_hour")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"선호도 조회 오류: user_id={current_user.get('id')}, error={e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="선호도 조회 중 오류가 발생했습니다"
        )


@router.put("", response_model=PreferencesResponse)
async def update_preferences(
    preferences_update: PreferencesUpdate,
    current_user: dict = Depends(get_current_user)
):
    """사용자 선호도 업데이트"""
    try:
        user_id = UUID(str(current_user["id"]))
        
        # 기존 선호도 조회
        existing_preferences = await PreferenceRepository.get(user_id)
        
        # 업데이트할 선호도 병합
        updated_preferences = {**existing_preferences}
        
        if preferences_update.notification_time_hour is not None:
            # 알림 시간 유효성 검사 (0-23)
            if not (0 <= preferences_update.notification_time_hour <= 23):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="알림 시간은 0-23 사이의 값이어야 합니다"
                )
            updated_preferences["notification_time_hour"] = preferences_update.notification_time_hour
        
        # 선호도 저장
        await PreferenceRepository.upsert(user_id, updated_preferences)
        
        return PreferencesResponse(
            notification_time_hour=updated_preferences.get("notification_time_hour")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"선호도 업데이트 오류: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="선호도 업데이트 중 오류가 발생했습니다"
        )

