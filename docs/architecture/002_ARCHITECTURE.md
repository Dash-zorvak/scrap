# MIPA — Motor de Inteligencia Política Auditada
## ARCHITECTURE
**Documento:** 002_ARCHITECTURE.md  
**Estado:** APROBADO (Baseline)  
**Versión metodológica:** MIPA 1.0.0  
**Clasificación:** Normativo (Obligatorio)

---

# 1. Propósito

Este documento define la arquitectura oficial de MIPA.

La arquitectura establece la distribución de responsabilidades entre los componentes del sistema y garantiza que cada dominio posea una única función claramente definida.

Toda implementación deberá respetar esta arquitectura.

---

# 2. Objetivos Arquitectónicos

La arquitectura de MIPA persigue los siguientes objetivos.

- Separación estricta de responsabilidades.
- Reproducibilidad.
- Auditabilidad.
- Escalabilidad.
- Extensibilidad.
- Bajo acoplamiento.
- Alta cohesión.
- Independencia tecnológica.
- Evolución metodológica controlada.

---

# 3. Arquitectura General

MIPA se implementa mediante una arquitectura por capas.

```
                 ┌──────────────────────┐
                 │   Panel de Carga     │
                 └──────────┬───────────┘
                            │
                            ▼
                  Ingesta y Validación

                            │
                            ▼

                 ┌──────────────────────┐
                 │ Bases de Datos Fuente │
                 └──────────┬───────────┘

                            │
                            ▼

            Pipeline Analítico + Motor Analítico
            (analytics/compute.py, analytics/queries.py,
             analytics/report.py::construir_analysis())

                            │
                            ▼

                 ┌──────────────────────┐
                 │  data/analysis.json   │
                 └──────────┬───────────┘

                            │
                            ▼

                     Dashboard Ejecutivo
                     (app.py, solo lee)

  ┌─────────────────────────────────────────────────────────┐
  │  DIFERIDO (diseño futuro): analytics.db como base       │
  │  analítica separada. Ver §9, §10. Hoy no existe.        │
  └─────────────────────────────────────────────────────────┘
```

---

# 4. Principio Fundamental

Toda información deberá avanzar únicamente hacia adelante.

Nunca hacia atrás.

El Dashboard jamás modificará el Pipeline.

El Pipeline jamás modificará la evidencia.

La evidencia jamás modificará la captura original.

---

# 5. Dominios Oficiales

La arquitectura oficial se divide en ocho dominios.

---

## Dominio 1 — Captura

Responsabilidad:

Obtener evidencia desde plataformas digitales.

Entradas:

- imágenes
- PDF
- enlaces

Salidas:

- archivos originales

No realiza cálculos.

---

## Dominio 2 — Extracción

Responsabilidad:

Convertir evidencia visual en información estructurada.

Puede utilizar modelos de IA.

Su salida siempre deberá pasar validación humana.

Entradas:

- imágenes
- PDF

Salidas:

- registros estructurados

No calcula indicadores.

---

## Dominio 3 — Validación Humana

Responsabilidad:

Confirmar que la información extraída representa correctamente la evidencia.

Todo dato oficial deberá atravesar este dominio.

Sin excepción.

---

## Dominio 4 — Persistencia

Responsabilidad:

Almacenar permanentemente la información.

Incluye:

- facebook.db
- tiktok.db
- externos.db

Estas bases representan la evidencia validada.

Nunca contienen indicadores derivados.

---

## Dominio 5 — Pipeline Analítico

Responsabilidad:

Transformar evidencia en datos analíticos.

Aquí ocurren exclusivamente procesos deterministas.

No existen decisiones humanas.

No existen interpretaciones.

No existen narrativas.

---

## Dominio 6 — Motor Analítico

Responsabilidad:

Construir indicadores oficiales.

Opera únicamente sobre datos previamente preparados por el Pipeline.

Nunca consulta directamente el Dashboard.

---

## Dominio 7 — Motor Narrativo

Responsabilidad:

Transformar indicadores en explicaciones ejecutivas.

Puede utilizar IA.

Nunca modifica indicadores.

Nunca modifica cálculos.

---

## Dominio 8 — Dashboard

Responsabilidad:

Visualizar resultados.

No calcula.

No interpreta.

No modifica.

---

# 6. Flujo Oficial

