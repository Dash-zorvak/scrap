# MIPA — Motor de Inteligencia Política Auditada
## PIPELINE
**Documento:** 005_PIPELINE.md  
**Estado:** APROBADO (Baseline)  
**Versión metodológica:** MIPA 1.0.0  
**Clasificación:** Normativo (Obligatorio)

---

# 1. Propósito

Este documento define el Pipeline Oficial de MIPA.

El Pipeline es el único componente autorizado para transformar evidencia validada en información analítica.

Toda transformación de datos deberá ejecutarse exclusivamente dentro del Pipeline.

Ningún otro componente podrá generar métricas oficiales.

---

# 2. Objetivos

El Pipeline tiene cinco objetivos fundamentales.

- garantizar reproducibilidad;
- garantizar trazabilidad;
- garantizar consistencia;
- garantizar auditabilidad;
- garantizar determinismo.

---

# 3. Alcance

El Pipeline inicia cuando la evidencia ya fue validada por un analista.

Finaliza cuando los resultados oficiales han sido persistidos y están disponibles para el Dashboard.

---

# 4. Entradas Oficiales

El Pipeline podrá consumir únicamente:

- facebook.db
- tiktok.db
- externos.db

Todas las entradas deberán encontrarse previamente validadas.

---

# 5. Salidas Oficiales

El Pipeline produce únicamente:

- analytics.db
- dashboard_snapshot.json
- logs de ejecución
- registros de auditoría
- reportes de validación

No produce narrativas.

No produce recomendaciones.

---

# 6. Principios del Pipeline

## PIPE-001

Todo cálculo deberá ejecutarse mediante procesos deterministas.

---

## PIPE-002

Toda ejecución deberá poder repetirse.

---

## PIPE-003

Toda transformación deberá quedar registrada.

---

## PIPE-004

Toda salida deberá poder reconstruirse.

---

## PIPE-005

La evidencia original nunca podrá modificarse.

---

# 7. Flujo Oficial

```
Bases Fuente

↓

Validación de Integridad

↓

Normalización

↓

Construcción de Variables

↓

Construcción de Métricas

↓

Construcción de Indicadores

↓

Construcción de Índices

↓

Validación Final

↓

analytics.db

↓

dashboard_snapshot.json
```

---

# 8. Fase 1 — Validación de Integridad

Antes de iniciar cualquier cálculo el Pipeline deberá verificar.

- existencia de bases;
- existencia de tablas obligatorias;
- integridad referencial;
- consistencia temporal;
- ausencia de corrupción;
- compatibilidad metodológica.

Si alguna validación falla.

El Pipeline deberá detenerse.

---

# 9. Fase 2 — Normalización

Todos los registros deberán normalizarse.

Incluye.

- fechas;
- números;
- identificadores;
- plataformas;
- zonas horarias;
- caracteres especiales;
- codificación.

La normalización nunca modificará la evidencia.

Generará únicamente datos derivados.

---

# 10. Fase 3 — Validación Semántica

El Pipeline verificará.

- emociones válidas;
- temas válidos;
- posturas válidas;
- plataformas válidas;
- rangos permitidos;
- consistencia entre entidades.

Los registros inválidos deberán registrarse.

Nunca eliminarse silenciosamente.

---

# 11. Fase 4 — Construcción de Variables

Las variables constituyen la materia prima del modelo analítico.

Ejemplos.

- total de publicaciones;
- total de comentarios;
- total de reacciones;
- total de compartidos;
- total de visualizaciones;
- emociones observadas;
- temas observados;
- posturas observadas.

---

# 12. Fase 5 — Construcción de Métricas

A partir de las variables deberán calcularse métricas elementales.

Ejemplos.

- porcentajes;
- tasas;
- frecuencias;
- promedios;
- medianas;
- distribuciones;
- tendencias.

Todas deberán registrarse.

---

# 13. Fase 6 — Construcción de Indicadores

Los indicadores oficiales deberán construirse únicamente utilizando métricas previamente calculadas.

Nunca utilizarán directamente la evidencia.

---

# 14. Fase 7 — Construcción de Índices

Los índices compuestos deberán calcularse únicamente utilizando indicadores oficiales.

Nunca utilizarán variables directamente.

---

# 15. Fase 8 — Validación Final

