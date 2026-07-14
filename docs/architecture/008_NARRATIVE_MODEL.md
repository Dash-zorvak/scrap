# MIPA — Motor de Inteligencia Política Auditada
## NARRATIVE_MODEL
**Documento:** 008_NARRATIVE_MODEL.md  
**Estado:** APROBADO (Baseline)  
**Versión metodológica:** MIPA 1.0.0  
**Clasificación:** Normativo (Obligatorio)

---

# 1. Propósito

Este documento define el Modelo Narrativo Oficial de MIPA.

El Modelo Narrativo transforma indicadores previamente calculados en explicaciones ejecutivas verificables.

Su función no consiste en interpretar libremente los datos, sino en comunicar de manera objetiva, transparente y auditada lo que muestran los indicadores oficiales.

---

# 2. Objetivos

Toda narrativa deberá cumplir simultáneamente los siguientes objetivos.

- explicar;
- justificar;
- demostrar;
- contextualizar;
- documentar.

Nunca persuadir.

Nunca exagerar.

Nunca especular.

---

# 3. Principios

## NAR-001

Toda afirmación deberá estar respaldada por evidencia verificable.

---

## NAR-002

Toda afirmación deberá poder reconstruirse matemáticamente.

---

## NAR-003

La narrativa nunca modificará los resultados analíticos.

---

## NAR-004

La narrativa nunca realizará inferencias políticas.

---

## NAR-005

Toda conclusión deberá derivarse únicamente de indicadores oficiales.

---

# 4. Entradas

El Modelo Narrativo únicamente podrá consumir.

- indicadores oficiales;
- métricas oficiales;
- índices oficiales;
- referencias de evidencia;
- metadatos del Pipeline.

No podrá consumir.

- comentarios sin procesar;
- prompts;
- respuestas anteriores del LLM;
- dashboard;
- opiniones humanas.

---

# 5. Salidas

El Modelo Narrativo produce únicamente.

- narrativas ejecutivas;
- memorandos;
- resúmenes;
- explicaciones metodológicas.

Nunca produce indicadores.

---

# 6. Arquitectura

La construcción narrativa seguirá el siguiente flujo.

```
Indicadores

↓

Verificación

↓

Selección de Evidencia

↓

Explicación

↓

Conclusión

↓

Referencias
```

---

# 7. Regla Fundamental

Toda narrativa responderá obligatoriamente.

1. ¿Qué ocurrió?

2. ¿Cómo se sabe?

3. ¿Con qué evidencia?

4. ¿Qué significa exactamente?

5. ¿Qué no significa?

---

# 8. Estructura Oficial

Toda narrativa deberá seguir el mismo orden.

## Paso 1

Presentación objetiva del dato.

---

## Paso 2

Explicación matemática.

---

## Paso 3

Presentación de evidencia.

---

## Paso 4

Limitaciones.

---

## Paso 5

Conclusión.

No podrá alterarse este orden.

---

# 9. Regla de Objetividad

Las narrativas deberán describir hechos.

Nunca calificaciones.

Ejemplo correcto.

> Durante el período analizado se registraron 3,842 comentarios.

Ejemplo incorrecto.

> La conversación fue excelente.

---

# 10. Regla de las Cifras

Toda cifra utilizada deberá poder rastrearse hasta.

- publicaciones;
- comentarios;
- reacciones;
- indicadores.

Nunca aparecerán cifras sin origen.

---

# 11. Regla Matemática

Cuando una conclusión dependa de un cálculo.

La narrativa deberá mostrar la operación utilizada.

Ejemplo.

```
44,700 representa el 5%.

44,700 ÷ 0.05

=

894,000 impresiones estimadas.
```

Las operaciones no deberán ocultarse.

---

# 12. Regla de Evidencia

Toda afirmación relevante deberá acompañarse de evidencia verificable.

Como mínimo.

- URL;
- plataforma;
- publicación;
- período.

Siempre que exista.

---

# 13. Regla de Referencias

Las referencias deberán corresponder exactamente a la evidencia utilizada.

Nunca se utilizarán referencias genéricas.

Cada enlace deberá permitir verificar el origen del dato.

---

# 14. Regla de Transparencia

Toda narrativa deberá indicar claramente.

- qué mide el indicador;
- qué no mide;
- cuáles son sus limitaciones.

---

# 15. Regla de Limitaciones

Las limitaciones forman parte obligatoria de la narrativa.

Ejemplo.

> Este indicador representa actividad digital observada.

> No constituye una encuesta de opinión.

---

# 16. Regla de Neutralidad

Queda prohibido utilizar.

- excelente;
- desastroso;
- histórico;
- extraordinario;
- impresionante;
- alarmante.

Salvo cuando dichos términos provengan directamente de una clasificación metodológica oficial.

---

# 17. Regla del Pulso IQ

Cuando la narrativa describa el Pulso IQ deberá explicar.

- qué variables participaron;
- cómo fueron ponderadas;
- cuál fue el período;
- qué plataformas fueron consideradas;
- qué evidencia respalda el cálculo.

Nunca deberá presentarse únicamente el valor final.

---

# 18. Regla de Popularidad Digital

La Popularidad Digital deberá describirse únicamente como actividad digital observable.

Nunca como.

- intención de voto;
- aprobación electoral;
- resultado electoral futuro.

---

# 19. Regla de Riesgo

Cuando exista un indicador de riesgo.

La narrativa deberá explicar.

- origen del riesgo;
- evidencia;
- velocidad;
- persistencia;
- alcance.

Nunca únicamente el nivel.

---

# 20. Regla del Veredicto

Toda narrativa finalizará con un veredicto explícito.

Formato.

```
Conclusión:
```

El veredicto deberá derivarse únicamente de los indicadores previamente explicados.

Nunca aparecerá una conclusión nueva.

---

# 21. Referencias

Toda narrativa deberá incluir.

- publicaciones utilizadas;
- enlaces originales;
- plataformas;
- período;
- cobertura.

---

# 22. Restricciones

Queda prohibido.

- inventar explicaciones;
- inventar evidencia;
- exagerar resultados;
- utilizar opiniones;
- utilizar adjetivos sin respaldo;
- ocultar limitaciones;
- ocultar operaciones matemáticas.

---

# 23. Validación

Antes de publicarse.

Toda narrativa deberá superar.

- validación metodológica;
- validación matemática;
- validación de referencias;
- validación de trazabilidad.

---

# 24. Criterios de Aceptación

El Modelo Narrativo será considerado correctamente implementado cuando.

- toda afirmación posea evidencia;
- toda cifra pueda verificarse;
- toda operación matemática pueda reconstruirse;
- toda conclusión derive de indicadores oficiales;
- toda narrativa indique claramente qué mide y qué no mide.

---

# 25. Vigencia

Este documento constituye la especificación oficial del Modelo Narrativo de MIPA.

Toda narrativa generada por el sistema deberá respetar estas reglas.

---

# Control del Documento

| Campo | Valor |
|--------|-------|
| Documento | 008_NARRATIVE_MODEL.md |
| Estado | Aprobado |
| Versión | 1.0.0 |
| Tipo | Normativo |
| Depende de | 000_PROJECT_CHARTER.md, 001_FOUNDATION.md, 002_ARCHITECTURE.md, 003_DATA_MODEL.md, 004_ANALYTICAL_MODEL.md, 005_PIPELINE.md, 006_EVIDENCE_MODEL.md, 007_METRIC_CATALOG.md |
| Referenciado por | 009_JSON_CONTRACTS.md, 010_PULSO_IQ.md |
| Última actualización | Baseline MIPA 1.0 |