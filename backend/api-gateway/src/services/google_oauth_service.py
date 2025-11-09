"""Google OAuth 2.0 서비스"""
from typing import Dict, Optional
from google.auth.transport import requests
from google.oauth2 import id_token
import sys
import os
import logging

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../shared'))
from config.settings import settings

logger = logging.getLogger(__name__)


class GoogleOAuthService:
    """Google OAuth 2.0 인증 서비스"""
    
    def __init__(self):
        # 모바일 앱용 클라이언트 ID 목록 (우선순위: Android > iOS)
        self.client_ids = []
        if settings.google_oauth_client_id_android:
            self.client_ids.append(settings.google_oauth_client_id_android)
        if settings.google_oauth_client_id_ios:
            self.client_ids.append(settings.google_oauth_client_id_ios)
        # 웹용 클라이언트 ID (하위 호환성)
        if settings.google_oauth_client_id:
            self.client_ids.append(settings.google_oauth_client_id)
        
        if not self.client_ids:
            logger.warning("Google OAuth Client ID가 설정되지 않았습니다")
    
    def verify_id_token(self, token: str) -> Optional[Dict]:
        """Google ID 토큰 검증 및 사용자 정보 추출
        
        Android와 iOS 클라이언트 ID를 모두 시도하여 검증합니다.
        """
        if not self.client_ids:
            raise ValueError("Google OAuth Client ID가 설정되지 않았습니다")
        
        request_obj = requests.Request()
        last_error = None
        
        # 각 클라이언트 ID로 순차적으로 검증 시도
        for client_id in self.client_ids:
            try:
                # ID 토큰 검증
                idinfo = id_token.verify_oauth2_token(
                    token, 
                    request_obj, 
                    client_id
                )
                
                # 토큰 발급자 확인
                if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                    raise ValueError('Wrong issuer.')
                
                # 사용자 정보 추출
                return {
                    'sub': idinfo['sub'],  # Google 사용자 ID
                    'email': idinfo.get('email'),
                    'email_verified': idinfo.get('email_verified', False),
                    'name': idinfo.get('name'),
                    'picture': idinfo.get('picture'),
                    'given_name': idinfo.get('given_name'),
                    'family_name': idinfo.get('family_name'),
                }
            except ValueError as e:
                # 이 클라이언트 ID로 검증 실패, 다음 클라이언트 ID 시도
                last_error = e
                logger.debug(f"클라이언트 ID {client_id}로 검증 실패: {e}")
                continue
            except Exception as e:
                # 예상치 못한 오류 발생
                logger.error(f"Google ID 토큰 검증 중 오류 발생: {e}", exc_info=True)
                raise ValueError(f"Google ID 토큰 검증 중 오류가 발생했습니다: {str(e)}")
        
        # 모든 클라이언트 ID로 검증 실패
        logger.error(f"Google ID 토큰 검증 실패: 모든 클라이언트 ID로 검증 실패. 마지막 오류: {last_error}")
        raise ValueError(f"유효하지 않은 Google ID 토큰입니다: {str(last_error)}")

