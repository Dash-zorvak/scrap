# MIPA — Motor de Inteligencia Política Auditada
## RIESGO_DIGITAL
**Documento:** 012_RIESGO_DIGITAL.md  
**Estado:** APROBADO (Baseline)  
**Versión metodológica:** MIPA 1.0.0  
**Clasificación:** Metodología Oficial (Obligatorio)

---

# 1. Propósito

Este documento define la metodología oficial del indicador **Riesgo Digital** dentro de MIPA.

Riesgo Digital identifica señales de fricción, deterioro conversacional, concentración negativa y patrones que requieren atención dentro del ecosistema digital analizado.

Su objetivo es detectar escenarios potencialmente relevantes antes de que se conviertan en crisis comunicacionales.

---

# 2. Definición Oficial

Riesgo Digital es un indicador compuesto que mide la presencia, intensidad y evolución de señales negativas observables dentro de la conversación digital.

No predice crisis.

No predice comportamiento electoral.

No determina causalidad política.

Representa únicamente señales digitales detectadas mediante evidencia verificable.

---

# 3. Objetivo

Responder una pregunta concreta.

> **¿Existen señales digitales que requieren atención debido a su volumen, intensidad o velocidad de crecimiento?**

---

# 4. Qué mide

Riesgo Digital mide.

- aumento de conversación crítica;
- concentración de emociones negativas;
- velocidad de propagación;
- persistencia de temas sensibles;
- aparición de puntos de fricción;
- comportamiento anómalo respecto al histórico.

---

# 5. Qué NO mide

Riesgo Digital no mide.

- gravedad política real;
- impacto electoral;
- intención de voto;
- opinión ciudadana completa;
- probabilidad de crisis futura.

---

# 6. Dimensiones Oficiales

El indicador está compuesto por cinco dimensiones.

---

# RD-01 Intensidad Negativa

Mide la proporción e intensidad de señales negativas dentro de la conversación.

Variables consideradas.

- emociones negativas;
- postura crítica;
- volumen de comentarios críticos.

---

# RD-02 Velocidad

Mide la rapidez con la que una conversación aumenta.

Variables consideradas.

- crecimiento temporal;
- incremento porcentual;
- concentración por período.

---

# RD-03 Persistencia

Mide si un fenómeno desaparece rápidamente o permanece activo.

Variables consideradas.

- repetición del tema;
- duración;
- frecuencia.

---

# RD-04 Concentración

Mide si un riesgo está concentrado en un tema específico.

Ejemplo.

```
50% de comentarios críticos
relacionados con un único tema
```

Representa mayor concentración que múltiples temas dispersos.

---

# RD-05 Alcance

Mide la capacidad potencial de expansión digital.

Variables consideradas.

- interacciones;
- publicaciones relacionadas;
- distribución entre plataformas.

---

# 7. Fórmula General

La estructura general es.

```
Riesgo Digital

=

Σ (Factor Riesgo Normalizado × Peso)
```

Los pesos deberán estar documentados.

---

# 8. Escala

| Valor | Interpretación |
|---|---|
| 0–20 | Bajo |
| 21–40 | Moderado |
| 41–60 | Elevado |
| 61–80 | Alto |
| 81–100 | Crítico |

Las etiquetas describen únicamente señales digitales observadas.

---

# 9. Evidencia

Todo nivel de riesgo deberá incluir.

- publicaciones relacionadas;
- comentarios asociados;
- plataforma;
- período;
- evolución temporal;
- referencias originales.

---

# 10. Explicabilidad

Nunca será suficiente mostrar.

```
Riesgo: 78
```

Debe explicar.

Ejemplo.

```
Riesgo Digital: 78

Motivos:

1. Incremento de 42% en comentarios críticos.
2. 63% de menciones negativas concentradas en seguridad.
3. El volumen aumentó durante 72 horas consecutivas.

Evidencia:

- publicaciones relacionadas;
- comentarios;
- enlaces originales.
```

---

# 11. Reglas de Interpretación

Un riesgo alto no significa automáticamente.

- error institucional;
- rechazo ciudadano;
- crisis política.

Significa.

> Existe una concentración significativa de señales digitales que requiere revisión.

---

# 12. Evidencia Tangible

Cada alerta deberá estar conectada con elementos verificables.

Ejemplos.

Correcto:

> 312 comentarios críticos relacionados con reparación vial en 5 publicaciones específicas.

Incorrecto:

> La ciudadanía está molesta.

---

# 13. Referencias

Toda alerta deberá incluir.

- URLs originales;
- publicaciones fuente;
- fechas;
- plataforma;
- identificadores internos.

El usuario debe poder verificar la evidencia.

---

# 14. Relación con Pulso IQ

Riesgo Digital participa como componente inverso dentro del Pulso IQ.

Cuando aumenta el riesgo.

El Pulso IQ puede disminuir.

La relación deberá estar documentada matemáticamente.

---

# 15. Relación con Popularidad Digital

Riesgo Digital complementa Popularidad Digital.

Ejemplo.

Una figura puede tener.

- alta popularidad digital;
- alto riesgo digital.

Esto significa.

Existe mucha conversación, pero con señales de fricción.

---

# 16. Limitaciones

Riesgo Digital no sustituye.

- análisis político;
- investigación social;
- encuestas;
- evaluación humana.

Es una herramienta de detección temprana.

---

# 17. Transparencia

El Dashboard deberá mostrar.

- nivel;
- factores;
- evidencia;
- período;
- limitaciones.

Nunca únicamente la etiqueta.

---

# 18. Versionado

Cada cálculo deberá registrar.

- versión metodológica;
- versión del algoritmo;
- fecha;
- ejecución del Pipeline.

---

# 19. Validación

Antes de publicarse deberá verificarse.

- consistencia matemática;
- evidencia disponible;
- período analizado;
- referencias.

---

# 20. Restricciones

Queda prohibido.

- afirmar existencia de crisis sin evidencia;
- transformar riesgo digital en predicción;
- ocultar datos utilizados;
- modificar manualmente niveles.

---

# 21. Criterios de Aceptación

Riesgo Digital será considerado correctamente implementado cuando.

- pueda reconstruirse desde evidencia;
- explique sus componentes;
- muestre referencias;
- documente limitaciones;
- diferencie señal digital de realidad política.

---

# 22. Vigencia

Este documento constituye la especificación oficial del indicador Riesgo Digital de MIPA.

Toda modificación requerirá una nueva versión metodológica.

---

# Control del Documento

| Campo | Valor |
|---|---|
| Documento | 012_RIESGO_DIGITAL.md |
| Estado | Aprobado |
| Versión | 1.0.0 |
| Tipo | Metodología Oficial |
| Depende de | 000_PROJECT_CHARTER.md, 001_FOUNDATION.md, 002_ARCHITECTURE.md, 003_DATA_MODEL.md, 004_ANALYTICAL_MODEL.md, 005_PIPELINE.md, 006_EVIDENCE_MODEL.md, 007_METRIC_CATALOG.md, 008_NARRATIVE_MODEL.md, 009_JSON_CONTRACTS.md, 010_PULSO_IQ.md, 011_POPULARIDAD_DIGITAL.md |
| Referenciado por | 020_FORMULAS.md, Dashboard Ejecutivo |
| Última actualización | Baseline MIPA 1.0 |