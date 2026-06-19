"""Sistema de diseño ejecutivo — Centro de monitoreo estratégico.

Estética: combinación de dashboard ejecutivo moderno + situation room +
informe de inteligencia corporativa. Paleta cyan / verde / amber / rojo
sobre lienzo profundo. Tipografía Inter (cuerpo) + IBM Plex Mono (labels).

Uso:  from dashboard.estilos import CSS ; st.markdown(CSS, unsafe_allow_html=True)
"""

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600;700&display=swap');

/* ═══════════════════════════════════════════
   PANEL EJECUTIVO · CENTRO DE MONITOREO
   Tokens · Layout · Componentes · Responsive
   ═══════════════════════════════════════════ */

:root {
  /* surfaces */
  --bg-base:      #0a0a0f;
  --bg-elev-1:    #0e1119;
  --bg-card:      #131724;
  --bg-card-hi:   #1a1f2f;
  --bg-inset:     #0c0f17;

  /* borders */
  --border:       #1c2030;
  --border-hi:    #2a3045;
  --border-soft:  #15192a;

  /* foreground */
  --fg-primary:   #e6e8ef;
  --fg-secondary: #9ba0b3;
  --fg-muted:     #5a6178;
  --fg-dim:       #3a4055;

  /* accents */
  --accent:       #22d3ee;
  --accent-2:     #06b6d4;
  --accent-soft:  rgba(34,211,238,0.08);
  --accent-strong:rgba(34,211,238,0.20);

  /* signal */
  --green:        #22c55e;
  --green-2:      #16a34a;
  --green-soft:   rgba(34,197,94,0.08);
  --green-strong: rgba(34,197,94,0.18);
  --amber:        #facc15;
  --amber-2:      #eab308;
  --amber-soft:   rgba(250,204,21,0.08);
  --amber-strong: rgba(250,204,21,0.18);
  --red:          #ef4444;
  --red-2:        #dc2626;
  --red-soft:     rgba(239,68,68,0.08);
  --red-strong:   rgba(239,68,68,0.18);
  --blue:         #3b82f6;
  --blue-soft:    rgba(59,130,246,0.08);
  --blue-strong:  rgba(59,130,246,0.20);
  --violet:       #a855f7;
  --violet-soft:  rgba(168,85,247,0.08);

  /* legacy alias — no romper código existente que use estos tokens */
  --bg-surface:   var(--bg-elev-1);
  --bg-elevated:  var(--bg-card-hi);
  --border-light: var(--border-hi);
  --accent-dim:   var(--accent-2);
  --accent-subtle:var(--accent-soft);
  --green-dim:    var(--green-strong);
  --green-bg:     var(--green-soft);
  --red-dim:      var(--red-strong);
  --red-bg:       var(--red-soft);
  --amber-dim:    var(--amber-strong);
  --amber-bg:     var(--amber-soft);
  --blue-dim:     var(--blue-strong);
  --blue-bg:      var(--blue-soft);

  /* type */
  --font-sans:    'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif;
  --font-mono:    'IBM Plex Mono', ui-monospace, 'SF Mono', Menlo, monospace;
  --font-display: var(--font-sans);

  /* type scale */
  --fs-overline:  10px;
  --fs-label:     11px;
  --fs-meta:      11px;
  --fs-body:      13px;
  --fs-h-sm:      14px;
  --fs-h-md:      18px;
  --fs-h-lg:      24px;
  --fs-kpi:       32px;
  --fs-hero:      56px;

  /* radii */
  --r-sm: 2px;
  --r-md: 4px;
  --r-lg: 6px;
}

/* ── Root ── */
html, body, .stApp {
  background: var(--bg-base);
  color: var(--fg-primary);
  font-family: var(--font-sans);
}
.stApp {
  background:
    radial-gradient(1200px 600px at 80% -200px, rgba(34,211,238,0.04), transparent 60%),
    radial-gradient(1000px 500px at -10% 110%, rgba(168,85,247,0.03), transparent 60%),
    var(--bg-base);
}
.block-container {
  padding-top: 1.4rem !important;
  padding-bottom: 2.5rem !important;
  max-width: 1440px;
}

