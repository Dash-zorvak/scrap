# MIPA — Motor de Inteligencia Política Auditada
## ARCHITECTURE
**Documento:** 002_ARCHITECTURE.md  
**Estado:** APROBADO (Baseline)  
**Versión metodológica:** MIPA 1.0.0  
**Clasificación:** Normativo (Obligatorio)

---

# 1. Propósito

Este documento define la arquitectura oficial de MIPA.

La arquitectura establece la distribución de responsabilidades entre los componentes del sistema y garantiza que cada dominio posea una única función claramente definida.

Toda implementación deberá respetar esta arquitectura.

---

# 2. Objetivos Arquitectónicos

La arquitectura de MIPA persigue los siguientes objetivos.

- Separación estricta de responsabilidades.
- Reproducibilidad.
- Auditabilidad.
- Escalabilidad.
- Extensibilidad.
- Bajo acoplamiento.
- Alta cohesión.
- Independencia tecnológica.
- Evolución metodológica controlada.

---

# 3. Arquitectura General

MIPA se implementa mediante una arquitectura por capas.

```
                 ┌──────────────────────┐
                 │   Panel de Carga     │
                 └──────────┬───────────┘
                            │
                            ▼
                  Ingesta y Validación

                            │
                            ▼

                 ┌──────────────────────┐
                 │ Bases de Datos Fuente │
                 └──────────┬───────────┘

                            │
                            ▼

                  Pipeline Analítico

                            │
                            ▼

                 ┌──────────────────────┐
                 │    analytics.db       │
                 └──────────┬───────────┘

                            │
                            ▼

                  Motor Analítico

                            │
                            ▼

                 dashboard_snapshot.json

                            │
                            ▼

                    Dashboard Ejecutivo
```

---

# 4. Principio Fundamental

Toda información deberá avanzar únicamente hacia adelante.

Nunca hacia atrás.

El Dashboard jamás modificará el Pipeline.

El Pipeline jamás modificará la evidencia.

La evidencia jamás modificará la captura original.

---

# 5. Dominios Oficiales

La arquitectura oficial se divide en ocho dominios.

---

## Dominio 1 — Captura

Responsabilidad:

Obtener evidencia desde plataformas digitales.

Entradas:

- imágenes
- PDF
- enlaces

Salidas:

- archivos originales

No realiza cálculos.

---

## Dominio 2 — Extracción

Responsabilidad:

Convertir evidencia visual en información estructurada.

Puede utilizar modelos de IA.

Su salida siempre deberá pasar validación humana.

Entradas:

- imágenes
- PDF

Salidas:

- registros estructurados

No calcula indicadores.

---

## Dominio 3 — Validación Humana

Responsabilidad:

Confirmar que la información extraída representa correctamente la evidencia.

Todo dato oficial deberá atravesar este dominio.

Sin excepción.

---

## Dominio 4 — Persistencia

Responsabilidad:

Almacenar permanentemente la información.

Incluye:

- facebook.db
- tiktok.db
- externos.db

Estas bases representan la evidencia validada.

Nunca contienen indicadores derivados.

---

## Dominio 5 — Pipeline Analítico

Responsabilidad:

Transformar evidencia en datos analíticos.

Aquí ocurren exclusivamente procesos deterministas.

No existen decisiones humanas.

No existen interpretaciones.

No existen narrativas.

---

## Dominio 6 — Motor Analítico

Responsabilidad:

Construir indicadores oficiales.

Opera únicamente sobre datos previamente preparados por el Pipeline.

Nunca consulta directamente el Dashboard.

---

## Dominio 7 — Motor Narrativo

Responsabilidad:

Transformar indicadores en explicaciones ejecutivas.

Puede utilizar IA.

Nunca modifica indicadores.

Nunca modifica cálculos.

---

## Dominio 8 — Dashboard

Responsabilidad:

Visualizar resultados.

No calcula.

No interpreta.

No modifica.

---

# 6. Flujo Oficial

El flujo oficial queda definido de la siguiente manera.

```
Captura

↓

Extracción

↓

Validación Humana

↓

Persistencia

↓

Pipeline

↓

analytics.db

↓

Motor Analítico

↓

dashboard_snapshot.json

↓

Dashboard
```

Ningún componente podrá alterar este flujo.

---

# 7. Flujo Prohibido

Los siguientes flujos quedan prohibidos.

Dashboard → Bases de datos

Dashboard → Pipeline

Dashboard → Motor Analítico

Narrativa → Indicadores

LLM → Indicadores

LLM → Dashboard

Dashboard → Evidencia

---

# 8. Componentes del Repositorio

La arquitectura actual del repositorio deberá evolucionar hacia la siguiente distribución.

