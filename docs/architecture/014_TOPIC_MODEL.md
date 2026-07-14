# 014 · Modelo de Temas

## Propósito

El Modelo de Temas define la metodología oficial mediante la cual MIPA identifica, clasifica y organiza los temas presentes en las conversaciones digitales.

Su objetivo es transformar grandes volúmenes de publicaciones y comentarios en conjuntos temáticos estructurados que permitan comprender de qué está hablando la ciudadanía, cómo evolucionan las conversaciones y qué asuntos concentran la atención durante un período determinado.

El modelo describe el contenido de las conversaciones, no la posición de quienes participan en ellas.

---

# Objetivo

El Modelo de Temas busca responder una pregunta específica:

> ¿Cuáles son los temas que estructuran la conversación digital observada durante el período analizado?

El objetivo no es determinar la importancia política de un tema, sino identificar su presencia, evolución y comportamiento dentro de la evidencia disponible.

---

# Qué mide

El modelo identifica y organiza:

- asuntos recurrentes;
- conversaciones relacionadas;
- agrupaciones semánticas;
- evolución temática;
- coexistencia de temas;
- concentración temática;
- distribución del contenido.

El resultado es un mapa estructurado de la conversación digital.

---

# Qué NO mide

El Modelo de Temas no mide:

- aprobación ciudadana;
- intención de voto;
- calidad de la gestión pública;
- relevancia política objetiva;
- veracidad de una publicación;
- postura ideológica;
- emociones.

Estas dimensiones pertenecen a modelos metodológicos independientes.

---

# Unidad de clasificación

La unidad mínima de análisis será cada evidencia individual.

Dependiendo de la plataforma, una evidencia puede corresponder a:

- una publicación;
- un comentario;
- una respuesta;
- cualquier unidad textual definida por el Pipeline.

Cada evidencia será clasificada temáticamente antes del cálculo de indicadores.

---

# Naturaleza de los temas

Un tema representa un conjunto de evidencias que comparten un mismo asunto principal.

Los temas no representan personas, instituciones ni categorías políticas.

Representan únicamente agrupaciones de contenido con características semánticas comunes.

---

# Clasificación temática

Cada evidencia deberá ser asignada al tema que mejor represente su contenido principal.

Cuando la metodología lo permita, una evidencia podrá estar asociada a múltiples temas.

La estrategia exacta de clasificación será definida por el Pipeline y documentada mediante su correspondiente versión metodológica.

---

# Independencia respecto a otros modelos

El tema asignado es independiente de:

- la emoción;
- la postura;
- la interacción obtenida;
- la popularidad;
- el riesgo;
- la intensidad conversacional.

Estos componentes podrán combinarse posteriormente durante el análisis, pero serán calculados de forma independiente.

---

# Uso dentro del Pipeline

El Pipeline será responsable de:

1. procesar la evidencia textual;
2. identificar el tema correspondiente;
3. validar la clasificación;
4. registrar la trazabilidad;
5. almacenar el resultado en analytics.db.

El Dashboard nunca clasificará temas.

Únicamente visualizará la información generada previamente.

---

# Agregaciones temáticas

A partir de las clasificaciones individuales podrán calcularse indicadores como:

- distribución de temas;
- participación relativa;
- evolución temporal;
- intensidad por tema;
- interacción por tema;
- riesgo por tema;
- emociones por tema;
- posturas por tema.

Todas estas agregaciones serán calculadas exclusivamente por el Pipeline.

---

# Evolución temporal

El modelo permitirá observar cómo cambian los temas durante distintos períodos.

Podrán identificarse, entre otros:

- temas emergentes;
- temas persistentes;
- temas en descenso;
- temas recurrentes;
- temas estacionales.

La evolución siempre estará basada en evidencia registrada.

---

# Concentración temática

El sistema podrá calcular el grado en que la conversación se concentra alrededor de pocos temas o se distribuye entre muchos.

Una elevada concentración indica que una proporción importante de la conversación gira alrededor de un número reducido de asuntos.

Una baja concentración refleja una conversación más diversa.

---

# Evidencia

Todo tema deberá poder rastrearse hasta las evidencias que lo originaron.

Cada clasificación permitirá acceder directamente a:

- publicaciones;
- comentarios;
- plataforma;
- fecha;
- identificadores originales.

Ningún tema podrá existir sin evidencia verificable.

---

# Cobertura

Cada resultado deberá indicar como mínimo:

- plataformas analizadas;
- período evaluado;
- cantidad de evidencias clasificadas;
- cantidad de evidencias excluidas;
- cobertura efectiva del análisis.

La cobertura forma parte obligatoria de la interpretación.

---

# Reproducibilidad

La clasificación temática deberá producir exactamente los mismos resultados cuando se procese nuevamente la misma evidencia utilizando:

- la misma versión del Pipeline;
- la misma metodología;
- el mismo modelo temático.

No se permitirán modificaciones manuales posteriores al procesamiento.

---

# Versionado

Toda modificación del Modelo de Temas deberá registrar:

- versión;
- fecha de implementación;
- cambios metodológicos;
- justificación técnica;
- compatibilidad con versiones anteriores.

Esto garantiza la consistencia histórica del sistema.

---

# Limitaciones

El Modelo de Temas depende exclusivamente del contenido disponible en la evidencia procesada.

No identifica temas presentes fuera de las plataformas analizadas.

No determina causalidad.

No evalúa la importancia objetiva de un asunto.

No interpreta motivaciones individuales.

Debe utilizarse siempre junto con el Modelo de Emociones, el Modelo de Posturas y los indicadores analíticos del sistema.

---

# Relación con otros documentos

Este modelo se integra con:

- 013_EMOTION_MODEL.md
- 015_POSTURE_MODEL.md
- 016_VALIDATION_MODEL.md
- 017_TRACEABILITY_MODEL.md
- 020_FORMULAS.md

En conjunto, estos documentos permiten transformar la evidencia digital en una representación estructurada, trazable y reproducible de las conversaciones observadas dentro de MIPA.