El flujo oficial queda definido de la siguiente manera.

```
Captura

↓

Extracción

↓

Validación Humana

↓

Persistencia

↓

Pipeline Analítico + Motor Analítico
(compute.py, queries.py, report.py::construir_analysis())

↓

data/analysis.json

↓

Dashboard (app.py, solo lee)

── DIFERIDO (diseño futuro): analytics.db — ver §9, §10 ──
```

Ningún componente podrá alterar este flujo.

---

# 7. Flujo Prohibido

Los siguientes flujos quedan prohibidos.

Dashboard → Bases de datos

Dashboard → Pipeline

Dashboard → Motor Analítico

Narrativa → Indicadores

LLM → Indicadores

LLM → Dashboard

Dashboard → Evidencia

---

# 8. Componentes del Repositorio

Estructura real del repositorio:

```
dashboard/
    app.py                    ← Motor narrativo + renderizado (solo lee analysis.json)
    auth.py                   ← Autenticación LLM
    capturas_store.py         ← Persistencia de capturas
    dash_ingesta.py           ← Panel de ingesta
    dash_metrics.py           ← Métricas de rendimiento
    dash_temas.py             ← Tarjetas de temas
    dash_ui.py                ← UI y estilos
    intencion_taxonomia.py    ← Catálogo abierto de intención comunicativa
    tema_aprobaciones.py      ← Persistencia de aprobaciones manuales
    tema_taxonomia.py         ← Catálogo abierto de emociones y temas
    taxonomias_pendientes.json← Propuestas pendientes de revisión
    (módulos de soporte: html_safety, dimension_labels, estilos, etc.)

analytics/
    compute.py                ← Pipeline analítico + Motor Analítico
    report.py                 ← Construcción de analysis.json (construir_analysis)
    schema_validator.py       ← Validación del esquema de salida
    narrative_renderer.py     ← Renderizado de narrativas LLM
    publish.py                ← Publicación de resultados
    queries.py                ← Consultas a bases de evidencia
    freshness.py              ← Detección de datos desactualizados
    cli.py                    ← Interfaz de línea de comandos

data/
    facebook.db               ← Base de evidencia (Facebook)
    tiktok.db                 ← Base de evidencia (TikTok)
    externos.db               ← Base de evidencia (externos)
    analysis.json             ← Salida oficial del pipeline (contrato dashboard↔analytics)
    analysis_schema.json      ← Esquema del contrato
    ANALYST_GUIDE.md          ← Reglas para generadores de analysis.json

scripts/
    _common.py                ← Utilidades compartidas
    clean_simulated.py        ← Limpieza de datos simulados
    dedupe_existing.py        ← Deduplicación
    purge_out_of_range.py     ← Eliminación fuera de rango
    verificar.py              ← Verificación de integridad

src/
    config.py                 ← Configuración global
    storage/                  ← Capa de almacenamiento

tests/
    analytics/                ← Tests del pipeline y report
    dashboard/                ← Tests del catálogo de intención
    (tests de integración, deduplicación, HTML safety, etc.)

docs/
    architecture/             ← Documentación arquitectónica
    appendix/                 ← Documentos de referencia (A01, etc.)
```

---

# 9. Bases de Datos

## Bases de evidencia

Representan información validada.

No contienen cálculos.

- facebook.db

- tiktok.db

- externos.db

---

## Base analítica (DIFERIDO)

> **Estado: DIFERIDO** — `analytics.db` es un diseño objetivo a futuro. Hoy, `data/analysis.json` cumple el rol de contrato entre el pipeline y el dashboard.

Representa únicamente resultados derivados.

analytics.db

Nunca almacena evidencia original.

---

# 10. analytics.db (DIFERIDO)

> **Estado: DIFERIDO** — `analytics.db` es un diseño objetivo a futuro. Hoy, `data/analysis.json` cumple este rol: almacena resultados derivados como un JSON consistente generado por `analytics/report.py::construir_analysis()`.

analytics.db constituirá la única base autorizada para almacenar resultados derivados.

Contendrá exclusivamente:

- indicadores
- agregaciones
- métricas
- series temporales
- auditorías
- versiones
- referencias
- hashes
- estados

Nunca contendrá comentarios originales.

Nunca contendrá publicaciones completas.

