"""키워드별 그룹화 및 번역 기능이 포함된 기사 요약 테스트 스크립트"""
print("[INIT] 스크립트 시작", flush=True)

print("[INIT] 모듈 import 시작...", flush=True)
import asyncio
print("[INIT] asyncio import 완료", flush=True)
import asyncpg
print("[INIT] asyncpg import 완료", flush=True)
import os
print("[INIT] os import 완료", flush=True)
import sys
print("[INIT] sys import 완료", flush=True)
from dotenv import load_dotenv
print("[INIT] dotenv import 완료", flush=True)
from uuid import UUID
print("[INIT] uuid import 완료", flush=True)
from collections import defaultdict
print("[INIT] collections import 완료", flush=True)
from typing import Dict, List, Any, Optional
print("[INIT] typing import 완료", flush=True)

# Windows 콘솔 인코딩 설정
print("[INIT] Windows 콘솔 설정 시작...", flush=True)
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    # 출력 버퍼링 비활성화 (실시간 로그 출력)
    try:
        sys.stdout.reconfigure(line_buffering=True)
        print("[INIT] 출력 버퍼링 비활성화 완료", flush=True)
    except:
        print("[INIT] 출력 버퍼링 설정 실패 (무시)", flush=True)

# 프로젝트 경로 추가
print("[INIT] 프로젝트 경로 추가 중...", flush=True)
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'shared'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'api-gateway', 'src'))
print("[INIT] 프로젝트 경로 추가 완료", flush=True)

print("[INIT] 환경변수 로드 중...", flush=True)
load_dotenv()
print("[INIT] 환경변수 로드 완료", flush=True)

# 번역 라이브러리 import 시도
print("[INIT] 번역 라이브러리 import 시도...", flush=True)
try:
    from googletrans import Translator
    TRANSLATION_AVAILABLE = True
    print("[INIT] ✅ googletrans import 성공", flush=True)
except ImportError as e:
    TRANSLATION_AVAILABLE = False
    print("[INIT] ⚠️ googletrans import 실패", flush=True)
    print("⚠️ 경고: googletrans 라이브러리가 설치되지 않았습니다.", flush=True)
    print("   외국어 기사는 번역되지 않고 원문으로 표시됩니다.", flush=True)
    print("   설치 방법: pip install googletrans==4.0.0rc1", flush=True)

# Gemini API import 시도
print("[INIT] Gemini API 라이브러리 import 시도...", flush=True)
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
    print("[INIT] ✅ google-generativeai import 성공", flush=True)
except ImportError as e:
    GEMINI_AVAILABLE = False
    print("[INIT] ⚠️ google-generativeai import 실패", flush=True)
    print("⚠️ 경고: google-generativeai 라이브러리가 설치되지 않았습니다.", flush=True)
    print("   Gemini API를 사용한 요약이 불가능합니다.", flush=True)
    print("   설치 방법: pip install google-generativeai", flush=True)

print("[INIT] 모든 초기화 완료", flush=True)


def translate_text(text: str, target_lang: str = 'ko') -> str:
    """텍스트를 한국어로 번역"""
    print(f"      [translate_text] 함수 진입, 텍스트 길이: {len(text) if text else 0}자", flush=True)
    if not TRANSLATION_AVAILABLE:
        print(f"      [translate_text] 번역 라이브러리 사용 불가, 원문 반환", flush=True)
        return text
    
    if not text or not text.strip():
        print(f"      [translate_text] 빈 텍스트, 원문 반환", flush=True)
        return text
    
    try:
        print(f"      [translate_text] 번역 시작 (대상 언어: {target_lang})", flush=True)
        translator = Translator()
        result = translator.translate(text, dest=target_lang)
        print(f"      [translate_text] 번역 완료", flush=True)
        return result.text
    except Exception as e:
        print(f"      [translate_text] ⚠️ 번역 실패 (원문 사용): {str(e)[:50]}", flush=True)
        return text


