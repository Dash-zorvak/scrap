# 024 · Historial de Cambios

## Propósito

Este documento registra la evolución oficial de la metodología de MIPA.

Su objetivo es mantener un historial completo, ordenado y auditable de todas las modificaciones realizadas sobre la especificación metodológica, permitiendo conocer qué cambió, cuándo cambió, por qué cambió y a partir de qué versión entró en vigor.

El Historial de Cambios forma parte integral de la gobernanza metodológica del proyecto.

---

# Objetivo

El Historial de Cambios busca responder una pregunta específica:

> ¿Cómo ha evolucionado oficialmente la metodología de MIPA a lo largo del tiempo?

Toda modificación metodológica deberá quedar registrada antes de ser considerada vigente.

No se permitirán cambios implícitos.

---

# Alcance

Este documento aplica a cualquier modificación relacionada con:

- principios metodológicos;
- arquitectura analítica;
- modelos analíticos;
- Pipeline;
- fórmulas;
- variables;
- métricas;
- indicadores;
- índices;
- contratos JSON;
- estructura de analytics.db;
- procesos de validación;
- procesos de trazabilidad;
- documentación oficial.

Toda modificación deberá incorporarse al historial.

---

# Principios

El registro de cambios deberá cumplir los siguientes principios:

- transparencia;
- trazabilidad;
- auditabilidad;
- reproducibilidad;
- versionado;
- preservación histórica.

El historial nunca deberá eliminar versiones anteriores.

---

# Versionado metodológico

Cada versión oficial de la metodología deberá poseer un identificador único.

Como mínimo deberá registrar:

- número de versión;
- fecha de entrada en vigor;
- estado;
- responsable de aprobación;
- alcance del cambio.

La numeración oficial será administrada por la gobernanza metodológica del proyecto.

---

# Registro obligatorio

Cada cambio deberá documentar como mínimo:

- identificador;
- versión;
- fecha;
- documentos afectados;
- descripción del cambio;
- justificación;
- impacto esperado;
- compatibilidad con versiones anteriores.

No podrán existir cambios sin justificación documentada.

---

# Clasificación de cambios

Los cambios podrán clasificarse, entre otros, como:

- incorporación;
- modificación;
- corrección;
- eliminación;
- aclaración metodológica;
- reorganización documental.

La clasificación facilita la comprensión de la evolución del proyecto.

---

# Compatibilidad

Cada cambio deberá indicar explícitamente si es:

- compatible con versiones anteriores;
- parcialmente compatible;
- incompatible.

Cuando exista incompatibilidad, deberá explicarse el impacto sobre los resultados históricos.

---

# Impacto analítico

Toda modificación deberá indicar si afecta:

- variables;
- métricas;
- indicadores;
- índices;
- narrativas;
- contratos JSON;
- analytics.db;
- Dashboard;
- Pipeline.

Esto permitirá identificar rápidamente el alcance operativo del cambio.

---

# Impacto sobre resultados históricos

Cuando una modificación altere la metodología de cálculo, deberá indicarse expresamente si:

- los resultados históricos permanecen válidos;
- requieren reprocesamiento;
- deberán conservarse como una versión independiente.

La comparabilidad histórica deberá preservarse siempre que sea posible.

---

# Procedimiento de actualización

Toda modificación metodológica deberá seguir el siguiente proceso:

1. propuesta de cambio;
2. análisis metodológico;
3. evaluación de impacto;
4. aprobación;
5. actualización de la documentación;
6. asignación de nueva versión;
7. implementación en el Pipeline;
8. publicación del cambio en este documento.

Ningún cambio será oficial hasta completar este proceso.

---

# Registro de implementaciones

Cuando una modificación metodológica requiera cambios en el Pipeline, deberá registrarse adicionalmente:

- versión del Pipeline;
- fecha de implementación;
- estado de despliegue;
- compatibilidad con versiones anteriores.

Esto permite sincronizar la evolución metodológica con la evolución técnica.

---

# Auditoría

El Historial de Cambios deberá permitir responder preguntas como:

- ¿Cuándo cambió esta metodología?
- ¿Qué documentos fueron modificados?
- ¿Por qué se realizó el cambio?
- ¿Qué versión estaba vigente durante un análisis específico?
- ¿Qué impacto tuvo sobre los indicadores?

Estas respuestas deberán obtenerse únicamente consultando este documento.

---

# Conservación histórica

Las versiones anteriores de la metodología no deberán eliminarse.

Cada versión conservará su validez histórica para:

- auditorías;
- reconstrucción de resultados;
- análisis comparativos;
- revisión metodológica.

La preservación histórica constituye un requisito obligatorio del proyecto.

---

# Reproducibilidad

Toda ejecución histórica del Pipeline deberá poder asociarse con la versión metodológica vigente en el momento de su procesamiento.

Esto permitirá reconstruir exactamente cualquier resultado histórico.

---

# Primera versión oficial

La primera versión oficial de la metodología corresponde a la documentación inicial de MIPA compuesta por los documentos:

- 000_PROJECT_CHARTER.md
- 001_FOUNDATION.md
- 002_ARCHITECTURE.md
- 003_DATA_MODEL.md
- 004_ANALYTICAL_MODEL.md
- 005_PIPELINE.md
- 006_EVIDENCE_MODEL.md
- 007_METRIC_CATALOG.md
- 008_NARRATIVE_MODEL.md
- 009_JSON_CONTRACTS.md
- 010_PULSO_IQ.md
- 011_POPULARIDAD_DIGITAL.md
- 012_RIESGO_DIGITAL.md
- 013_EMOTION_MODEL.md
- 014_TOPIC_MODEL.md
- 015_POSTURE_MODEL.md
- 016_VALIDATION_MODEL.md
- 017_TRACEABILITY_MODEL.md
- 018_PIPELINE_STAGES.md
- 019_ANALYTICS_DB_SCHEMA.md
- 020_FORMULAS.md
- 021_REFERENCES.md
- 022_LIMITATIONS.md
- 023_GLOSSARY.md
- 024_CHANGELOG.md

Esta colección constituye la especificación metodológica base de MIPA.

---

# Relación con otros documentos

El Historial de Cambios complementa la totalidad de la documentación metodológica del proyecto.

Toda actualización futura de cualquier documento oficial deberá reflejarse en este registro antes de considerarse parte de la metodología vigente.

Este documento constituye la referencia oficial para el seguimiento de la evolución metodológica de MIPA y garantiza la continuidad, estabilidad y auditabilidad del proyecto a lo largo de su ciclo de vida.