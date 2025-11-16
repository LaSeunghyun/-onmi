"""admin@onmi.com 계정의 키워드 기사 수집 및 요약 생성 스크립트"""
import sys
import os
from pathlib import Path
import asyncio
from uuid import UUID
import logging
from datetime import datetime

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    # 출력 버퍼링 비활성화 (Windows에서는 재구성 불가)
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except AttributeError:
        pass

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend" / "shared"))
sys.path.insert(0, str(project_root / "backend" / "ingestor" / "src"))
sys.path.insert(0, str(project_root / "backend" / "nlp-service" / "src"))
sys.path.insert(0, str(project_root / "backend" / "api-gateway" / "src"))

import asyncpg
from datetime import datetime
from config.settings import settings
from collectors.google_cse_collector import GoogleCSECollector
from processors.deduplicator import Deduplicator
from sentiment.rule_based import RuleBasedSentimentAnalyzer
from services.summary_service import SummaryService
from services.cse_query_limit_service import CSEQueryLimitService
from collectors.google_cse_collector import CSEQueryLimitExceededError

quota_service = CSEQueryLimitService()

# 로깅 설정
log_dir = Path(__file__).parent / "backend" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "crawl_and_summarize.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


async def crawl_and_summarize_keyword(keyword_id: UUID, keyword_text: str, user_id: UUID):
    """키워드 크롤링 및 요약 생성"""
    logger.info(f"{'='*80}")
    logger.info(f"키워드: {keyword_text} (ID: {keyword_id})")
    logger.info(f"{'='*80}")
    
    # 크롤러 초기화
    cse_collector = GoogleCSECollector()
    deduplicator = Deduplicator()
    sentiment_analyzer = RuleBasedSentimentAnalyzer()
    
    # 데이터베이스 연결
    conn = await asyncpg.connect(
        settings.database_url,
        statement_cache_size=0
    )
    
    try:
        # 키워드별 할당량 확인
        logger.info(f"[1/6] Google CSE에서 기사 검색 중...")
        try:
            # 키워드별 할당량 조회
            keyword_quota_info = await quota_service.calculate_keyword_quota(user_id, keyword_id)
            keyword_remaining = keyword_quota_info.get('keyword_remaining', 0)
            keyword_quota = keyword_quota_info.get('keyword_quota', 0)
            
            logger.info(f"  키워드 할당량: {keyword_quota}개, 잔여량: {keyword_remaining}개")
            
            # 키워드별 할당량에 맞춰 max_results 조정 (Google CSE는 10개씩 반환하므로)
            # 할당량이 있으면 그만큼만 사용, 없으면 0개 반환
            if keyword_remaining <= 0:
                logger.warning(f"키워드 '{keyword_text}'의 쿼리 할당량이 없습니다. 건너뜁니다.")
                return 0
            
            # 할당량에 맞춰 최대 검색 수 결정 (10개씩 반환하므로 할당량 * 10개)
            max_results = min(100, keyword_remaining * 10)
            logger.info(f"  할당량 기반 최대 검색 수: {max_results}개 (쿼리 {keyword_remaining}개 사용)")
            
            all_articles = await cse_collector.search_by_keyword(
                keyword_text,
                date_range=None,
                max_results=max_results,
                user_id=user_id,
                keyword_id=keyword_id,
                quota_manager=quota_service
            )
        except CSEQueryLimitExceededError as exc:
            detail = getattr(exc, "detail", {})
            logger.warning(f"Google CSE 쿼리 제한 초과: {detail}")
            return 0
        
        logger.info(f"검색 완료: {len(all_articles)}개 기사 발견")
        
        # 중복 제거
        logger.info(f"[2/6] 중복 제거 중...")
        unique_articles = deduplicator.filter_duplicates(all_articles)
        
        # 최소 1개는 보장 (검색 결과가 있으면 최소 1개는 유지)
        if len(all_articles) > 0 and len(unique_articles) == 0:
            logger.warning(f"모든 기사가 중복으로 판단됨. 첫 번째 기사를 유지합니다.")
            unique_articles = [all_articles[0]]
        
        logger.info(f"중복 제거 완료: {len(unique_articles)}개 기사 (제거됨: {len(all_articles) - len(unique_articles)}개)")
        
        # 키워드 매칭 필터링 (전체 키워드 우선 매칭, 주요 단어 모두 포함 확인)
        logger.info(f"[3/6] 키워드 매칭 필터링 중...")
        keyword_lower = keyword_text.lower().strip()
        # 키워드를 단어로 분리 (길이가 1보다 큰 단어만)
        keyword_words = [word.strip() for word in keyword_lower.split() if len(word.strip()) > 1]
        
        matched_articles = []
        for article in unique_articles:
            title = str(article.get('title', '')).lower()
            snippet = str(article.get('snippet', '')).lower()
            combined_text = f"{title} {snippet}"
            
            # 1. 전체 키워드가 포함되면 매칭 (최우선)
            if keyword_lower in combined_text:
                matched_articles.append(article)
                continue
            
            # 2. 키워드가 여러 단어로 구성된 경우, 모든 주요 단어가 포함되어야 매칭
            if len(keyword_words) > 1:
                # 모든 주요 단어가 포함되어야 함
                if all(word in combined_text for word in keyword_words):
                    matched_articles.append(article)
            # 3. 키워드가 단일 단어인 경우, 전체 키워드만 매칭 (이미 위에서 처리됨)
        
        # 매칭된 기사가 없으면 전체 키워드 매칭 없이도 일부 기사는 유지
        if len(matched_articles) == 0 and len(unique_articles) > 0:
            logger.warning(f"키워드 매칭 결과가 없습니다. 상위 10개 기사를 유지합니다.")
            matched_articles = unique_articles[:10]
        
        logger.info(f"키워드 매칭 완료: {len(matched_articles)}개 기사 (필터링됨: {len(unique_articles) - len(matched_articles)}개)")
        
        # 기사 저장
        logger.info(f"[4/6] 기사 저장 중...")
        saved_count = 0
        
        for article in matched_articles:
            try:
                url = str(article.get('url', ''))
                title = str(article.get('title', ''))
                snippet = str(article.get('snippet', ''))
                source = str(article.get('source', '')) if article.get('source') else 'Unknown'
                published_at = article.get('published_at')
                lang = str(article.get('lang', 'ko'))
                
                if not url:
                    continue
                
                # 기사 저장
                article_id = await conn.fetchval(
                    """
                    INSERT INTO articles (url, title, snippet, source, published_at, lang)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (url) DO UPDATE SET title = EXCLUDED.title
                    RETURNING id
                    """,
                    url, title, snippet, source, published_at, lang
                )
                
                # 키워드-기사 매핑 저장
                await conn.execute(
                    """
                    INSERT INTO keyword_articles (keyword_id, article_id, match_score, match_type)
                    VALUES ($1, $2, 1.0, 'exact')
                    ON CONFLICT (keyword_id, article_id) DO NOTHING
                    """,
                    keyword_id, article_id
                )
                
                # 감성 분석 수행
                sentiment_result = sentiment_analyzer.analyze(title, snippet)
                
                # 감성 분석 결과 저장
                import json
                rationale_value = sentiment_result['rationale']
                if isinstance(rationale_value, dict):
                    rationale_value = json.dumps(rationale_value, ensure_ascii=False)
                
                await conn.execute(
                    """
                    INSERT INTO sentiments (article_id, label, score, rationale, model_ver)
                    VALUES ($1, $2, $3, $4::jsonb, 'rule-based-v1')
                    ON CONFLICT (article_id) DO UPDATE SET
                        label = EXCLUDED.label,
                        score = EXCLUDED.score,
                        rationale = EXCLUDED.rationale
                    """,
                    article_id,
                    sentiment_result['label'],
                    sentiment_result['score'],
                    rationale_value
                )
                
                saved_count += 1
                if saved_count % 10 == 0:
                    logger.info(f"  저장 진행 중... {saved_count}개 저장 완료")
                
            except Exception as e:
                logger.warning(f"기사 저장 오류: {e}")
                continue
        
        # 키워드의 last_crawled_at 업데이트
        await conn.execute(
            "UPDATE keywords SET last_crawled_at = NOW() WHERE id = $1",
            keyword_id
        )
        
        logger.info(f"저장 완료: {saved_count}개 기사")
        
        # 요약 생성
        if saved_count > 0:
            logger.info(f"[5/6] 키워드별 요약 생성 중...")
            try:
                summary_service = SummaryService()
                summary_result = await summary_service.generate_keyword_summary(
                    keyword_id,
                    user_id
                )
                logger.info(f"요약 생성 완료!")
                logger.info(f"  세션 ID: {summary_result['session_id']}")
                logger.info(f"  기사 수: {summary_result['articles_count']}개")
                logger.info(f"  요약 미리보기: {summary_result['summary_text'][:150]}...")
            except Exception as e:
                logger.error(f"요약 생성 실패: {e}", exc_info=True)
        else:
            logger.info(f"[5/6] 저장된 기사가 없어 요약을 생성하지 않습니다.")
        
        logger.info(f"[6/6] 키워드 처리 완료!")
        logger.info(f"  총 검색: {len(all_articles)}개 → 중복 제거: {len(unique_articles)}개 → 매칭: {len(matched_articles)}개 → 저장: {saved_count}개")
        
        return saved_count
        
    finally:
        await conn.close()


