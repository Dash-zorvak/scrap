# MIPA — Motor de Inteligencia Política Auditada
## ANALYTICS_DB_DICTIONARY
**Documento:** 025_ANALYTICS_DB_DICTIONARY.md  
**Estado:** APROBADO (Baseline)  
**Versión metodológica:** MIPA 1.0.0  
**Clasificación:** Especificación Técnica (Obligatorio)

---

# 1. Propósito

Este documento define el diccionario oficial de datos de `analytics.db`.

`analytics.db` constituye la base analítica oficial del sistema MIPA.

No almacena evidencia original.

No almacena publicaciones.

No almacena comentarios.

Almacena exclusivamente resultados derivados del Pipeline Analítico.

---

# 2. Objetivos

analytics.db tiene cinco objetivos principales.

- Centralizar todos los cálculos.
- Eliminar cálculos en tiempo de ejecución.
- Mantener trazabilidad completa.
- Permitir auditoría matemática.
- Servir como única fuente analítica para el Dashboard.

---

# 3. Alcance

analytics.db almacena.

- variables derivadas;
- indicadores;
- índices;
- agregaciones;
- estadísticas;
- referencias;
- metadatos;
- resultados históricos.

Nunca reemplaza las bases fuente.

---

# 4. Bases del Sistema

El ecosistema completo queda definido como.

| Base | Función |
|-------|---------|
| facebook.db | Evidencia Facebook |
| tiktok.db | Evidencia TikTok |
| externos.db | Evidencia medios externos |
| analytics.db | Variables e indicadores derivados |

---

# 5. Principios

analytics.db sigue los siguientes principios.

## DB-001

Nunca modifica evidencia.

---

## DB-002

Nunca elimina información histórica.

---

## DB-003

Todo registro es reproducible.

---

## DB-004

Todo registro posee trazabilidad.

---

## DB-005

Todo cálculo es determinista.

---

# 6. Arquitectura General

```
facebook.db
            \
tiktok.db -----> Pipeline -----> analytics.db -----> dashboard_snapshot.json
            /
externos.db
```

analytics.db representa el resultado oficial del Pipeline.

---

# 7. Organización

Las tablas se agrupan en cinco categorías.

## Variables

Resultados intermedios.

---

## Indicadores

Indicadores simples.

---

## Índices

Indicadores compuestos.

---

## Referencias

Relaciones con evidencia.

---

## Auditoría

Información de ejecución.

---

# 8. Convenciones

Todos los nombres utilizarán.

- snake_case
- inglés
- singular para entidades
- prefijos consistentes

---

# 9. Tipos de Datos

Los tipos oficiales serán.

| Tipo | Uso |
|------|-----|
| INTEGER | Conteos |
| REAL | Índices |
| TEXT | Identificadores |
| BOOLEAN | Estados |
| DATETIME | Fechas |
| JSON | Configuración o evidencia agregada |

---

# 10. Llaves Primarias

Toda tabla deberá poseer.

- Primary Key
- Fecha de creación
- Versión metodológica
- Identificador de ejecución

---

# 11. Tabla: pipeline_run

Describe cada ejecución del Pipeline.

Campos mínimos.

| Campo | Tipo |
|--------|------|
| run_id | TEXT |
| started_at | DATETIME |
| finished_at | DATETIME |
| methodology_version | TEXT |
| pipeline_version | TEXT |
| status | TEXT |

---

# 12. Tabla: metric

Almacena métricas simples.

Campos.

| Campo | Tipo |
|--------|------|
| metric_id | TEXT |
| metric_name | TEXT |
| metric_value | REAL |
| period_start | DATE |
| period_end | DATE |
| run_id | TEXT |

---

# 13. Tabla: indicator

Almacena indicadores oficiales.

Campos.

| Campo | Tipo |
|--------|------|
| indicator_id | TEXT |
| indicator_name | TEXT |
| indicator_value | REAL |
| confidence | REAL |
| methodology_version | TEXT |
| run_id | TEXT |

---

# 14. Tabla: index_score

Almacena índices compuestos.

Ejemplos.

- Pulso IQ
- Popularidad Digital
- Riesgo Digital

