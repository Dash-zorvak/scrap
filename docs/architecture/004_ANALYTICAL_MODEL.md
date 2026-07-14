# MIPA — Motor de Inteligencia Política Auditada
## ANALYTICAL_MODEL
**Documento:** 004_ANALYTICAL_MODEL.md  
**Estado:** APROBADO (Baseline)  
**Versión metodológica:** MIPA 1.0.0  
**Clasificación:** Normativo (Obligatorio)

---

# 1. Propósito

Este documento define el Modelo Analítico oficial de MIPA.

El Modelo Analítico es el conjunto de reglas, fórmulas, procesos y criterios que permiten transformar evidencia digital validada en indicadores oficiales.

Todo indicador publicado por MIPA deberá ser generado exclusivamente mediante este modelo.

---

# 2. Objetivo

Garantizar que todos los indicadores:

- sean deterministas;
- sean reproducibles;
- sean matemáticamente verificables;
- puedan ser auditados;
- puedan reconstruirse utilizando únicamente la evidencia almacenada.

---

# 3. Alcance

El Modelo Analítico es responsable únicamente de producir información cuantitativa.

No interpreta.

No comunica.

No redacta.

No genera recomendaciones.

---

# 4. Entradas

El Modelo Analítico únicamente podrá recibir información proveniente de:

- facebook.db
- tiktok.db
- externos.db
- analytics.db (datos derivados previamente calculados)

No podrá consumir directamente:

- prompts;
- respuestas de LLM;
- texto generado;
- dashboard;
- archivos JSON de salida.

---

# 5. Salidas

El Modelo Analítico produce exclusivamente:

- métricas;
- indicadores;
- índices;
- distribuciones;
- agregaciones;
- series temporales;
- matrices;
- rankings;
- estados de alerta.

Nunca produce narrativa.

---

# 6. Principios Analíticos

Todo cálculo oficial deberá cumplir simultáneamente.

## MA-001 Determinismo

Mismos datos.

↓

Misma metodología.

↓

Mismo resultado.

---

## MA-002 Independencia

Los cálculos nunca dependerán del Dashboard.

---

## MA-003 Auditabilidad

Todo cálculo deberá poder reconstruirse paso a paso.

---

## MA-004 Explicabilidad

Todo indicador deberá explicar exactamente cómo fue calculado.

---

## MA-005 Versionado

Todo cálculo deberá registrar la versión metodológica utilizada.

---

## MA-006 Trazabilidad

Todo indicador deberá conocer exactamente qué evidencia participó en su construcción.

---

# 7. Arquitectura del Modelo

El modelo se divide en cinco niveles.

```
Evidencia

↓

Variables

↓

Métricas

↓

Indicadores

↓

Índices Compuestos
```

Cada nivel depende exclusivamente del anterior.

---

# 8. Variables

Las variables constituyen la unidad básica del modelo.

Ejemplos.

- número de comentarios;
- número de reacciones;
- número de publicaciones;
- compartidos;
- visualizaciones;
- fecha;
- plataforma;
- emoción;
- tema;
- postura.

Las variables nunca contienen interpretación.

---

# 9. Métricas

Las métricas representan operaciones matemáticas sobre variables.

Ejemplos.

- promedio;
- mediana;
- frecuencia;
- desviación;
- crecimiento;
- tasa;
- porcentaje;
- variación.

Las métricas todavía no representan indicadores oficiales.

---

# 10. Indicadores

Un indicador representa una medición oficial.

Todo indicador deberá poseer.

- nombre;
- definición;
- fórmula;
- variables utilizadas;
- interpretación;
- limitaciones;
- evidencia asociada;
- versión metodológica.

---

# 11. Índices Compuestos

Un índice compuesto resulta de combinar múltiples indicadores.

Ejemplos.

- Pulso IQ;
- Riesgo Digital;
- Intensidad Conversacional.

Todo índice deberá documentar.

- componentes;
- pesos;
- fórmula;
- normalización;
- rango de salida.

---

# 12. Clasificación de Indicadores

