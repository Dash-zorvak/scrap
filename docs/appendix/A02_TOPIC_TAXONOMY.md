# A02. Modelo de Taxonomía Temática

## 0. Propósito del Documento

El presente documento define el **Modelo de Taxonomía Temática** utilizado por el Motor de Inteligencia Política Auditada (MIPA) para identificar, clasificar y organizar los temas presentes en los documentos procesados por el Pipeline.

Su objetivo es establecer un marco metodológico completamente determinista, reproducible y auditable para la clasificación temática de contenido digital relacionado con instituciones públicas, garantizando que cada asignación pueda explicarse mediante evidencia observable y reglas explícitas.

La taxonomía constituye el componente encargado de responder a la pregunta:

> **¿Sobre qué tema trata el documento?**

Esta clasificación es independiente del análisis de intención comunicativa descrito en el documento **A01_COMMUNICATIVE_INTENT_MODEL.md**, aunque ambos modelos operan de manera complementaria durante el procesamiento analítico.

---

# 1. Introducción

El análisis temático representa uno de los componentes fundamentales del Pipeline de MIPA, ya que permite organizar grandes volúmenes de información en categorías homogéneas para facilitar su interpretación, agregación estadística y visualización.

A diferencia de los enfoques basados exclusivamente en palabras clave o modelos probabilísticos de clasificación, la metodología adoptada por MIPA combina una taxonomía jerárquica previamente definida con un sistema de identificación de evidencias temáticas sustentado en reglas deterministas.

Este enfoque permite clasificar documentos de forma consistente, transparente y verificable, evitando decisiones opacas o dependientes de procesos de inferencia no explicables.

El modelo reconoce que un mismo documento puede abordar simultáneamente varios asuntos de interés. Por ello, el Pipeline admite la asignación de un **Tema Principal** y múltiples **Temas Secundarios**, siempre que cada uno se encuentre respaldado por evidencia suficiente e independiente.

La clasificación temática obtenida constituye un insumo esencial para la generación de indicadores, series temporales, análisis territoriales, paneles ejecutivos y procesos de inteligencia institucional.

---

# 2. Alcance

El presente modelo aplica a todos los documentos procesados por el Pipeline de MIPA, independientemente de su origen o formato textual.

Entre otros, comprende:

- publicaciones en redes sociales;
- comentarios;
- respuestas;
- comunicados oficiales;
- notas periodísticas;
- transcripciones;
- documentos institucionales;
- cualquier contenido textual incorporado al proceso de análisis.

El modelo define exclusivamente la metodología para identificar el contenido temático de los documentos.

No evalúa:

- intención comunicativa;
- sentimiento;
- postura política;
- veracidad de los hechos;
- impacto electoral;
- credibilidad del emisor.

Estos componentes son abordados por otros módulos metodológicos del sistema.

---

# 3. Principios Metodológicos

El Modelo de Taxonomía Temática se fundamenta en los siguientes principios:

1. Todo tema deberá sustentarse en evidencia observable.
2. La clasificación será completamente determinista.
3. No se realizarán inferencias sobre información ausente.
4. Los temas podrán coexistir cuando exista evidencia suficiente.
5. La estructura temática será jerárquica y mutuamente consistente.
6. Toda clasificación deberá poder auditarse.
7. Las reglas de clasificación permanecerán explícitamente documentadas.
8. El modelo deberá ser reproducible bajo las mismas condiciones analíticas.
9. La taxonomía será independiente del análisis de intención comunicativa.
10. Toda modificación futura deberá sujetarse al esquema oficial de versionado.

---

# 4. Definiciones

Para efectos del presente documento se adoptan las siguientes definiciones operativas:

**Tema**

Categoría temática de primer nivel que representa un área general de contenido tratada en un documento.

**Subtema**

Categoría temática derivada de un tema principal que permite una clasificación más específica.

**Microtema**

Nivel más granular de la taxonomía utilizado para describir aspectos concretos dentro de un subtema.

**Clasificación temática**

Proceso mediante el cual un documento es asociado a uno o más temas utilizando evidencia verificable.

**Tema principal**

Tema que concentra la mayor cantidad y calidad de evidencia temática dentro del documento.

**Tema secundario**

Tema adicional identificado mediante evidencia independiente de la utilizada para justificar el tema principal.

**Evidencia temática**

Elemento lingüístico, semántico o contextual que respalda objetivamente la asignación de un tema específico.

Las definiciones adicionales serán desarrolladas en el glosario del presente documento.

---

# 5. Modelo Conceptual de la Taxonomía

## 5.1 Propósito del Modelo Conceptual

El Modelo Conceptual de la Taxonomía define la estructura lógica utilizada por el Pipeline para organizar, representar y clasificar los temas identificados dentro de los documentos procesados.

Su función principal es establecer una relación jerárquica entre diferentes niveles de especificidad temática, permitiendo que un mismo contenido pueda ser analizado desde una perspectiva general y posteriormente profundizado mediante categorías más específicas.

La taxonomía no representa una interpretación subjetiva del contenido, sino una estructura metodológica diseñada para ordenar información observable bajo criterios previamente definidos.

---

# 5.2 Principios del Modelo Conceptual

La construcción de la taxonomía temática se fundamenta en los siguientes principios:

## 1. Jerarquía temática

Los temas se organizan mediante niveles progresivos de especificidad:

```
Tema
   ↓
Subtema
   ↓
Microtema
```

Cada nivel representa un grado diferente de detalle analítico.

---

## 2. Coherencia semántica

Las categorías pertenecientes a una misma rama temática deben mantener una relación conceptual clara.

Un subtema debe representar una especialización válida del tema superior al que pertenece.

---

## 3. Independencia analítica

La clasificación temática se realiza de manera independiente respecto a:

- intención comunicativa;
- sentimiento;
- valoración;
- identidad del emisor;
- interpretación política.

Un documento puede tener una intención determinada y tratar múltiples temas simultáneamente.

---

## 4. Evidencia observable

La asignación temática requiere evidencia identificable dentro del contenido analizado.

No se clasifican temas basándose únicamente en:

- contexto externo;
- conocimiento previo del emisor;
- asociaciones políticas;
- suposiciones del analista.

---

## 5. Capacidad multi-temática

El modelo reconoce que los documentos públicos frecuentemente contienen múltiples asuntos.

Por esta razón, el Pipeline permite registrar:

- Tema Principal.
- Temas Secundarios.

Siempre que cada asignación tenga evidencia suficiente.

---

# 5.3 Estructura Jerárquica General

La taxonomía utiliza tres niveles principales:

```
Nivel 1
Tema

        ↓

Nivel 2
Subtema

        ↓

Nivel 3
Microtema
```

Cada documento puede ser clasificado en cualquiera de estos niveles dependiendo de la disponibilidad de evidencia.

---

# 5.4 Nivel 1 — Tema

El **Tema** representa la categoría conceptual más amplia dentro de la taxonomía.

Su objetivo es identificar el área general sobre la cual se desarrolla la comunicación.

Ejemplos conceptuales:

| Tema | Descripción |
|------|-------------|
| Infraestructura | Obras públicas, mantenimiento físico y desarrollo urbano |
| Servicios Públicos | Prestación y gestión de servicios municipales |
| Seguridad | Prevención, vigilancia y convivencia ciudadana |
| Desarrollo Social | Programas dirigidos a población y comunidades |
| Medio Ambiente | Gestión ambiental y sostenibilidad |
| Administración Pública | Gestión institucional y funcionamiento municipal |

El nivel Tema permite generar análisis generales y comparaciones históricas.

---

# 5.5 Nivel 2 — Subtema

El **Subtema** representa una especialización dentro de un tema principal.

Su función es incrementar la precisión analítica sin llegar al nivel máximo de detalle.

Ejemplo:

```
Infraestructura

├── Calles y vías
├── Obras municipales
├── Espacios públicos
└── Edificaciones públicas
```

El subtema permite identificar áreas específicas de gestión institucional.

---

# 5.6 Nivel 3 — Microtema

El **Microtema** corresponde al nivel más específico de clasificación dentro de la taxonomía.

Permite identificar aspectos concretos mencionados dentro de un documento.

Ejemplo:

```
Infraestructura

    └── Calles y vías

            └── Bacheo y reparación vial
```

Los microtemas permiten generar análisis detallados y detectar patrones específicos dentro de grandes volúmenes de información.

---

# 5.7 Relación entre Niveles

La relación jerárquica debe cumplir la siguiente condición:

```
Todo Microtema pertenece a un único Subtema.

Todo Subtema pertenece a un único Tema.

Todo documento puede contener múltiples ramas temáticas.
```

Ejemplo:

Documento:

> "La alcaldía inició la reparación de calles y anunció nuevas jornadas de limpieza comunitaria."

Clasificación:

Tema Principal:

- Infraestructura

Subtema:

- Calles y vías

Microtema:

- Reparación vial

Tema Secundario:

- Medio Ambiente

Subtema:

- Limpieza urbana

---

# 5.8 Representación Conceptual del Documento

Cada documento puede representarse mediante la siguiente estructura:

```
Documento

├── Tema Principal
│
│     ├── Subtema
│     │
│     └── Microtema
│
└── Temas Secundarios

      ├── Subtema
      │
      └── Microtema
```

Esta estructura permite conservar la relación entre el contenido original y la clasificación temática generada.

---

# 5.9 Diferencia entre Tema e Intención Comunicativa

El Modelo de Taxonomía Temática y el Modelo de Intención Comunicativa analizan dimensiones diferentes del mismo documento.

Ejemplo:

Mensaje:

> "Invitamos a todos los vecinos a participar en la jornada de reparación del parque municipal."

Análisis de intención:

Principal:

- Convocar

Análisis temático:

Principal:

- Infraestructura

Subtema:

- Espacios públicos

Microtema:

- Recuperación de parques

Ambos resultados son complementarios y no deben mezclarse.

---

# 5.10 Consideraciones Analíticas

El Modelo Conceptual de la Taxonomía constituye la base estructural para todos los procesos posteriores de clasificación temática.

Su diseño permite mantener equilibrio entre:

- simplicidad interpretativa;
- capacidad de detalle;
- escalabilidad;
- consistencia metodológica;
- trazabilidad analítica.

La separación entre niveles jerárquicos evita clasificaciones excesivamente generales o excesivamente específicas, permitiendo que el Pipeline produzca información útil tanto para análisis ejecutivos como para investigaciones detalladas.

La taxonomía representa una estructura viva del conocimiento institucional, pero cualquier modificación deberá gestionarse mediante el sistema oficial de versionado definido posteriormente en este documento.

---

# 6. Estructura Jerárquica de la Taxonomía

## 6.1 Propósito

La estructura jerárquica de la taxonomía define la organización formal mediante la cual el Pipeline representa los temas identificados dentro de los documentos analizados.

Su objetivo es establecer una relación ordenada entre categorías generales y específicas, permitiendo que los resultados puedan interpretarse desde diferentes niveles de profundidad analítica.

Esta estructura garantiza que cada clasificación temática mantenga coherencia conceptual, evitando duplicidad de categorías, ambigüedades semánticas y pérdida de información durante el proceso de análisis.

---

# 6.2 Modelo Jerárquico General

La taxonomía utiliza una estructura de tres niveles principales:

```
TEMA
 │
 ├── SUBTEMA
 │
 │      └── MICROTE MA
 │
```

Cada nivel cumple una función específica:

| Nivel | Función Analítica |
|------|-------------------|
| Tema | Identifica el área general de gestión o asunto público. |
| Subtema | Divide el tema en áreas funcionales más específicas. |
| Microtema | Describe elementos concretos mencionados dentro del contenido. |

---

# 6.3 Nivel Tema

## Definición

El **Tema** constituye el primer nivel de clasificación temática y representa la categoría más amplia dentro de la taxonomía.

Su propósito es agrupar contenidos relacionados con grandes áreas institucionales, sociales o administrativas.

Los temas deben cumplir las siguientes características:

- alta estabilidad temporal;
- amplia cobertura documental;
- independencia respecto a expresiones particulares;
- capacidad de agrupar múltiples subtemas;
- utilidad para análisis ejecutivo.

---

## Ejemplo conceptual

```
Tema:

Seguridad Ciudadana
```

Este tema puede incluir contenidos relacionados con:

- prevención;
- vigilancia;
- convivencia;
- atención comunitaria;
- coordinación institucional.

---

# 6.4 Nivel Subtema

## Definición

El **Subtema** representa una división funcional dentro de un Tema.