```
dashboard/

    app.py

    panel_carga.py

analytics/

    pipeline/

    calculations/

    validation/

    evidence/

    narrative/

storage/

    facebook.db

    tiktok.db

    externos.db

    analytics.db

data/

    dashboard_snapshot.json

docs/

tests/
```

---

# 9. Bases de Datos

## Bases de evidencia

Representan información validada.

No contienen cálculos.

- facebook.db

- tiktok.db

- externos.db

---

## Base analítica

Representa únicamente resultados derivados.

analytics.db

Nunca almacena evidencia original.

---

# 10. analytics.db

analytics.db constituye la única base autorizada para almacenar resultados derivados.

Contendrá exclusivamente:

- indicadores
- agregaciones
- métricas
- series temporales
- auditorías
- versiones
- referencias
- hashes
- estados

Nunca contendrá comentarios originales.

Nunca contendrá publicaciones completas.

Nunca sustituirá las bases fuente.

---

# 11. dashboard_snapshot.json

El Dashboard leerá únicamente un archivo oficial.

```
dashboard_snapshot.json
```

Este archivo representa un snapshot consistente del estado del sistema.

Nunca será editado manualmente.

Siempre será generado automáticamente.

---

# 12. Pipeline

El Pipeline constituye el núcleo del sistema.

Sus responsabilidades son:

- limpiar
- validar
- normalizar
- calcular
- agregar
- versionar
- registrar auditoría

No genera narrativas.

---

# 13. Motor Analítico

El Motor Analítico opera exclusivamente sobre analytics.db.

Su salida será:

- indicadores oficiales;
- métricas;
- índices;
- resúmenes cuantitativos.

Nunca generará texto.

---

# 14. Motor Narrativo

Recibe únicamente:

- indicadores;
- evidencia asociada;
- reglas narrativas.

Produce:

- explicaciones;
- memorándums;
- resúmenes;
- conclusiones.

Nunca modifica indicadores.

---

# 15. Dashboard

El Dashboard tiene únicamente cuatro responsabilidades.

- cargar dashboard_snapshot.json;
- validar integridad del archivo;
- renderizar;
- informar errores.

No posee lógica analítica.

---

# 16. Dependencias Permitidas

## Panel de Carga

Puede acceder a:

- LLM
- SQLite

---

## Pipeline

Puede acceder a:

- SQLite

Nunca al Dashboard.

---

## Motor Analítico

Puede acceder únicamente a:

analytics.db

---

## Dashboard

Puede acceder únicamente a:

dashboard_snapshot.json

---

# 17. Dependencias Prohibidas

El Dashboard no podrá importar módulos analíticos.

El Dashboard no podrá ejecutar consultas SQL.

El Dashboard no podrá recalcular indicadores.

El Dashboard no podrá modificar JSON.

---

# 18. Independencia Tecnológica

La arquitectura no depende de:

- Python
- SQLite
- Streamlit
- Claude
- OpenAI
- NVIDIA
- PostgreSQL

Estos componentes podrán cambiar sin modificar la arquitectura.

---

# 19. Escalabilidad

La incorporación de nuevas plataformas deberá afectar únicamente:

- Captura
- Extracción
- Persistencia

El Pipeline, el Motor Analítico y el Dashboard deberán continuar funcionando sin modificaciones estructurales.

---

# 20. Compatibilidad

Toda nueva versión deberá poder procesar evidencia histórica.

La evolución tecnológica nunca deberá impedir reconstruir indicadores previamente publicados.

---

# 21. Criterios de Aceptación

La arquitectura se considerará correctamente implementada cuando:

- el Dashboard no ejecute cálculos;
- exista una separación física entre evidencia y resultados derivados;
- analytics.db pueda reconstruirse completamente desde las bases fuente;
- dashboard_snapshot.json pueda regenerarse completamente desde analytics.db;
- eliminar analytics.db no implique pérdida de evidencia;
- eliminar dashboard_snapshot.json no implique pérdida de información analítica.

---

# 22. Vigencia

La arquitectura descrita en este documento constituye la arquitectura oficial de MIPA.

Toda implementación futura deberá respetar las responsabilidades, dependencias y restricciones aquí definidas.

---

# Control del Documento

| Campo | Valor |
|--------|-------|
| Documento | 002_ARCHITECTURE.md |
| Estado | Aprobado |
| Versión | 1.0.0 |
| Tipo | Normativo |
| Depende de | 000_PROJECT_CHARTER.md, 001_FOUNDATION.md |
| Referenciado por | 003_DATA_MODEL.md, 004_PIPELINE.md |
| Última actualización | Baseline MIPA 1.0 |