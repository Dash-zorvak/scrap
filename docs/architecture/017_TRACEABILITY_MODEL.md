# 017 · Modelo de Trazabilidad

## Propósito

El Modelo de Trazabilidad define la metodología oficial mediante la cual MIPA garantiza que todo dato, variable, métrica, indicador, índice, narrativa y visualización pueda reconstruirse completamente hasta su evidencia original.

La trazabilidad constituye uno de los principios fundamentales del sistema.

Ningún resultado podrá existir sin una cadena verificable de evidencia que permita explicar exactamente cómo fue obtenido.

---

# Objetivo

El Modelo de Trazabilidad busca responder una pregunta específica:

> ¿Puede demostrarse, paso a paso, de dónde proviene cada resultado mostrado por el sistema?

La respuesta deberá ser siempre afirmativa.

Todo cálculo deberá ser completamente auditable.

---

# Principios

La trazabilidad de MIPA se fundamenta en los siguientes principios:

- evidencia primero;
- reproducibilidad;
- transparencia;
- determinismo;
- auditabilidad;
- verificabilidad.

Todo resultado deberá poder reconstruirse utilizando únicamente la evidencia almacenada y la metodología oficial.

---

# Alcance

La trazabilidad aplica a todos los componentes del sistema, incluyendo:

- publicaciones;
- comentarios;
- metadatos;
- variables;
- métricas;
- indicadores;
- índices;
- narrativas;
- archivos JSON;
- visualizaciones del Dashboard.

No existen excepciones.

---

# Cadena oficial de trazabilidad

Todo resultado deberá poder recorrerse mediante la siguiente cadena:

Evidencia

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

dashboard_snapshot.json

↓

Dashboard

Cada nivel deberá conservar referencias explícitas al nivel inmediatamente anterior.

---

# Evidencia como fuente de verdad

La evidencia constituye la fuente primaria del sistema.

La evidencia permanece almacenada en las bases de datos originales:

- facebook.db;
- tiktok.db;
- externos.db.

Estas bases nunca serán modificadas por el Pipeline.

Todo cálculo deberá originarse en esta evidencia.

---

# Identificadores

Cada elemento utilizado por el Pipeline deberá poseer un identificador único y estable.

Como mínimo deberán existir identificadores para:

- evidencia;
- variables;
- métricas;
- indicadores;
- índices;
- narrativas;
- ejecuciones del Pipeline.

Los identificadores garantizan la reconstrucción exacta del proceso analítico.

---

# Relaciones

Todo elemento derivado deberá mantener referencias explícitas hacia los elementos que lo originaron.

Por ejemplo:

Una métrica deberá conocer las variables utilizadas.

Un indicador deberá conocer las métricas utilizadas.

Una narrativa deberá conocer los indicadores que describe.

El Dashboard únicamente visualizará información ya referenciada.

---

# Trazabilidad de variables

Cada variable almacenada en analytics.db deberá registrar como mínimo:

- identificador;
- nombre;
- origen;
- evidencia utilizada;
- versión metodológica;
- fecha de cálculo;
- ejecución del Pipeline.

Las variables constituyen el primer nivel analítico derivado de la evidencia.

---

# Trazabilidad de métricas

Cada métrica deberá registrar:

- variables utilizadas;
- fórmula aplicada;
- versión metodológica;
- fecha de cálculo;
- ejecución correspondiente.

La métrica deberá poder recalcularse utilizando exactamente las mismas variables.

---

# Trazabilidad de indicadores

Todo indicador deberá conservar:

- métricas utilizadas;
- componentes involucrados;
- fórmula oficial aplicada;
- versión metodológica;
- referencias de evidencia.

Esto permitirá reconstruir completamente cualquier resultado.

---

# Trazabilidad de índices

Los índices compuestos deberán registrar adicionalmente:

- indicadores participantes;
- ponderaciones utilizadas;
- normalizaciones aplicadas;
- parámetros metodológicos.

Cada índice deberá poder descomponerse completamente en sus componentes.

---

# Trazabilidad de narrativas

Las narrativas deberán registrar:

- indicadores utilizados;
- cifras citadas;
- evidencia relacionada;
- cobertura;
- limitaciones;
- versión del modelo narrativo.

La narrativa nunca podrá contener afirmaciones sin respaldo verificable.

---

# Trazabilidad del Dashboard

El Dashboard no generará información.

Cada elemento visual deberá corresponder directamente a un dato contenido en dashboard_snapshot.json.

Cada dato del snapshot deberá mantener referencias hacia analytics.db.

analytics.db deberá mantener referencias hacia la evidencia original.

De esta forma, cualquier cifra mostrada podrá rastrearse hasta su origen.

---

# Trazabilidad del Pipeline

Cada ejecución del Pipeline deberá registrar:

- identificador de ejecución;
- fecha y hora;
- versión del Pipeline;
- versión metodológica;
- conjuntos de datos utilizados;
- estado de la ejecución;
- resultados generados.

Esto permitirá reconstruir cualquier procesamiento histórico.

---

# Versionado

Toda referencia deberá incluir las versiones correspondientes de:

- Pipeline;
- metodología;
- modelos analíticos;
- fórmulas.

Los resultados obtenidos bajo distintas versiones deberán permanecer diferenciados.

---

# Auditoría

El Modelo de Trazabilidad permite que cualquier auditor pueda responder preguntas como:

- ¿De dónde proviene esta cifra?
- ¿Qué publicaciones fueron utilizadas?
- ¿Qué comentarios participaron?
- ¿Qué fórmula fue aplicada?
- ¿Qué versión metodológica produjo este resultado?
- ¿Qué ejecución del Pipeline generó este dato?

Estas respuestas deberán obtenerse sin intervención manual.

---

# Evidencia mínima

Todo resultado deberá permitir acceder, como mínimo, a:

- publicaciones originales;
- comentarios originales;
- plataforma;
- período analizado;
- identificadores de evidencia;
- variables utilizadas;
- fórmulas aplicadas.

Si alguno de estos elementos no puede recuperarse, la trazabilidad será considerada incompleta.

---

# Reproducibilidad

Ejecutar nuevamente el Pipeline sobre la misma evidencia utilizando las mismas versiones metodológicas deberá producir exactamente la misma cadena de trazabilidad.

No se permitirán referencias ambiguas, dinámicas o dependientes del usuario.

---

# Limitaciones

La trazabilidad garantiza el origen y la reconstrucción de los resultados.

No garantiza:

- la veracidad del contenido publicado;
- la autenticidad de las cuentas;
- la representatividad absoluta del universo digital.

Su función es demostrar de manera objetiva cómo se produjo cada resultado mostrado por MIPA.

---

# Relación con otros documentos

Este modelo se complementa con:

- 006_EVIDENCE_MODEL.md
- 016_VALIDATION_MODEL.md
- 018_PIPELINE_STAGES.md
- 019_ANALYTICS_DB_SCHEMA.md
- 020_FORMULAS.md
- 021_REFERENCES.md

En conjunto, estos documentos establecen la infraestructura metodológica que convierte a MIPA en un sistema completamente auditable, reproducible y verificable desde la evidencia original hasta cada visualización presentada en el Dashboard.