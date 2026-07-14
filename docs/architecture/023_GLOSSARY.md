# 023 · Glosario

## Propósito

Este documento define el vocabulario oficial de MIPA.

Su objetivo es establecer un lenguaje común para toda la documentación metodológica, el Pipeline, la base analítica y el Dashboard, garantizando que cada término posea una única definición oficial.

Cuando exista diferencia entre el uso común de un término y la definición establecida por MIPA, prevalecerá siempre la definición contenida en este documento.

---

# A

## Analytics.db

Base de datos analítica generada exclusivamente por el Pipeline.

Almacena variables, métricas, indicadores, índices, metadatos, referencias y trazabilidad.

No almacena evidencia original.

---

# C

## Cobertura

Porción de la evidencia disponible que participa efectivamente en un análisis determinado.

La cobertura siempre deberá indicarse explícitamente en los resultados.

---

## Comentario

Unidad de evidencia correspondiente a una respuesta publicada por un usuario dentro de una plataforma digital.

Los comentarios forman parte de la evidencia primaria del sistema.

---

# D

## Dashboard

Componente de visualización del sistema.

Su única responsabilidad consiste en presentar la información contenida en `dashboard_snapshot.json`.

No ejecuta cálculos.

No consulta bases de datos.

No modifica resultados.

---

## Dashboard Snapshot

Archivo JSON final generado por el Pipeline.

Constituye el único contrato de datos consumido por el Dashboard.

---

# E

## Evidencia

Información original capturada desde las plataformas digitales.

Constituye la fuente primaria de verdad del sistema.

Toda variable, métrica, indicador e índice debe poder rastrearse hasta la evidencia correspondiente.

---

# F

## Fórmula

Definición matemática oficial utilizada para calcular una variable, métrica, indicador o índice.

Todas las fórmulas forman parte de la metodología oficial y deben ser reproducibles.

---

# I

## Indicador

Medida analítica que sintetiza una o varias métricas para describir una dimensión específica del comportamiento digital.

Cada indicador deberá definir:

- qué mide;
- qué no mide;
- cómo se calcula;
- qué evidencia utiliza;
- cuáles son sus limitaciones.

---

## Índice

Indicador compuesto construido mediante la combinación de múltiples indicadores.

Resume un fenómeno complejo en un único valor, conservando la trazabilidad hacia sus componentes.

---

# M

## Métrica

Resultado obtenido mediante operaciones matemáticas aplicadas sobre variables previamente calculadas.

Las métricas constituyen el nivel intermedio entre las variables y los indicadores.

---

## Metodología

Conjunto de principios, reglas, modelos y documentos oficiales que regulan el funcionamiento analítico de MIPA.

---

## Modelo Analítico

Marco conceptual que define cómo se transforma la evidencia digital en conocimiento analítico mediante procesos deterministas.

---

# N

## Narrativa

Explicación redactada a partir de indicadores previamente calculados por el Pipeline.

Las narrativas no generan cálculos.

Únicamente interpretan resultados respaldados por evidencia.

---

# P

## Pipeline

Proceso automatizado responsable de transformar evidencia en información analítica.

Es el único componente autorizado para ejecutar cálculos dentro de MIPA.

---

## Plataforma

Origen de la evidencia capturada.

Actualmente las plataformas oficiales son:

- Facebook;
- TikTok;
- fuentes externas.

---

## Popularidad Digital

Indicador compuesto que representa el nivel de aceptación observable dentro del entorno digital.

No representa aprobación ciudadana ni intención de voto.

---

## Publicación

Unidad de evidencia correspondiente a un contenido publicado en una plataforma digital.

Las publicaciones constituyen la base del proceso analítico.

---

## Pulso IQ

Índice compuesto que resume el comportamiento digital observable integrando múltiples dimensiones analíticas.

No representa intención de voto ni aprobación electoral.

---

# R

## Referencia

Relación documentada que permite vincular un resultado con la evidencia, metodología y fórmulas que lo originaron.

---

## Riesgo Digital

Indicador compuesto que describe la presencia de condiciones asociadas con conversaciones de mayor capacidad de propagación, persistencia o conflicto dentro del entorno digital observado.

No representa una predicción de crisis ni una evaluación política.

---

# T

## Tema

Agrupación metodológica de evidencias que comparten un mismo asunto principal.

Los temas describen el contenido de las conversaciones.

No describen emociones ni posturas.

---

## Trazabilidad

Capacidad del sistema para reconstruir completamente cualquier resultado desde la evidencia original hasta el Dashboard.

---

# V

## Validación

Proceso mediante el cual el Pipeline verifica la calidad, consistencia e integridad de la información antes de utilizarla en los cálculos analíticos.

---

## Variable

Primer nivel de información derivada obtenido a partir de la evidencia original.

Las variables constituyen la materia prima para el cálculo de métricas, indicadores e índices.

---

# Versionado

Mecanismo mediante el cual el sistema registra la evolución de metodologías, modelos, fórmulas y ejecuciones del Pipeline, garantizando la comparabilidad histórica de los resultados.

---

# Definiciones oficiales

Todas las definiciones incluidas en este documento constituyen el vocabulario oficial de MIPA.

Los nuevos términos incorporados al sistema deberán agregarse a este glosario antes de formar parte de la metodología oficial.

No se permitirá el uso de conceptos ambiguos o con múltiples interpretaciones dentro de la documentación metodológica.

---

# Relación con otros documentos

Este glosario complementa la totalidad de la documentación metodológica de MIPA.

Toda definición utilizada en los siguientes documentos deberá interpretarse conforme a este vocabulario oficial:

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
- 024_CHANGELOG.md

Este documento constituye la referencia terminológica oficial de MIPA.