# MIPA — Motor de Inteligencia Política Auditada
## DATA MODEL
**Documento:** 003_DATA_MODEL.md  
**Estado:** APROBADO (Baseline)  
**Versión metodológica:** MIPA 1.0.0  
**Clasificación:** Normativo (Obligatorio)

---

# 1. Propósito

Este documento define el modelo oficial de datos de MIPA.

Su objetivo es establecer cómo debe representarse la información durante todo su ciclo de vida, desde la captura hasta la generación de indicadores.

Este documento no define tecnologías.

Define únicamente la estructura conceptual de los datos.

---

# 2. Principios del Modelo de Datos

El modelo de datos deberá cumplir los siguientes principios.

## MD-001 Inmutabilidad

La evidencia original nunca será modificada.

Toda transformación generará nuevos datos derivados.

---

## MD-002 Trazabilidad

Todo registro derivado deberá conocer exactamente cuál evidencia lo originó.

---

## MD-003 Versionado

Toda transformación deberá registrar:

- versión metodológica;
- versión del pipeline;
- fecha de cálculo;
- identificador del proceso.

---

## MD-004 Reproducibilidad

El mismo conjunto de evidencia deberá producir exactamente el mismo conjunto de datos derivados.

---

## MD-005 Separación

La evidencia y los resultados derivados nunca compartirán la misma responsabilidad.

---

# 3. Ciclo de Vida del Dato

Todo dato recorrerá obligatoriamente el siguiente ciclo.

```
Captura

↓

Extracción

↓

Validación Humana

↓

Persistencia

↓

Normalización

↓

Transformación

↓

Agregación

↓

Indicador

↓

Narrativa

↓

Visualización
```

No podrán omitirse etapas.

---

# 4. Clasificación Oficial de los Datos

MIPA reconoce cinco categorías oficiales.

## Nivel 1 — Evidencia

Información observada directamente.

Ejemplos:

- publicación;
- comentario;
- reacción;
- enlace;
- captura;
- imagen.

---

## Nivel 2 — Datos Normalizados

Información adaptada al modelo interno.

Ejemplos:

- fechas ISO;
- números enteros;
- identificadores;
- plataformas normalizadas.

---

## Nivel 3 — Datos Derivados

Resultados obtenidos mediante procesos matemáticos.

Ejemplos:

- engagement;
- velocidad;
- frecuencia;
- distribución.

---

## Nivel 4 — Indicadores

Resultados analíticos oficiales.

Ejemplos:

- Pulso IQ;
- Riesgo;
- Concentración temática;
- Polarización.

---

## Nivel 5 — Narrativas

Interpretación textual de los indicadores.

---

# 5. Entidades Oficiales

El modelo oficial reconoce las siguientes entidades.

## Fuente

Representa el origen de la información.

Ejemplos:

Facebook

TikTok

Medio digital

Portal oficial

---

## Publicación

Unidad principal de contenido.

Una publicación puede contener múltiples comentarios.

---

## Comentario

Unidad mínima de conversación.

Cada comentario pertenece exactamente a una publicación.

---

## Reacción

Representa una interacción cuantificable.

Ejemplos:

Like

Love

Angry

Wow

Care

Favorite

---

## Evidencia

Representa el vínculo verificable entre un dato y su origen.

---

## Indicador

Resultado calculado.

---

## Narrativa

Explicación generada a partir de indicadores.

---

# 6. Relaciones

Las relaciones oficiales quedan definidas como:

```
Fuente

1

↓

N

Publicaciones

↓

1

↓

N

Comentarios

↓

N

↓

N

Clasificaciones

↓

N

↓

1

Indicadores

↓

1

↓

N

Narrativas
```

---

# 7. Identificadores

Toda entidad deberá poseer un identificador permanente.

Los identificadores nunca cambiarán.

Nunca dependerán del orden de inserción.

Nunca dependerán del Dashboard.

---

# 8. Identidad del Registro

Todo registro deberá incluir como mínimo.

- identificador;
- fecha de creación;
- fecha de captura;
- plataforma;
- fuente;
- estado;
- versión metodológica.

