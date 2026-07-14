# Appendix/README.md

# Appendix — Marco Metodológico de MIPA

**Versión:** 1.0
**Estado:** Baseline Aprobado
**Proyecto:** MIPA — Motor de Inteligencia Política Auditada

---

# 1. Propósito

El Appendix constituye el **marco metodológico oficial** de MIPA.

Mientras los documentos **000–029** describen la arquitectura, el flujo de procesamiento, los contratos de datos y las reglas de implementación del sistema, este Appendix documenta los fundamentos conceptuales y metodológicos que sustentan los modelos analíticos utilizados por el Pipeline.

Su finalidad es garantizar que cada indicador, clasificación, puntuación y narrativa generados por MIPA sean:

* metodológicamente consistentes;
* auditables;
* reproducibles;
* explicables;
* mantenibles a largo plazo.

Este conjunto de documentos debe entenderse como la referencia normativa para el diseño, evolución y validación de los modelos analíticos del sistema.

---

# 2. Alcance

El Appendix documenta los modelos utilizados por el Pipeline Analítico para transformar datos provenientes de redes sociales en información estructurada que posteriormente será consumida por el Dashboard.

Incluye la definición de:

* modelos conceptuales;
* taxonomías;
* catálogos de clasificación;
* criterios metodológicos;
* modelos de indicadores;
* tablas de normalización;
* referencias bibliográficas;
* limitaciones conocidas;
* ejemplos de implementación;
* listas de verificación para validación.

No describe la implementación técnica del Pipeline ni del Dashboard, ya documentadas en los archivos principales del proyecto.

---

# 3. Relación con la documentación principal

La documentación de MIPA se divide en dos niveles claramente diferenciados.

## Nivel I — Arquitectura e implementación

Corresponde a los documentos:

000–029

Estos documentos describen:

* arquitectura del sistema;
* flujo de procesamiento;
* contratos JSON;
* estructura de bases de datos;
* variables;
* fórmulas;
* reglas de implementación.

Su objetivo es responder la pregunta:

> **¿Cómo funciona MIPA?**

---

## Nivel II — Fundamentación metodológica

Corresponde al presente Appendix.

Su objetivo es responder la pregunta:

> **¿Por qué MIPA analiza la información de esa manera?**

Aquí se documentan las decisiones metodológicas que sustentan los modelos analíticos del sistema.

---

# 4. Filosofía metodológica

MIPA adopta un enfoque de análisis comunicativo.

No busca medir únicamente el sentimiento expresado por la ciudadanía.

Busca modelar el comportamiento comunicativo observado dentro de la conversación pública digital.

En consecuencia, el sistema considera que el sentimiento constituye únicamente una dimensión derivada del proceso analítico y no el eje central de interpretación.

El análisis parte de la identificación del contenido temático y de la intención comunicativa expresada por cada intervención, para posteriormente integrar postura, emoción, intensidad y otras variables necesarias para la construcción de indicadores.

Este enfoque permite representar con mayor fidelidad la complejidad del discurso público y evita reducir la conversación ciudadana a una clasificación binaria o exclusivamente emocional.

---

# 5. Principios rectores

Todos los modelos descritos en este Appendix deberán respetar los siguientes principios.

## 5.1 Determinismo

Toda clasificación realizada por el Pipeline deberá producir el mismo resultado cuando reciba la misma información de entrada.

No se permitirán procesos cuya salida dependa de factores aleatorios o no controlados.

---

## 5.2 Auditabilidad

Cada indicador deberá poder reconstruirse a partir de la evidencia utilizada durante su cálculo.

Todo resultado debe ser verificable.

---

## 5.3 Explicabilidad

Cada decisión analítica deberá poder justificarse mediante reglas metodológicas claramente documentadas.

No se aceptarán clasificaciones imposibles de explicar.

---

## 5.4 Evidencia

Toda conclusión deberá sustentarse en evidencia observable.

Cuando el Dashboard presente una narrativa, ésta deberá poder rastrearse hasta:

* publicaciones;
* comentarios;
* métricas;
* indicadores;
* registros analizados.

---

## 5.5 Separación entre evidencia e interpretación

Los datos observados constituyen evidencia.

Las conclusiones constituyen interpretación.

Ambos niveles deberán permanecer claramente diferenciados durante todo el Pipeline.

---

## 5.6 Responsabilidad única

Cada documento del Appendix documenta un único modelo conceptual.

No deberán duplicarse definiciones entre documentos.

Cuando un modelo dependa de otro, deberá referenciarlo explícitamente.

---

# 6. Principio de trazabilidad

Toda variable generada por MIPA debe poder seguir el siguiente recorrido lógico:

Fuente original

↓

Dato observado

↓

