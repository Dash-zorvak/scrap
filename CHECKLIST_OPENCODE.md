# CHECKLIST — Balance Multiplataforma (Facebook / TikTok / Externos)

## Línea base de tests
- **Fecha:** 2026-07-16
- **Total tests:** 481 passed, 0 failed
- **Tests finales:** 502 passed, 0 failed (+21 tests nuevos)

## Bloqueos
_(Ninguno)_

---

## Punto 1 — "Aprobar temas" solo funciona con Facebook ✅
- [x] `render_revisor_temas` parametrizada con `tabla`, `col_id`, `col_texto`
- [x] Pestañas TikTok y Externos en `panel_carga.py`
- [x] Tests `tests/test_panel_carga.py` y `tests/test_dash_temas.py` (10 tests nuevos)
- [x] `py_compile` de archivos tocados
- [x] `pytest tests/ -v` sin regresiones

**Resumen:** `render_revisor_temas` ahora acepta `tabla`, `col_id`, `col_texto` con defaults de Facebook. `panel_carga.py` tiene 5 pestañas (cargar, editar, aprobar FB/TK/Ext). 10 tests creados y pasando.

## Punto 2 — Motor de cálculo no balanceado ✅
- [x] `get_externos_stats()` en `analytics/queries.py`
- [x] `cmd_generar` combina aprobaciones de las 3 DBs
- [x] `externos_stats` en `construir_analysis`
- [x] Integración en `total_reacciones_all`, `alcance_estimado`, ER ponderado
- [x] `py_compile` + `pytest tests/analytics/ -v`

**Resumen:** `get_externos_stats()` agrega posts/comments/total_reactions de Externos. `cmd_generar` ahora combina aprobaciones de las 3 DBs (o usa `--db` como override). `construir_analysis` acepta `externos_stats` y lo integra en meta, ER ponderado, total_reacciones_all y alcance_estimado. Sin regresiones.

## Punto 3 — "Temas Emergentes" no alimentado por las 3 DB ✅
- [x] `cargar_temas_aprobados()` combina las 3 DBs
- [x] Comentarios de las 3 plataformas alimentan `comentarios_texts`
- [x] `py_compile` + `pytest tests/analytics/ -v`

**Resumen:** `cargar_temas_aprobados()` combina `agregar_por_tema()` de las 3 DBs con conteos sumados por categoría. `cmd_generar` ahora obtiene comentarios de FB+TK+Ext para `comentarios_texts`, alimentando sentimiento léxico y temas emergentes desde las 3 fuentes.

## Punto 4 — "Voces de Influencia" solo Facebook + TikTok ✅
- [x] Construcción de voces en `report.py` incluye Externos
- [x] `get_external_page_engagement()` consulta external_pages + external_posts
- [x] `py_compile` + `pytest tests/analytics/test_report.py -v`

**Resumen:** Se agregó `get_external_page_engagement()` en `queries.py` que retorna engagement por página externa. La construcción de voces en `report.py` ahora incluye hasta 3 páginas externas con engagement > 0 junto a las voces derivadas de aprobaciones.

## Punto 5 — Externos solo decorativo ✅
- [x] `calcular_correlacion_noticias_picos` creada en `analytics/queries.py`
- [x] `indice_correlacion_externa` en `analysis.json` (bloque4)
- [x] Sección 17 nueva en `app.py` con tarjeta independiente
- [x] NO mezclado con sentimiento/riesgo existente
- [x] `py_compile` + tests

**Resumen:** `calcular_correlacion_noticias_picos(z_umbral=1.0, ventana_dias=3)` detecta picos de engagement por z-score y cuenta coincidencias temporales con noticias externas dentro de una ventana. Resultado expuesto como `indice_correlacion_externa` en bloque4 de `analysis.json`. Nueva sección 17 en `app.py` muestra el índice, picos detectados y coincidencias. Indicador independiente, no afecta scores existentes.

## Punto 6 — TikTok/Externos sin auditoría ✅
- [x] `TikTokStorage`/`ExternosStorage` creadas en `src/storage/db.py`
- [x] `audit_log` se crea automáticamente en tiktok.db y externos.db
- [x] `db_edits.py` migrado a nueva capa (update/delete delegan en Storage)
- [x] Edición/auditoría para Externos (update_post, delete_post, leer_posts_externos)
- [x] H-DS1 aplicado: ValueError en enteros negativos/inválidos
- [x] `py_compile` + 11 tests nuevos (`tests/test_db_edits.py`)

**Resumen:** `TikTokStorage` y `ExternosStorage` usan sqlite3 crudo con validación H-DS1 y crean `audit_log` automáticamente. `db_edits.py` migra `update_video_tiktok`/`delete_video_tiktok` para delegar en `TikTokStorage`. Nuevas funciones `update_post_externo`/`delete_post_externo`/`leer_posts_externos` para Externos. La capa es ADITIVA — no altera columnas existentes en videos/comments/external_posts/external_comments.

---

## Archivos modificados
- `dashboard/dash_temas.py` — firma parametrizada
- `dashboard/panel_carga.py` — 5 pestañas
- `dashboard/db_edits.py` — delegación a Storage classes
- `dashboard/app.py` — sección 17 (correlación externa)
- `analytics/queries.py` — get_externos_stats, get_external_page_engagement, get_tk/ext_comments, cargar_temas_aprobados, calcular_correlacion_noticias_picos
- `analytics/cli.py` — cmd_generar multi-DB
- `analytics/report.py` — externos_stats, voces con Externos, indice_correlacion_externa
- `src/storage/db.py` — TikTokStorage, ExternosStorage

## Tests creados
- `tests/test_panel_carga.py` — 6 tests
- `tests/test_dash_temas.py` — 4 tests
- `tests/test_db_edits.py` — 11 tests