Los indicadores se clasifican en cinco categorías.

## Volumen

Miden cantidad.

---

## Distribución

Miden composición.

---

## Intensidad

Miden magnitud.

---

## Tendencia

Miden evolución temporal.

---

## Compuestos

Integran múltiples indicadores.

---

# 13. Pipeline Analítico

Todo cálculo recorrerá obligatoriamente las siguientes etapas.

```
Validación

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

Validación

↓

Persistencia
```

---

# 14. Reglas Matemáticas

Toda fórmula oficial deberá ser.

- explícita;
- determinista;
- documentada;
- verificable;
- reproducible.

No se aceptarán fórmulas implícitas.

---

# 15. Normalización

Cuando un indicador combine múltiples escalas, todas deberán normalizarse previamente.

La metodología de normalización deberá documentarse.

Nunca podrá asumirse.

---

# 16. Ponderaciones

Toda ponderación deberá cumplir.

- justificación metodológica;
- documentación;
- estabilidad;
- versionado.

No existirán pesos arbitrarios.

---

# 17. Evidencia Mínima

Todo indicador deberá conservar.

- registros utilizados;
- cantidad de registros;
- período;
- cobertura;
- filtros aplicados.

---

# 18. Calidad del Indicador

Todo indicador deberá calcular.

- cobertura;
- completitud;
- consistencia;
- confianza.

La confianza forma parte del indicador.

No constituye narrativa.

---

# 19. Datos Faltantes

Cuando exista información incompleta.

El sistema deberá.

- identificarla;
- registrarla;
- excluirla o tratarla según metodología;
- documentar el tratamiento aplicado.

Nunca podrá ignorarse silenciosamente.

---

# 20. Valores Atípicos

Los valores atípicos deberán.

- detectarse;
- registrarse;
- conservarse;
- documentar el tratamiento aplicado.

Nunca podrán eliminarse sin trazabilidad.

---

# 21. Períodos

Todo cálculo deberá declarar explícitamente.

- fecha inicial;
- fecha final;
- zona horaria;
- criterio temporal.

---

# 22. Versionado

Cada indicador deberá registrar.

- versión metodológica;
- versión del algoritmo;
- versión del pipeline;
- fecha de cálculo.

---

# 23. Validación

Antes de publicarse.

Todo indicador deberá superar.

- validación estructural;
- validación matemática;
- validación metodológica;
- validación de evidencia.

---

# 24. Indicadores Experimentales

Los indicadores experimentales.

- no serán oficiales;
- no afectarán índices oficiales;
- deberán identificarse claramente;
- requerirán validación antes de incorporarse.

---

# 25. Prohibiciones

Queda prohibido.

- utilizar resultados del Dashboard como entrada;
- utilizar texto narrativo como variable;
- utilizar respuestas de LLM como indicador;
- modificar evidencia para mejorar resultados;
- ajustar manualmente métricas oficiales.

---

# 26. Criterios de Aceptación

El Modelo Analítico será considerado correctamente implementado cuando.

- todos los indicadores puedan recalcularse;
- todas las fórmulas estén documentadas;
- todas las variables sean identificables;
- toda evidencia pueda reconstruirse;
- el mismo conjunto de datos produzca exactamente el mismo resultado.

---

# 27. Vigencia

Este documento constituye la especificación oficial del Modelo Analítico de MIPA.

Toda implementación deberá respetar las reglas aquí descritas.

---

# Control del Documento

| Campo | Valor |
|--------|-------|
| Documento | 004_ANALYTICAL_MODEL.md |
| Estado | Aprobado |
| Versión | 1.0.0 |
| Tipo | Normativo |
| Depende de | 000_PROJECT_CHARTER.md, 001_FOUNDATION.md, 002_ARCHITECTURE.md, 003_DATA_MODEL.md |
| Referenciado por | 005_PIPELINE.md, 006_EVIDENCE_MODEL.md, 007_METRIC_CATALOG.md |
| Última actualización | Baseline MIPA 1.0 |