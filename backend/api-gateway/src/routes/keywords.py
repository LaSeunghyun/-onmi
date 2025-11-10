"""키워드 관련 라우터"""
import json
import logging
import os
import sys
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../shared'))
from src.routes.auth import get_current_user
from database.connection import get_db_connection

logger = logging.getLogger(__name__)

router = APIRouter()


class KeywordCreate(BaseModel):
    text: str


class KeywordResponse(BaseModel):
    id: str
    text: str
    status: str
    notify_level: str
    auto_share_enabled: bool
    auto_share_channels: List[str]
    created_at: datetime
    last_crawled_at: Optional[datetime]


@router.get("", response_model=List[KeywordResponse])
async def get_keywords(current_user: dict = Depends(get_current_user)):
    """사용자의 키워드 목록 조회"""
    try:
        async with get_db_connection() as conn:
            keywords = await conn.fetch(
                """
                SELECT id, text, status, notify_level, auto_share_enabled,
                       auto_share_channels, created_at, last_crawled_at
                FROM keywords
                WHERE user_id = $1 AND status = 'active'
                ORDER BY created_at DESC
                """,
                current_user["id"]
            )
            keyword_list: List[KeywordResponse] = []
            for kw in keywords:
                raw_channels = kw["auto_share_channels"]
                if isinstance(raw_channels, str):
                    try:
                        parsed_channels = json.loads(raw_channels)
                        if not isinstance(parsed_channels, list):
                            parsed_channels = []
                    except json.JSONDecodeError:
                        parsed_channels = []
                else:
                    parsed_channels = raw_channels or []

                keyword_list.append(
                    KeywordResponse(
                        id=str(kw["id"]),
                        text=kw["text"],
                        status=kw["status"],
                        notify_level=kw["notify_level"],
                        auto_share_enabled=kw["auto_share_enabled"],
                        auto_share_channels=parsed_channels,
                        created_at=kw["created_at"],
                        last_crawled_at=kw["last_crawled_at"],
                    )
                )
            return keyword_list
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"키워드 목록 조회 중 오류 발생: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="키워드 목록을 불러오는 중 오류가 발생했습니다"
        )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=KeywordResponse)
async def create_keyword(
    keyword: KeywordCreate,
    current_user: dict = Depends(get_current_user)
):
    """키워드 추가 (최대 3개)"""
    try:
        async with get_db_connection() as conn:
            # 키워드 개수 확인
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM keywords WHERE user_id = $1 AND status = 'active'",
                current_user["id"]
            )
            
            if count >= 3:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="최대 3개까지 키워드를 등록할 수 있습니다"
                )
            
            # 중복 확인
            existing = await conn.fetchrow(
                "SELECT id FROM keywords WHERE user_id = $1 AND text = $2 AND status = 'active'",
                current_user["id"], keyword.text
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="이미 등록된 키워드입니다"
                )
            
            # 키워드 생성
            keyword_id = await conn.fetchval(
                """
                INSERT INTO keywords (user_id, text, status, notify_level)
                VALUES ($1, $2, 'active', 'standard')
                RETURNING id
                """,
                current_user["id"], keyword.text
            )
            
            # 생성된 키워드 조회
            kw = await conn.fetchrow(
                """
                SELECT id, text, status, notify_level, auto_share_enabled,
                       auto_share_channels, created_at, last_crawled_at
                FROM keywords
                WHERE id = $1
                """,
                keyword_id
            )
            raw_channels = kw["auto_share_channels"]
            if isinstance(raw_channels, str):
                try:
                    parsed_channels = json.loads(raw_channels)
                    if not isinstance(parsed_channels, list):
                        parsed_channels = []
                except json.JSONDecodeError:
                    parsed_channels = []
            else:
                parsed_channels = raw_channels or []

            return KeywordResponse(
                id=str(kw["id"]),
                text=kw["text"],
                status=kw["status"],
                notify_level=kw["notify_level"],
                auto_share_enabled=kw["auto_share_enabled"],
                auto_share_channels=parsed_channels,
                created_at=kw["created_at"],
                last_crawled_at=kw["last_crawled_at"]
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"키워드 생성 중 오류 발생: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="키워드 생성 중 오류가 발생했습니다"
        )


@router.delete("/{keyword_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_keyword(
    keyword_id: str,
    current_user: dict = Depends(get_current_user)
):
    """키워드 삭제"""
    try:
        # UUID 유효성 검사
        try:
            keyword_uuid = UUID(keyword_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="유효하지 않은 키워드 ID입니다"
            )
        
        async with get_db_connection() as conn:
            # 소유권 확인
            keyword = await conn.fetchrow(
                "SELECT id FROM keywords WHERE id = $1 AND user_id = $2",
                keyword_uuid, current_user["id"]
            )
            
            if not keyword:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="키워드를 찾을 수 없습니다"
                )
            
            # 소프트 삭제 (status 변경)
            result = await conn.execute(
                "UPDATE keywords SET status = 'archived' WHERE id = $1",
                keyword_uuid
            )
            
            # 업데이트 결과 확인
            if result == "UPDATE 0":
                logger.warning(f"키워드 삭제 실패: {keyword_id} - 업데이트된 행이 없습니다")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="키워드를 찾을 수 없습니다"
                )
            
            return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"키워드 삭제 중 오류 발생: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"키워드 삭제 중 오류가 발생했습니다: {str(e)}"
        )


