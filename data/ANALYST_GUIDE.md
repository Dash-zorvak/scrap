# Guía del Analista — Generación de `data/analysis.json`

> **DEPRECADO (Block 25):** Esta guía describía el proceso manual/LLM externo
> para generar `data/analysis.json`. Ha sido reemplazada por el pipeline
> automatizado `python -m analytics.cli generar`, que es el único punto de
> escritura soportado. Este documento se conserva como referencia histórica de
> las reglas de negocio que el pipeline ahora implementa en código.

Este documento define las reglas que **debe** seguir todo proceso (LLM, script, manual) que genere o modifique `data/analysis.json`. El objetivo es garantizar consistencia, trazabilidad y que el panel renderice datos correctos sin depender de lógica correctiva en runtime.

> El panel (`dashboard/app.py`) lee este JSON sin calcular, inferir ni corregir nada. Lo que llegue aquí es lo que se muestra.

---

## Reglas Generales

### RG-0: Sentimiento por reglas léxicas (sin IA)

El análisis de sentimiento en MIPA se ejecuta exclusivamente mediante **reglas léxicas deterministas**. No se utilizan modelos entrenados (BERT, RoBERTa, u otros), ni llamadas a APIs de inferencia.

**Componentes del método:**

1. **Léxico**: diccionario de datos plano con ~80 palabras positivas y ~80 negativas en español, tuneado para discurso municipal/público. Ver `analytics/sentiment.py` → `POSITIVE_WORDS` / `NEGATIVE_WORDS`.

2. **Negación**: palabras "no", "nunca", "jamás", "tampoco", "ni" invierten la polaridad de la palabra positiva/negativa que aparezca dentro de las 3 palabras siguientes.

3. **Clasificación a 5 niveles**:
   - Sin coincidencias → `neutral`
   - Mayoría clara de un signo → `positivo` / `negativo`
   - Proporción ≥ 0.8 en un lado → `muy_positivo` / `muy_negativo`

4. **Escala numérica** (`SENTIMENT_ORDER`):
   - `muy_positivo = 2`, `positivo = 1`, `neutral = 0`, `negativo = -1`, `muy_negativo = -2`

5. **NSI (Net Sentiment Index)**: `(positivos - negativos) / total * 100` — se usa en `clima_narrativo` y narrativas.

**Nunca** mencionar en las narrativas que el sentimiento fue calculado por un modelo de IA. El método es completamente explicable y auditado via léxico + reglas.

---

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

### RG-6: Catálogo abierto de emociones y temas

El catálogo de emociones (`EMOCIONES`) y temas (`TEMAS`) en `dashboard/tema_taxonomia.py` es un **punto de partida, no un techo**. Las familias (joy, trust, fear, surprise, sadness, disgust, anger, anticipation, diada, civica) y los temas englobantes están fijos — son la estructura. Las hojas dentro de cada familia dejan de estar cerradas.

**Regla para el analista:** cuando el texto real no calce en ninguna emoción o tema existente, **debe proponer la hoja nueva** en vez de forzarlo a la más parecida. El sistema registra automáticamente la propuesta en `dashboard/taxonomias_pendientes.json` para revisión. No se descarta nada, no se fuerza a un valor por defecto.

**Cómo proponer:**
- Emociones: usar la clave descriptiva en minúsculas, sin espacios (ej. `indignacion_comunitaria`). El sistema asigna automáticamente la familia "civica" si no hay señal clara; el analista puede sugerir la familia más cercana.
- Temas: usar la clave descriptiva (ej. `infraestructura_deportiva`). Se registra como propuesta pendiente.

**Prohibido:** asignar una emoción o tema a `no_aplica` o `calma` solo porque no existe en el catálogo actual. Eso oculta información real.

---

### RG-7: Catálogo abierto de intención comunicativa