def convert_article_format(article_row: Dict) -> Dict[str, Any]:
    """ArticleRepository에서 조회한 article 데이터를 Summarizer 형식으로 변환"""
    print(f"      [convert_article_format] 기사 데이터 변환 시작 (ID: {article_row.get('id')})", flush=True)
    # sentiment 필드 통합
    sentiment = {}
    if article_row.get('sentiment_label'):
        sentiment['label'] = article_row['sentiment_label']
    else:
        sentiment['label'] = 'neutral'
    
    if article_row.get('sentiment_score') is not None:
        sentiment['score'] = float(article_row['sentiment_score'])
    else:
        sentiment['score'] = 0.5
    
    if article_row.get('sentiment_rationale'):
        sentiment['rationale'] = article_row['sentiment_rationale']
    
    result = {
        'id': str(article_row['id']),
        'title': article_row.get('title', '제목 없음'),
        'snippet': article_row.get('snippet', '') or '',
        'source': article_row.get('source', '') or '',
        'url': article_row.get('url', ''),
        'published_at': article_row.get('published_at'),
        'sentiment': sentiment,
        'lang': article_row.get('lang', 'ko')
    }
    print(f"      [convert_article_format] 변환 완료", flush=True)
    return result


async def fetch_articles_by_keyword(conn, user_id: Optional[UUID] = None, limit: int = 100) -> Dict[str, List[Dict]]:
    """키워드별로 article을 그룹화하여 조회"""
    print(f"   [fetch_articles_by_keyword] 함수 진입, user_id: {user_id}, limit: {limit}", flush=True)
    if user_id:
        print(f"   [fetch_articles_by_keyword] 사용자별 쿼리 사용", flush=True)
        query = """
            SELECT DISTINCT
                k.id as keyword_id,
                k.text as keyword_text,
                a.id, a.title, a.snippet, a.source, a.url, a.published_at,
                a.thumbnail_url_hash, a.created_at, a.lang,
                s.label as sentiment_label, s.score as sentiment_score,
                s.rationale as sentiment_rationale
            FROM articles a
            INNER JOIN keyword_articles ka ON a.id = ka.article_id
            INNER JOIN keywords k ON ka.keyword_id = k.id
            LEFT JOIN sentiments s ON a.id = s.article_id
            WHERE k.user_id = $1 AND k.status = 'active'
            ORDER BY k.text, a.published_at DESC NULLS LAST, a.created_at DESC
            LIMIT $2
        """
        print(f"   [fetch_articles_by_keyword] 쿼리 실행 중...", flush=True)
        rows = await conn.fetch(query, user_id, limit)
        print(f"   [fetch_articles_by_keyword] 쿼리 완료, {len(rows)}개 행 반환", flush=True)
    else:
        print(f"   [fetch_articles_by_keyword] 전체 쿼리 사용", flush=True)
        query = """
            SELECT DISTINCT
                k.id as keyword_id,
                k.text as keyword_text,
                a.id, a.title, a.snippet, a.source, a.url, a.published_at,
                a.thumbnail_url_hash, a.created_at, a.lang,
                s.label as sentiment_label, s.score as sentiment_score,
                s.rationale as sentiment_rationale
            FROM articles a
            INNER JOIN keyword_articles ka ON a.id = ka.article_id
            INNER JOIN keywords k ON ka.keyword_id = k.id
            LEFT JOIN sentiments s ON a.id = s.article_id
            WHERE k.status = 'active'
            ORDER BY k.text, a.published_at DESC NULLS LAST, a.created_at DESC
            LIMIT $1
        """
        print(f"   [fetch_articles_by_keyword] 쿼리 실행 중...", flush=True)
        rows = await conn.fetch(query, limit)
        print(f"   [fetch_articles_by_keyword] 쿼리 완료, {len(rows)}개 행 반환", flush=True)
    
    # 키워드별로 그룹화
    print(f"   [fetch_articles_by_keyword] 키워드별 그룹화 시작...", flush=True)
    keyword_groups = defaultdict(list)
    keyword_names = {}
    
    print(f"   [fetch_articles_by_keyword] {len(rows)}개 행 처리 중...", flush=True)
    for idx, row in enumerate(rows):
        if idx % 10 == 0:
            print(f"   [fetch_articles_by_keyword] 처리 중... {idx}/{len(rows)}", flush=True)
        keyword_id = str(row['keyword_id'])
        keyword_text = row['keyword_text']
        keyword_names[keyword_id] = keyword_text
        
        article_data = convert_article_format(row)
        keyword_groups[keyword_id].append(article_data)
    
    print(f"   [fetch_articles_by_keyword] 그룹화 완료: {len(keyword_groups)}개 키워드 그룹", flush=True)
    return dict(keyword_groups), keyword_names


