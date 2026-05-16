-- ============================================
-- SCRAPEO-SOCIAL v2.0 - Schema para Supabase
-- ============================================

-- Tablas principales

-- Posts de Facebook
CREATE TABLE fb_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id TEXT UNIQUE NOT NULL,
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
    sentiment TEXT CHECK (sentiment IN ('positive', 'negative', 'neutral', '')),
    sentiment_score FLOAT DEFAULT 0,
    topic_category TEXT,
    zona TEXT,
    scraped_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Posts de TikTok
CREATE TABLE tt_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id TEXT UNIQUE NOT NULL,
    username TEXT NOT NULL,
    description TEXT,
    create_time TIMESTAMPTZ,
    likes_count INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    shares_count INTEGER DEFAULT 0,
    views_count INTEGER DEFAULT 0,
    video_url TEXT,
    sentiment TEXT CHECK (sentiment IN ('positive', 'negative', 'neutral', '')),
    sentiment_score FLOAT DEFAULT 0,
    topic_category TEXT,
    zona TEXT,
    scraped_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Comentarios de Facebook
CREATE TABLE fb_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    comment_id TEXT UNIQUE NOT NULL,
    post_id TEXT NOT NULL,
    message TEXT,
    author_name TEXT,
    created_time TIMESTAMPTZ,
    like_count INTEGER DEFAULT 0,
    sentiment TEXT CHECK (sentiment IN ('positive', 'negative', 'neutral', '')),
    sentiment_score FLOAT DEFAULT 0,
    topic_category TEXT,
    zona TEXT,
    problematicas JSONB,
    scraped_at TIMESTAMPTZ DEFAULT NOW()
);

-- Comentarios de TikTok
CREATE TABLE tt_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    comment_id TEXT UNIQUE NOT NULL,
    video_id TEXT NOT NULL,
    message TEXT,
    author_name TEXT,
    create_time TIMESTAMPTZ,
    like_count INTEGER DEFAULT 0,
    sentiment TEXT CHECK (sentiment IN ('positive', 'negative', 'neutral', '')),
    sentiment_score FLOAT DEFAULT 0,
    topic_category TEXT,
    zona TEXT,
    problematicas JSONB,
    scraped_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tablas de análisis

-- Métricas diarias calculadas
CREATE TABLE daily_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform TEXT NOT NULL,
    date DATE NOT NULL,
    total_posts INTEGER DEFAULT 0,
    total_comments INTEGER DEFAULT 0,
    total_reactions INTEGER DEFAULT 0,
    positive_pct FLOAT DEFAULT 0,
    negative_pct FLOAT DEFAULT 0,
    neutral_pct FLOAT DEFAULT 0,
    nsi FLOAT DEFAULT 0,
    cai FLOAT DEFAULT 0,
    top_topics JSONB,
    top_problematicas JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(platform, date)
);

-- Problemáticas detectadas (issue tracking)
CREATE TABLE problematicas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform TEXT NOT NULL,
    post_id TEXT,
    comment_id TEXT,
    topic TEXT NOT NULL,
    zona TEXT,
    message TEXT,
    sentiment TEXT,
    sentiment_score FLOAT,
    detected_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insights generados automáticamente
CREATE TABLE insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    insight_type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    topic TEXT,
    zona TEXT,
    sentiment TEXT,
    priority INTEGER DEFAULT 0,
    post_id TEXT,
    metric_data JSONB,
    generated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Zonas de Santa Ana
CREATE TABLE zonas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre TEXT UNIQUE NOT NULL,
    keywords TEXT[],
    coord_bounds JSONB,
    active BOOLEAN DEFAULT TRUE
);

-- Topic taxonomy
CREATE TABLE topics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category TEXT UNIQUE NOT NULL,
    keywords TEXT[],
    is_emergency BOOLEAN DEFAULT FALSE,
    weight INTEGER DEFAULT 1
);

-- ============================================
-- ÍNDICES PARA MEJORAR PERFORMANCE
-- ============================================

CREATE INDEX idx_fb_posts_created ON fb_posts(created_time DESC);
CREATE INDEX idx_fb_posts_sentiment ON fb_posts(sentiment);
CREATE INDEX idx_fb_posts_topic ON fb_posts(topic_category);
CREATE INDEX idx_fb_posts_zona ON fb_posts(zona);

