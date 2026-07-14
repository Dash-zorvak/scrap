# MIPA — Motor de Inteligencia Política Auditada
## Project Charter
**Documento:** 000_PROJECT_CHARTER.md  
**Estado:** APROBADO (Baseline)  
**Versión metodológica:** MIPA 1.0.0  
**Clasificación:** Normativo (Obligatorio)  

---

# 1. Propósito del documento

Este documento constituye el contrato fundacional del proyecto MIPA.

Define el propósito, alcance, principios, responsabilidades y objetivos del sistema. Todo el desarrollo técnico, metodológico y operativo deberá alinearse con este documento.

Este documento tiene prioridad sobre cualquier decisión de implementación.

En caso de conflicto entre el código y este documento, prevalece este documento.

---

# 2. Visión

Construir el sistema de inteligencia ciudadana más transparente, reproducible y auditable posible para el análisis de conversación pública digital.

MIPA transforma evidencia digital pública en conocimiento verificable mediante procesos deterministas, validación humana y metodologías explícitas.

El objetivo no es producir opiniones.

El objetivo es producir evidencia organizada.

---

# 3. Misión

Convertir publicaciones, comentarios, reacciones y contenido digital público en indicadores reproducibles que permitan comprender el comportamiento observable de la conversación digital.

Cada indicador deberá poder ser explicado, auditado y reconstruido desde la evidencia original.

---

# 4. Problema que resuelve

Actualmente la mayoría de dashboards políticos presentan indicadores cuyo origen es desconocido.

Generalmente:

- no muestran la metodología;
- no muestran las fórmulas;
- no muestran la evidencia;
- no muestran las limitaciones;
- dependen del criterio del analista;
- dependen del razonamiento de un LLM.

Esto genera indicadores difíciles de verificar y poca confianza en los resultados.

MIPA elimina ese problema.

---

# 5. Objetivo General

Diseñar un motor analítico capaz de producir indicadores oficiales mediante procesos deterministas, completamente auditables y respaldados por evidencia verificable.

---

# 6. Objetivos específicos

El sistema deberá:

- centralizar la evidencia digital pública;
- preservar la evidencia original;
- calcular indicadores mediante modelos deterministas;
- separar cálculo y narrativa;
- permitir auditoría completa;
- mantener trazabilidad hasta la fuente original;
- comunicar resultados comprensibles para usuarios no técnicos.

---

# 7. Alcance

MIPA analiza únicamente actividad digital observable proveniente de fuentes públicas.

Entre ellas:

- Facebook
- TikTok
- medios digitales
- sitios oficiales
- fuentes externas configuradas por el proyecto

El alcance del sistema se limita exclusivamente al contenido disponible para observación pública.

---

# 8. Fuera de alcance

MIPA no pretende:

- predecir elecciones;
- estimar intención de voto;
- reemplazar estudios demoscópicos;
- sustituir encuestas científicas;
- inferir atributos personales;
- realizar perfiles psicológicos;
- manipular opinión pública;
- generar propaganda;
- producir conclusiones sin evidencia.

---

# 9. Producto

MIPA no es un dashboard.

MIPA no es un modelo de IA.

MIPA no es un scraper.

MIPA es una metodología implementada mediante software.

El dashboard constituye únicamente uno de sus mecanismos de visualización.

---

# 10. Principios Fundamentales

Toda evolución del sistema deberá respetar los siguientes principios.

## P-001 Reproducibilidad

Todo indicador oficial deberá poder calcularse nuevamente utilizando exactamente los mismos datos y producir exactamente el mismo resultado.

---

## P-002 Determinismo

Los cálculos oficiales nunca dependerán del razonamiento de un modelo de lenguaje.

---

## P-003 Trazabilidad

Todo resultado deberá poder rastrearse hasta la evidencia que lo originó.

---

## P-004 Evidencia

Ninguna conclusión podrá existir sin evidencia verificable.

---

## P-005 Explicabilidad

Todo indicador deberá explicar:

- cómo fue calculado;
- qué variables utilizó;
- qué representa;
- qué no representa.

---

## P-006 Auditoría

Todo cálculo deberá poder ser auditado por un tercero.

---

## P-007 Transparencia

Las fórmulas, reglas de negocio y metodología deberán estar documentadas.

---

## P-008 Separación de responsabilidades

Cada componente tendrá una única responsabilidad claramente definida.

---

## P-009 Conservación de evidencia

La evidencia original nunca será modificada por procesos analíticos.

---

## P-010 Evolución controlada

Toda modificación metodológica requerirá incremento de versión metodológica.

---

