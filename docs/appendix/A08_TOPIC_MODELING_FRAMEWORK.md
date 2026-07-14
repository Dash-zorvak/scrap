# A08_TOPIC_MODELING_FRAMEWORK.md

# Marco Metodológico de Modelado Temático

## 1. Introducción

El Marco de Modelado Temático de MIPA define los principios metodológicos utilizados para identificar, organizar y representar patrones temáticos dentro de los mensajes digitales analizados.

Este marco establece la base conceptual para la agrupación de contenidos por similitud temática y complementa el Modelo de Taxonomía Temática definido en **A02_TAXONOMY_MODEL.md**.

El modelo responde exclusivamente a la pregunta:

**¿Qué conjuntos de conceptos aparecen relacionados dentro del contenido analizado?**

El modelado temático permite descubrir estructuras recurrentes dentro de los datos, pero no reemplaza la clasificación taxonómica manual o determinista utilizada por MIPA.

---

# 2. Fundamentos Metodológicos

El modelado temático en MIPA se fundamenta en principios de análisis de contenido explicable.

Los resultados deben mantener:

* evidencia textual;
* criterios de agrupación;
* representación conceptual;
* nivel de confianza;
* trazabilidad.

El modelo no interpreta:

* intención política;
* aceptación ciudadana;
* preferencias electorales;
* motivaciones internas.

Su función es exclusivamente descriptiva.

---

# 3. Relación con la Taxonomía Temática

El modelado temático y la taxonomía temática cumplen funciones diferentes.

| Modelo             | Función                                                         |
| ------------------ | --------------------------------------------------------------- |
| Taxonomía Temática | Clasificar contenido dentro de categorías definidas previamente |
| Modelado Temático  | Identificar agrupaciones conceptuales emergentes                |

Ejemplo:

Conjunto de mensajes:

* reparación de calles;
* mantenimiento vial;
* construcción de caminos.

Modelado temático:

Tema emergente:

Infraestructura vial.

Taxonomía:

Categoría asignada:

Infraestructura Pública.

Ambos resultados pueden coexistir sin reemplazarse.

---

# 4. Principios del Modelo

## 4.1 Descubrimiento Controlado

El modelo identifica patrones presentes en los datos sin imponer interpretaciones externas.

---

## 4.2 Evidencia Documental

Cada tema identificado debe relacionarse con:

* términos representativos;
* mensajes asociados;
* evidencia textual.

---

## 4.3 Separación Conceptual

Un tema identificado no implica:

* aprobación;
* rechazo;
* intención;
* importancia política.

---

## 4.4 Reproducibilidad

Los mismos datos y parámetros deben permitir reconstruir resultados equivalentes.

---

# 5. Arquitectura del Modelado Temático

El proceso está compuesto por varias etapas.

---

# 5.1 Preparación del Corpus

Incluye:

* recopilación de mensajes;
* limpieza textual;
* normalización;
* segmentación.

El corpus debe conservar trazabilidad respecto a sus fuentes.

---

# 5.2 Representación Textual

Los documentos son transformados en representaciones analizables.

Puede incluir:

* términos;
* frecuencias;
* relaciones semánticas;
* vectores lingüísticos.

---

# 5.3 Identificación de Agrupaciones

El modelo busca relaciones entre documentos o términos.

Los criterios pueden incluir:

* similitud léxica;
* proximidad semántica;
* coexistencia de términos.

---

# 5.4 Interpretación Documentada

Cada agrupación identificada debe recibir una descripción basada en evidencia.

La interpretación no puede superar lo observado en los datos.

---

# 6. Tipos de Modelos Temáticos

## 6.1 Modelos Basados en Frecuencia

Analizan aparición y distribución de términos.

Ejemplos:

* frecuencia de palabras;
* términos predominantes;
* asociaciones.

---

## 6.2 Modelos Basados en Distribución Estadística

Identifican patrones mediante distribución de palabras dentro del corpus.

Ejemplo:

* modelos probabilísticos de tópicos.

---

## 6.3 Modelos Basados en Representación Semántica

Utilizan relaciones de significado entre términos y documentos.

Ejemplo:

* representaciones vectoriales.

---

# 7. Representación de Temas

Un tema identificado puede representarse mediante:

* nombre descriptivo;
* palabras asociadas;
* documentos relacionados;
* evidencia textual.

Ejemplo conceptual:

```json id="h72m4k"
{
  "topic": "Infraestructura comunitaria",
  "keywords": [
    "calles",
    "reparación",
    "obras"
  ],
  "confidence": "high"
}
```

