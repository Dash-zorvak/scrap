# Parches reales — Bloque I Pulso General

Esto reemplaza por completo las instrucciones anteriores (`OPENCODE_INSTRUCTIONS.md`). Ya NO se crean archivos nuevos. Todo se aplica sobre los 2 archivos reales que ya existen en el repo.

---

## 0) Diagnóstico de lo que ya se ejecutó

Revisé la rama por defecto de `Dash-zorvak/scrap` en GitHub y estos 5 archivos que te di antes **NO existen ahí**:

- `dashboard/tema_taxonomia_expandida.py`
- `dashboard/bloque1_narrativas.py`
- `dashboard/app_bloque1_snippets.py`
- `data/analysis_schema_bloque1_actualizado.json`
- `README_CAMBIOS.md`

Eso significa que esos cambios NUNCA llegaron a la rama principal publicada. Solo pueden estar en: (a) tu copia local sin commitear, (b) un commit local sin pushear, o (c) una rama distinta que sí se subió.

### Ejecuta esto primero y compara con los 4 escenarios:

```bash
git status
git branch --show-current
git log --oneline -5
```

**Escenario A — estás en una rama nueva (no main/master):**
```bash
git checkout main            # o master, tu rama por defecto
git pull origin main
git branch -D NOMBRE_DE_LA_RAMA
git push origin --delete NOMBRE_DE_LA_RAMA   # solo si se llegó a subir
```
Esto restaura `main` exactamente como está publicado — no hay nada que limpiar ahí porque esos archivos nunca la tocaron.

**Escenario B — estás en main/master con cambios sin commitear:**
```bash
git status --porcelain        # confirma la lista de archivos
git checkout -- .             # descarta cambios en archivos YA existentes (ej. si tocó app.py)
rm -f dashboard/tema_taxonomia_expandida.py
rm -f dashboard/bloque1_narrativas.py
rm -f dashboard/app_bloque1_snippets.py
rm -f data/analysis_schema_bloque1_actualizado.json
rm -f README_CAMBIOS.md
rm -f OPENCODE_INSTRUCTIONS.md   # si quedó copiado dentro del repo
```
(No uses `git clean -fd` a ciegas: borra CUALQUIER archivo sin trackear, incluso los que no tienen que ver con esto.)

**Escenario C — ya hiciste commit local pero NO push:**
```bash
git log --oneline -5     # identifica el sha ANTERIOR a esos commits
git reset --hard SHA_ANTERIOR
```

**Escenario D — ya hiciste commit Y push a main:**
No corras `reset --hard` + push forzado (reescribe historia compartida). Avísame con el sha del commit y te doy el `git revert` exacto.

> **Sobre tu pregunta de `git pull`:** solo te "limpia" en el Escenario A (tu rama local no tiene commits propios, así que se sobreescribe con lo remoto). Si ya se hizo push directo a main (Escenario D), `git pull` no deshace nada — necesitas `git revert`.

---

## 1) ¿Se necesita `data/ANALYST_GUIDE.md`?

Tienes razón en algo clave: **confirmé leyendo `dashboard/app.py` que nunca importa ni lee `ANALYST_GUIDE.md`. Cero efecto en lo que se pinta.** Lo único que controla el renderizado es `data/analysis_schema.json` (la forma) + `data/analysis.json` (los datos reales).

Pero `ANALYST_GUIDE.md` no compite con el schema — cumple un trabajo distinto: el schema dice **qué campos existen**; la guía dice **cómo se deben llenar bien** esos campos. Ahí ya está documentado, con ejemplos reales de errores que ya pasaron en este proyecto:

- No meter siglas (HHI, NSI, IR, PI, ER) en `narrativa`.
- No mencionar eventos fuera del período (ej. error real: mencionaron el "Club FAS" de un archivo viejo).
- No usar "censura"/"autocensura".
- Engagement ≠ impresiones.
- `enlaces_referencia` completo, no parcial.
- Casos reales de Voces de Influencia con engagement > 0 pero submétricas en 0 (matemáticamente imposible).

Un JSON no puede llevar esas reglas de redacción/consistencia como comentarios (JSON no soporta comentarios), así que si borras la guía, esas reglas simplemente se pierden y alguien (o un LLM) puede repetir los mismos errores que ya se detectaron y corrigieron una vez.

**Mi recomendación:** consérvalo, pero exclusivamente como el "manual de redacción" que acompaña al schema — no como algo que compite con él. El costo de mantenerlo es cero (no rompe nada, no se importa en runtime). Si de verdad prefieres una sola fuente, la única alternativa real es mover esas reglas a comentarios en un archivo `.md` hermano del schema — que es lo mismo que ya tienes, solo con otro nombre.

Si aun así decides eliminarlo, dímelo y te preparo el patch de borrado — pero no tocará el renderizado del dashboard en absoluto (por eso decías que analysis_schema.json es "el archivo real": es correcto para el renderizado, pero no es donde vive el estándar de calidad).

---

## 2) Parche real: `data/analysis_schema.json`

