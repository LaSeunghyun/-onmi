-- 수집 이력 및 요약 관련 테이블 추가
-- fetch_history: 키워드별 수집 이력 추적
-- summary_sessions: 요약 세션 관리
-- summary_feedback: 요약 피드백 관리

-- ============================================
-- fetch_history 테이블
-- ============================================
CREATE TABLE IF NOT EXISTS fetch_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    keyword_id UUID NOT NULL REFERENCES keywords(id) ON DELETE CASCADE,
    requested_start TIMESTAMPTZ NOT NULL,
    requested_end TIMESTAMPTZ NOT NULL,
    actual_start TIMESTAMPTZ NOT NULL,
    actual_end TIMESTAMPTZ NOT NULL,
    articles_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT fetch_history_articles_count_check CHECK (articles_count >= 0)
);

-- fetch_history 인덱스
CREATE INDEX IF NOT EXISTS idx_fetch_history_keyword_id ON fetch_history(keyword_id);
CREATE INDEX IF NOT EXISTS idx_fetch_history_actual_start ON fetch_history(actual_start DESC);
CREATE INDEX IF NOT EXISTS idx_fetch_history_actual_end ON fetch_history(actual_end DESC);
CREATE INDEX IF NOT EXISTS idx_fetch_history_keyword_actual_range ON fetch_history(keyword_id, actual_start, actual_end);
CREATE INDEX IF NOT EXISTS idx_fetch_history_created_at ON fetch_history(created_at DESC);

-- ============================================
-- summary_sessions 테이블
-- ============================================
CREATE TABLE IF NOT EXISTS summary_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    keyword_id UUID REFERENCES keywords(id) ON DELETE SET NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    summary_text TEXT NOT NULL,
    summary_type VARCHAR(20) NOT NULL,
    summarization_config JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT summary_sessions_summary_type_check CHECK (summary_type IN ('daily', 'keyword'))
);

-- summary_sessions 인덱스
CREATE INDEX IF NOT EXISTS idx_summary_sessions_user_id ON summary_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_summary_sessions_keyword_id ON summary_sessions(keyword_id);
CREATE INDEX IF NOT EXISTS idx_summary_sessions_user_keyword ON summary_sessions(user_id, keyword_id);
CREATE INDEX IF NOT EXISTS idx_summary_sessions_summary_type ON summary_sessions(summary_type);
CREATE INDEX IF NOT EXISTS idx_summary_sessions_created_at ON summary_sessions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_summary_sessions_user_type_created ON summary_sessions(user_id, summary_type, created_at DESC);

-- ============================================
-- summary_feedback 테이블
-- ============================================
CREATE TABLE IF NOT EXISTS summary_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    summary_session_id UUID NOT NULL REFERENCES summary_sessions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL,
    comment TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT summary_feedback_rating_check CHECK (rating >= 1 AND rating <= 5)
);

-- summary_feedback 인덱스
CREATE INDEX IF NOT EXISTS idx_summary_feedback_session_id ON summary_feedback(summary_session_id);
CREATE INDEX IF NOT EXISTS idx_summary_feedback_user_id ON summary_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_summary_feedback_user_session ON summary_feedback(user_id, summary_session_id);
CREATE INDEX IF NOT EXISTS idx_summary_feedback_rating ON summary_feedback(rating);
CREATE INDEX IF NOT EXISTS idx_summary_feedback_created_at ON summary_feedback(created_at DESC);

