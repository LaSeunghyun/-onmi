"""피드백 분석 서비스"""
from typing import Dict, Any, Optional, List
from uuid import UUID
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../shared'))
from ..repositories import (
    FeedbackRepository,
    PreferenceRepository,
    SummarySessionRepository
)


class FeedbackService:
    """피드백 분석 및 개선 서비스"""
    
    async def analyze_keyword_feedback(
        self,
        keyword_id: UUID,
        user_id: UUID
    ) -> Dict[str, Any]:
        """키워드별 피드백 통계 분석"""
        stats = await FeedbackRepository.aggregate_by_keyword(keyword_id, user_id)
        
        # 추가 분석
        analysis = {
            'stats': stats,
            'satisfaction_level': self._calculate_satisfaction_level(stats),
            'recommendations': self._generate_recommendations(stats)
        }
        
        return analysis
    
    async def analyze_user_feedback(self, user_id: UUID) -> Dict[str, Any]:
        """사용자별 피드백 통계 분석"""
        stats = await FeedbackRepository.aggregate_by_user(user_id)
        
        # 추가 분석
        analysis = {
            'stats': stats,
            'satisfaction_level': self._calculate_satisfaction_level(stats),
            'recommendations': self._generate_recommendations(stats)
        }
        
        return analysis
    
    def _calculate_satisfaction_level(self, stats: Dict[str, Any]) -> str:
        """만족도 수준 계산"""
        avg_rating = stats.get('avg_rating', 0.0)
        
        if avg_rating >= 4.0:
            return 'high'
        elif avg_rating >= 3.0:
            return 'medium'
        else:
            return 'low'
    
    def _generate_recommendations(self, stats: Dict[str, Any]) -> List[str]:
        """피드백 기반 개선 권장사항 생성"""
        recommendations = []
        avg_rating = stats.get('avg_rating', 0.0)
        negative_count = stats.get('negative_count', 0)
        total_count = stats.get('total_count', 0)
        
        if total_count == 0:
            recommendations.append("아직 피드백이 없습니다. 요약을 확인하고 피드백을 남겨주세요.")
            return recommendations
        
        if avg_rating < 3.0:
            recommendations.append("요약의 상세 수준을 높이는 것을 고려해보세요.")
        
        if negative_count > total_count * 0.3:
            recommendations.append("요약의 정확성을 개선할 필요가 있습니다.")
        
        if avg_rating >= 4.0:
            recommendations.append("현재 요약 품질이 좋습니다. 현재 설정을 유지하세요.")
        
        return recommendations
    
    async def update_preferences_from_feedback(
        self,
        user_id: UUID,
        keyword_id: Optional[UUID],
        rating: int
    ) -> Dict[str, Any]:
        """피드백 기반 선호도 업데이트"""
        detail_level = self._derive_detail_level(rating)
        
        await PreferenceRepository.upsert(
            user_id=user_id,
            keyword_id=keyword_id,
            preferred_detail_level=detail_level
        )
        
        return {
            'detail_level': detail_level,
            'updated': True
        }
    
    def _derive_detail_level(self, rating: int) -> str:
        """평점 기반 상세 수준 결정"""
        if rating >= 4:
            return 'maintain_current_detail'
        elif rating == 3:
            return 'tweak_for_more_context'
        else:
            return 'increase_detail'
    
    async def find_low_satisfaction_patterns(
        self,
        user_id: UUID,
        threshold: float = 3.0
    ) -> List[Dict[str, Any]]:
        """만족도가 낮은 패턴 분석"""
        # TODO: 실제 구현 필요
        # 키워드별 평균 평점이 threshold 미만인 경우를 찾아서 패턴 분석
        patterns = []
        return patterns

