-- 가입 방식 구분 컬럼 추가
-- 로컬 가입, Google 가입, 카카오 가입 등을 구분하기 위한 컬럼

-- auth_type 컬럼 추가 (기본값: 'local' - 기존 사용자는 로컬 가입으로 간주)
ALTER TABLE users ADD COLUMN IF NOT EXISTS auth_type VARCHAR(20) DEFAULT 'local';

-- 제약조건 추가
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_auth_type_check;
ALTER TABLE users ADD CONSTRAINT users_auth_type_check 
    CHECK (auth_type IN ('local', 'google', 'kakao', 'apple'));

-- 인덱스 추가 (auth_type으로 조회 최적화)
CREATE INDEX IF NOT EXISTS idx_users_auth_type ON users(auth_type);

-- 기존 OAuth 사용자 업데이트 (oauth_provider가 있으면 해당 값으로 설정)
UPDATE users 
SET auth_type = CASE 
    WHEN oauth_provider = 'google' THEN 'google'
    WHEN oauth_provider = 'kakao' THEN 'kakao'
    WHEN oauth_provider = 'apple' THEN 'apple'
    ELSE 'local'
END
WHERE auth_type = 'local' AND oauth_provider IS NOT NULL;









