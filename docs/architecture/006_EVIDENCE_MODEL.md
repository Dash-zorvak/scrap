# MIPA — Motor de Inteligencia Política Auditada
## EVIDENCE_MODEL
**Documento:** 006_EVIDENCE_MODEL.md  
**Estado:** APROBADO (Baseline)  
**Versión metodológica:** MIPA 1.0.0  
**Clasificación:** Normativo (Obligatorio)

---

# 1. Propósito

Este documento define el Modelo Oficial de Evidencia de MIPA.

La evidencia constituye el activo más importante del sistema.

Todos los indicadores, métricas, índices y narrativas existen únicamente porque existe evidencia que los respalda.

Sin evidencia verificable no podrá existir información oficial.

---

# 2. Objetivo

Garantizar que cualquier resultado generado por MIPA pueda reconstruirse completamente desde la evidencia original.

La evidencia constituye la única fuente oficial de verdad del sistema.

---

# 3. Definición Oficial

Se considera evidencia cualquier información pública capturada, validada y preservada cuya autenticidad pueda demostrarse.

La evidencia no es una interpretación.

La evidencia no es una conclusión.

La evidencia representa únicamente un hecho observable.

---

# 4. Principios del Modelo de Evidencia

## EVID-001

Toda evidencia deberá ser verificable.

---

## EVID-002

Toda evidencia deberá ser trazable.

---

## EVID-003

Toda evidencia deberá conservarse íntegra.

---

## EVID-004

Toda evidencia deberá permanecer disponible para auditoría.

---

## EVID-005

Toda evidencia deberá mantener relación explícita con los indicadores que ayudó a construir.

---

# 5. Tipos Oficiales de Evidencia

MIPA reconoce únicamente los siguientes tipos.

## Evidencia Visual

- captura de pantalla
- imagen
- fotografía
- PDF

---

## Evidencia Textual

- publicación
- comentario
- descripción
- titular

---

## Evidencia Cuantitativa

- reacciones
- comentarios
- compartidos
- visualizaciones
- seguidores

---

## Evidencia Contextual

- plataforma
- fecha
- autor
- fuente
- enlace

---

# 6. Ciclo de Vida

Toda evidencia recorrerá el siguiente flujo.

```
Capturada

↓

Extraída

↓

Validada

↓

Persistida

↓

Referenciada

↓

Utilizada

↓

Auditada

↓

Conservada
```

Nunca podrá omitirse una etapa.

---

# 7. Identidad

Toda evidencia deberá poseer un identificador permanente.

Este identificador nunca cambiará.

Nunca dependerá del almacenamiento físico.

Nunca dependerá del Dashboard.

---

# 8. Metadatos Obligatorios

Toda evidencia deberá registrar como mínimo.

- identificador
- plataforma
- fuente
- fecha de captura
- fecha del contenido
- URL original
- tipo de evidencia
- estado
- hash de integridad
- versión metodológica

---

# 9. Integridad

La evidencia nunca podrá modificarse después de haber sido validada.

Si ocurre una corrección.

Se generará una nueva versión.

La versión anterior permanecerá disponible para auditoría.

---

# 10. Hash de Integridad

Toda evidencia deberá poseer un hash criptográfico.

Su finalidad es detectar modificaciones posteriores.

El algoritmo utilizado deberá documentarse.

---

# 11. Referencias

Todo indicador oficial deberá mantener referencias explícitas hacia la evidencia utilizada.

Como mínimo deberá conservar.

- identificador de publicación
- identificador de comentario
- URL
- plataforma

---

# 12. Evidencia de Cálculo

Además de la evidencia original.

Todo cálculo deberá generar evidencia analítica.

Por ejemplo.

- variables utilizadas
- métricas intermedias
- filtros aplicados
- universo analizado
- registros descartados

---

# 13. Evidencia Narrativa

Toda afirmación realizada por el Motor Narrativo deberá poder asociarse a uno o más elementos de evidencia.

No se permitirán afirmaciones sin respaldo.

---

# 14. Evidencia de Auditoría

Toda ejecución del Pipeline deberá generar evidencia de proceso.

Como mínimo.

- fecha
- duración
- versión
- usuario o proceso
- resultados
- errores
- advertencias

---

# 15. Cobertura

Cada indicador deberá informar.

- cantidad de publicaciones analizadas
- cantidad de comentarios analizados
- plataformas incluidas
- período cubierto
- porcentaje de cobertura

La cobertura forma parte del indicador.

---

# 16. Evidencia Excluida

Cuando registros sean descartados.

El sistema deberá registrar.

- motivo
- cantidad
- identificadores
- etapa donde fueron descartados

Nunca podrán desaparecer silenciosamente.

---

# 17. Evidencia Histórica

La evidencia histórica nunca será reemplazada.

El sistema deberá permitir reconstruir cualquier período previamente publicado.

---

# 18. Evidencia por Indicador

Cada indicador deberá conservar una relación explícita con toda la evidencia utilizada para construirlo.

Esta relación deberá permitir.

- auditoría;
- reconstrucción;
- navegación desde el Dashboard;
- exportación.

---

# 19. Evidencia por Narrativa

Cada narrativa oficial deberá incluir referencias verificables.

Como mínimo.

- publicaciones utilizadas
- comentarios utilizados
- evidencia cuantitativa
- enlaces originales

No se aceptarán referencias genéricas.

---

# 20. Evidencia en el Dashboard

El Dashboard deberá permitir consultar la evidencia asociada a cada indicador.

Como mínimo deberá mostrar.

- publicaciones relevantes
- enlaces originales
- plataforma
- fecha
- métricas observadas

El usuario deberá poder verificar el origen de cualquier cifra presentada.

---

# 21. Conservación

La evidencia constituye patrimonio metodológico.

Nunca será eliminada por procesos analíticos.

La eliminación física únicamente podrá producirse mediante procesos administrativos documentados.

---

# 22. Independencia

El modelo de evidencia será independiente de.

- SQLite
- PostgreSQL
- almacenamiento local
- almacenamiento en nube
- formato de archivo

La implementación podrá cambiar.

La evidencia permanecerá idéntica.

---

# 23. Restricciones

Queda prohibido.

- editar evidencia para mejorar indicadores;
- modificar capturas originales;
- alterar publicaciones;
- alterar comentarios;
- eliminar evidencia sin trazabilidad;
- construir indicadores sin evidencia asociada.

---

# 24. Criterios de Aceptación

El Modelo de Evidencia será considerado correctamente implementado cuando.

- cualquier indicador pueda navegar hasta la evidencia utilizada;
- toda evidencia posea hash de integridad;
- toda evidencia posea URL verificable cuando exista;
- todo cálculo conserve referencias;
- toda narrativa posea respaldo explícito;
- ninguna evidencia pueda perder trazabilidad.

---

# 25. Vigencia

Este documento constituye la especificación oficial del Modelo de Evidencia de MIPA.

Toda implementación futura deberá respetar las reglas aquí establecidas.

---

# Control del Documento

| Campo | Valor |
|--------|-------|
| Documento | 006_EVIDENCE_MODEL.md |
| Estado | Aprobado |
| Versión | 1.0.0 |
| Tipo | Normativo |
| Depende de | 000_PROJECT_CHARTER.md, 001_FOUNDATION.md, 002_ARCHITECTURE.md, 003_DATA_MODEL.md, 004_ANALYTICAL_MODEL.md, 005_PIPELINE.md |
| Referenciado por | 007_METRIC_CATALOG.md, 008_NARRATIVE_MODEL.md, 009_JSON_CONTRACTS.md |
| Última actualización | Baseline MIPA 1.0 |