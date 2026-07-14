# A04_EMOTION_CLASSIFICATION_MODEL.md

# Modelo de Clasificación Emocional

## 1. Introducción

El Modelo de Clasificación Emocional de MIPA define el marco metodológico utilizado para identificar emociones expresadas dentro de mensajes digitales relacionados con una institución pública.

Este modelo complementa el análisis de sentimiento mediante una representación más específica de las señales emocionales presentes en el contenido.

Mientras el análisis de sentimiento responde:

**¿Cuál es la carga emocional expresada?**

El modelo de clasificación emocional responde:

**¿Qué tipo de emoción está expresándose dentro del mensaje?**

Ambos modelos son dimensiones relacionadas pero independientes.

El modelo no determina estados psicológicos reales de los usuarios, personalidad, motivaciones internas ni condiciones emocionales permanentes.

Únicamente clasifica patrones emocionales observables en el contenido textual.

---

# 2. Fundamentos Metodológicos

La clasificación emocional en MIPA se basa en principios de análisis lingüístico explicable.

Toda clasificación debe estar sustentada mediante:

* evidencia textual;
* reglas de identificación;
* patrones lingüísticos observables;
* puntuación determinista;
* nivel de confianza;
* trazabilidad.

El sistema evita inferencias externas sobre la persona que genera el mensaje.

---

# 3. Relación con el Modelo de Sentimiento

El sentimiento y la emoción representan niveles diferentes de análisis.

| Dimensión   | Pregunta                                             |
| ----------- | ---------------------------------------------------- |
| Sentimiento | ¿La carga expresada es positiva, negativa o neutral? |
| Emoción     | ¿Qué emoción específica aparece en el mensaje?       |

Ejemplo:

Mensaje:

"Estamos muy agradecidos por la reparación del parque."

Sentimiento:

Positivo.

Emoción predominante:

Gratitud.

---

# 4. Principios del Modelo

## 4.1 Observación del Lenguaje

El modelo analiza únicamente expresiones presentes dentro del mensaje.

No utiliza:

* información privada;
* identidad del autor;
* historial individual;
* comportamiento externo.

---

## 4.2 Explicabilidad Emocional

Toda emoción identificada debe contar con evidencia verificable.

Ejemplo:

Mensaje:

"Estamos preocupados por la falta de iluminación."

Emoción:

Preocupación.

Evidencia:

"estamos preocupados".

---

## 4.3 Independencia Interpretativa

La clasificación emocional no debe mezclarse con:

* intención comunicativa;
* clasificación temática;
* evaluación política;
* predicción de comportamiento.

---

# 5. Arquitectura del Modelo

El modelo está compuesto por cuatro componentes principales.

## 5.1 Entrada del Mensaje

Recibe contenido textual procesado por el pipeline.

Fuentes posibles:

* publicaciones;
* comentarios;
* respuestas;
* comunicaciones institucionales.

---

## 5.2 Extracción de Señales Emocionales

El sistema identifica elementos lingüísticos asociados a emociones.

Incluye:

* palabras emocionales;
* expresiones afectivas;
* verbos emocionales;
* adjetivos valorativos;
* estructuras lingüísticas.

---

## 5.3 Clasificación Emocional

Las señales identificadas son comparadas con categorías emocionales definidas.

La clasificación genera:

* emoción principal;
* emociones secundarias;
* evidencia asociada;
* confianza.

---

## 5.4 Registro Analítico

Los resultados son almacenados para:

* auditoría;
* reproducción;
* análisis histórico;
* integración con otros módulos.

---

# 6. Taxonomía Emocional

MIPA utiliza una clasificación basada en emociones observables dentro del lenguaje.

Las categorías principales son:

---

## 6.1 Alegría

Representa expresiones de satisfacción, entusiasmo o valoración favorable.

Ejemplos:

* felicidad;
* celebración;
* entusiasmo;
* reconocimiento positivo.

Ejemplo:

"Nos alegra mucho esta mejora para la comunidad."

---

## 6.2 Gratitud

Representa expresiones explícitas de agradecimiento.

Indicadores:

* gracias;
* agradecemos;
* reconocimiento;
* valoración del apoyo recibido.

Ejemplo:

"Gracias por escuchar las necesidades del barrio."

---

## 6.3 Esperanza

Representa expresiones orientadas hacia expectativas favorables futuras.

Ejemplo:

"Esperamos que este proyecto beneficie a todos."

---

## 6.4 Preocupación

Representa expresiones asociadas con inquietud o alerta.

Indicadores:

* preocupación;
* temor;
* incertidumbre;
* advertencia.

Ejemplo:

"Nos preocupa el estado actual de la carretera."

---

## 6.5 Frustración

Representa expresiones relacionadas con dificultad, cansancio o insatisfacción acumulada.

Ejemplo:

"Llevamos meses esperando una solución."

---

## 6.6 Enojo

Representa expresiones de molestia intensa o rechazo emocional.

Indicadores:

* indignación;
* molestia;
* reclamo fuerte.

Ejemplo:

"Estamos cansados de esta situación."

---

## 6.7 Tristeza

Representa expresiones asociadas con pérdida, decepción o pesar.

Ejemplo:

"Es triste ver el abandono de este lugar."

---

## 6.8 Sorpresa

Representa expresiones de asombro ante un hecho positivo o negativo.

Ejemplo:

