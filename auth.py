"""Módulo de Autenticación, Hashing Seguro (PBKDF2), RBAC Estricto y 2FA TOTP (ERP LABFIX)."""

import hashlib
import hmac
import json
import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple
import streamlit as st
from core.totp import (
    generate_backup_codes,
    generate_totp_secret,
    get_totp_uri,
    verify_and_consume_backup_code,
    verify_totp_code,
)
from database import get_connection, init_db, log_audit


def hash_password(password: str) -> str:
    """Genera un hash criptográfico PBKDF2-HMAC-SHA256 con salt de 16 bytes y 100.000 rondas."""
    salt = os.urandom(16)
    pw_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return f"{salt.hex()}${pw_hash.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Comprueba la contraseña contra el hash de manera segura contra ataques de temporización."""
    try:
        salt_hex, hash_hex = stored_hash.split("$")
        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(hash_hex)
        calculated_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
        return hmac.compare_digest(calculated_hash, expected_hash)
    except Exception:
        return False


def get_user_count(org_id: int = 1) -> int:
    """Retorna la cantidad total de usuarios registrados en la organización."""
    init_db()
    conn = get_connection()
    row = conn.execute("SELECT COUNT(*) FROM usuarios WHERE organizacion_id = ?", (org_id,)).fetchone()
    return int(row[0]) if row else 0


def create_user(
    username: str,
    password: str,
    nombre: str,
    rol: str = "TECNICO",
    comision_pct: float = 0.0,
    org_id: int = 1,
) -> bool:
    """Inserta un nuevo usuario con rol normalizado (ADMIN, TECNICO, VENDEDOR)."""
    init_db()
    conn = get_connection()
    pw_hash = hash_password(password)
    rol_clean = rol.strip().upper()
    if rol_clean not in ["ADMIN", "TECNICO", "VENDEDOR"]:
        rol_clean = "TECNICO"

    with conn:
        conn.execute(
            """
            INSERT INTO usuarios (organizacion_id, username, password_hash, nombre, rol, comision_pct, activo)
            VALUES (?, ?, ?, ?, ?, ?, 1)
            """,
            (org_id, username.strip().lower(), pw_hash, nombre.strip(), rol_clean, float(comision_pct)),
        )
    return True


def authenticate_user(username: str, password: str, org_id: int = 1) -> Optional[Dict[str, Any]]:
    """Comprueba credenciales básicas en la base de datos."""
    init_db()
    conn = get_connection()
    row = conn.execute(
        """
        SELECT id, organizacion_id, username, password_hash, nombre, rol, comision_pct,
               totp_secret, totp_enabled, backup_codes_json, activo
        FROM usuarios
        WHERE username = ? AND organizacion_id = ?
        """,
        (username.strip().lower(), org_id),
    ).fetchone()

    if row is None:
        return None

    user = dict(row)
    if not user.get("activo", 1):
        return None

    if verify_password(password, user["password_hash"]):
        return {
            "id": user["id"],
            "organizacion_id": user["organizacion_id"],
            "username": user["username"],
            "nombre": user["nombre"],
            "rol": user["rol"].upper(),
            "comision_pct": user["comision_pct"],
            "totp_enabled": bool(user["totp_enabled"]),
            "totp_secret": user["totp_secret"],
            "backup_codes_json": user["backup_codes_json"],
        }
    return None


def enable_2fa_for_user(user_id: int, secret: str, hashed_backup_codes: List[str]) -> bool:
    """Habilita la autenticación en dos pasos (TOTP) guardando secreto y hashes de respaldo."""
    conn = get_connection()
    with conn:
        conn.execute(
            """
            UPDATE usuarios SET
                totp_secret = ?, totp_enabled = 1, backup_codes_json = ?
            WHERE id = ?
            """,
            (secret.strip(), json.dumps(hashed_backup_codes), user_id),
        )
    return True


