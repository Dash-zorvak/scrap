# PLAN_V2 - Plataforma Ejecutiva de Analítica Social

> **Versión**: 2.0
> **Fecha**: 15 mayo 2026
> **Deadline**: 30 junio 2026 (45 días)
> **Objetivo**: Dashboard ejecutivo tipo Bloomberg para presentar al Alcalde de Santa Ana

---

## Contexto Confirmado

- **Hardware**: Servidor local (no cloud público), modo SaaS
- **Frecuencia**: Dashboard actualizado diariamente
- **Usuario**: Solo el alcalde
- **GPU**: Local (no APIs externas)
- **Alcance**: Solo Santa Ana (sin comparativa competitiva)
- **Scraping**: Último año (desde hoy hacia atrás), reacciones/comentarios/shares reales

---

## Arquitectura General

```
┌─────────────────────────────────────────────────────────────────────┐
│                     SCRAPEO-SOCIAL v2.0                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐   │
│  │  FB Scraper  │    │ TT Scraper   │    │  Comment Scraper     │   │
│  │ (Playwright) │    │ (TikTok API) │    │  (Posts + Comments) │   │
│  └──────┬───────┘    └──────┬───────┘    └──────────┬───────────┘   │
│         │                   │                       │               │
│         └───────────────────┼───────────────────────┘               │
│                             ▼                                       │
│                    ┌───────────────┐                                │
│                    │   PostgreSQL  │                                │
│                    │  (Time-series)│                                │
│                    └───────┬───────┘                                │
│                            ▼                                        │
│         ┌──────────────────────────────────────────────┐           │
│         │              PIPELINE DE ANÁLISIS             │           │
│         ├──────────────────────────────────────────────┤           │
│         │  • Sentiment Analysis (pysentimiento)        │           │
│         │  • Topic Detection (taxonomía municipal)     │           │
│         │  • Problemática Extraction (NER + keywords)  │           │
│         │  • Zone Mapping (regex + IA)                 │           │
│         │  • Key Insights Generator                    │           │
│         │  • Executive Metrics Calculator              │           │
│         └──────────────────────┬───────────────────────┘           │
│                                ▼                                    │
│         ┌──────────────────────────────────────────────┐           │
│         │           DASHBOARD EJECUTIVO                │           │
│         │              (Streamlit/React)                │           │
│         │  • Executive Scorecard                        │           │
│         │  • Topic Urgency Matrix                       │           │
│         │  • Problemáticas por Zona                    │           │
│         │  • Sentiment Trends                           │           │
│         │  • Actionable Insights                       │           │
│         └──────────────────────────────────────────────┘           │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Fases de Implementación

### FASE 1: Infraestructura (Días 1-7)

**Objetivo**: Setup de base de datos, scrapers funcionando, pipeline básico

| Día | Tarea | Entregable |
|-----|-------|------------|
| 1 | Migrar SQLite → PostgreSQL | PostgreSQL corriendo |
| 2 | Mejorar FB scraper (comentarios + reactions) | Scraper con comments |
| 3 | Mejorar TT scraper (comentarios + reactions) | Scraper con comments |
| 4 | Implementar topic taxonomy predefinida | taxonomy.json |
| 5 | Implementar extracting de problemáticas | extractor.py |
| 6 | Implementar zone mapping | zone_mapper.py |
| 7 | Test end-to-end con 100 posts | Pipeline funcionando |

**Topic Taxonomy Municipal** (predefinida):
```json
{
  "obras_publicas": ["bache", "calle", "carpeta", "asfalto", "puente", "路灯", "parque", "广场"],
  "seguridad": ["robo", "asalto", "delincuencia", "seguridad", "policía", "crimen", "matar"],
  "servicios": ["agua", "luz", "basura", "recolección", "servicio", "corte"],
  "empleo": ["trabajo", "empleo", "desempleo", "negocio", "empresa"],
  "salud": ["hospital", "clínica", "doctor", "salud", "enfermedad"],
  "educacion": ["escuela", "colegio", "educación", "maestro", "estudiante"],
  "movilidad": ["tráfico", "transito", "carro", "bus", "ruta", "parada"],
  "corrupcion": ["corrupto", "robo", "malo", "mentira", "fraude"],
  "medio_ambiente": ["contaminación", "basura", "río", "árbol", "verde"],
  "transparencia": ["información", "transparente", "donde", "gasto"]
}
```

**Zone Mapping**:
- Distritos de Santa Ana: Norte, Sur, Centro, Este, Oeste
- Detección por: mention explícita ("en el norte", "por Villa Jardín") + coordenadas si están disponibles
- Fallback: regex de zonas conocidas

---

### FASE 2: Scraping a Escala (Días 8-21)

**Objetivo**: Extraer 20K FB posts + 4K TT videos + comentarios

| Período | Target | Notas |
|---------|--------|-------|
| Días 8-10 | 500 posts FB piloto | Testear límites, ajustar delays |
| Días 11-14 | 3,000 posts FB | Rotación de cuentas |
| Días 15-18 | 6,000 posts FB | Monitoreo de shadowban |
| Días 19-21 | 10,500 posts FB (total 20K) | Completar FB |

| Período | Target | Notas |
|---------|--------|-------|
| Días 12-15 | 500 videos TT piloto | Test API limits |
| Días 16-19 | 2,000 videos TT | 2K de Alcaldía |
| Días 20-21 | 2,000 videos TT | 2K del Alcalde |

**Scraping Strategy**:
- FB: 2 cuentas rotando, 25-40 posts/día por cuenta, 30-60s delay
- TT: 1 cuenta, 60-80 videos/día, 15-30s delay
- Solo horario 8am-6pm
- Checkpoint cada 50 items
- Logging de errores detallado

**Comments Scraping**:
- Extraer todos los comments por post (depth first 2 niveles)
- Guardar: author_name, message, like_count, created_time
- Target: ~50 comments/post promedio = ~1.2M comments total

---

### FASE 3: Análisis e Insights (Días 22-35)

**Objetivo**: Pipeline completo de análisis + métricas ejecutivas

| Día | Módulo | Funcionalidad |
|-----|--------|---------------|
| 22-24 | Sentiment Enhanced | Sentiment por post + por comment + por tema |
| 25-26 | Topic Detection | Clasificar cada post/comentario en taxonomy |
| 27-28 | Problemática Extraction | Extraer issues específicos mentioned |
| 29-30 | Zone Aggregation | Agrupar problemáticas por zona |
| 31-32 | Key Insights Generator | Generar actionable insights automático |
| 33-34 | Executive Metrics | Calcular: NSI, Crisis Index, Topic Urgency |
| 35 | Daily Report Generator | JSON + PDF para mostrar al alcalde |

**Métricas Ejecutivas**:

```python
# Net Sentiment Index (NSI) - como NPS pero para sentiment
NSI = (Positive% - Negative%) * 100
# Rango: -100 (todo negativo) a +100 (todo positivo)