---

# 8. Relación entre Temas

Los temas pueden presentar relaciones.

Ejemplo:

Tema principal:

Infraestructura.

Temas relacionados:

* transporte;
* servicios públicos;
* desarrollo urbano.

Estas relaciones son descriptivas y no representan causalidad.

---

# 9. Resolución de Ambigüedades Temáticas

## 9.1 Términos Compartidos

Algunos términos pueden aparecer en diferentes contextos.

Ejemplo:

"Proyecto"

Puede relacionarse con:

* infraestructura;
* educación;
* desarrollo social.

---

## 9.2 Temas Superpuestos

Un mensaje puede pertenecer a múltiples agrupaciones.

Ejemplo:

"Construcción de escuela comunitaria."

Temas:

* educación;
* infraestructura.

---

## 9.3 Baja Evidencia

Cuando existe poca información:

Resultado:

* tema incierto;
* menor confianza.

---

# 10. Integración con Clasificación Temática

El modelado temático funciona como complemento analítico.

Flujo:

1. identificación de patrones;
2. generación de agrupaciones;
3. revisión metodológica;
4. relación con taxonomía existente.

El modelo no modifica automáticamente categorías oficiales sin evidencia metodológica documentada.

---

# 11. Niveles de Confianza

## Alta

El tema presenta términos consistentes y evidencia suficiente.

---

## Media

Existe relación conceptual pero con variabilidad.

---

## Baja

La agrupación tiene evidencia limitada.

---

# 12. Variables Generadas por el Pipeline

El modelo puede generar variables como:

```json id="v91q2d"
{
  "topics": [
    {
      "name": "Infraestructura",
      "keywords": [
        "calles",
        "obras"
      ],
      "confidence": "high"
    }
  ]
}
```

Estas variables permiten:

* exploración;
* análisis agregado;
* auditoría;
* comparación temporal.

---

# 13. Integración con el Pipeline Analítico

El modelado temático se integra como una capa complementaria.

Flujo general:

1. carga del contenido;
2. procesamiento lingüístico;
3. extracción de características;
4. identificación temática;
5. almacenamiento.

Mantiene independencia respecto a:

* sentimiento;
* emoción;
* intención;
* entidades.

---

# 14. Integración con analysis.json

Los resultados pueden incluir:

* identificador del tema;
* descripción;
* términos asociados;
* evidencia;
* confianza;
* versión del modelo.

Esto permite reconstruir el proceso analítico.

---

# 15. Versionado del Modelo

El modelo utiliza:

MAJOR.MINOR.PATCH

## MAJOR

Cambios estructurales:

* metodología;
* representación;
* interpretación principal.

---

## MINOR

Cambios compatibles:

* nuevos criterios;
* ajustes de agrupación;
* mejoras documentales.

---

## PATCH

Correcciones menores:

* errores;
* documentación;
* ajustes técnicos.

---

# 16. Limitaciones del Modelo

El modelado temático no determina:

* importancia política;
* relevancia ciudadana;
* popularidad;
* intención electoral.

Los temas identificados representan patrones presentes en el contenido analizado.

---

# 17. Consideraciones Metodológicas Finales

El Modelado Temático dentro de MIPA proporciona una herramienta de exploración y descubrimiento estructurado de patrones conceptuales.

Su función es complementar la clasificación temática determinista mediante una perspectiva descriptiva adicional.

El modelo mantiene los principios fundamentales del sistema:

* evidencia;
* transparencia;
* reproducibilidad;
* auditoría;
* separación analítica.

---

# 18. Glosario

## Tema

Conjunto de conceptos relacionados dentro de un corpus textual.

## Modelado Temático

Proceso de identificación de agrupaciones conceptuales en documentos.

## Corpus

Conjunto de documentos analizados.

## Agrupación

Conjunto de elementos relacionados por similitud.

## Representación Semántica

Forma de representar relaciones de significado.

## Evidencia Temática

Elementos textuales que respaldan un tema.

---

# 19. Referencias Metodológicas / Bibliografía

* Blei, D. M., Ng, A. Y., & Jordan, M. I. (2003). *Latent Dirichlet Allocation*.

* Deerwester, S. et al. (1990). *Indexing by Latent Semantic Analysis*.

* Manning, C. D., Raghavan, P., & Schütze, H. (2008). *Introduction to Information Retrieval*.

* Jurafsky, D., & Martin, J. H. *Speech and Language Processing*.

* Griffiths, T. L., & Steyvers, M. (2004). *Finding scientific topics*.