Estos son los campos que **de verdad faltan** dentro de `bloque1` (confirmé contra el código real de `dashboard/app.py`; no invento estructura nueva, solo completo huecos con la misma convención plana que ya usa el archivo).

### 2.1 `metricas_rendimiento` — le faltan 2 campos que `app.py` YA intenta leer (bug latente) + 2 que pide la guía

`app.py` lee `mr.get("reacciones_positivas")` y `mr.get("reacciones_negativas")` (conteos absolutos) pero el schema solo define `reacciones_positivas_pct` / `reacciones_negativas_pct`. Hoy esos números siempre saldrán en 0 aunque el análisis real tenga datos. Además falta `explicacion_simple` y `enlaces_referencia`, que sí tienen las demás secciones del Bloque I.

```jsonc
"metricas_rendimiento": {
  "engagement_rate": 0,
  "engagement_rate_formula": "ER = (reacciones + comentarios + compartidos) / impresiones * 100",
  "alcance_estimado": 0,
  "reacciones_positivas": 0,            // NUEVO — conteo absoluto, ya lo usa app.py
  "reacciones_negativas": 0,            // NUEVO — conteo absoluto, ya lo usa app.py
  "reacciones_positivas_pct": 0,
  "reacciones_negativas_pct": 0,
  "ratio_amor_enojo": 0,
  "ratio_amor_enojo_formula": "R = (likes + loves + cares) / (angrys + sads + hahas)",
  "porque_funciona": "",
  "narrativa": "",
  "explicacion_simple": "",             // NUEVO
  "enlaces_referencia": []              // NUEVO
}
```

### 2.2 `termometro_zonas[]` — cada zona necesita su propia narrativa citable

Hoy cada zona tiene datos (tensión, tema dominante, emoción dominante, citas) pero NINGUNA explicación en prosa ni enlaces — exactamente el hueco que señalaste ("formulas explicadas con números reales, nada inventado, enlaces de referencia").

```jsonc
"termometro_zonas": [
  {
    "zona": "",
    "n_comentarios": 0,
    "pct_apoyo": 0,
    "pct_critica": 0,
    "pct_objecion": 0,
    "pct_neutral": 0,
    "emocion_dominante": "",
    "tema_dominante": "",
    "problema_principal": "",
    "citas_ejemplo": [],
    "nivel_tension": "",
    "score_zona": 0,
    "narrativa": "",              // NUEVO
    "explicacion_simple": "",     // NUEVO
    "enlaces_referencia": []      // NUEVO
  }
]
```

### 2.3 `pulso_iq` — falta el desglose de los componentes que ya usa la fórmula

La fórmula guardada (`formula_usada`) ya menciona 7 componentes (aprobación, conexión, tranquilidad, diversidad, presencia, consistencia, atención) pero el schema nunca guarda sus valores individuales. Sin esto, es imposible que la narrativa diga "el IQ es 62 porque aprobación=70, conexión=55..." con números reales — que es justo lo que pediste.

```jsonc
"pulso_iq": {
  "valor": 0,
  "cuadrante": "",
  "componentes": {                 // NUEVO — mismos nombres que la fórmula
    "aprobacion": 0,
    "conexion": 0,
    "tranquilidad": 0,
    "diversidad": 0,
    "presencia": 0,
    "consistencia": 0,
    "atencion": 0
  },
  "narrativa": "",
  "explicacion_simple": "",        // NUEVO
  "enlaces_referencia": [],        // NUEVO
  "formula_usada": "IQ = (aprobacion*1.0 + conexion*1.0 + tranquilidad*1.0 + diversidad*0.8 + presencia*0.7 + consistencia*0.9 + atencion*0.6) / suma_pesos"
}
```

> Nada de esto toca `indice_emociones` — ese bloque lo dejamos pendiente a propósito (ver sección 4).

---

## 3) Parche real: `dashboard/app.py`

Hoy `app.py` NO renderiza `narrativa` / `explicacion_simple` / `enlaces_referencia` en las secciones 05 y 06 ni en Pulso IQ, aunque sí lo hace en 01/03/04. Aplica estos 3 cambios (usa tu editor o `git apply`/búsqueda-reemplazo exacta; son inserciones puntuales, no reescriben nada existente):

### 3.1 Sección 05 · Métricas de Rendimiento — agrega narrativa + explicación + fórmula + enlaces

Buscar:
```python
    mr = b1.get("metricas_rendimiento", {})
    if mr and any(v for v in [mr.get("engagement_rate"), mr.get("ratio_amor_enojo"), mr.get("alcance_estimado")]):
```
Reemplazar por:
```python
    mr = b1.get("metricas_rendimiento", {})
    if mr and any(v for v in [mr.get("engagement_rate"), mr.get("ratio_amor_enojo"), mr.get("alcance_estimado")]):
        narrativa_mr = mr.get("narrativa", "")
        if narrativa_mr:
            st.markdown(f"""
            <div class="interpretation">
                <div class="interpretation-label">LECTURA EJECUTIVA</div>
                <div class="interpretation-texto">{narrativa_mr}</div>
            </div>
            """, unsafe_allow_html=True)
        _expander_enlaces(mr.get("enlaces_referencia", []))
```