Su objetivo es aumentar la precisión analítica identificando áreas específicas dentro de una categoría general.

Un Subtema debe:

- pertenecer únicamente a un Tema;
- mantener relación semántica directa;
- representar una categoría recurrente;
- ser suficientemente estable para análisis histórico.

---

## Ejemplo conceptual

```
Tema:

Seguridad Ciudadana

Subtemas:

├── Prevención del delito
├── Vigilancia comunitaria
├── Seguridad vial
└── Emergencias
```

---

# 6.5 Nivel Microtema

## Definición

El **Microtema** representa el nivel más específico de la estructura temática.

Su función es identificar elementos concretos, situaciones particulares o áreas operativas dentro de un Subtema.

Un Microtema debe:

- pertenecer a un único Subtema;
- representar una unidad analítica específica;
- contar con evidencia temática suficiente;
- evitar fragmentación excesiva.

---

## Ejemplo conceptual

```
Tema:

Seguridad Ciudadana

    ↓

Subtema:

Vigilancia comunitaria

    ↓

Microtema:

Instalación de cámaras de seguridad
```

---

# 6.6 Reglas de Pertenencia Jerárquica

La estructura debe cumplir las siguientes reglas:

## Regla 1 — Unicidad superior

Cada Subtema debe pertenecer únicamente a un Tema.

Ejemplo correcto:

```
Seguridad Ciudadana

└── Vigilancia comunitaria
```

Ejemplo incorrecto:

```
Seguridad Ciudadana

└── Vigilancia comunitaria

Infraestructura

└── Vigilancia comunitaria
```

Una misma categoría no debe existir simultáneamente en ramas distintas salvo que exista una justificación metodológica documentada.

---

## Regla 2 — Especialización progresiva

Cada nivel inferior debe incrementar la precisión.

Ejemplo correcto:

```
Infraestructura

    ↓

Calles y vías

    ↓

Bacheo urbano
```

Cada nivel responde a una pregunta más específica:

- ¿Sobre qué área general?
- ¿Sobre qué componente?
- ¿Sobre qué aspecto concreto?

---

## Regla 3 — No duplicidad semántica

La taxonomía debe evitar categorías con significado equivalente.

Ejemplo incorrecto:

```
Servicios Públicos

├── Recolección de basura

└── Limpieza de residuos
```

Si ambas representan el mismo fenómeno deberán consolidarse o definirse claramente sus diferencias.

---

## Regla 4 — Independencia del lenguaje utilizado

Las categorías no deben depender de palabras específicas.

Ejemplo:

El microtema:

```
Mantenimiento vial
```

debe reconocer expresiones como:

- reparación de calles;
- arreglo de carreteras;
- recuperación de vías;
- bacheo.

La taxonomía representa conceptos, no únicamente términos.

---

# 6.7 Profundidad Variable

Aunque la estructura base utiliza tres niveles, no todos los documentos requerirán necesariamente alcanzar el nivel Microtema.

La profundidad dependerá de la evidencia disponible.

Ejemplo:

Documento:

> "La alcaldía continúa desarrollando proyectos de infraestructura."

Clasificación:

Tema:

- Infraestructura

Sin evidencia suficiente para asignar:

- Subtema.
- Microtema.

---

Documento:

> "Inició la reparación de baches en la colonia El Palmar."

Clasificación:

Tema:

- Infraestructura

Subtema:

- Calles y vías

Microtema:

- Reparación de baches

---

# 6.8 Relación entre Taxonomía y Evidencia

La asignación jerárquica deberá seguir una lógica de evidencia acumulativa.

Mientras mayor sea la especificidad requerida, mayor deberá ser la evidencia disponible.

Ejemplo:

Para asignar:

Tema:

Infraestructura

Puede bastar evidencia general:

- obra pública;
- construcción;
- mantenimiento.

Para asignar:

Microtema:

Reparación de baches

Se requiere evidencia específica:

- baches;
- pavimento;
- reparación vial;
- calles deterioradas.

---

# 6.9 Representación Formal

Cada clasificación temática puede representarse como:

```
Clasificación Temática

{
Tema:
    {
    Subtema:
        {
        Microtema:
        }
    }
}
```

Cuando existen múltiples temas:

```
Documento

├── Tema Principal
│
│    ├── Subtema
│    │
│    └── Microtema
│
└── Temas Secundarios

     ├── Subtema
     │
     └── Microtema
```

---

# 6.10 Consideraciones Analíticas

La estructura jerárquica permite que el Pipeline mantenga simultáneamente una visión estratégica y una visión detallada del contenido analizado.

Los niveles superiores facilitan:

- dashboards ejecutivos;
- tendencias generales;
- comparación temporal;
- análisis institucional.

Los niveles inferiores permiten:

- detección de problemas específicos;
- análisis operativo;
- identificación de patrones locales;
- generación de indicadores especializados.

La jerarquía temática constituye el mecanismo que transforma grandes volúmenes de conversación digital en información organizada, comparable y auditable, manteniendo siempre una relación verificable entre el contenido original y la clasificación generada.

---

# 7. Reglas Generales de Clasificación Temática

## 7.1 Propósito

Las reglas generales de clasificación temática establecen los criterios deterministas mediante los cuales el Pipeline asigna uno o más temas a un documento analizado.

Su objetivo es garantizar que todas las clasificaciones temáticas sean:

- consistentes;
- reproducibles;
- explicables;
- auditables;
- independientes de interpretaciones subjetivas.

Estas reglas definen cómo debe evaluarse la evidencia temática, cómo deben resolverse ambigüedades y bajo qué condiciones un tema puede ser considerado válido dentro del modelo.

---

# 7.2 Principios Generales de Clasificación

La clasificación temática se fundamenta en los siguientes principios:

## 1. La evidencia precede a la clasificación

Un tema únicamente podrá asignarse cuando exista evidencia observable que lo respalde.

No se clasificará un documento basándose en:

- suposiciones;
- conocimiento externo;
- identidad del emisor;
- contexto político previo;
- asociaciones no expresadas.

---

## 2. El contenido determina el tema

La clasificación se realiza sobre el contenido del documento y no sobre:

- quién publica;
- dónde publica;
- qué posición política representa;
- qué intención se presume.

El modelo analiza exclusivamente la información comunicada.

---

## 3. El concepto prevalece sobre la palabra

La identificación temática no depende de coincidencias literales.

El Pipeline evalúa conceptos y relaciones semánticas.

Ejemplo:

Las expresiones:

- reparar calles;
- mejorar vías;
- arreglar pavimento;
- eliminar baches;

pueden representar el mismo concepto temático:

```
Infraestructura
    └── Calles y vías
```

---

## 4. La clasificación puede ser múltiple

Un documento puede contener más de un tema cuando existan evidencias independientes.

Ejemplo:

> "Iniciamos la construcción del parque y realizamos una jornada de limpieza comunitaria."

Clasificación:

Tema principal:

- Infraestructura

Tema secundario:

- Medio Ambiente

---

# 7.3 Proceso General de Clasificación

El proceso de clasificación temática sigue las siguientes etapas:

```
Documento

↓

Extracción de evidencias temáticas

↓

Identificación de conceptos asociados

↓

Evaluación de correspondencia con taxonomía

↓

Asignación de puntuación temática

↓

Selección de temas

↓

Determinación de confianza

↓

Registro de resultados
```

Cada etapa mantiene trazabilidad para auditoría posterior.

---

# 7.4 Regla de Evidencia Directa

Un tema puede asignarse cuando el documento contiene referencias directas a conceptos pertenecientes a una categoría temática.

Ejemplo:

Documento:

> "La alcaldía reparará cinco kilómetros de calles dañadas."

Evidencia:

- calles;
- reparación;
- kilómetros de vía.

Clasificación:

Tema:

- Infraestructura

Subtema:

- Calles y vías

---

# 7.5 Regla de Evidencia Contextual

Cuando un tema no aparece expresado literalmente, podrá asignarse si existe suficiente evidencia contextual dentro del documento.

Ejemplo:

Documento:

> "Se instalaron nuevos puntos de vigilancia con monitoreo permanente."

Aunque no aparece la palabra "seguridad", la evidencia permite identificar:

Tema:

- Seguridad Ciudadana

Subtema:

- Vigilancia

---

# 7.6 Regla de Evidencia Acumulada

La clasificación temática deberá considerar la suma de múltiples evidencias compatibles.

Una sola referencia aislada puede ser insuficiente.

Ejemplo:

Documento:

> "Nueva inversión municipal: construcción de aulas, reparación de techos y mejora de instalaciones escolares."

Evidencias:

- aulas;
- instalaciones escolares;
- reparación;
- infraestructura educativa.

Resultado:

Mayor respaldo para:

Tema:

- Educación

Subtema:

- Infraestructura educativa

---

# 7.7 Regla de Relevancia Temática

La presencia de una palabra relacionada con un tema no garantiza automáticamente su clasificación.

El Pipeline debe evaluar si el concepto tiene relevancia dentro del mensaje.

Ejemplo:

> "Recordamos la importancia histórica del antiguo hospital municipal."

La palabra "hospital" no implica necesariamente:

Tema:

- Salud

si el contenido trata únicamente sobre historia institucional.

---

# 7.8 Regla de Predominio Temático

Cuando un documento contiene múltiples temas, el tema principal será aquel que represente la finalidad temática predominante.

La selección considera:

- cantidad de evidencia;
- especificidad;
- extensión dentro del documento;
- posición discursiva;
- relación con el objetivo principal del contenido.

---

# 7.9 Regla de Jerarquía Temática

La clasificación debe respetar la estructura:

```
Tema

↓

Subtema

↓

Microtema
```

No deberá asignarse un Microtema sin una relación válida con su Subtema correspondiente.

Ejemplo incorrecto:

```
Microtema:

Bacheo urbano
```

sin:

```
Subtema:

Calles y vías
```

ni:

```
Tema:

Infraestructura
```

---

# 7.10 Regla de Especificidad

Cuando exista evidencia suficiente, el Pipeline deberá preferir el nivel más específico disponible.

Ejemplo:

Documento:

> "Programa de vacunación infantil en centros comunitarios."

Clasificación preferente:

Tema:

- Salud

Subtema:

- Programas de vacunación

Microtema:

- Vacunación infantil

No deberá quedarse únicamente en:

Tema:

- Salud

si existe evidencia suficiente para mayor precisión.

---

# 7.11 Regla de Conservación de Información

Cuando la evidencia no permita determinar un nivel inferior, la clasificación deberá conservar el nivel superior.

Ejemplo:

Documento:

> "La municipalidad desarrolla nuevos proyectos sociales."

Clasificación:

Tema:

- Desarrollo Social

Sin asignar:

- Subtema.

- Microtema.

La ausencia de detalle no debe compensarse con inferencias.

---

# 7.12 Regla de Exclusión Temática

Un tema deberá excluirse cuando:

- la referencia sea incidental;
- no exista relación con el propósito del mensaje;
- la evidencia sea insuficiente;
- la clasificación dependa de información externa.

Ejemplo:

> "El alcalde visitó una escuela para anunciar obras municipales."

La mención de la escuela no necesariamente implica:

Tema principal:

- Educación.

La evidencia puede corresponder principalmente a:

Tema:

- Infraestructura.

---

# 7.13 Regla de Contexto Institucional

El contexto institucional puede apoyar la interpretación, pero nunca sustituye la evidencia textual.

Ejemplo:

Una publicación de una alcaldía puede hablar frecuentemente de:

- obras;
- servicios;
- comunidades.

Sin embargo, cada clasificación deberá justificarse por el contenido específico del documento analizado.

---

# 7.14 Registro de Decisión Temática

Cada clasificación generada deberá almacenar:

- tema asignado;
- nivel jerárquico alcanzado;
- evidencias detectadas;
- puntuación obtenida;
- confianza asociada;
- versión de la taxonomía utilizada.

Esto permite reconstruir la decisión analítica posteriormente.

---

# 7.15 Consideraciones Analíticas

Las reglas generales de clasificación temática constituyen el núcleo operativo del modelo taxonómico.

Su aplicación garantiza que la asignación de temas no dependa de interpretaciones subjetivas ni de modelos opacos, sino de evidencia estructurada y criterios previamente definidos.

El enfoque permite equilibrar dos necesidades:

- suficiente generalización para generar análisis ejecutivos;
- suficiente precisión para identificar fenómenos específicos.

De esta manera, el Pipeline transforma contenido digital no estructurado en una representación temática organizada, verificable y apta para análisis longitudinal, manteniendo la trazabilidad completa entre documento original, evidencia detectada y clasificación final.