/* ── Streamlit chrome cleanup ── */
#MainMenu { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; height: 0; }
footer { visibility: hidden; }
button[kind="header"] { color: var(--fg-muted); }

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
  background: var(--bg-elev-1);
  border-right: 1px solid var(--border);
  width: 240px !important;
}
section[data-testid="stSidebar"] .block-container {
  padding: 1rem 0.85rem !important;
}

/* ── Topbar institucional ── */
.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 2px 0 14px 0;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--border);
}
.topbar-brand {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 1.8px;
  color: var(--fg-primary);
  text-transform: uppercase;
}
.topbar-brand .sep {
  color: var(--accent);
  margin: 0 8px;
  font-weight: 700;
}
.topbar-brand .who {
  color: var(--fg-secondary);
  font-weight: 500;
}
.topbar-meta {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--fg-muted);
  letter-spacing: 0.5px;
}

/* ── Page title block (overline + título + sub) ── */
.page-head {
  margin: 4px 0 18px 0;
}
.page-overline {
  font-family: var(--font-mono);
  font-size: var(--fs-overline);
  letter-spacing: 2px;
  color: var(--accent);
  text-transform: uppercase;
  font-weight: 600;
  margin-bottom: 6px;
}
.page-h {
  font-family: var(--font-sans);
  font-size: var(--fs-h-lg);
  font-weight: 700;
  color: var(--fg-primary);
  letter-spacing: -0.02em;
  line-height: 1.2;
  margin-bottom: 6px;
}
.page-sub {
  font-family: var(--font-sans);
  font-size: var(--fs-body);
  color: var(--fg-secondary);
  line-height: 1.65;
  max-width: 760px;
}
.page-stats {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--fg-muted);
  margin-top: 10px;
  letter-spacing: 0.5px;
}
.page-stats .sep { color: var(--accent-2); margin: 0 6px; }

/* ── Section overline + headers ── */
.section-overline {
  font-family: var(--font-mono);
  font-size: var(--fs-overline);
  letter-spacing: 1.8px;
  text-transform: uppercase;
  color: var(--fg-muted);
  font-weight: 600;
  margin-bottom: 10px;
}
.section-overline .acc { color: var(--accent); }

.section-header {
  margin: 26px 0 14px 0;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border);
}
.section-title {
  font-family: var(--font-mono);
  font-size: var(--fs-label);
  letter-spacing: 2px;
  text-transform: uppercase;
  font-weight: 600;
  color: var(--fg-primary);
}
.section-subtitle {
  font-family: var(--font-sans);
  font-size: var(--fs-meta);
  color: var(--fg-muted);
  margin-top: 4px;
}

/* ── Tabs as pill-nav (◆ marker) ── */
.stTabs [data-baseweb="tab-list"] {
  gap: 4px;
  border-bottom: 1px solid var(--border);
  padding: 0;
  background: transparent;
  margin-bottom: 4px;
}
.stTabs [data-baseweb="tab"] {
  font-family: var(--font-mono);
  font-size: var(--fs-label);
  letter-spacing: 1.5px;
  text-transform: uppercase;
  font-weight: 500;
  color: var(--fg-muted);
  background: transparent;
  padding: 10px 16px;
  border-bottom: 2px solid transparent;
  transition: color 0.15s, border-color 0.15s;
}
.stTabs [data-baseweb="tab"]::before {
  content: '◆';
  margin-right: 8px;
  color: var(--border-hi);
  font-size: 9px;
  vertical-align: middle;
  transition: color 0.15s;
}
.stTabs [data-baseweb="tab"]:hover { color: var(--fg-secondary); }
.stTabs [data-baseweb="tab"]:hover::before { color: var(--accent-2); }
.stTabs [data-baseweb="tab"][aria-selected="true"] {
  color: var(--accent);
  border-bottom-color: var(--accent);
  font-weight: 600;
}
.stTabs [data-baseweb="tab"][aria-selected="true"]::before { color: var(--accent); }
.stTabs [data-baseweb="tab-panel"] { padding-top: 22px; }
.stTabs [data-baseweb="tab-highlight"] { display: none; }

