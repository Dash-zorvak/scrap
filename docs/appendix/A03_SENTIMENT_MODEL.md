# A03_SENTIMENT_MODEL.md

# Modelo de Análisis de Sentimiento

## 1. Introducción

El Modelo de Análisis de Sentimiento de MIPA define el marco metodológico utilizado para identificar y clasificar la carga emocional expresada en mensajes digitales relacionados con una institución pública.

Este modelo forma parte del conjunto de dimensiones analíticas independientes del sistema y responde exclusivamente a la pregunta:

**¿Cuál es la carga emocional expresada en el mensaje?**

El modelo no determina intención comunicativa, aceptación ciudadana, apoyo político, percepción pública ni comportamiento futuro.

El análisis de sentimiento se limita a la identificación de señales emocionales observables dentro del contenido analizado.

---

# 2. Fundamentos Metodológicos

El análisis de sentimiento en MIPA se basa en principios de clasificación lingüística explicable.

Cada resultado debe estar sustentado mediante:

* evidencia textual;
* reglas definidas;
* criterios de clasificación;
* puntuaciones deterministas;
* nivel de confianza;
* trazabilidad del resultado.

El modelo evita interpretaciones psicológicas o inferencias externas no contenidas explícitamente en el mensaje.

---

# 3. Principios del Modelo

El modelo se fundamenta en los siguientes principios:

## 3.1 Observabilidad

Solo se consideran elementos presentes dentro del contenido analizado.

No se utilizan:

* contexto privado del usuario;
* historial personal;
* información externa no asociada al mensaje;
* inferencias sobre emociones no expresadas.

---

## 3.2 Separación Analítica

El sentimiento constituye una dimensión independiente.

No debe confundirse con:

| Dimensión              | Pregunta que responde                  |
| ---------------------- | -------------------------------------- |
| Tema                   | ¿Sobre qué trata el mensaje?           |
| Intención Comunicativa | ¿Qué busca realizar el mensaje?        |
| Sentimiento            | ¿Cuál es la carga emocional expresada? |

Un mensaje puede tener:

* sentimiento positivo con intención crítica;
* sentimiento negativo con intención informativa;
* sentimiento neutral con intención convocante.

---

## 3.3 Explicabilidad

Toda clasificación emocional debe poder justificarse mediante evidencia observable.

Ejemplo:

Mensaje:

"Gracias por mejorar el parque de nuestra comunidad."

Resultado:

Sentimiento:

Positivo

Evidencia:

* expresión de agradecimiento;
* valoración favorable;
* ausencia de elementos negativos.

---

# 4. Arquitectura del Modelo de Sentimiento

El modelo está compuesto por los siguientes componentes:

## 4.1 Entrada Analítica

La entrada corresponde al contenido textual procesado por el pipeline.

Puede incluir:

* publicaciones;
* comentarios;
* respuestas;
* mensajes institucionales;
* contenido digital relacionado.

---

## 4.2 Extracción de Evidencias

El sistema identifica señales lingüísticas asociadas a carga emocional.

Las evidencias pueden incluir:

* palabras valorativas;
* expresiones emocionales;
* calificadores positivos o negativos;
* estructuras de aprobación o rechazo;
* marcadores de satisfacción o inconformidad.

---

## 4.3 Clasificación Emocional

Las evidencias identificadas son procesadas mediante reglas de clasificación.

La salida principal corresponde a una categoría emocional.

---

# 5. Categorías de Sentimiento

MIPA utiliza tres categorías principales.

## 5.1 Sentimiento Positivo

Representa expresiones con valoración favorable hacia un elemento mencionado.

Ejemplos de evidencia:

* agradecimiento;
* reconocimiento;
* aprobación;
* satisfacción;
* valoración positiva.

Ejemplo:

"Excelente trabajo realizado por la alcaldía."

Clasificación:

Positivo.

---

## 5.2 Sentimiento Negativo

Representa expresiones con valoración desfavorable o rechazo explícito.

Ejemplos de evidencia:

* queja;
* inconformidad;
* crítica;
* desaprobación;
* frustración expresada.

Ejemplo:

"El servicio todavía presenta muchos problemas."

Clasificación:

Negativo.

---

## 5.3 Sentimiento Neutral

Representa mensajes donde no existe una carga emocional claramente identificable.

Ejemplos:

* información objetiva;
* anuncios;
* comunicados;
* datos descriptivos.

Ejemplo:

"La alcaldía realizará una reunión el próximo lunes."

Clasificación:

Neutral.

---

# 6. Evidencias de Sentimiento

El modelo considera diferentes niveles de evidencia.

## 6.1 Evidencia Lingüística

Corresponde a palabras o expresiones directamente asociadas con valoración emocional.

Ejemplos:

* positivo:

  * excelente;
  * gracias;
  * felicitaciones.

* negativo:

  * deficiente;
  * problema;
  * incumplimiento.

---

## 6.2 Evidencia Semántica

Considera el significado general de una expresión dentro del mensaje.

Ejemplo:

"Finalmente repararon la calle después de meses de espera."

Puede contener:

* reconocimiento positivo;
* referencia negativa al retraso previo.

La interpretación depende de la estructura completa del mensaje.

---

## 6.3 Evidencia Contextual

Considera elementos del mensaje que modifican la interpretación emocional.

Ejemplos:

* negaciones;
* sarcasmo explícito;
* contraste entre afirmaciones;
* condiciones temporales.