---

# 8. Evidencias Temáticas

## 8.1 Propósito

Las **Evidencias Temáticas** constituyen los elementos observables utilizados por el Pipeline para determinar la relación entre un documento y una categoría dentro de la taxonomía temática.

Su función es proporcionar la base objetiva para la clasificación de temas, subtemas y microtemas, garantizando que cada asignación pueda justificarse mediante información identificable dentro del contenido analizado.

El modelo no clasifica temas mediante coincidencias simples de palabras, sino mediante la evaluación conjunta de evidencias lingüísticas, semánticas y contextuales.

---

# 8.2 Principios de Evidencia Temática

La identificación de evidencias temáticas se fundamenta en los siguientes principios:

1. Toda clasificación temática requiere evidencia verificable.

2. La evidencia debe encontrarse dentro del documento analizado.

3. Una palabra aislada no determina una clasificación.

4. La evidencia debe evaluarse dentro de su contexto discursivo.

5. La acumulación de evidencias incrementa la solidez de la clasificación.

6. Las evidencias pueden corresponder a distintos niveles jerárquicos.

7. Toda evidencia utilizada debe quedar registrada para auditoría.

---

# 8.3 Tipos de Evidencia Temática

El modelo reconoce cuatro tipos principales de evidencia:

| Tipo | Descripción |
|------|-------------|
| Evidencia lingüística | Palabras, expresiones o términos asociados a una categoría temática. |
| Evidencia semántica | Relación conceptual entre el contenido y una categoría temática aunque no exista coincidencia literal. |
| Evidencia contextual | Información del mensaje que permite interpretar correctamente el tema tratado. |
| Evidencia estructural | Elementos organizativos del contenido como títulos, etiquetas o secciones. |

---

# 8.4 Evidencia Lingüística

## Definición

Corresponde a términos o expresiones explícitamente presentes en el documento que se relacionan con una categoría temática.

Ejemplo:

Documento:

> "Iniciamos la reparación de calles dañadas."

Evidencias lingüísticas:

- reparación;
- calles;
- dañadas.

Clasificación:

Tema:

- Infraestructura.

Subtema:

- Calles y vías.

---

## Limitaciones

La evidencia lingüística por sí sola no siempre es suficiente.

Ejemplo:

> "El alcalde visitó la escuela donde estudió de niño."

La palabra "escuela" aparece, pero el contenido puede no corresponder al tema Educación.

---

# 8.5 Evidencia Semántica

## Definición

La evidencia semántica identifica relaciones conceptuales entre el contenido y una categoría temática aunque no exista una coincidencia literal.

Ejemplo:

Documento:

> "Se instalaron nuevos sistemas de monitoreo en puntos estratégicos del municipio."

Aunque no aparece la palabra "seguridad", existe relación conceptual con:

Tema:

- Seguridad Ciudadana.

Subtema:

- Vigilancia.

---

## Características

La evidencia semántica considera:

- equivalencias conceptuales;
- sinónimos;
- relaciones funcionales;
- asociaciones operativas;
- descripción de actividades.

---

# 8.6 Evidencia Contextual

## Definición

La evidencia contextual utiliza la relación entre diferentes elementos del documento para determinar el tema dominante.

Ejemplo:

Documento:

> "La municipalidad inició la construcción de aulas nuevas para mejorar las condiciones educativas."

Evidencias:

- construcción;
- aulas;
- condiciones educativas.

El contexto permite identificar:

Tema:

- Educación.

Subtema:

- Infraestructura educativa.

---

# 8.7 Evidencia Estructural

## Definición

Corresponde a elementos de organización del contenido que aportan información temática adicional.

Incluye:

- títulos;
- encabezados;
- etiquetas;
- categorías declaradas;
- nombres de programas;
- nombres oficiales de proyectos.

Ejemplo:

Título:

> "Programa Municipal de Reciclaje Comunitario"

Puede aportar evidencia para:

Tema:

- Medio Ambiente.

Subtema:

- Gestión de residuos.

---

# 8.8 Niveles de Fortaleza de Evidencia

Al igual que el modelo de intención comunicativa, las evidencias temáticas se clasifican según su fuerza.

---

## Evidencia Fuerte

### Definición

Indicador con relación directa y altamente específica con una categoría temática.

Ejemplos:

- "bacheo de calles";
- "vacunación infantil";
- "recolección de basura";
- "alumbrado público".

Características:

- alta precisión;
- bajo nivel de ambigüedad;
- relación directa con la taxonomía.

---

## Evidencia Moderada

### Definición

Indicador compatible con una categoría temática, pero que requiere apoyo adicional.

Ejemplos:

- "obras";
- "comunidad";
- "servicios";
- "programas sociales".

Características:

- mayor amplitud conceptual;
- múltiples interpretaciones posibles;
- necesita contexto adicional.

---

## Evidencia Débil

### Definición

Indicador genérico que puede relacionarse con varios temas.

Ejemplos:

- "mejoras";
- "desarrollo";
- "apoyo";
- "progreso".

Características:

- bajo poder discriminante;
- requiere múltiples evidencias complementarias.

---

# 8.9 Evidencia por Nivel Jerárquico

La fuerza requerida depende del nivel de clasificación.

## Para Tema

Puede ser suficiente evidencia general.

Ejemplo:

"obra pública"

→ Infraestructura.

---

## Para Subtema

Se requiere mayor especificidad.

Ejemplo:

"reparación de carreteras"

→ Infraestructura  
→ Calles y vías.

---

## Para Microtema

Se requiere evidencia altamente específica.

Ejemplo:

"reparación de baches en avenida principal"

→ Infraestructura  
→ Calles y vías  
→ Bacheo urbano.

---

# 8.10 Evidencias Negativas

El modelo también considera evidencia que contradice una posible clasificación.

Ejemplo:

Documento:

> "La historia del antiguo hospital municipal será presentada en una exposición."

Aunque aparece "hospital", la evidencia indica un contexto histórico y no necesariamente:

Tema:

- Salud.

Las evidencias negativas ayudan a reducir clasificaciones incorrectas.

---

# 8.11 Acumulación de Evidencias

La clasificación temática no depende de una única evidencia.

El Pipeline combina:

- cantidad;
- calidad;
- diversidad;
- coherencia.

Ejemplo:

Documento:

> "Nueva campaña de reciclaje, instalación de contenedores y jornadas comunitarias de limpieza."

Evidencias:

| Evidencia | Tipo |
|-|-|
| reciclaje | fuerte |
| contenedores | fuerte |
| limpieza | moderada |
| jornadas comunitarias | moderada |

Resultado:

Tema:

- Medio Ambiente.

---

# 8.12 Registro de Evidencias

Para cada clasificación temática deberán almacenarse:

- evidencia identificada;
- tipo de evidencia;
- nivel de fortaleza;
- categoría asociada;
- puntuación asignada;
- ubicación dentro del documento cuando sea posible.

Este registro permite auditoría completa del proceso.

---

# 8.13 Integración con el Pipeline

Las evidencias temáticas alimentan las siguientes etapas:

- clasificación temática;
- asignación jerárquica;
- puntuación temática;
- determinación de confianza;
- generación de variables;
- construcción de indicadores.

La evidencia constituye el vínculo verificable entre el texto original y la categoría temática generada.

---

# 8.14 Consideraciones Analíticas

El modelo de evidencias temáticas garantiza que la taxonomía funcione como un sistema explicable y no como una clasificación basada exclusivamente en frecuencia de palabras.

La combinación de evidencia lingüística, semántica y contextual permite capturar la complejidad del lenguaje natural manteniendo criterios deterministas.

El objetivo no es identificar únicamente términos presentes, sino establecer relaciones verificables entre contenido y categorías temáticas.

De esta manera, el Pipeline conserva la capacidad de analizar grandes volúmenes de comunicación digital sin perder transparencia, reproducibilidad ni capacidad de auditoría.

---

# 9. Resolución de Conflictos entre Temas

## 9.1 Propósito

La resolución de conflictos entre temas establece las reglas metodológicas utilizadas por el Pipeline cuando un documento contiene evidencias correspondientes a múltiples categorías temáticas que compiten entre sí.

Su objetivo es garantizar que la clasificación final mantenga coherencia analítica, evitando asignaciones arbitrarias y permitiendo determinar:

- Tema Principal.
- Temas Secundarios.
- Nivel jerárquico aplicable.
- Grado de confianza asociado.

El conflicto temático no se interpreta como un error del modelo, sino como una característica natural de la comunicación institucional, donde un mismo mensaje puede abordar simultáneamente múltiples asuntos.

---

# 9.2 Principios Generales

La resolución de conflictos se fundamenta en los siguientes principios:

1. La coexistencia temática es válida cuando existe evidencia suficiente.

2. Ningún tema debe eliminarse únicamente por aparecer junto a otro.

3. La selección del tema principal debe basarse en evidencia y relevancia.

4. Las categorías superiores no deben imponerse automáticamente sobre categorías más específicas.

5. La clasificación debe conservar la información disponible.

6. Toda decisión debe ser reconstruible mediante las evidencias registradas.

---

# 9.3 Tipos de Conflicto Temático

El modelo reconoce cuatro tipos principales de conflicto.

---

## 1. Conflicto entre temas independientes

Ocurre cuando un documento aborda dos áreas diferentes sin relación jerárquica directa.

Ejemplo:

> "Iniciamos la reparación del parque municipal y realizamos una campaña de vacunación."

Evidencias:

Tema 1:

- Infraestructura.

Tema 2:

- Salud.

Resolución:

Ambos pueden coexistir.

Resultado:

Tema Principal:

- Infraestructura.

Tema Secundario:

- Salud.

---

## 2. Conflicto entre niveles jerárquicos

Ocurre cuando una evidencia puede clasificarse en distintos niveles de especificidad.

Ejemplo:

Documento:

> "Programa de mantenimiento vial."

Posibles clasificaciones:

Tema:

- Infraestructura.

Subtema:

- Calles y vías.

Microtema:

- Mantenimiento vial.

Resolución:

Se conserva la clasificación más específica cuando existe evidencia suficiente.

---

## 3. Conflicto por ambigüedad semántica

Ocurre cuando una expresión puede pertenecer a múltiples categorías.

Ejemplo:

> "Mejoramos los espacios comunitarios."

Posibles interpretaciones:

- Infraestructura.
- Desarrollo Social.

Resolución:

Se requiere evidencia adicional.

Si no existe suficiente información:

Clasificación:

Tema general correspondiente.

No se realizan inferencias adicionales.

---

## 4. Conflicto por evidencia contradictoria

Ocurre cuando diferentes elementos del documento apuntan hacia categorías incompatibles.

Ejemplo:

> "Nuevo proyecto ambiental que genera críticas por afectaciones urbanas."

Evidencias:

- Medio Ambiente.
- Desarrollo Urbano.

Resolución:

Se evalúa:

- cantidad de evidencia;
- especificidad;
- posición discursiva;
- relación con el propósito principal.

---

# 9.4 Criterios de Priorización Temática

Cuando múltiples temas compiten por ser el Tema Principal, el Pipeline utiliza los siguientes criterios:

---

## 1. Mayor evidencia acumulada

El tema con mayor cantidad de evidencia compatible obtiene mayor prioridad.

Ejemplo:

Tema A:

5 evidencias.

Tema B:

2 evidencias.

Prioridad:

Tema A.

---

## 2. Mayor especificidad

Una categoría específica puede superar una categoría general cuando ambas describen el mismo contenido.

Ejemplo:

Documento:

> "Construcción de aulas escolares."

Comparación:

Educación:

General.

Infraestructura educativa:

Específica.

Resultado:

Infraestructura educativa.

---

## 3. Mayor centralidad discursiva

El tema que ocupa una posición principal dentro del mensaje puede recibir prioridad.

Se considera:

- título;
- inicio del documento;
- objetivo declarado;
- repetición temática.

---

## 4. Mayor relevancia operativa

Cuando dos temas tienen evidencia similar, se prioriza aquel que representa la acción principal descrita.

Ejemplo:

> "Construcción de un centro de salud para ampliar la atención médica."

Aunque existe:

Infraestructura.

El propósito principal corresponde a:

Salud.

---

# 9.5 Regla de Coexistencia Temática

Cuando dos o más temas poseen evidencia suficiente, el modelo deberá conservarlos.

Ejemplo:

Documento:

> "La alcaldía inauguró un parque ecológico con actividades comunitarias."