async def main():
    """메인 함수"""
    logger.info(f"{'='*80}")
    logger.info(f"admin@onmi.com 계정 키워드 기사 수집 및 요약 생성")
    logger.info(f"{'='*80}")
    logger.info(f"시작 시간: {datetime.now()}")
    logger.info(f"로그 파일: {log_file}")
    
    # 데이터베이스 연결
    conn = await asyncpg.connect(
        settings.database_url,
        statement_cache_size=0
    )
    
    try:
        # 사용자 ID 조회
        user = await conn.fetchrow(
            "SELECT id, email FROM users WHERE email = $1",
            "admin@onmi.com"
        )
        
        if not user:
            logger.error("admin@onmi.com 계정을 찾을 수 없습니다.")
            return
        
        user_id = UUID(str(user['id']))
        logger.info(f"사용자 확인: {user['email']} (ID: {user_id})")
        
        # 활성 키워드 조회
        keywords = await conn.fetch(
            """
            SELECT id, text, status
            FROM keywords
            WHERE user_id = $1 AND status = 'active'
            ORDER BY created_at DESC
            """,
            user_id
        )
        
        if not keywords:
            logger.warning("등록된 활성 키워드가 없습니다.")
            return
        
        logger.info(f"{len(keywords)}개의 활성 키워드를 찾았습니다:")
        for kw in keywords:
            logger.info(f"  - {kw['text']} (ID: {kw['id']})")
        
        # 각 키워드별 크롤링 및 요약 생성
        total_saved = 0
        for keyword in keywords:
            keyword_id = UUID(str(keyword['id']))
            keyword_text = keyword['text']
            
            try:
                saved = await crawl_and_summarize_keyword(
                    keyword_id,
                    keyword_text,
                    user_id
                )
                total_saved += saved
            except Exception as e:
                logger.error(f"키워드 '{keyword_text}' 처리 중 오류: {e}", exc_info=True)
                continue
        
        # 일일 요약 생성
        logger.info(f"{'='*80}")
        logger.info(f"일일 요약 생성")
        logger.info(f"{'='*80}")
        
        if total_saved > 0:
            try:
                logger.info(f"[1/2] 일일 요약 생성 중...")
                summary_service = SummaryService()
                daily_result = await summary_service.generate_daily_summary(user_id)
                logger.info(f"일일 요약 생성 완료!")
                logger.info(f"  세션 ID: {daily_result['session_id']}")
                logger.info(f"  기사 수: {daily_result['articles_count']}개")
                logger.info(f"  요약 미리보기: {daily_result['summary_text'][:200]}...")
            except Exception as e:
                logger.error(f"일일 요약 생성 실패: {e}", exc_info=True)
        else:
            logger.warning(f"수집된 기사가 없어 일일 요약을 생성하지 않습니다.")
        
        logger.info(f"{'='*80}")
        logger.info(f"모든 작업 완료!")
        logger.info(f"  총 저장된 기사: {total_saved}개")
        logger.info(f"  완료 시간: {datetime.now()}")
        logger.info(f"{'='*80}")
        
    finally:
        await conn.close()


if __name__ == "__main__":
    # Windows에서 asyncio 이벤트 루프 정책 설정
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n작업이 사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

