# A12_SENTIMENT_SCORING_FRAMEWORK.md

# Marco de Puntuación de Sentimiento

## 1. Introducción

El Marco de Puntuación de Sentimiento de MIPA define la metodología utilizada para representar cuantitativamente la carga emocional expresada dentro de los mensajes digitales analizados.

Este marco complementa el **A03_SENTIMENT_MODEL.md** proporcionando una estructura de puntuación que permite representar la intensidad relativa de las señales emocionales identificadas.

El modelo responde exclusivamente a la pregunta:

**¿Cuál es la magnitud de la carga emocional expresada en el mensaje?**

La puntuación de sentimiento no representa:

* apoyo ciudadano;
* intención electoral;
* aprobación institucional;
* percepción pública general;
* estado emocional real del autor.

La puntuación corresponde únicamente a la evidencia emocional observable dentro del contenido textual.

---

# 2. Fundamentos Metodológicos

La puntuación de sentimiento en MIPA se basa en criterios deterministas y explicables.

Cada puntuación debe estar respaldada por:

* evidencia textual;
* reglas de asignación;
* intensidad emocional identificada;
* ajustes por contexto;
* nivel de confianza;
* trazabilidad.

El sistema evita generar valores numéricos sin una justificación metodológica documentada.

---

# 3. Relación con el Modelo de Sentimiento

El modelo de sentimiento y su puntuación cumplen funciones complementarias.

| Elemento                  | Función                           |
| ------------------------- | --------------------------------- |
| Etiqueta de Sentimiento   | Clasifica la dirección emocional  |
| Puntuación de Sentimiento | Representa la intensidad relativa |

Ejemplo:

Mensaje:

"Excelente trabajo realizado por la alcaldía."

Clasificación:

Sentimiento:

Positivo.

Puntuación:

Alta intensidad positiva.

---

# 4. Principios del Modelo de Puntuación

## 4.1 Determinismo

La misma evidencia procesada bajo las mismas reglas debe producir resultados equivalentes.

---

## 4.2 Interpretabilidad

Toda puntuación debe poder explicarse mediante evidencia observable.

---

## 4.3 Normalización

Las puntuaciones deben utilizar una escala consistente para permitir comparación entre mensajes.

---

## 4.4 Separación Conceptual

Una puntuación alta no significa:

* mayor apoyo político;
* mayor aceptación;
* mayor importancia social.

Solo representa intensidad emocional expresada.

---

# 5. Escala de Puntuación

MIPA utiliza una escala normalizada para representar intensidad.

Ejemplo conceptual:

| Rango         | Interpretación       |
| ------------- | -------------------- |
| -1.00 a -0.60 | Negatividad alta     |
| -0.59 a -0.20 | Negatividad moderada |
| -0.19 a 0.19  | Neutralidad          |
| 0.20 a 0.59   | Positividad moderada |
| 0.60 a 1.00   | Positividad alta     |

La escala permite mantener consistencia analítica.

---

# 6. Componentes de la Puntuación

La puntuación puede construirse mediante diferentes componentes.

---

# 6.1 Polaridad Emocional

Representa la dirección del sentimiento.

Valores posibles:

* negativo;
* neutral;
* positivo.

---

# 6.2 Intensidad Léxica

Considera la fuerza de expresiones emocionales.

Ejemplo:

Menor intensidad:

"bien".

Mayor intensidad:

"excelente".

---

# 6.3 Contexto Lingüístico

Considera elementos que modifican el significado.

Incluye:

* negaciones;
* contrastes;
* expresiones condicionales.

Ejemplo:

"No fue una buena decisión."

La palabra positiva no domina la puntuación final.

---

# 6.4 Evidencia Acumulada

Considera la cantidad y consistencia de señales emocionales presentes.

---

# 7. Reglas de Ajuste de Puntuación

## 7.1 Regla de Intensificación

Expresiones intensificadoras pueden aumentar la puntuación.

Ejemplo:

"Muy excelente trabajo."

Mayor intensidad positiva.

---

## 7.2 Regla de Negación

Las negaciones modifican el valor emocional.

Ejemplo:

"No estamos satisfechos."

Resultado:

Tendencia negativa.

---

## 7.3 Regla de Contraste

Cuando existen emociones opuestas, la puntuación debe reflejar la coexistencia.

Ejemplo:

"La obra es buena, pero tardaron demasiado."

Resultado:

Puntuación moderada o reducida.

---

