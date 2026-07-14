# MIPA — Motor de Inteligencia Política Auditada
## JSON_CONTRACTS
**Documento:** 009_JSON_CONTRACTS.md  
**Estado:** APROBADO (Baseline)  
**Versión metodológica:** MIPA 1.0.0  
**Clasificación:** Normativo (Obligatorio)

---

# 1. Propósito

Este documento define los contratos oficiales de intercambio de datos de MIPA.

Los contratos JSON representan la única interfaz autorizada entre los distintos componentes del sistema.

Su finalidad es desacoplar completamente la arquitectura para que cada módulo pueda evolucionar sin afectar al resto del Pipeline.

---

# 2. Objetivos

Los contratos JSON buscan garantizar.

- compatibilidad;
- estabilidad;
- independencia;
- versionado;
- validación;
- interoperabilidad.

---

# 3. Alcance

Todo intercambio entre módulos deberá realizarse mediante contratos documentados.

No se permitirá intercambio implícito de estructuras.

---

# 4. Principios

## JSON-001

Todo contrato será versionado.

---

## JSON-002

Todo contrato será determinista.

---

## JSON-003

Todo contrato será validable mediante esquema.

---

## JSON-004

Todo contrato será independiente de la implementación.

---

## JSON-005

La compatibilidad hacia atrás deberá preservarse siempre que sea posible.

---

# 5. Contratos Oficiales

MIPA reconoce los siguientes contratos.

| Contrato | Responsable |
|----------|-------------|
| ingestion.json | Panel de Carga |
| validation.json | Validación Humana |
| analytics.json | Pipeline Analítico |
| dashboard_snapshot.json | Dashboard |
| narrative.json | Motor Narrativo |
| audit.json | Auditoría |

Cada contrato posee un propósito específico.

---

# 6. ingestion.json

Representa la salida del Panel de Carga.

Contiene exclusivamente.

- publicaciones extraídas;
- comentarios;
- métricas observadas;
- capturas;
- metadatos de extracción.

No contiene indicadores.

---

# 7. validation.json

Representa la salida del proceso de validación humana.

Contiene.

- registros aprobados;
- registros rechazados;
- correcciones;
- observaciones;
- estado de validación.

Todo registro incluido en este contrato podrá ingresar al Pipeline.

---

# 8. analytics.json

Representa la salida oficial del Pipeline Analítico.

Contiene únicamente.

- variables;
- métricas;
- indicadores;
- índices;
- referencias;
- metadatos.

No contiene narrativa.

---

# 9. dashboard_snapshot.json

Representa el estado que consumirá el Dashboard.

Contiene.

- indicadores;
- narrativas;
- referencias;
- visualizaciones;
- configuración.

El Dashboard nunca calculará información.

Únicamente representará este contrato.

---

# 10. narrative.json

Representa la salida del Motor Narrativo.

Incluye.

- narrativas;
- conclusiones;
- referencias;
- limitaciones.

Nunca incluye cálculos.

---

# 11. audit.json

Representa el resultado completo de una ejecución del Pipeline.

Incluye.

- fecha;
- duración;
- versión;
- errores;
- advertencias;
- registros procesados;
- registros descartados;
- identificador de ejecución.

---

# 12. Estructura General

Todo contrato deberá incluir como mínimo.

```json
{
  "schema_version": "",
  "pipeline_version": "",
  "methodology_version": "",
  "generated_at": "",
  "run_id": "",
  "data": {}
}
```

Estos campos son obligatorios.

---

# 13. Versionado

Cada contrato deberá declarar.

- versión del esquema;
- versión metodológica;
- versión del Pipeline.

Las versiones deberán permanecer visibles.

---

# 14. Compatibilidad

Los cambios se clasifican en.

## Compatible

Agregar campos opcionales.

---

## Condicional

Modificar comportamiento documentado.

---

## Incompatible

Eliminar campos obligatorios.

Renombrar estructuras.

Modificar significado de datos.

---

# 15. Validación

Todo contrato deberá validarse automáticamente antes de publicarse.

Como mínimo deberán verificarse.

- estructura;
- tipos;
- obligatoriedad;
- coherencia;
- referencias.

---

# 16. Trazabilidad

Cada contrato deberá indicar.

- qué ejecución lo produjo;
- qué metodología utilizó;
- qué Pipeline lo generó.

---

# 17. Persistencia

Los contratos publicados deberán conservarse para auditoría.

Nunca deberán sobrescribirse sin conservar historial.

---

# 18. Atomicidad

La publicación de un contrato será atómica.

Nunca podrán existir archivos parcialmente escritos.

---

# 19. Independencia

Los contratos deberán ser independientes de.

- SQLite;
- PostgreSQL;
- DuckDB;
- formato interno de clases;
- implementación del código.

Representan únicamente intercambio de información.

---

# 20. Restricciones

Queda prohibido.

- incluir lógica de negocio;
- incluir código ejecutable;
- incluir resultados experimentales no identificados;
- modificar contratos manualmente en producción.

---

# 21. Contratos y Dashboard

El Dashboard únicamente podrá consumir.

dashboard_snapshot.json

No podrá consultar bases de datos.

No podrá recalcular indicadores.

No podrá modificar contratos.

---

# 22. Contratos y Pipeline

El Pipeline podrá consumir.

- ingestion.json
- validation.json

Y producirá.

- analytics.json
- dashboard_snapshot.json
- audit.json

---

# 23. Contratos y Narrativa

El Motor Narrativo consumirá exclusivamente.

analytics.json

Y producirá.

narrative.json

Posteriormente ambos podrán integrarse para construir.

dashboard_snapshot.json

---

# 24. Auditoría

Todo contrato deberá permitir responder.

- quién lo generó;
- cuándo fue generado;
- con qué metodología;
- con qué evidencia;
- mediante qué ejecución.

---

# 25. Criterios de Aceptación

Los contratos JSON serán considerados correctamente implementados cuando.

- puedan validarse automáticamente;
- puedan versionarse;
- puedan reconstruirse;
- sean independientes del código;
- permitan desacoplar completamente los módulos del sistema.

---

# 26. Vigencia

Este documento constituye la especificación oficial de los contratos JSON de MIPA.

Toda integración futura deberá ajustarse a las reglas aquí establecidas.

---

# Control del Documento

| Campo | Valor |
|--------|-------|
| Documento | 009_JSON_CONTRACTS.md |
| Estado | Aprobado |
| Versión | 1.0.0 |
| Tipo | Normativo |
| Depende de | 000_PROJECT_CHARTER.md, 001_FOUNDATION.md, 002_ARCHITECTURE.md, 003_DATA_MODEL.md, 004_ANALYTICAL_MODEL.md, 005_PIPELINE.md, 006_EVIDENCE_MODEL.md, 007_METRIC_CATALOG.md, 008_NARRATIVE_MODEL.md |
| Referenciado por | 010_PULSO_IQ.md, 011_POPULARIDAD_DIGITAL.md, 012_RIESGO_DIGITAL.md |
| Última actualización | Baseline MIPA 1.0 |