-- #onmi Supabase 데이터베이스 완전 마이그레이션 스크립트
-- 이 스크립트는 Supabase SQL Editor에서 실행하세요.
-- 실행 방법: Supabase 대시보드 > SQL Editor > New Query > 이 스크립트 붙여넣기 > Run
--
-- 모든 마이그레이션을 포함한 완전한 스키마입니다.
-- 기존 테이블이 있어도 안전하게 실행됩니다 (IF NOT EXISTS 사용).

-- ============================================
-- 마이그레이션 001: 초기 스키마
-- ============================================

-- users 테이블
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    locale VARCHAR(10) DEFAULT 'ko-KR',
    auth_type VARCHAR(20) DEFAULT 'local',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT users_auth_type_check CHECK (auth_type IN ('local', 'google', 'kakao', 'apple'))
);

-- keywords 테이블
CREATE TABLE IF NOT EXISTS keywords (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    text VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    notify_level VARCHAR(20) DEFAULT 'standard',
    auto_share_enabled BOOLEAN DEFAULT FALSE,
    auto_share_channels JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_crawled_at TIMESTAMPTZ,
    CONSTRAINT keywords_status_check CHECK (status IN ('active', 'inactive', 'archived')),
    CONSTRAINT keywords_notify_level_check CHECK (notify_level IN ('low', 'standard', 'high'))
);

-- articles 테이블
CREATE TABLE IF NOT EXISTS articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url TEXT UNIQUE NOT NULL,
    source VARCHAR(255),
    title TEXT NOT NULL,
    snippet TEXT,
    published_at TIMESTAMPTZ,
    thumbnail_url_hash VARCHAR(64),
    lang VARCHAR(10) DEFAULT 'ko',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- keyword_articles 매핑 테이블
CREATE TABLE IF NOT EXISTS keyword_articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    keyword_id UUID REFERENCES keywords(id) ON DELETE CASCADE,
    article_id UUID REFERENCES articles(id) ON DELETE CASCADE,
    match_score FLOAT DEFAULT 1.0,
    match_type VARCHAR(20) DEFAULT 'exact',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(keyword_id, article_id),
    CONSTRAINT keyword_articles_match_type_check CHECK (match_type IN ('exact', 'partial', 'synonym'))
);

-- sentiments 테이블
CREATE TABLE IF NOT EXISTS sentiments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id UUID REFERENCES articles(id) ON DELETE CASCADE,
    label VARCHAR(10) NOT NULL,
    score FLOAT NOT NULL,
    rationale JSONB,
    model_ver VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(article_id),
    CONSTRAINT sentiments_label_check CHECK (label IN ('positive', 'negative', 'neutral')),
    CONSTRAINT sentiments_score_check CHECK (score >= 0 AND score <= 1)
);

-- user_actions 테이블 (save, share, feedback 포함)
CREATE TABLE IF NOT EXISTS user_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    article_id UUID REFERENCES articles(id) ON DELETE CASCADE,
    action VARCHAR(20) NOT NULL,
    payload JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT user_actions_action_check CHECK (action IN ('save', 'share', 'feedback'))
);

-- share_history 테이블 (공유 히스토리 전용, 통계 최적화)
CREATE TABLE IF NOT EXISTS share_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    article_id UUID REFERENCES articles(id) ON DELETE CASCADE,
    keyword_id UUID REFERENCES keywords(id) ON DELETE SET NULL,
    channel VARCHAR(50) NOT NULL,
    recipient VARCHAR(255),
    shared_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT share_history_channel_check CHECK (channel IN ('kakao', 'email', 'sms', 'clipboard', 'auto', 'other'))
);

-- ============================================
-- 마이그레이션 006: Google CSE 쿼리 사용량 추적
-- ============================================

CREATE TABLE IF NOT EXISTS cse_query_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    keyword_id UUID REFERENCES keywords(id) ON DELETE CASCADE,
    queries_used INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT cse_query_usage_queries_used_check CHECK (queries_used >= 0),
    CONSTRAINT cse_query_usage_unique_per_day UNIQUE (date, user_id, keyword_id)
);

CREATE INDEX IF NOT EXISTS idx_cse_query_usage_date ON cse_query_usage(date DESC);
CREATE INDEX IF NOT EXISTS idx_cse_query_usage_user_id ON cse_query_usage(user_id);
CREATE INDEX IF NOT EXISTS idx_cse_query_usage_keyword_id ON cse_query_usage(keyword_id);
CREATE INDEX IF NOT EXISTS idx_cse_query_usage_date_user ON cse_query_usage(date, user_id);

DROP TRIGGER IF EXISTS update_cse_query_usage_updated_at ON cse_query_usage;
CREATE TRIGGER update_cse_query_usage_updated_at
    BEFORE UPDATE ON cse_query_usage
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 마이그레이션 003: 토큰 사용량 추적 테이블
-- ============================================

CREATE TABLE IF NOT EXISTS token_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE NOT NULL UNIQUE,
    total_tokens_used INTEGER NOT NULL DEFAULT 0,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT token_usage_total_tokens_check CHECK (total_tokens_used >= 0),
    CONSTRAINT token_usage_input_tokens_check CHECK (input_tokens >= 0),
    CONSTRAINT token_usage_output_tokens_check CHECK (output_tokens >= 0)
);

-- ============================================
-- 마이그레이션 004: OAuth 필드 추가
-- ============================================

-- password_hash를 NULL 허용으로 변경 (OAuth 사용자는 비밀번호 없음)
ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL;

-- OAuth 필드 추가
ALTER TABLE users ADD COLUMN IF NOT EXISTS oauth_provider VARCHAR(20);
ALTER TABLE users ADD COLUMN IF NOT EXISTS oauth_id VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS oauth_email VARCHAR(255);

