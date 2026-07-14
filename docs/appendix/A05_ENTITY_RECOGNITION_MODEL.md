# A05_ENTITY_RECOGNITION_MODEL.md

# Modelo de Reconocimiento de Entidades

## 1. Introducción

El Modelo de Reconocimiento de Entidades de MIPA define el marco metodológico utilizado para identificar entidades mencionadas dentro de los mensajes digitales analizados.

Este modelo permite determinar los elementos concretos a los cuales hace referencia un contenido, facilitando la organización, trazabilidad y análisis contextual de la información procesada.

El modelo responde exclusivamente a la pregunta:

**¿Qué entidades aparecen mencionadas dentro del mensaje?**

No determina:

* importancia política de una entidad;
* valoración positiva o negativa hacia una entidad;
* intención del autor;
* relación causal entre entidades;
* influencia de una entidad sobre la población.

El reconocimiento de entidades es una tarea descriptiva basada únicamente en evidencia textual observable.

---

# 2. Fundamentos Metodológicos

El reconocimiento de entidades en MIPA se basa en principios de extracción lingüística explicable.

Toda entidad identificada debe estar respaldada por:

* evidencia textual;
* ubicación dentro del mensaje;
* categoría asignada;
* nivel de confianza;
* trazabilidad del procesamiento.

El modelo evita inferencias no verificables y mantiene separación respecto a otras dimensiones analíticas.

---

# 3. Relación con Otros Modelos MIPA

El reconocimiento de entidades constituye una dimensión independiente.

| Modelo                 | Pregunta                                  |
| ---------------------- | ----------------------------------------- |
| Taxonomía Temática     | ¿Sobre qué trata el mensaje?              |
| Intención Comunicativa | ¿Qué busca realizar el mensaje?           |
| Sentimiento            | ¿Cuál es la carga emocional expresada?    |
| Emoción                | ¿Qué emoción aparece?                     |
| Entidades              | ¿Qué elementos concretos son mencionados? |

Ejemplo:

Mensaje:

"Gracias a la alcaldía por reparar la calle del barrio El Carmen."

Resultado:

Entidad:

* Alcaldía de Santa Ana.
* Barrio El Carmen.

Sentimiento:

* Positivo.

Intención:

* Reconocimiento.

Tema:

* Infraestructura pública.

Cada dimensión conserva su independencia metodológica.

---

# 4. Principios del Modelo

## 4.1 Evidencia Explícita

Una entidad debe encontrarse expresamente mencionada dentro del contenido.

No se agregan entidades por:

* conocimiento externo;
* contexto político;
* suposiciones;
* relaciones no escritas.

---

## 4.2 Neutralidad Analítica

El reconocimiento de una entidad no implica valoración.

Ejemplo:

"La alcaldía anunció una nueva obra."

La entidad identificada no recibe clasificación positiva o negativa por aparecer en el mensaje.

---

## 4.3 Conservación de Información

El modelo conserva la forma original de aparición de la entidad para permitir auditoría posterior.

Ejemplo:

Texto original:

"Alcaldía de Santa Ana"

Entidad normalizada:

"Alcaldía de Santa Ana"

---

# 5. Arquitectura del Modelo

El modelo está compuesto por los siguientes componentes.

## 5.1 Entrada del Mensaje

Recibe el texto procesado por el pipeline analítico.

Fuentes:

* publicaciones;
* comentarios;
* respuestas;
* comunicados;
* contenido institucional.

---

## 5.2 Detección de Menciones

El sistema identifica fragmentos textuales que pueden representar entidades.

Ejemplos:

* nombres propios;
* instituciones;
* lugares;
* organizaciones;
* eventos;
* proyectos.

---

## 5.3 Clasificación de Entidades

Cada entidad identificada recibe una categoría metodológica.

Ejemplo:

Texto:

"Parque Libertad"

Clasificación:

Lugar.

---

## 5.4 Normalización

La normalización permite agrupar menciones equivalentes.

Ejemplo:

Variantes:

* "Alcaldía de Santa Ana";
* "la alcaldía santaneca";
* "gobierno municipal".

Proceso:

Conservar evidencia original y asociar una entidad normalizada cuando corresponda.

---

# 6. Tipología de Entidades

MIPA utiliza categorías generales de entidades.

---

## 6.1 Organizaciones

Incluye:

* instituciones públicas;
* organizaciones privadas;
* asociaciones;
* grupos comunitarios.

Ejemplos:

* Alcaldía de Santa Ana.
* Ministerio relacionado.
* Organización comunitaria.

---

## 6.2 Personas

Incluye nombres de individuos identificados explícitamente.

Ejemplo:

"Alcalde Juan Pérez."

Entidad:

Persona.

---

## 6.3 Lugares

Incluye:

* municipios;
* barrios;
* comunidades;
* edificios;
* espacios públicos.

Ejemplo:

"Barrio El Carmen."

Entidad:

Lugar.

---

## 6.4 Infraestructura

Incluye elementos físicos mencionados.

Ejemplos:

* calles;
* parques;
* mercados;
* edificios públicos.

---

## 6.5 Eventos

Incluye actividades o acontecimientos identificables.

Ejemplos:

* jornadas comunitarias;
* inauguraciones;
* reuniones.

---

## 6.6 Programas y Proyectos

