"""Hoja de estilos (tema Bloomberg) del dashboard, extraida de app.py.

Uso:  from dashboard.estilos import CSS ; st.markdown(CSS, unsafe_allow_html=True)
"""

CSS = """
<style>
/* Tokens */
:root {
  --bg-base:      #0a0e17;
  --bg-surface:   #10141e;
  --bg-card:      #141822;
  --bg-elevated:  #1a1f2e;
  --fg-primary:   #e8e6e3;
  --fg-secondary: #9a9892;
  --fg-muted:     #5c5a55;
  --border:       #1e2332;
  --border-light: #2a2f3e;
  --accent:       #f0b34b;
  --accent-dim:   #a67c2e;
  --green:        #34d399;
  --green-dim:    #065f46;
  --red:          #f87171;
  --red-dim:      #7f1d1d;
  --amber:        #fbbf24;
  --amber-dim:    #713f12;
  --blue:         #60a5fa;
  --purple:       #a78bfa;
}

@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap');

.stApp { background-color: var(--bg-base); color: var(--fg-primary); }
.stSidebar { background-color: var(--bg-surface); border-right: 1px solid var(--border); }
section[data-testid="stSidebar"] { background-color: var(--bg-surface); }

.stSelectbox > div > div {
  background-color: var(--bg-card);
  color: var(--fg-primary);
  border-color: var(--border-light);
  border-radius: 2px;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 12px;
}
.stSelectbox > div > div:focus { border-color: var(--accent); box-shadow: 0 0 0 1px var(--accent-dim); }

.stRadio > div { color: var(--fg-primary); font-size: 12px; font-family: 'Inter', sans-serif; }
div[data-testid="stRadio"] label { font-size: 12px; }

div[data-testid="stToggle"] label { font-size: 12px; color: var(--fg-secondary); }
div[data-testid="stToggle"] > div[aria-checked="true"] {
  background-color: var(--accent-dim) !important;
}
div[data-testid="stMetric"] { background: var(--bg-card); border: 1px solid var(--border); border-radius: 2px; padding: 8px 12px; margin-bottom: 8px; }
div[data-testid="stMetricValue"] { font-family: 'IBM Plex Mono', monospace; font-size: 1.6rem !important; color: var(--fg-primary); }
div[data-testid="stMetricLabel"] { font-family: 'Inter', sans-serif; font-size: 0.7rem !important; color: var(--fg-muted); letter-spacing: 0.5px; text-transform: uppercase; }

.bloom-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 2px;
  padding: 16px 20px;
  margin-bottom: 10px;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.bloom-card:hover {
  border-color: var(--accent-dim);
  box-shadow: none;
}
.bloom-card-title {
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 1.8px;
  text-transform: uppercase;
  color: var(--fg-muted);
  margin-bottom: 6px;
  font-family: 'Inter', sans-serif;
}
.bloom-card-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--fg-primary);
  font-family: 'IBM Plex Mono', monospace;
  line-height: 1.1;
  letter-spacing: -0.5px;
}
.bloom-card-sub {
  font-size: 11px;
  color: var(--fg-secondary);
  margin-top: 3px;
  font-family: 'Inter', sans-serif;
}
.bloom-border-accent { border-left: 3px solid var(--accent); }

.semaforo-verde {
  background: linear-gradient(135deg, #052e16 0%, #0a3d1f 100%);
  border: 1px solid var(--green-dim);
  border-left: 4px solid var(--green);
  border-radius: 2px;
  padding: 20px 28px;
  text-align: center;
  margin-bottom: 18px;
  transition: opacity 0.3s ease;
}
.semaforo-amarillo {
  background: linear-gradient(135deg, #1c1407 0%, #2d1f07 100%);
  border: 1px solid var(--amber-dim);
  border-left: 4px solid var(--amber);
  border-radius: 2px;
  padding: 20px 28px;
  text-align: center;
  margin-bottom: 18px;
  transition: opacity 0.3s ease;
}
.semaforo-rojo {
  background: linear-gradient(135deg, #1a0505 0%, #2d0a0a 100%);
  border: 1px solid var(--red-dim);
  border-left: 4px solid var(--red);
  border-radius: 2px;
  padding: 20px 28px;
  text-align: center;
  margin-bottom: 18px;
  transition: opacity 0.3s ease;
}
.semaforo-texto {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 0.3px;
  margin: 0;
  font-family: 'Inter', sans-serif;
}
.semaforo-icono {
  font-size: 28px;
  display: block;
  margin-bottom: 6px;
}

.interpretacion-box {
  background: var(--bg-card);
  border-left: 3px solid var(--accent);
  padding: 14px 18px;
  margin-bottom: 14px;
}
.interpretacion-label {
  font-size: 9px;
  color: var(--fg-muted);
  margin: 0 0 4px 0;
  font-weight: 600;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  font-family: 'Inter', sans-serif;
}
.interpretacion-texto {
  font-size: 13px;
  color: var(--fg-primary);
  margin: 0;
  line-height: 1.7;
  font-family: 'Inter', sans-serif;
}

.seccion-header {
  border-bottom: 1px solid var(--border);
  padding-bottom: 10px;
  margin-bottom: 20px;
}
.seccion-titulo {
  font-size: 16px;
  font-weight: 700;
  color: var(--fg-primary);
  letter-spacing: 0.5px;
  font-family: 'Inter', sans-serif;
}
.seccion-subtitulo {
  font-size: 11px;
  color: var(--fg-muted);
  margin-top: 2px;
  font-family: 'Inter', sans-serif;
}

.patron-rechazo {
  background: #120808;
  border: 1px solid #3f1a1a;
  border-left: 4px solid var(--red);
  border-radius: 2px;
  padding: 18px 22px;
  margin-bottom: 14px;
}
.patron-respaldo {
  background: #071a0f;
  border: 1px solid #0a3d1f;
  border-left: 4px solid var(--green);
  border-radius: 2px;
  padding: 18px 22px;
  margin-bottom: 14px;
}
.patron-titulo { font-size: 12px; font-weight: 700; letter-spacing: 0.3px; margin-bottom: 4px; font-family: 'Inter', sans-serif; }
.patron-meta { font-size: 12px; color: var(--fg-secondary); margin-bottom: 10px; font-family: 'Inter', sans-serif; }
.patron-count { font-size: 24px; font-weight: 700; font-family: 'IBM Plex Mono', monospace; }

.comentario-rep {
  background: var(--bg-surface);
  border-left: 2px solid var(--border-light);
  padding: 10px 14px;
  font-size: 13px;
  font-style: italic;
  color: var(--fg-primary);
  margin: 6px 0;
  line-height: 1.5;
  font-family: 'Inter', sans-serif;
}
.comentario-lista { font-size: 11px; color: var(--fg-secondary); margin: 3px 0; padding-left: 10px; font-family: 'Inter', sans-serif; }

.badge-positivo { background: var(--green-dim); color: var(--green); padding: 2px 7px; font-size: 10px; font-weight: 600; font-family: 'IBM Plex Mono', monospace; letter-spacing: 0.5px; }
.badge-mixto { background: var(--amber-dim); color: var(--amber); padding: 2px 7px; font-size: 10px; font-weight: 600; font-family: 'IBM Plex Mono', monospace; letter-spacing: 0.5px; }
.badge-critico { background: var(--red-dim); color: var(--red); padding: 2px 7px; font-size: 10px; font-weight: 600; font-family: 'IBM Plex Mono', monospace; letter-spacing: 0.5px; }

.riesgo-alto { color: var(--red); font-weight: 700; font-size: 11px; font-family: 'IBM Plex Mono', monospace; }
.riesgo-medio { color: var(--amber); font-weight: 700; font-size: 11px; font-family: 'IBM Plex Mono', monospace; }
.riesgo-bajo { color: var(--green); font-weight: 700; font-size: 11px; font-family: 'IBM Plex Mono', monospace; }

.senal-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 2px;
  padding: 18px 22px;
  margin-bottom: 14px;
}
.senal-numero {
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 2px;
  color: var(--fg-muted);
  text-transform: uppercase;
  font-family: 'IBM Plex Mono', monospace;
}
.senal-titulo {
  font-size: 14px;
  font-weight: 700;
  color: var(--fg-primary);
  margin: 4px 0 10px 0;
  font-family: 'Inter', sans-serif;
}

.anomalia-item {
  background: #120808;
  border: 1px solid #3f1a1a;
  border-radius: 2px;
  padding: 10px 14px;
  margin: 6px 0;
  font-size: 12px;
}

.que-ves-box {
  background: var(--bg-surface);
  border-left: 2px solid var(--border-light);
  padding: 8px 12px;
  margin-bottom: 10px;
}
.que-ves-label {
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 1.5px;
  color: var(--fg-muted);
  text-transform: uppercase;
  font-family: 'IBM Plex Mono', monospace;
}
.que-ves-texto {
  font-size: 11px;
  color: var(--fg-secondary);
  margin: 3px 0 0 0;
  line-height: 1.5;
  font-family: 'Inter', sans-serif;
}

.tabla-grid {
  display: grid;
  padding: 8px 14px;
  border-bottom: 1px solid var(--border);
  font-size: 12px;
  align-items: center;
}
.tabla-header {
  padding: 8px 14px;
  border-bottom: 1px solid var(--border-light);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 1px;
  color: var(--fg-muted);
  text-transform: uppercase;
  font-family: 'IBM Plex Mono', monospace;
}
.tabla-numero {
  font-family: 'IBM Plex Mono', monospace;
  color: var(--blue);
  font-weight: 700;
}

@keyframes blinkFadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes pulseGlow {
  0%, 100% { box-shadow: 0 0 0 rgba(240, 179, 75, 0); }
  50% { box-shadow: 0 0 6px rgba(240, 179, 75, 0.15); }
}
@keyframes cursorBlink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
@keyframes countUp {
  from { opacity: 0; }
  to { opacity: 1; }
}
.card-animate {
  animation: blinkFadeIn 0.4s ease both;
}
.semaforo-verde, .semaforo-amarillo, .semaforo-rojo {
  animation: blinkFadeIn 0.5s ease both;
}
.bloom-card {
  animation: blinkFadeIn 0.35s ease both;
}
.bloom-card:nth-child(2) { animation-delay: 0.05s; }
.bloom-card:nth-child(3) { animation-delay: 0.1s; }
.bloom-card:nth-child(4) { animation-delay: 0.15s; }
.bloom-card:nth-child(5) { animation-delay: 0.2s; }

h1, h2, h3, h4 { font-family: 'Inter', sans-serif !important; color: var(--fg-primary) !important; letter-spacing: -0.02em; }
h1 { font-size: 1.4rem !important; font-weight: 700 !important; }
h2 { font-size: 1.15rem !important; font-weight: 600 !important; }
h3 { font-size: 1rem !important; font-weight: 600 !important; }
.stMarkdown { font-family: 'Inter', sans-serif; color: var(--fg-primary); }

div[data-testid="stAlert"] { background: var(--bg-card) !important; border: 1px solid var(--border) !important; border-left: 3px solid var(--accent) !important; color: var(--fg-primary) !important; font-family: 'Inter', sans-serif; font-size: 12px !important; border-radius: 2px !important; }
div[data-testid="stAlert"] [data-testid="stMarkdownContainer"] p { font-size: 12px !important; color: var(--fg-primary) !important; }
.st-bd { background-color: transparent !important; }

hr.stDivider { border-color: var(--border) !important; margin-top: 20px !important; margin-bottom: 20px !important; }

.stCaption { color: var(--fg-muted) !important; font-family: 'IBM Plex Mono', monospace !important; font-size: 10px !important; }

div[data-testid="stDataFrame"] { font-family: 'IBM Plex Mono', monospace; font-size: 11px; }
div[data-testid="stDataFrame"] td { background: var(--bg-surface) !important; color: var(--fg-primary) !important; border-color: var(--border) !important; }
div[data-testid="stDataFrame"] th { background: var(--bg-elevated) !important; color: var(--fg-muted) !important; border-color: var(--border) !important; font-size: 10px; letter-spacing: 0.5px; text-transform: uppercase; }

::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg-base); }
::-webkit-scrollbar-thumb { background: var(--border-light); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--fg-muted); }

.grid-header {
  display: grid; padding: 10px 16px; border-bottom: 2px solid var(--border-light);
  font-size: 11px; font-weight: 600; letter-spacing: 1px;
  color: var(--fg-muted); text-transform: uppercase;
}
.grid-row {
  display: grid; padding: 14px 16px; border-bottom: 1px solid var(--border);
  font-size: 13px; align-items: center;
}
.grid-num {
  font-family: 'IBM Plex Mono', monospace; color: var(--blue); font-weight: 700;
}
.grid-label { font-weight: 600; color: var(--fg-primary); }
.grid-muted { color: var(--fg-secondary); }

.bloom-status-info {
  background: var(--bg-card); border: 1px solid var(--border);
  border-left: 3px solid var(--blue); border-radius: 2px;
  padding: 12px 16px; margin-bottom: 14px;
  font-size: 12px; color: var(--fg-primary); font-family: 'Inter', sans-serif;
}
.bloom-status-warning {
  background: var(--bg-card); border: 1px solid var(--border);
  border-left: 3px solid var(--amber); border-radius: 2px;
  padding: 12px 16px; margin-bottom: 14px;
  font-size: 12px; color: var(--fg-primary); font-family: 'Inter', sans-serif;
}
.bloom-status-label {
  color: var(--amber); font-size: 10px; font-weight: 700;
  letter-spacing: 1px; text-transform: uppercase;
  font-family: 'IBM Plex Mono', monospace;
}

.bloom-subheader {
  font-size: 15px; font-weight: 600; color: var(--fg-primary);
  font-family: 'Inter', sans-serif; letter-spacing: -0.02em; margin-bottom: 6px;
}
.bloom-caption {
  font-size: 10px; color: var(--fg-muted);
  font-family: 'IBM Plex Mono', monospace; margin-bottom: 14px;
}

.plat-badge-fb {
  background: #1877f2; color: white; padding: 2px 8px;
  font-size: 10px; font-weight: 700; letter-spacing: 0.5px;
  font-family: 'IBM Plex Mono', monospace;
}
.plat-badge-tk {
  background: #ff0050; color: white; padding: 2px 8px;
  font-size: 10px; font-weight: 700; letter-spacing: 0.5px;
  font-family: 'IBM Plex Mono', monospace;
}
.cat-tag {
  background: var(--bg-elevated); color: var(--fg-muted);
  padding: 2px 8px; font-size: 10px;
  font-family: 'IBM Plex Mono', monospace;
}

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
  div[data-testid="stMetricValue"] { font-size: 1.3rem !important; }
  div[data-testid="stMetricLabel"] { font-size: 0.7rem !important; }
  .block-container { padding-left: 0.6rem !important; padding-right: 0.6rem !important; padding-top: 0.8rem !important; }
  h1 { font-size: 1.4rem !important; }
  h2 { font-size: 1.15rem !important; }
  h3 { font-size: 1rem !important; }
}
</style>
"""
