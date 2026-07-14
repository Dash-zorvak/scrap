# 021 · Referencias

## Propósito

Este documento define el modelo oficial de referencias de MIPA.

Su objetivo es garantizar que toda variable, métrica, indicador, índice, narrativa y visualización pueda respaldarse mediante evidencia verificable.

En MIPA, la referencia principal no es una cita bibliográfica.

La referencia principal es siempre la evidencia que originó el resultado.

---

# Objetivo

El Modelo de Referencias busca responder una pregunta específica:

> ¿Cómo puede verificarse cualquier afirmación realizada por el sistema?

La respuesta deberá encontrarse siempre en la evidencia utilizada por el Pipeline.

Toda afirmación deberá poder demostrarse.

---

# Principios

El sistema de referencias se fundamenta en los siguientes principios:

- verificabilidad;
- transparencia;
- trazabilidad;
- evidencia primero;
- reproducibilidad;
- auditabilidad.

No se permitirán afirmaciones sin respaldo.

---

# Fuente primaria

La fuente primaria de referencia está constituida por la evidencia almacenada en:

- facebook.db;
- tiktok.db;
- externos.db.

Estas bases representan la única fuente oficial de información utilizada por el Pipeline.

Toda referencia deberá poder rastrearse hasta ellas.

---

# Jerarquía de referencias

Las referencias seguirán la siguiente jerarquía:

Evidencia original

↓

Variables

↓

Métricas

↓

Indicadores

↓

Índices

↓

Narrativas

↓

Dashboard

Cada nivel deberá conservar referencias hacia el nivel anterior.

---

# Referencias de evidencia

Toda evidencia utilizada por el sistema deberá conservar, como mínimo:

- identificador único;
- plataforma;
- tipo de evidencia;
- fecha de publicación;
- enlace original cuando exista.

Estos elementos permiten localizar el origen de cualquier resultado.

---

# Referencias de variables

Cada variable deberá registrar:

- evidencia utilizada;
- definición;
- versión metodológica;
- ejecución del Pipeline.

Esto permite conocer exactamente cómo fue construida.

---

# Referencias de métricas

Cada métrica deberá indicar:

- variables utilizadas;
- fórmula aplicada;
- versión metodológica;
- fecha de cálculo.

La referencia deberá permitir reconstruir completamente el cálculo.

---

# Referencias de indicadores

Cada indicador deberá registrar:

- métricas utilizadas;
- cobertura;
- limitaciones;
- versión metodológica;
- referencias hacia la evidencia correspondiente.

No podrán existir indicadores sin respaldo verificable.

---

# Referencias de índices

Los índices compuestos deberán registrar:

- indicadores participantes;
- ponderaciones aplicadas;
- fórmula oficial;
- versión correspondiente.

Cada índice deberá poder descomponerse completamente.

---

# Referencias de narrativas

Toda narrativa deberá incluir referencias explícitas hacia:

- indicadores utilizados;
- evidencia relacionada;
- cobertura del análisis;
- limitaciones;
- período evaluado.

Las narrativas no podrán contener conclusiones que no puedan relacionarse con evidencia verificable.

---

# Referencias del Dashboard

Cada visualización presentada por el Dashboard deberá permitir identificar:

- indicador mostrado;
- período analizado;
- cobertura;
- versión metodológica;
- referencia hacia la evidencia correspondiente.

El Dashboard únicamente presentará referencias generadas previamente por el Pipeline.

---

# Acceso a la evidencia

Siempre que la plataforma lo permita, el sistema deberá facilitar el acceso directo a:

- publicaciones originales;
- comentarios originales;
- enlaces públicos;
- identificadores de contenido.

Esto permitirá verificar la información presentada sin reinterpretaciones.

---

# Cobertura

Toda referencia deberá indicar el alcance del análisis realizado.

Como mínimo deberá informar:

- plataformas incluidas;
- período analizado;
- cantidad de publicaciones;
- cantidad de comentarios;
- cobertura efectiva;
- registros excluidos, cuando corresponda.

La cobertura forma parte obligatoria del contexto analítico.

---

# Referencias metodológicas

Además de la evidencia, cada resultado deberá conservar referencias hacia:

- versión del Pipeline;
- versión metodológica;
- versión de las fórmulas;
- modelos analíticos utilizados.

Esto garantiza la reconstrucción completa del proceso.

---

# Referencias documentales

Cuando un indicador se base en una definición metodológica específica, deberá conservar la referencia al documento oficial correspondiente.

Entre ellos:

- Project Charter;
- Modelo Analítico;
- Catálogo de Métricas;
- Modelo de Emociones;
- Modelo de Temas;
- Modelo de Posturas;
- Fórmulas.

Estas referencias documentan el marco conceptual utilizado.

---

# Auditoría

El sistema de referencias deberá permitir responder preguntas como:

- ¿Qué evidencia respalda este indicador?
- ¿Qué publicaciones participaron?
- ¿Qué comentarios fueron utilizados?
- ¿Qué fórmula produjo este resultado?
- ¿Qué metodología estaba vigente?
- ¿Qué versión del Pipeline ejecutó el cálculo?

Estas respuestas deberán obtenerse sin intervención manual.

---

# Reproducibilidad

Toda referencia deberá permanecer estable entre ejecuciones.

Procesar nuevamente la misma evidencia utilizando las mismas versiones metodológicas deberá producir exactamente las mismas relaciones de referencia.

No se permitirán referencias ambiguas o dinámicas.

---

# Limitaciones

El Modelo de Referencias garantiza el acceso al origen de la información utilizada por MIPA.

No garantiza:

- la permanencia pública de enlaces externos;
- la disponibilidad futura de contenido eliminado por las plataformas;
- la autenticidad del contenido publicado.

Su función es preservar la cadena documental que respalda cada resultado generado por el sistema.

---

# Relación con otros documentos

Este documento se complementa con:

- 006_EVIDENCE_MODEL.md
- 008_NARRATIVE_MODEL.md
- 017_TRACEABILITY_MODEL.md
- 019_ANALYTICS_DB_SCHEMA.md
- 020_FORMULAS.md
- 022_LIMITATIONS.md

En conjunto, estos documentos establecen el modelo documental que convierte cada resultado de MIPA en una afirmación verificable, respaldada por evidencia y completamente auditable.