Clasificación:

Tema principal:

- Medio Ambiente.

Tema secundario:

- Desarrollo Social.

La coexistencia evita pérdida de información relevante.

---

# 9.6 Regla de Exclusión por Insuficiencia

Un tema deberá descartarse cuando:

- la evidencia sea incidental;
- aparezca únicamente como referencia secundaria;
- dependa de información externa;
- no tenga relación directa con el propósito del documento.

Ejemplo:

> "El alcalde visitó una escuela durante la entrega de una calle renovada."

La palabra "escuela" no justifica automáticamente:

Tema:

Educación.

---

# 9.7 Regla de Preferencia por Evidencia Directa

Entre dos posibles clasificaciones, tendrá prioridad la categoría con evidencia más directa.

Ejemplo:

Documento:

> "Se entregaron medicamentos gratuitos durante una jornada médica."

Posibles temas:

- Desarrollo Social.
- Salud.

Evidencia directa:

medicamentos;
jornada médica.

Resultado:

Salud.

---

# 9.8 Resolución de Conflictos entre Tema y Subtema

Cuando existe evidencia suficiente para clasificar un nivel inferior, el Pipeline debe mantener la relación jerárquica completa.

Ejemplo:

Resultado correcto:

```
Tema:

Salud

    ↓

Subtema:

Atención médica

    ↓

Microtema:

Jornadas médicas comunitarias
```

No debe registrarse únicamente:

```
Microtema:

Jornadas médicas comunitarias
```

sin su contexto superior.

---

# 9.9 Registro del Conflicto

Cuando exista competencia entre categorías, el sistema deberá registrar:

- temas evaluados;
- evidencias asociadas;
- puntuaciones obtenidas;
- criterio aplicado;
- decisión final.

Esto permite explicar por qué una categoría fue seleccionada o descartada.

---

# 9.10 Casos de Empate

Cuando dos temas obtienen evidencia equivalente:

El Pipeline podrá:

1. Registrar ambos como temas principales secundarios según configuración metodológica.
2. Mantener ambos con igual nivel de confianza.
3. Evitar una decisión arbitraria basada únicamente en orden de aparición.

Los empates deberán conservar trazabilidad completa.

---

# 9.11 Integración con la Clasificación Multi-Tema

La resolución de conflictos constituye la etapa previa a la generación del resultado multi-tema.

Proceso:

```
Extracción de evidencias

↓

Identificación de temas candidatos

↓

Evaluación de conflictos

↓

Asignación Tema Principal

↓

Asignación Temas Secundarios

↓

Cálculo de confianza
```

---

# 9.12 Consideraciones Analíticas

La resolución de conflictos entre temas permite que el modelo represente adecuadamente la complejidad de la comunicación pública sin forzar clasificaciones exclusivas.

El objetivo metodológico no es reducir la realidad comunicativa a una única categoría, sino identificar la estructura temática dominante y conservar los asuntos complementarios cuando exista evidencia suficiente.

Este enfoque mantiene equilibrio entre precisión, interpretabilidad y capacidad analítica, permitiendo que el Pipeline genere información útil para análisis institucionales sin introducir decisiones arbitrarias.

Cada conflicto resuelto debe permanecer explicado mediante evidencia, reglas y trazabilidad documental, preservando el carácter determinista y auditable del sistema.

---

# 10. Clasificación Multi-Tema

## 10.1 Propósito

La clasificación multi-tema define el mecanismo mediante el cual el Pipeline identifica y registra la presencia de múltiples temas dentro de un mismo documento.

Su objetivo es representar de manera fiel la complejidad de la comunicación institucional, evitando que contenidos con múltiples dimensiones sean reducidos artificialmente a una única categoría temática.

El modelo reconoce que una publicación, comunicado o conversación digital puede abordar simultáneamente diferentes áreas de gestión pública, programas institucionales o asuntos ciudadanos.

Por esta razón, la taxonomía permite asignar:

- un Tema Principal;
- uno o varios Temas Secundarios.

Cada asignación debe estar respaldada por evidencia temática independiente y verificable.

---

# 10.2 Principios de la Clasificación Multi-Tema

La clasificación multi-tema se fundamenta en los siguientes principios:

## 1. Representación completa del contenido

El objetivo es conservar la mayor cantidad de información temática relevante sin introducir categorías no justificadas.

---

## 2. Independencia entre temas

Cada tema identificado debe evaluarse de manera independiente.

La existencia de un Tema Principal no invalida automáticamente otros temas presentes.

---

## 3. Evidencia independiente

Cada tema secundario debe contar con evidencia propia.

No deberá asignarse un tema únicamente por asociación con otro.

Ejemplo incorrecto:

> "Se construyó un parque y por eso contiene automáticamente Desarrollo Social."

La clasificación requiere evidencia adicional.

---

## 4. Priorización sin exclusión

La existencia de un Tema Principal permite ordenar la información, pero no elimina temas secundarios relevantes.

---

# 10.3 Modelo de Representación

Cada documento puede representarse mediante la siguiente estructura:

```
Documento

│
├── Tema Principal
│
│      ├── Subtema
│      └── Microtema
│
└── Temas Secundarios
       │
       ├── Tema Secundario 1
       │       ├── Subtema
       │       └── Microtema
       │
       └── Tema Secundario 2
               ├── Subtema
               └── Microtema
```

Esta estructura mantiene la relación entre contenido, jerarquía y evidencia.

---

# 10.4 Identificación del Tema Principal

El Tema Principal corresponde a la categoría que concentra la mayor relevancia temática dentro del documento.

Su determinación considera:

- cantidad de evidencias;
- calidad de evidencias;
- especificidad alcanzada;
- centralidad discursiva;
- relación con el objetivo principal del mensaje.

Ejemplo:

Documento:

> "Iniciamos la construcción del nuevo centro de salud municipal para ampliar la atención médica."

Evaluación:

Infraestructura:

Evidencia:
- construcción;
- edificio.

Salud:

Evidencia:
- centro de salud;
- atención médica.

Resultado:

Tema Principal:

- Salud.

Tema Secundario:

- Infraestructura.

La razón es que la infraestructura funciona como medio para alcanzar un objetivo sanitario.

---

# 10.5 Identificación de Temas Secundarios

Un tema secundario será registrado cuando:

- tenga evidencia suficiente;
- represente una dimensión real del contenido;
- aporte información analítica relevante.

No se incluyen temas secundarios únicamente por coincidencia de términos.

Ejemplo:

Documento:

> "La alcaldía realizó una jornada de limpieza en parques públicos con participación vecinal."

Resultado:

Tema Principal:

- Medio Ambiente.

Tema Secundario:

- Desarrollo Social.

---

# 10.6 Límite de Multiplicidad Temática

El modelo permite múltiples temas secundarios, pero evita una clasificación excesivamente amplia.

La incorporación de cada tema debe cumplir:

- evidencia suficiente;
- relevancia contextual;
- coherencia con la taxonomía.

El objetivo no es asignar todas las categorías posibles, sino aquellas que representen contenido significativo.

---

# 10.7 Clasificación por Capas Temáticas

Cuando un documento contiene diferentes niveles de información, la clasificación puede organizarse por capas.

Ejemplo:

Documento:

> "La municipalidad lanzó un programa de empleo juvenil mediante capacitación técnica."

Capas identificadas:

Capa institucional:

- Administración Pública.

Capa social:

- Desarrollo Social.

Capa específica:

- Empleo juvenil.

La taxonomía seleccionará las categorías correspondientes según la estructura definida.

---

# 10.8 Casos de Clasificación Multi-Tema

## Caso 1 — Infraestructura + Servicios Públicos

Mensaje:

> "Se repararon calles y se mejoró el sistema de iluminación pública."

Resultado:

Tema Principal:

- Infraestructura.

Tema Secundario:

- Servicios Públicos.

---

## Caso 2 — Seguridad + Participación Comunitaria

Mensaje:

> "Vecinos participaron en reuniones de prevención junto a autoridades locales."

Resultado:

Tema Principal:

- Seguridad Ciudadana.

Tema Secundario:

- Desarrollo Social.

---

## Caso 3 — Medio Ambiente + Educación

Mensaje:

> "Estudiantes participaron en talleres de reciclaje escolar."

Resultado:

Tema Principal:

- Medio Ambiente.

Tema Secundario:

- Educación.

---

# 10.9 Casos donde NO aplica Multi-Tema

No se deben asignar múltiples temas cuando:

## 1. Existe una única referencia incidental

Ejemplo:

> "El alcalde visitó una escuela durante una obra vial."

No implica automáticamente:

Educación.

---

## 2. Un tema es solamente contexto narrativo

Ejemplo:

> "Recordamos la historia del antiguo edificio municipal."

No implica necesariamente:

Infraestructura.

---

## 3. La relación requiere inferencia externa

Ejemplo:

> "Una nueva inversión beneficiará a la comunidad."

No permite asignar:

Desarrollo Social.

sin evidencia adicional.

---

# 10.10 Variables Generadas

La clasificación multi-tema genera variables específicas:

| Variable | Descripción |
|----------|-------------|
| tema_principal | Categoría temática dominante |
| temas_secundarios | Lista de categorías complementarias |
| nivel_tema | Profundidad alcanzada |
| evidencia_tematica | Evidencias utilizadas |
| puntuacion_tematica | Valor acumulado |
| confianza_tematica | Nivel de seguridad de la clasificación |

---

# 10.11 Integración con el Pipeline

El proceso multi-tema ocurre después de la identificación inicial de categorías candidatas.

Flujo:

```
Documento

↓

Extracción temática

↓

Generación de candidatos

↓

Evaluación individual

↓

Resolución de conflictos

↓

Tema Principal

↓

Temas Secundarios

↓

Registro analítico
```

---

# 10.12 Relación con A01 — Modelo de Intención Comunicativa

La clasificación multi-tema funciona de manera independiente al modelo de intención comunicativa.

Un documento puede presentar:

Ejemplo:

Intención Principal:

- Convocar.

Tema Principal:

- Medio Ambiente.

Temas Secundarios:

- Participación Ciudadana.

Esto significa:

La intención responde:

> ¿Qué busca comunicar el mensaje?

La taxonomía responde:

> ¿Sobre qué asunto trata el mensaje?

Ambas dimensiones pueden analizarse simultáneamente.

---

# 10.13 Auditoría de la Clasificación Multi-Tema

Cada resultado multi-tema deberá permitir reconstruir:

- temas candidatos;
- evidencias utilizadas;
- puntuaciones;
- conflictos encontrados;
- reglas aplicadas;
- versión de la taxonomía.

La auditoría debe permitir comprender por qué un documento recibió una clasificación determinada.

---

# 10.14 Consideraciones Analíticas

La clasificación multi-tema permite que MIPA represente la complejidad natural de la comunicación pública sin sacrificar la capacidad de análisis estructurado.

Este enfoque evita dos errores frecuentes:

1. Simplificación excesiva mediante una única categoría obligatoria.
2. Sobreclasificación mediante la asignación indiscriminada de múltiples temas.

El equilibrio se obtiene mediante evidencia, jerarquía y reglas explícitas.

La clasificación multi-tema convierte documentos no estructurados en representaciones temáticas organizadas, permitiendo análisis más precisos de tendencias institucionales, demandas ciudadanas y evolución de la conversación digital.

---

# 11. Niveles de Confianza

## 11.1 Propósito

Los **Niveles de Confianza Temática** establecen el mecanismo mediante el cual el Pipeline expresa la solidez metodológica de una clasificación temática generada.

Su objetivo es indicar qué tan consistente es la evidencia disponible para asignar un tema, subtema o microtema determinado.

La confianza representa exclusivamente la fuerza del soporte analítico disponible.

No representa:

- probabilidad de ocurrencia;
- certeza absoluta;
- veracidad del contenido;
- intención del emisor;
- impacto social o político.

---

# 11.2 Principios Generales

El cálculo de confianza temática se fundamenta en los siguientes principios:

1. La confianza depende de evidencia observable.
2. La confianza debe ser explicable.
3. La confianza no sustituye la clasificación.
4. Una puntuación elevada no implica automáticamente mayor importancia temática.
5. La confianza debe considerar cantidad y calidad de evidencia.
6. Toda confianza asignada debe poder auditarse.

---

# 11.3 Componentes de la Confianza Temática

El nivel de confianza se determina mediante la evaluación conjunta de los siguientes componentes:

