# A07_KEYWORD_EXTRACTION_MODEL.md

# Modelo de Extracción de Palabras Clave

## 1. Introducción

El Modelo de Extracción de Palabras Clave de MIPA define el marco metodológico utilizado para identificar términos relevantes dentro de los mensajes digitales analizados.

Este modelo permite reducir un contenido textual a un conjunto de elementos lingüísticos representativos que facilitan la exploración, clasificación y análisis posterior de la información.

El modelo responde exclusivamente a la pregunta:

**¿Cuáles son los términos más representativos dentro del mensaje?**

No determina:

* importancia política de un término;
* intención del autor;
* relevancia social;
* aprobación ciudadana;
* impacto comunicativo.

La extracción de palabras clave constituye una operación descriptiva basada en evidencia textual observable.

---

# 2. Fundamentos Metodológicos

La extracción de palabras clave en MIPA se fundamenta en técnicas de análisis lingüístico explicable.

Cada palabra clave identificada debe conservar:

* término extraído;
* evidencia textual;
* criterio de selección;
* puntuación asignada;
* nivel de confianza;
* trazabilidad.

El modelo evita seleccionar términos mediante criterios ocultos o interpretaciones externas.

---

# 3. Relación con Otros Modelos MIPA

La extracción de palabras clave funciona como una dimensión auxiliar dentro del sistema.

| Modelo                 | Pregunta                                |
| ---------------------- | --------------------------------------- |
| Palabras Clave         | ¿Qué términos representan el contenido? |
| Taxonomía Temática     | ¿Sobre qué trata el mensaje?            |
| Entidades              | ¿Qué elementos concretos aparecen?      |
| Intención Comunicativa | ¿Qué busca realizar?                    |
| Sentimiento            | ¿Cuál es la carga emocional?            |

Ejemplo:

Mensaje:

"La alcaldía inicia proyecto de recuperación del parque central."

Palabras clave:

* alcaldía;
* proyecto;
* recuperación;
* parque.

Tema:

* infraestructura pública.

Entidades:

* Alcaldía de Santa Ana.
* Parque Central.

---

# 4. Principios del Modelo

## 4.1 Representatividad Textual

Una palabra clave debe representar información relevante contenida en el mensaje.

---

## 4.2 Observabilidad

El término debe estar presente dentro del contenido analizado.

No se generan palabras clave a partir de:

* conocimiento externo;
* interpretación política;
* inferencias.

---

## 4.3 Reducción Informativa Controlada

El modelo busca reducir complejidad textual conservando información relevante.

---

## 4.4 Explicabilidad

Cada palabra clave debe poder rastrearse hasta el fragmento textual donde aparece.

---

# 5. Arquitectura del Modelo

El modelo está compuesto por las siguientes etapas:

---

# 5.1 Preprocesamiento del Texto

Incluye:

* limpieza;
* normalización;
* eliminación de ruido textual;
* segmentación.

---

# 5.2 Identificación de Candidatos

Se generan candidatos a partir de:

* sustantivos;
* grupos nominales;
* términos frecuentes;
* expresiones relevantes.

Ejemplo:

Texto:

"Construcción de nueva unidad de salud comunitaria."

Candidatos:

* construcción;
* unidad de salud;
* salud comunitaria.

---

# 5.3 Evaluación de Relevancia

Cada candidato puede evaluarse mediante criterios como:

* frecuencia;
* especificidad;
* posición dentro del texto;
* relación semántica;
* importancia contextual.

---

# 5.4 Selección Final

El sistema conserva los términos con mayor representación informativa.

---

# 6. Criterios de Selección de Palabras Clave

## 6.1 Frecuencia de Aparición

Los términos repetidos pueden representar conceptos centrales.

Sin embargo, la frecuencia por sí sola no determina relevancia.

---

## 6.2 Especificidad

Los términos específicos tienen mayor capacidad descriptiva.

Ejemplo:

Mayor especificidad:

"reparación de calles"

Menor especificidad:

"actividad"

---

## 6.3 Relevancia Contextual

Un término puede ser importante aunque aparezca pocas veces.

Ejemplo:

Nombre de un proyecto específico.

---

## 6.4 Valor Semántico

Los términos seleccionados deben aportar significado al contenido.

---

# 7. Tipos de Palabras Clave

## 7.1 Conceptuales

Representan ideas generales.

Ejemplos:

* educación;
* seguridad;
* salud.

---

## 7.2 Institucionales

Relacionadas con organizaciones o actores.

Ejemplos:

* alcaldía;
* municipalidad.

---

## 7.3 Territoriales

Relacionadas con lugares.

Ejemplos:

* barrio;
* comunidad;
* municipio.

---

## 7.4 Accionales

Representan acciones.

