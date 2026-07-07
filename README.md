---
title: Panel Santa Ana
emoji: 📊
colorFrom: blue
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
---

# Panel Santa Ana · Inteligencia Ciudadana

Dashboard ejecutivo de percepción pública para la Alcaldía de Santa Ana.

## Arquitectura

El sistema opera en dos pasos separados:

1. **Análisis (externo):** Las bases de datos (`facebook.db`, `tiktok.db`,
   `externos.db`) se procesan por un analista externo que genera `data/analysis.json`
2. **Visualización (dashboard):** `app.py` lee el JSON y renderiza los 4 bloques
   ejecutivos sin cálculo en runtime

```
DBs → Analista → analysis.json → app.py → Dashboard
```

## Estructura del proyecto

```
dashboard/
  app.py                  # Dashboard principal (solo lectura de JSON)
  config.py               # Rutas y configuración
  estilos.py              # Tema Bloomberg oscuro
  estilos_override.py     # Overrides de estilos
  escritura_tiktok.py     # Ingesta manual TikTok
  _generar_id.py          # Utilidad de IDs

data/
  facebook.db             # Base de datos Facebook (no versionada)
  tiktok.db               # Base de datos TikTok (no versionada)
  externos.db             # Base de datos externos (no versionada)
  analysis.json           # JSON generado por analista (no versionado)
  analysis_schema.json    # Esquema de referencia (versionado)

src/                      # Módulos de ingesta y procesamiento
scripts/                  # Scripts utilitarios
tests/                    # Suite de tests
```

## Esquema analysis.json

Ver `data/analysis_schema.json` para la estructura completa con todas las
claves requeridas por el dashboard.

Los 4 bloques corresponden a:
- **bloque1**: Pulso General (clima narrativo, intensidad, concentración temática)
- **bloque2**: Segmentación de Audiencia (mapa de públicos, polarización, voces, temas LDA)
- **bloque3**: Riesgo y Autenticidad (autenticidad, alertas, propagación, fricción)
- **bloque4**: Memorándum Estratégico (10 narrativas ejecutivas)

## Ejecutar dashboard

```bash
streamlit run dashboard/app.py
```

El dashboard muestra "Análisis pendiente" si `data/analysis.json` no existe.

## Ingesta de datos

La ingesta de datos se realiza por separado usando los scripts en `scripts/`
y los módulos de ingesta en `src/`. El dashboard no tiene acceso de escritura.
