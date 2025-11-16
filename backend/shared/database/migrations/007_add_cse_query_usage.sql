-- Google CSE 쿼리 사용량 추적 테이블 추가
-- 유저별/키워드별 일일 쿼리 사용량을 기록하여 제한 관리에 활용

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

-- updated_at 자동 갱신 트리거
DROP TRIGGER IF EXISTS update_cse_query_usage_updated_at ON cse_query_usage;
CREATE TRIGGER update_cse_query_usage_updated_at
    BEFORE UPDATE ON cse_query_usage
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();