Clasificación

↓

Variable derivada

↓

Indicador

↓

Narrativa

↓

Visualización

En ningún punto del proceso deberá perderse la capacidad de reconstruir el origen del dato.

---

# 7. Uso de literatura especializada

MIPA adopta un enfoque basado en evidencia.

Siempre que exista literatura consolidada sobre un tema, los modelos descritos en este Appendix deberán fundamentarse en:

* investigación científica;
* estándares internacionales;
* marcos conceptuales ampliamente aceptados;
* metodologías reconocidas por la comunidad académica o profesional.

El objetivo no es replicar literalmente dichos modelos, sino utilizarlos como base para una implementación operacional adaptada al contexto de la inteligencia política digital.

---

# 8. Extensiones metodológicas propias

No todos los componentes de MIPA corresponden a modelos existentes en la literatura.

Algunos elementos representan propuestas metodológicas desarrolladas específicamente para este proyecto.

Cuando esto ocurra, el documento correspondiente deberá distinguir claramente entre:

* el marco conceptual de referencia;
* la adaptación realizada por MIPA;
* las reglas propias incorporadas por el sistema.

Esta diferenciación evita atribuir incorrectamente a la literatura científica conceptos que corresponden al diseño específico de MIPA.

---

# 9. Organización del Appendix

El Appendix está compuesto por los siguientes documentos.

| Documento                         | Propósito                                       |
| --------------------------------- | ----------------------------------------------- |
| README.md                         | Introducción general y principios metodológicos |
| A01_COMMUNICATIVE_INTENT_MODEL.md | Modelo de intención comunicativa                |
| A02_TOPIC_TAXONOMY.md             | Taxonomía jerárquica de temas                   |
| A03_POSTURE_CATALOG.md            | Catálogo de posturas comunicativas              |
| A04_EMOTION_CATALOG.md            | Modelo y catálogo emocional                     |
| A05_PULSO_IQ_MODEL.md             | Modelo conceptual de Pulso IQ                   |
| A06_POPULARITY_MODEL.md           | Modelo de Popularidad Digital                   |
| A07_RISK_MODEL.md                 | Modelo multidimensional de riesgo               |
| A08_SCORING_TABLES.md             | Tablas de puntuación                            |
| A09_NORMALIZATION_TABLES.md       | Métodos de normalización                        |
| A10_REFERENCE_PAPERS.md           | Referencias metodológicas                       |
| A11_LIMITATIONS.md                | Alcances y limitaciones del sistema             |
| A12_JSON_EXAMPLES.md              | Ejemplos completos de salida                    |
| A13_VALIDATION_CHECKLIST.md       | Lista oficial de validación metodológica        |

Cada documento aborda un único componente del modelo analítico y debe leerse de forma complementaria con los demás.

---

# 10. Gobernanza metodológica

Las modificaciones metodológicas deberán cumplir las siguientes reglas:

* no alterar la arquitectura aprobada del sistema;
* preservar la compatibilidad con los contratos de datos vigentes;
* mantener la trazabilidad de los indicadores;
* documentar toda modificación conceptual;
* justificar los cambios mediante evidencia técnica o bibliográfica cuando corresponda.

Las actualizaciones deberán conservar la coherencia entre todos los documentos del Appendix.

---

# 11. Convenciones de documentación

Con el fin de mantener consistencia entre documentos, cada archivo del Appendix procurará incluir, cuando sea aplicable:

* propósito;
* alcance;
* definiciones;
* fundamentos conceptuales;
* metodología;
* criterios de clasificación;
* reglas operativas;
* casos límite;
* exclusiones;
* ejemplos;
* limitaciones;
* referencias.

La profundidad de cada documento deberá ser comparable con la documentación principal del proyecto.

---

# 12. Naturaleza normativa

Salvo que se indique expresamente lo contrario, los documentos contenidos en este Appendix tienen carácter normativo para el desarrollo del Pipeline Analítico.

Las implementaciones deberán ajustarse a las definiciones aquí establecidas.

Cuando exista discrepancia entre una implementación y este Appendix, prevalecerá la metodología documentada hasta que una nueva versión oficial la sustituya.

---

# 13. Consideraciones finales

El objetivo de MIPA no es reemplazar el juicio humano, sino proporcionar un marco analítico transparente, reproducible y fundamentado para comprender la conversación pública digital.

El valor del sistema depende tanto de la calidad de sus algoritmos como de la claridad con la que estos pueden ser explicados, auditados y revisados.

Por esta razón, el Appendix constituye una parte esencial de la documentación del proyecto y debe evolucionar con el mismo rigor que el resto de la arquitectura, preservando la coherencia metodológica y la confianza en los resultados generados por el sistema.
