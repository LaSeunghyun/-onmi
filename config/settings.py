"""공통 설정 모듈 프록시

실제 설정 정의는 `backend.shared.config.settings`에 위치한다.
이 모듈은 해당 설정을 재노출해 기존 `config.settings` 임포트 경로를 지원한다.
"""

from backend.shared.config.settings import Settings, settings

__all__ = ["Settings", "settings"]