def translate_articles(articles: List[Dict]) -> List[Dict]:
    """외국어 기사를 한국어로 번역"""
    print(f"   [translate_articles] 함수 진입, 기사 수: {len(articles)}개", flush=True)
    translated_articles = []
    
    for idx, article in enumerate(articles):
        if idx % 5 == 0:
            print(f"   [translate_articles] 처리 중... {idx}/{len(articles)}", flush=True)
        lang = article.get('lang', 'ko')
        translated_article = article.copy()
        
        # 한국어가 아닌 경우 번역
        if lang != 'ko':
            print(f"   [translate_articles] 🔄 번역 중: {article.get('title', '')[:50]}... ({lang} → ko)", flush=True)
            translated_article['title'] = translate_text(article.get('title', ''), 'ko')
            if article.get('snippet'):
                translated_article['snippet'] = translate_text(article.get('snippet', ''), 'ko')
        else:
            print(f"   [translate_articles] 한국어 기사, 번역 생략", flush=True)
        
        translated_articles.append(translated_article)
    
    print(f"   [translate_articles] 번역 완료, {len(translated_articles)}개 기사 반환", flush=True)
    return translated_articles


async def generate_summary_with_gemini(articles: List[Dict], keyword_text: str) -> str:
    """Gemini API를 사용하여 키워드별 기사 그룹을 한국어로 요약"""
    print(f"      [generate_summary_with_gemini] 함수 진입, 키워드: {keyword_text}, 기사 수: {len(articles)}", flush=True)
    if not GEMINI_AVAILABLE:
        print(f"      [generate_summary_with_gemini] ❌ Gemini 라이브러리 없음", flush=True)
        raise ImportError("google-generativeai 라이브러리가 설치되지 않았습니다.")
    
    print(f"      [generate_summary_with_gemini] 환경변수 확인 중...", flush=True)
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    gemini_model_raw = os.getenv('GEMINI_MODEL', 'models/gemini-2.5-flash')
    
    # 모델 이름 정규화
    gemini_model = gemini_model_raw.strip()
    
    # 'models/' 접두사가 없으면 추가
    if not gemini_model.startswith('models/'):
        gemini_model = f'models/{gemini_model}'
    
    # 구버전 모델 이름을 최신 모델로 매핑
    deprecated_models = {
        'models/gemini-1.5-flash': 'models/gemini-2.5-flash',
        'models/gemini-1.5-flash-latest': 'models/gemini-2.5-flash',
        'models/gemini-1.5-pro': 'models/gemini-2.5-pro',
        'models/gemini-1.5-pro-latest': 'models/gemini-2.5-pro',
    }
    
    if gemini_model in deprecated_models:
        print(f"      [generate_summary_with_gemini] ⚠️ 구버전 모델 감지: {gemini_model}", flush=True)
        gemini_model = deprecated_models[gemini_model]
        print(f"      [generate_summary_with_gemini] ✅ 최신 모델로 변경: {gemini_model}", flush=True)
    
    # 기본값이 없거나 잘못된 경우 models/gemini-2.5-flash 사용
    if not gemini_model or gemini_model == 'models/':
        gemini_model = 'models/gemini-2.5-flash'
    
    print(f"      [generate_summary_with_gemini] 최종 모델 이름: {gemini_model} (원본: {gemini_model_raw})", flush=True)
    
    if not gemini_api_key:
        print(f"      [generate_summary_with_gemini] ❌ API 키 없음", flush=True)
        raise ValueError("GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
    
    print(f"      [generate_summary_with_gemini] Gemini API 설정 중...", flush=True)
    # Gemini API 설정
    genai.configure(api_key=gemini_api_key)
    model = genai.GenerativeModel(gemini_model)
    print(f"      [generate_summary_with_gemini] 모델 초기화 완료: {gemini_model}", flush=True)
    
    # 기사 내용을 텍스트로 구성
    print(f"      [generate_summary_with_gemini] 기사 텍스트 구성 중...", flush=True)
    articles_text = []
    for i, article in enumerate(articles, 1):
        title = article.get('title', '제목 없음')
        snippet = article.get('snippet', '') or ''
        source = article.get('source', '') or ''
        
        article_text = f"기사 {i}:\n"
        article_text += f"제목: {title}\n"
        if snippet:
            article_text += f"내용: {snippet}\n"
        if source:
            article_text += f"출처: {source}\n"
        articles_text.append(article_text)
    
    all_articles_text = "\n\n".join(articles_text)
    print(f"      [generate_summary_with_gemini] 텍스트 구성 완료, 총 길이: {len(all_articles_text)}자", flush=True)
    
    # 프롬프트 작성
    print(f"      [generate_summary_with_gemini] 프롬프트 작성 중...", flush=True)
    prompt = f"""안녕하세요! '{keyword_text}' 키워드와 관련된 {len(articles)}개의 뉴스 기사들을 읽어보았습니다. 
이 기사들을 바탕으로, '{keyword_text}'와 관련된 이슈가 무엇인지 한국어를 기준으로 친근하고 따뜻한 톤으로 설명해주세요.

중요한 원칙:
- 제공된 기사 내용에 대해서만 요약해주세요. 기사에 없는 정보나 학습 데이터의 일반적인 지식을 추가하지 마세요.
- 기사에서 명시적으로 언급된 사실과 내용만을 바탕으로 요약을 작성해주세요.
- 추측이나 일반적인 상식은 포함하지 말고, 오직 제공된 기사 내용만을 기반으로 작성해주세요.

요약 작성 가이드:
1. 마치 친한 친구에게 설명하듯이 따뜻하고 친근한 톤으로 작성해주세요.
2. '{keyword_text}' 키워드와 관련된 주요 이슈가 무엇인지 명확하게 설명해주세요.
3. 제공된 기사들에서 읽은 핵심 내용과 중요한 포인트들을 자연스럽게 전달해주세요.
4. 기사들 간의 공통점이나 연관성을 찾아서 통합적으로 설명해주세요.
5. 독자가 쉽게 이해할 수 있도록 구체적이고 명확하게 작성해주세요.
6. 반드시 한국어로 작성해주세요.
7. 적절한 길이로 작성해주세요 (500-800자 정도).
8. 독자가 생각해볼만한 포인트를 작성해주세요.

기사 목록:
{all_articles_text}

위 기사들을 읽고, '{keyword_text}'와 관련된 이슈를 따뜻하고 친근한 톤으로 설명해주세요. 
반드시 제공된 기사 내용에 대해서만 요약하고, 기사에 없는 정보는 포함하지 마세요:"""
    print(f"      [generate_summary_with_gemini] 프롬프트 작성 완료, 길이: {len(prompt)}자", flush=True)

    try:
        print(f"      [generate_summary_with_gemini] 🤖 Gemini API 호출 시작... (모델: {gemini_model})", flush=True)
        print(f"      [generate_summary_with_gemini] 프롬프트 길이: {len(prompt)}자", flush=True)
        print(f"      [generate_summary_with_gemini] 기사 개수: {len(articles)}개", flush=True)
        print(f"      [generate_summary_with_gemini] API 호출 대기 중... (최대 120초 대기)", flush=True)
        
        # GenerationConfig 설정 (temperature 0.5)
        generation_config = genai.types.GenerationConfig(
            temperature=0.5
        )
        
        # 타임아웃 설정 (120초)
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(model.generate_content, prompt, generation_config=generation_config),
                timeout=120.0
            )
            print(f"      [generate_summary_with_gemini] ✅ API 응답 수신 완료", flush=True)
        except asyncio.TimeoutError:
            print(f"      [generate_summary_with_gemini] ❌ API 호출 타임아웃 (120초 초과)", flush=True)
            raise TimeoutError("Gemini API 호출이 120초 내에 완료되지 않았습니다.")
        
        print(f"      [generate_summary_with_gemini] 응답 처리 중...", flush=True)
        if response and response.text:
            summary = response.text.strip()
            print(f"      [generate_summary_with_gemini] ✅ 요약 생성 완료 ({len(summary)}자)", flush=True)
            return summary
        else:
            print(f"      [generate_summary_with_gemini] ⚠️ Gemini API가 응답을 반환하지 않았습니다.", flush=True)
            return "요약을 생성할 수 없습니다."
    except Exception as e:
        print(f"      [generate_summary_with_gemini] ❌ Gemini API 호출 실패: {e}", flush=True)
        print(f"      [generate_summary_with_gemini] 예외 타입: {type(e).__name__}", flush=True)
        raise


