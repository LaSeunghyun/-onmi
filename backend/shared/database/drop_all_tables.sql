-- #onmi 데이터베이스 전체 삭제 스크립트
-- 주의: 이 스크립트는 모든 테이블, 인덱스, 트리거, 함수를 삭제합니다.
-- 실행 전에 데이터 백업을 권장합니다.

-- ============================================
-- 트리거 삭제
-- ============================================

DROP TRIGGER IF EXISTS update_users_updated_at ON users;
DROP TRIGGER IF EXISTS update_keywords_updated_at ON keywords;
DROP TRIGGER IF EXISTS update_articles_updated_at ON articles;
DROP TRIGGER IF EXISTS update_sentiments_updated_at ON sentiments;
DROP TRIGGER IF EXISTS update_token_usage_updated_at ON token_usage;

-- ============================================
-- 테이블 삭제 (외래키 제약조건 때문에 순서 중요)
-- ============================================

-- 외래키를 참조하는 테이블부터 삭제
DROP TABLE IF EXISTS share_history CASCADE;
DROP TABLE IF EXISTS user_actions CASCADE;
DROP TABLE IF EXISTS sentiments CASCADE;
DROP TABLE IF EXISTS keyword_articles CASCADE;
DROP TABLE IF EXISTS keywords CASCADE;
DROP TABLE IF EXISTS articles CASCADE;
DROP TABLE IF EXISTS token_usage CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- ============================================
-- 함수 삭제
-- ============================================

DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;

-- ============================================
-- 완료 메시지
-- ============================================
DO $$
BEGIN
    RAISE NOTICE '✅ 모든 테이블과 관련 객체가 삭제되었습니다.';
END $$;