-- ============================================
-- 마이그레이션 005: 가입 방식 구분 컬럼 추가
-- ============================================

-- auth_type 컬럼 추가 (로컬 가입, Google 가입, 카카오 가입 등 구분)
ALTER TABLE users ADD COLUMN IF NOT EXISTS auth_type VARCHAR(20) DEFAULT 'local';

-- 제약조건 추가
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_auth_type_check;
ALTER TABLE users ADD CONSTRAINT users_auth_type_check 
    CHECK (auth_type IN ('local', 'google', 'kakao', 'apple'));

-- 기존 OAuth 사용자 업데이트
UPDATE users 
SET auth_type = CASE 
    WHEN oauth_provider = 'google' THEN 'google'
    WHEN oauth_provider = 'kakao' THEN 'kakao'
    WHEN oauth_provider = 'apple' THEN 'apple'
    ELSE 'local'
END
WHERE auth_type = 'local' AND oauth_provider IS NOT NULL;

-- ============================================
-- 인덱스 생성
-- ============================================

-- articles 테이블 인덱스
CREATE INDEX IF NOT EXISTS idx_articles_url ON articles(url);
CREATE INDEX IF NOT EXISTS idx_articles_published_at ON articles(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_created_at ON articles(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source);
CREATE INDEX IF NOT EXISTS idx_articles_lang ON articles(lang);

-- keywords 테이블 인덱스
CREATE INDEX IF NOT EXISTS idx_keywords_user_id ON keywords(user_id);
CREATE INDEX IF NOT EXISTS idx_keywords_status ON keywords(status);
CREATE INDEX IF NOT EXISTS idx_keywords_text ON keywords(text);
CREATE INDEX IF NOT EXISTS idx_keywords_created_at ON keywords(created_at DESC);

-- keyword_articles 매핑 테이블 인덱스
CREATE INDEX IF NOT EXISTS idx_keyword_articles_keyword_id ON keyword_articles(keyword_id);
CREATE INDEX IF NOT EXISTS idx_keyword_articles_article_id ON keyword_articles(article_id);
CREATE INDEX IF NOT EXISTS idx_keyword_articles_created_at ON keyword_articles(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_keyword_articles_match_score ON keyword_articles(match_score DESC);

-- sentiments 테이블 인덱스
CREATE INDEX IF NOT EXISTS idx_sentiments_article_id ON sentiments(article_id);
CREATE INDEX IF NOT EXISTS idx_sentiments_label ON sentiments(label);
CREATE INDEX IF NOT EXISTS idx_sentiments_score ON sentiments(score DESC);

-- user_actions 테이블 인덱스
CREATE INDEX IF NOT EXISTS idx_user_actions_user_id ON user_actions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_actions_article_id ON user_actions(article_id);
CREATE INDEX IF NOT EXISTS idx_user_actions_user_article ON user_actions(user_id, article_id);
CREATE INDEX IF NOT EXISTS idx_user_actions_action ON user_actions(action);
CREATE INDEX IF NOT EXISTS idx_user_actions_created_at ON user_actions(created_at DESC);

-- share_history 테이블 인덱스
CREATE INDEX IF NOT EXISTS idx_share_history_user_id ON share_history(user_id);
CREATE INDEX IF NOT EXISTS idx_share_history_article_id ON share_history(article_id);
CREATE INDEX IF NOT EXISTS idx_share_history_keyword_id ON share_history(keyword_id);
CREATE INDEX IF NOT EXISTS idx_share_history_user_keyword ON share_history(user_id, keyword_id);
CREATE INDEX IF NOT EXISTS idx_share_history_shared_at ON share_history(shared_at DESC);
CREATE INDEX IF NOT EXISTS idx_share_history_channel ON share_history(channel);

-- users 테이블 인덱스
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at DESC);

-- token_usage 테이블 인덱스
CREATE INDEX IF NOT EXISTS idx_token_usage_date ON token_usage(date DESC);
CREATE INDEX IF NOT EXISTS idx_token_usage_updated_at ON token_usage(updated_at DESC);

-- OAuth 인덱스
CREATE INDEX IF NOT EXISTS idx_users_oauth ON users(oauth_provider, oauth_id);
CREATE INDEX IF NOT EXISTS idx_users_oauth_email ON users(oauth_email);

-- auth_type 인덱스
CREATE INDEX IF NOT EXISTS idx_users_auth_type ON users(auth_type);

-- ============================================
-- 업데이트 트리거 함수 (updated_at 자동 갱신)
-- ============================================

-- updated_at 자동 갱신 함수
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 각 테이블에 updated_at 트리거 추가
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_keywords_updated_at ON keywords;
CREATE TRIGGER update_keywords_updated_at
    BEFORE UPDATE ON keywords
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_articles_updated_at ON articles;
CREATE TRIGGER update_articles_updated_at
    BEFORE UPDATE ON articles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_sentiments_updated_at ON sentiments;
CREATE TRIGGER update_sentiments_updated_at
    BEFORE UPDATE ON sentiments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_token_usage_updated_at ON token_usage;
CREATE TRIGGER update_token_usage_updated_at
    BEFORE UPDATE ON token_usage
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 완료 메시지
-- ============================================
DO $$
BEGIN
    RAISE NOTICE '✅ #onmi 데이터베이스 스키마가 성공적으로 생성되었습니다!';
    RAISE NOTICE '📊 생성된 테이블: users, keywords, articles, keyword_articles, sentiments, user_actions, share_history, token_usage';
    RAISE NOTICE '📈 인덱스와 트리거가 설정되었습니다.';
    RAISE NOTICE '🔐 OAuth 필드가 추가되었습니다.';
    RAISE NOTICE '🔑 auth_type 컬럼이 추가되어 가입 방식을 구분할 수 있습니다.';
END $$;