/* ── KPI executive row ── */
.kpi-row {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
  margin-bottom: 14px;
}
.kpi-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-top: 2px solid var(--fg-dim);
  padding: 14px 18px;
  border-radius: var(--r-sm);
}
.kpi-label {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 1.6px;
  text-transform: uppercase;
  color: var(--fg-muted);
  font-weight: 600;
  margin-bottom: 6px;
}
.kpi-value {
  font-family: var(--font-sans);
  font-size: var(--fs-kpi);
  font-weight: 700;
  line-height: 1;
  letter-spacing: -0.02em;
  color: var(--fg-primary);
}
.kpi-value .unit { font-size: 16px; font-weight: 500; margin-left: 2px; }
.kpi-meta {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--fg-muted);
  margin-top: 6px;
  letter-spacing: 0.3px;
}
.kpi-card-eng  { border-top-color: var(--accent); }
.kpi-card-eng  .kpi-value { color: var(--accent); }
.kpi-card-sent { border-top-color: var(--green); }
.kpi-card-sent .kpi-value { color: var(--green); }
.kpi-card-ctrl { border-top-color: var(--amber); }
.kpi-card-ctrl .kpi-value { color: var(--amber); }
.kpi-card-eff  { border-top-color: var(--blue); }
.kpi-card-eff  .kpi-value { color: var(--blue); }
.kpi-card-risk { border-top-color: var(--red); }
.kpi-card-risk .kpi-value { color: var(--red); }

/* ── Stat row ── */
.stat-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}
.stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  padding: 18px 20px;
  border-radius: var(--r-sm);
  text-align: center;
}
.stat-value {
  font-family: var(--font-sans);
  font-size: 26px;
  font-weight: 700;
  color: var(--fg-primary);
  letter-spacing: -0.01em;
  line-height: 1;
}
.stat-label {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--fg-muted);
  margin-top: 8px;
  font-weight: 600;
}

/* ── Panel ── */
.panel {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--r-sm);
  padding: 18px 20px;
  margin-bottom: 14px;
}
.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  border-bottom: 1px solid var(--border);
  padding-bottom: 10px;
  margin-bottom: 14px;
}
.panel-title {
  font-family: var(--font-mono);
  font-size: var(--fs-label);
  letter-spacing: 1.8px;
  text-transform: uppercase;
  color: var(--fg-secondary);
  font-weight: 600;
}
.panel-meta {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--fg-muted);
  letter-spacing: 0.5px;
}

/* ── Bar row (ranking) ── */
.bar-row {
  display: grid;
  grid-template-columns: 140px 1fr 120px;
  gap: 14px;
  align-items: center;
  padding: 7px 0;
  border-bottom: 1px solid var(--border-soft);
}
.bar-row:last-child { border-bottom: none; }
.bar-row-label {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--fg-secondary);
  letter-spacing: 0.2px;
}
.bar-row-val {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--fg-primary);
  text-align: right;
  font-weight: 500;
}
.bar-track {
  height: 6px;
  background: var(--bg-inset);
  border-radius: 3px;
  overflow: hidden;
}
.bar-fill { height: 100%; border-radius: 3px; background: var(--accent); }
.bar-fill-cy  { background: var(--accent); }
.bar-fill-grn { background: var(--green); }
.bar-fill-amb { background: var(--amber); }
.bar-fill-red { background: var(--red); }
.bar-fill-blu { background: var(--blue); }
.bar-fill-vio { background: var(--violet); }

