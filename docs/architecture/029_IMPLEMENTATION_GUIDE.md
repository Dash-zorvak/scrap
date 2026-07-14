# MIPA — Motor de Inteligencia Política Auditada
## IMPLEMENTATION_GUIDE
**Documento:** 029_IMPLEMENTATION_GUIDE.md  
**Estado:** APROBADO (Baseline)  
**Versión metodológica:** MIPA 1.0.0  
**Clasificación:** Guía Oficial de Implementación (Obligatorio)

---

# 1. Propósito

Este documento define las reglas oficiales para implementar MIPA dentro del repositorio.

Su objetivo es garantizar que toda implementación respete la arquitectura, la metodología y los principios definidos por la documentación oficial.

Este documento constituye el puente entre la documentación metodológica y el código fuente.

---

# 2. Alcance

Aplica a cualquier modificación realizada sobre.

- panel_carga.py
- analytics/
- dashboard/
- src/
- scripts/
- data/
- tests/

Toda nueva funcionalidad deberá cumplir este documento.

---

# 3. Principios

## IMP-001

La metodología tiene prioridad sobre la implementación.

---

## IMP-002

El código deberá adaptarse a la documentación.

Nunca al contrario.

---

## IMP-003

Toda implementación deberá ser determinista.

---

## IMP-004

Toda implementación deberá ser auditable.

---

## IMP-005

Toda implementación deberá ser reproducible.

---

# 4. Arquitectura Oficial

La arquitectura queda definida como.

```
Panel de Carga

↓

Validación Humana

↓

facebook.db
tiktok.db
externos.db

↓

Pipeline Analítico

↓

analytics.db

↓

dashboard_snapshot.json

↓

Dashboard
```

No se permitirá ninguna variante fuera de este flujo.

---

# 5. Responsabilidades

## Panel de Carga

Responsable de.

- extracción;
- validación humana;
- persistencia de evidencia.

Nunca calculará indicadores.

---

## Bases Fuente

Responsables de conservar.

- publicaciones;
- comentarios;
- métricas originales.

Nunca almacenarán indicadores derivados.

---

## Pipeline

Responsable de.

- cálculos;
- normalizaciones;
- indicadores;
- índices;
- referencias;
- auditoría.

Todo procesamiento matemático ocurre aquí.

---

## analytics.db

Responsable de persistir.

- variables;
- métricas;
- indicadores;
- índices;
- históricos;
- trazabilidad.

---

## Dashboard

Responsable únicamente de visualizar.

Nunca calculará.

Nunca inferirá.

Nunca corregirá datos.

---

# 6. Flujo de Datos

Toda información deberá seguir el siguiente recorrido.

Captura

↓

Validación

↓

Persistencia

↓

Pipeline

↓

analytics.db

↓

dashboard_snapshot.json

↓

Dashboard

---

# 7. Evidencia

La evidencia original permanecerá exclusivamente en.

- facebook.db
- tiktok.db
- externos.db

Nunca será duplicada dentro de analytics.db.

---

# 8. Pipeline Incremental

El Pipeline deberá ejecutarse de forma incremental.

Cada ejecución procesará únicamente registros nuevos o modificados.

No deberá recalcular innecesariamente períodos históricos.

---

# 9. Reprocesamiento

Cuando un registro histórico cambie.

El Pipeline recalculará únicamente los indicadores afectados.

Nunca reconstruirá completamente toda la base.

---

# 10. Versionado

Toda ejecución registrará.

- pipeline_version;
- methodology_version;
- run_id;
- execution_date.

---

# 11. Auditoría

Toda ejecución deberá generar.

- audit.json;
- registros de ejecución;
- tiempos;
- advertencias;
- errores.

---

# 12. Dashboard

El Dashboard consumirá exclusivamente.

dashboard_snapshot.json

Nunca accederá directamente a analytics.db.

Nunca accederá a SQLite.

---

# 13. Narrativas

El Motor Narrativo consumirá exclusivamente.

analytics.json

Nunca consultará bases SQLite.

Nunca realizará cálculos.

---

# 14. Validaciones

Antes de publicar resultados deberán ejecutarse.

- validación estructural;
- validación matemática;
- validación metodológica;
- validación de referencias;
- validación de cobertura.

---

# 15. Referencias

Todo indicador publicado deberá conservar referencias verificables hacia.

- publicaciones;
- comentarios;
- plataforma;
- URL original;
- período analizado.

---

# 16. Persistencia

Toda escritura deberá realizarse mediante operaciones atómicas.

Nunca podrán publicarse archivos parcialmente escritos.

---

# 17. Históricos

El sistema conservará todas las ejecuciones relevantes.

Nunca eliminará información histórica sin una política explícita de retención.

---

# 18. Pruebas

Toda implementación deberá incorporar pruebas para.

- cálculos;
- fórmulas;
- normalizaciones;
- JSON;
- Pipeline;
- integridad.

Ningún cambio metodológico podrá aprobarse sin pruebas.

---

# 19. Compatibilidad

Toda implementación deberá mantener compatibilidad con la versión metodológica vigente.

Los cambios incompatibles requerirán una nueva versión.

---

# 20. Restricciones

Queda prohibido.

- calcular indicadores dentro del Dashboard;
- generar narrativa antes del Pipeline;
- modificar evidencia original;
- alterar indicadores manualmente;
- utilizar variables no documentadas.

---

# 21. Evolución

Toda nueva funcionalidad deberá.

- documentarse;
- versionarse;
- auditarse;
- probarse;
- aprobarse antes de implementarse.

---

# 22. Relación con la Documentación

Este documento depende de toda la documentación metodológica previa.

La implementación nunca podrá contradecir.

- arquitectura;
- modelos analíticos;
- fórmulas;
- contratos JSON;
- diccionario de datos.

---

# 23. Criterios de Aceptación

La implementación será considerada correcta cuando.

- respete la arquitectura oficial;
- todos los cálculos ocurran en el Pipeline;
- el Dashboard sea completamente pasivo;
- exista trazabilidad completa;
- toda salida pueda reconstruirse desde la evidencia.

---

# 24. Vigencia

Este documento constituye la guía oficial para implementar MIPA dentro del repositorio.

Toda modificación arquitectónica deberá reflejarse primero en la documentación y posteriormente en el código.

---

# Control del Documento

| Campo | Valor |
|--------|-------|
| Documento | 029_IMPLEMENTATION_GUIDE.md |
| Estado | Aprobado |
| Versión | 1.0.0 |
| Tipo | Guía Oficial de Implementación |
| Depende de | 000_PROJECT_CHARTER.md – 028_FORMULA_REFERENCE.md |
| Referenciado por | Appendix/README.md, Roadmap de Implementación |
| Última actualización | Baseline MIPA 1.0 |