## 7.4 Regla de Ausencia de Evidencia

Si no existen señales emocionales:

Resultado:

Valor cercano a neutralidad.

---

# 8. Cálculo Conceptual

La puntuación puede representarse como combinación de factores:

```
Sentiment Score =
Polaridad
+
Intensidad
+
Contexto
+
Evidencia
```

Cada componente debe mantener trazabilidad.

---

# 9. Resolución de Casos Complejos

## 9.1 Mensajes Mixtos

Ejemplo:

"Gracias por la obra, aunque esperábamos más rapidez."

Resultado:

* sentimiento positivo y negativo;
* puntuación intermedia;
* confianza reducida.

---

## 9.2 Mensajes Sarcásticos

Cuando el significado literal contradice el significado contextual:

Resultado:

* evidencia conservada;
* confianza reducida.

---

## 9.3 Mensajes Breves

Ejemplo:

"Bien."

Resultado:

* señal positiva;
* intensidad limitada por falta de contexto.

---

# 10. Niveles de Confianza

## Alta

La evidencia emocional es clara y consistente.

---

## Media

La puntuación requiere interpretación contextual.

---

## Baja

Existe poca evidencia o conflicto emocional.

---

# 11. Variables Generadas por el Pipeline

Ejemplo conceptual:

```json id="n83p7v"
{
  "sentiment_score": {
    "value": 0.78,
    "label": "positive",
    "confidence": "high",
    "evidence": [
      "excelente trabajo"
    ]
  }
}
```

Estas variables permiten:

* análisis agregado;
* comparación temporal;
* auditoría;
* reproducción.

---

# 12. Integración con el Pipeline Analítico

El marco de puntuación funciona sobre el resultado del modelo de sentimiento.

Flujo:

1. análisis textual;
2. identificación de evidencia emocional;
3. clasificación de sentimiento;
4. cálculo de puntuación;
5. almacenamiento.

El resultado permanece independiente de:

* tema;
* intención;
* entidades;
* emoción específica.

---

# 13. Integración con analysis.json

La estructura analítica puede almacenar:

* puntuación;
* etiqueta;
* evidencia;
* confianza;
* versión del modelo.

Esto permite verificar cómo se obtuvo cada valor.

---

# 14. Versionado del Modelo

El modelo utiliza:

MAJOR.MINOR.PATCH

## MAJOR

Cambios en:

* escala;
* metodología;
* reglas principales.

---

## MINOR

Cambios compatibles:

* nuevos ajustes;
* mejoras de calibración;
* ampliaciones documentales.

---

## PATCH

Correcciones menores:

* errores;
* documentación;
* precisión técnica.

---

# 15. Limitaciones del Modelo

La puntuación de sentimiento no representa:

* nivel de apoyo político;
* intención electoral;
* satisfacción poblacional;
* impacto social.

Una puntuación alta únicamente indica mayor intensidad emocional expresada.

---

# 16. Consideraciones Metodológicas Finales

El Marco de Puntuación de Sentimiento proporciona una representación cuantitativa explicable de señales emocionales presentes en mensajes digitales.

Su propósito es complementar la clasificación cualitativa del sentimiento mediante una escala reproducible y auditable.

El modelo mantiene los principios centrales de MIPA:

* determinismo;
* transparencia;
* evidencia;
* reproducibilidad;
* separación analítica.

---

# 17. Glosario

## Puntuación de Sentimiento

Valor numérico asociado a la intensidad emocional expresada.

## Polaridad

Dirección emocional:

* positiva;
* negativa;
* neutral.

## Intensidad

Fuerza de la expresión emocional.

## Normalización

Proceso de llevar valores a una escala comparable.

## Evidencia

Elemento textual que justifica una puntuación.

## Confianza

Nivel de seguridad asociado al resultado.

---

# 18. Referencias Metodológicas / Bibliografía

* Pang, B., & Lee, L. (2008). *Opinion Mining and Sentiment Analysis*. Foundations and Trends in Information Retrieval.

* Liu, B. (2012). *Sentiment Analysis and Opinion Mining*. Morgan & Claypool Publishers.

* Taboada, M. et al. (2011). *Lexicon-Based Methods for Sentiment Analysis*. Computational Linguistics.

* Jurafsky, D., & Martin, J. H. *Speech and Language Processing*.

* Mohammad, S. M. (2016). *Sentiment Analysis: Detecting Valence, Emotions, and Other Affectual States from Text*.