/* ── Tricolor bar ── */
.bar-tri {
  display: flex;
  height: 6px;
  width: 100%;
  border-radius: 3px;
  overflow: hidden;
  background: var(--bg-inset);
}
.bar-tri > span { display: block; height: 100%; }
.bar-tri-pos { background: var(--green); }
.bar-tri-neu { background: var(--amber); }
.bar-tri-neg { background: var(--red); }

/* ── Docstrip footer ── */
.docstrip-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 24px;
  padding: 12px 4px 4px 4px;
  border-top: 1px solid var(--border);
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--fg-muted);
  letter-spacing: 0.5px;
}
.docstrip-footer .acc { color: var(--accent); }
.docstrip-footer .sep { color: var(--border-hi); margin: 0 6px; }

/* ── Indicator (semáforo refinado) ── */
.indicator {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 18px;
  border-radius: var(--r-sm);
  margin: 6px 0 14px 0;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-left-width: 3px;
}
.indicator-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.indicator-text {
  font-family: var(--font-sans);
  font-size: var(--fs-h-sm);
  font-weight: 600;
  letter-spacing: -0.005em;
  line-height: 1.4;
}
.indicator-positive { border-left-color: var(--green); }
.indicator-positive .indicator-dot { background: var(--green); box-shadow: 0 0 0 4px rgba(34,197,94,0.15); }
.indicator-positive .indicator-text { color: var(--green); }
.indicator-warning  { border-left-color: var(--amber); }
.indicator-warning .indicator-dot { background: var(--amber); box-shadow: 0 0 0 4px rgba(250,204,21,0.15); }
.indicator-warning .indicator-text { color: var(--amber); }
.indicator-critical { border-left-color: var(--red); }
.indicator-critical .indicator-dot { background: var(--red); box-shadow: 0 0 0 4px rgba(239,68,68,0.15); }
.indicator-critical .indicator-text { color: var(--red); }

/* ── Interpretation block ── */
.interpretation {
  padding: 14px 18px;
  margin: 6px 0 16px 0;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-left: 2px solid var(--accent);
  border-radius: 0 var(--r-sm) var(--r-sm) 0;
}
.interpretation-label {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 1.6px;
  text-transform: uppercase;
  color: var(--accent);
  font-weight: 600;
  margin-bottom: 6px;
}
.interpretation-texto {
  font-family: var(--font-sans);
  font-size: 12px;
  color: var(--fg-primary);
  line-height: 1.7;
}

/* ── Exec card / subheader / caption ── */
.exec-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--r-sm);
  padding: 14px 18px;
  margin-bottom: 10px;
  transition: border-color 0.18s;
}
.exec-card:hover { border-color: var(--border-hi); }
.exec-card-title {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 1.6px;
  text-transform: uppercase;
  color: var(--fg-muted);
  font-weight: 600;
  margin-bottom: 6px;
}
.exec-card-value {
  font-family: var(--font-sans);
  font-size: 22px;
  font-weight: 700;
  color: var(--fg-primary);
  line-height: 1.1;
  letter-spacing: -0.01em;
}
.exec-card-sub {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--fg-secondary);
  margin-top: 4px;
}
.exec-subheader {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 1.8px;
  text-transform: uppercase;
  color: var(--fg-secondary);
  margin: 16px 0 10px 0;
}
.exec-subheader::before {
  content: '◆';
  color: var(--accent);
  margin-right: 8px;
  font-size: 9px;
}
.exec-caption {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--fg-muted);
  margin-bottom: 12px;
  letter-spacing: 0.3px;
  line-height: 1.6;
}

/* ── Status messages ── */
.status-info, .status-warning, .status-critical {
  border-radius: var(--r-sm);
  padding: 10px 14px;
  margin: 6px 0 12px 0;
  font-family: var(--font-sans);
  font-size: 11px;
  line-height: 1.6;
  color: var(--fg-secondary);
  border: 1px solid var(--border);
  border-left-width: 2px;
  background: var(--bg-card);
}
.status-info     { border-left-color: var(--blue); }
.status-warning  { border-left-color: var(--amber); }
.status-critical { border-left-color: var(--red); color: var(--fg-primary); }
.status-label {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 1.4px;
  font-weight: 700;
  text-transform: uppercase;
  margin-right: 8px;
}
.status-label-warning { color: var(--amber); }
.status-label-caution { color: var(--blue); }