"No esperábamos una respuesta tan rápida."

---

## 6.9 Neutralidad Emocional

Representa mensajes donde no existe evidencia emocional específica.

Ejemplo:

"La reunión se realizará el viernes."

---

# 7. Evidencias Emocionales

El modelo considera diferentes niveles de evidencia.

## 7.1 Evidencia Directa

Expresiones emocionales explícitas.

Ejemplo:

"Estamos felices."

---

## 7.2 Evidencia Indirecta

Expresiones cuyo significado implica una emoción.

Ejemplo:

"Después de años finalmente recibimos ayuda."

Puede indicar:

* alivio;
* satisfacción.

---

## 7.3 Evidencia Contextual

Elementos que modifican la interpretación.

Incluye:

* negaciones;
* contradicciones;
* sarcasmo explícito;
* combinación emocional.

---

# 8. Modelo Multi-Emoción

Un mensaje puede contener más de una emoción.

Ejemplo:

"Estamos agradecidos por la obra, pero preocupados por el retraso."

Resultado:

Emoción principal:

Gratitud.

Emoción secundaria:

Preocupación.

El modelo conserva la coexistencia emocional cuando existe evidencia suficiente.

---

# 9. Resolución de Conflictos Emocionales

## 9.1 Conflicto entre Emociones Positivas y Negativas

Ejemplo:

"El proyecto es bueno, pero la espera fue demasiado larga."

Resultado:

* emociones múltiples;
* reducción de confianza.

---

## 9.2 Conflicto por Intensidad

Cuando aparecen varias emociones, la emoción principal se determina mediante:

* fuerza lingüística;
* claridad;
* frecuencia;
* posición dentro del mensaje.

---

## 9.3 Conflicto por Ambigüedad

Cuando la evidencia no permite determinar una emoción específica:

Resultado:

* categoría general;
* menor nivel de confianza.

---

# 10. Niveles de Confianza

## Alta

Existe evidencia emocional directa y consistente.

---

## Media

Existe evidencia emocional interpretable pero con elementos ambiguos.

---

## Baja

La emoción es incierta o depende demasiado del contexto.

---

# 11. Variables Generadas por el Pipeline

El modelo genera variables analíticas como:

```json id="r9x2m1"
{
  "emotion_primary": "gratitude",
  "emotion_secondary": [
    "hope"
  ],
  "emotion_confidence": "high",
  "emotion_evidence": [
    "gracias por apoyar"
  ]
}
```

Estas variables permiten:

* seguimiento metodológico;
* auditoría;
* comparación histórica;
* análisis agregado.

---

# 12. Integración con el Pipeline Analítico

El modelo opera como módulo independiente.

Flujo:

1. recepción del mensaje;
2. análisis lingüístico;
3. identificación de señales emocionales;
4. clasificación;
5. generación de variables;
6. almacenamiento.

La clasificación emocional no modifica:

* tema;
* intención comunicativa;
* sentimiento.

---

# 13. Integración con analysis.json

Los resultados emocionales pueden almacenarse junto con:

* etiqueta emocional;
* emoción principal;
* emociones secundarias;
* evidencia;
* confianza;
* versión del modelo.

La información mantiene trazabilidad completa.

---

# 14. Versionado del Modelo

El modelo utiliza versionado:

MAJOR.MINOR.PATCH

## MAJOR

Cambios en:

* estructura emocional;
* categorías principales;
* reglas fundamentales.

---

## MINOR

Cambios compatibles:

* nuevas emociones;
* nuevas reglas;
* ampliaciones metodológicas.

---

## PATCH

Correcciones menores:

* documentación;
* errores;
* ajustes técnicos.

---

# 15. Limitaciones del Modelo

El modelo no determina:

* emociones reales de una persona;
* estado psicológico;
* intención oculta;
* personalidad;
* comportamiento futuro.

Solo clasifica señales emocionales presentes en el contenido analizado.

---

# 16. Consideraciones Metodológicas Finales

La clasificación emocional dentro de MIPA constituye una representación descriptiva de señales afectivas expresadas lingüísticamente.

Su propósito es complementar el análisis institucional mediante una dimensión emocional explicable y auditable.

El modelo mantiene los principios centrales del sistema:

* determinismo;
* transparencia;
* reproducibilidad;
* separación analítica;
* trazabilidad.

---

# 17. Glosario

## Emoción

Categoría afectiva observable expresada mediante señales lingüísticas.

## Emoción Principal

Emoción con mayor evidencia dentro del mensaje.

## Emoción Secundaria

Emoción adicional identificada con evidencia suficiente.

## Evidencia Emocional

Elemento textual que justifica una clasificación.

## Intensidad Emocional

Fuerza expresiva asociada a una emoción.

## Confianza

Nivel de seguridad asociado al resultado.

---

# 18. Referencias Metodológicas / Bibliografía

* Ekman, P. (1992). *An Argument for Basic Emotions*. Cognition and Emotion.

* Plutchik, R. (1980). *Emotion: A Psychoevolutionary Synthesis*. Harper & Row.

* Liu, B. (2012). *Sentiment Analysis and Opinion Mining*. Morgan & Claypool Publishers.

* Mohammad, S. M. (2016). *Sentiment Analysis: Detecting Valence, Emotions, and Other Affectual States from Text*.

* Jurafsky, D., & Martin, J. H. *Speech and Language Processing*.
