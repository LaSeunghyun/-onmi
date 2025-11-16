"""규칙 기반 감성 분석기"""
from typing import Dict, List, Tuple
import re


class RuleBasedSentimentAnalyzer:
    """규칙 기반 감성 분석 클래스"""
    
    def __init__(self):
        # 긍정 단어 사전 (가중치 포함)
        self.positive_words = {
            '최고': 2.0, '훌륭': 1.8, '좋': 1.5, '성공': 1.8, '혁신': 1.7,
            '성장': 1.6, '향상': 1.5, '개선': 1.5, '긍정': 1.6, '낙관': 1.5,
            '기대': 1.4, '희망': 1.5, '승리': 1.7, '돌파': 1.6, '상승': 1.5,
            '증가': 1.4, '확대': 1.5, '발전': 1.6, '진보': 1.5, '혁명': 1.8
        }
        
        # 부정 단어 사전 (가중치 포함)
        self.negative_words = {
            '논란': 1.8, '사기': 2.0, '부정': 1.7, '비리': 1.9, '의혹': 1.8,
            '문제': 1.5, '위기': 1.7, '실패': 1.8, '하락': 1.6, '감소': 1.5,
            '축소': 1.5, '후퇴': 1.6, '침체': 1.7, '불안': 1.6, '우려': 1.5,
            '경고': 1.6, '위험': 1.7, '손실': 1.6, '피해': 1.7, '사고': 1.8
        }
        
        # 부정어
        self.negation_words = ['안', '않', '못', '없', '비', '불', '미']
    
    def preprocess(self, text: str) -> str:
        """텍스트 전처리"""
        # 이모지 제거
        text = re.sub(r'[^\w\s가-힣]', ' ', text)
        # 연속 공백 제거
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def analyze(self, title: str, content: str = "") -> Dict:
        """감성 분석 수행"""
        title = self.preprocess(title)
        content = self.preprocess(content)
        
        # 제목 가중치 (1.5배)
        title_score = self._calculate_score(title) * 1.5
        content_score = self._calculate_score(content)
        
        # 전체 점수 계산
        total_score = title_score + content_score
        
        # 부정문 처리
        if self._has_negation(title, content):
            total_score *= -0.7  # 부정문은 점수 감소
        
        # 정규화 (0~1 범위)
        normalized_score = self._normalize_score(total_score)
        
        # 레이블 결정
        if normalized_score >= 0.6:
            label = 'positive'
        elif normalized_score <= 0.4:
            label = 'negative'
        else:
            label = 'neutral'
        
        # 근거 토큰 추출
        rationale_tokens = self._extract_rationale_tokens(title, content)
        
        return {
            'label': label,
            'score': normalized_score,
            'rationale': {
                'tokens': rationale_tokens,
                'title_score': title_score,
                'content_score': content_score
            }
        }
    
    def _calculate_score(self, text: str) -> float:
        """텍스트의 감성 점수 계산"""
        score = 0.0
        words = text.lower().split()
        
        for word in words:
            # 긍정 단어 확인
            for pos_word, weight in self.positive_words.items():
                if pos_word in word:
                    score += weight
                    break
            
            # 부정 단어 확인
            for neg_word, weight in self.negative_words.items():
                if neg_word in word:
                    score -= weight
                    break
        
        return score
    
    def _has_negation(self, title: str, content: str) -> bool:
        """부정문 포함 여부 확인"""
        text = (title + " " + content).lower()
        for neg_word in self.negation_words:
            if neg_word in text:
                return True
        return False
    
    def _normalize_score(self, score: float) -> float:
        """점수를 0~1 범위로 정규화"""
        # 시그모이드 함수 사용
        import math
        normalized = 1 / (1 + math.exp(-score / 10))
        return max(0.0, min(1.0, normalized))
    
    def _extract_rationale_tokens(self, title: str, content: str, top_n: int = 5) -> List[str]:
        """근거 토큰 추출 (상위 N개)"""
        text = (title + " " + content).lower()
        tokens = []
        
        # 긍정/부정 단어 찾기
        for word, weight in sorted(self.positive_words.items(), key=lambda x: x[1], reverse=True):
            if word in text:
                tokens.append(f"+{word}")
        
        for word, weight in sorted(self.negative_words.items(), key=lambda x: x[1], reverse=True):
            if word in text:
                tokens.append(f"-{word}")
        
        return tokens[:top_n]













