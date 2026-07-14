# 018 · Etapas del Pipeline

## Propósito

Este documento define las etapas oficiales del Pipeline analítico de MIPA.

El Pipeline constituye el núcleo operativo del sistema y es el único componente autorizado para transformar evidencia en información analítica.

Todas las métricas, indicadores, índices, narrativas y archivos consumidos por el Dashboard deberán generarse exclusivamente mediante este proceso.

No se permiten cálculos fuera del Pipeline.

---

# Objetivo

El Pipeline busca responder una pregunta específica:

> ¿Cómo se transforma la evidencia digital en resultados analíticos completamente auditables, reproducibles y deterministas?

Para ello, el procesamiento se divide en etapas claramente definidas, cada una con responsabilidades específicas y verificables.

---

# Principios

Todas las etapas del Pipeline deberán cumplir los siguientes principios:

- determinismo;
- reproducibilidad;
- trazabilidad;
- auditabilidad;
- incrementalidad;
- versionado;
- automatización.

Cada etapa deberá producir resultados consistentes e independientes de la intervención humana.

---

# Flujo oficial

El flujo oficial del Pipeline es el siguiente:

Captura

↓

Extracción mediante IA

↓

Validación humana

↓

Bases SQLite

↓

Pipeline

↓

analytics.db

↓

analytics.json

↓

narrative.json

↓

dashboard_snapshot.json

↓

Dashboard

Cada etapa consume únicamente la salida de la etapa anterior.

---

# Etapa 1 · Captura

## Objetivo

Registrar la evidencia proveniente de las distintas plataformas digitales.

## Entradas

- Facebook
- TikTok
- fuentes externas

## Salidas

Evidencia sin procesar.

La captura no realiza cálculos analíticos.

---

# Etapa 2 · Extracción mediante IA

## Objetivo

Extraer información estructurada a partir de la evidencia capturada.

Esta etapa podrá incluir tareas como:

- extracción de texto;
- identificación de metadatos;
- normalización inicial.

La IA no calculará indicadores.

Únicamente estructurará información.

---

# Etapa 3 · Validación humana

## Objetivo

Permitir la revisión de la información extraída antes de incorporarla a la base de evidencia.

La validación humana constituye el último punto donde puede corregirse la información capturada.

Una vez aprobada, la evidencia se considera inmutable.

---

# Etapa 4 · Persistencia en SQLite

## Objetivo

Almacenar permanentemente la evidencia validada.

Las bases oficiales son:

- facebook.db
- tiktok.db
- externos.db

Estas bases constituyen la fuente primaria de verdad.

Nunca serán modificadas por el Pipeline.

---

# Etapa 5 · Inicio automático del Pipeline

Una vez finalizada la persistencia en SQLite, el sistema iniciará automáticamente el Pipeline.

Esta ejecución será iniciada por:

panel_carga.py

No será necesaria ninguna acción manual adicional.

---

# Etapa 6 · Validación del Pipeline

Antes de ejecutar cualquier cálculo deberán verificarse:

- integridad de la evidencia;
- consistencia de relaciones;
- disponibilidad de datos;
- cumplimiento del modelo metodológico.

Si alguna validación falla, el Pipeline deberá detenerse.

No podrán generarse resultados parciales.

---

# Etapa 7 · Construcción de variables

El Pipeline calculará todas las variables básicas necesarias para el resto del procesamiento.

Estas variables constituirán la materia prima para las métricas posteriores.

Las variables deberán almacenarse en analytics.db.

---

# Etapa 8 · Construcción de métricas

Utilizando las variables previamente calculadas, el Pipeline generará las métricas oficiales del sistema.

Cada métrica deberá:

- conservar trazabilidad;
- registrar su versión;
- almacenar su fórmula aplicada.

---

# Etapa 9 · Construcción de indicadores

Las métricas servirán como insumo para los indicadores oficiales.

Cada indicador deberá:

- explicar qué mide;
- explicar qué no mide;
- registrar cobertura;
- registrar limitaciones;
- mantener referencias completas.

---

# Etapa 10 · Construcción de índices

Los indicadores podrán combinarse para formar índices compuestos.

Entre ellos:

- Pulso IQ;
- Riesgo Digital;
- otros índices definidos por la metodología.

Las fórmulas oficiales serán documentadas en:

020_FORMULAS.md

---

# Etapa 11 · Persistencia analítica

Todos los resultados calculados deberán almacenarse en:

analytics.db

Esta base constituye el repositorio oficial del conocimiento analítico generado por el Pipeline.

No almacena evidencia original.

Almacena únicamente resultados derivados.

---

# Etapa 12 · Generación de analytics.json

A partir de analytics.db se generará:

analytics.json

Este archivo contendrá exclusivamente información analítica estructurada.

No incluirá narrativas.

---

# Etapa 13 · Generación de narrative.json

El modelo narrativo utilizará analytics.json como única fuente de información.

Claude recibirá:

- indicadores;
- métricas;
- referencias;
- cobertura;
- limitaciones;
- evidencia asociada.

Claude no realizará cálculos.

Únicamente redactará narrativas.

---

# Etapa 14 · Generación de dashboard_snapshot.json

El Pipeline integrará:

- analytics.json;
- narrative.json.

Como resultado producirá:

dashboard_snapshot.json

Este archivo constituye el contrato final consumido por el Dashboard.

---

# Etapa 15 · Visualización

El Dashboard leerá exclusivamente:

dashboard_snapshot.json

El Dashboard no:

- consultará SQLite;
- calculará indicadores;
- modificará resultados;
- reinterpretará información.

Su única responsabilidad será presentar los datos.

---

# Manejo de errores

Cada etapa deberá finalizar en uno de los siguientes estados:

- completada;
- detenida;
- fallida.

Si una etapa falla:

- el Pipeline registrará el incidente;
- conservará evidencia del error;
- evitará la propagación de resultados inválidos.

No se permitirán ejecuciones parcialmente exitosas.

---

# Incrementalidad

El Pipeline deberá procesar únicamente la información nueva o modificada cuando la metodología lo permita.

La incrementalidad nunca podrá comprometer:

- la reproducibilidad;
- la consistencia;
- la trazabilidad.

Cuando sea necesario, podrá ejecutarse un reprocesamiento completo.

---

# Versionado

Cada ejecución deberá registrar:

- identificador;
- fecha;
- versión del Pipeline;
- versión metodológica;
- duración;
- estado;
- componentes ejecutados.

Esto permitirá reconstruir cualquier ejecución histórica.

---

# Reproducibilidad

Procesar nuevamente la misma evidencia utilizando la misma versión metodológica deberá producir exactamente los mismos resultados.

No se permitirán componentes aleatorios ni decisiones manuales durante el procesamiento.

---

# Relación con otros documentos

Este documento se complementa con:

- 005_PIPELINE.md
- 016_VALIDATION_MODEL.md
- 017_TRACEABILITY_MODEL.md
- 019_ANALYTICS_DB_SCHEMA.md
- 020_FORMULAS.md
- 021_REFERENCES.md

En conjunto, estos documentos definen el funcionamiento operativo completo del Pipeline analítico de MIPA, desde la captura de evidencia hasta la generación del contrato final consumido por el Dashboard.