| Componente | Descripción |
|------------|-------------|
| Fortaleza de evidencia | Calidad de los indicadores utilizados. |
| Cantidad de evidencia | Número de elementos compatibles identificados. |
| Especificidad | Nivel jerárquico alcanzado dentro de la taxonomía. |
| Coherencia semántica | Consistencia entre evidencias y categoría asignada. |
| Ausencia de conflicto | Existencia o inexistencia de temas competidores. |

---

# 11.4 Relación entre Evidencia y Confianza

La confianza aumenta cuando:

- existen múltiples evidencias independientes;
- las evidencias son específicas;
- existe coherencia entre diferentes elementos del documento;
- la clasificación alcanza niveles jerárquicos inferiores.

Ejemplo:

Documento:

> "Inició el programa de vacunación infantil en centros comunitarios."

Evidencias:

- vacunación;
- infantil;
- centros comunitarios.

Resultado:

Tema:

Salud.

Subtema:

Programas de vacunación.

Microtema:

Vacunación infantil.

Confianza:

Alta.

---

# 11.5 Escala de Confianza

El modelo utiliza tres niveles principales:

| Nivel | Descripción |
|------|-------------|
| Alta | Evidencia suficiente, específica y consistente. |
| Media | Evidencia válida pero con cierta ambigüedad o menor especificidad. |
| Baja | Evidencia limitada que permite una clasificación preliminar. |

---

# 11.6 Confianza Alta

## Definición

Se asigna cuando existe evidencia clara, directa y consistente con una categoría temática.

Características:

- múltiples evidencias compatibles;
- baja ambigüedad;
- relación directa con la taxonomía;
- ausencia de conflictos relevantes.

Ejemplo:

Documento:

> "La alcaldía inició trabajos de bacheo en calles del centro histórico."

Clasificación:

Tema:

Infraestructura.

Subtema:

Calles y vías.

Microtema:

Bacheo urbano.

Confianza:

Alta.

---

# 11.7 Confianza Media

## Definición

Se asigna cuando existe evidencia suficiente para una clasificación, pero presenta elementos que reducen la precisión.

Características:

- evidencia parcialmente específica;
- posible coexistencia con otros temas;
- menor cantidad de indicadores;
- necesidad de interpretación contextual.

Ejemplo:

Documento:

> "Nuevos proyectos para mejorar la calidad de vida de las familias."

Posible clasificación:

Tema:

Desarrollo Social.

Confianza:

Media.

La evidencia existe, pero la especificidad es limitada.

---

# 11.8 Confianza Baja

## Definición

Se asigna cuando la clasificación depende de evidencia limitada o altamente general.

Características:

- pocos indicadores;
- conceptos amplios;
- alta ambigüedad;
- ausencia de detalles suficientes.

Ejemplo:

Documento:

> "Seguimos trabajando por el desarrollo del municipio."

Posible clasificación:

Tema:

Administración Pública.

Confianza:

Baja.

---

# 11.9 Confianza por Nivel Jerárquico

La confianza debe evaluarse de manera independiente para cada nivel.

Ejemplo:

Documento:

> "Mejoramiento de infraestructura educativa mediante reparación de aulas."

Resultado:

Tema:

Educación.

Confianza:

Alta.

Subtema:

Infraestructura educativa.

Confianza:

Alta.

Microtema:

Reparación de aulas.

Confianza:

Media.

La evidencia puede ser suficiente para el tema general pero limitada para el nivel más específico.

---

# 11.10 Confianza en Clasificación Multi-Tema

Cada tema identificado debe tener su propia confianza.

Ejemplo:

Documento:

> "Construcción de parque ecológico con talleres ambientales para estudiantes."

Resultado:

Tema Principal:

Medio Ambiente.

Confianza:

Alta.

Tema Secundario:

Educación.

Confianza:

Media.

La confianza no se hereda entre temas.

---

# 11.11 Factores que Reducen la Confianza

La confianza disminuye cuando existe:

- lenguaje ambiguo;
- evidencia insuficiente;
- múltiples interpretaciones posibles;
- contradicción temática;
- clasificación basada únicamente en términos genéricos.

Ejemplo:

"Mejoraremos los servicios."

Puede corresponder a:

- Servicios Públicos.
- Administración Pública.
- Desarrollo Social.

Sin mayor evidencia, la confianza debe reducirse.

---

# 11.12 Factores que Incrementan la Confianza

La confianza aumenta cuando existe:

- coincidencia entre múltiples evidencias;
- presencia de términos específicos;
- relación directa entre acción y categoría;
- consistencia entre título y contenido;
- profundidad jerárquica justificada.

---

# 11.13 Registro de Confianza

Cada clasificación temática deberá almacenar:

- nivel de confianza;
- evidencias utilizadas;
- puntuación obtenida;
- categoría asignada;
- conflictos considerados;
- versión del modelo aplicada.

Ejemplo conceptual:

```json
{
  "tema": "Infraestructura",
  "subtema": "Calles y vías",
  "microtema": "Bacheo urbano",
  "confianza": "alta",
  "evidencias": [
    "reparación de calles",
    "baches"
  ]
}
```

---

# 11.14 Relación con el Sistema de Puntuación

El nivel de confianza utiliza como insumo la puntuación por evidencia, pero no depende exclusivamente de ella.

Una clasificación puede tener:

- alta puntuación;
- baja confianza;

si las evidencias son numerosas pero ambiguas.

También puede ocurrir:

- puntuación moderada;
- confianza alta;

cuando existe una evidencia altamente específica y directa.

---

# 11.15 Consideraciones Analíticas

Los niveles de confianza permiten diferenciar entre una clasificación temática sólida y una clasificación condicionada por limitaciones del lenguaje natural.

Este mecanismo evita presentar todos los resultados con el mismo grado de certeza metodológica y proporciona una medida transparente sobre la calidad de la evidencia disponible.

La confianza constituye un componente fundamental de la auditabilidad del sistema, ya que permite identificar qué clasificaciones poseen respaldo fuerte y cuáles requieren interpretación cuidadosa.

En conjunto con la evidencia temática, la puntuación y las reglas de resolución de conflictos, los niveles de confianza garantizan que la taxonomía funcione como un modelo explicable, reproducible y verificable.

---

# 12. Variables Generadas por el Pipeline

## 12.1 Propósito

El presente capítulo define las variables generadas por el Pipeline como resultado del proceso de clasificación temática.

Estas variables constituyen la representación estructurada de la información obtenida durante el análisis y permiten integrar los resultados del modelo taxonómico con:

- bases de datos analíticas;
- archivos de salida;
- indicadores institucionales;
- dashboards;
- procesos de auditoría.

El objetivo es garantizar que cada clasificación temática pueda ser almacenada, consultada y analizada de forma consistente.

---

# 12.2 Principios de Generación de Variables

Las variables generadas deben cumplir los siguientes principios:

1. Cada variable debe tener una definición clara.
2. Toda variable debe derivarse de evidencia observable.
3. La estructura debe mantenerse estable entre versiones compatibles.
4. Las variables deben permitir auditoría posterior.
5. No deben contener inferencias no verificables.
6. Deben conservar relación con el documento original.

---

# 12.3 Categorías de Variables

Las variables generadas se agrupan en seis categorías principales:

| Categoría | Propósito |
|-----------|-----------|
| Identificación | Relacionar el resultado con el documento analizado. |
| Clasificación temática | Representar los temas asignados. |
| Evidencia | Registrar los elementos que sustentan la clasificación. |
| Confianza | Expresar la solidez metodológica. |
| Trazabilidad | Permitir reconstrucción del proceso. |
| Analítica | Facilitar agregaciones e indicadores. |

---

# 12.4 Variables de Identificación

## document_id

### Definición

Identificador único del documento procesado.

### Propósito

Permite relacionar la clasificación temática con el contenido original.

---

## source_id

### Definición

Identificador de la fuente de origen del documento.

### Propósito

Permite agrupar resultados por origen de información.

---

## processing_date

### Definición

Fecha en la que el Pipeline realizó el procesamiento.

---

# 12.5 Variables de Clasificación Temática

## tema_principal

### Definición

Tema con mayor relevancia analítica dentro del documento.

### Tipo

Cadena de texto.

### Ejemplo:

```
Infraestructura
```

---

## temas_secundarios

### Definición

Lista de temas adicionales identificados dentro del documento.

### Tipo

Arreglo de valores.

### Ejemplo:

```json
[
 "Medio Ambiente",
 "Participación Ciudadana"
]
```

---

## subtema_principal

### Definición

Subcategoría asociada al tema principal cuando existe evidencia suficiente.

---

## microtema_principal

### Definición

Categoría de máxima especificidad alcanzada dentro del tema principal.

---

## profundidad_taxonomica

### Definición

Nivel jerárquico máximo alcanzado por la clasificación.

Valores posibles:

```
tema
subtema
microtema
```

---

# 12.6 Variables de Evidencia Temática

## evidencias_tematica

### Definición

Lista de evidencias utilizadas para justificar la clasificación.

Ejemplo:

```json
[
 "reparación de calles",
 "bacheo"
]
```

---

## tipo_evidencia

### Definición

Clasificación del tipo de evidencia utilizada.

Valores:

- lingüística;
- semántica;
- contextual;
- estructural.

---

## fortaleza_evidencia

### Definición

Nivel metodológico asignado a cada evidencia.

Valores:

- fuerte;
- moderada;
- débil.

---

## ubicacion_evidencia

### Definición

Posición aproximada de la evidencia dentro del documento cuando sea disponible.

Ejemplos:

- título;
- inicio;
- cuerpo;
- cierre.

---

# 12.7 Variables de Puntuación

## puntuacion_tematica

### Definición

Valor acumulado obtenido mediante la suma de evidencias asociadas a un tema.

---

## puntuacion_por_tema

### Definición

Distribución de puntuaciones para todos los temas candidatos.

Ejemplo:

```json
{
 "Infraestructura": 12,
 "Medio Ambiente": 6
}
```

---

## diferencia_competencia_tematica

### Definición

Distancia entre la puntuación del tema principal y los temas competidores.

### Propósito

Ayuda a evaluar claridad de predominancia temática.

---

# 12.8 Variables de Confianza

## confianza_tematica

### Definición

Nivel de confianza asignado a la clasificación temática.

Valores:

- alta;
- media;
- baja.

---

## confianza_por_nivel

### Definición

Confianza independiente para:

- tema;
- subtema;
- microtema.

---

## factores_confianza

### Definición

Elementos utilizados para determinar la confianza.

Ejemplo:

```json
[
 "evidencia directa",
 "múltiples indicadores",
 "baja ambigüedad"
]
```

---

# 12.9 Variables de Resolución de Conflictos

## temas_evaluados

### Definición

Lista de categorías consideradas durante el proceso.

---

## conflictos_detectados

### Definición

Registro de situaciones donde múltiples temas compitieron.

---

## regla_resolucion_aplicada

### Definición

Regla metodológica utilizada para seleccionar el resultado final.

Ejemplos:

- mayor evidencia;
- mayor especificidad;
- centralidad discursiva.

---

# 12.10 Variables de Trazabilidad

## taxonomy_version

### Definición

Versión del modelo taxonómico utilizada.

Ejemplo:

```
1.0.0
```

---

## pipeline_version

### Definición

Versión del Pipeline que ejecutó la clasificación.

---

## model_execution_id

### Definición

Identificador único de la ejecución analítica.

---

## classification_timestamp

### Definición

Marca temporal de la clasificación.

---

# 12.11 Variables Analíticas Derivadas

Estas variables pueden utilizarse posteriormente para generación de indicadores.

---

## frecuencia_tematica

### Definición

Cantidad de documentos asociados a un tema durante un periodo determinado.

---

## distribucion_tematica

### Definición

Proporción relativa de temas dentro de un conjunto de documentos.

---

## evolucion_tematica

### Definición

Cambio temporal de la presencia de temas dentro de la conversación digital.

---

## concentracion_tematica

### Definición

Nivel de concentración de documentos alrededor de determinados temas.

---

# 12.12 Ejemplo de Registro Completo

Ejemplo conceptual:

```json
{
 "document_id": "DOC-001",
 "tema_principal": "Infraestructura",
 "subtema_principal": "Calles y vías",
 "microtema_principal": "Bacheo urbano",
 "temas_secundarios": [
    "Servicios Públicos"
 ],
 "confianza_tematica": "alta",
 "puntuacion_tematica": 14,
 "taxonomy_version": "1.0.0"
}
```

---

# 12.13 Integración con analysis.json