/* ── Pattern card ── */
.pattern-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--r-sm);
  padding: 12px 16px;
  margin-bottom: 10px;
}
.pattern-card-critical { border-left: 2px solid var(--red); }
.pattern-card-safe { border-left: 2px solid var(--green); }
.pattern-title {
  font-family: var(--font-sans);
  font-size: 12px;
  font-weight: 600;
  color: var(--fg-primary);
  margin-bottom: 4px;
}
.pattern-meta {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--fg-secondary);
  margin-bottom: 6px;
}
.pattern-count {
  font-family: var(--font-sans);
  font-size: 20px;
  font-weight: 700;
}

/* ── Memo (Bloque IV) ── */
.memo-container {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--r-sm);
  padding: 28px 32px;
  margin-bottom: 20px;
  position: relative;
}
.memo-container::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: linear-gradient(90deg, var(--accent), transparent);
}
.memo-header {
  margin-bottom: 22px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--border);
}
.memo-title {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 2.5px;
  color: var(--accent);
  font-weight: 700;
  text-transform: uppercase;
  margin-bottom: 4px;
}
.memo-ref {
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--fg-muted);
  letter-spacing: 0.5px;
}
.memo-section { margin-bottom: 22px; }
.memo-section-number {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 1.8px;
  color: var(--accent);
  font-weight: 700;
  margin-bottom: 4px;
}
.memo-section-title {
  font-family: var(--font-sans);
  font-size: 15px;
  font-weight: 700;
  color: var(--fg-primary);
  margin-bottom: 10px;
  letter-spacing: -0.01em;
}
.memo-body {
  font-family: var(--font-sans);
  font-size: 13px;
  color: var(--fg-primary);
  line-height: 1.75;
}
.memo-divider {
  border: none;
  border-top: 1px solid var(--border);
  margin: 16px 0;
}
.memo-item, .memo-item-positivo, .memo-item-negativo, .memo-item-neutral,
.memo-item-positive, .memo-item-negative {
  font-family: var(--font-mono);
  font-size: 12px;
  margin-bottom: 6px;
  padding: 6px 12px;
  border-left: 2px solid var(--border-hi);
  background: var(--bg-elev-1);
  color: var(--fg-secondary);
  border-radius: 0 var(--r-sm) var(--r-sm) 0;
}
.memo-item-positivo, .memo-item-positive {
  color: var(--green);
  border-left-color: var(--green);
  background: var(--green-soft);
}
.memo-item-negativo, .memo-item-negative {
  color: var(--red);
  border-left-color: var(--red);
  background: var(--red-soft);
}
.memo-item-neutral {
  color: var(--fg-secondary);
  border-left-color: var(--border-hi);
}

/* ── PDF Doc Center ── */
.doc-center {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--r-sm);
  padding: 22px 26px;
  margin-bottom: 22px;
  position: relative;
}
.doc-center::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: linear-gradient(90deg, var(--accent), transparent);
}
.doc-label {
  display: flex;
  align-items: center;
  gap: 16px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 14px;
}
.doc-icon-box {
  width: 44px;
  height: 44px;
  border: 1.5px solid var(--accent-2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 700;
  color: var(--accent);
  letter-spacing: 0.5px;
  border-radius: var(--r-sm);
  background: var(--accent-soft);
}
.doc-info { flex: 1; }
.doc-filename {
  font-family: var(--font-sans);
  font-size: 14px;
  font-weight: 600;
  color: var(--fg-primary);
  margin-bottom: 2px;
}
.doc-meta {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--fg-muted);
  letter-spacing: 0.3px;
}
.doc-empty {
  text-align: center;
  padding: 28px 20px;
  border: 1px dashed var(--border-hi);
  border-radius: var(--r-sm);
  background: var(--bg-inset);
}
.doc-empty-label {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--fg-muted);
  letter-spacing: 0.4px;
  line-height: 1.7;
  max-width: 420px;
  margin: 0 auto;
}