def disable_2fa_for_user(user_id: int) -> bool:
    """Desactiva 2FA para el usuario."""
    conn = get_connection()
    with conn:
        conn.execute(
            "UPDATE usuarios SET totp_secret = '', totp_enabled = 0, backup_codes_json = '[]' WHERE id = ?",
            (user_id,),
        )
    return True


def update_consumed_backup_codes(user_id: int, remaining_hashes: List[str]) -> None:
    """Actualiza la lista de códigos de respaldo tras consumir uno."""
    conn = get_connection()
    with conn:
        conn.execute(
            "UPDATE usuarios SET backup_codes_json = ? WHERE id = ?",
            (json.dumps(remaining_hashes), user_id),
        )


def get_all_users(org_id: int = 1) -> List[Dict[str, Any]]:
    """Retorna lista de todos los usuarios de la organización."""
    init_db()
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, username, nombre, rol, comision_pct, totp_enabled, activo, creado_en FROM usuarios WHERE organizacion_id = ? ORDER BY id ASC",
        (org_id,),
    ).fetchall()
    return [dict(r) for r in rows] if rows else []


def get_all_technicians(org_id: int = 1) -> List[Dict[str, Any]]:
    """Retorna usuarios técnicos o admin activos."""
    init_db()
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, nombre, comision_pct FROM usuarios WHERE organizacion_id = ? AND rol IN ('TECNICO', 'ADMIN') AND activo = 1 ORDER BY nombre ASC",
        (org_id,),
    ).fetchall()
    return [dict(r) for r in rows] if rows else []


def get_all_salespeople(org_id: int = 1) -> List[Dict[str, Any]]:
    """Retorna usuarios de mostrador o admin activos."""
    init_db()
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, nombre, comision_pct FROM usuarios WHERE organizacion_id = ? AND rol IN ('VENDEDOR', 'ADMIN') AND activo = 1 ORDER BY nombre ASC",
        (org_id,),
    ).fetchall()
    return [dict(r) for r in rows] if rows else []


def init_session_state() -> None:
    """Inicializa variables de sesión globales de seguridad y navegación."""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "user_id" not in st.session_state:
        st.session_state["user_id"] = None
    if "username" not in st.session_state:
        st.session_state["username"] = ""
    if "tecnico_nombre" not in st.session_state:
        st.session_state["tecnico_nombre"] = ""
    if "user_role" not in st.session_state:
        st.session_state["user_role"] = ""
    if "organizacion_id" not in st.session_state:
        st.session_state["organizacion_id"] = 1
    if "active_nav_key" not in st.session_state:
        st.session_state["active_nav_key"] = "oper_dashboard"
    if "2fa_pending_user" not in st.session_state:
        st.session_state["2fa_pending_user"] = None


def logout_user() -> None:
    """Cierra la sesión activa de forma segura."""
    st.session_state["authenticated"] = False
    st.session_state["user_id"] = None
    st.session_state["username"] = ""
    st.session_state["tecnico_nombre"] = ""
    st.session_state["user_role"] = ""
    st.session_state["2fa_pending_user"] = None
    st.rerun()


def _login_success(user: Dict[str, Any]) -> None:
    """Establece la sesión iniciada."""
    st.session_state["authenticated"] = True
    st.session_state["user_id"] = user["id"]
    st.session_state["username"] = user["username"]
    st.session_state["tecnico_nombre"] = user["nombre"]
    st.session_state["user_role"] = user["rol"].upper()
    st.session_state["organizacion_id"] = user.get("organizacion_id", 1)
    st.session_state["2fa_pending_user"] = None

    # Redirección por rol
    rol = user["rol"].upper()
    if rol == "TECNICO":
        st.session_state["active_nav_key"] = "oper_tecnicos"
    elif rol == "VENDEDOR":
        st.session_state["active_nav_key"] = "com_pos"
    else:
        st.session_state["active_nav_key"] = "oper_dashboard"

    log_audit(user["username"], "usuarios", str(user["id"]), "LOGIN_EXITOSO", f"Sesión iniciada con rol {rol}", org_id=user.get("organizacion_id", 1))
    st.toast(f"¡Bienvenido, {user['nombre']}!", icon="⚡")
    st.rerun()


