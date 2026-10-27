"""Módulo de Autenticación, Hashing Seguro y Gestión de Sesiones de Usuario."""

import hashlib
import hmac
import os
import sqlite3
from typing import Optional
import streamlit as st
from core.db import get_connection, init_db


def hash_password(password: str) -> str:
    """Genera un hash seguro utilizando PBKDF2-HMAC-SHA256 con salt aleatorio."""
    salt = os.urandom(16)
    pw_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, 100_000
    )
    return f"{salt.hex()}${pw_hash.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verifica una contraseña contra el hash almacenado en tiempo constante."""
    try:
        salt_hex, hash_hex = stored_hash.split("$")
        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(hash_hex)
        calculated_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, 100_000
        )
        return hmac.compare_digest(calculated_hash, expected_hash)
    except Exception:
        return False


def get_user_count() -> int:
    """Retorna la cantidad de usuarios registrados en el sistema."""
    init_db()
    conn = get_connection()
    row = conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()
    return int(row[0]) if row else 0


def create_user(username: str, password: str, nombre_completo: str, rol: str = "tecnico") -> bool:
    """Registra un nuevo usuario en la base de datos."""
    init_db()
    conn = get_connection()
    pw_hash = hash_password(password)
    with conn:
        conn.execute(
            """
            INSERT INTO usuarios (username, password_hash, nombre_completo, rol, activo)
            VALUES (?, ?, ?, ?, 1)
            """,
            (username.strip().lower(), pw_hash, nombre_completo.strip(), rol.strip().lower()),
        )
    return True


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """Autentica las credenciales ingresadas y retorna el dict de usuario o None."""
    init_db()
    conn = get_connection()
    row = conn.execute(
        "SELECT id, username, password_hash, nombre_completo, rol, activo FROM usuarios WHERE username = ?",
        (username.strip().lower(),),
    ).fetchone()

    if row is None:
        return None

    user = dict(row)
    if not user.get("activo", 1):
        return None

    if verify_password(password, user["password_hash"]):
        return {
            "id": user["id"],
            "username": user["username"],
            "nombre_completo": user["nombre_completo"],
            "rol": user["rol"],
        }
    return None


def get_all_technicians() -> list[str]:
    """Retorna los nombres completos de todos los usuarios registrados activos."""
    init_db()
    conn = get_connection()
    rows = conn.execute(
        "SELECT nombre_completo FROM usuarios WHERE activo = 1 ORDER BY nombre_completo ASC"
    ).fetchall()
    return [r[0] for r in rows] if rows else []


def get_available_technicians() -> list[str]:
    """Retorna una lista unificada de tecnicos registrados y de ordenes existentes."""
    init_db()
    conn = get_connection()
    registered = get_all_technicians()

    try:
        order_rows = conn.execute(
            "SELECT DISTINCT tecnico FROM ordenes WHERE tecnico IS NOT NULL AND tecnico != '' ORDER BY tecnico ASC"
        ).fetchall()
        from_orders = [r[0] for r in order_rows] if order_rows else []
    except Exception:
        from_orders = []

    combined = []
    for t in registered + from_orders:
        if t and t not in combined:
            combined.append(t)

    if not combined:
        from core.config import TECNICOS
        combined = list(TECNICOS)

    return combined


def get_all_users() -> list[dict]:
    """Retorna todos los usuarios registrados para administración."""
    init_db()
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, username, nombre_completo, rol, activo, creado_en FROM usuarios ORDER BY id ASC"
    ).fetchall()
    return [dict(r) for r in rows] if rows else []


def delete_user(user_id: int) -> bool:
    """Elimina o desactiva un usuario."""
    conn = get_connection()
    with conn:
        conn.execute("DELETE FROM usuarios WHERE id = ?", (user_id,))
    return True


def init_session_state() -> None:
    """Inicializa las variables de estado de sesión de autenticación."""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "username" not in st.session_state:
        st.session_state["username"] = ""
    if "tecnico_nombre" not in st.session_state:
        st.session_state["tecnico_nombre"] = ""
    if "user_role" not in st.session_state:
        st.session_state["user_role"] = ""


def logout_user() -> None:
    """Limpia el estado de sesión y cierra la sesión actual."""
    st.session_state["authenticated"] = False
    st.session_state["username"] = ""
    st.session_state["tecnico_nombre"] = ""
    st.session_state["user_role"] = ""
    st.rerun()