CREATE INDEX idx_tt_posts_created ON tt_posts(create_time DESC);
CREATE INDEX idx_tt_posts_sentiment ON tt_posts(sentiment);
CREATE INDEX idx_tt_posts_topic ON tt_posts(topic_category);

CREATE INDEX idx_fb_comments_post ON fb_comments(post_id);
CREATE INDEX idx_fb_comments_zona ON fb_comments(zona);
CREATE INDEX idx_fb_comments_topic ON fb_comments(topic_category);

CREATE INDEX idx_tt_comments_video ON tt_comments(video_id);

CREATE INDEX idx_daily_metrics_date ON daily_metrics(date DESC);
CREATE INDEX idx_problematicas_topic ON problematicas(topic);
CREATE INDEX idx_problematicas_zona ON problematicas(zona);
CREATE INDEX idx_problematicas_detected ON problematicas(detected_at DESC);

CREATE INDEX idx_insights_priority ON insights(priority DESC);
CREATE INDEX idx_insights_generated ON insights(generated_at DESC);

-- ============================================
-- SEED DATA: Zonas de Santa Ana
-- ============================================

INSERT INTO zonas (nombre, keywords) VALUES
('Norte', ARRAY['norte', 'norte de santa ana', 'villa jardín', 'urbanización norte', 'barrio norte', 'sector norte']),
('Sur', ARRAY['sur', 'sur de santa ana', 'colonia sur', 'sector sur']),
('Centro', ARRAY['centro', 'city center', 'downtown', 'casco urbano']),
('Este', ARRAY['este', 'este de santa ana', 'sector este']),
('Oeste', ARRAY['oeste', 'west', 'sector oeste']);

-- ============================================
-- SEED DATA: Topic Taxonomy Municipal
-- ============================================

INSERT INTO topics (category, keywords, is_emergency, weight) VALUES
('obras_publicas', ARRAY['bache', 'baches', 'calle', 'calles', 'carpeta', 'asfalto', 'puente', '路灯', 'parque', '广场', 'obra', 'obras', 'cordón', 'summo'], FALSE, 3),
('seguridad', ARRAY['robo', 'robos', 'asalto', 'asaltos', 'delincuencia', 'delincuente', 'seguridad', 'policía', 'crimen', 'matar', 'muerte', 'asesinato', 'pandilla', 'extorsión'], TRUE, 5),
('servicios_publicos', ARRAY['agua', 'luz', 'electricidad', 'basura', 'recolección', 'servicio', 'corte', 'servicios', 'tubería', 'alcantarillado', 'desague'], FALSE, 4),
('empleo', ARRAY['trabajo', 'empleo', 'desempleo', 'desempleado', 'negocio', 'negocios', 'empresa', 'empresas', 'trabajador', 'patrón'], FALSE, 3),
('salud', ARRAY['hospital', 'hospìtal', 'clínica', 'doctor', 'doctora', 'salud', 'enfermedad', 'enfermo', 'consulta', 'médico'], FALSE, 4),
('educacion', ARRAY['escuela', 'colegio', 'educación', 'educacion', 'maestro', 'maestra', 'estudiante', 'alumno', 'clase'], FALSE, 3),
('movilidad', ARRAY['tráfico', 'trafico', 'transito', 'tránsito', 'carro', 'carros', 'vehículo', 'bus', 'buses', 'ruta', 'parada', 'semáforo', 'semaforo'], FALSE, 2),
('corrupcion', ARRAY['corrupto', 'corrupta', 'corrupción', 'robo', 'ladrón', 'ladrones', 'mentira', 'mentiras', 'fraude', 'desvío'], TRUE, 5),
('medio_ambiente', ARRAY['contaminación', 'basura', 'río', 'arbol', 'árbol', 'verde', 'contaminacion', 'ambiente', 'ecología', 'ecologia'], FALSE, 2),
('transparencia', ARRAY['información', 'informacion', 'transparente', 'donde está', 'gasto', 'gastos', 'presupuesto', 'informe'], FALSE, 3);

-- ============================================
-- FUNCIONES ÚTILES
-- ============================================

-- Función para calcular NSI (Net Sentiment Index)
CREATE OR REPLACE FUNCTION calculate_nsi(
    positive_pct FLOAT,
    negative_pct FLOAT
) RETURNS FLOAT AS $$
BEGIN
    RETURN (positive_pct - negative_pct);
