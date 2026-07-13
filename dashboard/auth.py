"""Autenticacion minima por contrasena compartida para el panel de carga.

No es un sistema multiusuario: es un candado de acceso al panel que
escribe en produccion (C4). El hash se define en .streamlit/secrets.toml
(clave PANEL_PASSWORD_HASH), nunca en codigo ni en el repo.
"""
import bcrypt
import streamlit as st


def _get_hash() -> str | None:
    try:
        return st.secrets.get("PANEL_PASSWORD_HASH")
    except Exception:
        return None


def require_auth() -> bool:
    """Bloquea la ejecucion del resto del script hasta autenticar.

    Devuelve True si ya esta autenticado en esta sesion. Si no hay
    PANEL_PASSWORD_HASH configurado, MUESTRA UN ERROR BLOQUEANTE (nunca
    deja pasar sin contrasena: fail-closed, no fail-open).
    """
    password_hash = _get_hash()
    if not password_hash:
        st.error(
            "PANEL_PASSWORD_HASH no configurado en .streamlit/secrets.toml. "
            "El panel de carga no puede operar sin autenticacion configurada."
        )
        st.stop()

    if st.session_state.get("panel_autenticado"):
        return True

    st.markdown("### Acceso restringido - Panel de carga")
    pwd = st.text_input("Contrasena", type="password", key="panel_login_pwd")
    if st.button("Entrar", key="panel_login_btn"):
        if bcrypt.checkpw(pwd.encode("utf-8"), password_hash.encode("utf-8")):
            st.session_state["panel_autenticado"] = True
            st.rerun()
        else:
            st.error("Contrasena incorrecta.")
    st.stop()
