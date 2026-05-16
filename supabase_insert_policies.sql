-- Políticas de INSERT/UPDATE para el cliente anon
-- Esto permite que el scraper pueda escribir datos

-- FB Posts: allow insert/upsert
DROP POLICY IF EXISTS "Allow anon read" ON fb_posts;
CREATE POLICY "Allow anon read" ON fb_posts FOR SELECT USING (true);
CREATE POLICY "Allow anon insert" ON fb_posts FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow anon upsert" ON fb_posts FOR UPDATE USING (true);

-- TT Posts
DROP POLICY IF EXISTS "Allow anon read" ON tt_posts;
CREATE POLICY "Allow anon read" ON tt_posts FOR SELECT USING (true);
CREATE POLICY "Allow anon insert" ON tt_posts FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow anon upsert" ON tt_posts FOR UPDATE USING (true);

-- FB Comments
DROP POLICY IF EXISTS "Allow anon read" ON fb_comments;
CREATE POLICY "Allow anon read" ON fb_comments FOR SELECT USING (true);
CREATE POLICY "Allow anon insert" ON fb_comments FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow anon upsert" ON fb_comments FOR UPDATE USING (true);

-- TT Comments
DROP POLICY IF EXISTS "Allow anon read" ON tt_comments;
CREATE POLICY "Allow anon read" ON tt_comments FOR SELECT USING (true);
CREATE POLICY "Allow anon insert" ON tt_comments FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow anon upsert" ON tt_comments FOR UPDATE USING (true);

-- Daily Metrics
DROP POLICY IF EXISTS "Allow anon read" ON daily_metrics;
CREATE POLICY "Allow anon read" ON daily_metrics FOR SELECT USING (true);
CREATE POLICY "Allow anon insert" ON daily_metrics FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow anon upsert" ON daily_metrics FOR UPDATE USING (true);

-- Insights
DROP POLICY IF EXISTS "Allow anon read" ON insights;
CREATE POLICY "Allow anon read" ON insights FOR SELECT USING (true);
CREATE POLICY "Allow anon insert" ON insights FOR INSERT WITH CHECK (true);

-- Problematicas
DROP POLICY IF EXISTS "Allow anon read" ON problematicas;
CREATE POLICY "Allow anon read" ON problematicas FOR SELECT USING (true);
CREATE POLICY "Allow anon insert" ON problematicas FOR INSERT WITH CHECK (true);

-- Zonas (solo lectura)
DROP POLICY IF EXISTS "Allow anon read" ON zonas;
CREATE POLICY "Allow anon read" ON zonas FOR SELECT USING (true);

-- Topics (solo lectura)
DROP POLICY IF EXISTS "Allow anon read" ON topics;
CREATE POLICY "Allow anon read" ON topics FOR SELECT USING (true);

SELECT 'Políticas actualizadas correctamente!' as status;