END;
$$ LANGUAGE plpgsql;

-- Función para obtener métricas por zona
CREATE OR REPLACE FUNCTION get_zone_metrics(
    p_platform TEXT,
    p_topic TEXT,
    p_days INTEGER DEFAULT 30
) RETURNS TABLE (
    zona TEXT,
    count INTEGER,
    positive_pct FLOAT,
    negative_pct FLOAT,
    sentiment TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.zona,
        COUNT(*)::INTEGER as count,
        ROUND(AVG(CASE WHEN p.sentiment = 'positive' THEN 100.0 ELSE 0 END)::numeric, 2) as positive_pct,
        ROUND(AVG(CASE WHEN p.sentiment = 'negative' THEN 100.0 ELSE 0 END)::numeric, 2) as negative_pct,
        CASE 
            WHEN AVG(CASE WHEN p.sentiment = 'positive' THEN 1.0 ELSE 0 END) > AVG(CASE WHEN p.sentiment = 'negative' THEN 1.0 ELSE 0 END)
            THEN 'positive'
            WHEN AVG(CASE WHEN p.sentiment = 'negative' THEN 1.0 ELSE 0 END) > AVG(CASE WHEN p.sentiment = 'positive' THEN 1.0 ELSE 0 END)
            THEN 'negative'
            ELSE 'neutral'
        END as sentiment
    FROM (
        SELECT 'fb' as platform, zona, sentiment FROM fb_posts WHERE created_time > NOW() - (p_days || ' days')::INTERVAL
        UNION ALL
        SELECT 'tt' as platform, zona, sentiment FROM tt_posts WHERE create_time > NOW() - (p_days || ' days')::INTERVAL
    ) p
    WHERE p.platform = p_platform
    AND (p.topic IS NULL OR p.topic = p_topic)
    GROUP BY p.zona;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- VISTAS PARA DASHBOARD
-- ============================================

-- Vista: Resumen ejecutivo diaria
CREATE OR REPLACE VIEW executive_summary AS
SELECT 
    platform,
    date,
    total_posts,
    total_comments,
    positive_pct,
    negative_pct,
    nsi,
    cai
FROM daily_metrics
ORDER BY date DESC, platform;

-- Vista: Problemáticas por zona (últimos 30 días)
CREATE VIEW problematicas_by_zone AS
SELECT 
    zona,
    topic,
    COUNT(*) as mentions,
    ROUND(AVG(sentiment_score)::numeric, 3) as avg_sentiment,
    COUNT(*) FILTER (WHERE sentiment = 'negative') as negative_count,
    COUNT(*) FILTER (WHERE sentiment = 'positive') as positive_count
FROM problematicas
WHERE detected_at > NOW() - '30 days'::INTERVAL
GROUP BY zona, topic
ORDER BY mentions DESC;

-- Vista: Top insights del día
CREATE VIEW top_insights AS
SELECT 
    title,
    description,
    topic,
    zona,
    priority,
    generated_at
FROM insights
WHERE generated_at > NOW() - '24 hours'::INTERVAL
ORDER BY priority DESC, generated_at DESC
LIMIT 10;

-- Habilitar Row Level Security (opcional para más seguridad)
ALTER TABLE fb_posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE tt_posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE fb_comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE tt_comments ENABLE ROW LEVEL SECURITY;

-- Policy simple para anon (el dashboard puede leer)
CREATE POLICY "Allow anon read" ON fb_posts FOR SELECT USING (true);
CREATE POLICY "Allow anon read" ON tt_posts FOR SELECT USING (true);
CREATE POLICY "Allow anon read" ON fb_comments FOR SELECT USING (true);
CREATE POLICY "Allow anon read" ON tt_comments FOR SELECT USING (true);
CREATE POLICY "Allow anon read" ON daily_metrics FOR SELECT USING (true);
CREATE POLICY "Allow anon read" ON insights FOR SELECT USING (true);
CREATE POLICY "Allow anon read" ON problematicas FOR SELECT USING (true);
CREATE POLICY "Allow anon read" ON zonas FOR SELECT USING (true);
CREATE POLICY "Allow anon read" ON topics FOR SELECT USING (true);

-- ============================================
-- COMPLETADO
-- ============================================

SELECT 'Schema creado exitosamente!' as status;