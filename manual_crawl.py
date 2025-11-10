"""수동 크롤링 스크립트 - 특정 키워드 수집"""
import sys
import os
from pathlib import Path
import asyncio
import json
from datetime import datetime

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# 출력 버퍼링 비활성화 (실시간 로그 출력)
sys.stdout.reconfigure(line_buffering=True)

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend" / "shared"))
sys.path.insert(0, str(project_root / "backend" / "ingestor" / "src"))
sys.path.insert(0, str(project_root / "backend" / "nlp-service" / "src"))

import asyncpg
from uuid import UUID
from config.settings import settings
from collectors.google_cse_collector import GoogleCSECollector
from processors.deduplicator import Deduplicator
from sentiment.rule_based import RuleBasedSentimentAnalyzer

# SummaryService import를 위한 경로 추가
sys.path.insert(0, str(project_root / "backend" / "api-gateway" / "src"))
try:
    from services.summary_service import SummaryService
    SUMMARY_SERVICE_AVAILABLE = True
except ImportError as e:
    SUMMARY_SERVICE_AVAILABLE = False
    print(f"경고: SummaryService를 import할 수 없습니다. 요약 생성 기능이 비활성화됩니다.")
    print(f"  오류: {e}")

from services.cse_query_limit_service import CSEQueryLimitService
from collectors.google_cse_collector import CSEQueryLimitExceededError

quota_service = CSEQueryLimitService()


