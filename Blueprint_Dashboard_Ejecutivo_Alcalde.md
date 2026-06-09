# Blueprint: Dashboard Ejecutivo de Inteligencia Ciudadana

**Proyecto:** Análisis de redes sociales del alcalde y alcaldía | Facebook + TikTok | 20K+ posts | 1 año de datos | SQLite  
**Metodología:** Inspirada en Cambridge Analytica — adaptada a datos agregados por post.  
**Destino:** Documento de especificación para agente de IA desarrollador.

---

## 0. Contexto y limitación metodológica clave

Cambridge Analytica perfilaba **individuos** (usuario → score OCEAN). Este proyecto tiene datos **agregados por post** (post → total de reacciones). Por eso no se construye OCEAN individual. En cambio se construye el equivalente funcional para un alcalde: **perfilamiento de temas y emociones colectivas**.

| Dimensión | Cambridge Analytica original | Este proyecto |
|---|---|---|
| Unidad de análisis | Usuario individual | Post / pieza de contenido |
| Input principal | Likes por usuario (quién dio like a qué) | Reacciones por post (cuántos likes tuvo) |
| Output principal | Score OCEAN por persona | Score emocional + temático por post/período |
| Segmentación | Audiencias por personalidad | Clusters de contenido por patrón de reacción |
| Fuente de texto | Perfil y actividad del usuario | Texto del post + comentarios |
| Validez científica | Probada (Kosinski 2013) | Válida para análisis de contenido y sentimiento |

---

## 1. Datos de entrada — SQLite

### Tablas esperadas

| Tabla | Campos mínimos esperados | Plataforma |
|---|---|---|
| `facebook_posts` | post_id, fecha, texto_post, me_gusta, me_encanta, me_divierte, me_asombra, me_entristece, me_enoja, comentarios_count, compartidos, views | Facebook |
| `facebook_comentarios` | comentario_id, post_id, texto_comentario, fecha | Facebook |
| `tiktok_videos` | video_id, fecha, descripcion, likes, comentarios_count, favoritos, compartidos, views | TikTok |
| `tiktok_comentarios` | comentario_id, video_id, texto_comentario, fecha | TikTok |
| `noticias_externas` | noticia_id, fecha, titular, texto, fuente, url | Web scraping |

> Si las tablas tienen nombres distintos, el agente debe mapearlas antes de continuar. Verificar que `fecha` esté en formato ISO (YYYY-MM-DD) o convertir al inicio del pipeline.

### Vector de reacción emocional (Facebook)

Cada post tiene 6 tipos de reacción como **proxy emocional**. Se normalizan como % del total de reacciones para comparar posts con distinto alcance.

| Reacción | Emoción proxy | Dimensión psicológica aproximada |
|---|---|---|
| Me gusta 👍 | Aprobación neutra | Baseline — no diferenciador |
| Me encanta ❤️ | Afecto positivo fuerte | Alto Agreeableness colectivo |
| Me divierte 😆 | Humor / ligereza | Bajo Conscientiousness / alta Extraversión |
| Me asombra 😮 | Sorpresa / impacto | Alta Apertura colectiva |
| Me entristece 😢 | Empatía / negatividad suave | Alto Neuroticismo colectivo |
| Me enoja 😡 | Rechazo / confrontación | Alto Neuroticismo / baja Amabilidad |

> **Nota:** estas asociaciones son analógicas, no equivalentes al test OCEAN validado. El dashboard las usa como señales de tono emocional colectivo, no como diagnóstico psicológico.

---

## 2. Pipeline analítico — 5 módulos

Cada módulo es independiente. El agente desarrollador ejecuta en orden. Output de cada módulo = nueva tabla en SQLite + visualización para el dashboard.

---

### Módulo 1 — Categorización automática de contenido (NLP)

**Objetivo:** Convertir texto crudo de posts en categorías temáticas.  
**Técnica:** LDA (Latent Dirichlet Allocation) o clustering K-Means sobre embeddings.

| Paso | Acción | Herramienta sugerida |
|---|---|---|
| 1.1 | Limpiar texto: quitar emojis, URLs, stopwords en español | spaCy (`es_core_news_sm`) |
| 1.2 | Generar embeddings de cada post | sentence-transformers (`paraphrase-multilingual`) |
| 1.3 | Clustering de posts por similitud semántica | K-Means (k=8–12 categorías) |
| 1.4 | Etiquetar clusters con nombre legible (manual o GPT) | Revisión manual o LLM |
| 1.5 | Guardar: `post_id → categoria_tema` en SQLite | pandas + sqlite3 |