/* ── Sidebar items ── */
.sys-header {
  padding: 4px 0 12px 0;
  margin-bottom: 14px;
  border-bottom: 1px solid var(--border);
}
.sys-brand {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1.8px;
  color: var(--fg-primary);
  text-transform: uppercase;
}
.sys-brand-sub {
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--accent);
  margin-top: 4px;
  letter-spacing: 0.8px;
}
.sys-divider {
  border: none;
  border-top: 1px solid var(--border);
  margin: 12px 0;
}
.sys-section-label {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 1.8px;
  text-transform: uppercase;
  color: var(--fg-muted);
  font-weight: 600;
  margin: 12px 0 6px 0;
}
.sys-footer {
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--fg-muted);
  letter-spacing: 0.4px;
  padding-top: 10px;
  margin-top: 10px;
  border-top: 1px solid var(--border);
}

/* ── Streamlit inputs ── */
.stSelectbox label, .stRadio label, div[data-testid="stToggle"] label {
  font-family: var(--font-mono) !important;
  font-size: 9px !important;
  color: var(--fg-muted) !important;
  letter-spacing: 1.5px !important;
  font-weight: 600 !important;
  text-transform: uppercase !important;
}
.stSelectbox > div > div {
  background: var(--bg-card) !important;
  color: var(--fg-primary) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--r-sm) !important;
  font-family: var(--font-mono) !important;
  font-size: 11px !important;
  min-height: 32px !important;
}
.stSelectbox > div > div:hover { border-color: var(--border-hi) !important; }
.stSelectbox > div > div:focus-within {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 1px var(--accent-soft) !important;
}
div[data-testid="stRadio"] {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--r-sm);
  padding: 8px 12px;
}
div[data-testid="stRadio"] [role="radiogroup"] { gap: 4px; }
div[data-testid="stRadio"] label {
  font-family: var(--font-sans) !important;
  font-size: 11px !important;
  color: var(--fg-secondary) !important;
  letter-spacing: 0 !important;
  font-weight: 500 !important;
  text-transform: none !important;
  padding: 4px 0;
}
div[data-testid="stRadio"] label:hover { color: var(--fg-primary) !important; }
div[data-testid="stRadio"] [data-testid="stMarkdownContainer"] p {
  font-size: 11px !important;
  margin: 0;
}
div[data-testid="stToggle"] > div[aria-checked="true"] {
  background-color: var(--accent) !important;
}

/* ── Expander ── */
.streamlit-expanderHeader, [data-testid="stExpander"] summary {
  font-family: var(--font-mono) !important;
  font-size: 9px !important;
  letter-spacing: 1.4px !important;
  text-transform: uppercase !important;
  color: var(--fg-muted) !important;
  background: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--r-sm) !important;
  padding: 8px 12px !important;
  font-weight: 600 !important;
}
.streamlit-expanderHeader:hover, [data-testid="stExpander"] summary:hover {
  border-color: var(--border-hi) !important;
  color: var(--fg-secondary) !important;
}

/* ── Metric ── */
div[data-testid="stMetric"] {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--r-sm);
  padding: 14px 18px;
}
div[data-testid="stMetricValue"] {
  font-family: var(--font-sans) !important;
  font-size: 1.6rem !important;
  color: var(--fg-primary) !important;
  letter-spacing: -0.01em !important;
  font-weight: 700 !important;
}
div[data-testid="stMetricLabel"] {
  font-family: var(--font-mono) !important;
  font-size: 9px !important;
  color: var(--fg-muted) !important;
  letter-spacing: 1.4px !important;
  text-transform: uppercase !important;
  font-weight: 600 !important;
}

