-- 샘플 데이터 생성 SQL 스크립트

-- 1. 테스트 사용자 생성 (비밀번호: test1234의 해시값)
INSERT INTO users (email, password_hash, locale)
VALUES ('test@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYz5Y5Y5Y5Y', 'ko-KR')
ON CONFLICT (email) DO NOTHING;

-- 2. 키워드 생성
DO $$
DECLARE
    v_user_id UUID;
    v_keyword1_id UUID;
    v_keyword2_id UUID;
    v_keyword3_id UUID;
    v_article1_id UUID;
    v_article2_id UUID;
    v_article3_id UUID;
    v_article4_id UUID;
    v_article5_id UUID;
BEGIN
    -- 사용자 ID 가져오기
    SELECT id INTO v_user_id FROM users WHERE email = 'test@example.com';
    
    -- 키워드 생성
    INSERT INTO keywords (user_id, text, status, notify_level)
    VALUES 
        (v_user_id, 'AI', 'active', 'standard'),
        (v_user_id, 'Blockchain', 'active', 'standard'),
        (v_user_id, 'Climate', 'active', 'high')
    ON CONFLICT DO NOTHING;
    
    -- 키워드 ID 가져오기
    SELECT id INTO v_keyword1_id FROM keywords WHERE user_id = v_user_id AND text = 'AI';
    SELECT id INTO v_keyword2_id FROM keywords WHERE user_id = v_user_id AND text = 'Blockchain';
    SELECT id INTO v_keyword3_id FROM keywords WHERE user_id = v_user_id AND text = 'Climate';
    
    -- 기사 생성
    INSERT INTO articles (url, source, title, snippet, published_at, lang)
    VALUES 
        ('https://example.com/article1', 'Tech News', 'The Future of AI: GPT Model Development', 
         'AI technology is rapidly advancing, especially large language models are improving.',
         NOW() - INTERVAL '1 day', 'ko'),
        ('https://example.com/article2', 'Crypto Daily', 'New Leap in Blockchain Technology',
         'Blockchain technology is being applied to various industries beyond finance.',
         NOW() - INTERVAL '2 days', 'ko'),
        ('https://example.com/article3', 'Environment Today', 'Global Cooperation for Climate Change',
         'The world is cooperating to solve climate change issues and efforts are underway to achieve carbon neutrality.',
         NOW() - INTERVAL '5 hours', 'ko'),
        ('https://example.com/article4', 'Tech News', 'How AI Will Change Jobs',
         'Many jobs are changing due to AI development, with new opportunities and challenges emerging.',
         NOW() - INTERVAL '10 hours', 'ko'),
        ('https://example.com/article5', 'Crypto Daily', 'Digital Asset Regulation Status',
         'Regulation of blockchain-based digital assets is being discussed globally.',
         NOW() - INTERVAL '3 days', 'ko')
    ON CONFLICT (url) DO NOTHING;
    
    -- 기사 ID 가져오기
    SELECT id INTO v_article1_id FROM articles WHERE url = 'https://example.com/article1';
    SELECT id INTO v_article2_id FROM articles WHERE url = 'https://example.com/article2';
    SELECT id INTO v_article3_id FROM articles WHERE url = 'https://example.com/article3';
    SELECT id INTO v_article4_id FROM articles WHERE url = 'https://example.com/article4';
    SELECT id INTO v_article5_id FROM articles WHERE url = 'https://example.com/article5';
    
    -- 감정 분석 결과 생성
    INSERT INTO sentiments (article_id, label, score, rationale, model_ver)
    VALUES 
        (v_article1_id, 'positive', 0.85, '{"reason": "Positive outlook and development potential"}'::jsonb, 'rule-based-v1'),
        (v_article2_id, 'positive', 0.72, '{"reason": "Positive evaluation of technological innovation"}'::jsonb, 'rule-based-v1'),
        (v_article3_id, 'neutral', 0.55, '{"reason": "Objective information"}'::jsonb, 'rule-based-v1'),
        (v_article4_id, 'positive', 0.78, '{"reason": "Positive view on future opportunities"}'::jsonb, 'rule-based-v1'),
        (v_article5_id, 'neutral', 0.50, '{"reason": "Neutral reporting on regulation"}'::jsonb, 'rule-based-v1')
    ON CONFLICT (article_id) DO UPDATE SET label = EXCLUDED.label, score = EXCLUDED.score;
    
    -- 키워드-기사 매핑 생성
    INSERT INTO keyword_articles (keyword_id, article_id, match_score, match_type)
    VALUES 
        (v_keyword1_id, v_article1_id, 1.0, 'exact'),
        (v_keyword1_id, v_article4_id, 1.0, 'exact'),
        (v_keyword2_id, v_article2_id, 1.0, 'exact'),
        (v_keyword2_id, v_article5_id, 1.0, 'exact'),
        (v_keyword3_id, v_article3_id, 1.0, 'exact')
    ON CONFLICT (keyword_id, article_id) DO NOTHING;
    
    RAISE NOTICE 'Sample data created successfully!';
    RAISE NOTICE 'Created data:';
    RAISE NOTICE '  - Users: 1 (test@example.com)';
    RAISE NOTICE '  - Keywords: 3';
    RAISE NOTICE '  - Articles: 5';
    RAISE NOTICE '  - Sentiments: 5';
    RAISE NOTICE '  - Keyword-Article mappings: 5';
END $$;