Las variables generadas por el modelo temático forman parte de la estructura analítica utilizada por MIPA.

Su almacenamiento debe permitir:

- consulta individual;
- agregación estadística;
- generación de dashboards;
- auditoría metodológica.

La información temática deberá mantenerse separada conceptualmente de otros módulos analíticos como intención comunicativa o sentimiento.

---

# 12.14 Consideraciones Analíticas

Las variables generadas por el Pipeline representan la capa estructurada que conecta el análisis lingüístico con la explotación analítica del sistema.

Su diseño permite conservar simultáneamente:

- información del documento original;
- clasificación temática;
- evidencia utilizada;
- confianza metodológica;
- trazabilidad completa.

Estas variables garantizan que los resultados del modelo no sean únicamente etiquetas finales, sino registros analíticos auditables capaces de explicar cómo y por qué un documento fue asociado a determinadas categorías temáticas.

En conjunto con la taxonomía, las reglas de clasificación y el sistema de confianza, las variables generadas permiten transformar comunicación digital no estructurada en información organizada, reproducible y verificable.

---

# 13. Integración con el Pipeline

## 13.1 Propósito

El presente capítulo define la integración del **Modelo de Taxonomía Temática** con el Pipeline analítico de MIPA.

Su objetivo es establecer cómo las reglas, evidencias, variables y resultados generados por el modelo temático participan dentro del flujo completo de procesamiento de documentos.

La integración garantiza que la clasificación temática funcione como un componente modular, trazable y verificable dentro de la arquitectura analítica existente.

---

# 13.2 Principios de Integración

La integración del modelo temático se fundamenta en los siguientes principios:

1. La taxonomía funciona como un módulo independiente dentro del Pipeline.
2. Cada clasificación debe conservar relación con el documento original.
3. Los resultados temáticos deben generarse mediante reglas documentadas.
4. La información temática debe ser compatible con otros módulos analíticos.
5. Ningún módulo debe alterar la interpretación de otro.
6. Toda salida debe conservar trazabilidad metodológica.

---

# 13.3 Posición dentro del Flujo Analítico

El modelo temático participa dentro del flujo general de procesamiento de la siguiente manera:

```
Ingreso de documento

        ↓

Normalización del contenido

        ↓

Extracción de información lingüística

        ↓

Análisis temático

        ↓

Análisis de intención comunicativa

        ↓

Generación de variables analíticas

        ↓

Almacenamiento estructurado

        ↓

Visualización y explotación analítica
```

La clasificación temática constituye una dimensión independiente del análisis general del documento.

---

# 13.4 Entrada del Modelo Temático

El módulo de clasificación temática recibe como entrada:

- contenido textual normalizado;
- metadatos disponibles;
- identificador del documento;
- información estructural disponible;
- configuración vigente de la taxonomía.

Ejemplo conceptual:

```json
{
 "document_id": "DOC-001",
 "text": "Iniciamos reparación de calles municipales",
 "metadata": {
    "source": "red_social"
 }
}
```

---

# 13.5 Proceso Interno de Clasificación

El procesamiento temático sigue las siguientes etapas:

```
Documento recibido

↓

Identificación de conceptos relevantes

↓

Extracción de evidencias temáticas

↓

Comparación con taxonomía vigente

↓

Generación de temas candidatos

↓

Asignación de puntuaciones

↓

Resolución de conflictos

↓

Selección de temas

↓

Cálculo de confianza

↓

Generación de variables
```

Cada etapa debe producir resultados verificables.

---

# 13.6 Relación con el Modelo de Intención Comunicativa

El Modelo de Taxonomía Temática y el Modelo de Intención Comunicativa operan de manera complementaria.

La separación metodológica es:

| Modelo | Pregunta que responde |
|---|---|
| Intención Comunicativa | ¿Qué busca comunicar el mensaje? |
| Taxonomía Temática | ¿Sobre qué asunto trata el mensaje? |

Ejemplo:

Documento:

> "Invitamos a los vecinos a participar en la jornada de limpieza del parque."

Resultado de intención:

Intención Principal:

- Convocar.

Resultado temático:

Tema Principal:

- Medio Ambiente.

Tema Secundario:

- Participación Ciudadana.

Ambos análisis describen dimensiones diferentes del mismo contenido.

---

# 13.7 Integración con el Motor de Evidencias

El módulo temático utiliza el sistema de evidencia definido en este documento.

Cada clasificación debe conservar:

- evidencia detectada;
- categoría asociada;
- nivel de fortaleza;
- puntuación;
- confianza.

Esto permite reconstruir la decisión tomada por el Pipeline.

---

# 13.8 Integración con el Sistema de Puntuación

La puntuación temática se genera mediante la acumulación de evidencias compatibles.

Flujo conceptual:

```
Evidencia temática

↓

Peso asignado

↓

Puntuación por categoría

↓

Comparación entre candidatos

↓

Selección temática
```

La puntuación funciona como mecanismo cuantitativo de apoyo, pero siempre debe interpretarse junto con las reglas metodológicas.

---

# 13.9 Integración con analysis.json

Los resultados del modelo temático deben almacenarse dentro de la estructura analítica utilizada por MIPA.

Ejemplo conceptual:

```json
{
 "document_id": "DOC-001",

 "topics": {
    "primary": {
       "name": "Infraestructura",
       "confidence": "alta"
    },

    "secondary": [
       {
        "name": "Servicios Públicos",
        "confidence": "media"
       }
    ]
 }
}
```

La estructura exacta dependerá de la implementación vigente del sistema, manteniendo siempre los principios metodológicos definidos.

---

# 13.10 Integración con Base de Datos Analítica

Los resultados temáticos pueden alimentar tablas analíticas destinadas a:

- consultas históricas;
- agregaciones;
- indicadores;
- dashboards;
- análisis comparativos.

La información almacenada debe permitir responder:

- qué temas aparecen;
- cuándo aparecen;
- con qué frecuencia;
- con qué confianza;
- con qué evidencia fueron identificados.

---

# 13.11 Integración con Visualización

La clasificación temática permite generar representaciones como:

- distribución de temas;
- evolución temporal;
- comparación entre periodos;
- identificación de temas emergentes;
- análisis por fuente.

Las visualizaciones deben reflejar únicamente información generada por el modelo y no incorporar interpretaciones externas.

---

# 13.12 Control de Errores y Validación

Durante la integración, el Pipeline debe verificar:

- existencia del tema dentro de la taxonomía vigente;
- consistencia jerárquica;
- presencia de evidencia asociada;
- compatibilidad de versión;
- integridad de variables generadas.

Cualquier inconsistencia deberá registrarse para auditoría.

---

# 13.13 Trazabilidad del Proceso

Cada clasificación temática deberá poder reconstruirse mediante:

```
Documento original

↓

Evidencias identificadas

↓

Categorías evaluadas

↓

Puntuaciones obtenidas

↓

Conflictos resueltos

↓

Clasificación final

↓

Versión utilizada
```

Esta trazabilidad constituye un requisito fundamental del modelo.

---

# 13.14 Independencia Operativa

Aunque el modelo temático se integra con otros componentes del Pipeline, mantiene independencia conceptual.

La clasificación temática no debe verse afectada por:

- intención comunicativa detectada;
- sentimiento;
- valoración positiva o negativa;
- identidad del emisor.

Un mismo tema puede aparecer asociado a diferentes intenciones y posiciones comunicativas.

---

# 13.15 Consideraciones Analíticas

La integración del Modelo de Taxonomía Temática dentro del Pipeline permite transformar información textual no estructurada en una representación analítica organizada.

El modelo funciona como una capa semántica intermedia entre el contenido original y los indicadores generados por MIPA.

Su integración garantiza:

- consistencia entre análisis;
- separación de responsabilidades;
- trazabilidad completa;
- compatibilidad con otros módulos;
- capacidad de auditoría.

De esta forma, la taxonomía temática se incorpora al sistema como un componente científico y operativo que permite estudiar la conversación digital institucional desde una perspectiva estructurada, determinista y verificable.

---

# 14. Integración con analysis.json

## 14.1 Propósito

El presente capítulo define la relación entre el **Modelo de Taxonomía Temática** y el archivo estructurado **analysis.json** utilizado por MIPA como capa de intercambio y almacenamiento de resultados analíticos.

Su objetivo es establecer cómo los resultados de clasificación temática son representados dentro de una estructura digital que permita:

- almacenamiento persistente;
- consumo por otros módulos;
- generación de indicadores;
- visualización en dashboards;
- auditoría metodológica.

La integración mantiene el principio fundamental del proyecto:

> Toda salida analítica debe conservar la relación entre resultado, evidencia y metodología aplicada.

---

# 14.2 Principios de Integración

La incorporación de resultados temáticos dentro de `analysis.json` debe cumplir los siguientes principios:

1. La información temática debe mantener una estructura consistente.

2. Cada clasificación debe conservar su trazabilidad.

3. Los campos generados deben representar exclusivamente información obtenida por el Pipeline.

4. La estructura debe permitir clasificación multi-tema.

5. Debe existir compatibilidad entre la versión de la taxonomía y los resultados almacenados.

6. La información temática debe permanecer diferenciada de otros módulos analíticos.

---

# 14.3 Función de analysis.json dentro del Modelo

Dentro del flujo analítico de MIPA, `analysis.json` funciona como una representación estructurada de los resultados obtenidos después del procesamiento.

Su función no es almacenar únicamente etiquetas finales, sino conservar una representación analítica completa del proceso.

Incluye:

- clasificación temática;
- evidencia utilizada;
- nivel de confianza;
- variables derivadas;
- información de trazabilidad.

---

# 14.4 Estructura Conceptual

La información temática puede representarse conceptualmente mediante la siguiente estructura:

```json
{
  "document_id": "DOC-001",

  "topics": {

    "primary": {
      "topic": "Infraestructura",
      "subtopic": "Calles y vías",
      "microtopic": "Bacheo urbano",
      "confidence": "alta"
    },

    "secondary": [
      {
        "topic": "Servicios Públicos",
        "confidence": "media"
      }
    ]
  }
}
```

Esta representación conserva la jerarquía definida por la taxonomía.

---

# 14.5 Componentes Temáticos del JSON

## topics

### Definición

Nodo principal donde se almacenan los resultados de clasificación temática.

---

## primary

### Definición

Objeto que contiene la clasificación temática principal del documento.

Incluye:

- tema;
- subtema;
- microtema cuando exista;
- nivel de confianza.

---

## secondary

### Definición

Lista de temas secundarios identificados.

Permite representar la naturaleza multi-temática de la comunicación digital.

---

# 14.6 Registro de Evidencias

La estructura puede incluir las evidencias utilizadas para justificar cada clasificación.

Ejemplo:

```json
{
 "topic": "Infraestructura",

 "evidence": [
    {
      "text": "reparación de calles",
      "type": "lingüística",
      "strength": "fuerte"
    }
 ]
}
```

Esto permite reconstruir la decisión analítica.

---

# 14.7 Registro de Confianza

Cada clasificación temática debe conservar su nivel de confianza asociado.

Ejemplo:

```json
{
 "topic": "Salud",
 "confidence": {
    "level": "alta",
    "factors": [
       "evidencia directa",
       "alta especificidad"
    ]
 }
}
```

La confianza debe permanecer asociada al tema correspondiente.

---

# 14.8 Registro de Puntuación Temática

Cuando la implementación lo requiera, `analysis.json` puede almacenar la puntuación obtenida durante la evaluación temática.

Ejemplo:

```json
{
 "topic_scores": {

    "Infraestructura": 14,

    "Servicios Públicos": 6

 }
}
```

Esta información permite auditar la selección del tema principal.

---

# 14.9 Registro de Versión

Toda clasificación temática debe mantener referencia a la versión utilizada.

Ejemplo:

```json
{
 "taxonomy_version": "1.0.0"
}
```

Esto permite identificar exactamente qué reglas y categorías estaban vigentes durante el procesamiento.

---

# 14.10 Separación de Módulos Analíticos

La información temática debe mantenerse separada de:

- intención comunicativa;
- sentimiento;
- clasificación de usuarios;
- métricas externas.

Ejemplo conceptual:

```json
{
 "analysis": {

    "topic_analysis": {},

    "intent_analysis": {},

    "sentiment_analysis": {}

 }
}
```

Esta separación evita contaminación metodológica entre componentes.

---

# 14.11 Validaciones de Integridad

Antes de almacenar resultados temáticos en `analysis.json`, el Pipeline debe validar:

## Validación jerárquica

Que:

