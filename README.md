# Panel Santa Ana · Inteligencia Ciudadana

Dashboard ejecutivo de percepción pública para la Alcaldía de Santa Ana.

## Arquitectura

El sistema opera en tres pasos:

1. **Ingesta (local, panel del analista):** `dashboard/panel_carga.py` — el analista
   sube capturas de pantalla o PDFs de publicaciones; Groq Vision extrae los datos,
   el analista revisa/corrige y confirma. Solo escribe datos crudos en `facebook.db`,
   `tiktok.db` y `externos.db`. No calcula métricas, sentimiento ni narrativas.
2. **Análisis (pipeline automatizado):** `python -m analytics.cli generar` procesa
   las bases de datos, calcula métricas §D-I, valida contra el esquema y genera
   `data/analysis.json`. **Único punto de escritura.** No existe ruta paralela.
3. **Visualización (dashboard):** `app.py` lee el JSON y renderiza los 4 bloques
   ejecutivos sin cálculo en runtime.

​
Panel de carga (local) → DBs crudas → CLI (`analytics.cli`) → analysis.json → app.py → Dashboard

## Estructura del proyecto

​
dashboard/
app.py                  # Dashboard del alcalde (solo lectura de JSON)
config.py                # Rutas y configuración
estilos.py                # Tema visual
estilos_override.py       # Overrides de estilos
panel_carga.py            # Panel de carga del analista (uso local, puerto 8502)
dash_ui.py                 # Helpers de UI del panel de carga
dash_ingesta.py            # Carga y revisión de lotes (capturas/PDF)
ingreso_extraccion.py      # Extracción de datos con Groq Vision
llm_groq.py                 # Cliente de Groq
guardar_lote.py             # Escritura de lotes revisados a SQLite
escritura_tiktok.py         # Escritura SQLite para TikTok
_generar_id.py               # Generación de IDs con dedupe por contenido
externos_store.py            # Persistencia de páginas externas
capturas_store.py            # Persistencia de capturas subidas
editor_db.py                  # Corrección/borrado de registros guardados
db_edits.py                    # Operaciones de bajo nivel sobre SQLite
dash_temas.py                   # Aprobación manual de tema/categoría por comentario
tema_aprobaciones.py             # Persistencia de aprobaciones de tema
tema_taxonomia.py                 # Taxonomía de categorías/temas
data/
facebook.db             # Base de datos Facebook (no versionada)
tiktok.db               # Base de datos TikTok (no versionada)
externos.db             # Base de datos externos (no versionada)
analysis.json            # JSON generado por el CLI (no versionado)
analysis_schema.json      # Esquema de referencia (versionado)
src/                      # Módulos heredados de almacenamiento/analizador
scripts/                  # Scripts utilitarios (dedupe, mantenimiento, etc.)
tests/                    # Suite de tests

## Esquema analysis.json

Ver `data/analysis_schema.json` para la estructura completa con todas las
claves requeridas por el dashboard.

**Nota sobre `idioms_sv_global.json`:** este archivo es material de referencia
histórico del proceso manual original; no es consumido por ningún módulo Python
del repo.

Los 4 bloques corresponden a:
- **bloque1**: Pulso General (clima narrativo, intensidad, concentración temática)
- **bloque2**: Segmentación de Audiencia (mapa de públicos, polarización, voces, temas LDA)
- **bloque3**: Riesgo y Autenticidad (autenticidad, alertas, propagación, fricción)
- **bloque4**: Memorándum Estratégico (10 narrativas ejecutivas)

## Ejecutar el dashboard (alcalde, solo lectura)

​
streamlit run dashboard/app.py

El dashboard muestra "Análisis pendiente" si `data/analysis.json` no existe.

## Generar el análisis (pipeline automatizado)

​
python -m analytics.cli generar --periodo "YYYY-MM" --fecha-hasta "YYYY-MM-DD" --db data/facebook.db

Este es el **único camino de escritura** a `data/analysis.json`. El pipeline:
1. Consulta las DBs (Facebook + TikTok) vía `analytics/queries.py`
2. Calcula métricas §D-I vía `analytics/compute.py`
3. Construye el dict vía `analytics/report.py::construir_analysis()`
4. Valida contra `data/analysis_schema.json` (V01-V11)
5. Publica el JSON vía `analytics/publish.py`

No existe ni se soporta ningún generador paralelo o manual para este archivo.

## Ejecutar el panel de carga (analista, solo local)

​
./run_panel.sh
o directamente:
streamlit run dashboard/panel_carga.py --server.port 8502 --server.address 127.0.0.1

Abre `http://localhost:8502`. Este panel **no se expone por el túnel** de
Cloudflare (ver `DESPLIEGUE.md`) y opera sobre las bases de datos locales
definidas en `config.py`. Tiene tres secciones:

- **📥 Cargar contenido** — sube capturas/PDF, extrae datos con Groq Vision,
  revisas y guardas el lote como datos crudos.
- **✏️ Corregir registros** — corrige o elimina un registro ya guardado.
- **✅ Aprobar temas** — asigna manualmente el tema/categoría de cada comentario
  (proceso 100% manual, sin sugerencia ni aprendizaje automático).

## Ingesta de datos

La ingesta es **100% manual**, a través de `dashboard/panel_carga.py`. El panel
no calcula métricas, sentimiento ni narrativas — el análisis y generación de
`data/analysis.json` lo ejecuta el pipeline automatizado (`analytics.cli`).
`dashboard/app.py` lee directamente el JSON resultante.