def render_login_view() -> None:
    """Pantalla de Login, Verificación 2FA y Onboarding Inicial."""
    init_session_state()
    user_count = get_user_count(org_id=1)

    if user_count == 0:
        render_initial_onboarding()
        return

    st.markdown(
        """
        <div style="max-width: 440px; margin: 3rem auto 1.5rem auto; text-align: center;">
            <div style="font-size: 2.2rem; font-weight: 800; color: #FFFFFF; letter-spacing: -0.03em;">
                ⚡ LABFIX ERP
            </div>
            <div style="color: #9CA3AF; font-size: 0.9rem; margin-top: 0.25rem;">
                Sistema Integral de Gestión de Taller, Punto de Venta & Finanzas
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_l, col_center, col_r = st.columns([1, 1.8, 1])
    with col_center:
        st.markdown(
            """
            <div style="background: #111827; border: 1px solid #1F2937; border-top: 3px solid #00F0FF; padding: 1.5rem; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.4);">
            """,
            unsafe_allow_html=True,
        )

        # Si el usuario pasó contraseña y requiere 2FA
        if st.session_state["2fa_pending_user"]:
            u_pend = st.session_state["2fa_pending_user"]
            st.markdown(
                f"""
                <div style="text-align: center; margin-bottom: 1rem;">
                    <div style="font-size: 1.1rem; font-weight: bold; color: #00F0FF;">🔐 Verificación en Dos Pasos (2FA)</div>
                    <span style="font-size: 0.8rem; color: #9CA3AF;">Usuario: <b>@{u_pend['username']}</b></span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            code_in = st.text_input("Código de 6 dígitos o Código de Respaldo:", placeholder="123456 o XXXX-XXXX", key="auth_2fa_code_input")

            c_sub, c_can = st.columns([2, 1])
            with c_sub:
                if st.button("Verificar y Entrar", type="primary", use_container_width=True, key="auth_btn_verify_2fa"):
                    # 1. Probar como TOTP
                    secret = u_pend.get("totp_secret", "")
                    if verify_totp_code(secret, code_in):
                        _login_success(u_pend)
                    else:
                        # 2. Probar como código de respaldo
                        try:
                            backup_hashes = json.loads(u_pend.get("backup_codes_json", "[]"))
                        except Exception:
                            backup_hashes = []
                        ok_b, rem = verify_and_consume_backup_code(code_in, backup_hashes)
                        if ok_b:
                            update_consumed_backup_codes(u_pend["id"], rem)
                            st.toast("⚠️ Código de respaldo utilizado con éxito", icon="🔑")
                            _login_success(u_pend)
                        else:
                            st.error("Código 2FA o de respaldo inválido.")

            with c_can:
                if st.button("Cancelar", use_container_width=True, key="auth_btn_cancel_2fa"):
                    st.session_state["2fa_pending_user"] = None
                    st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)
            return

        # Login Normal / Alta
        auth_mode = st.radio("Acción:", options=["🔑 Iniciar Sesión", "👤 Registrar personal"], horizontal=True, key="auth_radio_mode")
        st.markdown("<div style='margin-top: 0.75rem;'></div>", unsafe_allow_html=True)

        if auth_mode.startswith("🔑"):
            u_in = st.text_input("Usuario:", placeholder="ej: admin / lucas_tec", key="login_in_user")
            p_in = st.text_input("Contraseña:", type="password", key="login_in_pass")

            if st.button("Ingresar al Sistema", type="primary", use_container_width=True, key="login_btn_submit"):
                if not u_in.strip() or not p_in.strip():
                    st.error("Completá usuario y contraseña.")
                else:
                    user = authenticate_user(u_in, p_in)
                    if user:
                        if user["totp_enabled"]:
                            st.session_state["2fa_pending_user"] = user
                            st.rerun()
                        else:
                            _login_success(user)
                    else:
                        st.error("Credenciales inválidas.")

        else:
            st.markdown("<b style='color: #00F0FF;'>Alta de Nuevo Personal</b>", unsafe_allow_html=True)
            n_name = st.text_input("Nombre y Apellido:", placeholder="Ej: Sofía Gómez", key="reg_name")
            n_user = st.text_input("Usuario:", placeholder="Ej: sofia_g", key="reg_user")
            n_pass = st.text_input("Contraseña:", type="password", key="reg_pass")
            n_pass_c = st.text_input("Confirmar Contraseña:", type="password", key="reg_pass_c")
            col_r1, col_r2 = st.columns([1.5, 1])
            with col_r1:
                n_rol = st.selectbox(
                    "Rol en el Taller:",
                    options=["TECNICO", "VENDEDOR", "ADMIN"],
                    format_func=lambda r: "🔬 Técnico de Laboratorio" if r == "TECNICO" else ("💳 Mostrador / Comercial" if r == "VENDEDOR" else "👑 Administrador General"),
                    key="reg_rol",
                )
            with col_r2:
                n_com = st.number_input("% Comisión:", min_value=0.0, max_value=50.0, value=5.0, step=0.5, key="reg_com")

            if st.button("Registrar Usuario", type="primary", use_container_width=True, key="reg_submit"):
                if not n_name.strip() or not n_user.strip() or not n_pass.strip():
                    st.error("Completá todos los campos.")
                elif n_pass != n_pass_c:
                    st.error("Las contraseñas no coinciden.")
                else:
                    try:
                        create_user(n_user, n_pass, n_name, n_rol, n_com, org_id=1)
                        st.success(f"¡Usuario '{n_user}' ({n_rol}) registrado con éxito! Ya podés iniciar sesión.")
                    except sqlite3.IntegrityError:
                        st.error("El nombre de usuario ya existe.")
                    except Exception as exc:
                        st.error(f"Error: {exc}")

        st.markdown("</div>", unsafe_allow_html=True)


