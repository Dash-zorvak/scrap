# Guía del Analista — Generación de `data/analysis.json`

Este documento define las reglas que **debe** seguir todo proceso (LLM, script, manual) que genere o modifique `data/analysis.json`. El objetivo es garantizar consistencia, trazabilidad y que el panel renderice datos correctos sin depender de lógica correctiva en runtime.

> El panel (`dashboard/app.py`) lee este JSON sin calcular, inferir ni corregir nada. Lo que llegue aquí es lo que se muestra.

---

## Reglas Generales

### RG-1: Jerga técnica solo en `formula_usada`

Los campos `narrativa` / `explicacion_simple` **nunca** deben contener siglas técnicas como `HHI`, `NSI`, `IR`, `PI`, `ER`, etc. Esos nombres van **únicamente** en `formula_usada`.

**Correcto:**  
`"narrativa": "La conversación está distribuida entre 8 temas sin que ninguno domine (índice de concentración de 0.19 sobre 1)."`  
`"formula_usada": "HHI = Σ(share_i²) donde share_i = n_tema_i / total_temas"`

**Incorrecto:**  
`"narrativa": "El HHI es 0.19, lo que indica fragmentación."`

---

### RG-2: Narrativas basadas solo en datos del período analizado

Ninguna narrativa puede mencionar eventos, publicaciones o métricas que **no ocurrieron dentro de la semana/periodo analizado**.

**Ejemplo real detectado (INTENSIDAD — INCORRECTO):**  
> "El pico ocurrió el 23 de junio con 2,232 interacciones —impulsado por el post viral del «habitante de Altos del Palmar» (105 comentarios, 433 likes) y el reconocimiento al Club FAS."

El reconocimiento al Club FAS **no ocurrió en la semana analizada**; pertenece al archivo antiguo "medalla del alcalde". La narrativa debe describir solo los eventos del 21–26 de junio.

---

### RG-3: Prohibido usar "censura" o "autocensura"

**Ejemplo real detectado (POLARIZACIÓN — INCORRECTO):**  
> "La audiencia no está polarizada: 126 comentarios favorables versus solo 5 críticos explícitos. Sin embargo, esto refleja en parte **autocensura** —la crítica real se expresa más en reacciones (hahas/sads) que en texto."

Debe decir:  
> "Sin embargo, esto refleja una **limitación metodológica** de medir solo texto público —la crítica real se expresa más en reacciones (hahas/sads) que en comentarios de texto."

---

### RG-4: Engagement ≠ Impresiones

No mezclar estos conceptos. *Engagement* = reacciones + comentarios + compartidos. *Impresiones* = veces que el contenido fue visto. No usar "engagement" cuando se habla de alcance/impresiones ni viceversa.

---

### RG-5: Cada afirmación específica debe traer su enlace real

El campo `enlaces_referencia` debe contener **la lista completa** de URLs de los posts que respaldan las afirmaciones de esa sección. No una muestra ni un subconjunto. Si la narrativa dice "3 posts sobre política antisoborno", deben aparecer los 3 enlaces.

---

## Bloque I — Pulso General

| Sección | Reglas |
|---------|--------|
| Clima Narrativo | `narrativa` sigue exactamente la descripción del campo `narrativa` en `data/analysis_schema.json` (bloque1.clima_narrativo). No dupliques la plantilla aquí para evitar que ambos textos queden desincronizados. `enlaces_referencia` debe incluir los posts representativos del período. |

---

## Bloque II — Segmentación de Audiencia

### Voces de Influencia — Corrección de cálculo

Cada entrada de `voces_influencia` debe tener **todos** estos campos derivados de la misma fuente de datos, sin inconsistencias matemáticas:

```json
{
  "pagina": "Alcaldía de Santa Ana",
  "publicaciones": 37,
  "engagement": 2997,
  "alcance_estimado": 15000,
  "reacciones_totales": 1800,
  "comentarios_totales": 400,
  "compartidos_totales": 797
}
```