---

# 7. Reglas de Clasificación

La clasificación sigue reglas deterministas.

## Regla 1

Una expresión emocional explícita tiene mayor peso que una interpretación indirecta.

---

## Regla 2

La presencia de palabras positivas no garantiza sentimiento positivo si existe negación o contradicción.

Ejemplo:

"No fue una buena decisión."

Resultado:

Negativo.

---

## Regla 3

Los mensajes informativos sin valoración emocional permanecen como neutrales.

---

## Regla 4

Cuando existen señales emocionales contradictorias, el sistema debe conservar la evidencia y reducir la confianza.

---

# 8. Resolución de Conflictos Emocionales

Los conflictos pueden presentarse cuando un mensaje contiene señales positivas y negativas simultáneamente.

## 8.1 Conflicto Positivo-Negativo

Ejemplo:

"La obra quedó bien, pero tardaron demasiado."

Resultado:

Sentimiento:

Mixto evaluado como categoría dominante según evidencia.

Confianza:

Reducida.

---

## 8.2 Conflicto por Negación

Ejemplo:

"No estamos satisfechos con el resultado."

La palabra positiva no domina debido a la estructura negativa.

---

## 8.3 Conflicto por Contexto

Ejemplo:

"Gran trabajo dejando la calle abandonada nuevamente."

La interpretación depende del significado completo de la expresión.

---

# 9. Niveles de Confianza

El modelo asigna niveles de confianza según la claridad de la evidencia.

## Alta

Existe evidencia emocional directa y consistente.

Ejemplo:

"Muchas gracias por este excelente proyecto."

---

## Media

Existe evidencia emocional identificable, pero con elementos ambiguos.

Ejemplo:

"El proyecto tiene cosas buenas, aunque falta mejorar."

---

## Baja

La señal emocional es débil o contradictoria.

Ejemplo:

Mensajes breves sin suficiente contexto.

---

# 10. Variables Generadas por el Pipeline

El modelo genera variables analíticas asociadas al sentimiento.

Ejemplos conceptuales:

```json
{
  "sentiment_label": "positive",
  "sentiment_score": 0.82,
  "sentiment_confidence": "high",
  "sentiment_evidence": [
    "excelente trabajo",
    "agradecimiento explícito"
  ]
}
```

Estas variables permiten:

* auditoría;
* reproducción;
* análisis posterior;
* trazabilidad metodológica.

---

# 11. Integración con el Pipeline Analítico

El modelo de sentimiento funciona como un módulo independiente dentro del pipeline.

Flujo general:

1. recepción del contenido;
2. procesamiento lingüístico;
3. extracción de evidencia;
4. clasificación emocional;
5. generación de variables;
6. almacenamiento del resultado.

El resultado puede combinarse con otras dimensiones sin modificar su independencia conceptual.

---

# 12. Integración con analysis.json

Los resultados de sentimiento son almacenados dentro de la estructura analítica generada por el sistema.

La integración permite conservar:

* etiqueta emocional;
* puntuación;
* evidencia;
* confianza;
* versión metodológica.

La información debe permanecer disponible para auditoría posterior.

---

# 13. Versionado del Modelo

El modelo utiliza control de versiones metodológico.

Formato:

MAJOR.MINOR.PATCH

## MAJOR

Cambios fundamentales en:

* categorías;
* reglas principales;
* interpretación metodológica.

---

## MINOR

Cambios compatibles:

* nuevas reglas;
* ampliación de evidencia;
* ajustes documentales.

---

## PATCH

Correcciones menores:

* errores documentales;
* mejoras de claridad;
* correcciones técnicas.

---

# 14. Limitaciones del Modelo

El modelo no determina:

* intención política;
* apoyo electoral;
* satisfacción general de población;
* opinión pública completa;
* comportamiento futuro.

El sentimiento identificado corresponde únicamente al contenido observado.

---

# 15. Consideraciones Metodológicas Finales

El análisis de sentimiento dentro de MIPA constituye una clasificación descriptiva y explicable de señales emocionales presentes en mensajes digitales.

Su función es complementar el análisis institucional mediante una dimensión emocional independiente.

El modelo mantiene los principios fundamentales del sistema:

* determinismo;
* transparencia;
* reproducibilidad;
* auditoría;
* separación conceptual entre dimensiones analíticas.

---

# 16. Glosario

## Sentimiento

Carga emocional expresada dentro de un mensaje.

## Evidencia Emocional

Elemento textual utilizado para justificar una clasificación emocional.

## Polaridad

Dirección emocional del mensaje:

* positiva;
* negativa;
* neutral.

## Confianza

Nivel de seguridad asociado al resultado generado.

## Señal Lingüística

Elemento textual observable asociado a una categoría emocional.

---

# 17. Referencias Metodológicas / Bibliografía

* Pang, B., & Lee, L. (2008). *Opinion Mining and Sentiment Analysis*. Foundations and Trends in Information Retrieval.

* Liu, B. (2012). *Sentiment Analysis and Opinion Mining*. Morgan & Claypool Publishers.

* Feldman, R. (2013). *Techniques and Applications for Sentiment Analysis*. Communications of the ACM.

* Medhat, W., Hassan, A., & Korashy, H. (2014). Sentiment analysis algorithms and applications: A survey.

* Jurafsky, D., & Martin, J. H. *Speech and Language Processing*.