---

# 9. Estados Oficiales

Todo registro podrá encontrarse únicamente en uno de los siguientes estados.

Capturado

↓

Extraído

↓

Validado

↓

Persistido

↓

Procesado

↓

Publicado

Estados adicionales deberán documentarse metodológicamente.

---

# 10. Normalización

Antes de cualquier cálculo deberán normalizarse.

- fechas;
- horas;
- zonas horarias;
- formatos numéricos;
- codificación;
- emojis;
- caracteres especiales;
- plataformas;
- identificadores.

---

# 11. Integridad

Todo registro deberá satisfacer.

## Integridad estructural

Los campos obligatorios deberán existir.

---

## Integridad referencial

Toda referencia deberá existir.

---

## Integridad temporal

Las fechas deberán ser coherentes.

---

## Integridad metodológica

Los datos deberán corresponder a la versión metodológica vigente.

---

# 12. Evidencia

Toda evidencia deberá conservar.

- URL original;
- plataforma;
- fecha de captura;
- identificador interno;
- hash de integridad;
- fuente;
- estado de validación.

---

# 13. Metadatos

Todo dato derivado deberá registrar.

- fecha de cálculo;
- algoritmo utilizado;
- versión del algoritmo;
- versión metodológica;
- usuario o proceso generador;
- identificador del lote.

---

# 14. Datos Derivados

Los datos derivados nunca podrán sobrescribir evidencia.

Toda transformación generará nuevos registros.

---

# 15. Historial

Toda modificación deberá conservar historial.

Nunca se perderá información por sobrescritura.

El historial deberá permitir reconstruir cualquier versión anterior.

---

# 16. Temporalidad

Todos los cálculos deberán asociarse explícitamente a un período.

Ejemplos.

- últimas 24 horas;
- semana;
- mes;
- trimestre;
- personalizado.

El período forma parte del indicador.

No constituye un filtro visual.

---

# 17. Agregaciones

Toda agregación deberá especificar.

- universo analizado;
- cantidad de registros;
- criterios de inclusión;
- criterios de exclusión.

---

# 18. Eliminación

La eliminación física de evidencia queda prohibida.

Únicamente podrá cambiar su estado.

Ejemplos.

Activo

Descartado

Duplicado

Inválido

Oculto

Nunca se eliminará sin dejar trazabilidad.

---

# 19. Compatibilidad

El modelo deberá permitir incorporar nuevas plataformas sin modificar las entidades existentes.

La incorporación de nuevas fuentes no podrá romper indicadores históricos.

---

# 20. Independencia

El modelo de datos será independiente de.

- SQLite;
- PostgreSQL;
- DuckDB;
- MySQL;
- archivos JSON;
- formatos Parquet.

La tecnología constituye únicamente un mecanismo de almacenamiento.

---

# 21. Restricciones

Queda prohibido.

- almacenar indicadores dentro de las bases fuente;
- modificar evidencia durante el cálculo;
- recalcular evidencia;
- duplicar registros oficiales;
- utilizar el Dashboard como almacenamiento.

---

# 22. Criterios de Aceptación

El modelo de datos será considerado correctamente implementado cuando.

- toda evidencia pueda localizarse mediante su identificador;
- todo indicador pueda reconstruirse desde la evidencia;
- todo dato derivado conserve trazabilidad;
- ninguna transformación modifique la evidencia original;
- el historial permita reconstruir cualquier estado previo.

---

# 23. Vigencia

El presente documento define el modelo oficial de datos de MIPA.

Toda implementación futura deberá ajustarse a las reglas aquí descritas.

---

# Control del Documento

| Campo | Valor |
|--------|-------|
| Documento | 003_DATA_MODEL.md |
| Estado | Aprobado |
| Versión | 1.0.0 |
| Tipo | Normativo |
| Depende de | 000_PROJECT_CHARTER.md, 001_FOUNDATION.md, 002_ARCHITECTURE.md |
| Referenciado por | 004_PIPELINE.md, 005_EVIDENCE_MODEL.md |
| Última actualización | Baseline MIPA 1.0 |