El catálogo de intención comunicativa (`INTENCIONES`) en `dashboard/intencion_taxonomia.py` es un **punto de partida, no un techo**. Las 12 familias (informacion, evaluacion, solicitud, fiscalizacion, participacion, deliberacion, expresion_social, movilizacion, humor, identidad, interaccion, enganoso) están fijas — son la estructura. Las hojas (intenciones específicas) dentro de cada familia son abiertas.

**Regla para el analista:** cuando el texto real no calce en ninguna intención existente, **debe proponer la hoja nueva** en vez de forzarlo a la más parecida. El sistema registra automáticamente la propuesta en `dashboard/taxonomias_pendientes.json` para revisión. No se descarta nada, no se fuerza a un valor por defecto.

**Clasificación dual (A01 §11):** cada comentario puede tener una `intencion_principal` (una sola) y `intenciones_secundarias` (lista de atéste 3). La intención principal es la que define el propósito comunicativo dominante; las secundarias capturan matices (ej. un comentario que critica Y propone solución tiene intención principal "evaluacion" y secundaria "solicitud").

**Cómo proponer:**
- Intenciones: usar la clave descriptiva en minúsculas, sin espacios (ej. `exigir_transparencia`). Se registra como propuesta pendiente con su familia asociada.
- Si la familia no es obvia, usar `informacion` como familia por defecto (la más genérica del catálogo).

**Prohibido:** asignar una intención a `no_aplica` solo porque no existe en el catálogo actual. Eso oculta información real sobre qué está haciendo el ciudadano con su comunicación.

---

### RG-8: Emoción por reglas léxicas (sin IA)

La clasificación de emoción en MIPA se ejecuta mediante **reglas léxicas deterministas**. No se utilizan modelos de inferencia.

**Componentes del método (`analytics/emotion.py`):**

1. **Léxico semilla**: ~80 palabras/frases por una de las 31 categorías canónicas de Plutchik (ver `EMOTION_LEXICON`). Cada emoción tiene su propio set de semillas.

2. **Coincidencia por tokens y frases**: tokens individuales se buscan en el set normalizado; frases multi-palabra se buscan por substring en el texto normalizado.

3. **Intensificadores**: palabras ("muy", "totalmente", "extremadamente"), mayúsculas de 3+ letras y signos de exclamación repetidos (`!!`) empujan la intensidad de leve → media → intensa dentro de la misma familia.

4. **Regla "me divierte"**: en publicaciones oficiales, marcadores de risa/ironía ("jaja", "me divierten", "xd") clasifican como `ironia` (familia `civica`). Esta regla **solo** aplica cuando el parámetro `es_oficial=True`.

5. **Agregación batch**: `aggregate_emotions()` retorna conteos por emoción, porcentajes, dominante y conteos por familia.

**Nunca** mencionar en las narrativas que la emoción fue calculada por IA.

---

### RG-9: Tema por reglas léxicas (sin IA)

La clasificación de tema se ejecuta mediante **reglas léxicas deterministas**.

**Componentes del método (`analytics/topic.py`):**

1. **Léxico por tema**: ~50 palabras/frases por cada una de las 10 categorías fijas (`TOPIC_LEXICON`): obras_servicios, seguridad, movilidad, empleo, salud, educacion, medio_ambiente, gobernanza, cultura_deportes, apoyo_generico.

2. **Coincidencia**: mismo patrón de tokens + frases multi-palabra que la emoción.

3. **Desempate**: mayor conteo gana. Sin coincidencias → `no_aplica`.

4. **Remapeo de categorías legacy**: `obras_publicas`/`servicios_publicos` → `obras_servicios`, `corrupcion`/`transparencia` → `gobernanza`, `cultura`/`deportes` → `cultura_deportes`.

---

### RG-10: Temas emergentes por n-gramas (sin IA)

La detección de temas emergentes se ejecuta mediante **extracción de bigramas/trigramas y comparación de frecuencia entre períodos**.

**Componentes del método (`analytics/emergent.py`):**

