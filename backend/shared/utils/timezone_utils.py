"""시간대 유틸리티 함수

한국 시간(KST, UTC+9) 기준으로 시간을 처리하기 위한 유틸리티 함수들
"""
from datetime import datetime, timezone, timedelta

# 한국 시간대 (KST = UTC+9)
KST = timezone(timedelta(hours=9))


def utc_to_kst(utc_dt: datetime) -> datetime:
    """UTC datetime을 한국 시간(KST)으로 변환
    
    Args:
        utc_dt: UTC 시간대 정보가 포함된 datetime 객체
        
    Returns:
        KST 시간대로 변환된 datetime 객체
    """
    if utc_dt.tzinfo is None:
        # 시간대 정보가 없으면 UTC로 가정
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    elif utc_dt.tzinfo != timezone.utc:
        # UTC가 아니면 UTC로 변환 후 KST로 변환
        utc_dt = utc_dt.astimezone(timezone.utc)
    
    return utc_dt.astimezone(KST)


def now_kst() -> datetime:
    """현재 시간을 한국 시간(KST)으로 반환
    
    Returns:
        현재 시간(KST)
    """
    return datetime.now(timezone.utc).astimezone(KST)


def kst_to_iso_string(kst_dt: datetime) -> str:
    """KST datetime을 ISO 8601 형식 문자열로 변환
    
    Args:
        kst_dt: KST 시간대 정보가 포함된 datetime 객체
        
    Returns:
        ISO 8601 형식 문자열 (예: "2024-01-01T12:00:00+09:00")
    """
    if kst_dt.tzinfo is None:
        # 시간대 정보가 없으면 KST로 가정
        kst_dt = kst_dt.replace(tzinfo=KST)
    elif kst_dt.tzinfo != KST:
        # KST가 아니면 KST로 변환
        kst_dt = kst_dt.astimezone(KST)
    
    return kst_dt.isoformat()


def parse_date_kst(date_str: str) -> datetime.date:
    """날짜 문자열을 파싱하여 한국 시간 기준 날짜로 반환
    
    Args:
        date_str: YYYY-MM-DD 형식의 날짜 문자열
        
    Returns:
        한국 시간 기준 날짜
    """
    parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    return parsed_date