Ejemplos:

* construcción;
* reparación;
* entrega.

---

## 7.5 Temporales

Representan referencias de tiempo.

Ejemplos:

* aniversario;
* próximo;
* inicio.

---

# 8. Normalización de Términos

La normalización permite agrupar variantes lingüísticas.

Ejemplo:

Variantes:

* "calles dañadas";
* "reparación vial";
* "mejoramiento de calles".

Concepto relacionado:

Infraestructura vial.

La normalización conserva:

* término original;
* término agrupado;
* relación establecida.

---

# 9. Resolución de Ambigüedades

## 9.1 Términos Genéricos

Palabras como:

* cosa;
* actividad;
* situación;

poseen bajo valor descriptivo.

---

## 9.2 Polisemia

Una palabra puede tener múltiples significados.

Ejemplo:

"Proyecto"

Puede referirse a:

* obra pública;
* iniciativa;
* planificación.

---

## 9.3 Contexto Insuficiente

Mensajes cortos pueden producir pocas palabras clave confiables.

---

# 10. Puntuación de Palabras Clave

El modelo puede asignar puntuaciones considerando:

* frecuencia;
* especificidad;
* relación contextual;
* presencia estructural.

Ejemplo conceptual:

```json id="x83m2q"
{
  "keyword": "infraestructura vial",
  "score": 0.87,
  "evidence": [
    "reparación de calles"
  ],
  "confidence": "high"
}
```

---

# 11. Niveles de Confianza

## Alta

El término representa claramente el contenido principal.

---

## Media

El término tiene relevancia probable pero puede depender del contexto.

---

## Baja

El término aparece con poca evidencia representativa.

---

# 12. Variables Generadas por el Pipeline

El modelo genera variables como:

```json id="b92k7z"
{
  "keywords": [
    {
      "term": "parque",
      "score": 0.81,
      "confidence": "high"
    },
    {
      "term": "comunidad",
      "score": 0.66,
      "confidence": "medium"
    }
  ]
}
```

Estas variables permiten:

* búsqueda;
* agrupación;
* análisis descriptivo;
* trazabilidad.

---

# 13. Integración con el Pipeline Analítico

La extracción de palabras clave funciona como módulo auxiliar.

Flujo:

1. recepción del mensaje;
2. procesamiento lingüístico;
3. extracción de candidatos;
4. evaluación;
5. generación de palabras clave;
6. almacenamiento.

El módulo no sustituye:

* clasificación temática;
* reconocimiento de entidades;
* análisis emocional.

---

# 14. Integración con analysis.json

La información almacenada puede incluir:

* término;
* puntuación;
* evidencia;
* confianza;
* versión del modelo.

Esto permite reconstruir el origen de cada palabra clave.

---

# 15. Versionado del Modelo

El modelo utiliza:

MAJOR.MINOR.PATCH

## MAJOR

Cambios fundamentales en:

* criterios principales;
* estructura de salida;
* metodología.

---

## MINOR

Cambios compatibles:

* nuevos criterios;
* ampliación de vocabulario;
* ajustes metodológicos.

---

## PATCH

Correcciones menores:

* errores;
* documentación;
* ajustes técnicos.

---

# 16. Limitaciones del Modelo

El modelo no determina:

* relevancia política;
* importancia social;
* intención del usuario;
* impacto comunicativo.

Una palabra clave únicamente representa presencia y relevancia textual.

---

# 17. Consideraciones Metodológicas Finales

El Modelo de Extracción de Palabras Clave proporciona una representación compacta y explicable del contenido textual analizado.

Su función es facilitar la exploración y organización de información manteniendo los principios fundamentales de MIPA:

* determinismo;
* transparencia;
* reproducibilidad;
* trazabilidad;
* independencia analítica.

---

# 18. Glosario

## Palabra Clave

Término seleccionado por su capacidad representativa dentro de un mensaje.

## Candidato

Término evaluado antes de ser seleccionado.

## Relevancia

Capacidad de representar información significativa del contenido.

## Normalización

Proceso de agrupación de variantes lingüísticas equivalentes.

## Puntuación

Valor asignado según criterios definidos.

## Evidencia

Fragmento textual que respalda la selección.

---

# 19. Referencias Metodológicas / Bibliografía

* Salton, G., & Buckley, C. (1988). *Term-weighting approaches in automatic text retrieval*.

* Manning, C. D., Raghavan, P., & Schütze, H. (2008). *Introduction to Information Retrieval*.

* Mihalcea, R., & Tarau, P. (2004). *TextRank: Bringing Order into Texts*.

* Jurafsky, D., & Martin, J. H. *Speech and Language Processing*.

* Turney, P. D. (2002). *Learning Algorithms for Keyphrase Extraction*.
