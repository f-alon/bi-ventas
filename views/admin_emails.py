"""Módulo 5.2: Automatización de Notificaciones por Email y Configuración SMTP (ERP LABFIX)."""

from typing import Any, Dict
import streamlit as st
from components.cards import empty_state, metric_card
from database import get_workshop_config, log_audit, update_workshop_config


def render_emails_view() -> None:
    """Renderiza el configurador de servidor SMTP y plantillas de correo automatizadas para clientes."""
    user = st.session_state.get("username", "admin")
    user_role = st.session_state.get("user_role", "admin")

    st.markdown(
        """
        <div style="margin-bottom: 1.25rem;">
            <h2 style="color: #FFFFFF; font-weight: 800; margin: 0; font-size: 1.6rem; letter-spacing: -0.02em;">
                📧 Automatización de Emails & Servidor SMTP
            </h2>
            <span style="color: #9CA3AF; font-size: 0.85rem;">
                Notificación automática del estado de reparación por correo electrónico a los clientes
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if user_role != "admin":
        st.error("⛔ Acceso restringido a Administradores.")
        return

    config = get_workshop_config()

    t_smtp, t_tpl = st.tabs(["🔌 Configuración de Servidor SMTP", "📝 Plantillas Automatizadas por Estado"])

    with t_smtp:
        st.markdown("<b style='color: #00F0FF; font-size: 1rem;'>Credenciales de Salida SMTP</b>", unsafe_allow_html=True)
        with st.form(key="form_smtp_cfg"):
            c1, c2 = st.columns(2)
            with c1:
                host = st.text_input("Servidor SMTP (Host):", value=config.get("smtp_host", "smtp.gmail.com"), key="smtp_h_in")
                user_smtp = st.text_input("Usuario / Correo Remitente:", value=config.get("smtp_user", "notificaciones@taller.com"), key="smtp_u_in")
            with c2:
                port = st.number_input("Puerto SMTP:", min_value=1, max_value=65535, value=int(config.get("smtp_port", 587)), key="smtp_p_in")
                pass_smtp = st.text_input("Contraseña de Aplicación / Token:", value=config.get("smtp_pass", ""), type="password", key="smtp_pwd_in")

            ssl_chk = st.checkbox("Habilitar TLS / SSL Seguro", value=bool(config.get("smtp_ssl", 1)), key="smtp_ssl_in")

            submit_smtp = st.form_submit_button("💾 Guardar Configuración SMTP", use_container_width=True)
            if submit_smtp:
                data_update = dict(config)
                data_update.update({
                    "smtp_host": host.strip(),
                    "smtp_port": int(port),
                    "smtp_user": user_smtp.strip(),
                    "smtp_pass": pass_smtp.strip(),
                    "smtp_ssl": 1 if ssl_chk else 0,
                })
                update_workshop_config(data_update)
                log_audit(user, "taller_config", "1", "ACTUALIZAR_SMTP", f"SMTP Host: {host}")
                st.toast("✅ Configuración SMTP actualizada", icon="🔌")
                st.rerun()

    with t_tpl:
        st.markdown("<b style='color: #10B981; font-size: 1rem;'>Diseñador de Plantillas de Notificación</b>", unsafe_allow_html=True)
        st.markdown(
            """
            <span style="color: #9CA3AF; font-size: 0.8rem;">Variables dinámicas disponibles: 
                <code>{cliente_nombre}</code>, <code>{ot_codigo}</code>, <code>{equipo_modelo}</code>, 
                <code>{estado_actual}</code>, <code>{saldo_pendiente}</code>, <code>{taller_nombre}</code>
            </span>
            """,
            unsafe_allow_html=True,
        )

        sel_trigger = st.selectbox(
            "Seleccionar Disparador de Notificación:",
            ["Ingreso de Equipo", "Presupuesto Listo", "Equipo Listo para Retiro", "Equipo Entregado"],
            key="email_trigger_sel",
        )

        default_tpl = (
            "Hola {cliente_nombre},\n\n"
            "Te informamos que tu equipo {equipo_modelo} bajo la orden de servicio #{ot_codigo} ha cambiado al estado: {estado_actual}.\n\n"
            "Saldo pendiente a abonar al retirar: ${saldo_pendiente}.\n\n"
            "Atentamente,\n"
            "El equipo de {taller_nombre}"
        )

        tpl_subject = st.text_input("Asunto del Correo:", value=f"Actualización de tu equipo #{'{ot_codigo}'} - {'{taller_nombre}'}", key="email_sub_in")
        tpl_body = st.text_area("Cuerpo del Mensaje:", value=default_tpl, height=160, key="email_body_in")

        # Vista previa interactiva
        st.markdown("<b style='color: #00F0FF; font-size: 0.9rem;'>👁️ Vista Previa del Email Renderizado:</b>", unsafe_allow_html=True)
        preview_body = (
            tpl_body
            .replace("{cliente_nombre}", "Carlos Benítez")
            .replace("{ot_codigo}", "OT-1002")
            .replace("{equipo_modelo}", "iPhone 13 Pro")
            .replace("{estado_actual}", sel_trigger)
            .replace("{saldo_pendiente}", "15.000")
            .replace("{taller_nombre}", config.get("nombre_taller", "LABFIX"))
        )

        st.markdown(
            f"""
            <div style="background: #111827; border: 1px solid #1F2937; border-radius: 8px; padding: 15px; font-family: sans-serif; font-size: 0.85rem; color: #E5E7EB; white-space: pre-wrap;">
                <b>Para:</b> cliente@gmail.com<br>
                <b>Asunto:</b> Actualización de tu equipo #OT-1002 - {config.get('nombre_taller', 'LABFIX')}<br>
                <hr style="border-color: #374151; margin: 8px 0;">
                {preview_body}
            </div>
            """,
            unsafe_allow_html=True,
        )

