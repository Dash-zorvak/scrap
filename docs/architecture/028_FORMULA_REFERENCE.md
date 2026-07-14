# MIPA — Motor de Inteligencia Política Auditada
## FORMULA_REFERENCE
**Documento:** 028_FORMULA_REFERENCE.md  
**Estado:** APROBADO (Baseline)  
**Versión metodológica:** MIPA 1.0.0  
**Clasificación:** Especificación Técnica (Obligatorio)

---

# 1. Propósito

Este documento define el catálogo oficial de fórmulas matemáticas utilizadas por MIPA.

Toda métrica, indicador e índice deberá derivarse exclusivamente de las fórmulas aquí documentadas.

No podrán existir cálculos implícitos ni fórmulas ocultas dentro del código.

---

# 2. Objetivos

Las fórmulas oficiales tienen como propósito.

- garantizar reproducibilidad;
- facilitar auditorías;
- eliminar ambigüedad;
- permitir validación matemática;
- asegurar consistencia entre versiones.

---

# 3. Principios

## FORM-001

Toda fórmula tendrá un identificador único.

---

## FORM-002

Toda fórmula tendrá una definición matemática.

---

## FORM-003

Toda fórmula deberá documentar sus variables.

---

## FORM-004

Toda fórmula deberá indicar su unidad de salida.

---

## FORM-005

Toda modificación requerirá una nueva versión metodológica.

---

# 4. Alcance

Este documento aplica a.

- métricas
- indicadores
- índices
- normalizaciones
- ponderaciones
- penalizaciones

---

# 5. Estructura Oficial

Cada fórmula deberá documentarse mediante la siguiente estructura.

| Campo | Descripción |
|--------|-------------|
| formula_id | Identificador único |
| formula_name | Nombre oficial |
| description | Objetivo |
| variables | Variables utilizadas |
| expression | Expresión matemática |
| output | Resultado esperado |
| unit | Unidad |
| version | Versión metodológica |

---

# 6. Variables

Las fórmulas únicamente podrán utilizar variables documentadas en.

026_PIPELINE_VARIABLES.md

Queda prohibido utilizar variables no documentadas.

---

# 7. Normalización

Toda fórmula deberá indicar si trabaja con.

- valores crudos;
- valores normalizados;
- percentiles;
- escalas transformadas.

---

# 8. Ponderaciones

Toda ponderación utilizada deberá documentar.

- origen;
- justificación;
- rango permitido;
- versión.

No podrán existir pesos ocultos.

---

# 9. Penalizaciones

Las penalizaciones deberán documentar.

- condición de activación;
- intensidad;
- efecto matemático;
- límites.

---

# 10. Índices Compuestos

Todo índice compuesto deberá especificar.

- componentes;
- pesos;
- método de agregación;
- normalización;
- límites.

---

# 11. Trazabilidad

Toda fórmula deberá permitir responder.

- qué variables utilizó;
- qué versión aplicó;
- qué resultado produjo;
- durante qué ejecución.

---

# 12. Reproducibilidad

Una fórmula será reproducible cuando.

- produzca siempre el mismo resultado;
- reciba exactamente las mismas entradas;
- utilice la misma versión metodológica.

---

# 13. Auditoría

Toda fórmula deberá poder reconstruirse completamente.

No podrán existir operaciones internas no documentadas.

---

# 14. Versionado

Cada fórmula deberá registrar.

- formula_version;
- methodology_version;
- pipeline_version.

---

# 15. Compatibilidad

Las fórmulas existentes no cambiarán de significado entre versiones.

Cuando una modificación altere el resultado deberá crearse una nueva versión.

---

# 16. Restricciones

Queda prohibido.

- modificar fórmulas en producción;
- utilizar constantes no documentadas;
- incorporar parámetros ocultos;
- recalibrar pesos manualmente.

---

# 17. Validación

Antes de utilizar una fórmula el Pipeline deberá verificar.

- existencia;
- versión;
- variables requeridas;
- integridad;
- compatibilidad.

---

# 18. Relación con analytics.db

Toda fórmula implementada deberá encontrarse registrada en la tabla.

formula

descrita en.

025_ANALYTICS_DB_DICTIONARY.md

---

# 19. Relación con el Pipeline

El Pipeline será el único responsable de ejecutar las fórmulas.

El Dashboard nunca ejecutará operaciones matemáticas.

---

# 20. Relación con Narrativas

Las narrativas deberán utilizar únicamente resultados producidos por fórmulas oficiales.

Nunca realizarán cálculos propios.

---

# 21. Transparencia

Todo indicador mostrado al usuario deberá poder vincularse con.

- fórmula utilizada;
- variables;
- evidencia;
- referencias.

---

# 22. Catálogo Oficial

El catálogo completo de expresiones matemáticas se documentará en futuras versiones metodológicas mediante anexos especializados.

Este documento establece la estructura obligatoria que deberán seguir todas ellas.

---

# 23. Criterios de Aceptación

El catálogo de fórmulas será considerado correctamente implementado cuando.

- todas las fórmulas estén documentadas;
- toda operación sea reproducible;
- toda variable esté identificada;
- toda ponderación sea pública;
- toda ejecución sea auditable.

---

# 24. Vigencia

Este documento constituye la especificación oficial de las fórmulas matemáticas utilizadas por MIPA.

Toda modificación requerirá actualización de la versión metodológica.

---

# Control del Documento

| Campo | Valor |
|--------|-------|
| Documento | 028_FORMULA_REFERENCE.md |
| Estado | Aprobado |
| Versión | 1.0.0 |
| Tipo | Especificación Técnica |
| Depende de | 000_PROJECT_CHARTER.md – 027_JSON_SCHEMA_REFERENCE.md |
| Referenciado por | 029_IMPLEMENTATION_GUIDE.md, Appendix A05_SCORING_TABLES.md |
| Última actualización | Baseline MIPA 1.0 |