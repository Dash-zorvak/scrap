# A10_MESSAGE_STRUCTURE_MODEL.md

# Modelo de Estructura del Mensaje

## 1. Introducción

El Modelo de Estructura del Mensaje de MIPA define el marco metodológico utilizado para identificar y representar la organización interna de los mensajes digitales analizados.

Este modelo permite describir cómo está construido un mensaje desde una perspectiva estructural, identificando sus componentes lingüísticos y comunicativos principales.

El modelo responde exclusivamente a la pregunta:

**¿Cómo está organizado internamente el mensaje?**

El análisis estructural no determina:

* intención real del autor;
* sentimiento;
* importancia política;
* aceptación ciudadana;
* impacto comunicativo.

Su función es descriptiva y se basa en elementos observables dentro del contenido textual.

---

# 2. Fundamentos Metodológicos

El análisis de estructura del mensaje en MIPA se fundamenta en principios de análisis lingüístico y comunicación textual.

Cada resultado debe conservar:

* elementos estructurales identificados;
* evidencia textual;
* reglas aplicadas;
* nivel de confianza;
* trazabilidad.

El modelo busca representar la composición del mensaje sin introducir interpretaciones externas.

---

# 3. Relación con Otros Modelos MIPA

La estructura del mensaje representa una dimensión independiente.

| Modelo                 | Pregunta                                |
| ---------------------- | --------------------------------------- |
| Estructura del Mensaje | ¿Cómo está construido el mensaje?       |
| Análisis Lingüístico   | ¿Qué características tiene el lenguaje? |
| Intención Comunicativa | ¿Qué busca realizar?                    |
| Contenido              | ¿Qué tipo de mensaje es?                |
| Sentimiento            | ¿Qué carga emocional expresa?           |

Ejemplo:

Mensaje:

"Invitamos a los vecinos a participar en la jornada de limpieza del parque este sábado."

Estructura:

* apertura convocante;
* actor receptor;
* acción solicitada;
* referencia temporal;
* objetivo comunitario.

---

# 4. Principios del Modelo

## 4.1 Observación Estructural

El modelo identifica componentes presentes dentro del mensaje.

No utiliza:

* información externa;
* perfil del autor;
* contexto político no escrito.

---

## 4.2 Representación Jerárquica

Los mensajes pueden dividirse en componentes relacionados.

Ejemplo:

Mensaje:

"Informamos que la alcaldía iniciará la construcción del parque comunitario."

Estructura:

Actor:

Alcaldía.

Acción:

Iniciar construcción.

Objeto:

Parque comunitario.

---

## 4.3 Neutralidad Analítica

La estructura describe la composición del mensaje.

No determina:

* calidad;
* efectividad;
* intención oculta.

---

## 4.4 Reproducibilidad

La aplicación de las mismas reglas debe producir resultados equivalentes.

---

# 5. Arquitectura del Modelo

El análisis estructural está compuesto por varias capas.

---

# 5.1 Segmentación del Mensaje

El mensaje puede dividirse en:

* frases;
* oraciones;
* unidades informativas.

---

# 5.2 Identificación de Componentes

El modelo identifica elementos como:

* actor;
* acción;
* objeto;
* contexto;
* tiempo;
* ubicación;
* audiencia.

---

# 5.3 Representación Estructural

Los componentes identificados se organizan en una representación descriptiva.

Ejemplo:

```json id="z82k5m"
{
  "structure": {
    "actor": "Alcaldía de Santa Ana",
    "action": "realizar",
    "object": "jornada comunitaria",
    "location": "Barrio Central",
    "confidence": "high"
  }
}
```

---

# 6. Componentes del Mensaje

## 6.1 Actor o Participante

Identifica quién realiza o aparece relacionado con una acción.

Ejemplos:

* institución;
* comunidad;
* persona;
* organización.

---

## 6.2 Acción

Representa el evento o actividad expresada mediante verbos.

Ejemplos:

* informar;
* construir;
* solicitar;
* mejorar.

---

## 6.3 Objeto

Representa aquello sobre lo cual recae la acción.

Ejemplos:

* obra;
* servicio;
* actividad;
* problema.

---

## 6.4 Beneficiario o Audiencia

Identifica a quién se dirige o afecta el mensaje.

Ejemplos:

* vecinos;
* comunidad;
* usuarios.

---

## 6.5 Contexto Temporal

Incluye referencias de tiempo.

Ejemplos:

* fechas;
* períodos;
* momentos específicos.

---

## 6.6 Contexto Territorial

Incluye referencias geográficas.

Ejemplos:

* barrios;
* comunidades;
* municipios.

---

# 7. Tipos de Estructura Comunicativa

## 7.1 Estructura Informativa

Características:

* transmisión de datos;
* descripción de hechos;
* comunicación institucional.

Ejemplo:

"La alcaldía entregó la obra terminada."

---

## 7.2 Estructura Convocante

