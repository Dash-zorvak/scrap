"""Override de tipografia: jerarquia visual legible sin tocar estilos.py.

estilos.py define una escala de fuentes (--fs-*) usada en todo el dashboard,
pero los tamanos eran demasiado pequenos y obligaban a hacer zoom. Aqui se
REDEFINE esa escala con tamanos mas grandes y una jerarquia clara
(titulo > subtitulo > metrica > narrativa > referencia). Se inyecta DESPUES de
estilos.CSS en app.py, asi que prevalece sin necesidad de reescribir el archivo
grande de estilos.
"""

CSS_OVERRIDE = """
<style>
:root {
  --fs-overline: 11px;
  --fs-label: 12px;
  --fs-meta: 12.5px;
  --fs-body: 15px;
  --fs-h-sm: 16px;
  --fs-h-md: 21px;
  --fs-h-lg: 28px;
  --fs-kpi: 40px;
  --fs-hero: 52px;
}

/* Texto narrativo: el cuerpo que lee el alcalde. */
.stMarkdown p, .stMarkdown li {
  font-size: var(--fs-body) !important;
  line-height: 1.65 !important;
}
.stMarkdown td, .stMarkdown th { font-size: var(--fs-body) !important; }

/* Subir el piso de los textos diminutos (overlines, metadatos, etiquetas). */
.panel-meta, .sys-section-label, .doc-meta, .topbar-meta,
.exec-caption, .wys-text {
  font-size: var(--fs-meta) !important;
  letter-spacing: 0.4px !important;
}

/* Titulos de seccion y de pagina. */
h1, h2 { font-size: var(--fs-h-lg) !important; }
.page-sub, h3 { font-size: var(--fs-h-md) !important; }

/* Metricas / KPIs destacados. */
.kpi-value, .metric-value, [data-testid=\"stMetricValue\"] {
  font-size: var(--fs-kpi) !important;
}
[data-testid=\"stMetricLabel\"] { font-size: var(--fs-label) !important; }
</style>
"""
