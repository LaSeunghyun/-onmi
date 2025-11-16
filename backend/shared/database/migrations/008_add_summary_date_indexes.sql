-- summary_sessions 날짜별 조회 최적화를 위한 인덱스 추가
BEGIN;

CREATE INDEX IF NOT EXISTS idx_summary_sessions_user_date
    ON summary_sessions (user_id, (DATE(created_at)));

CREATE INDEX IF NOT EXISTS idx_summary_sessions_user_type_date
    ON summary_sessions (user_id, summary_type, (DATE(created_at)));

CREATE INDEX IF NOT EXISTS idx_summary_sessions_keyword_date
    ON summary_sessions (keyword_id, (DATE(created_at)))
    WHERE keyword_id IS NOT NULL;

COMMIT;








