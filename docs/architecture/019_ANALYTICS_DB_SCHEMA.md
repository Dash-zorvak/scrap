# 019 · Esquema de analytics.db

## Propósito

Este documento define la arquitectura lógica de `analytics.db`, la base de datos analítica oficial de MIPA.

Su propósito es almacenar todos los resultados derivados producidos por el Pipeline, preservando su trazabilidad, reproducibilidad y versionado.

`analytics.db` no almacena evidencia original.

La evidencia permanece exclusivamente en las bases de datos fuente.

---

# Objetivo

`analytics.db` responde una pregunta específica:

> ¿Dónde se almacena el conocimiento analítico generado por el Pipeline de forma estructurada, auditable y reutilizable?

Esta base constituye el repositorio oficial de todas las variables, métricas, indicadores e índices producidos por MIPA.

---

# Alcance

`analytics.db` almacenará únicamente información derivada.

Entre otros elementos:

- variables;
- métricas;
- indicadores;
- índices;
- referencias;
- metadatos;
- resultados de validación;
- información de trazabilidad;
- historial de ejecuciones del Pipeline.

Nunca almacenará evidencia primaria.

---

# Principios

La estructura de `analytics.db` deberá cumplir los siguientes principios:

- normalización;
- integridad referencial;
- trazabilidad completa;
- versionado;
- reproducibilidad;
- auditabilidad.

Cada registro deberá poder relacionarse con su origen.

---

# Fuente de datos

Toda la información almacenada en `analytics.db` deberá provenir exclusivamente del Pipeline oficial.

No se permitirán:

- inserciones manuales;
- cálculos externos;
- modificaciones realizadas por el Dashboard.

El Pipeline será el único componente autorizado para escribir en esta base.

---

# Relación con las bases de evidencia

Las bases de evidencia son:

- facebook.db;
- tiktok.db;
- externos.db.

Estas bases contienen la información original.

`analytics.db` únicamente almacenará referencias hacia dicha evidencia y los resultados derivados de su procesamiento.

---

# Modelo lógico

La estructura lógica de `analytics.db` se organiza en seis niveles principales:

1. Variables.
2. Métricas.
3. Indicadores.
4. Índices.
5. Metadatos.
6. Trazabilidad.

Cada nivel depende del anterior.

---

# Variables

Las variables representan el primer nivel de procesamiento analítico.

Cada registro deberá conservar como mínimo:

- identificador;
- nombre;
- definición;
- valor;
- unidad;
- evidencia utilizada;
- versión metodológica;
- fecha de cálculo;
- ejecución del Pipeline.

Las variables constituyen la base de todos los cálculos posteriores.

---

# Métricas

Las métricas representan resultados obtenidos mediante operaciones sobre variables.

Cada métrica deberá registrar:

- identificador;
- nombre;
- definición;
- fórmula aplicada;
- variables utilizadas;
- valor calculado;
- unidad;
- versión metodológica;
- ejecución del Pipeline.

---

# Indicadores

Los indicadores sintetizan una o varias métricas para describir una dimensión específica del comportamiento digital.

Cada indicador deberá almacenar:

- identificador;
- nombre;
- definición;
- qué mide;
- qué no mide;
- métricas utilizadas;
- valor;
- cobertura;
- limitaciones;
- versión metodológica.

---

# Índices

Los índices representan indicadores compuestos construidos a partir de múltiples indicadores.

Cada índice deberá registrar:

- identificador;
- nombre;
- indicadores participantes;
- ponderaciones;
- fórmula oficial;
- valor final;
- versión metodológica.

Ejemplos:

- Pulso IQ;
- Riesgo Digital.

---

# Metadatos

Los metadatos describen el contexto del procesamiento.

Entre ellos:

- período analizado;
- plataformas utilizadas;
- cantidad de publicaciones;
- cantidad de comentarios;
- cobertura efectiva;
- fecha de ejecución;
- duración del Pipeline.

Estos datos acompañan a todos los resultados analíticos.

---

# Trazabilidad

La base deberá conservar todas las relaciones necesarias para reconstruir cualquier resultado.

Como mínimo deberá registrar referencias hacia:

- evidencia original;
- variables;
- métricas;
- indicadores;
- índices;
- ejecución del Pipeline;
- versión metodológica.

Ningún registro podrá perder su cadena de origen.

---

# Validaciones

`analytics.db` almacenará los resultados de las validaciones ejecutadas durante el Pipeline.

Esto permitirá conocer:

- qué fue validado;
- cuándo;
- con qué resultado;
- bajo qué versión metodológica.

La información de validación forma parte del historial analítico.

---

# Versionado

Todos los registros deberán conservar las versiones correspondientes de:

- Pipeline;
- metodología;
- modelos analíticos;
- fórmulas.

El versionado garantiza la comparabilidad histórica de los resultados.

---

# Integridad referencial

Toda relación entre registros deberá mantener integridad referencial.

No podrán existir:

- referencias huérfanas;
- indicadores sin métricas;
- métricas sin variables;
- variables sin evidencia.

La consistencia de la base constituye un requisito obligatorio.

---

# Escritura

Únicamente el Pipeline podrá:

- insertar registros;
- actualizar resultados;
- generar nuevas versiones.

El Dashboard tendrá acceso exclusivamente de lectura al resultado final mediante `dashboard_snapshot.json`.

Nunca accederá directamente a `analytics.db`.

---

# Consumo

`analytics.db` será utilizada por el Pipeline para generar:

- analytics.json;
- narrative.json;
- dashboard_snapshot.json.

Estos archivos constituyen contratos independientes definidos en la documentación metodológica.

---

# Auditoría

Todo registro almacenado deberá permitir responder preguntas como:

- ¿Cuándo fue calculado?
- ¿Con qué evidencia?
- ¿Qué versión metodológica utilizó?
- ¿Qué fórmula produjo este valor?
- ¿Qué ejecución del Pipeline lo generó?

Estas respuestas deberán obtenerse directamente desde la base.

---

# Reproducibilidad

Ejecutar nuevamente el Pipeline sobre la misma evidencia deberá producir una estructura equivalente en `analytics.db`, siempre que se utilicen las mismas versiones metodológicas.

No se permitirán modificaciones manuales posteriores al procesamiento.

---

# Limitaciones

`analytics.db` no sustituye las bases de evidencia.

No almacena publicaciones originales.

No almacena comentarios originales.

No constituye un sistema documental.

Su función exclusiva es conservar el conocimiento analítico derivado generado por el Pipeline.

---

# Relación con otros documentos

Este documento se complementa con:

- 003_DATA_MODEL.md
- 005_PIPELINE.md
- 009_JSON_CONTRACTS.md
- 017_TRACEABILITY_MODEL.md
- 018_PIPELINE_STAGES.md
- 020_FORMULAS.md

En conjunto, estos documentos definen la arquitectura de almacenamiento analítico que permite a MIPA producir resultados completamente auditables, reproducibles y desacoplados de la evidencia original.