async def test_summary():
    """저장된 article을 기준으로 키워드별 요약 생성 테스트"""
    print("=" * 60, flush=True)
    print("키워드별 기사 요약 테스트", flush=True)
    print("=" * 60, flush=True)
    
    # 환경변수 확인
    print("\n[1/6] 환경변수 확인 중...", flush=True)
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("   ❌ DATABASE_URL 환경변수가 설정되지 않았습니다.", flush=True)
        return
    print("   ✅ DATABASE_URL 확인 완료", flush=True)
    
    # Gemini API 확인
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if gemini_api_key:
        print(f"   ✅ GEMINI_API_KEY 확인 완료", flush=True)
    else:
        print(f"   ⚠️ GEMINI_API_KEY가 설정되지 않았습니다. 템플릿 기반 요약을 사용합니다.", flush=True)
    
    try:
        # 데이터베이스 연결
        print("\n[2/6] 데이터베이스 연결 시도 중...", flush=True)
        print(f"   연결 URL: {database_url[:50]}...", flush=True)
        print("   연결 중...", flush=True)
        conn = await asyncpg.connect(database_url, statement_cache_size=0)
        print("   ✅ 데이터베이스 연결 성공", flush=True)
        
        # 사용자 ID 조회 (선택사항)
        print("\n[3/6] 사용자 조회 중...", flush=True)
        user_email = os.getenv('TEST_USER_EMAIL', 'admin@onmi.com')
        print(f"   이메일: {user_email}", flush=True)
        print("   쿼리 실행: SELECT id, email FROM users WHERE email = $1", flush=True)
        user = await conn.fetchrow(
            "SELECT id, email FROM users WHERE email = $1",
            user_email
        )
        
        user_id = user['id'] if user else None
        if user:
            print(f"   ✅ 사용자 발견: {user['email']} (ID: {user_id})", flush=True)
        else:
            print(f"   ⚠️ 사용자를 찾을 수 없습니다. 모든 활성 키워드의 기사를 조회합니다.", flush=True)
        
        # 키워드별 article 조회
        print(f"\n[4/6] 키워드별 기사 조회 중...", flush=True)
        print(f"   사용자 ID: {user_id if user_id else '전체'}", flush=True)
        print(f"   최대 조회 개수: 200개", flush=True)
        print("   쿼리 실행 중...", flush=True)
        keyword_groups, keyword_names = await fetch_articles_by_keyword(conn, user_id, limit=200)
        print(f"   쿼리 완료", flush=True)
        
        if not keyword_groups:
            print("   ❌ 조회된 기사가 없습니다.", flush=True)
            await conn.close()
            return
        
        print(f"   ✅ {len(keyword_groups)}개의 키워드 그룹 발견:", flush=True)
        total_articles = 0
        for keyword_id, articles in keyword_groups.items():
            keyword_text = keyword_names.get(keyword_id, keyword_id)
            print(f"      - {keyword_text}: {len(articles)}개 기사", flush=True)
            total_articles += len(articles)
        print(f"\n   총 {total_articles}개의 기사", flush=True)
        
        print(f"\n   🔌 데이터베이스 연결 종료 중...", flush=True)
        try:
            # 연결이 이미 닫혔는지 확인
            if not conn.is_closed():
                await conn.close()
                print("   ✅ 연결 종료 완료", flush=True)
            else:
                print("   ℹ️ 연결이 이미 종료되었습니다", flush=True)
        except (asyncio.CancelledError, KeyboardInterrupt) as e:
            print(f"   ⚠️ 연결 종료 중 취소됨: {type(e).__name__}", flush=True)
        except Exception as e:
            print(f"   ⚠️ 연결 종료 중 오류 (무시): {type(e).__name__}: {e}", flush=True)
        print(f"   [test_summary] 데이터베이스 작업 완료, 요약 생성 단계로 이동", flush=True)
        
        # 키워드별 요약 생성
        print(f"\n[5/6] 키워드별 요약 생성 준비 중...", flush=True)
        print("=" * 60, flush=True)
        
        # Gemini API 사용 가능 여부 확인
        print("   [test_summary] Gemini API 사용 가능 여부 확인 중...", flush=True)
        use_gemini = GEMINI_AVAILABLE and os.getenv('GEMINI_API_KEY')
        print(f"   [test_summary] GEMINI_AVAILABLE: {GEMINI_AVAILABLE}, API_KEY 존재: {bool(os.getenv('GEMINI_API_KEY'))}", flush=True)
        if use_gemini:
            print("   ✅ Gemini API 사용 가능", flush=True)
        else:
            print("   ⚠️ Gemini API 사용 불가", flush=True)
        
        # 템플릿 기반 요약용 설정 (Gemini 사용 불가 시 또는 대체용)
        print("   [test_summary] 요약 설정 초기화 중...", flush=True)
        summarizer = None
        default_config = {
            'detail_level': 'standard',
            'max_length': 500,
            'include_sentiment': True,
            'include_keywords': False,
            'include_sources': False,
            'top_articles_count': 5
        }
        print("   [test_summary] 기본 설정 완료", flush=True)
        
        if not use_gemini:
            print("   ⚠️ Gemini API를 사용할 수 없습니다. 기본 템플릿 기반 요약을 사용합니다.", flush=True)
            print("   💡 Gemini API를 사용하려면:", flush=True)
            print("      1. pip install google-generativeai", flush=True)
            print("      2. .env 파일에 GEMINI_API_KEY 설정", flush=True)
            
            # 경로 설정 (템플릿 기반 요약용)
            print("   📦 템플릿 기반 요약 모듈 로드 중...", flush=True)
            backend_path = os.path.join(os.path.dirname(__file__), 'backend')
            shared_path = os.path.join(backend_path, 'shared')
            api_gateway_path = os.path.join(backend_path, 'api-gateway', 'src')
            print(f"   [test_summary] 경로 설정: shared={shared_path}, api_gateway={api_gateway_path}", flush=True)
            
            sys.path.insert(0, shared_path)
            sys.path.insert(0, api_gateway_path)
            print("   [test_summary] 경로 추가 완료", flush=True)
            
            try:
                print("   [test_summary] Summarizer import 시도...", flush=True)
                from services.summary_service import Summarizer
                print("   [test_summary] Summarizer import 성공, 인스턴스 생성 중...", flush=True)
                summarizer = Summarizer()
                print("   ✅ 템플릿 기반 요약 모듈 로드 완료", flush=True)
            except ImportError as e:
                print(f"   ⚠️ Summarizer를 import할 수 없습니다: {e}", flush=True)
                import traceback
                traceback.print_exc()
            except Exception as e:
                print(f"   ⚠️ Summarizer 초기화 실패: {e}", flush=True)
                import traceback
                traceback.print_exc()
        
        print(f"   [test_summary] 요약 준비 완료, summarizer={summarizer is not None}", flush=True)
        
        print(f"\n[6/6] 키워드별 요약 생성 시작...", flush=True)
        print("=" * 60, flush=True)
        
        keyword_count = len(keyword_groups)
        current_keyword = 0
        
        print(f"   [test_summary] 키워드 루프 시작, 총 {keyword_count}개 키워드", flush=True)
        for keyword_id, articles in keyword_groups.items():
            current_keyword += 1
            keyword_text = keyword_names.get(keyword_id, keyword_id)
            
            print(f"\n   [test_summary] 키워드 루프 [{current_keyword}/{keyword_count}] 시작", flush=True)
            print(f"[{current_keyword}/{keyword_count}] 🔑 키워드: {keyword_text}", flush=True)
            print(f"   기사 수: {len(articles)}개", flush=True)
            print("-" * 60, flush=True)
            
            # 외국어 기사 번역
            if TRANSLATION_AVAILABLE:
                foreign_count = sum(1 for a in articles if a.get('lang', 'ko') != 'ko')
                if foreign_count > 0:
                    print(f"   🌐 외국어 기사 번역 중... ({foreign_count}개)", flush=True)
                    translated_articles = translate_articles(articles)
                    print(f"   ✅ 번역 완료", flush=True)
                else:
                    print(f"   ℹ️ 번역할 외국어 기사 없음", flush=True)
                    translated_articles = articles
            else:
                translated_articles = articles
            
            # 요약 생성
            try:
                print(f"   📝 요약 생성 중...", flush=True)
                print(f"   [test_summary] use_gemini={use_gemini}, summarizer={summarizer is not None}", flush=True)
                if use_gemini:
                    print(f"   [test_summary] Gemini API 사용 (모델: {os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')})", flush=True)
                if use_gemini:
                    # Gemini API를 사용한 요약
                    print(f"   [test_summary] Gemini API로 요약 생성 시작", flush=True)
                    summary_text = await generate_summary_with_gemini(translated_articles, keyword_text)
                    print(f"   [test_summary] Gemini API 요약 완료", flush=True)
                else:
                    # 템플릿 기반 요약
                    if summarizer is None:
                        print(f"   [test_summary] ❌ Summarizer가 None입니다!", flush=True)
                        raise ValueError("템플릿 기반 요약을 사용할 수 없습니다. Summarizer를 초기화할 수 없습니다.")
                    print(f"   [test_summary] 템플릿 기반 요약 생성 시작...", flush=True)
                    print(f"   [test_summary] 기사 수: {len(translated_articles)}개", flush=True)
                    summary_text = summarizer.generate(translated_articles, default_config)
                    print(f"   [test_summary] 템플릿 기반 요약 생성 완료, 길이: {len(summary_text)}자", flush=True)
                    print(f"   ✅ 요약 생성 완료 ({len(summary_text)}자)", flush=True)
                
                print(f"\n   📄 요약 결과:", flush=True)
                print("   " + "=" * 58, flush=True)
                if summary_text:
                    # 요약을 여러 줄로 나누어 출력
                    for line in summary_text.split('\n'):
                        print(f"   {line}", flush=True)
                else:
                    print("   (요약 내용 없음)", flush=True)
                print("   " + "=" * 58, flush=True)
                print("-" * 60, flush=True)
            except (asyncio.CancelledError, KeyboardInterrupt) as e:
                print(f"\n   [test_summary] ⚠️ 요약 생성이 취소되었습니다: {type(e).__name__}", flush=True)
                raise  # CancelledError와 KeyboardInterrupt는 다시 raise
            except Exception as e:
                try:
                    print(f"\n   [test_summary] ❌ 요약 생성 실패: {str(e)[:100]}", flush=True)
                    print(f"   [test_summary] 예외 타입: {type(e).__name__}", flush=True)
                    print("   템플릿 기반 요약으로 대체합니다...", flush=True)
                    # 템플릿 기반 요약으로 대체
                    print(f"   [test_summary] 템플릿 기반 요약 초기화 중...", flush=True)
                    if summarizer is None:
                        print(f"   [test_summary] Summarizer 인스턴스 생성 중...", flush=True)
                        backend_path = os.path.join(os.path.dirname(__file__), 'backend')
                        shared_path = os.path.join(backend_path, 'shared')
                        api_gateway_path = os.path.join(backend_path, 'api-gateway', 'src')
                        sys.path.insert(0, shared_path)
                        sys.path.insert(0, api_gateway_path)
                        from services.summary_service import Summarizer
                        summarizer = Summarizer()
                        print(f"   [test_summary] Summarizer 인스턴스 생성 완료", flush=True)
                    
                    print(f"   [test_summary] 템플릿 기반 요약 생성 중...", flush=True)
                    summary_text = summarizer.generate(translated_articles, default_config)
                    print(f"   [test_summary] 템플릿 기반 요약 생성 완료", flush=True)
                    print(f"\n📄 요약 (템플릿 기반):", flush=True)
                    print("   " + "=" * 58, flush=True)
                    if summary_text:
                        for line in summary_text.split('\n'):
                            print(f"   {line}", flush=True)
                    else:
                        print("   (요약 내용 없음)", flush=True)
                    print("   " + "=" * 58, flush=True)
                    print("-" * 60, flush=True)
                except Exception as e2:
                    try:
                        print(f"   [test_summary] ❌ 템플릿 기반 요약도 실패: {str(e2)[:100]}", flush=True)
                        print(f"   [test_summary] 예외 타입: {type(e2).__name__}", flush=True)
                    except:
                        print(f"   [test_summary] ❌ 예외 처리 중 오류 발생", flush=True)
            
            print(f"   [test_summary] 키워드 루프 [{current_keyword}/{keyword_count}] 완료", flush=True)
        
        print(f"   [test_summary] 모든 키워드 루프 완료", flush=True)
        print(f"\n✅ 모든 키워드별 요약 생성 완료!", flush=True)
        print(f"   총 {keyword_count}개의 키워드에 대한 요약이 생성되었습니다.", flush=True)
        
    except (asyncio.CancelledError, KeyboardInterrupt) as e:
        print(f"\n⚠️ 프로그램이 취소되었습니다: {type(e).__name__}", flush=True)
        raise  # CancelledError와 KeyboardInterrupt는 다시 raise
    except asyncpg.exceptions.InvalidPasswordError as e:
        print(f"\n❌ 데이터베이스 인증 실패:", flush=True)
        print(f"   오류: {e}", flush=True)
        print(f"   💡 DATABASE_URL의 비밀번호를 확인해주세요.", flush=True)
    except asyncpg.exceptions.ConnectionDoesNotExistError as e:
        print(f"\n❌ 데이터베이스 연결 실패:", flush=True)
        print(f"   오류: {e}", flush=True)
        print(f"   💡 DATABASE_URL이 올바른지 확인해주세요.", flush=True)
    except Exception as e:
        try:
            print(f"\n❌ 오류 발생:", flush=True)
            print(f"   오류 타입: {type(e).__name__}", flush=True)
            print(f"   오류 메시지: {str(e)[:200]}", flush=True)
            print(f"\n   상세 스택 트레이스:", flush=True)
            import traceback
            traceback.print_exc()
        except:
            print(f"\n❌ 오류 발생 (상세 정보 출력 실패)", flush=True)


if __name__ == "__main__":
    print("[MAIN] 스크립트 시작", flush=True)
    print("[MAIN] asyncio.run 호출 전", flush=True)
    try:
        asyncio.run(test_summary())
        print("[MAIN] 스크립트 완료", flush=True)
    except (asyncio.CancelledError, KeyboardInterrupt) as e:
        print(f"\n[MAIN] ⚠️ 프로그램이 사용자에 의해 취소되었습니다.", flush=True)
    except Exception as e:
        try:
            print(f"[MAIN] ❌ 스크립트 실행 중 오류: {str(e)[:200]}", flush=True)
            print(f"[MAIN] 오류 타입: {type(e).__name__}", flush=True)
            import traceback
            traceback.print_exc()
        except:
            print(f"[MAIN] ❌ 오류 발생 (상세 정보 출력 실패)", flush=True)