# 11. Arquitectura Conceptual

El sistema se divide en seis dominios independientes.

## Dominio de Ingesta

Responsable de recibir evidencia.

No realiza cálculos analíticos.

---

## Dominio de Persistencia

Responsable del almacenamiento permanente.

No interpreta información.

---

## Dominio Analítico

Responsable de producir indicadores.

No genera narrativas.

---

## Dominio de Evidencias

Responsable de mantener la relación entre indicadores y evidencia.

---

## Dominio Narrativo

Responsable de comunicar resultados.

Nunca modifica indicadores.

Nunca recalcula métricas.

---

## Dominio de Visualización

Responsable de presentar información.

Nunca calcula.

Nunca interpreta.

Nunca modifica datos.

---

# 12. Separación de responsabilidades

La arquitectura oficial queda definida de la siguiente manera.

| Componente | Responsabilidad |
|------------|-----------------|
| Panel de Carga | Ingesta |
| SQLite | Persistencia |
| Pipeline | Transformación |
| Motor Analítico | Cálculo |
| Motor de Evidencias | Relación indicador ↔ evidencia |
| Motor Narrativo | Comunicación |
| Dashboard | Visualización |

Ningún componente podrá asumir responsabilidades pertenecientes a otro dominio.

---

# 13. Principio de Cadena de Confianza

Todo dato deberá conservar la siguiente cadena de trazabilidad:

Captura

↓

Extracción

↓

Validación Humana

↓

Persistencia

↓

Cálculo

↓

Indicador

↓

Narrativa

↓

Dashboard

La cadena deberá poder recorrerse en ambos sentidos.

---

# 14. Modelo de Confianza

La confianza del sistema dependerá exclusivamente de:

- calidad de la evidencia;
- calidad del proceso de validación;
- calidad del modelo analítico.

Nunca dependerá de la autoridad del modelo de IA utilizado.

---

# 15. Rol de la Inteligencia Artificial

Los modelos de lenguaje podrán utilizarse para:

- extracción estructurada;
- clasificación;
- asistencia al analista;
- redacción narrativa;
- resumen ejecutivo.

Los modelos de lenguaje no podrán:

- producir indicadores oficiales;
- modificar cálculos;
- alterar métricas;
- sustituir procesos deterministas.

---

# 16. Fuente Oficial de la Verdad

La fuente oficial de la verdad será la evidencia almacenada.

No serán fuente oficial:

- prompts;
- conversaciones;
- narrativas;
- respuestas del LLM;
- interpretación humana.

---

# 17. Gobernanza Metodológica

Toda modificación deberá clasificarse como:

## Metodológica

Afecta la interpretación científica.

Requiere nueva versión metodológica.

---

## Técnica

Afecta únicamente la implementación.

No modifica la metodología.

---

## Operativa

Afecta configuración o ejecución.

No modifica metodología ni arquitectura.

---

# 18. Criterios de Éxito

MIPA será considerado exitoso cuando cualquier auditor independiente pueda:

1. reconstruir cualquier indicador;
2. verificar cada cálculo;
3. acceder a la evidencia correspondiente;
4. comprender las limitaciones del indicador;
5. reproducir exactamente el mismo resultado.

---

# 19. Criterios de Aceptación

La implementación deberá garantizar que:

- ningún indicador dependa exclusivamente de un LLM;
- toda narrativa posea evidencia;
- toda métrica posea metodología documentada;
- toda evidencia posea trazabilidad;
- el Dashboard no realice cálculos;
- el sistema pueda reconstruir cualquier resultado histórico utilizando la misma metodología.

---

# 20. Definición Oficial de MIPA

MIPA (Motor de Inteligencia Política Auditada) es una metodología implementada mediante software para transformar actividad digital pública en indicadores reproducibles, auditables y explicables, preservando la trazabilidad hacia la evidencia original y comunicando sus resultados mediante procesos transparentes y metodológicamente documentados.

---

# 21. Vigencia

Este documento constituye la base normativa del proyecto.

Todos los documentos posteriores deberán desarrollar, ampliar o implementar las reglas aquí establecidas.

Ningún documento posterior podrá contradecir este Project Charter sin una nueva versión metodológica aprobada.

---

# Control del Documento

| Campo | Valor |
|--------|-------|
| Documento | 000_PROJECT_CHARTER.md |
| Estado | Aprobado |
| Versión | 1.0.0 |
| Tipo | Normativo |
| Dependencias | Ninguna |
| Sustituye | Ninguno |
| Referenciado por | Todos los documentos de arquitectura |
| Última actualización | Baseline MIPA 1.0 |