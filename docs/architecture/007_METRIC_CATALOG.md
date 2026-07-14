# MIPA — Motor de Inteligencia Política Auditada
## METRIC_CATALOG
**Documento:** 007_METRIC_CATALOG.md  
**Estado:** APROBADO (Baseline)  
**Versión metodológica:** MIPA 1.0.0  
**Clasificación:** Normativo (Obligatorio)

---

# 1. Propósito

Este documento constituye el Catálogo Oficial de Métricas de MIPA.

Define todas las métricas que el sistema puede calcular, los datos que requieren, su interpretación, sus limitaciones y las reglas metodológicas que regulan su utilización.

Ningún indicador oficial podrá utilizar métricas que no se encuentren documentadas en este catálogo.

---

# 2. Principios

Toda métrica oficial deberá cumplir simultáneamente.

- ser objetiva;
- ser reproducible;
- ser determinista;
- ser verificable;
- ser trazable;
- poseer una fórmula documentada.

---

# 3. Jerarquía

Las métricas se organizan en cinco niveles.

```
Variables

↓

Métricas básicas

↓

Métricas derivadas

↓

Indicadores

↓

Índices compuestos
```

---

# 4. Variables Base

Las siguientes variables constituyen el conjunto mínimo del sistema.

## Publicaciones

Cantidad de publicaciones analizadas.

---

## Comentarios

Cantidad de comentarios analizados.

---

## Reacciones

Cantidad total de reacciones.

---

## Compartidos

Cantidad total de compartidos.

---

## Visualizaciones

Cantidad total de reproducciones.

---

## Seguidores

Cantidad de seguidores de la cuenta analizada.

---

## Emociones

Clasificación emocional aprobada manualmente.

---

## Temas

Clasificación temática aprobada manualmente.

---

## Posturas

Clasificación de apoyo, crítica o neutralidad.

---

# 5. Métricas de Cobertura

## MC-001 Cobertura de Publicaciones

Porcentaje de publicaciones analizadas respecto al universo disponible.

---

## MC-002 Cobertura de Comentarios

Porcentaje de comentarios clasificados respecto al total capturado.

---

## MC-003 Cobertura por Plataforma

Distribución de registros entre plataformas.

---

## MC-004 Cobertura Temporal

Período efectivamente cubierto por la evidencia.

---

# 6. Métricas de Actividad

## MA-001 Frecuencia de Publicación

Publicaciones por unidad de tiempo.

---

## MA-002 Frecuencia de Comentarios

Comentarios por unidad de tiempo.

---

## MA-003 Ritmo Conversacional

Velocidad de generación de conversación.

---

## MA-004 Participación

Promedio de interacción por publicación.

---

# 7. Métricas de Interacción

## MI-001 Reacciones Promedio

Promedio de reacciones por publicación.

---

## MI-002 Comentarios Promedio

Promedio de comentarios por publicación.

---

## MI-003 Compartidos Promedio

Promedio de compartidos por publicación.

---

## MI-004 Engagement Digital

Nivel de interacción obtenido por cada publicación.

La fórmula oficial será documentada en un documento metodológico específico.

---

# 8. Métricas Emocionales

Las emociones provienen exclusivamente del Modelo de Emociones aprobado.

No serán inferidas por el Dashboard.

---

## ME-001 Distribución Emocional

Distribución porcentual de emociones.

---

## ME-002 Intensidad Emocional

Magnitud relativa de las emociones predominantes.

---

## ME-003 Diversidad Emocional

Cantidad de emociones distintas presentes en el período.

---

## ME-004 Polarización Emocional

Grado de concentración entre emociones opuestas.

---

# 9. Métricas Temáticas

## MT-001 Distribución Temática

Participación porcentual de cada tema.

---

## MT-002 Concentración Temática

Nivel de concentración de la conversación.

---

## MT-003 Diversidad Temática

Cantidad efectiva de temas presentes.

---

## MT-004 Emergencia Temática

Velocidad de aparición de nuevos temas.

---

# 10. Métricas de Postura

## MP-001 Distribución de Posturas

Porcentaje de apoyo, crítica y neutralidad.

---

