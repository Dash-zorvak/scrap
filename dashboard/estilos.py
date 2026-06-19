"""Sistema de diseno ejecutivo corporativo — Sala de Situacion Estrategica.

Inspirado en dashboards de inteligencia corporativa, centros de monitoreo
ejecutivo y herramientas de toma de decisiones de alto nivel.

Uso:  from dashboard.estilos import CSS ; st.markdown(CSS, unsafe_allow_html=True)
"""

CSS = """
<style>
/* ═══════════════════════════════════════════
   SISTEMA DE DISENO EJECUTIVO
   Sala de situacion corporativa · Centro de monitoreo estrategico
   Inspirado en dashboards de inteligencia, consultoria de alto nivel
   y herramientas de decision ejecutiva.
   ═══════════════════════════════════════════ */

/* ── Tokens ── */
:root {
  --bg-base:      #0a0d14;
  --bg-surface:   #0f131e;
  --bg-card:      #141926;
  --bg-elevated:  #1a2030;
  --fg-primary:   #e6e4dd;
  --fg-secondary: #888580;
  --fg-muted:     #555555;
  --border:       #1e2435;
  --border-light: #282f42;
  --accent:       #f0a820;
  --accent-dim:   #9a6e00;
  --accent-subtle:rgba(240, 168, 32, 0.07);
  --green:        #22c55e;
  --green-dim:    rgba(34, 197, 94, 0.12);
  --green-bg:     rgba(34, 197, 94, 0.06);
  --red:          #ef4444;
  --red-dim:      rgba(239, 68, 68, 0.12);
  --red-bg:       rgba(239, 68, 68, 0.06);
  --amber:        #eab308;
  --amber-dim:    rgba(234, 179, 8, 0.12);
  --amber-bg:     rgba(234, 179, 8, 0.06);
  --blue:         #3b82f6;
  --blue-dim:     rgba(59, 130, 246, 0.12);
  --blue-bg:      rgba(59, 130, 246, 0.06);
  --font-display: Inter, system-ui, -apple-system, sans-serif;
  --font-mono:    "IBM Plex Mono", ui-monospace, Menlo, monospace;
}

/* ── Layout raiz ── */
.stApp {
  background-color: var(--bg-base);
  color: var(--fg-primary);
}

.block-container {
  padding-top: 1rem !important;
  padding-bottom: 2rem !important;
}

/* ── Header del sistema (sidebar branding) ── */
.sys-header {
  padding-bottom: 12px;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--border);
}
.sys-brand {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 2px;
  color: var(--fg-primary);
  font-family: var(--font-display);
  text-transform: uppercase;
}
.sys-brand-sub {
  font-size: 9px;
  color: var(--fg-muted);
  margin-top: 2px;
  font-family: var(--font-mono);
}
.sys-divider {
  border: none;
  border-top: 1px solid var(--border);
  margin: 8px 0;
}
.sys-section-label {
  font-size: 8px;
  letter-spacing: 1.8px;
  color: var(--fg-muted);
  font-weight: 600;
  font-family: var(--font-mono);
  text-transform: uppercase;
  margin-bottom: 8px;
  padding-top: 4px;
}
.sys-footer {
  font-size: 8px;
  color: var(--fg-muted);
  font-family: var(--font-mono);
  letter-spacing: 0.5px;
  padding-top: 8px;
  border-top: 1px solid var(--border);
}

/* ── Sidebar ── */
.stSidebar {
  background-color: var(--bg-surface);
  border-right: 1px solid var(--border);
}
section[data-testid="stSidebar"] {
  background-color: var(--bg-surface);
  width: 230px !important;
}
section[data-testid="stSidebar"] .block-container {
  padding: 0.8rem !important;
}

/* ── Selectbox ── */
.stSelectbox > div > div {
  background-color: var(--bg-card);
  color: var(--fg-primary);
  border-color: var(--border-light);
  border-radius: 4px;
  font-family: var(--font-mono);
  font-size: 11px;
  min-height: 30px;
}
.stSelectbox > div > div:hover {
  border-color: var(--accent-dim);
}
.stSelectbox > div > div:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 1px var(--accent-dim);
}
.stSelectbox label {
  font-size: 9px !important;
  color: var(--fg-muted) !important;
  font-family: var(--font-mono) !important;
  letter-spacing: 1px !important;
  font-weight: 600 !important;
  text-transform: uppercase !important;
}

/* ── Radio ── */
.stRadio > div {
  color: var(--fg-primary);
  font-size: 11px;
  font-family: var(--font-display);
}
div[data-testid="stRadio"] label {
  font-size: 11px;
  color: var(--fg-secondary);
  font-family: var(--font-display);
}
div[data-testid="stRadio"] label:hover {
  color: var(--fg-primary);
}
div[data-testid="stRadio"] [data-testid="stMarkdownContainer"] p {
  font-size: 11px;
}

/* ── Toggle ── */
div[data-testid="stToggle"] label {
  font-size: 10px;
  color: var(--fg-secondary);
  font-family: var(--font-mono);
  letter-spacing: 0.5px;
}
div[data-testid="stToggle"] > div[aria-checked="true"] {
  background-color: var(--accent-dim) !important;
}

/* ── Metric ── */
div[data-testid="stMetric"] {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 12px 16px;
  margin-bottom: 8px;
}
div[data-testid="stMetricValue"] {
  font-family: var(--font-mono);
  font-size: 1.4rem !important;
  color: var(--fg-primary);
  letter-spacing: -0.3px;
}
div[data-testid="stMetricLabel"] {
  font-family: var(--font-display);
  font-size: 0.6rem !important;
  color: var(--fg-muted);
  letter-spacing: 0.6px;
  text-transform: uppercase;
}

/* ── Expander ── */
.streamlit-expanderHeader {
  font-family: var(--font-mono) !important;
  font-size: 10px !important;
  color: var(--fg-muted) !important;
  background: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 4px !important;
  padding: 6px 12px !important;
}
.streamlit-expanderHeader:hover {
  border-color: var(--accent-dim) !important;
}
.streamlit-expanderContent {
  border: 1px solid var(--border) !important;
  border-top: none !important;
  background: var(--bg-surface) !important;
  border-radius: 0 0 4px 4px !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
  gap: 0;
  border-bottom: 1px solid var(--border);
  background: transparent;
}
.stTabs [data-baseweb="tab"] {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.8px;
  color: var(--fg-muted);
  background: transparent;
  padding: 8px 16px;
  border-bottom: 2px solid transparent;
  transition: color 0.15s, border-color 0.15s;
  text-transform: uppercase;
}
.stTabs [data-baseweb="tab"]:hover {
  color: var(--fg-primary);
  border-bottom-color: var(--border-light);
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
  color: var(--accent);
  border-bottom-color: var(--accent);
  font-weight: 600;
}
.stTabs [data-baseweb="tab-panel"] {
  padding-top: 20px;
}

/* ── Section Headers ── */
.section-header {
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
}
.section-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--fg-primary);
  letter-spacing: 0.2px;
  font-family: var(--font-display);
}
.section-subtitle {
  font-size: 9px;
  color: var(--fg-muted);
  margin-top: 3px;
  font-family: var(--font-mono);
  letter-spacing: 0.3px;
}

/* ── Section number prefix ── */
.section-num {
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--accent-dim);
  letter-spacing: 1px;
  font-weight: 600;
  margin-bottom: 6px;
}

/* ── Cards ── */
.exec-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 16px 18px;
  margin-bottom: 10px;
  transition: border-color 0.2s ease;
}
.exec-card:hover {
  border-color: var(--border-light);
}
.exec-card-title {
  font-size: 8px;
  font-weight: 600;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--fg-muted);
  margin-bottom: 4px;
  font-family: var(--font-mono);
}
.exec-card-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--fg-primary);
  font-family: var(--font-mono);
  line-height: 1.1;
  letter-spacing: -0.3px;
}
.exec-card-sub {
  font-size: 9px;
  color: var(--fg-secondary);
  margin-top: 3px;
  font-family: var(--font-mono);
}

/* ── Executive Metric Row ── */
.exec-metric-row {
  display: flex;
  gap: 10px;
  margin-bottom: 14px;
}
.exec-metric {
  flex: 1;
  background: var(--bg-card);
  border: 1px solid var(--border);
  padding: 14px 16px;
  border-radius: 4px;
}
.exec-metric-label {
  font-size: 8px;
  letter-spacing: 1.2px;
  color: var(--fg-muted);
  font-weight: 600;
  text-transform: uppercase;
  font-family: var(--font-mono);
  margin-bottom: 3px;
}
.exec-metric-value {
  font-size: 22px;
  font-weight: 700;
  color: var(--fg-primary);
  font-family: var(--font-mono);
  line-height: 1.2;
  letter-spacing: -0.3px;
}
.exec-metric-delta {
  font-size: 9px;
  color: var(--fg-secondary);
  font-family: var(--font-display);
  margin-top: 2px;
}

/* ── Indicator (semaforo refinado) ── */
.indicator {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  border-radius: 4px;
  margin-bottom: 16px;
}
.indicator-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.indicator-text {
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.2px;
  font-family: var(--font-display);
  line-height: 1.3;
}
.indicator-positive {
  background: var(--green-bg);
  border: 1px solid var(--green-dim);
}
.indicator-positive .indicator-dot {
  background: var(--green);
}
.indicator-positive .indicator-text {
  color: var(--green);
}
.indicator-warning {
  background: var(--amber-bg);
  border: 1px solid var(--amber-dim);
}
.indicator-warning .indicator-dot {
  background: var(--amber);
}
.indicator-warning .indicator-text {
  color: var(--amber);
}
.indicator-critical {
  background: var(--red-bg);
  border: 1px solid var(--red-dim);
}
.indicator-critical .indicator-dot {
  background: var(--red);
}
.indicator-critical .indicator-text {
  color: var(--red);
}

/* ── Interpretation block ── */
.interpretation {
  padding: 12px 16px;
  margin-bottom: 14px;
  border-left: 2px solid var(--border-light);
  background: var(--bg-surface);
  border-radius: 0 4px 4px 0;
}
.interpretation-label {
  font-size: 8px;
  color: var(--fg-muted);
  margin: 0 0 4px 0;
  font-weight: 600;
  letter-spacing: 1.2px;
  text-transform: uppercase;
  font-family: var(--font-mono);
}
.interpretation-texto {
  font-size: 12px;
  color: var(--fg-primary);
  margin: 0;
  line-height: 1.7;
  font-family: var(--font-display);
}

/* ── Subheaders ── */
.exec-subheader {
  font-size: 13px;
  font-weight: 600;
  color: var(--fg-primary);
  font-family: var(--font-display);
  letter-spacing: -0.01em;
  margin-bottom: 8px;
}
.exec-caption {
  font-size: 9px;
  color: var(--fg-muted);
  font-family: var(--font-mono);
  margin-bottom: 12px;
  letter-spacing: 0.3px;
}

/* ── Status Messages ── */
.status-info {
  background: var(--blue-bg);
  border: 1px solid var(--blue-dim);
  border-radius: 4px;
  padding: 10px 14px;
  margin-bottom: 12px;
  font-size: 11px;
  color: var(--fg-primary);
  font-family: var(--font-display);
  line-height: 1.5;
}
.status-warning {
  background: var(--amber-bg);
  border: 1px solid var(--amber-dim);
  border-radius: 4px;
  padding: 10px 14px;
  margin-bottom: 12px;
  font-size: 11px;
  color: var(--fg-primary);
  font-family: var(--font-display);
  line-height: 1.5;
}
.status-critical {
  background: var(--red-bg);
  border: 1px solid var(--red-dim);
  border-radius: 4px;
  padding: 10px 14px;
  margin-bottom: 12px;
  font-size: 11px;
  color: var(--fg-primary);
  font-family: var(--font-display);
  line-height: 1.5;
}
.status-label {
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.8px;
  text-transform: uppercase;
  font-family: var(--font-mono);
}
.status-label-warning {
  color: var(--amber);
}
.status-label-caution {
  color: var(--blue);
}

/* ── Pattern cards (riesgo) -- */
.pattern-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 14px 18px;
  margin-bottom: 12px;
}
.pattern-card-critical {
  border-left: 3px solid var(--red);
  background: var(--red-bg);
}
.pattern-card-safe {
  border-left: 3px solid var(--green);
  background: var(--green-bg);
}
.pattern-title {
  font-size: 11px;
  font-weight: 700;
  margin-bottom: 4px;
  font-family: var(--font-display);
}
.pattern-meta {
  font-size: 10px;
  color: var(--fg-secondary);
  margin-bottom: 8px;
  font-family: var(--font-mono);
}
.pattern-count {
  font-size: 20px;
  font-weight: 700;
  font-family: var(--font-mono);
}

/* ── Comment display ── */
.comment-quote {
  background: var(--bg-surface);
  border-left: 2px solid var(--border-light);
  padding: 8px 12px;
  font-size: 11px;
  font-style: italic;
  color: var(--fg-primary);
  margin: 6px 0;
  line-height: 1.5;
  font-family: var(--font-display);
  border-radius: 0 4px 4px 0;
}

/* ── Badges ── */
.badge {
  display: inline-block;
  padding: 2px 8px;
  font-size: 9px;
  font-weight: 600;
  font-family: var(--font-mono);
  letter-spacing: 0.4px;
  border-radius: 2px;
}
.badge-positive {
  background: var(--green-dim);
  color: var(--green);
}
.badge-mixed {
  background: var(--amber-dim);
  color: var(--amber);
}
.badge-critical {
  background: var(--red-dim);
  color: var(--red);
}

/* ── Risk indicators ── */
.risk-high { color: var(--red); font-weight: 700; font-size: 10px; font-family: var(--font-mono); }
.risk-medium { color: var(--amber); font-weight: 700; font-size: 10px; font-family: var(--font-mono); }
.risk-low { color: var(--green); font-weight: 700; font-size: 10px; font-family: var(--font-mono); }

/* ── Signal card ── */
.signal-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 16px 20px;
  margin-bottom: 12px;
}
.signal-number {
  font-size: 8px;
  font-weight: 600;
  letter-spacing: 1.5px;
  color: var(--fg-muted);
  text-transform: uppercase;
  font-family: var(--font-mono);
}
.signal-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--fg-primary);
  margin: 4px 0 8px 0;
  font-family: var(--font-display);
}
.signal-body {
  font-size: 11px;
  color: var(--fg-secondary);
  line-height: 1.6;
  font-family: var(--font-display);
}

/* ── Anomaly item ── */
.anomaly-item {
  background: var(--red-bg);
  border: 1px solid var(--red-dim);
  border-radius: 4px;
  padding: 8px 12px;
  margin: 6px 0;
  font-size: 11px;
  border-left: 2px solid var(--red);
}

/* ── What-You-See box ── */
.wys-box {
  background: var(--bg-surface);
  border-left: 2px solid var(--border-light);
  padding: 8px 12px;
  margin-bottom: 10px;
  border-radius: 0 4px 4px 0;
}
.wys-label {
  font-size: 8px;
  font-weight: 600;
  letter-spacing: 1.2px;
  color: var(--fg-muted);
  text-transform: uppercase;
  font-family: var(--font-mono);
}
.wys-text {
  font-size: 10px;
  color: var(--fg-secondary);
  margin: 3px 0 0 0;
  line-height: 1.5;
  font-family: var(--font-display);
}

/* ── Grid table ── */
.grid-table {
  display: grid;
  padding: 8px 14px;
  border-bottom: 1px solid var(--border);
  font-size: 11px;
  align-items: center;
}
.grid-header {
  padding: 8px 14px;
  border-bottom: 1px solid var(--border-light);
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 0.8px;
  color: var(--fg-muted);
  text-transform: uppercase;
  font-family: var(--font-mono);
}
.grid-number {
  font-family: var(--font-mono);
  color: var(--blue);
  font-weight: 700;
}

/* ── Executive Memo (Bloque IV) ── */
.memo-container {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 32px 36px;
  margin-bottom: 24px;
  position: relative;
}
.memo-container::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, var(--accent), transparent);
}
.memo-header {
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border);
}
.memo-title {
  font-size: 10px;
  letter-spacing: 2.5px;
  color: var(--accent);
  font-weight: 700;
  text-transform: uppercase;
  font-family: var(--font-mono);
  margin-bottom: 4px;
}
.memo-ref {
  font-size: 9px;
  color: var(--fg-muted);
  font-family: var(--font-mono);
}
.memo-section {
  margin-bottom: 20px;
}
.memo-section-number {
  font-size: 8px;
  letter-spacing: 1.8px;
  color: var(--accent-dim);
  font-weight: 600;
  font-family: var(--font-mono);
  margin-bottom: 2px;
}
.memo-section-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--fg-primary);
  font-family: var(--font-display);
  margin-bottom: 8px;
  letter-spacing: -0.01em;
}
.memo-section-title::after {
  content: '';
  display: block;
  width: 24px;
  height: 1px;
  background: var(--accent-dim);
  margin-top: 4px;
}
.memo-body {
  font-size: 13px;
  color: var(--fg-primary);
  line-height: 1.7;
  font-family: var(--font-display);
  margin: 0;
}
.memo-divider {
  border: none;
  border-top: 1px solid var(--border-light);
  margin: 16px 0;
}
.memo-item {
  margin-bottom: 6px;
  font-size: 12px;
  color: var(--fg-secondary);
  font-family: var(--font-mono);
  padding-left: 12px;
  border-left: 2px solid var(--border-light);
}
.memo-item-positive {
  color: var(--green);
  border-left-color: var(--green);
}
.memo-item-negative {
  color: var(--red);
  border-left-color: var(--red);
}
.memo-item-neutral {
  color: var(--fg-secondary);
  border-left-color: var(--border-light);
}

/* ── PDF Document Center ── */
.doc-center {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 24px 28px;
  margin-bottom: 24px;
  position: relative;
}
.doc-center::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, var(--accent), transparent);
}
.doc-label {
  display: flex;
  align-items: center;
  gap: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 16px;
}
.doc-icon-box {
  width: 44px;
  height: 44px;
  border: 1.5px solid var(--accent-dim);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  color: var(--accent);
  font-family: var(--font-mono);
  font-weight: 700;
  letter-spacing: 0.5px;
  border-radius: 2px;
}
.doc-info {
  flex: 1;
}
.doc-filename {
  font-size: 13px;
  font-weight: 600;
  color: var(--fg-primary);
  font-family: var(--font-display);
  margin-bottom: 2px;
}
.doc-meta {
  font-size: 9px;
  color: var(--fg-muted);
  font-family: var(--font-mono);
}
.doc-empty {
  text-align: center;
  padding: 28px 16px;
  border: 1px dashed var(--border-light);
  border-radius: 4px;
}
.doc-empty-label {
  font-size: 9px;
  color: var(--fg-muted);
  font-family: var(--font-mono);
  letter-spacing: 0.5px;
  max-width: 360px;
  margin: 0 auto;
  line-height: 1.6;
}

/* ── Platform badges ── */
.plat-badge-fb {
  display: inline-block;
  background: #1877f2; color: white; padding: 2px 7px;
  font-size: 9px; font-weight: 700; letter-spacing: 0.4px;
  font-family: var(--font-mono); border-radius: 2px;
}
.plat-badge-tk {
  display: inline-block;
  background: #ff0050; color: white; padding: 2px 7px;
  font-size: 9px; font-weight: 700; letter-spacing: 0.4px;
  font-family: var(--font-mono); border-radius: 2px;
}
.cat-tag {
  display: inline-block;
  background: var(--bg-elevated); color: var(--fg-muted);
  padding: 2px 7px; font-size: 9px;
  font-family: var(--font-mono); border-radius: 2px;
}

/* ── Typography ── */
h1, h2, h3, h4 {
  font-family: var(--font-display) !important;
  color: var(--fg-primary) !important;
  letter-spacing: -0.01em;
}
h1 { font-size: 1.2rem !important; font-weight: 700 !important; }
h2 { font-size: 1rem !important; font-weight: 600 !important; }
h3 { font-size: 0.9rem !important; font-weight: 600 !important; }
.stMarkdown {
  font-family: var(--font-display);
  color: var(--fg-primary);
}
.stMarkdown p {
  font-size: 12px;
  line-height: 1.6;
}

/* ── Alert overwrite ── */
div[data-testid="stAlert"] {
  background: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  border-left: 2px solid var(--blue) !important;
  color: var(--fg-primary) !important;
  font-family: var(--font-mono) !important;
  font-size: 11px !important;
  border-radius: 4px !important;
}
div[data-testid="stAlert"] [data-testid="stMarkdownContainer"] p {
  font-size: 11px !important;
  color: var(--fg-primary) !important;
}
.st-bd { background-color: transparent !important; }

/* ── Divider ── */
hr.stDivider {
  border-color: var(--border) !important;
  margin-top: 16px !important;
  margin-bottom: 16px !important;
}

/* ── Caption ── */
.stCaption {
  color: var(--fg-muted) !important;
  font-family: var(--font-mono) !important;
  font-size: 9px !important;
}

/* ── DataFrame ── */
div[data-testid="stDataFrame"] {
  font-family: var(--font-mono);
  font-size: 10px;
}
div[data-testid="stDataFrame"] td {
  background: var(--bg-surface) !important;
  color: var(--fg-primary) !important;
  border-color: var(--border) !important;
}
div[data-testid="stDataFrame"] th {
  background: var(--bg-elevated) !important;
  color: var(--fg-muted) !important;
  border-color: var(--border) !important;
  font-size: 9px;
  letter-spacing: 0.4px;
  text-transform: uppercase;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: var(--bg-base); }
::-webkit-scrollbar-thumb { background: var(--border-light); border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: var(--fg-muted); }

/* ── Grid helpers ── */
.grid-row {
  display: grid; padding: 10px 14px; border-bottom: 1px solid var(--border);
  font-size: 11px; align-items: center;
}
.grid-label { font-weight: 600; color: var(--fg-primary); }
.grid-muted { color: var(--fg-secondary); }

/* ── Button overwrite ── */
.stButton button {
  font-family: var(--font-mono) !important;
  font-size: 10px !important;
  letter-spacing: 0.4px !important;
  border-radius: 4px !important;
}

/* ── Form overwrite ── */
.stTextInput input, .stTextArea textarea, .stNumberInput input {
  font-family: var(--font-mono) !important;
  font-size: 11px !important;
  background: var(--bg-card) !important;
  color: var(--fg-primary) !important;
  border-color: var(--border-light) !important;
  border-radius: 4px !important;
}
.stTextInput input:focus, .stTextArea textarea:focus, .stNumberInput input:focus {
  border-color: var(--accent-dim) !important;
  box-shadow: 0 0 0 1px var(--accent-dim) !important;
}
.stFileUploader {
  font-family: var(--font-mono) !important;
  font-size: 10px !important;
}

/* ── Progress / Status ── */
.stStatusWidget {
  font-family: var(--font-mono) !important;
  font-size: 10px !important;
  background: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 4px !important;
}

/* ── Notification ── */
div[data-testid="stNotification"] {
  font-family: var(--font-mono) !important;
}

/* ── Animations ── */
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(3px); }
  to { opacity: 1; transform: translateY(0); }
}
.card-animate {
  animation: fadeIn 0.35s ease both;
}
.exec-card {
  animation: fadeIn 0.35s ease both;
}
.exec-card:nth-child(2) { animation-delay: 0.05s; }
.exec-card:nth-child(3) { animation-delay: 0.1s; }
.exec-card:nth-child(4) { animation-delay: 0.15s; }
.exec-card:nth-child(5) { animation-delay: 0.2s; }

/* ═══════════════════════════════════════════
   RESPONSIVE — Layout adaptativo
   ═══════════════════════════════════════════ */

/* ── Tablet (768px - 1024px) ── */
@media (max-width: 1024px) {
  section[data-testid="stSidebar"] {
    width: 200px !important;
  }
  .block-container {
    padding-left: 1rem !important;
    padding-right: 1rem !important;
  }
}

/* ── Small tablet / large phone (640px - 768px) ── */
@media (max-width: 768px) {
  section[data-testid="stSidebar"] {
    width: 100% !important;
    min-width: 100% !important;
    position: relative !important;
  }
  .block-container {
    padding-top: 0.6rem !important;
    padding-left: 0.8rem !important;
    padding-right: 0.8rem !important;
  }
  .memo-container {
    padding: 20px !important;
  }
  .doc-center {
    padding: 18px 16px !important;
  }
}

/* ── Phone (< 640px) ── */
@media (max-width: 640px) {
  div[data-testid="stHorizontalBlock"] {
    flex-direction: column !important;
    gap: 0.4rem !important;
  }
  div[data-testid="stHorizontalBlock"] > div[data-testid="column"],
  div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
    width: 100% !important;
    flex: 1 1 100% !important;
    min-width: 100% !important;
  }
  div[data-testid="stMetricValue"] { font-size: 1.1rem !important; }
  div[data-testid="stMetricLabel"] { font-size: 0.55rem !important; }
  .block-container {
    padding-left: 0.5rem !important;
    padding-right: 0.5rem !important;
    padding-top: 0.5rem !important;
  }
  h1 { font-size: 1.1rem !important; }
  h2 { font-size: 0.95rem !important; }
  h3 { font-size: 0.85rem !important; }
  .stTabs [data-baseweb="tab"] {
    font-size: 8px;
    padding: 6px 10px;
  }
  .memo-container {
    padding: 14px 12px !important;
  }
  .memo-body {
    font-size: 12px !important;
  }
  .memo-section-title {
    font-size: 12px !important;
  }
  .exec-metric-row {
    flex-direction: column;
    gap: 8px;
  }
  .doc-label {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
}
</style>
"""