- el subtema pertenezca al tema;
- el microtema pertenezca al subtema.

---

## Validación de evidencia

Que cada clasificación tenga evidencia asociada.

---

## Validación de versión

Que la taxonomía utilizada exista y esté registrada.

---

## Validación estructural

Que los campos requeridos mantengan el formato esperado.

---

# 14.12 Ejemplo de Registro Completo

Ejemplo conceptual:

```json
{
 "document_id": "DOC-002",

 "topic_analysis": {

   "taxonomy_version": "1.0.0",

   "primary": {

      "topic": "Medio Ambiente",

      "subtopic": "Gestión de residuos",

      "microtopic": "Reciclaje comunitario",

      "confidence": "alta",

      "score": 12,

      "evidence": [
        "programa de reciclaje",
        "contenedores comunitarios"
      ]
   },

   "secondary": [

      {
       "topic": "Participación Ciudadana",
       "confidence": "media"
      }

   ]

 }
}
```

---

# 14.13 Compatibilidad con Dashboards

La estructura temática almacenada en `analysis.json` permite alimentar componentes visuales como:

- distribución temática;
- tendencias por periodo;
- ranking de temas;
- evolución histórica;
- análisis comparativo.

Los dashboards deberán consumir únicamente la información validada por el Pipeline.

---

# 14.14 Auditoría del Registro JSON

Una auditoría deberá poder responder:

- ¿Qué tema fue asignado?
- ¿Qué evidencias lo justificaron?
- ¿Qué puntuación obtuvo?
- ¿Qué nivel de confianza tenía?
- ¿Qué versión de la taxonomía se utilizó?
- ¿Qué conflictos fueron considerados?

Si estas respuestas pueden obtenerse directamente del registro, el proceso mantiene trazabilidad completa.

---

# 14.15 Consideraciones Analíticas

La integración con `analysis.json` representa el punto donde el modelo conceptual de taxonomía se transforma en información operativa utilizada por MIPA.

Esta integración permite conservar simultáneamente:

- estructura temática;
- evidencia;
- confianza;
- puntuación;
- versionado;
- relación con el documento original.

El resultado es una representación digital auditable que permite utilizar la clasificación temática en procesos analíticos posteriores sin perder transparencia metodológica.

De esta forma, `analysis.json` actúa como una capa estructurada de conocimiento que conecta el procesamiento lingüístico con la explotación analítica del sistema.

---

# 15. Versionado

## 15.1 Propósito

El sistema de versionado define el mecanismo mediante el cual MIPA controla los cambios realizados en la **Taxonomía Temática**, sus reglas de clasificación, estructuras jerárquicas y componentes asociados.

Su objetivo es garantizar que cualquier resultado analítico pueda ser relacionado con la versión exacta del modelo utilizado durante su generación.

El versionado constituye un elemento esencial de la auditabilidad del sistema, ya que permite responder:

- qué estructura temática estaba vigente;
- qué reglas fueron aplicadas;
- qué categorías existían durante el procesamiento;
- cuándo ocurrió una modificación;
- cómo comparar resultados entre versiones.

---

# 15.2 Principios de Versionado

El modelo de versionado se fundamenta en los siguientes principios:

1. Todo cambio metodológico debe quedar registrado.

2. Una clasificación generada debe conservar la versión utilizada.

3. Las modificaciones deben ser identificables y trazables.

4. No deben sobrescribirse versiones históricas utilizadas en análisis previos.

5. Los cambios deben diferenciarse según su impacto analítico.

6. La evolución de la taxonomía debe poder reconstruirse.

---

# 15.3 Componentes Versionados

El sistema mantiene control de versión sobre los siguientes componentes:

| Componente | Descripción |
|------------|-------------|
| Taxonomía temática | Estructura de temas, subtemas y microtemas. |
| Reglas de clasificación | Criterios utilizados para asignación temática. |
| Diccionario semántico | Relaciones conceptuales utilizadas por el modelo. |
| Sistema de evidencias | Definiciones y pesos asociados. |
| Variables generadas | Estructura de salida analítica. |
| Documentación metodológica | Descripción científica del modelo. |

---

# 15.4 Esquema de Versionado

MIPA utiliza un esquema de versionado basado en tres componentes:

```
MAJOR.MINOR.PATCH
```

Ejemplo:

```
1.2.3
```

Cada componente representa un nivel diferente de modificación.

---

# 15.5 Versión Mayor (MAJOR)

## Definición

Representa cambios que modifican de manera significativa la interpretación del modelo.

Se incrementa cuando existe:

- cambio estructural de la taxonomía;
- reorganización de familias temáticas;
- modificación de principios metodológicos;
- incompatibilidad con resultados anteriores.

Ejemplo:

```
1.x.x → 2.x.x
```

---

## Impacto

Una nueva versión mayor implica que los resultados generados con versiones anteriores deben considerarse dentro de su contexto histórico.

No deben mezclarse automáticamente sin validación metodológica.

---

# 15.6 Versión Menor (MINOR)

## Definición

Representa ampliaciones compatibles con la estructura existente.

Se incrementa cuando existe:

- incorporación de nuevos temas;
- creación de nuevos subtemas;
- expansión del diccionario semántico;
- mejora de cobertura temática.

Ejemplo:

```
1.2.x → 1.3.x
```

---

## Impacto

Los resultados pueden continuar siendo comparables, pero debe registrarse la versión específica utilizada.

---

# 15.7 Versión Correctiva (PATCH)

## Definición

Representa ajustes menores que no cambian la estructura conceptual.

Incluye:

- correcciones documentales;
- aclaraciones metodológicas;
- ajustes de descripción;
- corrección de errores de implementación.

Ejemplo:

```
1.2.3 → 1.2.4
```

---

## Impacto

Normalmente no modifica la interpretación de resultados existentes.

---

# 15.8 Registro de Cambios

Cada versión debe mantener un registro de modificaciones.

Ejemplo:

```markdown
## Versión 1.1.0

Fecha:
2026-07-14

Cambios:

- Nuevo subtema agregado:
  Participación Comunitaria.

- Actualización del diccionario semántico.

- Ajuste de evidencias asociadas.
```

---

# 15.9 Identificación de Versión en Resultados

Cada resultado generado por el Pipeline debe incluir:

- versión de taxonomía;
- versión del Pipeline;
- fecha de procesamiento.

Ejemplo:

```json
{
 "taxonomy_version": "1.0.0",
 "pipeline_version": "1.0.0",
 "processed_at": "2026-07-14"
}
```

---

# 15.10 Compatibilidad entre Versiones

Cuando se comparen resultados obtenidos con diferentes versiones deberá considerarse:

- cambios estructurales;
- categorías agregadas;
- categorías eliminadas;
- modificaciones semánticas.

La comparación histórica debe realizarse considerando la versión utilizada.

---

# 15.11 Migración de Resultados

Cuando una nueva versión requiera actualizar resultados históricos, deberá existir un proceso documentado de migración.

La migración debe conservar:

- documento original;
- clasificación anterior;
- nueva clasificación;
- reglas aplicadas;
- diferencias encontradas.

Ejemplo conceptual:

```
Resultado versión 1.0

↓

Proceso de migración

↓

Resultado versión 1.1

↓

Registro de diferencias
```

---

# 15.12 Control de Cambios No Permitidos

No deberán realizarse modificaciones silenciosas sobre:

- categorías existentes;
- definiciones temáticas;
- reglas de clasificación;
- variables almacenadas.

Toda modificación debe producir una nueva versión.

---

# 15.13 Relación con Auditoría

El versionado permite verificar:

- por qué dos análisis pueden producir resultados diferentes;
- qué cambios metodológicos ocurrieron;
- qué versión generó cada indicador;
- qué estructura temática estaba disponible en un periodo determinado.

La ausencia de versionado impediría una auditoría completa.

---

# 15.14 Relación con Reproducibilidad Científica

Un análisis es reproducible cuando otra persona puede reconstruir el mismo resultado utilizando:

- mismo documento;
- misma versión del modelo;
- mismas reglas;
- mismas configuraciones.

El versionado garantiza esta condición dentro de MIPA.

---

# 15.15 Consideraciones Analíticas

El versionado convierte la evolución de la taxonomía temática en un proceso controlado y documentado.

En sistemas de análisis de lenguaje natural, las categorías y reglas pueden evolucionar con el tiempo. Sin un mecanismo formal de control, los resultados históricos perderían comparabilidad y capacidad de auditoría.

Por esta razón, cada clasificación temática debe entenderse como una combinación de:

```
Documento analizado

+

Modelo utilizado

+

Versión aplicada

+

Evidencia encontrada

+

Reglas ejecutadas
```

El versionado asegura que MIPA mantenga consistencia metodológica a largo plazo, permitiendo evolución controlada sin perder trazabilidad científica.

---

# 16. Consideraciones Metodológicas Finales

## 16.1 Propósito

El presente capítulo consolida las consideraciones metodológicas fundamentales que rigen el funcionamiento del **Modelo de Taxonomía Temática** dentro de MIPA.

Su objetivo es establecer los límites interpretativos, principios científicos y condiciones de uso que deben mantenerse para garantizar que la clasificación temática sea:

- determinista;
- explicable;
- reproducible;
- auditable;
- metodológicamente consistente.

---

# 16.2 Naturaleza del Modelo Temático

La taxonomía temática representa un modelo de organización semántica del contenido digital analizado.

Su función es identificar:

- los asuntos tratados dentro de una comunicación;
- las áreas institucionales relacionadas;
- los niveles de especificidad alcanzados;
- la distribución temática de la conversación digital.

El modelo no intenta determinar:

- opiniones individuales;
- intención política;
- comportamiento electoral;
- aceptación ciudadana;
- impacto real fuera del entorno digital.

---

# 16.3 Relación entre Texto y Clasificación

Toda clasificación temática debe entenderse como una transformación estructurada:

```
Contenido digital

↓

Extracción de evidencia

↓

Evaluación semántica

↓

Asignación temática

↓

Representación analítica
```

La clasificación final no reemplaza el documento original, sino que constituye una representación organizada basada en evidencia.

---

# 16.4 Principio de No Inferencia Externa

El modelo no utiliza información externa al contenido analizado para asignar temas.

No se consideran:

- identidad política del emisor;
- contexto electoral;
- historial público de una institución;
- percepción social previa;
- interpretaciones externas.

La clasificación depende exclusivamente de la evidencia disponible dentro del documento.

---

# 16.5 Diferencia entre Tema e Importancia

La presencia de un tema no implica automáticamente importancia estratégica.

Ejemplo:

Un tema puede aparecer frecuentemente, pero eso no significa:

- mayor relevancia institucional;
- mayor impacto ciudadano;
- mayor prioridad política.

La taxonomía mide presencia temática, no importancia absoluta.

---

# 16.6 Diferencia entre Tema y Sentimiento

La clasificación temática es independiente del tono emocional.

Ejemplo:

Dos documentos pueden pertenecer al mismo tema:

Documento A:

> "Excelente trabajo en la reparación de calles."

Documento B:

> "Exigimos reparar las calles dañadas."

Tema:

- Infraestructura.

Pero pueden tener:

- sentimiento diferente;
- intención comunicativa diferente.

---

# 16.7 Diferencia entre Tema e Intención Comunicativa

El modelo temático responde:

> ¿Sobre qué trata el mensaje?

El modelo de intención comunicativa responde:

> ¿Qué busca realizar el mensaje?

Ejemplo:

Mensaje:

> "Solicitamos mejorar la seguridad del barrio."

Tema:

- Seguridad Ciudadana.

Intención:

- Solicitar.

Ambas dimensiones deben analizarse de manera independiente.

---

# 16.8 Limitaciones del Modelo

Aunque el sistema utiliza reglas deterministas y evidencia estructurada, existen limitaciones inherentes al lenguaje natural.

Entre ellas:

- ambigüedad semántica;
- expresiones indirectas;
- información incompleta;
- lenguaje coloquial;
- evolución de términos sociales.

Estas limitaciones son gestionadas mediante:

- niveles de confianza;
- registro de evidencias;
- resolución de conflictos;
- versionado.

---

# 16.9 Uso Responsable de Resultados

Los resultados temáticos deben utilizarse como herramienta de análisis y monitoreo.

Son adecuados para:

- identificar tendencias comunicativas;
- observar evolución de temas;
- organizar grandes volúmenes de información;
- generar indicadores descriptivos.

No deben utilizarse para:

- inferir intención electoral;
- predecir comportamiento individual;
- reemplazar estudios cualitativos;
- establecer conclusiones causales sin evidencia adicional.

