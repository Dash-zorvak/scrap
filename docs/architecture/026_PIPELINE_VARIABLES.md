# MIPA — Motor de Inteligencia Política Auditada
## PIPELINE_VARIABLES
**Documento:** 026_PIPELINE_VARIABLES.md  
**Estado:** APROBADO (Baseline)  
**Versión metodológica:** MIPA 1.0.0  
**Clasificación:** Especificación Técnica (Obligatorio)

---

# 1. Propósito

Este documento define el catálogo oficial de variables utilizadas por el Pipeline Analítico de MIPA.

Una variable representa cualquier dato derivado, normalizado o calculado que participa en la construcción de métricas, indicadores e índices.

Este documento constituye la única referencia autorizada para la definición de variables analíticas.

---

# 2. Objetivos

El catálogo de variables tiene los siguientes objetivos.

- Estandarizar nombres.
- Evitar duplicidades.
- Facilitar auditorías.
- Garantizar reproducibilidad.
- Permitir trazabilidad completa.

---

# 3. Principios

## VAR-001

Toda variable tendrá un nombre único.

---

## VAR-002

Toda variable tendrá una definición oficial.

---

## VAR-003

Toda variable tendrá una unidad de medida.

---

## VAR-004

Toda variable deberá indicar su origen.

---

## VAR-005

Toda variable deberá indicar si es persistente o temporal.

---

# 4. Clasificación

Las variables se agrupan en las siguientes categorías.

- Variables de Evidencia
- Variables Derivadas
- Variables Normalizadas
- Variables de Indicadores
- Variables de Índices
- Variables de Auditoría

---

# 5. Estructura Oficial

Toda variable deberá documentarse mediante la siguiente estructura.

| Campo | Descripción |
|--------|-------------|
| variable_name | Nombre único |
| description | Definición oficial |
| data_type | Tipo de dato |
| unit | Unidad de medida |
| source | Origen |
| calculation | Método de cálculo |
| persistence | Temporal o persistente |
| version | Versión metodológica |

---

# 6. Variables de Evidencia

Son variables obtenidas directamente de las bases fuente.

Ejemplos.

- facebook_posts
- facebook_comments
- tiktok_videos
- tiktok_comments
- external_posts
- external_comments

Estas variables nunca son modificadas.

---

# 7. Variables de Cobertura

Miden el volumen de información disponible.

Ejemplos.

- analyzed_posts
- analyzed_comments
- analyzed_platforms
- analyzed_sources
- coverage_percentage

---

# 8. Variables de Participación

Representan interacción observable.

Ejemplos.

- total_reactions
- total_comments
- total_shares
- total_views
- total_engagement

---

# 9. Variables Temporales

Representan comportamiento durante un período.

Ejemplos.

- daily_growth
- weekly_growth
- monthly_growth
- activity_rate

---

# 10. Variables de Emoción

Representan la distribución emocional.

Ejemplos.

- joy_score
- anger_score
- trust_score
- fear_score
- irony_score
- gratitude_score

Cada emoción se documentará en el Modelo de Emociones.

---

# 11. Variables de Postura

Representan la postura observada.

Ejemplos.

- support_ratio
- criticism_ratio
- neutral_ratio

---

# 12. Variables Temáticas

Representan concentración temática.

Ejemplos.

- security_share
- governance_share
- infrastructure_share
- environment_share

---

# 13. Variables de Riesgo

Representan factores de riesgo.

Ejemplos.

- propagation_rate
- controversy_score
- friction_score
- concentration_score
- escalation_score

---

# 14. Variables de Popularidad

Ejemplos.

- acceptance_score
- interaction_quality
- recognition_score
- audience_response

---

# 15. Variables de Pulso IQ

Ejemplos.

- conversation_component
- interaction_component
- perception_component
- diversity_component
- risk_component

---

# 16. Variables de Calidad

Representan calidad del conjunto analizado.

Ejemplos.

- confidence_score
- validation_score
- completeness_score
- consistency_score

---

# 17. Variables de Normalización

Son utilizadas internamente por el Pipeline.

Ejemplos.

- normalized_value
- percentile_rank
- z_score
- min_max_value

Nunca se muestran al usuario final.

---

# 18. Variables de Auditoría

Ejemplos.

- pipeline_version
- methodology_version
- execution_time
- run_id
- generated_at

---

# 19. Variables Calculadas

Toda variable calculada deberá documentar.

- fórmula;
- variables utilizadas;
- versión;
- responsable del cálculo.

---

# 20. Variables Persistentes

Se almacenan permanentemente en analytics.db.

Ejemplos.

- indicadores
- índices
- métricas
- resultados históricos

---

# 21. Variables Temporales

Existen únicamente durante la ejecución del Pipeline.

No deberán persistirse.

---

# 22. Convenciones

Toda variable utilizará.

- snake_case
- inglés
- nombres descriptivos
- sin abreviaturas ambiguas

---

# 23. Restricciones

Queda prohibido.

- reutilizar nombres con significados distintos;
- redefinir variables sin cambiar versión metodológica;
- utilizar variables no documentadas.

---

# 24. Versionado

Toda variable registrará.

- versión metodológica;
- versión del Pipeline;
- fecha de creación;
- última modificación.

---

# 25. Compatibilidad

Las variables existentes no deberán cambiar de significado entre versiones.

Cuando una variable cambie semánticamente deberá crearse una nueva.

---

# 26. Validación

Antes de utilizar una variable el Pipeline deberá validar.

- tipo;
- rango esperado;
- origen;
- consistencia;
- disponibilidad.

---

# 27. Auditoría

Toda variable deberá responder.

- de dónde proviene;
- cómo se calcula;
- cuándo fue calculada;
- con qué versión;
- mediante qué ejecución.

---

# 28. Criterios de Aceptación

El catálogo de variables será considerado correctamente implementado cuando.

- todas las variables estén documentadas;
- no existan duplicidades;
- toda variable tenga trazabilidad;
- todas las fórmulas sean reproducibles;
- todas las dependencias sean conocidas.

---

# 29. Vigencia

Este documento constituye el catálogo oficial de variables del Pipeline Analítico de MIPA.

Toda incorporación o modificación de variables requerirá actualización de este documento.

---

# Control del Documento

| Campo | Valor |
|--------|-------|
| Documento | 026_PIPELINE_VARIABLES.md |
| Estado | Aprobado |
| Versión | 1.0.0 |
| Tipo | Especificación Técnica |
| Depende de | 000_PROJECT_CHARTER.md – 025_ANALYTICS_DB_DICTIONARY.md |
| Referenciado por | 027_JSON_SCHEMA_REFERENCE.md, 028_FORMULA_REFERENCE.md, 029_IMPLEMENTATION_GUIDE.md |
| Última actualización | Baseline MIPA 1.0 |