async def crawl_keyword(keyword_id: str, keyword_text: str):
    """특정 키워드 크롤링"""
    print(f"키워드 수집 시작: {keyword_text} (ID: {keyword_id})")
    
    # 크롤러 초기화
    cse_collector = GoogleCSECollector()
    deduplicator = Deduplicator()
    sentiment_analyzer = RuleBasedSentimentAnalyzer()
    
    # 데이터베이스 연결 (Supabase pgbouncer 호환을 위해 statement_cache_size=0 설정)
    conn = await asyncpg.connect(
        settings.database_url,
        statement_cache_size=0  # pgbouncer 호환성
    )
    
    try:
        # 키워드 소유자 조회
        keyword_uuid = UUID(keyword_id)
        keyword_row = await conn.fetchrow(
            "SELECT user_id FROM keywords WHERE id = $1",
            keyword_uuid
        )
        owner_id = keyword_row['user_id'] if keyword_row else None

        # Google CSE로 키워드 검색
        print("Google CSE에서 기사 검색 중...")
        sys.stdout.flush()
        try:
            all_articles = await cse_collector.search_by_keyword(
                keyword_text,
                date_range=None,  # 전체 기간 검색
                max_results=100,
                user_id=owner_id,
                keyword_id=keyword_uuid,
                quota_manager=quota_service if owner_id else None
            )
        except CSEQueryLimitExceededError as exc:
            detail = getattr(exc, "detail", {})
            print(f"⚠️  Google CSE 쿼리 제한 초과: {detail}")
            return
        print(f"✅ 검색 완료: {len(all_articles)}개 기사 발견")
        sys.stdout.flush()
        
        # 중복 제거
        print("중복 제거 중...")
        sys.stdout.flush()
        unique_articles = deduplicator.filter_duplicates(all_articles)
        print(f"✅ 중복 제거 완료: {len(unique_articles)}개 기사 (제거됨: {len(all_articles) - len(unique_articles)}개)")
        sys.stdout.flush()
        
        # 키워드 매칭 필터링 (제목이나 snippet에 키워드가 포함된 기사만 저장)
        print(f"키워드 '{keyword_text}' 매칭 필터링 중...")
        sys.stdout.flush()
        keyword_lower = keyword_text.lower()
        matched_articles = []
        filtered_count = 0
        
        for article in unique_articles:
            title = str(article.get('title', '')).lower()
            snippet = str(article.get('snippet', '')).lower()
            
            # 제목이나 snippet에 키워드가 포함되어 있는지 확인
            if keyword_lower in title or keyword_lower in snippet:
                matched_articles.append(article)
            else:
                filtered_count += 1
        
        print(f"✅ 키워드 매칭 완료: {len(matched_articles)}개 기사 (필터링됨: {filtered_count}개)")
        sys.stdout.flush()
        
        # article 객체 정리 (필요한 필드만 남기고 타입 보장)
        print("기사 데이터 정리 중...")
        sys.stdout.flush()
        cleaned_articles = []
        for idx, article in enumerate(matched_articles):
            # 첫 번째 기사 디버깅
            if idx == 0:
                print(f"\n[디버깅] 원본 article 객체 (첫 번째):")
                print(f"  Keys: {list(article.keys())}")
                for key, value in article.items():
                    value_str = str(value)
                    if len(value_str) > 150:
                        value_str = value_str[:150] + "..."
                    print(f"  {key}: {type(value).__name__} = {value_str}")
                print()
            # source 필드 안전하게 추출 (dict인 경우 명시적으로 처리)
            source_raw = article.get('source', '')
            if isinstance(source_raw, dict):
                source = 'Unknown'
                if idx == 0:
                    print(f"  [경고] Source가 dict 타입입니다: {type(source_raw).__name__}, 'Unknown'으로 변환")
            elif isinstance(source_raw, str):
                source = source_raw if source_raw else 'Unknown'
            elif source_raw:
                source = str(source_raw)
                if idx == 0:
                    print(f"  [경고] Source 타입 변환: {type(source_raw).__name__} -> str")
            else:
                source = 'Unknown'
            
            # snippet 필드 안전하게 추출
            snippet_raw = article.get('snippet', '')
            if isinstance(snippet_raw, dict):
                snippet = ''
                if idx == 0:
                    print(f"  [경고] Snippet이 dict 타입입니다: {type(snippet_raw).__name__}, 빈 문자열로 변환")
            elif isinstance(snippet_raw, str):
                snippet = snippet_raw
            elif snippet_raw:
                snippet = str(snippet_raw)
            else:
                snippet = ''
            
            # 최종 타입 검증 (cleaned dict에 넣기 전)
            if not isinstance(source, str):
                source = 'Unknown'
            if not isinstance(snippet, str):
                snippet = ''
            
            cleaned = {
                'url': str(article.get('url', '')) if article.get('url') else '',
                'title': str(article.get('title', '')) if article.get('title') else '',
                'snippet': snippet,
                'source': source,
                'published_at': article.get('published_at'),
                'lang': str(article.get('lang', 'ko')) if article.get('lang') else 'ko'
            }
            
            # cleaned dict의 타입 최종 검증
            if not isinstance(cleaned['source'], str):
                cleaned['source'] = 'Unknown'
            if not isinstance(cleaned['snippet'], str):
                cleaned['snippet'] = ''
            
            cleaned_articles.append(cleaned)
        
        # 데이터베이스에 저장
        saved_count = 0
        total_count = len(cleaned_articles)
        print(f"\n기사 저장 시작: 총 {total_count}개 기사")
        sys.stdout.flush()
        
        for idx, article in enumerate(cleaned_articles):
            try:
                # 진행 상황 출력 (10개마다)
                if (idx + 1) % 10 == 0 or idx == 0:
                    print(f"  진행 중... {idx + 1}/{total_count} ({saved_count}개 저장 완료)")
                    sys.stdout.flush()
                # 필드 추출 (이미 정리된 article 객체 사용)
                url_raw = article.get('url', '')
                title_raw = article.get('title', '')
                snippet_raw = article.get('snippet', '')
                source_raw = article.get('source', '')
                published_at = article.get('published_at')
                lang_raw = article.get('lang', 'ko')
                
                # 타입 안전성 검증 및 변환 (DB 쿼리 전 최종 검증)
                # url 검증
                if isinstance(url_raw, str) and url_raw:
                    url = url_raw
                else:
                    if idx < 3:  # 처음 3개만 상세 로그
                        print(f"  [기사 {idx+1}] URL 타입 오류: {type(url_raw).__name__} = {str(url_raw)[:100]}")
                    continue
                
                # title 검증
                if isinstance(title_raw, str):
                    title = title_raw if title_raw else ''
                elif title_raw:
                    title = str(title_raw)
                    if idx < 3:
                        print(f"  [기사 {idx+1}] Title 타입 변환: {type(title_raw).__name__} -> str")
                else:
                    title = ''
                
                # snippet 검증
                if isinstance(snippet_raw, str):
                    snippet = snippet_raw
                elif isinstance(snippet_raw, dict):
                    snippet = ''
                    if idx < 3:
                        print(f"  [기사 {idx+1}] Snippet이 dict 타입: {type(snippet_raw).__name__}, 빈 문자열로 변환")
                elif snippet_raw:
                    snippet = str(snippet_raw)
                    if idx < 3:
                        print(f"  [기사 {idx+1}] Snippet 타입 변환: {type(snippet_raw).__name__} -> str")
                else:
                    snippet = ''
                
                # source 검증 (dict인 경우 명시적으로 처리)
                if isinstance(source_raw, str):
                    source = source_raw if source_raw else 'Unknown'
                elif isinstance(source_raw, dict):
                    source = 'Unknown'
                    if idx < 3:
                        print(f"  [기사 {idx+1}] Source가 dict 타입: {type(source_raw).__name__} = {str(source_raw)[:100]}, 'Unknown'으로 변환")
                elif source_raw:
                    source = str(source_raw)
                    if idx < 3:
                        print(f"  [기사 {idx+1}] Source 타입 변환: {type(source_raw).__name__} -> str")
                else:
                    source = 'Unknown'
                
                # lang 검증
                if isinstance(lang_raw, str):
                    lang = lang_raw if lang_raw else 'ko'
                else:
                    lang = 'ko'
                    if idx < 3:
                        print(f"  [기사 {idx+1}] Lang 타입 변환: {type(lang_raw).__name__} -> 'ko'")
                
                # published_at 검증 (None이거나 datetime/timestamp 타입이어야 함)
                if published_at is not None and not isinstance(published_at, (datetime, type(None))):
                    # 문자열인 경우 datetime으로 변환 시도 (표준 라이브러리만 사용)
                    if isinstance(published_at, str):
                        try:
                            # ISO 형식 문자열 파싱 시도
                            published_at = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                        except (ValueError, AttributeError):
                            try:
                                # 다른 일반적인 형식 시도
                                published_at = datetime.strptime(published_at, '%Y-%m-%d %H:%M:%S')
                            except (ValueError, AttributeError):
                                published_at = None
                    else:
                        published_at = None
                
                # DB 쿼리 전 최종 타입 검증
                if not isinstance(url, str) or not url:
                    continue
                if not isinstance(title, str):
                    title = str(title) if title else ''
                if not isinstance(snippet, str):
                    snippet = str(snippet) if snippet else ''
                if not isinstance(source, str):
                    source = 'Unknown'
                if not isinstance(lang, str):
                    lang = 'ko'
                
                # 첫 번째 기사만 DB 쿼리 전 값 확인
                if idx == 0:
                    print(f"\n[디버깅] DB 쿼리 전 변수 값:")
                    print(f"  url: {type(url).__name__} = {url[:50]}")
                    print(f"  title: {type(title).__name__} = {title[:50]}")
                    print(f"  snippet: {type(snippet).__name__} = {snippet[:50]}")
                    print(f"  source: {type(source).__name__} = {source}")
                    print(f"  published_at: {type(published_at).__name__} = {published_at}")
                    print(f"  lang: {type(lang).__name__} = {lang}")
                
                # 기사 저장 또는 조회
                article_id = await conn.fetchval(
                    """
                    INSERT INTO articles (url, title, snippet, source, published_at, lang)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (url) DO UPDATE SET title = EXCLUDED.title
                    RETURNING id
                    """,
                    url,
                    title,
                    snippet,
                    source,
                    published_at,
                    lang
                )
                
                # 키워드-기사 매핑 저장
                await conn.execute(
                    """
                    INSERT INTO keyword_articles (keyword_id, article_id, match_score, match_type)
                    VALUES ($1, $2, 1.0, 'exact')
                    ON CONFLICT (keyword_id, article_id) DO NOTHING
                    """,
                    keyword_uuid, article_id
                )
                
                # 감성 분석 수행
                sentiment_result = sentiment_analyzer.analyze(
                    article['title'],
                    article.get('snippet', '')
                )
                
                # 감성 분석 결과 저장
                # rationale이 dict인 경우 JSONB로 변환
                rationale_value = sentiment_result['rationale']
                if isinstance(rationale_value, dict):
                    # dict를 JSON 문자열로 변환 (asyncpg가 JSONB로 자동 변환)
                    rationale_value = json.dumps(rationale_value, ensure_ascii=False)
                elif not isinstance(rationale_value, (str, type(None))):
                    # 다른 타입인 경우 문자열로 변환 시도
                    rationale_value = json.dumps(rationale_value, ensure_ascii=False) if rationale_value else None
                
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
                # 10개마다 또는 마지막 기사일 때 진행 상황 출력
                if saved_count % 10 == 0 or idx == len(cleaned_articles) - 1:
                    print(f"  저장 완료: {saved_count}개 (진행률: {idx + 1}/{total_count})")
                    sys.stdout.flush()
            
            except Exception as e:
                # 상세한 오류 정보 출력
                error_msg = str(e)
                print(f"\n[기사 저장 오류 {idx+1}/{total_count}]")
                print(f"  오류 메시지: {error_msg}")
                print(f"  오류 타입: {type(e).__name__}")
                sys.stdout.flush()
                
                # 필드별 타입 및 값 정보 출력
                try:
                    print(f"  필드 정보:")
                    print(f"    url: {type(article.get('url')).__name__} = {str(article.get('url', ''))[:50]}")
                    print(f"    title: {type(article.get('title')).__name__} = {str(article.get('title', ''))[:50]}")
                    print(f"    snippet: {type(article.get('snippet')).__name__} = {str(article.get('snippet', ''))[:50]}")
                    source_val = article.get('source', '')
                    print(f"    source: {type(source_val).__name__} = {str(source_val)[:100]}")
                    print(f"    published_at: {type(article.get('published_at')).__name__} = {article.get('published_at')}")
                    print(f"    lang: {type(article.get('lang')).__name__} = {article.get('lang', '')}")
                except Exception as debug_error:
                    print(f"  디버깅 정보 추출 실패: {debug_error}")
                
                # 스택 트레이스 출력 (처음 3개 기사만)
                if idx < 3:
                    import traceback
                    print(f"  스택 트레이스:")
                    traceback.print_exc()
                continue
        
        # 키워드의 last_crawled_at 업데이트
        await conn.execute(
            "UPDATE keywords SET last_crawled_at = NOW() WHERE id = $1",
            keyword_uuid
        )
        
        print(f"\n{'='*60}")
        print(f"키워드 수집 완료: {keyword_text}")
        print(f"{'='*60}")
        print(f"  📊 통계:")
        print(f"    - 총 검색된 기사: {len(all_articles)}개")
        print(f"    - 중복 제거 후: {len(unique_articles)}개")
        print(f"    - 키워드 매칭 필터링 후: {len(matched_articles)}개")
        print(f"    - 최종 저장된 기사: {saved_count}개")
        sys.stdout.flush()
        
        # 요약 생성 여부 확인
        print(f"\n요약 생성 조건 확인:")
        print(f"  - 저장된 기사 수: {saved_count}개")
        print(f"  - SUMMARY_SERVICE_AVAILABLE: {SUMMARY_SERVICE_AVAILABLE}")
        sys.stdout.flush()
        
        # 키워드별 요약 생성 (저장된 기사가 있는 경우에만)
        if saved_count > 0 and SUMMARY_SERVICE_AVAILABLE:
            try:
                print(f"\n📝 키워드별 요약 생성 시작...")
                sys.stdout.flush()
                
                # 사용자 ID 조회
                print(f"  [1/5] 사용자 ID 조회 중...")
                sys.stdout.flush()
                user_row = await conn.fetchrow(
                    "SELECT user_id FROM keywords WHERE id = $1",
                    keyword_uuid
                )
                if user_row:
                    user_id = user_row['user_id']
                    print(f"  ✅ 사용자 ID 조회 완료: {user_id}")
                    sys.stdout.flush()
                    
                    print(f"  [2/5] SummaryService 초기화 중...")
                    sys.stdout.flush()
                    summary_service = SummaryService()
                    print(f"  ✅ SummaryService 초기화 완료")
                    sys.stdout.flush()
                    
                    print(f"  [3/5] 키워드별 요약 생성 실행 중...")
                    print(f"    - 키워드 ID: {keyword_id}")
                    print(f"    - 사용자 ID: {user_id}")
                    sys.stdout.flush()
                    
                    summary_result = await summary_service.generate_keyword_summary(
                        keyword_uuid,
                        UUID(str(user_id))
                    )
                    
                    print(f"  [4/5] 요약 생성 완료!")
                    print(f"    - 기반 기사 수: {summary_result['articles_count']}개")
                    print(f"    - 요약 세션 ID: {summary_result['session_id']}")
                    sys.stdout.flush()
                    
                    print(f"  [5/5] 요약 정보:")
                    print(f"    - 프론트엔드에서 /summaries/keywords/{keyword_id}로 조회 가능")
                    print(f"  ✅ 모든 작업 완료!")
                    sys.stdout.flush()
                else:
                    print(f"  ⚠️ 사용자 정보를 찾을 수 없어 요약을 생성하지 않습니다.")
                    sys.stdout.flush()
            except Exception as e:
                print(f"\n  ❌ 요약 생성 중 오류 발생!")
                print(f"  오류 타입: {type(e).__name__}")
                print(f"  오류 메시지: {str(e)}")
                import traceback
                print(f"\n  스택 트레이스:")
                traceback.print_exc()
                sys.stdout.flush()
        elif saved_count > 0 and not SUMMARY_SERVICE_AVAILABLE:
            print(f"\n⚠️ 요약 생성 기능이 비활성화되어 있습니다.")
            print(f"  (SummaryService를 import할 수 없습니다)")
            sys.stdout.flush()
        else:
            print(f"\n⚠️ 저장된 기사가 없어 요약을 생성하지 않습니다.")
            sys.stdout.flush()
        
        print(f"\n{'='*60}")
        print(f"크롤링 작업 최종 완료")
        print(f"{'='*60}")
        sys.stdout.flush()
        
        return saved_count
    
    finally:
        print("데이터베이스 연결 종료 중...")
        sys.stdout.flush()
        await conn.close()
        print("데이터베이스 연결 종료 완료")
        sys.stdout.flush()