Y al final del bloque `if mr and ...:` (justo después de donde hoy termina con el `if pfunciona:` / antes del `else:`), agrega:
```python
        _card_explicacion_simple(mr.get("explicacion_simple", ""))
        if mr.get("engagement_rate_formula"):
            st.caption(f"Fórmula: {mr.get('engagement_rate_formula')}")
        if mr.get("ratio_amor_enojo_formula"):
            st.caption(f"Fórmula: {mr.get('ratio_amor_enojo_formula')}")
```

### 3.2 Sección 06 · Termómetro de Zonas — narrativa por zona dentro de la misma tarjeta

Buscar (dentro del `for zona in termometro_zonas:`):
```python
            citas_html = "".join(
                f'<div style="font-style:italic;color:var(--fg-secondary);font-size:12px;margin-top:4px">"{c}"</div>'
                for c in zona.get("citas_ejemplo", [])[:2]
            )
```
Agrega justo debajo (antes de construir `_render_card`):
```python
            narrativa_zona = zona.get("narrativa", "")
            narrativa_zona_html = (
                f'<div style="font-size:12px;color:var(--fg-primary);margin-top:8px;line-height:1.6">{narrativa_zona}</div>'
                if narrativa_zona else ""
            )
```
Y dentro del f-string de `_render_card(...)`, agrega `{narrativa_zona_html}` justo después de `{citas_html}`. Después de cerrar el `for zona in termometro_zonas:` (fuera del loop, o dentro por zona si prefieres una por tarjeta), agrega la llamada a enlaces por zona dentro del mismo `for`:
```python
            _expander_enlaces(zona.get("enlaces_referencia", []), label=f"Ver enlaces de {zona.get('zona','esta zona')}")
```

### 3.3 Pulso IQ — mostrar los 7 componentes reales de la fórmula

Buscar:
```python
    iq = b1.get("pulso_iq", {})
    if iq.get("valor") or iq.get("cuadrante"):
        iq_val = iq.get("valor", 0)
        iq_cuad = iq.get("cuadrante", "—")
        iq_narr = iq.get("narrativa", "—")
```
Reemplazar por:
```python
    iq = b1.get("pulso_iq", {})
    if iq.get("valor") or iq.get("cuadrante"):
        iq_val = iq.get("valor", 0)
        iq_cuad = iq.get("cuadrante", "—")
        iq_narr = iq.get("narrativa", "—")
        iq_comp = iq.get("componentes", {})
        chips_iq = "".join(
            f'<span style="font-size:11px;padding:2px 8px;background:var(--bg-elevated);'
            f'border-radius:10px;color:var(--fg-secondary);margin:2px">{k.capitalize()} '
            f'<strong>{v:.0f}</strong></span>'
            for k, v in iq_comp.items() if v
        )
```
Y dentro del bloque `st.markdown(f""" ... """, unsafe_allow_html=True)` que pinta el panel del IQ, agrega `{chips_iq}` justo después del `<div>{iq_narr}</div>` (envuelto en un `<div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:8px;justify-content:center">{chips_iq}</div>`). Luego, después de ese bloque `st.markdown(...)`, agrega:
```python
        _card_explicacion_simple(iq.get("explicacion_simple", ""))
        if iq.get("formula_usada"):
            st.caption(f"Fórmula: {iq.get('formula_usada')}")
        _expander_enlaces(iq.get("enlaces_referencia", []))
```

---

## 4) Pendiente: ampliación de emociones (necesito el archivo original)

Revisé este sandbox y el repo real de GitHub: **`dashboard/tema_taxonomia_expandida.py` no existe en ninguno de los dos** — el sandbox donde lo generé la vez anterior ya se reinició, y como confirmamos en la sección 0, nunca llegó a GitHub. No tengo forma de recuperar ese trabajo "robusto" de emociones que armé antes.

Para no perder nada y no reconstruirlo a ciegas (arriesgando cambiar lo que ya te gustó), por favor:

1. Si todavía tienes el archivo `mejoras_bloque1_pulso_general.zip` que te descargué antes, súbelo de nuevo aquí (o solo `tema_taxonomia_expandida.py`).
2. Con eso, fusiono las emociones nuevas directamente en los 3 lugares que deben estar sincronizados siempre ("regla de oro" de este proyecto, ya usada en PRs anteriores):
   - `data/analysis_schema.json` → `bloque1.indice_emociones` (agregar las claves nuevas + su `pct_<emocion>` correspondiente, en el mismo formato plano).
   - `dashboard/tema_taxonomia.py` → diccionario `EMOCIONES` (+ `EMOCIONES_VALIDAS`, `EMOCION_LABELS`, `_EMOCION_SINONIMOS`).
   - `dashboard/app.py` → lista `_EMO_DEFS` (que es la que de verdad dibuja las barras — si falta ahí, la emoción nunca se ve aunque esté en el JSON).

Sin el archivo original no puedo garantizar que se preserve exactamente lo que revisaste y aprobaste; en cuanto lo tenga, te entrego el patch de estos 3 archivos en el mismo formato de esta guía.
