-- Supabase Schema for scrapeo-social v2.0
-- Ejecutar este SQL en el SQL Editor de Supabase

-- ============================================
-- TABLAS PRINCIPALES
-- ============================================

-- Posts de Facebook
CREATE TABLE fb_posts (
    id TEXT PRIMARY KEY,
    page_id TEXT NOT NULL,
    page_name TEXT,
    message TEXT,
    created_time TIMESTAMPTZ,
    likes_count INTEGER DEFAULT 0,
    loves_count INTEGER DEFAULT 0,
    hahas_count INTEGER DEFAULT 0,
    wows_count INTEGER DEFAULT 0,
    sads_count INTEGER DEFAULT 0,
    angrys_count INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    shares_count INTEGER DEFAULT 0,
    post_url TEXT,
    source TEXT DEFAULT 'graph_api',
    sentiment TEXT DEFAULT '',
    sentiment_score FLOAT DEFAULT 0.0,
    topic_category TEXT,
    topics_detected JSONB,
    scraped_at TIMESTAMPTZ DEFAULT NOW()
);

-- Comments de Facebook
CREATE TABLE fb_comments (
    id TEXT PRIMARY KEY,
    post_id TEXT NOT NULL,
    message TEXT,
    author_name TEXT,
    created_time TIMESTAMPTZ,
    like_count INTEGER DEFAULT 0,
    sentiment TEXT DEFAULT '',
    sentiment_score FLOAT DEFAULT 0.0,
    topic_category TEXT,
    zone_detected TEXT,
    issue_keywords JSONB,
    scraped_at TIMESTAMPTZ DEFAULT NOW()
);

-- Posts de TikTok
CREATE TABLE tt_posts (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    description TEXT,
    create_time TIMESTAMPTZ,
    likes_count INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    shares_count INTEGER DEFAULT 0,
    views_count INTEGER DEFAULT 0,
    video_url TEXT,
    sentiment TEXT DEFAULT '',
    sentiment_score FLOAT DEFAULT 0.0,
    topic_category TEXT,
    topics_detected JSONB,
    scraped_at TIMESTAMPTZ DEFAULT NOW()
);

