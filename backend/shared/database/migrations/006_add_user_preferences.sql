-- 사용자 선호도 테이블
-- 사용자별 설정 정보 저장 (알림 시간 등)

CREATE TABLE IF NOT EXISTS user_preferences (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    preferences JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id ON user_preferences(user_id);
CREATE INDEX IF NOT EXISTS idx_user_preferences_updated_at ON user_preferences(updated_at DESC);

-- updated_at 자동 갱신 트리거
DROP TRIGGER IF EXISTS update_user_preferences_updated_at ON user_preferences;
CREATE TRIGGER update_user_preferences_updated_at
    BEFORE UPDATE ON user_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- preferences JSONB 필드에 GIN 인덱스 추가 (JSONB 쿼리 최적화)
CREATE INDEX IF NOT EXISTS idx_user_preferences_preferences_gin ON user_preferences USING GIN (preferences);

-- 알림 시간 조회를 위한 함수형 인덱스 (notification_time_hour 필드)
CREATE INDEX IF NOT EXISTS idx_user_preferences_notification_time 
    ON user_preferences ((preferences->>'notification_time_hour'));