Nunca sustituirá las bases fuente.

---

# 11. dashboard_snapshot.json (DIFERIDO)

> **Estado: DIFERIDO** — `dashboard_snapshot.json` es un diseño objetivo a futuro. Hoy, `data/analysis.json` cumple este rol: el Dashboard lee únicamente este archivo como contrato de entrada.

El Dashboard leerá únicamente un archivo oficial (actualmente `data/analysis.json`):

```
data/analysis.json
```

Este archivo representa un snapshot consistente del estado del sistema.

Nunca será editado manualmente.

Siempre será generado automáticamente.

---

# 12. Pipeline

El Pipeline constituye el núcleo del sistema.

Sus responsabilidades son:

- limpiar
- validar
- normalizar
- calcular
- agregar
- versionar
- registrar auditoría

No genera narrativas.

---

# 13. Motor Analítico

El Motor Analítico opera exclusivamente sobre analytics.db.

Su salida será:

- indicadores oficiales;
- métricas;
- índices;
- resúmenes cuantitativos.

Nunca generará texto.

---

# 14. Motor Narrativo

Recibe únicamente:

- indicadores;
- evidencia asociada;
- reglas narrativas.

Produce:

- explicaciones;
- memorándums;
- resúmenes;
- conclusiones.

Nunca modifica indicadores.

---

# 15. Dashboard

El Dashboard tiene únicamente cuatro responsabilidades.

- cargar data/analysis.json;
- validar integridad del archivo;
- renderizar;
- informar errores.

No posee lógica analítica.

---

# 16. Dependencias Permitidas

## Panel de Carga

Puede acceder a:

- LLM
- SQLite

---

## Pipeline

Puede acceder a:

- SQLite

Nunca al Dashboard.

---

## Motor Analítico

Puede acceder únicamente a:

analytics.db

---

## Dashboard

Puede acceder únicamente a:

data/analysis.json (contrato actual)

> **Nota:** En el diseño diferido, el Dashboard leerá `dashboard_snapshot.json`. Hoy, `data/analysis.json` cumple este rol.

---

# 17. Dependencias Prohibidas

El Dashboard no podrá importar módulos analíticos.

El Dashboard no podrá ejecutar consultas SQL.

El Dashboard no podrá recalcular indicadores.

El Dashboard no podrá modificar data/analysis.json.

---

# 18. Independencia Tecnológica

La arquitectura no depende de:

- Python
- SQLite
- Streamlit
- Claude
- OpenAI
- NVIDIA
- PostgreSQL

Estos componentes podrán cambiar sin modificar la arquitectura.

---

# 19. Escalabilidad

La incorporación de nuevas plataformas deberá afectar únicamente:

- Captura
- Extracción
- Persistencia

El Pipeline, el Motor Analítico y el Dashboard deberán continuar funcionando sin modificaciones estructurales.

---

# 20. Compatibilidad

Toda nueva versión deberá poder procesar evidencia histórica.

La evolución tecnológica nunca deberá impedir reconstruir indicadores previamente publicados.

---

# 21. Criterios de Aceptación

La arquitectura se considerará correctamente implementada cuando:

- el Dashboard no ejecute cálculos;
- exista una separación física entre evidencia y resultados derivados;
- analytics.db pueda reconstruirse completamente desde las bases fuente (DIFERIDO);
- data/analysis.json pueda regenerarse completamente desde las bases fuente (vía report.py::construir_analysis());
- eliminar analytics.db no implique pérdida de evidencia;
- eliminar data/analysis.json no implique pérdida de evidencia (se regenera desde las bases fuente).

---

# 22. Vigencia

La arquitectura descrita en este documento constituye la arquitectura oficial de MIPA.

Toda implementación futura deberá respetar las responsabilidades, dependencias y restricciones aquí definidas.

---

# Control del Documento

| Campo | Valor |
|--------|-------|
| Documento | 002_ARCHITECTURE.md |
| Estado | Aprobado |
| Versión | 1.0.0 |
| Tipo | Normativo |
| Depende de | 000_PROJECT_CHARTER.md, 001_FOUNDATION.md |
| Referenciado por | 003_DATA_MODEL.md, 004_PIPELINE.md |
| Última actualización | Bloque 3.1 — analytics.db fuera del flujo activo en §3/§6 |