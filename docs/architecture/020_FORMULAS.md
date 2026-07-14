# 020 · Fórmulas

## Propósito

Este documento define el marco metodológico para la construcción, documentación y versionado de todas las fórmulas utilizadas por MIPA.

Su objetivo es garantizar que cada variable, métrica, indicador e índice sea calculado de forma determinista, reproducible, auditable y completamente transparente.

Las fórmulas constituyen la implementación matemática oficial de la metodología analítica de MIPA.

---

# Objetivo

Este documento busca responder una pregunta específica:

> ¿Cómo deben definirse, documentarse y mantenerse las fórmulas utilizadas por el Pipeline?

El objetivo no es describir una implementación técnica específica, sino establecer las reglas obligatorias que deberán cumplir todas las operaciones matemáticas del sistema.

---

# Alcance

Las reglas definidas en este documento aplican a:

- variables derivadas;
- métricas;
- indicadores;
- índices compuestos;
- procesos de normalización;
- procesos de ponderación;
- procesos de agregación;
- cálculos estadísticos;
- transformaciones matemáticas.

Toda operación numérica utilizada por el Pipeline deberá cumplir este documento.

---

# Principios

Las fórmulas oficiales deberán cumplir los siguientes principios:

- determinismo;
- reproducibilidad;
- simplicidad;
- transparencia;
- trazabilidad;
- auditabilidad;
- versionado.

No se permitirán cálculos cuya lógica no pueda explicarse completamente.

---

# Fuente de datos

Toda fórmula deberá utilizar únicamente información proveniente de:

- la evidencia original;
- variables previamente calculadas;
- métricas previamente calculadas;
- indicadores previamente calculados.

No se permitirán valores externos no documentados.

---

# Cadena de cálculo

Toda operación matemática deberá respetar la siguiente jerarquía:

Evidencia

↓

Variables

↓

Métricas

↓

Indicadores

↓

Índices

No se permitirán dependencias circulares.

Cada nivel utilizará exclusivamente información proveniente de niveles anteriores.

---

# Definición obligatoria

Cada fórmula oficial deberá documentar como mínimo:

- nombre;
- identificador;
- objetivo;
- definición matemática;
- variables de entrada;
- unidad del resultado;
- rango esperado;
- interpretación;
- limitaciones;
- versión metodológica.

Una fórmula incompletamente documentada no podrá formar parte del Pipeline.

---

# Variables de entrada

Toda variable utilizada por una fórmula deberá estar previamente definida en la metodología oficial.

Cada variable deberá indicar:

- origen;
- significado;
- unidad;
- método de cálculo;
- evidencia utilizada.

No se permitirán variables implícitas.

---

# Operaciones permitidas

Las fórmulas podrán utilizar únicamente operaciones matemáticas claramente documentadas.

Entre ellas:

- suma;
- resta;
- multiplicación;
- división;
- promedios;
- medianas;
- proporciones;
- porcentajes;
- normalizaciones;
- ponderaciones;
- funciones estadísticas.

Toda operación deberá poder reproducirse exactamente.

---

# Normalización

Cuando una fórmula requiera normalización, deberá documentar explícitamente:

- método utilizado;
- rango objetivo;
- justificación metodológica;
- tratamiento de valores extremos.

El método de normalización formará parte de la definición oficial de la fórmula.

---

# Ponderaciones

Los índices compuestos podrán utilizar ponderaciones.

Toda ponderación deberá documentar:

- valor utilizado;
- componente afectado;
- justificación metodológica;
- versión correspondiente.

No se permitirán ponderaciones arbitrarias.

---

# Manejo de valores faltantes

Cada fórmula deberá definir explícitamente cómo tratar:

- datos ausentes;
- valores nulos;
- divisiones entre cero;
- registros excluidos;
- cobertura insuficiente.

El tratamiento deberá ser consistente en todas las ejecuciones.

---

# Precisión

Cada fórmula deberá definir el nivel de precisión utilizado durante los cálculos.

La metodología deberá establecer:

- número de decimales;
- reglas de redondeo;
- formato de almacenamiento;
- formato de presentación.

El Dashboard únicamente mostrará los resultados producidos por el Pipeline.

---

# Versionado

Toda modificación de una fórmula deberá registrar:

- identificador;
- versión;
- fecha de implementación;
- cambios realizados;
- justificación metodológica;
- impacto esperado;
- compatibilidad con versiones anteriores.

Los resultados calculados bajo distintas versiones deberán permanecer diferenciados.

---

# Validación

Toda fórmula deberá superar el proceso oficial de validación antes de incorporarse al Pipeline.

Como mínimo deberá verificarse:

- consistencia matemática;
- reproducibilidad;
- estabilidad;
- compatibilidad metodológica;
- trazabilidad.

Las fórmulas no validadas no podrán utilizarse en producción.

---

# Auditoría

Toda fórmula deberá permitir responder preguntas como:

- ¿Qué calcula?
- ¿Qué variables utiliza?
- ¿Cuál es su definición matemática?
- ¿Qué versión se utilizó?
- ¿Qué evidencia alimentó el cálculo?
- ¿Qué resultado produjo?

La documentación deberá ser suficiente para reproducir completamente cualquier cálculo.

---

# Implementación

Las fórmulas serán implementadas exclusivamente dentro del Pipeline.

No podrán implementarse en:

- Dashboard;
- analytics.json;
- narrative.json;
- dashboard_snapshot.json.

Estos componentes únicamente consumirán resultados previamente calculados.

---

# Reproducibilidad

Ejecutar nuevamente una fórmula utilizando:

- la misma evidencia;
- las mismas variables;
- la misma versión metodológica;
- la misma versión del Pipeline;

deberá producir exactamente el mismo resultado.

No se permitirán operaciones aleatorias ni dependientes del entorno de ejecución.

---

# Limitaciones

Las fórmulas describen relaciones matemáticas sobre la evidencia disponible.

No corrigen:

- sesgos de captura;
- ausencia de datos;
- limitaciones propias de las plataformas;
- representatividad del universo digital.

La interpretación de los resultados deberá considerar siempre las limitaciones metodológicas del sistema.

---

# Catálogo oficial de fórmulas

Cada fórmula oficial será documentada individualmente dentro del catálogo metodológico correspondiente.

Como mínimo deberá incluir:

- identificador único;
- nombre;
- descripción;
- definición matemática;
- variables de entrada;
- unidad;
- interpretación;
- limitaciones;
- ejemplos de cálculo;
- versión.

Este catálogo constituye la referencia oficial para la implementación del Pipeline.

---

# Relación con otros documentos

Este documento se complementa con:

- 004_ANALYTICAL_MODEL.md
- 007_METRIC_CATALOG.md
- 010_PULSO_IQ.md
- 011_POPULARIDAD_DIGITAL.md
- 012_RIESGO_DIGITAL.md
- 017_TRACEABILITY_MODEL.md
- 019_ANALYTICS_DB_SCHEMA.md

En conjunto, estos documentos establecen el marco metodológico que garantiza que toda operación matemática realizada por MIPA sea completamente documentada, verificable, reproducible y auditable.