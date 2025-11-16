-- OAuth 로그인 지원을 위한 users 테이블 수정
-- password_hash를 NULL 허용으로 변경 (OAuth 사용자는 비밀번호 없음)
-- OAuth 관련 필드 추가

-- password_hash를 NULL 허용으로 변경
ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL;

-- OAuth 필드 추가
ALTER TABLE users ADD COLUMN IF NOT EXISTS oauth_provider VARCHAR(20);
ALTER TABLE users ADD COLUMN IF NOT EXISTS oauth_id VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS oauth_email VARCHAR(255);

-- OAuth 사용자 식별을 위한 인덱스
CREATE INDEX IF NOT EXISTS idx_users_oauth ON users(oauth_provider, oauth_id);

-- OAuth 이메일 인덱스 (이메일로 OAuth 사용자 조회 최적화)
CREATE INDEX IF NOT EXISTS idx_users_oauth_email ON users(oauth_email);

-- 제약조건: OAuth 사용자는 oauth_provider와 oauth_id가 있어야 함
-- 일반 사용자는 password_hash가 있어야 함
-- (애플리케이션 레벨에서 검증)