-- Comments de TikTok
CREATE TABLE tt_comments (
    id TEXT PRIMARY KEY,
    video_id TEXT NOT NULL,
    message TEXT,
    author_name TEXT,
    create_time TIMESTAMPTZ,
    likes_count INTEGER DEFAULT 0,
    sentiment TEXT DEFAULT '',
    sentiment_score FLOAT DEFAULT 0.0,
    topic_category TEXT,
    zone_detected TEXT,
    issue_keywords JSONB,
    scraped_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- TABLAS DE ANÁLISIS
-- ============================================

-- Topics por zona (agregado)
CREATE TABLE zone_topics (
    id SERIAL PRIMARY KEY,
    zone TEXT NOT NULL,
    topic_category TEXT NOT NULL,
    mention_count INTEGER DEFAULT 0,
    positive_count INTEGER DEFAULT 0,
    negative_count INTEGER DEFAULT 0,
    neutral_count INTEGER DEFAULT 0,
    avg_sentiment_score FLOAT DEFAULT 0.0,
    trend_percentage FLOAT DEFAULT 0.0,
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(zone, topic_category)
);

-- Key Insights generados
CREATE TABLE insights (
    id SERIAL PRIMARY KEY,
    insight_type TEXT NOT NULL,
    post_id TEXT,
    topic_category TEXT,
    zone TEXT,
    description TEXT NOT NULL,
    sentiment TEXT,
    urgency_score FLOAT,
    action_recommendation TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Métricas diarias
CREATE TABLE daily_metrics (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    platform TEXT NOT NULL,
    total_posts INTEGER DEFAULT 0,
    total_comments INTEGER DEFAULT 0,
    total_reactions INTEGER DEFAULT 0,
    positive_pct FLOAT DEFAULT 0.0,
    negative_pct FLOAT DEFAULT 0.0,
    neutral_pct FLOAT DEFAULT 0.0,
    nsi_score FLOAT DEFAULT 0.0,
    cai_score FLOAT DEFAULT 0.0,
    top_topics JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- ÍNDICES PARA PERFORMANCE
-- ============================================

CREATE INDEX idx_fb_posts_created ON fb_posts(created_time);
CREATE INDEX idx_fb_posts_sentiment ON fb_posts(sentiment);
CREATE INDEX idx_fb_posts_topic ON fb_posts(topic_category);
CREATE INDEX idx_fb_comments_post ON fb_comments(post_id);
CREATE INDEX idx_fb_comments_zone ON fb_comments(zone_detected);
CREATE INDEX idx_fb_comments_topic ON fb_comments(topic_category);

CREATE INDEX idx_tt_posts_created ON tt_posts(create_time);
CREATE INDEX idx_tt_posts_sentiment ON tt_posts(sentiment);
CREATE INDEX idx_tt_posts_topic ON tt_posts(topic_category);
CREATE INDEX idx_tt_comments_video ON tt_comments(video_id);
CREATE INDEX idx_tt_comments_zone ON tt_comments(zone_detected);

CREATE INDEX idx_zone_topics_zone ON zone_topics(zone);
CREATE INDEX idx_insights_created ON insights(created_at);
CREATE INDEX idx_daily_metrics_date ON daily_metrics(date);

-- ============================================
-- FUNCIONES ÚTILES
-- ============================================

-- Obtener topics más mencionados por zona
CREATE OR REPLACE FUNCTION get_zone_topics(p_zone TEXT, p_days INTEGER DEFAULT 30)
RETURNS TABLE(
    topic_category TEXT,
    mention_count INTEGER,
    sentiment TEXT,
    trend_pct FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        fc.topic_category,
        COUNT(*)::INTEGER as mention_count,
        CASE
            WHEN AVG(CASE fc.sentiment WHEN 'positive' THEN 1 WHEN 'negative' THEN -1 ELSE 0 END) > 0.2 THEN 'positive'
            WHEN AVG(CASE fc.sentiment WHEN 'positive' THEN 1 WHEN 'negative' THEN -1 ELSE 0 END) < -0.2 THEN 'negative'
            ELSE 'neutral'
        END::TEXT as sentiment,
        0.0::FLOAT as trend_pct
    FROM fb_comments fc
    WHERE fc.zone_detected = p_zone
        AND fc.created_time >= NOW() - (p_days || ' days')::INTERVAL
        AND fc.topic_category IS NOT NULL
    GROUP BY fc.topic_category
    ORDER BY mention_count DESC;
END;
$$ LANGUAGE plpgsql;

-- Calcular NSI (Net Sentiment Index)
CREATE OR REPLACE FUNCTION calculate_nsi(p_platform TEXT, p_days INTEGER DEFAULT 30)
RETURNS FLOAT AS $$
DECLARE
    total INTEGER;
    positives INTEGER;
    negatives INTEGER;
BEGIN
    IF p_platform = 'facebook' THEN
        SELECT COUNT(*), 
               COUNT(*) FILTER (WHERE sentiment = 'positive'),
               COUNT(*) FILTER (WHERE sentiment = 'negative')
        INTO total, positives, negatives
        FROM fb_posts
        WHERE created_time >= NOW() - (p_days || ' days')::INTERVAL
          AND sentiment IN ('positive', 'negative', 'neutral');
    ELSE
        SELECT COUNT(*),
               COUNT(*) FILTER (WHERE sentiment = 'positive'),
               COUNT(*) FILTER (WHERE sentiment = 'negative')
        INTO total, positives, negatives
        FROM tt_posts
        WHERE create_time >= NOW() - (p_days || ' days')::INTERVAL
          AND sentiment IN ('positive', 'negative', 'neutral');
    END IF;

    IF total = 0 THEN RETURN 0; END IF;

    RETURN ROUND(((positives::FLOAT / total) - (negatives::FLOAT / total)) * 100, 2);
END;
$$ LANGUAGE plpgsql;