## MP-002 Intensidad Crítica

Magnitud relativa de la conversación crítica.

---

## MP-003 Intensidad de Apoyo

Magnitud relativa de la conversación favorable.

---

## MP-004 Balance Conversacional

Relación matemática entre apoyo y crítica.

---

# 11. Métricas de Riesgo

## MR-001 Riesgo Conversacional

Nivel de riesgo detectado en la conversación pública.

---

## MR-002 Velocidad de Propagación

Rapidez con la que una conversación aumenta su alcance.

---

## MR-003 Persistencia

Tiempo durante el cual un tema permanece activo.

---

## MR-004 Concentración de Riesgo

Porcentaje del riesgo concentrado en pocos temas.

---

# 12. Métricas de Influencia

## MF-001 Influencia por Fuente

Participación relativa de cada fuente.

---

## MF-002 Influencia por Plataforma

Peso relativo de cada plataforma.

---

## MF-003 Concentración de Influencia

Dependencia del debate respecto a pocos actores.

---

# 13. Métricas de Calidad

## MQ-001 Completitud

Porcentaje de datos disponibles.

---

## MQ-002 Consistencia

Nivel de coherencia interna.

---

## MQ-003 Confianza

Grado de confiabilidad del cálculo.

---

## MQ-004 Trazabilidad

Porcentaje de registros con evidencia verificable.

---

# 14. Índices Oficiales

Los índices oficiales combinan múltiples indicadores.

Actualmente el sistema reconoce.

- Pulso IQ
- Riesgo Digital
- Intensidad Conversacional
- Popularidad Digital
- Influencia Digital

Cada uno será documentado en un documento metodológico independiente.

---

# 15. Interpretación

Toda métrica deberá documentar.

- qué mide;
- qué no mide;
- cómo se calcula;
- qué evidencia utiliza;
- cuáles son sus limitaciones.

---

# 16. Limitaciones

Las métricas de MIPA.

No miden.

- intención de voto;
- preferencia electoral;
- aprobación ciudadana fuera del entorno digital;
- opinión de personas que no participan en plataformas analizadas.

Representan únicamente actividad y percepción digital observable.

---

# 17. Evidencia

Toda métrica deberá conservar referencia explícita hacia la evidencia utilizada durante su cálculo.

Ninguna métrica podrá publicarse sin respaldo.

---

# 18. Versionado

Cada métrica deberá registrar.

- versión metodológica;
- versión del algoritmo;
- fecha de cálculo;
- identificador del Pipeline.

---

# 19. Validación

Antes de ser utilizada por un indicador.

Toda métrica deberá superar.

- validación estructural;
- validación matemática;
- validación metodológica;
- validación de trazabilidad.

---

# 20. Restricciones

Queda prohibido.

- modificar métricas manualmente;
- utilizar métricas sin documentación;
- construir índices con métricas experimentales;
- utilizar métricas sin evidencia asociada.

---

# 21. Criterios de Aceptación

El Catálogo de Métricas será considerado correctamente implementado cuando.

- todas las métricas utilizadas por MIPA se encuentren documentadas;
- todas posean definición metodológica;
- todas sean reproducibles;
- todas puedan reconstruirse desde la evidencia;
- todas indiquen claramente qué miden y qué no miden.

---

# 22. Vigencia

Este documento constituye el Catálogo Oficial de Métricas de MIPA.

Toda incorporación de nuevas métricas requerirá una actualización formal de este documento.

---

# Control del Documento

| Campo | Valor |
|--------|-------|
| Documento | 007_METRIC_CATALOG.md |
| Estado | Aprobado |
| Versión | 1.0.0 |
| Tipo | Normativo |
| Depende de | 000_PROJECT_CHARTER.md, 001_FOUNDATION.md, 002_ARCHITECTURE.md, 003_DATA_MODEL.md, 004_ANALYTICAL_MODEL.md, 005_PIPELINE.md, 006_EVIDENCE_MODEL.md |
| Referenciado por | 008_NARRATIVE_MODEL.md, 009_JSON_CONTRACTS.md, 010_PULSO_IQ.md |
| Última actualización | Baseline MIPA 1.0 |