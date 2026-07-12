"""Override de selectores específicos que no cubre estilos.py.

La escala --fs- vive únicamente en estilos.py; aquí ya no se redefine.
Se inyecta DESPUÉS de estilos.CSS en app.py para ajustar métricas
nativas de Streamlit y tipografía de cuerpo con !important.
"""

CSS_OVERRIDE = """
<style>

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
