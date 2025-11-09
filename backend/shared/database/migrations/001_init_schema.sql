-- #onmi 데이터베이스 스키마 초기화
-- Supabase PostgreSQL 호환

-- users 테이블
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    locale VARCHAR(10) DEFAULT 'ko-KR',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
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

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_articles_url ON articles(url);
CREATE INDEX IF NOT EXISTS idx_articles_published_at ON articles(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_created_at ON articles(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source);
CREATE INDEX IF NOT EXISTS idx_articles_lang ON articles(lang);
CREATE INDEX IF NOT EXISTS idx_sentiments_article_id ON sentiments(article_id);
CREATE INDEX IF NOT EXISTS idx_sentiments_label ON sentiments(label);
CREATE INDEX IF NOT EXISTS idx_sentiments_score ON sentiments(score DESC);
CREATE INDEX IF NOT EXISTS idx_keyword_articles_keyword_id ON keyword_articles(keyword_id);
CREATE INDEX IF NOT EXISTS idx_keyword_articles_article_id ON keyword_articles(article_id);
CREATE INDEX IF NOT EXISTS idx_keyword_articles_created_at ON keyword_articles(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_keyword_articles_match_score ON keyword_articles(match_score DESC);
CREATE INDEX IF NOT EXISTS idx_keywords_user_id ON keywords(user_id);
CREATE INDEX IF NOT EXISTS idx_keywords_status ON keywords(status);
CREATE INDEX IF NOT EXISTS idx_keywords_text ON keywords(text);
CREATE INDEX IF NOT EXISTS idx_keywords_created_at ON keywords(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_actions_user_id ON user_actions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_actions_article_id ON user_actions(article_id);
CREATE INDEX IF NOT EXISTS idx_user_actions_user_article ON user_actions(user_id, article_id);
CREATE INDEX IF NOT EXISTS idx_user_actions_action ON user_actions(action);
CREATE INDEX IF NOT EXISTS idx_user_actions_created_at ON user_actions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_share_history_user_id ON share_history(user_id);
CREATE INDEX IF NOT EXISTS idx_share_history_article_id ON share_history(article_id);
CREATE INDEX IF NOT EXISTS idx_share_history_keyword_id ON share_history(keyword_id);
CREATE INDEX IF NOT EXISTS idx_share_history_user_keyword ON share_history(user_id, keyword_id);
CREATE INDEX IF NOT EXISTS idx_share_history_shared_at ON share_history(shared_at DESC);
CREATE INDEX IF NOT EXISTS idx_share_history_channel ON share_history(channel);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at DESC);

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


