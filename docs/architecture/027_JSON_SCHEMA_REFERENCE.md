# MIPA — Motor de Inteligencia Política Auditada
## JSON_SCHEMA_REFERENCE
**Documento:** 027_JSON_SCHEMA_REFERENCE.md  
**Estado:** APROBADO (Baseline)  
**Versión metodológica:** MIPA 1.0.0  
**Clasificación:** Especificación Técnica (Obligatorio)

---

# 1. Propósito

Este documento define la especificación oficial de todos los esquemas JSON utilizados por MIPA.

Los esquemas JSON representan el mecanismo de intercambio entre módulos del sistema.

Ningún componente podrá consumir ni producir estructuras distintas a las aquí documentadas.

---

# 2. Objetivos

Los esquemas JSON tienen como finalidad.

- garantizar interoperabilidad;
- eliminar dependencias entre módulos;
- facilitar validación automática;
- permitir versionado;
- asegurar compatibilidad.

---

# 3. Principios

## JSON-001

Todo documento JSON deberá cumplir un esquema oficial.

---

## JSON-002

Todo esquema deberá ser versionado.

---

## JSON-003

Todo esquema deberá poder validarse automáticamente.

---

## JSON-004

Los cambios incompatibles requerirán una nueva versión.

---

## JSON-005

Todo JSON deberá ser completamente reproducible.

---

# 4. Documentos JSON Oficiales

MIPA reconoce los siguientes documentos.

| Documento | Responsable |
|------------|-------------|
| ingestion.json | Panel de Carga |
| validation.json | Validación Humana |
| analytics.json | Pipeline Analítico |
| narrative.json | Motor Narrativo |
| dashboard_snapshot.json | Dashboard |
| audit.json | Auditoría |

---

# 5. Encabezado Obligatorio

Todo documento JSON deberá contener.

```json
{
  "schema_version": "",
  "methodology_version": "",
  "pipeline_version": "",
  "generated_at": "",
  "run_id": "",
  "data": {}
}
```

Estos campos nunca podrán omitirse.

---

# 6. ingestion.json

Representa la salida del Panel de Carga.

Debe contener únicamente.

- publicaciones;
- comentarios;
- métricas observadas;
- capturas;
- enlaces;
- metadatos de extracción.

No contendrá indicadores.

---

# 7. validation.json

Representa la salida del proceso de validación humana.

Debe incluir.

- registros aprobados;
- registros rechazados;
- observaciones;
- correcciones;
- responsable;
- fecha.

---

# 8. analytics.json

Representa la salida oficial del Pipeline.

Debe contener exclusivamente.

- variables;
- métricas;
- indicadores;
- índices;
- referencias;
- limitaciones.

No contendrá narrativa.

---

# 9. narrative.json

Representa la salida del Motor Narrativo.

Debe contener.

- narrativas;
- conclusiones;
- referencias;
- limitaciones.

Nunca contendrá cálculos.

---

# 10. dashboard_snapshot.json

Representa exactamente la información consumida por el Dashboard.

Debe incluir.

- KPIs;
- indicadores;
- índices;
- narrativas;
- referencias;
- visualizaciones;
- metadatos.

El Dashboard no realizará ningún cálculo adicional.

---

# 11. audit.json

Representa el resultado completo de una ejecución.

Debe contener.

- duración;
- estado;
- errores;
- advertencias;
- métricas;
- versiones;
- registros procesados.

---

# 12. Convenciones

Todos los documentos utilizarán.

- UTF-8;
- snake_case;
- fechas ISO-8601;
- valores numéricos explícitos;
- nombres en inglés.

---

# 13. Tipos Permitidos

Los tipos oficiales son.

| Tipo | Uso |
|------|-----|
| string | Identificadores |
| integer | Conteos |
| number | Métricas |
| boolean | Estados |
| object | Estructuras |
| array | Colecciones |
| null | Valores ausentes documentados |

---

# 14. Fechas

Todas las fechas deberán utilizar.

```
YYYY-MM-DD
```

Los timestamps deberán utilizar.

```
YYYY-MM-DDTHH:mm:ssZ
```

---

# 15. Valores Numéricos

Las reglas oficiales son.

- no utilizar NaN;
- no utilizar Infinity;
- no utilizar valores negativos cuando no correspondan;
- utilizar punto decimal.

---

# 16. Identificadores

Todo objeto persistente deberá poseer un identificador único.

Ejemplos.

- run_id
- indicator_id
- metric_id
- reference_id

---

# 17. Arreglos

Los arreglos deberán mantener un orden determinista.

Nunca dependerán del orden interno de una base de datos.

---

# 18. Objetos

Todo objeto deberá poseer una estructura fija.

No se permitirán claves dinámicas no documentadas.

---

# 19. Validación

Todo JSON será validado antes de publicarse.

Como mínimo deberán verificarse.

- estructura;
- tipos;
- obligatoriedad;
- restricciones;
- coherencia.

---

# 20. Compatibilidad

Los cambios se clasifican como.

Compatible.

Agregar campos opcionales.

Condicional.

Modificar reglas documentadas.

Incompatible.

Eliminar campos obligatorios.

Cambiar significado.

Modificar tipos.

---

# 21. Versionado

Todo documento registrará.

- schema_version;
- methodology_version;
- pipeline_version.

---

# 22. Integridad

Todo JSON deberá ser consistente con.

- analytics.db;
- evidencia;
- ejecución del Pipeline.

---

# 23. Atomicidad

Los documentos deberán publicarse mediante escritura atómica.

Nunca podrán existir archivos parcialmente escritos.

---

# 24. Auditoría

Todo documento deberá responder.

- quién lo generó;
- cuándo;
- mediante qué Pipeline;
- con qué metodología;
- utilizando qué ejecución.

---

# 25. Restricciones

Queda prohibido.

- modificar manualmente JSON publicados;
- eliminar metadatos;
- eliminar versiones;
- eliminar identificadores;
- utilizar estructuras no documentadas.

---

# 26. Criterios de Aceptación

Los esquemas JSON serán considerados correctamente implementados cuando.

- todos los documentos puedan validarse automáticamente;
- exista compatibilidad entre módulos;
- los cambios sean versionados;
- la estructura sea determinista;
- la trazabilidad sea completa.

---

# 27. Vigencia

Este documento constituye la especificación oficial de todos los esquemas JSON utilizados por MIPA.

Toda modificación requerirá actualización de la versión metodológica.

---

# Control del Documento

| Campo | Valor |
|--------|-------|
| Documento | 027_JSON_SCHEMA_REFERENCE.md |
| Estado | Aprobado |
| Versión | 1.0.0 |
| Tipo | Especificación Técnica |
| Depende de | 000_PROJECT_CHARTER.md – 026_PIPELINE_VARIABLES.md |
| Referenciado por | 028_FORMULA_REFERENCE.md, 029_IMPLEMENTATION_GUIDE.md |
| Última actualización | Baseline MIPA 1.0 |