Características:

* llamada a participación;
* invitación;
* acción dirigida a audiencia.

Ejemplo:

"Participa en la jornada comunitaria."

---

## 7.3 Estructura Solicitud

Características:

* petición;
* requerimiento;
* demanda de acción.

Ejemplo:

"Solicitamos reparación de la calle."

---

## 7.4 Estructura Evaluativa

Características:

* valoración;
* comparación;
* opinión.

Ejemplo:

"El proyecto representa una mejora importante."

---

## 7.5 Estructura Reclamativa

Características:

* señalamiento de problema;
* inconformidad;
* necesidad de respuesta.

Ejemplo:

"La comunidad continúa esperando solución."

---

# 8. Relaciones Internas del Mensaje

El modelo puede representar relaciones entre componentes.

Ejemplo:

Mensaje:

"La alcaldía reparó la calle principal del barrio."

Relación:

Actor:

Alcaldía.

Acción:

Reparó.

Objeto:

Calle principal.

Ubicación:

Barrio.

Estas relaciones son descriptivas y no implican causalidad externa.

---

# 9. Resolución de Ambigüedades Estructurales

## 9.1 Actor No Identificado

Cuando no existe sujeto explícito:

Resultado:

Actor desconocido.

---

## 9.2 Acción Ambigua

Cuando el verbo no permite determinar claramente la acción:

Resultado:

Clasificación reducida.

---

## 9.3 Mensajes Incompletos

Mensajes breves pueden contener estructuras parciales.

Ejemplo:

"Necesitamos ayuda."

Componentes:

Acción:

Solicitud.

Objeto:

No especificado.

---

# 10. Niveles de Confianza

## Alta

La estructura presenta componentes claramente identificables.

---

## Media

Existen componentes reconocibles con información parcial.

---

## Baja

La estructura es incompleta o ambigua.

---

# 11. Variables Generadas por el Pipeline

Ejemplo conceptual:

```json id="q73n8v"
{
  "message_structure": {
    "type": "informational",
    "components": {
      "actor": "municipalidad",
      "action": "informar",
      "object": "actividad"
    },
    "confidence": "medium"
  }
}
```

Estas variables permiten:

* análisis estructural;
* auditoría;
* comparación;
* trazabilidad.

---

# 12. Integración con el Pipeline Analítico

El modelo funciona como una capa descriptiva del procesamiento textual.

Flujo:

1. recepción del mensaje;
2. segmentación;
3. identificación estructural;
4. extracción de componentes;
5. generación de variables;
6. almacenamiento.

Mantiene independencia respecto a:

* tema;
* intención;
* sentimiento;
* emoción.

---

# 13. Integración con analysis.json

Los resultados pueden incluir:

* tipo estructural;
* componentes identificados;
* relaciones internas;
* evidencia;
* confianza;
* versión metodológica.

Esto permite reconstruir la interpretación estructural.

---

# 14. Versionado del Modelo

El modelo utiliza:

MAJOR.MINOR.PATCH

## MAJOR

Cambios en:

* estructura del modelo;
* componentes principales;
* reglas fundamentales.

---

## MINOR

Cambios compatibles:

* nuevos componentes;
* nuevas categorías;
* ampliaciones metodológicas.

---

## PATCH

Correcciones menores:

* documentación;
* errores;
* ajustes técnicos.

---

# 15. Limitaciones del Modelo

El análisis estructural no determina:

* intención oculta;
* significado político;
* verdad del contenido;
* influencia del mensaje.

Solo representa la organización observable del texto.

---

# 16. Consideraciones Metodológicas Finales

El Modelo de Estructura del Mensaje proporciona una representación formal de la composición interna del contenido digital analizado.

Su función es facilitar la trazabilidad y comprensión del mensaje mediante elementos observables.

El modelo mantiene los principios fundamentales de MIPA:

* determinismo;
* explicabilidad;
* reproducibilidad;
* independencia analítica;
* auditoría.

---

# 17. Glosario

## Estructura del Mensaje

Organización interna de los componentes comunicativos de un texto.

## Componente

Elemento identificable dentro de la estructura del mensaje.

## Actor

Entidad que realiza o participa en una acción.

## Acción

Evento expresado mediante una forma verbal.

## Objeto

Elemento relacionado con una acción.

## Evidencia Estructural

Fragmento textual que respalda una representación.

---

# 18. Referencias Metodológicas / Bibliografía

* Halliday, M. A. K. (1994). *An Introduction to Functional Grammar*.

* Chomsky, N. (1965). *Aspects of the Theory of Syntax*.

* Jurafsky, D., & Martin, J. H. *Speech and Language Processing*.

* Manning, C. D., & Schütze, H. (1999). *Foundations of Statistical Natural Language Processing*.

* van Dijk, T. A. (1980). *Macrostructures: An Interdisciplinary Study of Global Structures in Discourse*.