Antes de persistir resultados deberán verificarse.

- consistencia matemática;
- coherencia metodológica;
- cobertura mínima;
- ausencia de valores imposibles;
- integridad de referencias.

---

# 16. Persistencia

Una vez aprobada la validación.

El Pipeline escribirá.

analytics.db

Posteriormente generará.

dashboard_snapshot.json

Nunca en orden inverso.

---

# 17. Pipeline Incremental

El Pipeline deberá soportar procesamiento incremental.

Cuando ingresen nuevos datos.

No será necesario recalcular información histórica que permanezca inalterada.

Únicamente deberán recalcularse los indicadores afectados por la nueva evidencia.

---

# 18. Recalculo Histórico

El sistema deberá permitir un recálculo completo.

Este proceso reconstruirá analytics.db desde cero utilizando únicamente las bases fuente.

El resultado deberá ser idéntico para una misma versión metodológica.

---

# 19. Auditoría

Toda ejecución deberá generar un registro de auditoría.

Como mínimo.

- fecha;
- hora;
- duración;
- versión metodológica;
- versión del pipeline;
- registros procesados;
- registros descartados;
- advertencias;
- errores.

---

# 20. Versionado

Cada ejecución deberá poseer un identificador único.

Ejemplo.

PIPELINE_RUN_ID

Este identificador acompañará todos los indicadores generados.

---

# 21. Recuperación

Si ocurre una falla.

El Pipeline deberá.

- cancelar la publicación;
- conservar la evidencia;
- conservar los cálculos previos;
- registrar el error;
- permitir reanudación.

Nunca dejar resultados parciales publicados.

---

# 22. Idempotencia

Ejecutar el Pipeline múltiples veces utilizando exactamente la misma evidencia deberá producir exactamente el mismo resultado.

Esta propiedad es obligatoria.

---

# 23. Atomicidad

La publicación será atómica.

dashboard_snapshot.json nunca podrá quedar parcialmente escrito.

analytics.db nunca podrá quedar parcialmente actualizado.

---

# 24. Rendimiento

La velocidad de ejecución nunca tendrá prioridad sobre.

- consistencia;
- reproducibilidad;
- auditabilidad.

La optimización nunca podrá modificar resultados.

---

# 25. Registro de Cambios

Toda modificación producida por el Pipeline deberá poder responder.

- qué cambió;
- por qué cambió;
- cuándo cambió;
- qué evidencia provocó el cambio;
- qué indicadores fueron afectados.

---

# 26. Compatibilidad

El Pipeline deberá permitir incorporar nuevas plataformas sin modificar las etapas existentes.

Las nuevas plataformas únicamente deberán implementar.

- captura;
- extracción;
- normalización.

El resto del Pipeline permanecerá inalterado.

---

# 27. Restricciones

El Pipeline no podrá.

- modificar evidencia;
- ejecutar lógica del Dashboard;
- generar narrativas;
- consultar prompts;
- utilizar respuestas del LLM como cálculo;
- alterar manualmente indicadores.

---

# 28. Criterios de Aceptación

El Pipeline será considerado correctamente implementado cuando.

- analytics.db pueda eliminarse y reconstruirse completamente;
- dashboard_snapshot.json pueda regenerarse automáticamente;
- el mismo conjunto de datos produzca exactamente los mismos indicadores;
- toda ejecución genere auditoría;
- toda transformación sea trazable;
- ningún cálculo dependa del Dashboard.

---

# 29. Vigencia

Este documento constituye la especificación oficial del Pipeline de MIPA.

Toda implementación futura deberá respetar las reglas aquí establecidas.

---

# Control del Documento

| Campo | Valor |
|--------|-------|
| Documento | 005_PIPELINE.md |
| Estado | Aprobado |
| Versión | 1.0.0 |
| Tipo | Normativo |
| Depende de | 000_PROJECT_CHARTER.md, 001_FOUNDATION.md, 002_ARCHITECTURE.md, 003_DATA_MODEL.md, 004_ANALYTICAL_MODEL.md |
| Referenciado por | 006_EVIDENCE_MODEL.md, 007_METRIC_CATALOG.md, 008_NARRATIVE_MODEL.md |
| Última actualización | Baseline MIPA 1.0 |