Campos.

| Campo | Tipo |
|--------|------|
| index_name | TEXT |
| value | REAL |
| normalized_value | REAL |
| run_id | TEXT |

---

# 15. Tabla: component_score

Describe cada componente utilizado para construir un índice.

Ejemplo.

Pulso IQ

↓

Conversación

↓

Peso

↓

Contribución

Campos.

| Campo | Tipo |
|--------|------|
| component_name | TEXT |
| raw_value | REAL |
| normalized_value | REAL |
| weight | REAL |
| contribution | REAL |

---

# 16. Tabla: evidence_reference

Relaciona indicadores con evidencia.

Campos.

| Campo | Tipo |
|--------|------|
| reference_id | TEXT |
| indicator_name | TEXT |
| platform | TEXT |
| source_table | TEXT |
| source_id | TEXT |
| url | TEXT |

Esta tabla permite reconstruir cualquier indicador.

---

# 17. Tabla: normalization

Almacena parámetros de normalización.

Ejemplo.

mínimo

máximo

escala

versión

---

# 18. Tabla: formula

Documenta las fórmulas utilizadas.

Campos.

| Campo | Tipo |
|--------|------|
| formula_name | TEXT |
| formula_version | TEXT |
| expression | TEXT |
| description | TEXT |

---

# 19. Tabla: limitation

Documenta las limitaciones metodológicas aplicadas durante una ejecución.

Ejemplo.

Cobertura parcial.

Plataforma sin datos.

Periodo incompleto.

---

# 20. Tabla: dashboard_cache

Representa exactamente la información exportada al Dashboard.

No contiene lógica.

Únicamente datos listos para visualizar.

---

# 21. Tabla: audit_log

Registra toda modificación realizada por el Pipeline.

Campos mínimos.

- timestamp
- operación
- versión
- usuario
- módulo
- resultado

---

# 22. Relaciones

Toda relación deberá utilizar llaves explícitas.

Nunca relaciones implícitas.

---

# 23. Versionado

Cada registro almacenará.

- metodología;
- algoritmo;
- Pipeline;
- fecha;
- ejecución.

---

# 24. Persistencia

analytics.db conservará históricos.

Nunca sobrescribirá resultados sin conservar la ejecución previa.

---

# 25. Reproducibilidad

Cualquier indicador deberá poder reconstruirse utilizando.

- evidencia original;
- versión metodológica;
- fórmula;
- parámetros;
- identificador de ejecución.

---

# 26. Restricciones

Queda prohibido almacenar.

- publicaciones completas;
- comentarios completos;
- imágenes;
- archivos PDF;
- capturas;
- contenido multimedia.

Toda evidencia permanece en las bases originales.

---

# 27. Rendimiento

analytics.db estará optimizada para lectura.

No para escritura masiva.

La escritura ocurre únicamente durante el Pipeline.

---

# 28. Integridad

Toda tabla deberá cumplir.

- claves primarias;
- claves foráneas;
- restricciones de tipo;
- restricciones de unicidad;
- validaciones metodológicas.

---

# 29. Compatibilidad

analytics.db deberá permitir futuras migraciones sin romper versiones anteriores.

---

# 30. Criterios de Aceptación

analytics.db será considerado correctamente implementado cuando.

- pueda reconstruir todos los indicadores;
- mantenga trazabilidad completa;
- preserve históricos;
- no almacene evidencia duplicada;
- permita auditoría matemática completa.

---

# 31. Vigencia

Este documento constituye la especificación oficial del diccionario de datos de analytics.db.

Toda modificación requerirá una nueva versión metodológica.

---

# Control del Documento

| Campo | Valor |
|--------|-------|
| Documento | 025_ANALYTICS_DB_DICTIONARY.md |
| Estado | Aprobado |
| Versión | 1.0.0 |
| Tipo | Especificación Técnica |
| Depende de | 000_PROJECT_CHARTER.md – 024_CHANGELOG.md |
| Referenciado por | 026_PIPELINE_VARIABLES.md, 027_JSON_SCHEMA_REFERENCE.md |
| Última actualización | Baseline MIPA 1.0 |