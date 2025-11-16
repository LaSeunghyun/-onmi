"""공통 설정 패키지 프록시

이 모듈은 `backend.shared.config` 패키지를 노출하여
기존 `config.settings` 임포트 경로를 유지하면서도
실제 설정 정의는 공유 모듈에 위치하도록 한다.
"""

from backend.shared.config.settings import Settings, settings

__all__ = ["Settings", "settings"]