def render_initial_onboarding() -> None:
    """Pantalla inicial de registro del Administrador cuando la base está vacía."""
    st.markdown(
        """
        <div style="max-width: 500px; margin: 3rem auto 1rem auto; text-align: center;">
            <div style="font-size: 2.2rem; font-weight: 800; color: #FFFFFF;">⚡ LABFIX ERP</div>
            <div style="background: rgba(0, 240, 255, 0.12); border: 1px solid #00F0FF; padding: 0.6rem 1rem; border-radius: 8px; margin: 1rem 0; color: #00F0FF; font-size: 0.9rem;">
                <b>🚀 Configuración Inicial:</b> Registrá la cuenta del <b>Administrador Principal</b> para habilitar el ERP.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_l, col_center, col_r = st.columns([1, 1.8, 1])
    with col_center:
        st.markdown(
            """
            <div style="background: #111827; border: 1px solid #1F2937; border-top: 3px solid #10B981; padding: 1.5rem; border-radius: 12px;">
            """,
            unsafe_allow_html=True,
        )

        admin_nombre = st.text_input("Nombre Completo:", value="Administrador General", key="onboard_in_nombre")
        admin_user = st.text_input("Nombre de Usuario (Login):", value="admin", key="onboard_in_user")
        admin_pass = st.text_input("Contraseña Maestra:", type="password", key="onboard_in_pass")
        admin_pass_conf = st.text_input("Repetir Contraseña:", type="password", key="onboard_in_pass_conf")

        btn_onboard = st.button("Crear Administrador y Arrancar ERP", type="primary", use_container_width=True, key="onboard_btn_submit")

        if btn_onboard:
            if not admin_user.strip() or not admin_pass.strip():
                st.error("Completá todos los campos.")
            elif admin_pass != admin_pass_conf:
                st.error("Las contraseñas no coinciden.")
            else:
                create_user(admin_user, admin_pass, admin_nombre, "ADMIN", 0.0, org_id=1)
                user = authenticate_user(admin_user, admin_pass, org_id=1)
                if user:
                    _login_success(user)

        st.markdown("</div>", unsafe_allow_html=True)
