"""샘플 데이터 생성 스크립트"""
import asyncio
import asyncpg
import os
import sys
from datetime import datetime, timedelta
from uuid import uuid4

# 데이터베이스 연결 정보
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://onmi:onmi_dev_password@localhost:5432/onmi_db"
)


async def seed_sample_data():
    """샘플 데이터 생성"""
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # 트랜잭션 시작
        async with conn.transaction():
            # 1. 테스트 사용자 생성
            print("📝 테스트 사용자 생성 중...")
            user_id = await conn.fetchval("""
                INSERT INTO users (email, password_hash, locale)
                VALUES ($1, $2, $3)
                ON CONFLICT (email) DO UPDATE SET email = users.email
                RETURNING id
            """, "test@example.com", "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYz5Y5Y5Y5Y", "ko-KR")
            
            if not user_id:
                user_id = await conn.fetchval("SELECT id FROM users WHERE email = $1", "test@example.com")
            
            print(f"✅ 사용자 생성 완료: {user_id}")
            
            # 2. 키워드 생성
            print("📝 키워드 생성 중...")
            keywords_data = [
                ("인공지능", "active", "standard"),
                ("블록체인", "active", "standard"),
                ("기후변화", "active", "high"),
            ]
            
            keyword_ids = []
            for text, status, notify_level in keywords_data:
                keyword_id = await conn.fetchval("""
                    INSERT INTO keywords (user_id, text, status, notify_level)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT DO NOTHING
                    RETURNING id
                """, user_id, text, status, notify_level)
                
                if not keyword_id:
                    keyword_id = await conn.fetchval(
                        "SELECT id FROM keywords WHERE user_id = $1 AND text = $2",
                        user_id, text
                    )
                
                if keyword_id:
                    keyword_ids.append((keyword_id, text))
                    print(f"  ✅ 키워드 생성: {text} ({keyword_id})")
            
            # 3. 샘플 기사 생성
            print("📝 샘플 기사 생성 중...")
            articles_data = [
                {
                    "url": "https://example.com/article1",
                    "source": "Tech News",
                    "title": "인공지능의 미래: GPT 모델의 발전",
                    "snippet": "최근 인공지능 기술이 급속도로 발전하고 있으며, 특히 대규모 언어 모델의 성능이 향상되고 있습니다.",
                    "published_at": datetime.now() - timedelta(days=1),
                    "lang": "ko"
                },
                {
                    "url": "https://example.com/article2",
                    "source": "Crypto Daily",
                    "title": "블록체인 기술의 새로운 도약",
                    "snippet": "블록체인 기술이 금융 분야를 넘어 다양한 산업에 적용되고 있습니다.",
                    "published_at": datetime.now() - timedelta(days=2),
                    "lang": "ko"
                },
                {
                    "url": "https://example.com/article3",
                    "source": "Environment Today",
                    "title": "기후변화 대응을 위한 글로벌 협력",
                    "snippet": "전 세계가 기후변화 문제 해결을 위해 협력하고 있으며, 탄소 중립 목표를 달성하기 위한 노력이 진행 중입니다.",
                    "published_at": datetime.now() - timedelta(hours=5),
                    "lang": "ko"
                },
                {
                    "url": "https://example.com/article4",
                    "source": "Tech News",
                    "title": "AI가 가져올 직업의 변화",
                    "snippet": "인공지능의 발전으로 인해 많은 직업이 변화하고 있으며, 새로운 기회와 도전이 동시에 나타나고 있습니다.",
                    "published_at": datetime.now() - timedelta(hours=10),
                    "lang": "ko"
                },
                {
                    "url": "https://example.com/article5",
                    "source": "Crypto Daily",
                    "title": "디지털 자산의 규제 현황",
                    "snippet": "블록체인 기반 디지털 자산에 대한 규제가 전 세계적으로 논의되고 있습니다.",
                    "published_at": datetime.now() - timedelta(days=3),
                    "lang": "ko"
                },
            ]
            
            article_ids = []
            for article_data in articles_data:
                article_id = await conn.fetchval("""
                    INSERT INTO articles (url, source, title, snippet, published_at, lang)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (url) DO UPDATE SET title = articles.title
                    RETURNING id
                """, article_data["url"], article_data["source"], article_data["title"],
                    article_data["snippet"], article_data["published_at"], article_data["lang"])
                
                if not article_id:
                    article_id = await conn.fetchval(
                        "SELECT id FROM articles WHERE url = $1",
                        article_data["url"]
                    )
                
                if article_id:
                    article_ids.append(article_id)
                    print(f"  ✅ 기사 생성: {article_data['title'][:30]}... ({article_id})")
            
            # 4. 감정 분석 결과 생성
            print("📝 감정 분석 결과 생성 중...")
            sentiments_data = [
                ("positive", 0.85, {"reason": "긍정적인 전망과 발전 가능성"}),
                ("positive", 0.72, {"reason": "기술적 혁신에 대한 긍정적 평가"}),
                ("neutral", 0.55, {"reason": "객관적인 정보 제공"}),
                ("positive", 0.78, {"reason": "미래 기회에 대한 긍정적 시각"}),
                ("neutral", 0.50, {"reason": "규제 관련 중립적 보도"}),
            ]
            
            for i, (label, score, rationale) in enumerate(sentiments_data):
                if i < len(article_ids):
                    await conn.execute("""
                        INSERT INTO sentiments (article_id, label, score, rationale, model_ver)
                        VALUES ($1, $2, $3, $4, $5)
                        ON CONFLICT (article_id) DO UPDATE SET label = $2, score = $3
                    """, article_ids[i], label, score, rationale, "rule-based-v1")
                    print(f"  ✅ 감정 분석: {label} (점수: {score})")
            
            # 5. 키워드-기사 매핑 생성
            print("📝 키워드-기사 매핑 생성 중...")
            mappings = [
                (keyword_ids[0][0], article_ids[0]),  # 인공지능 - 기사1
                (keyword_ids[0][0], article_ids[3]),  # 인공지능 - 기사4
                (keyword_ids[1][0], article_ids[1]),  # 블록체인 - 기사2
                (keyword_ids[1][0], article_ids[4]),  # 블록체인 - 기사5
                (keyword_ids[2][0], article_ids[2]),  # 기후변화 - 기사3
            ]
            
            for keyword_id, article_id in mappings:
                await conn.execute("""
                    INSERT INTO keyword_articles (keyword_id, article_id, match_score, match_type)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (keyword_id, article_id) DO NOTHING
                """, keyword_id, article_id, 1.0, "exact")
                print(f"  ✅ 매핑 생성: 키워드-기사 연결")
            
            print("\n✅ 샘플 데이터 생성 완료!")
            print(f"\n📊 생성된 데이터:")
            print(f"  - 사용자: 1명 (test@example.com)")
            print(f"  - 키워드: {len(keyword_ids)}개")
            print(f"  - 기사: {len(article_ids)}개")
            print(f"  - 감정 분석: {len(sentiments_data)}개")
            print(f"  - 키워드-기사 매핑: {len(mappings)}개")
            print(f"\n🔑 테스트 계정:")
            print(f"  이메일: test@example.com")
            print(f"  비밀번호: test1234 (실제로는 해시된 값이 저장됨)")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        raise
    finally:
        await conn.close()


if __name__ == "__main__":
    print("=== 샘플 데이터 생성 시작 ===\n")
    asyncio.run(seed_sample_data())