/* ── Typography ── */
h1, h2, h3, h4 {
  font-family: var(--font-sans) !important;
  color: var(--fg-primary) !important;
  letter-spacing: -0.01em;
}
h1 { font-size: 22px !important; font-weight: 700 !important; }
h2 { font-size: 17px !important; font-weight: 600 !important; }
h3 { font-size: 14px !important; font-weight: 600 !important; }
.stMarkdown { font-family: var(--font-sans); color: var(--fg-primary); }
.stMarkdown p { font-size: 13px; line-height: 1.65; color: var(--fg-secondary); }

/* ── Alert ── */
div[data-testid="stAlert"] {
  background: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  border-left: 2px solid var(--blue) !important;
  color: var(--fg-primary) !important;
  font-family: var(--font-sans) !important;
  font-size: 11px !important;
  border-radius: var(--r-sm) !important;
}
div[data-testid="stAlert"] [data-testid="stMarkdownContainer"] p {
  font-size: 11px !important;
  color: var(--fg-primary) !important;
}

/* ── Buttons ── */
.stButton button {
  font-family: var(--font-mono) !important;
  font-size: 10px !important;
  letter-spacing: 1.2px !important;
  text-transform: uppercase !important;
  font-weight: 600 !important;
  border-radius: var(--r-sm) !important;
  background: var(--bg-card) !important;
  border: 1px solid var(--border-hi) !important;
  color: var(--fg-primary) !important;
  padding: 8px 14px !important;
  transition: all 0.15s !important;
}
.stButton button:hover {
  background: var(--bg-card-hi) !important;
  border-color: var(--accent) !important;
  color: var(--accent) !important;
}
.stButton button[kind="primary"] {
  background: var(--accent-soft) !important;
  border-color: var(--accent) !important;
  color: var(--accent) !important;
}

/* ── Inputs ── */
.stTextInput input, .stTextArea textarea, .stNumberInput input {
  font-family: var(--font-mono) !important;
  font-size: 11px !important;
  background: var(--bg-card) !important;
  color: var(--fg-primary) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--r-sm) !important;
}
.stTextInput input:focus, .stTextArea textarea:focus, .stNumberInput input:focus {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 1px var(--accent-soft) !important;
}
.stFileUploader { font-family: var(--font-mono) !important; font-size: 10px !important; }

/* ── DataFrame ── */
div[data-testid="stDataFrame"] {
  font-family: var(--font-mono);
  font-size: 10px;
  border: 1px solid var(--border);
  border-radius: var(--r-sm);
}
div[data-testid="stDataFrame"] td {
  background: var(--bg-card) !important;
  color: var(--fg-primary) !important;
  border-color: var(--border) !important;
}
div[data-testid="stDataFrame"] th {
  background: var(--bg-elev-1) !important;
  color: var(--fg-muted) !important;
  border-color: var(--border) !important;
  font-size: 9px;
  letter-spacing: 1px;
  text-transform: uppercase;
  font-weight: 600;
}

/* ── Caption ── */
.stCaption, [data-testid="stCaptionContainer"] {
  color: var(--fg-muted) !important;
  font-family: var(--font-mono) !important;
  font-size: 10px !important;
  letter-spacing: 0.3px !important;
}

/* ── Divider ── */
hr {
  border: none !important;
  border-top: 1px solid var(--border) !important;
  margin: 16px 0 !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg-base); }
::-webkit-scrollbar-thumb { background: var(--border-hi); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--fg-dim); }

/* ── Plotly blend ── */
.js-plotly-plot, .plotly { background: transparent !important; }
.stSpinner > div { border-color: var(--accent) transparent transparent transparent !important; }

/* ── Misc utility ── */
.wys-box {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-left: 2px solid var(--accent-2);
  padding: 10px 14px;
  margin-bottom: 10px;
  border-radius: 0 var(--r-sm) var(--r-sm) 0;
}
.wys-label {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--accent-2);
  font-weight: 600;
}
.wys-text {