1. **Extracción**: bigramas y trigramas de textos con stopwords removidas.

2. **Frecuencia**: conteo de cada n-grama en el período actual.

3. **Tendencia** (si hay período previo):
   - `frecuencia_actual / max(frecuencia_previa, 1) ≥ 1.5` → `acelerando`
   - `frecuencia_actual / max(frecuencia_previa, 1) ≤ 0.67` → `desacelerando`
   - `frecuencia_previa == 0` y `actual > 0` → `nuevo`
   - Sin historial previo → `sin_comparacion`

4. **Mínimo**: `min_freq=2` por defecto para filtrar ruido.

---

### RG-11: Zona/ubicación por gazetteer (sin IA)

La detección de zona se ejecuta mediante **coincidencia de substring/palabra** contra un gazetteer curado.

**Componentes del método (`analytics/zona.py`):**

1. **Gazetteer**: departamentos (22), municipios (~60), zonas de la Ciudad de Guatemala (~25), barrios/colonias (~50).

2. **Prioridad**: zona GT > barrios > municipios > departamentos.

3. **Sin zona por defecto**: si no se reconoce ninguna zona en el texto, se retorna `zona=""`. Nunca se fuerza una zona.

4. **Propuestas**: nombres que parecen zona pero no están en el gazetteer se registran como propuesta (`tipo="zona"`). El gazetteer es extensible.

---

## Bloque I — Pulso General

| Sección | Reglas |
|---------|--------|
| Clima Narrativo | `narrativa` sigue exactamente la descripción del campo `narrativa` en `data/analysis_schema.json` (bloque1.clima_narrativo). No dupliques la plantilla aquí para evitar que ambos textos queden desincronizados. `enlaces_referencia` debe incluir los posts representativos del período. |

---

## Bloque II — Segmentación de Audiencia

### Mapa de Públicos — `total_posts_analizados`

`total_posts_analizados` debe ser el conteo total de publicaciones del período de las cuales se extrajeron los comentarios usados en `mapa_publicos`. No es el total de comentarios, ni el total de posts del dataset completo — solo los que alimentan esta segmentación específica.

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

- [ ] `clima_narrativo` tiene `tono_dominante`, `pct_favorable`, `pct_neutral`, `pct_critico` calculados por reglas léxicas (no por modelo IA).
- [ ] `clima_narrativo` tiene `tono_score_hoy` (promedio SENTIMENT_ORDER) y `formula_usada` = "NSI = (positivos - negativos) / total * 100".
- [ ] `narrativa` de Clima Narrativo tiene una frase "Conclusión:" explícita y ningún adjetivo sin cifra o tema detrás.
- [ ] Ninguna `narrativa` contiene HHI, NSI, IR, PI, ER.
- [ ] Ninguna `narrativa` contiene "censura" o "autocensura".
- [ ] Engagement = reacciones + comentarios + compartidos (consistencia).
- [ ] Voces de Influencia: si `engagement > 0`, sus submétricas no son 0.
- [ ] Alertas Cambridge: cada `tipo` incluye `enlaces_referencia` si menciona posts específicos.
- [ ] Puntos de Fricción: si `n_negativos > 0`, `emocion_dominante` no está vacío.
- [ ] Puntos de Fricción: campo `zona` poblado con gazetteer (vacío si no se detectó zona).
- [ ] Temas Emergentes: `temas_emergentes_lda` contiene n-gramas reales, no temas genéricos.
- [ ] Bloque IV: cada sección es `{"narrativa": "...", "enlaces_referencia": [...]}`.
- [ ] Bloque IV: cada `enlaces_referencia` contiene las URLs reales, no está vacío si la narrativa hace afirmaciones específicas.
- [ ] Ninguna afirmación se basa en datos fuera del período del `meta.periodo`.
- [ ] Toda narrativa termina con una línea "= NOMBRE CONTUNDENTE" derivada del ancla mencionada.