> **Categorías esperadas** (ajustar según contenido real): Obras públicas, Seguridad, Eventos culturales, Salud, Educación, Comunicados oficiales, Humor/entretenimiento, Ataques políticos / controversia.

---

### Módulo 2 — Análisis de sentimiento de comentarios

**Objetivo:** Determinar si la opinión en comentarios es positiva, negativa o neutral por post.

| Paso | Acción | Herramienta sugerida |
|---|---|---|
| 2.1 | Limpiar texto de comentarios (mismo preproceso que M1) | spaCy |
| 2.2 | Clasificar cada comentario: positivo / negativo / neutral | pysentimiento (modelo BERT español) |
| 2.3 | Agregar por post: % positivo, % negativo, % neutral | pandas groupby |
| 2.4 | Calcular `score_sentimiento = %positivo - %negativo` (rango -1 a +1) | pandas |
| 2.5 | Guardar: `post_id → score_sentimiento, distribucion_sentimiento` | sqlite3 |

---

### Módulo 3 — Score de engagement emocional por post

**Objetivo:** Combinar reacciones + sentimiento en un índice único por post. Este es el equivalente funcional al score OCEAN de CA — pero a nivel de contenido.

| Métrica | Fórmula | Qué mide |
|---|---|---|
| `engagement_total` | likes + encanta + divierte + asombra + entristece + enoja + compartidos | Alcance total |
| `engagement_rate` | engagement_total / views | Eficiencia del contenido |
| `indice_afecto_positivo` | (encanta + asombra) / engagement_total | Resonancia emocional positiva |
| `indice_controversia` | (enoja + entristece) / engagement_total | Polarización / rechazo |
| `indice_viralidad` | compartidos / views | Potencial de difusión orgánica |
| `score_emocional_neto` | indice_afecto_positivo - indice_controversia + (score_sentimiento × 0.3) | Salud emocional del post |

---

### Módulo 4 — Serie temporal + detección de anomalías

**Objetivo:** Identificar picos de engagement, caídas y eventos críticos en el tiempo.

| Paso | Acción | Herramienta |
|---|---|---|
| 4.1 | Agrupar métricas por semana/mes para cada plataforma | pandas `resample` |
| 4.2 | Calcular media móvil 4 semanas para suavizar ruido | pandas `rolling` |
| 4.3 | Detectar anomalías: puntos >2 desviaciones estándar de la media | scipy o IsolationForest |
| 4.4 | Etiquetar anomalías con fecha para cruzar con eventos externos | merge con tabla `noticias_externas` |
| 4.5 | Clasificar anomalías: pico positivo / pico negativo / caída | lógica condicional |

---

### Módulo 5 — Contexto externo (noticias / páginas del alcalde)

**Objetivo:** Correlacionar picos de engagement con eventos reales noticiosos.

| Paso | Acción | Herramienta |
|---|---|---|
| 5.1 | Scraping de páginas externas que mencionan al alcalde | BeautifulSoup + requests o Playwright |
| 5.2 | Extraer: fecha, titular, texto, fuente, URL | pandas |
| 5.3 | Clasificar noticia: positiva / negativa / neutral (mismo M2) | pysentimiento |
| 5.4 | Etiquetar tema de la noticia (mismo M1) | sentence-transformers |
| 5.5 | JOIN temporal: noticias ± 3 días de cada pico detectado en M4 | pandas `merge_asof` |
| 5.6 | Output: tabla `evento_externo → pico_engagement → tema → sentimiento` | sqlite3 |

---

## 3. Estructura del dashboard ejecutivo

5 vistas. Una pantalla principal + 4 vistas de profundidad. Diseñado para un alcalde no técnico: números grandes, colores semáforo, sin jerga estadística.

| Vista | Nombre | KPIs / Visualizaciones clave |
|---|---|---|
| 1 — Principal | Pulso ciudadano (hoy) | Score emocional neto últimos 30 días · Tendencia vs mes anterior · Alerta si controversia >20% |
| 2 — Temas | ¿Qué temas resuenan? | Mapa de calor: tema × emoción · Ranking de temas por engagement_rate · Tema más viral vs más controversial |
| 3 — Tiempo | ¿Cuándo reacciona la gente? | Serie temporal de engagement · Picos marcados con etiqueta de evento · Comparación Facebook vs TikTok |
| 4 — Comentarios | ¿Qué dice la gente? | % positivo/negativo/neutral por tema · Nube de palabras de comentarios negativos · Frases más repetidas |
| 5 — Contexto | ¿Qué pasó afuera? | Timeline: noticia externa → reacción en redes · Clasificación de noticias por tono · Correlación evento → engagement |

