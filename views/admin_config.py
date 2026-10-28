"""Módulo 5.1: Configuración Institucional, Parámetros del Taller, 2FA y Mantenimiento (ERP LABFIX)."""

from typing import Any, Dict
import streamlit as st
from auth import (
    disable_2fa_for_user,
    enable_2fa_for_user,
    generate_backup_codes,
    generate_totp_secret,
    get_connection,
    get_totp_uri,
    verify_totp_code,
)
from components.cards import empty_state, format_currency, metric_card
from core.config import ALICUOTAS_IVA
from database import get_workshop_config, log_audit, purge_all_tables, update_workshop_config


def render_config_view() -> None:
    """Renderiza el panel de configuración del taller, parámetros fiscales, seguridad 2FA y mantenimiento."""
    user = st.session_state.get("username", "admin")
    user_id = st.session_state.get("user_id", 1)
    user_role = str(st.session_state.get("user_role", "admin")).upper()

    st.markdown(
        """
        <div style="margin-bottom: 1.25rem;">
            <h2 style="color: #FFFFFF; font-weight: 800; margin: 0; font-size: 1.6rem; letter-spacing: -0.02em;">
                ⚙️ Configuración del Taller & Parámetros Generales
            </h2>
            <span style="color: #9CA3AF; font-size: 0.85rem;">
                Datos fiscales, alícuotas de IVA, seguridad 2FA, políticas de garantía y mantenimiento
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if user_role != "ADMIN":
        st.error("⛔ Acceso restringido. Solo los usuarios con rol de Administrador pueden modificar la configuración general.")
        return

    config = get_workshop_config()
    conn = get_connection()

    t_datos, t_2fa, t_legal, t_maint = st.tabs([
        "🏢 Datos Fiscales y Organización",
        "🔐 Seguridad & 2FA (Authy / Authenticator)",
        "📜 Términos de Garantía Legal",
        "⚠️ Mantenimiento y Reset",
    ])

    # =========================================================================
    # TAB 1: DATOS FISCALES & ORGANIZACIÓN
    # =========================================================================
    with t_datos:
        with st.form(key="form_config_taller"):
            c1, c2 = st.columns(2)
            with c1:
                nom = st.text_input("Nombre de Fantasía del Taller *", value=config.get("nombre", config.get("nombre_taller", "")), key="cfg_nom_in")
                cuit = st.text_input("CUIT / Identificación Tributaria", value=config.get("cuit_rut", config.get("cuit", "")), key="cfg_cuit_in")
                pais = st.text_input("País de Operación", value=config.get("pais", "Argentina"), key="cfg_pais_in")
                moneda = st.selectbox("Moneda Principal de Gestión", ["ARS", "USD", "EUR", "CLP", "UYU", "BRL"], index=0, key="cfg_moneda_in")
                tel = st.text_input("Teléfono / WhatsApp de Atención", value=config.get("telefono", ""), key="cfg_tel_in")

            with c2:
                em = st.text_input("Email de Contacto", value=config.get("email", ""), key="cfg_em_in")
                dir_t = st.text_input("Dirección del Laboratorio / Local", value=config.get("direccion", ""), key="cfg_dir_in")
                
                # Alícuota por defecto
                current_iva = float(config.get("alicuota_iva_defecto", 21.0))
                iva_idx = ALICUOTAS_IVA.index(current_iva) if current_iva in ALICUOTAS_IVA else 2
                alicuota_iva = st.selectbox("Alícuota de IVA por Defecto (%)", ALICUOTAS_IVA, index=iva_idx, key="cfg_iva_in")
                
                # Autoasignación de técnicos
                auto_asig = st.checkbox(
                    "Permitir Autoasignación de Órdenes a Técnicos",
                    value=bool(config.get("autoasignacion_tecnicos", 1)),
                    help="Si está activo, los técnicos pueden tomar órdenes de trabajo no asignadas desde su mesa de trabajo.",
                    key="cfg_auto_asig_in",
                )

            submit_cfg = st.form_submit_button("💾 Guardar Parámetros de la Organización", use_container_width=True)
            if submit_cfg:
                data_update = {
                    "nombre": nom.strip(),
                    "cuit_rut": cuit.strip(),
                    "pais": pais.strip(),
                    "moneda_principal": moneda,
                    "alicuota_iva_defecto": alicuota_iva,
                    "autoasignacion_tecnicos": 1 if auto_asig else 0,
                    "telefono": tel.strip(),
                    "email": em.strip(),
                    "direccion": dir_t.strip(),
                }
                update_workshop_config(data_update)
                log_audit(user, "taller_config", "1", "ACTUALIZAR_CONFIG", "Actualización de datos institucionales y RLS")
                st.toast("✅ Configuración guardada exitosamente", icon="⚙️")
                st.rerun()

    # =========================================================================
    # TAB 2: SEGURIDAD & AUTENTICACIÓN EN DOS PASOS (2FA)
    # =========================================================================
    with t_2fa:
        st.markdown("<b style='color: #00F0FF; font-size: 1.05rem;'>Autenticación en Dos Pasos (TOTP - RFC 6238)</b>", unsafe_allow_html=True)
        st.markdown(
            "<span style='color: #9CA3AF; font-size: 0.85rem; display: block; margin-bottom: 1rem;'>"
            "Protege el acceso a tu cuenta mediante un generador de códigos en tu dispositivo móvil (Google Authenticator, Authy, Microsoft Authenticator o 1Password)."
            "</span>",
            unsafe_allow_html=True,
        )

        row_user = conn.execute("SELECT id, username, totp_enabled, totp_secret, backup_codes_json FROM usuarios WHERE id = ?", (user_id,)).fetchone()
        totp_active = bool(row_user["totp_enabled"]) if row_user else False

        if totp_active:
            st.markdown(
                """
                <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); padding: 14px; border-radius: 8px; margin-bottom: 1rem;">
                    <div style="color: #10B981; font-weight: 700; font-size: 1rem;">🛡️ Autenticación 2FA Activada</div>
                    <div style="color: #D1D5DB; font-size: 0.85rem; margin-top: 4px;">
                        Tu cuenta está protegida. Al iniciar sesión se requerirá el código dinámico de 6 dígitos de tu aplicación de autenticación.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if st.button("❌ Desactivar Autenticación en 2 Pasos (2FA)", key="btn_disable_2fa", type="secondary"):
                disable_2fa_for_user(user_id)
                log_audit(user, "usuarios", str(user_id), "DISABLE_2FA", "2FA desactivado por el usuario")
                st.toast("2FA desactivado correctamente.", icon="ℹ️")
                st.rerun()

        else:
            st.markdown(
                """
                <div style="background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); padding: 12px; border-radius: 8px; margin-bottom: 1rem;">
                    <span style="color: #F59E0B; font-weight: 600; font-size: 0.9rem;">⚠️ 2FA Desactivado</span>:
                    <span style="color: #D1D5DB; font-size: 0.85rem;">Te recomendamos activar 2FA para resguardar la caja y datos de clientes.</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if "setup_2fa_secret" not in st.session_state:
                if st.button("🚀 Comenzar Configuración de 2FA", key="btn_start_2fa", use_container_width=True):
                    secret = generate_totp_secret()
                    plain_codes, hashed_codes = generate_backup_codes(8)
                    st.session_state["setup_2fa_secret"] = secret
                    st.session_state["setup_2fa_plain_codes"] = plain_codes
                    st.session_state["setup_2fa_hashed_codes"] = hashed_codes
                    st.rerun()
            else:
                secret = st.session_state["setup_2fa_secret"]
                plain_codes = st.session_state["setup_2fa_plain_codes"]
                hashed_codes = st.session_state["setup_2fa_hashed_codes"]
                otp_uri = get_totp_uri(secret, username=user, issuer="LABFIX")

                c_qr, c_verify = st.columns([1, 1])

                with c_qr:
                    st.markdown("<b style='color: #E5E7EB; font-size: 0.9rem;'>Paso 1: Vincular App</b>", unsafe_allow_html=True)
                    st.markdown("<span style='color: #9CA3AF; font-size: 0.8rem;'>Ingresa la siguiente clave secreta manualmente en tu aplicación de autenticación:</span>", unsafe_allow_html=True)
                    st.code(secret, language="text")
                    st.markdown(f"<span style='color: #6B7280; font-size: 0.75rem;'>URI: <code style='font-size: 0.7rem;'>{otp_uri}</code></span>", unsafe_allow_html=True)

                    st.markdown("<b style='color: #F59E0B; font-size: 0.9rem; margin-top: 1rem; display: block;'>Paso 2: Guarda tus Códigos de Respaldo</b>", unsafe_allow_html=True)
                    st.markdown("<span style='color: #9CA3AF; font-size: 0.78rem;'>Si pierdes acceso a tu teléfono, podrás usar cada uno de estos códigos una única vez:</span>", unsafe_allow_html=True)
                    codes_str = "  |  ".join(plain_codes)
                    st.code(codes_str, language="text")

                with c_verify:
                    st.markdown("<b style='color: #E5E7EB; font-size: 0.9rem;'>Paso 3: Verificar y Confirmar</b>", unsafe_allow_html=True)
                    st.markdown("<span style='color: #9CA3AF; font-size: 0.8rem;'>Introduce el código de 6 dígitos que muestra tu app para confirmar el enlace:</span>", unsafe_allow_html=True)
                    test_code = st.text_input("Código de Verificación (6 dígitos)", max_chars=6, key="input_test_totp")

                    c_act, c_can = st.columns(2)
                    with c_act:
                        if st.button("✅ Activar 2FA Ahora", key="btn_confirm_enable_2fa", use_container_width=True):
                            if verify_totp_code(secret, test_code):
                                enable_2fa_for_user(user_id, secret, hashed_codes)
                                log_audit(user, "usuarios", str(user_id), "ENABLE_2FA", "2FA activado con éxito")
                                del st.session_state["setup_2fa_secret"]
                                del st.session_state["setup_2fa_plain_codes"]
                                del st.session_state["setup_2fa_hashed_codes"]
                                st.success("¡Autenticación en Dos Pasos activada con éxito!")
                                st.rerun()
                            else:
                                st.error("❌ Código incorrecto o expirado. Asegúrate de que la hora de tu teléfono esté sincronizada.")
                    with c_can:
                        if st.button("Cancelar", key="btn_cancel_2fa", use_container_width=True):
                            del st.session_state["setup_2fa_secret"]
                            del st.session_state["setup_2fa_plain_codes"]
                            del st.session_state["setup_2fa_hashed_codes"]
                            st.rerun()

    # =========================================================================
    # TAB 3: TÉRMINOS LEGALES DE GARANTÍA
    # =========================================================================
    with t_legal:
        with st.form(key="form_config_legal"):
            st.markdown("<span style='color: #9CA3AF; font-size: 0.85rem;'>Este texto aparecerá al pie de cada <b>Remito de Entrega Oficial</b> y en el comprobante firmado por el cliente:</span>", unsafe_allow_html=True)
            term_val = st.text_area(
                "Cláusulas Legales de Garantía:",
                value=config.get("terminos_legales", ""),
                height=180,
                key="cfg_term_in",
            )
            submit_legal = st.form_submit_button("💾 Guardar Cláusulas Legales", use_container_width=True)
            if submit_legal:
                data_update = {"terminos_legales": term_val.strip()}
                update_workshop_config(data_update)
                log_audit(user, "taller_config", "1", "ACTUALIZAR_LEGAL", "Actualización de términos legales de garantía")
                st.toast("✅ Cláusulas legales actualizadas", icon="📜")
                st.rerun()

    # =========================================================================
    # TAB 4: MANTENIMIENTO Y PURGADO
    # =========================================================================
    with t_maint:
        st.markdown(
            """
            <div style="background: rgba(244, 63, 94, 0.1); border: 1px solid rgba(244, 63, 94, 0.4); padding: 18px; border-radius: 8px;">
                <h4 style="color: #F43F5E; margin: 0 0 8px 0;">Zona Crítica: Purgado de Base de Datos (Clean Reset)</h4>
                <p style="color: #E5E7EB; font-size: 0.85rem; margin: 0 0 12px 0;">
                    Esta acción vacía todas las órdenes de trabajo, ventas, caja, stock y comprobantes, dejando el sistema en cero absoluto sin alterar las cuentas de usuario ni contraseñas.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.write("")
        confirm_purge = st.checkbox("Confirmo que deseo purgar todas las transacciones operativas del ERP", key="chk_confirm_purge")
        if st.button("🔥 Reiniciar Base de Datos a Cero", type="secondary", disabled=not confirm_purge, key="btn_do_purge"):
            purge_all_tables(keep_users=True)
            log_audit(user, "sistema", "database", "PURGA_DATOS", "Reinicio de base de datos a cero (conservando usuarios)")
            st.toast("✅ Base de datos reiniciada a cero", icon="🔥")
            st.rerun()
