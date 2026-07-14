# 013 · Modelo de Emociones

## Propósito

El Modelo de Emociones define la metodología oficial mediante la cual MIPA clasifica, organiza y utiliza las emociones presentes en las conversaciones digitales.

Su objetivo es representar con mayor fidelidad la complejidad emocional del discurso observado, evitando reducir el análisis a categorías simplificadas como "positivo", "neutro" o "negativo".

Todas las clasificaciones emocionales utilizadas por el sistema deberán seguir este modelo.

---

# Objetivo

El Modelo de Emociones busca responder una pregunta específica:

> ¿Qué emociones predominan en la conversación digital y cómo influyen en la interpretación del comportamiento colectivo observado?

El objetivo no es asignar una valoración moral a los mensajes, sino describir el estado emocional reflejado en la evidencia disponible.

---

# Principios metodológicos

El modelo se fundamenta en los siguientes principios:

- Las emociones son multidimensionales.
- Un mismo tema puede generar emociones diferentes.
- Una emoción no implica necesariamente una postura.
- Una emoción no determina la intención del autor.
- El comportamiento colectivo no puede resumirse mediante una única polaridad.

Por esta razón, MIPA utiliza un modelo emocional amplio en lugar de una clasificación binaria o ternaria.

---

# Modelo oficial

MIPA utilizará un catálogo oficial compuesto por 31 emociones.

Este catálogo constituye el estándar metodológico del sistema.

Ningún componente del Pipeline podrá sustituir este modelo por clasificaciones como:

- positivo
- negativo
- neutro

Estas categorías podrán derivarse posteriormente como agregaciones analíticas si algún indicador lo requiere, pero nunca reemplazarán el modelo emocional oficial.

---

# Unidad de clasificación

La unidad mínima de clasificación emocional será cada evidencia individual.

Dependiendo de la plataforma, una evidencia puede corresponder a:

- una publicación
- un comentario
- una respuesta
- un texto procesado
- cualquier otra unidad definida por el Pipeline

Cada evidencia recibirá una única clasificación emocional según la metodología vigente.

---

# Independencia respecto a otros modelos

La emoción clasificada es independiente de:

- la postura política
- el tema tratado
- la popularidad del contenido
- el nivel de interacción
- la relevancia de la publicación

Estos componentes serán modelados por documentos metodológicos independientes.

---

# Uso dentro del Pipeline

El Pipeline será responsable de:

1. identificar la evidencia textual;
2. ejecutar el proceso de clasificación emocional;
3. validar la consistencia del resultado;
4. almacenar la emoción asignada;
5. registrar la trazabilidad completa del proceso.

El Dashboard nunca realizará clasificaciones emocionales.

Únicamente visualizará los resultados producidos por el Pipeline.

---

# Almacenamiento

Cada clasificación emocional deberá registrarse en analytics.db.

Como mínimo deberá conservar:

- identificador de la evidencia;
- emoción asignada;
- versión del modelo;
- fecha de procesamiento;
- versión del Pipeline;
- referencias de trazabilidad.

El esquema completo será definido en:

019_ANALYTICS_DB_SCHEMA.md

---

# Agregaciones

A partir de las clasificaciones individuales podrán calcularse métricas agregadas como:

- distribución emocional;
- evolución temporal;
- intensidad emocional;
- diversidad emocional;
- concentración emocional;
- estabilidad emocional;
- variación entre períodos.

Estas agregaciones serán calculadas exclusivamente por el Pipeline.

---

# Relación con los indicadores

Las emociones constituyen un insumo para diversos indicadores metodológicos, entre ellos:

- Pulso IQ;
- Riesgo Digital;
- Popularidad Digital;
- indicadores temáticos;
- análisis narrativo.

La emoción nunca sustituye al indicador final.

Cada indicador define de manera independiente cómo incorpora la información emocional.

---

# Interpretación

Una emoción representa únicamente la clasificación del contenido observado.

No representa:

- una intención política;
- una preferencia electoral;
- una opinión permanente del autor;
- una característica psicológica de la persona.

El sistema describe el contenido, no a las personas.

---

# Evidencia

Toda clasificación emocional deberá estar vinculada directamente con la evidencia que la originó.

Cada resultado deberá permitir acceder a:

- publicación original;
- comentario original;
- plataforma;
- fecha;
- identificador de la evidencia.

La emoción nunca podrá existir sin una referencia verificable.

---

# Cobertura

Cada análisis emocional deberá indicar explícitamente:

- cantidad de evidencias procesadas;
- cantidad de evidencias excluidas;
- plataformas incluidas;
- período analizado;
- cobertura efectiva del análisis.

La cobertura forma parte obligatoria de la interpretación.

---

# Reproducibilidad

La clasificación emocional deberá ser reproducible utilizando:

- la misma evidencia;
- la misma versión del modelo;
- la misma versión del Pipeline.

No se permitirán modificaciones manuales posteriores a la clasificación.

Toda actualización metodológica deberá generar una nueva versión del modelo.

---

# Versionado

El Modelo de Emociones será versionado.

Toda modificación deberá registrar como mínimo:

- versión;
- fecha de entrada en vigor;
- cambios realizados;
- justificación metodológica;
- compatibilidad con versiones anteriores.

Esto garantiza la comparabilidad histórica de los resultados.

---

# Limitaciones

El Modelo de Emociones describe únicamente la emoción inferida a partir de la evidencia disponible.

No puede determinar:

- la intención real del autor;
- el contexto externo no presente en el contenido;
- emociones no expresadas;
- estados emocionales permanentes.

Los resultados deben interpretarse siempre junto con el contexto analítico y el resto de indicadores del sistema.

---

# Relación con otros documentos

Este modelo se complementa con:

- 014_TOPIC_MODEL.md
- 015_POSTURE_MODEL.md
- 016_VALIDATION_MODEL.md
- 017_TRACEABILITY_MODEL.md
- 020_FORMULAS.md

En conjunto, estos documentos conforman la base metodológica para la clasificación y análisis del comportamiento digital dentro de MIPA.