# Crisis Alert Index (CAI)
# Basado en: tasa de cambio negativa + volumen de negativos + keywords de emergencia
CAI = (Negative_Velocity * 0.4) + (Emergency_Keywords * 0.3) + (Volume_Spike * 0.3)
# 0-10: Normal, 10-20: Precaución, 20+: Crisis

# Topic Urgency Matrix
# Para cada topic: sentiment_score * volume * recency
Urgency(topic) = Sentiment_Negative% * Total_Comments * (1 / Days_Old)

# Key Insight Generator
# Formula: "En el post [ID] se mencionó '[topic]' ([count] veces en comentarios)
# y eso provocó [sentiment] según análisis. Este tema le interesa a la población."
```

---

### FASE 4: Dashboard Ejecutivo (Días 36-42)

**Objetivo**: Interfaz tipo Bloomberg para presentar al alcalde

**Stack**: Streamlit (MVP rápido) o Next.js + Tailwind (más profesional)

**Vista Principal - Executive Scorecard**:

```
╔══════════════════════════════════════════════════════════════════════╗
║              SANTA ANA - ANÁLISIS DE PERCEPCIÓN SOCIAL                ║
║                        Fecha: 15 junio 2026                          ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                       ║
║  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ║
║  │ NSI: +42    │  │ CAI: 6.2    │  │ Posts: 20K  │  │ Comments:   │  ║
║  │ ↑ 5 vs ayer │  │ Normal      │  │ FB: 20,000  │  │ 1.2M        │  ║
║  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  ║
║                                                                       ║
╠══════════════════════════════════════════════════════════════════════╣
║  TOP PROBLEMÁTICAS POR ZONA (últimos 30 días)                         ║
║  ┌─────────────────────────────────────────────────────────────────┐  ║
║  │ ZONA NORTE (32% de mentions):                                   │  ║
║  │ • Baches +254% vs mes anterior - SENTIMENT: 🔴 NEGATIVO        │  ║
║  │ • Agua potable +89% - SENTIMENT: 🟡 NEUTRAL                    │  ║
║  │ • Seguridad +45% - SENTIMENT: 🔴 NEGATIVO                      │  ║
║  ├─────────────────────────────────────────────────────────────────┤  ║
║  │ ZONA SUR (28% de mentions):                                    │  ║
║  │ • Luz eléctrica +156% - SENTIMENT: 🔴 NEGATIVO                 │  ║
║  │ • Recolección basura +67% - SENTIMENT: 🟢 POSITIVO             │  ║
║  │ • Calles +34% - SENTIMENT: 🟡 NEUTRAL                          │  ║
║  ├─────────────────────────────────────────────────────────────────┤  ║
║  │ ZONA CENTRO (25% de mentions):                                 │  ║
║  │ • Tráfico +78% - SENTIMENT: 🟡 NEUTRAL                         │  ║
║  │ • Seguridad +56% - SENTIMENT: 🔴 NEGATIVO                      │  ║
║  └─────────────────────────────────────────────────────────────────┘  ║
║                                                                       ║
╠══════════════════════════════════════════════════════════════════════╣
║  TENDENCIA DE SENTIMIENTO (últimos 30 días)                          ║
║  [Gráfico de línea: positivo/negativo/neutral por día]              ║
║                                                                       ║
╠══════════════════════════════════════════════════════════════════════╣
║  KEY INSIGHTS - ACCIONABLES                                          ║
║  ┌─────────────────────────────────────────────────────────────────┐  ║
║  │ 📌 Post ID 489234: Se mencionó "baches" en 67 comentarios      │  ║
║  │    → 89% de comentarios negativos → Este tema genera mayor    │  ║
║  │      frustración. Recomendación: Priorizar en zona norte.      │  ║
║  ├─────────────────────────────────────────────────────────────────┤  ║
║  │ 📌 Post ID 489567: Se mencionó "agua" en 45 comentarios         │  ║
║  │    → Sentimiento mixto pero con urgencia creciente             │  ║
║  │      → Alert: Incremento de 156% vs mes anterior.              │  ║
║  ├─────────────────────────────────────────────────────────────────┤  │
║  │ 📌 Topic "seguridad" en zona norte tiene CAI de 8.4           │  ║
║  │    → Requiere atención inmediata.                             │  ║
║  └─────────────────────────────────────────────────────────────────┘  ║
║                                                                       ║
╠══════════════════════════════════════════════════════════════════════╣
║  PLATAFORMAS                                                          ║
║  Facebook: 20,000 posts | 89% positive sentiment | 1.1M reactions    ║
║  TikTok: 4,000 videos | 76% positive sentiment | 890K views          ║
║                                                                       ║
╚══════════════════════════════════════════════════════════════════════╝
```

**Navegación del Dashboard**:
1. **Scorecard** (Home): Overview ejecutivo con métricas clave
2. **Problemáticas**: Mapa de calor por zona + timeline
3. **Sentimiento**: Gráficos de tendencia + breakdown por tema
4. **Posts**: Lista searchable de posts con drill-down
5. **Insights**: Todos los insights generados automáticamente
6. **Config**: Settings del dashboard (refrescar datos, exportar)

---

### FASE 5: Test y Entrega (Días 43-45)

| Día | Tarea |
|-----|-------|
| 43 | Testing end-to-end con datos completos |
| 44 | Ajustes basados en testing |
| 45 | Demo final al alcalde + documentación |

---

## Presupuesto de Recursos

### Hardware (Local)
- **Mínimo**: 16GB RAM, 8-core CPU, 1TB SSD
- **Recomendado**: 32GB RAM, 16-core CPU, 2TB SSD, GPU (RTX 3060+)

### Software
- PostgreSQL (free)
- Python 3.11+
- Streamlit o Next.js
- pysentimiento (GPU-accelerated)
- Playwright (scraping)

---

## Métricas de Éxito

| Métrica | Target |
|---------|--------|
| Posts scrapeados | 20,000+ FB, 4,000+ TT |
| Comments extraídos | 1,000,000+ |
| Topics detectados | 10 categorías |
| Zonas identificadas | 5 zonas + regex |
| Insights generados | 50+ diarios |
| Dashboard uptime | 99% |
| Tiempo de generación daily report | < 5 minutos |

---

## Riesgos y Mitigaciones

| Riesgo | Probabilidad | Mitigación |
|--------|--------------|-------------|
| Shadowban FB | Alta | Rotación de cuentas, delays, comportamiento humano |
| API limits TikTok | Media | Pool de cuentas, caching, errores retry |
| GPU insuficiente | Baja | Fallback a CPU (más lento pero funcional) |
| Datos insuficientes para insights | Media | Aumentar sampling de comments |
|Deadline ajustado | Alta | Priorizar MVP sobre features completos |

---

## Próximos Pasos Inmediatos

1. **HOY**: Confirmar acceso a servidor/local con specs de hardware
2. **HOY**: Verificar credenciales FB/TT disponibles
3. **Mañana**: Setup PostgreSQL + migrar schema actual
4. **Mañana**: Implementar topic taxonomy
5. **Día 2**: Test scraper con 10 posts (e2e test)

---

**Versión**: 1.0
**Actualizado**: 15 mayo 2026