def render_login_view() -> None:
    """Renderiza la pantalla de Login o el Registro Inicial si no hay usuarios."""
    init_session_state()
    user_count = get_user_count()

    # Si la base de datos no tiene usuarios, mostramos el Onboarding Inicial
    if user_count == 0:
        render_initial_onboarding()
        return

    # Pantalla de Login / Registro de técnico
    st.markdown(
        """
        <div style="max-width: 440px; margin: 3rem auto 1.5rem auto; text-align: center;">
            <div style="font-size: 2.2rem; font-weight: 800; color: #FFFFFF; letter-spacing: -0.03em;">
                ⚡ LABFIX BI
            </div>
            <div style="color: #9CA3AF; font-size: 0.9rem; margin-top: 0.25rem;">
                Control de Acceso y Gestión de Laboratorio Técnico
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_l, col_center, col_r = st.columns([1, 1.8, 1])
    with col_center:
        with st.container():
            st.markdown(
                """
                <div style="background: #111827; border: 1px solid #1F2937; border-top: 3px solid #00F0FF; padding: 1.5rem; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.4);">
                """,
                unsafe_allow_html=True,
            )

            auth_mode = st.radio(
                "Seleccionar Acción:",
                options=["🔑 Iniciar Sesión", "👤 Registrar nuevo técnico"],
                horizontal=True,
                key="auth_radio_mode",
            )

            st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)

            if auth_mode.startswith("🔑"):
                username_in = st.text_input("Usuario:", placeholder="ej: lucas_tec", key="login_in_username")
                password_in = st.text_input("Contraseña:", type="password", key="login_in_password")

                btn_login = st.button("Ingresar al Laboratorio", type="primary", use_container_width=True, key="login_btn_submit")

                if btn_login:
                    if not username_in.strip() or not password_in.strip():
                        st.error("Por favor completa usuario y contraseña.")
                    else:
                        user = authenticate_user(username_in, password_in)
                        if user:
                            st.session_state["authenticated"] = True
                            st.session_state["username"] = user["username"]
                            st.session_state["tecnico_nombre"] = user["nombre_completo"]
                            st.session_state["user_role"] = user["rol"]
                            st.toast(f"¡Bienvenido, {user['nombre_completo']}!", icon="⚡")
                            st.rerun()
                        else:
                            st.error("Usuario o contraseña incorrectos.")

            else:
                st.markdown("<b style='color: #00F0FF; font-size: 0.88rem;'>Alta de Nuevo Técnico</b>", unsafe_allow_html=True)
                new_nombre = st.text_input("Nombre y Apellido:", placeholder="Ej: Sofía Gómez", key="reg_in_nombre")
                new_user = st.text_input("Nombre de Usuario:", placeholder="Ej: sofia_g", key="reg_in_user")
                new_pass = st.text_input("Contraseña:", type="password", key="reg_in_pass")
                new_pass_confirm = st.text_input("Confirmar Contraseña:", type="password", key="reg_in_pass_conf")
                new_role = st.selectbox("Rol Asignado:", options=["tecnico", "admin"], format_func=lambda r: "Técnico de Laboratorio" if r == "tecnico" else "Administrador / Jefe de Taller", key="reg_sel_rol")

                btn_reg = st.button("Registrar Usuario", type="primary", use_container_width=True, key="reg_btn_submit")

                if btn_reg:
                    if not new_nombre.strip() or not new_user.strip() or not new_pass.strip():
                        st.error("Todos los campos son obligatorios.")
                    elif new_pass != new_pass_confirm:
                        st.error("Las contraseñas no coinciden.")
                    elif len(new_pass) < 4:
                        st.error("La contraseña debe tener al menos 4 caracteres.")
                    else:
                        try:
                            create_user(
                                username=new_user.strip(),
                                password=new_pass,
                                nombre_completo=new_nombre.strip(),
                                rol=new_role,
                            )
                            st.success(f"✅ ¡Usuario {new_user} registrado exitosamente! Ya podés iniciar sesión.")
                        except sqlite3.IntegrityError:
                            st.error("Ese nombre de usuario ya está en uso. Por favor elegí otro.")
                        except Exception as exc:
                            st.error(f"Error al registrar: {exc}")

            st.markdown("</div>", unsafe_allow_html=True)


def render_initial_onboarding() -> None:
    """Pantalla inicial para dar de alta al primer Administrador del sistema."""
    st.markdown(
        """
        <div style="max-width: 500px; margin: 3rem auto 1rem auto; text-align: center;">
            <div style="font-size: 2.2rem; font-weight: 800; color: #FFFFFF;">⚡ LABFIX BI</div>
            <div style="background: rgba(0, 240, 255, 0.12); border: 1px solid #00F0FF; padding: 0.6rem 1rem; border-radius: 8px; margin: 1rem 0; color: #00F0FF; font-size: 0.9rem;">
                <b>🚀 Configuración Inicial:</b> Registrá la cuenta del <b>Administrador Principal</b> para habilitar el sistema.
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

        admin_nombre = st.text_input("Nombre Completo:", value="Administrador Principal", key="onboard_in_nombre")
        admin_user = st.text_input("Nombre de Usuario (Login):", value="admin", key="onboard_in_user")
        admin_pass = st.text_input("Contraseña Maestra:", type="password", key="onboard_in_pass")
        admin_pass_conf = st.text_input("Repetir Contraseña:", type="password", key="onboard_in_pass_conf")

        btn_onboard = st.button("Crear Cuenta Administrador y Comenzar", type="primary", use_container_width=True, key="onboard_btn_submit")

        if btn_onboard:
            if not admin_user.strip() or not admin_pass.strip():
                st.error("Por favor completa todos los campos.")
            elif admin_pass != admin_pass_conf:
                st.error("Las contraseñas no coinciden.")
            else:
                create_user(
                    username=admin_user.strip(),
                    password=admin_pass,
                    nombre_completo=admin_nombre.strip(),
                    rol="admin",
                )
                # Iniciar sesión automáticamente
                st.session_state["authenticated"] = True
                st.session_state["username"] = admin_user.strip().lower()
                st.session_state["tecnico_nombre"] = admin_nombre.strip()
                st.session_state["user_role"] = "admin"
                st.toast("¡Administrador creado con éxito!", icon="⚡")
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