**Ejemplo real detectado (INCORRECTO):**  
`"Alcaldía de Santa Ana"` aparece con 37 publicaciones y 2,997 de engagement pero **0 en alcance, 0 reacciones, 0 comentarios y 0 compartidos**. Esto es matemáticamente imposible: engagement = reacciones + comentarios + compartidos. Si engagement > 0, los submétricas no pueden ser 0.

---

## Bloque III — Riesgo y Autenticidad

### Nivel de Alerta — `alertas_cambridge`

Cada alerta debe incluir los enlaces de los posts que la justifican. No basta con el número.

**Ejemplo real detectado (INCORRECTO):**  
```json
{
  "tipo": "REACCION_NEGATIVA_ALTA",
  "detalle": "El 23.5% de las reacciones son hahas/sads/angrys. En 3 posts sobre política antisoborno y reconocimientos institucionales, los hahas superan el 40%..."
}
```
Faltan `enlaces_referencia` con las URLs de esos 3 posts.

**Correcto:**  
```json
{
  "tipo": "REACCION_NEGATIVA_ALTA",
  "detalle": "...",
  "enlaces_referencia": [
    "https://facebook.com/.../post1",
    "https://facebook.com/.../post2",
    "https://facebook.com/.../post3"
  ]
}
```

---

### Velocidad de Propagación — `narrativa`

La narrativa debe nombrar los **temas específicos** que aceleran o desaceleran la conversación, no quedarse en descripciones genéricas.

**Incorrecto:** "La curva muestra un pico claro el 23 de junio seguido de descenso sostenido."  
**Correcto:** "La conversación desacelera por la caída de los temas de obras públicas (−45%) y política institucional (−30%), mientras que el tema de drones agrícolas acelera (+100%)."

---

### Puntos de Fricción

Nunca dejar `emocion_dominante` vacío ni `reacciones_enojo` en 0 si el punto ya fue clasificado como fricción activa (tiene `n_negativos > 0`).

**Incorrecto:**  
```json
{
  "tema": "Promesas incumplidas",
  "n_negativos": 4,
  "emocion_dominante": "",
  "reacciones_enojo": 0
}
```

**Correcto:**  
```json
{
  "tema": "Promesas incumplidas",
  "n_negativos": 4,
  "emocion_dominante": "enojo",
  "reacciones_enojo": 12
}
```

---

## Bloque IV — Memorándum Estratégico

Cada una de las 8 secciones narrativas de Bloque IV (`eco_historico`, `leccion_aprendida`, `brecha_percepcion_realidad`, `contexto_no_visible`, `correlacion_contenido_reaccion`, `comparativa_sectorial`, `proyeccion_escenario`, `recomendacion_estrategica`) debe cumplir:

1. **Formato:** `{"narrativa": "", "enlaces_referencia": []}` (dict, no string plano).
2. **La narrativa debe integrar los números/porcentajes/fórmulas reales dentro de la prosa**, no leer como suposición genérica. Cada afirmación cuantitativa debe poder rastrearse a un dato del período.
3. **`enlaces_referencia` completo:** lista de todas las URLs citadas en la narrativa, no una muestra.

### Errores reales detectados (a corregir):

| Sección | Problema |
|---------|----------|
| **Eco Histórico** | Menciona el "reconocimiento del Club FAS" del archivo viejo. Debe reformularse solo con datos de la semana analizada. |
| **Lección Aprendida** | No cita de dónde sale cada número (105 comentarios, 38–42% hahas, etc.). Debe referenciar los posts específicos. |
| **Brecha Percepción-Realidad** | Usa cifras (30% favorable, 1.2% crítico, 23.5% reacciones negativas, 40%+ hahas) sin indicar qué posts generan cada cifra. |
| **Contexto No Visible** | Menciona "temporada lluviosa", "fallecimiento sargento PNC", "elecciones municipales" como afirmaciones sin enlaces. |
| **Correlación Contenido-Reacción** | Compara promedios (13.3 vs 3.7 comentarios por post) sin citar los conjuntos de posts de cada cuenta. |