Incluye iniciativas con nombre propio o referencia específica.

Ejemplo:

"Programa de recuperación urbana."

---

# 7. Evidencia de Entidades

El modelo utiliza diferentes niveles de evidencia.

## 7.1 Evidencia Directa

La entidad aparece claramente escrita.

Ejemplo:

"Alcaldía de Santa Ana."

---

## 7.2 Evidencia Parcial

La entidad aparece mediante una referencia abreviada.

Ejemplo:

"La municipalidad anunció..."

---

## 7.3 Evidencia Ambigua

La referencia puede corresponder a múltiples entidades.

Ejemplo:

"El gobierno informó..."

Resultado:

Confianza reducida.

---

# 8. Resolución de Ambigüedades

## 8.1 Entidades con el mismo nombre

Cuando una entidad puede corresponder a múltiples elementos, el sistema conserva:

* texto original;
* posibles coincidencias;
* nivel de confianza.

---

## 8.2 Referencias Genéricas

Expresiones como:

* gobierno;
* municipio;
* institución;

requieren evidencia contextual adicional.

---

## 8.3 Variaciones Lingüísticas

Ejemplo:

* "alcaldía";
* "municipalidad";
* "gobierno local".

Estas expresiones pueden relacionarse únicamente cuando existe evidencia suficiente.

---

# 9. Relaciones entre Entidades

El modelo puede conservar relaciones explícitas entre entidades.

Ejemplo:

Mensaje:

"La alcaldía entregó una obra en el barrio El Carmen."

Entidades:

* Alcaldía de Santa Ana.
* Barrio El Carmen.

Relación observable:

Institución → Acción → Lugar.

El modelo no interpreta:

* impacto;
* éxito;
* aprobación.

---

# 10. Niveles de Confianza

## Alta

La entidad aparece claramente identificada.

---

## Media

La entidad requiere interpretación contextual limitada.

---

## Baja

La referencia es incompleta o ambigua.

---

# 11. Variables Generadas por el Pipeline

El modelo genera variables analíticas como:

```json id="p7v31k"
{
  "entities": [
    {
      "text": "Alcaldía de Santa Ana",
      "type": "organization",
      "confidence": "high"
    },
    {
      "text": "Barrio El Carmen",
      "type": "location",
      "confidence": "high"
    }
  ]
}
```

Estas variables permiten:

* auditoría;
* agrupación analítica;
* trazabilidad;
* análisis relacional descriptivo.

---

# 12. Integración con el Pipeline Analítico

El reconocimiento de entidades se integra como módulo independiente.

Flujo:

1. recepción del contenido;
2. procesamiento lingüístico;
3. detección de entidades;
4. clasificación;
5. normalización;
6. almacenamiento.

El resultado puede combinarse con:

* temas;
* sentimientos;
* emociones;
* intención.

Sin modificar la independencia de cada dimensión.

---

# 13. Integración con analysis.json

La información de entidades puede almacenarse incluyendo:

* texto detectado;
* tipo de entidad;
* forma normalizada;
* confianza;
* evidencia textual;
* versión del modelo.

Esto permite reconstruir cómo fue generado cada resultado.

---

# 14. Versionado del Modelo

El modelo utiliza:

MAJOR.MINOR.PATCH

## MAJOR

Cambios fundamentales:

* categorías;
* reglas principales;
* estructura de salida.

---

## MINOR

Cambios compatibles:

* nuevas categorías;
* ampliación de reglas;
* mejoras metodológicas.

---

## PATCH

Correcciones menores:

* documentación;
* errores;
* ajustes técnicos.

---

# 15. Limitaciones del Modelo

El modelo no determina:

* importancia de una entidad;
* popularidad;
* aprobación ciudadana;
* influencia política;
* relación causal.

Solo identifica entidades mencionadas explícitamente.

---

# 16. Consideraciones Metodológicas Finales

El Reconocimiento de Entidades dentro de MIPA constituye una capa descriptiva destinada a preservar los elementos concretos presentes en la comunicación digital.

Su función es aportar estructura y trazabilidad al análisis sin introducir interpretaciones externas.

El modelo mantiene los principios fundamentales del sistema:

* determinismo;
* explicabilidad;
* reproducibilidad;
* independencia analítica;
* auditoría.

---

# 17. Glosario

## Entidad

Elemento identificable mencionado dentro de un mensaje.

## Mención

Fragmento textual donde aparece una entidad.

## Normalización

Proceso de agrupación de variantes que representan una misma entidad.

## Tipo de Entidad

Categoría asignada a una entidad reconocida.

## Evidencia

Fragmento textual que respalda una identificación.

## Confianza

Nivel de seguridad asociado al reconocimiento.

---

# 18. Referencias Metodológicas / Bibliografía

* Grishman, R., & Sundheim, B. (1996). *Message Understanding Conference-6: A Brief History*.

* Nadeau, D., & Sekine, S. (2007). *A Survey of Named Entity Recognition and Classification*. Linguisticae Investigationes.

* Jurafsky, D., & Martin, J. H. *Speech and Language Processing*.

* Manning, C. D., Raghavan, P., & Schütze, H. (2008). *Introduction to Information Retrieval*.

* Bird, S., Klein, E., & Loper, E. (2009). *Natural Language Processing with Python*.
