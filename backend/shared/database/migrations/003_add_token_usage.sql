-- 토큰 사용량 추적 테이블 (시스템 전체 공통)
-- 일일 토큰 사용량을 추적하여 시스템 전체 제한을 관리

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

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_token_usage_date ON token_usage(date DESC);
CREATE INDEX IF NOT EXISTS idx_token_usage_updated_at ON token_usage(updated_at DESC);

-- updated_at 자동 갱신 트리거
DROP TRIGGER IF EXISTS update_token_usage_updated_at ON token_usage;
CREATE TRIGGER update_token_usage_updated_at
    BEFORE UPDATE ON token_usage
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();