async def generate_summary_from_existing_articles(keyword_id: str):
    """데이터베이스에 저장된 기사로부터 요약 생성"""
    print(f"\n{'='*60}")
    print(f"기존 기사 기반 요약 생성 시작")
    print(f"{'='*60}")
    print(f"키워드 ID: {keyword_id}")
    sys.stdout.flush()
    
    # 데이터베이스 연결
    conn = await asyncpg.connect(
        settings.database_url,
        statement_cache_size=0
    )
    
    try:
        # 사용자 ID 조회
        print(f"\n[1/4] 사용자 ID 조회 중...")
        sys.stdout.flush()
        user_row = await conn.fetchrow(
            "SELECT user_id FROM keywords WHERE id = $1",
            keyword_id
        )
        
        if not user_row:
            print(f"  ❌ 키워드를 찾을 수 없습니다.")
            return None
        
        user_id = user_row['user_id']
        print(f"  ✅ 사용자 ID: {user_id}")
        sys.stdout.flush()
        
        # 기사 개수 확인
        print(f"\n[2/4] 저장된 기사 조회 중...")
        sys.stdout.flush()
        article_count = await conn.fetchval(
            """
            SELECT COUNT(DISTINCT a.id)
            FROM articles a
            INNER JOIN keyword_articles ka ON a.id = ka.article_id
            WHERE ka.keyword_id = $1
            """,
            keyword_id
        )
        print(f"  ✅ 저장된 기사 수: {article_count}개")
        sys.stdout.flush()
        
        if article_count == 0:
            print(f"  ⚠️ 저장된 기사가 없어 요약을 생성할 수 없습니다.")
            return None
        
        # SummaryService로 요약 생성
        if not SUMMARY_SERVICE_AVAILABLE:
            print(f"  ❌ SummaryService를 사용할 수 없습니다.")
            return None
        
        print(f"\n[3/4] SummaryService로 요약 생성 중...")
        sys.stdout.flush()
        summary_service = SummaryService()
        
        summary_result = await summary_service.generate_keyword_summary(
            UUID(keyword_id),
            UUID(str(user_id))
        )
        
        print(f"  ✅ 요약 생성 완료!")
        print(f"    - 기반 기사 수: {summary_result['articles_count']}개")
        print(f"    - 요약 세션 ID: {summary_result['session_id']}")
        sys.stdout.flush()
        
        print(f"\n[4/4] 요약 정보:")
        print(f"    - 프론트엔드에서 /summaries/keywords/{keyword_id}로 조회 가능")
        print(f"    - 요약 텍스트 미리보기:")
        summary_preview = summary_result['summary_text'][:200] + "..." if len(summary_result['summary_text']) > 200 else summary_result['summary_text']
        print(f"      {summary_preview}")
        sys.stdout.flush()
        
        return summary_result
        
    except Exception as e:
        print(f"\n  ❌ 요약 생성 중 오류 발생!")
        print(f"  오류 타입: {type(e).__name__}")
        print(f"  오류 메시지: {str(e)}")
        import traceback
        print(f"\n  스택 트레이스:")
        traceback.print_exc()
        sys.stdout.flush()
        return None
    finally:
        await conn.close()


async def main():
    """메인 함수"""
    # admin@onmi.com의 "oci" 키워드 ID
    keyword_id = "c7223c6d-6d5e-4d11-a858-86adfbf7e727"
    keyword_text = "oci"
    
    print(f"요약 생성 시작: {datetime.now()}")
    print(f"키워드: {keyword_text}")
    print(f"키워드 ID: {keyword_id}")
    print("-" * 50)
    
    try:
        # 크롤링 없이 기존 기사로 요약 생성
        summary_result = await generate_summary_from_existing_articles(keyword_id)
        
        print("-" * 50)
        print(f"요약 생성 작업 완료: {datetime.now()}")
        if summary_result:
            print(f"✅ 요약이 성공적으로 생성되었습니다.")
            print(f"   세션 ID: {summary_result['session_id']}")
        else:
            print(f"⚠️ 요약 생성에 실패했습니다.")
    except Exception as e:
        print(f"요약 생성 작업 오류: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    # Windows에서 asyncio 이벤트 루프 정책 설정
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n크롤링이 사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

