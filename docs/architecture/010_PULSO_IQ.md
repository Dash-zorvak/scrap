# MIPA — Motor de Inteligencia Política Auditada
## PULSO_IQ
**Documento:** 010_PULSO_IQ.md  
**Estado:** APROBADO (Baseline)  
**Versión metodológica:** MIPA 1.0.0  
**Clasificación:** Metodología Oficial (Obligatorio)

---

# 1. Propósito

Este documento define la metodología oficial del indicador **Pulso IQ**.

Pulso IQ constituye el principal indicador compuesto de MIPA.

Su finalidad es medir el estado general de la conversación pública digital alrededor de una institución, organización o figura política utilizando exclusivamente evidencia verificable.

---

# 2. Definición Oficial

Pulso IQ es un índice compuesto que resume la calidad del entorno conversacional digital mediante la integración ponderada de múltiples dimensiones analíticas.

No representa una emoción.

No representa una encuesta.

No representa intención de voto.

No representa aprobación electoral.

Representa exclusivamente el comportamiento observable de la conversación digital.

---

# 3. Objetivo

Responder una única pregunta.

> **¿Cuál es el estado general de la conversación pública digital durante un período determinado?**

---

# 4. Alcance

Pulso IQ integra información proveniente de todas las plataformas soportadas por MIPA.

Actualmente.

- Facebook
- TikTok
- Medios digitales
- Fuentes externas

La incorporación de nuevas plataformas no modifica la metodología.

Únicamente amplía la cobertura.

---

# 5. Escala

El índice utiliza una escala continua.

| Rango | Interpretación |
|--------|----------------|
| 0 – 20 | Muy desfavorable |
| 21 – 40 | Desfavorable |
| 41 – 60 | Mixto o inestable |
| 61 – 80 | Favorable |
| 81 – 100 | Muy favorable |

Los rangos describen únicamente el comportamiento digital observado.

No representan valoración política.

---

# 6. Componentes Oficiales

Pulso IQ está compuesto por cinco dimensiones.

## IQ-01 Conversación

Mide la intensidad y volumen de participación.

---

## IQ-02 Interacción

Mide el nivel de interacción generado.

---

## IQ-03 Percepción

Mide la distribución de emociones y posturas observadas.

---

## IQ-04 Riesgo

Mide el nivel de fricción y riesgo conversacional.

Esta dimensión actúa como penalización.

---

## IQ-05 Diversidad

Mide la amplitud y distribución de la conversación entre temas, públicos y plataformas.

---

# 7. Variables

Cada dimensión utiliza únicamente indicadores previamente calculados.

Nunca utiliza evidencia directamente.

---

# 8. Fórmula General

La forma general del índice es.

```
Pulso IQ

=

Σ (Indicador Normalizado × Peso)
```

Todos los indicadores deberán encontrarse previamente normalizados.

---

# 9. Ponderaciones

Las ponderaciones oficiales deberán documentarse explícitamente.

Ningún peso podrá modificarse sin actualizar la versión metodológica.

---

# 10. Normalización

Todos los indicadores deberán convertirse previamente a una escala común.

La metodología de normalización deberá ser consistente para todas las ejecuciones.

---

# 11. Evidencia

Todo valor de Pulso IQ deberá conservar.

- publicaciones utilizadas;
- comentarios utilizados;
- plataformas;
- período;
- cobertura;
- identificador de ejecución.

---

# 12. Explicabilidad

Todo resultado deberá poder responder.

- qué indicadores participaron;
- cuánto aportó cada uno;
- cuál fue la penalización por riesgo;
- cuál fue el período analizado;
- cuál fue la cobertura.

---

# 13. Interpretación

Pulso IQ mide.

- percepción digital;
- intensidad conversacional;
- interacción observable;
- comportamiento colectivo en plataformas digitales.

No mide.

- intención de voto;
- aprobación electoral;
- satisfacción ciudadana total;
- opinión fuera del entorno digital.

---

# 14. Limitaciones

Pulso IQ depende de la evidencia disponible.

Si una plataforma no fue capturada.

Su comportamiento no formará parte del índice.

El índice siempre representa únicamente la cobertura efectivamente analizada.

---

# 15. Transparencia

El Dashboard deberá mostrar.

- valor del índice;
- componentes;
- pesos;
- evidencia utilizada;
- referencias;
- limitaciones.

Nunca únicamente el valor numérico.

---

# 16. Referencias

Cada resultado deberá permitir acceder a.

- publicaciones originales;
- enlaces;
- plataformas;
- comentarios relevantes;
- período analizado.

El usuario deberá poder verificar cualquier resultado.

---

# 17. Versionado

Cada cálculo deberá registrar.

- versión metodológica;
- versión del algoritmo;
- fecha;
- identificador del Pipeline.

---

# 18. Validación

Antes de publicarse.

Pulso IQ deberá superar.

- validación matemática;
- validación metodológica;
- validación de cobertura;
- validación de trazabilidad.

---

# 19. Restricciones

Queda prohibido.

- modificar manualmente el valor del índice;
- ocultar componentes;
- ocultar ponderaciones;
- ocultar limitaciones;
- utilizar datos sin evidencia.

---

# 20. Criterios de Aceptación

Pulso IQ será considerado correctamente implementado cuando.

- pueda reconstruirse completamente desde la evidencia;
- todos sus componentes estén documentados;
- las ponderaciones sean públicas;
- la metodología sea reproducible;
- el Dashboard explique claramente qué mide y qué no mide.

---

# 21. Vigencia

Este documento constituye la especificación oficial del indicador Pulso IQ.

Toda modificación requerirá una nueva versión metodológica.

---

# Control del Documento

| Campo | Valor |
|--------|-------|
| Documento | 010_PULSO_IQ.md |
| Estado | Aprobado |
| Versión | 1.0.0 |
| Tipo | Metodología Oficial |
| Depende de | 000_PROJECT_CHARTER.md, 001_FOUNDATION.md, 002_ARCHITECTURE.md, 003_DATA_MODEL.md, 004_ANALYTICAL_MODEL.md, 005_PIPELINE.md, 006_EVIDENCE_MODEL.md, 007_METRIC_CATALOG.md, 008_NARRATIVE_MODEL.md, 009_JSON_CONTRACTS.md |
| Referenciado por | 011_POPULARIDAD_DIGITAL.md, 020_FORMULAS.md |
| Última actualización | Baseline MIPA 1.0 |