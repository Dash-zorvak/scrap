# Despliegue — Dashboard en línea con la base de datos en local

Esta guía deja el **dashboard del alcalde** accesible desde internet con una
URL propia y **login por correo**, mientras la **base de datos nunca sale de tu
Mac**. El **panel de carga** del analista corre solo en local.

> Modelo "on-demand": el dashboard está en línea **mientras tu Mac esté
> encendida y el script corriendo**. Si la apagas, la URL deja de responder
> (los datos siguen seguros en local).

---

## 1. Arquitectura en una imagen

```
  Alcalde (navegador)
        │  https://dashboard.tudominio.com  (login por correo)
        ▼
  Cloudflare Access  ────────────┐  (solo correos autorizados)
        │                              │
  Cloudflare Tunnel (cloudflared)      │
        │  (conexión saliente, sin abrir puertos)
        ▼
  Tu Mac:  Streamlit  http://localhost:8501  (dashboard/app.py)
        └─ lee la DB LOCAL (config.py)  ← nunca se sube

  Panel de carga (solo tú):  http://localhost:8502  (dashboard/panel_carga.py)
        └─ NO pasa por el túnel, se queda en tu Mac
```

- **Dashboard del alcalde** → puerto **8501** → expuesto por el túnel.
- **Panel de carga** → puerto **8502** → **solo localhost**, jamás se expone.
- **DB** → archivos locales leídos por `config.py`. No se sube a ningún lado.

---

## 2. Requisitos (una sola vez)

### 2.1 Instalar cloudflared

```bash
brew install cloudflared
```

(Si no tienes Homebrew: https://brew.sh)

### 2.2 Tener un dominio en Cloudflare (plan gratis sirve)

El login por correo (Cloudflare Access) necesita un dominio gestionado por
Cloudflare. Si ya tienes uno, agrégalo en https://dash.cloudflare.com y apunta
sus nameservers a Cloudflare. Un dominio económico (.com / .app) basta; lo
único que usaremos es un subdominio, p. ej. `dashboard.tudominio.com`.

> ¿Solo quieres una prueba rápida sin dominio ni login? Mira el **Anexo A**
> (URL temporal). Para el alcalde usa el método con dominio + login.

---

## 3. Crear el túnel (una sola vez)

```bash
# 1. Autenticar cloudflared con tu cuenta (abre el navegador y eliges el dominio)
cloudflared tunnel login

# 2. Crear el túnel (genera un ID y un archivo de credenciales .json)
cloudflared tunnel create santaana-dashboard

# 3. Apuntar el subdominio al túnel
cloudflared tunnel route dns santaana-dashboard dashboard.tudominio.com
```

Luego crea el archivo de configuración `~/.cloudflared/config.yml` con este
contenido (reemplaza `TU-TUNNEL-ID`, `TU-USUARIO` y el dominio):

```yaml
tunnel: TU-TUNNEL-ID
credentials-file: /Users/TU-USUARIO/.cloudflared/TU-TUNNEL-ID.json

ingress:
  - hostname: dashboard.tudominio.com
    service: http://localhost:8501
  - service: http_status:404
```

> El `TU-TUNNEL-ID` lo imprime el paso 2; también aparece como nombre del
> archivo `.json` dentro de `~/.cloudflared/`.

---

## 4. Activar el login por correo (Cloudflare Access)

1. Entra a **Cloudflare Zero Trust**: https://one.dash.cloudflare.com
2. **Access → Applications → Add an application → Self-hosted**.
3. **Application domain**: `dashboard.tudominio.com`.
4. Crea una **Policy**:
   - Action: **Allow**
   - Include → **Emails** → agrega el correo del **alcalde** y el **tuyo**.
5. Método de login: deja activo **One-time PIN** (Cloudflare envía un código
   al correo; no requiere que el alcalde cree cuenta).

Resultado: cualquiera que abra la URL debe poner su correo y el código que
recibe. Solo los correos de la lista entran.

---

## 5. Arranque diario (con los scripts)

Da permisos de ejecución una sola vez:

```bash
chmod +x run_dashboard.sh run_panel.sh
```

### Dashboard del alcalde (en línea)

```bash
./run_dashboard.sh
```

Esto levanta Streamlit en el puerto 8501 y enciende el túnel. La URL
`https://dashboard.tudominio.com` queda activa **mientras el script corra**.
Para apagarlo: `Ctrl + C` (cierra el túnel y el dashboard).

### Panel de carga (solo tú, local)

```bash
./run_panel.sh
```

Abre `http://localhost:8502` solo en tu Mac. Aquí subes el contenido; **no se
expone por el túnel**.

---

## 6. Notas importantes

- **La DB siempre en local.** Las apps leen los archivos definidos en
  `config.py`. No subas los `.db` a ningún servicio.
- **On-demand.** El dashboard responde solo con tu Mac encendida y
  `run_dashboard.sh` corriendo. Para tenerlo 24/7 necesitarías una máquina
  siempre encendida (un mini-PC o Raspberry con la DB local + el mismo túnel).
- **Seguridad.** El panel de carga nunca se enruta en `config.yml`, así que no
  es alcanzable desde internet aunque alguien tenga la URL del dashboard.

---

## Anexo A — Prueba rápida sin dominio (sin login)

Solo para que veas el dashboard en línea unos minutos. **No tiene login**, así
que cualquiera con el enlace entra: úsalo solo para pruebas, no para el alcalde.

```bash
streamlit run dashboard/app.py --server.port 8501 --server.headless true &
cloudflared tunnel --url http://localhost:8501
```

Cloudflare imprime una URL `https://....trycloudflare.com` temporal.
