# 015 · Modelo de Posturas

## Propósito

El Modelo de Posturas define la metodología oficial mediante la cual MIPA identifica y clasifica la posición expresada por una evidencia respecto al sujeto de análisis.

Su objetivo es determinar la orientación del discurso observado sin confundirla con las emociones, la interacción, la popularidad o cualquier otro componente analítico.

La postura representa la dirección de la opinión expresada dentro de una evidencia específica.

---

# Objetivo

El Modelo de Posturas busca responder una pregunta específica:

> ¿Qué posición expresa la evidencia respecto al sujeto analizado?

La clasificación de postura permite comprender la distribución del discurso dentro de la conversación digital y constituye un insumo para diversos indicadores del sistema.

---

# Qué mide

El modelo mide la orientación observable del contenido expresado en cada evidencia.

La postura describe la relación entre el discurso y el sujeto analizado.

No evalúa la intensidad emocional ni la importancia del contenido.

---

# Qué NO mide

El Modelo de Posturas no mide:

- emociones;
- intención de voto;
- aprobación ciudadana;
- percepción general;
- veracidad de una afirmación;
- popularidad;
- riesgo digital;
- interacción obtenida;
- calidad de la gestión pública.

Estas dimensiones son analizadas mediante modelos metodológicos independientes.

---

# Unidad de clasificación

La unidad mínima de clasificación será cada evidencia individual.

Dependiendo de la plataforma, una evidencia podrá corresponder a:

- una publicación;
- un comentario;
- una respuesta;
- cualquier unidad textual definida por el Pipeline.

Cada evidencia recibirá una única clasificación de postura conforme a la metodología vigente.

---

# Naturaleza de la postura

La postura representa únicamente la posición expresada dentro del contenido analizado.

No representa:

- la identidad política del autor;
- sus preferencias permanentes;
- su comportamiento fuera de la evidencia observada.

El sistema clasifica el contenido, no a las personas.

---

# Clasificación oficial

MIPA utilizará un catálogo oficial de posturas definido por la metodología vigente.

Cada categoría deberá contar con una definición clara, mutuamente excluyente y reproducible.

Las categorías oficiales serán documentadas y versionadas como parte del modelo analítico.

---

# Independencia respecto a otros modelos

La postura es independiente de:

- la emoción;
- el tema;
- la interacción;
- la popularidad;
- el riesgo digital;
- la intensidad conversacional.

Una misma postura puede expresarse mediante emociones diferentes.

De igual manera, una misma emoción puede aparecer asociada a posturas distintas.

---

# Uso dentro del Pipeline

El Pipeline será responsable de:

1. identificar la evidencia;
2. ejecutar la clasificación de postura;
3. validar el resultado;
4. registrar la trazabilidad completa;
5. almacenar la clasificación en analytics.db.

El Dashboard nunca clasificará posturas.

Únicamente visualizará los resultados producidos por el Pipeline.

---

# Agregaciones

A partir de las clasificaciones individuales podrán calcularse indicadores como:

- distribución de posturas;
- evolución temporal;
- participación relativa;
- interacción por postura;
- emociones por postura;
- temas por postura;
- riesgo asociado a cada postura.

Todas estas métricas serán calculadas exclusivamente por el Pipeline.

---

# Evolución temporal

El modelo permitirá analizar cómo cambian las posturas durante distintos períodos.

Podrán identificarse cambios en:

- participación relativa;
- estabilidad;
- crecimiento;
- disminución;
- persistencia.

La evolución siempre estará sustentada en evidencia registrada.

---

# Evidencia

Toda clasificación de postura deberá estar vinculada directamente con la evidencia que la originó.

Cada resultado permitirá acceder a:

- publicación original;
- comentario original;
- plataforma;
- fecha;
- identificador de la evidencia.

No podrá existir ninguna clasificación sin respaldo verificable.

---

# Cobertura

Cada análisis de posturas deberá indicar explícitamente:

- plataformas incluidas;
- período analizado;
- cantidad de evidencias clasificadas;
- cantidad de evidencias excluidas;
- cobertura efectiva.

La cobertura constituye un elemento obligatorio para interpretar cualquier resultado.

---

# Reproducibilidad

La clasificación de postura deberá producir exactamente el mismo resultado cuando se procese nuevamente utilizando:

- la misma evidencia;
- la misma metodología;
- la misma versión del Pipeline.

No se permitirán ajustes manuales posteriores a la clasificación.

---

# Versionado

Toda modificación del Modelo de Posturas deberá registrar:

- versión;
- fecha de implementación;
- cambios realizados;
- justificación metodológica;
- compatibilidad con versiones anteriores.

Esto garantiza la consistencia y comparabilidad histórica del sistema.

---

# Limitaciones

El Modelo de Posturas depende exclusivamente del contenido disponible en la evidencia procesada.

No puede determinar:

- la intención real del autor;
- motivaciones personales;
- afiliaciones políticas;
- opiniones no expresadas;
- cambios de opinión fuera del período analizado.

Los resultados deben interpretarse siempre junto con el Modelo de Emociones, el Modelo de Temas y el resto de indicadores metodológicos.

---

# Relación con otros documentos

Este modelo se complementa con:

- 013_EMOTION_MODEL.md
- 014_TOPIC_MODEL.md
- 016_VALIDATION_MODEL.md
- 017_TRACEABILITY_MODEL.md
- 020_FORMULAS.md

En conjunto, estos documentos conforman el marco metodológico que permite describir de manera objetiva, trazable y reproducible el comportamiento del discurso digital analizado por MIPA.