---

## Plantilla obligatoria de `narrativa` (Clima Narrativo)

Sin relleno ni adjetivos sueltos («moderado», «cierto margen para la crítica»,
«señales mixtas») que no estén anclados a una cifra o a un tema concreto.
Estructura fija, en este orden:

1. Cifras crudas: total de comentarios, % favorable/neutral/crítico y el
   índice de sentimiento neto ya calculado sobre 100 (nunca la palabra "NSI"
   ni la fórmula).
2. El dato que más importa: la comparación exacta contra el período anterior
   en puntos (ej. "+3.2 pts"), nunca una palabra vaga como "mejorando". Si no
   hay período previo, decirlo explícitamente.
3. El ancla concreta: el tema real (no genérico) que concentra la crítica o
   el apoyo, con su peso numérico (conteo o %). Si no hay dato de tema, decir
   "no hay datos suficientes para atribuir un tema concreto" — nunca inventarlo.
4. Conclusión: una frase final que empiece con "Conclusión:" y diga qué
   significa el número para la gestión — un veredicto, no una repetición de
   las cifras ya dichas.
5. Cierre obligatorio: después de la frase de Conclusión, en una línea nueva,
   agregar "= NOMBRE CONTUNDENTE EN MAYÚSCULAS" — un título corto (2 a 5
   palabras) que resuma el veredicto como una etiqueta, no una oración.
   Debe derivarse del dato/ancla ya mencionado en esta misma narrativa, nunca
   un nombre genérico tipo "= RESULTADO POSITIVO".

Plantilla:
"De {n_total_comentarios} comentarios del período, {pct_favorable}% son
favorables, {pct_neutral}% neutros y {pct_critico}% críticos — saldo neto de
{NSI} puntos sobre 100 ({tendencia en puntos exactos} respecto al período
anterior). {Tema concreto} concentra {peso} de los comentarios
{favorables/críticos}. Conclusión: {veredicto directo, sin relleno}.
= {NOMBRE CONTUNDENTE}"

Ejemplo:
"De 430 comentarios del período, 37% son favorables, 33% neutros y 29%
críticos — saldo neto de 8.0 puntos sobre 100 (+3.2 pts respecto al período
anterior). «Obras públicas» concentra el 61% de los comentarios críticos.
Conclusión: el saldo es positivo pero depende de un solo tema — si la crítica
en obras públicas escala, el balance se revierte.
= OBRAS PÚBLICAS DOMINA LA CRÍTICA"

## Validación rápida pre-entrega

Antes de guardar el JSON, verifique:

- [ ] `narrativa` de Clima Narrativo tiene una frase "Conclusión:" explícita y ningún adjetivo sin cifra o tema detrás.
- [ ] Ninguna `narrativa` contiene HHI, NSI, IR, PI, ER.
- [ ] Ninguna `narrativa` contiene "censura" o "autocensura".
- [ ] Engagement = reacciones + comentarios + compartidos (consistencia).
- [ ] Voces de Influencia: si `engagement > 0`, sus submétricas no son 0.
- [ ] Alertas Cambridge: cada `tipo` incluye `enlaces_referencia` si menciona posts específicos.
- [ ] Puntos de Fricción: si `n_negativos > 0`, `emocion_dominante` no está vacío.
- [ ] Bloque IV: cada sección es `{"narrativa": "...", "enlaces_referencia": [...]}`.
- [ ] Bloque IV: cada `enlaces_referencia` contiene las URLs reales, no está vacío si la narrativa hace afirmaciones específicas.
- [ ] Ninguna afirmación se basa en datos fuera del período del `meta.periodo`.
- [ ] Toda narrativa termina con una línea "= NOMBRE CONTUNDENTE" derivada del ancla mencionada.