---

# 16.10 Transparencia Analítica

Cada clasificación debe poder responder:

### ¿Qué tema fue asignado?

Mediante la taxonomía utilizada.

### ¿Por qué fue asignado?

Mediante las evidencias registradas.

### ¿Con qué nivel de confianza?

Mediante el sistema de confianza.

### ¿Con qué versión del modelo?

Mediante el control de versiones.

Esta capacidad constituye uno de los principios centrales de MIPA.

---

# 16.11 Reproducibilidad

Un tercero debe poder reconstruir una clasificación utilizando:

- mismo documento;
- misma versión de taxonomía;
- mismas reglas;
- misma configuración del Pipeline.

La reproducibilidad transforma el modelo en un sistema analítico verificable y no en una interpretación subjetiva.

---

# 16.12 Separación entre Medición y Interpretación

El Pipeline genera mediciones estructuradas:

- frecuencia temática;
- distribución;
- evolución temporal;
- presencia relativa.

La interpretación estratégica corresponde a una etapa posterior y debe realizarse considerando el contexto apropiado.

El modelo no sustituye el análisis humano, sino que proporciona una base organizada para realizarlo.

---

# 16.13 Aplicación dentro de MIPA

Dentro del sistema completo, la taxonomía temática funciona como una dimensión analítica que permite:

- organizar conversación digital;
- identificar asuntos recurrentes;
- comparar periodos;
- analizar concentración temática;
- complementar otras dimensiones del modelo.

Su valor proviene de combinar:

```
Clasificación temática

+

Evidencia

+

Confianza

+

Trazabilidad

+

Versionado
```

---

# 16.14 Criterio de Cierre Metodológico

El modelo se considera correctamente aplicado cuando:

- las categorías utilizadas pertenecen a una taxonomía definida;
- las asignaciones tienen evidencia registrada;
- los conflictos fueron resueltos mediante reglas;
- la confianza fue calculada;
- la versión utilizada está documentada;
- los resultados pueden ser auditados.

---

# 16.15 Consideraciones Analíticas Finales

La Taxonomía Temática de MIPA constituye una capa metodológica diseñada para transformar comunicación digital no estructurada en información organizada y verificable.

Su diseño prioriza:

- transparencia sobre complejidad innecesaria;
- evidencia sobre interpretación subjetiva;
- reproducibilidad sobre decisiones opacas;
- trazabilidad sobre resultados aislados.

El modelo reconoce que la comunicación pública es dinámica, contextual y compleja. Por esta razón, no busca reducirla a etiquetas simples, sino representar sus patrones temáticos mediante un sistema estructurado capaz de evolucionar de forma controlada.

La clasificación temática generada por MIPA debe entenderse como una medición descriptiva y auditable de la conversación digital, construida mediante reglas explícitas y evidencia verificable.

Con este enfoque, la taxonomía temática se integra como un componente científico del sistema, manteniendo los principios fundamentales del proyecto:

```
No cajas negras.

No inferencias ocultas.

No decisiones arbitrarias.

Solo evidencia, reglas y trazabilidad.
```

---

# 17. Glosario

## 17.1 Propósito

El presente glosario define los principales términos utilizados dentro del **Modelo de Taxonomía Temática de MIPA**.

Su objetivo es establecer un lenguaje común para la interpretación metodológica, técnica y analítica del modelo.

Las definiciones aquí descritas corresponden al uso específico dentro del contexto del sistema y no necesariamente representan definiciones generales fuera del proyecto.

---

# 17.2 Términos Fundamentales

## Análisis Temático

Proceso mediante el cual un documento es evaluado para identificar los asuntos, áreas o categorías conceptuales presentes dentro de su contenido.

---

## Categoría Temática

Unidad conceptual utilizada para organizar documentos según el asunto principal o secundario que representan.

Ejemplo:

```
Infraestructura
```

---

## Clasificación Temática

Proceso de asignación de uno o más temas a un documento mediante evidencia observable y reglas metodológicas.

---

## Documento

Unidad individual de información procesada por el Pipeline.

Puede corresponder a:

- publicación digital;
- comunicado;
- comentario;
- texto institucional;
- contenido ciudadano.

---

## Evidencia Temática

Elemento observable dentro del contenido que justifica la asignación de una categoría temática.

Puede ser:

- lingüística;
- semántica;
- contextual;
- estructural.

---

## Evidencia Fuerte

Indicador con relación directa y específica respecto a una categoría temática.

Ejemplo:

```
bacheo urbano
```

---

## Evidencia Moderada

Indicador relacionado con una categoría, pero que requiere contexto adicional.

Ejemplo:

```
obras
```

---

## Evidencia Débil

Indicador general con bajo poder discriminante.

Ejemplo:

```
desarrollo
```

---

# 17.3 Estructura Taxonómica

## Taxonomía Temática

Sistema organizado de categorías utilizado para clasificar contenido según relaciones jerárquicas y conceptuales.

---

## Tema

Nivel superior de clasificación que representa un área general de análisis.

Ejemplo:

```
Salud
```

---

## Subtema

Nivel intermedio que divide un tema general en áreas funcionales específicas.

Ejemplo:

```
Salud

└── Atención médica
```

---

## Microtema

Nivel de mayor especificidad dentro de la estructura temática.

Ejemplo:

```
Salud

└── Atención médica

    └── Jornadas médicas comunitarias
```

---

## Jerarquía Temática

Relación estructurada entre:

```
Tema

↓

Subtema

↓

Microtema
```

---

# 17.4 Clasificación y Decisión Analítica

## Tema Principal

Categoría temática con mayor relevancia dentro de un documento según evidencia y criterios metodológicos.

---

## Tema Secundario

Categoría adicional identificada cuando existe evidencia suficiente dentro del contenido.

---

## Clasificación Multi-Tema

Modelo que permite asignar múltiples categorías temáticas a un mismo documento.

---

## Conflicto Temático

Situación donde diferentes categorías compiten por representar el contenido analizado.

---

## Resolución de Conflictos

Proceso mediante el cual el Pipeline determina cómo priorizar o conservar categorías temáticas competidoras.

---

# 17.5 Confianza y Evidencia

## Nivel de Confianza

Representación metodológica de la solidez de una clasificación temática.

Valores:

- alta;
- media;
- baja.

---

## Puntuación Temática

Valor cuantitativo obtenido mediante la combinación de evidencias asociadas a una categoría.

---

## Trazabilidad

Capacidad del sistema para reconstruir el origen y proceso mediante el cual se generó un resultado.

Incluye:

- documento;
- evidencia;
- reglas;
- versión.

---

# 17.6 Componentes Técnicos

## Pipeline

Conjunto de procesos automatizados utilizados por MIPA para transformar documentos en resultados analíticos estructurados.

---

## analysis.json

Archivo estructurado donde se almacenan resultados analíticos generados por el sistema.

---

## Variable Analítica

Campo generado por el Pipeline que representa una característica medible o clasificable del análisis.

---

## Versionado

Sistema de control que permite identificar cambios realizados en modelos, reglas y estructuras analíticas.

---

# 17.7 Conceptos Metodológicos

## Determinismo

Propiedad mediante la cual una misma entrada procesada bajo las mismas condiciones produce resultados reproducibles.

---

## Auditabilidad

Capacidad de verificar cómo fue generado un resultado mediante evidencia y reglas documentadas.

---

## Reproducibilidad

Capacidad de obtener nuevamente un resultado utilizando los mismos datos, versión y metodología.

---

## Inferencia Externa

Conclusión obtenida utilizando información que no proviene directamente del contenido analizado.

El modelo excluye este tipo de inferencia.

---

## Representación Semántica

Proceso de capturar el significado conceptual de un texto más allá de coincidencias literales.

---

# 17.8 Consideración Final

El glosario establece una referencia común para mantener consistencia conceptual entre:

- documentación;
- implementación;
- análisis;
- auditoría.

El uso uniforme de estos términos garantiza que la interpretación del modelo permanezca alineada con los principios metodológicos de MIPA.

---

# 18. Referencias Metodológicas / Bibliografía

## 18.1 Propósito

El presente capítulo reúne las principales referencias académicas y metodológicas utilizadas como fundamento conceptual para el desarrollo del Modelo de Taxonomía Temática de MIPA.

Estas referencias proporcionan bases teóricas relacionadas con:

- clasificación temática;
- procesamiento de lenguaje natural;
- representación semántica;
- análisis de contenido;
- construcción de taxonomías;
- sistemas auditables de clasificación.

El modelo implementado en MIPA no depende exclusivamente de una metodología externa, sino que adapta principios científicos existentes a un sistema determinista y verificable.

---

# 18.2 Análisis de Contenido

## Krippendorff, K. (2018)

**Content Analysis: An Introduction to Its Methodology.  
SAGE Publications.**

Referencia fundamental para el diseño de procesos sistemáticos de análisis de contenido.

Aporta principios relacionados con:

- definición de categorías;
- codificación;
- confiabilidad;
- interpretación estructurada de textos.

---

## Neuendorf, K. A. (2017)

**The Content Analysis Guidebook.  
SAGE Publications.**

Referencia metodológica para construcción de esquemas de clasificación y análisis cuantitativo de contenido.

---

# 18.3 Procesamiento de Lenguaje Natural

## Jurafsky, D., & Martin, J. H.

**Speech and Language Processing.**

Obra de referencia sobre:

- procesamiento lingüístico;
- representación semántica;
- clasificación textual;
- modelos computacionales del lenguaje.

---

## Manning, C. D., Raghavan, P., & Schütze, H. (2008)

**Introduction to Information Retrieval.  
Cambridge University Press.**

Referencia para:

- recuperación de información;
- representación documental;
- clasificación basada en características.

---

# 18.4 Representación Semántica y Aprendizaje Automático

## Mikolov, T., Chen, K., Corrado, G., & Dean, J. (2013)

**Efficient Estimation of Word Representations in Vector Space.**

Referencia asociada al desarrollo de representaciones vectoriales del lenguaje.

Aporta fundamentos sobre relaciones semánticas computacionales.

---

## Devlin, J., Chang, M. W., Lee, K., & Toutanova, K. (2019)

**BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding.**

Referencia sobre modelos contextuales de representación lingüística.

---

# 18.5 Construcción de Taxonomías y Ontologías

## Gruber, T. R. (1993)

**A Translation Approach to Portable Ontology Specifications.**

Referencia clásica sobre definición formal de conceptos y relaciones dentro de estructuras de conocimiento.

---

## Uschold, M., & Gruninger, M. (1996)

**Ontologies: Principles, Methods and Applications.**

Aporta fundamentos para:

- organización conceptual;
- relaciones jerárquicas;
- representación del conocimiento.

---

# 18.6 Sistemas Explicables y Auditables

## Ribeiro, M. T., Singh, S., & Guestrin, C. (2016)

**"Why Should I Trust You?": Explaining the Predictions of Any Classifier.**

Referencia sobre interpretación y explicación de modelos de clasificación.

---

## Doshi-Velez, F., & Kim, B. (2017)

**Towards A Rigorous Science of Interpretable Machine Learning.**

Referencia sobre evaluación de interpretabilidad en sistemas analíticos.

---

# 18.7 Metodologías de Clasificación Documental

## Sebastiani, F. (2002)

**Machine Learning in Automated Text Categorization.**

Artículo de referencia sobre clasificación automática de documentos.

Incluye conceptos relacionados con:

- categorías;
- entrenamiento;
- evaluación;
- métricas de clasificación.

---

# 18.8 Aplicación Metodológica en MIPA

Las referencias anteriores sirven como fundamento conceptual para:

- diseño de categorías;
- construcción jerárquica;
- clasificación temática;
- evaluación de evidencia;
- trazabilidad metodológica.

El modelo MIPA adapta estos principios bajo una condición específica:

```
La clasificación debe permanecer explicable,
verificable y auditable.
```

---

# 18.9 Consideraciones Finales

La bibliografía utilizada establece el marco científico sobre el cual se construye la Taxonomía Temática de MIPA.

Sin embargo, el modelo desarrollado mantiene una orientación propia:

- no utiliza cajas negras;
- no depende exclusivamente de predicciones probabilísticas;
- conserva evidencia explícita;
- registra decisiones analíticas;
- permite auditoría completa.

La combinación entre fundamentos académicos y reglas deterministas permite construir un sistema capaz de analizar comunicación digital institucional manteniendo rigor metodológico, transparencia y reproducibilidad.