### Tecnología sugerida para el dashboard

| Opción | Stack | Ventaja | Desventaja |
|---|---|---|---|
| A (recomendada) | Python + Streamlit + Plotly | Rápido, conecta directo a SQLite, desplegable en web | Requiere servidor Python activo |
| B | Power BI Desktop | El alcalde puede explorar sin programador | Requiere licencia, menos flexible |
| C | HTML/JS + Chart.js (estático) | Sin dependencias, corre en cualquier navegador | No se actualiza automáticamente |

---

## 4. Instrucciones precisas para el agente de IA desarrollador

> Copiar estas instrucciones como prompt de contexto al agente que desarrollará el código.

- **Lenguaje:** Python 3.10+. Todo el análisis en scripts modulares, uno por módulo (`modulo1_categorias.py`, `modulo2_sentimiento.py`, etc.).
- **Base de datos:** SQLite. Ruta configurable en `config.py`. No hardcodear rutas.
- **Librerías core:** `pandas`, `sqlite3`, `scikit-learn`, `sentence-transformers`, `pysentimiento`, `spacy` (es_core_news_sm), `plotly` (para gráficas), `streamlit` (para dashboard).
- **Preprocesamiento de texto:** Siempre limpiar antes de embeddings: lowercase, quitar URLs, quitar emojis, quitar stopwords español, quitar caracteres especiales.
- **Idioma del contenido:** Español. Usar modelos multilingüe o específicos para español en sentimiento y embeddings.
- **Normalización de reacciones:** Siempre dividir entre total de reacciones del post antes de comparar. Posts con <10 reacciones excluir del análisis de proporciones.
- **Output de cada módulo:** Escribir resultados en nueva tabla SQLite + generar un CSV de respaldo en carpeta `/outputs`.
- **Dashboard:** Construir en Streamlit. Una `app.py` principal que importa los módulos de visualización. Sidebar con filtros de fecha y plataforma (Facebook / TikTok / Ambas).
- **Manejo de errores:** Si una columna no existe en SQLite, el script debe fallar con mensaje claro indicando qué campo falta, no con traceback críptico.
- **No inventar datos:** Si un módulo no tiene suficientes datos (ej. <50 posts en una categoría), mostrar advertencia en el dashboard, no fabricar estadísticas.

---

## 5. Orden de ejecución para el agente

| Paso | Script | Depende de | Output en SQLite |
|---|---|---|---|
| 1 | `config.py` | — | Configura rutas y parámetros globales |
| 2 | `modulo1_categorias.py` | config.py | tabla: `post_categorias` (post_id, plataforma, categoria, embedding) |
| 3 | `modulo2_sentimiento.py` | config.py | tabla: `post_sentimiento` (post_id, score, pct_pos, pct_neg, pct_neu) |
| 4 | `modulo3_engagement.py` | modulo1, modulo2 | tabla: `post_engagement` (post_id, todas las métricas calculadas) |
| 5 | `modulo4_series.py` | modulo3 | tabla: `series_temporales` (semana, plataforma, categoria, metricas_promedio, es_anomalia) |
| 6 | `modulo5_noticias.py` | modulo4 | tabla: `eventos_correlacionados` (noticia_id, post_pico_id, correlacion_temporal) |
| 7 | `app.py` (Streamlit) | todos los módulos | Dashboard web en localhost:8501 |

---

## 6. Límites honestos del sistema

> Incluir en el dashboard una sección de "Notas metodológicas" visible para el alcalde.

- ⚠ Este análisis **NO predice** el comportamiento de votantes individuales — predice qué temas generan qué emociones en conjunto.
- ⚠ El vector emocional de reacciones es un proxy, no un test psicológico validado. Úsalo como señal, no como diagnóstico.
- ⚠ El análisis de sentimiento en comentarios tiene ~85% de precisión en español. Un 15% de comentarios pueden estar mal clasificados.
- ⚠ La correlación entre noticias externas y picos de engagement **NO implica causalidad**. Puede haber terceros factores.
- ⚠ TikTok no tiene tipos de reacción diferenciados — solo likes. El análisis emocional de TikTok depende 100% de comentarios.

---

*Blueprint v1.0 — Basado en metodología Kosinski et al. (2013) adaptada a datos agregados + limitaciones identificadas por Farina et al. (2025).*
