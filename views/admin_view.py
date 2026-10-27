"""Panel Maestro de Administración y Business Intelligence Global (Admin View)."""

import pandas as pd
import streamlit as st
from auth import (
    create_user,
    delete_user,
    get_all_technicians,
    get_all_users,
    get_available_technicians,
)
from components.cards import empty_state, format_currency, format_number, render_header
from core.config import ESTADOS_WIP
from core.db import purge_database
from core.seed import seed_database
from views.tab_diagnostics import render_tab_diagnostics
from views.tab_explorer import render_tab_explorer
from views.tab_financial import render_tab_financial
from views.tab_ingestion import render_tab_ingestion
from views.tab_overview import render_tab_overview


def render_admin_dashboard(df_all: pd.DataFrame, df_filtered: pd.DataFrame) -> None:
    """Renderiza el centro de comando administrativo completo con métricas globales y gestión de equipo."""
    total_orders = len(df_all)
    active_wip = len(df_all[df_all["estado"].isin(ESTADOS_WIP)]) if not df_all.empty else 0

    # Header principal
    render_header(total_orders=total_orders, active_wip=active_wip)

    # Selector Global de Auditoría por Técnico
    todos_tecnicos = ["Todos los técnicos (Vista Global)"] + get_available_technicians()

    c_audit_label, c_audit_sel = st.columns([1.5, 2])
    with c_audit_label:
        st.markdown(
            """
            <div style="padding-top: 0.4rem; color: #9CA3AF; font-size: 0.88rem;">
                <b style="color: #00F0FF;">👑 Vista de Administrador:</b> Filtrar analíticas por técnico o ver taller completo:
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c_audit_sel:
        filtro_tecnico_admin = st.selectbox(
            "Auditar Técnico:",
            options=todos_tecnicos,
            index=0,
            key="admin_sel_audit_tech",
            label_visibility="collapsed",
        )

    # Aplicar filtro de técnico sobre el dataset si se seleccionó uno específico
    if filtro_tecnico_admin != "Todos los técnicos (Vista Global)":
        df_view = df_filtered[df_filtered["tecnico"] == filtro_tecnico_admin].copy()
        st.markdown(
            f"""
            <div style="background: rgba(0, 240, 255, 0.08); border-left: 3px solid #00F0FF; padding: 0.4rem 0.8rem; border-radius: 4px; margin-bottom: 0.75rem; font-size: 0.85rem; color: #00F0FF;">
                Auditando métricas exclusivas de: <b>{filtro_tecnico_admin}</b> ({len(df_view)} órdenes en período).
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        df_view = df_filtered

    # Pestañas completas del Administrador
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        [
            "📊 Panel Ejecutivo y Operativo",
            "💰 Análisis Financiero & Rentabilidad",
            "🔬 Métricas de Dispositivos & Fallas",
            "🔍 Explorador & Auditoría",
            "➕ Ingesta & Carga de OTs",
            "👥 Gestión de Usuarios & Taller",
        ]
    )

    with tab1:
        render_tab_overview(df_view)

    with tab2:
        render_tab_financial(df_view)

    with tab3:
        render_tab_diagnostics(df_view)

    with tab4:
        render_tab_explorer(df_all)

    with tab5:
        render_tab_ingestion()

    with tab6:
        render_user_and_system_management()


def render_user_and_system_management() -> None:
    """Pestaña de administración de personal, altas de técnicos y control de base de datos."""
    st.markdown("<h4 style='color: #F3F4F6;'>Gestión de Usuarios y Personal Técnico</h4>", unsafe_allow_html=True)

    col_users_list, col_new_user = st.columns([1.6, 1.2])

    with col_users_list:
        st.markdown("<b style='color: #00F0FF;'>Usuarios Registrados en el Sistema:</b>", unsafe_allow_html=True)
        users = get_all_users()
        if not users:
            st.info("No hay usuarios registrados.")
        else:
            users_df = pd.DataFrame(users)
            st.dataframe(
                users_df[["id", "username", "nombre_completo", "rol", "creado_en"]].rename(
                    columns={
                        "id": "ID",
                        "username": "Usuario",
                        "nombre_completo": "Nombre y Apellido",
                        "rol": "Rol",
                        "creado_en": "Fecha Alta",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

            # Eliminar usuario
            with st.expander("🗑️ Dar de Baja un Usuario"):
                user_del_id = st.selectbox(
                    "Seleccionar Usuario para eliminar:",
                    options=[u["id"] for u in users if u["username"] != st.session_state.get("username")],
                    format_func=lambda uid: next(f"{u['nombre_completo']} ({u['username']})" for u in users if u["id"] == uid),
                    key="admin_sel_del_user",
                ) if len(users) > 1 else None

                if user_del_id and st.button("Eliminar Usuario Seleccionado", type="secondary", key="btn_del_user"):
                    delete_user(user_del_id)
                    st.toast("Usuario eliminado correctamente.", icon="🗑️")
                    st.rerun()

    with col_new_user:
        st.markdown("<b style='color: #10B981;'>Dar de Alta Nuevo Técnico o Admin:</b>", unsafe_allow_html=True)
        with st.container():
            n_nombre = st.text_input("Nombre y Apellido:", placeholder="Ej: Marcelo Gómez", key="admin_add_nombre")
            n_user = st.text_input("Nombre de Usuario (Login):", placeholder="Ej: marcelo_g", key="admin_add_user")
            n_pass = st.text_input("Contraseña:", type="password", key="admin_add_pass")
            n_rol = st.selectbox("Rol Asignado:", options=["tecnico", "admin"], format_func=lambda r: "Técnico de Laboratorio" if r == "tecnico" else "Administrador / Jefe", key="admin_add_rol")

            if st.button("➕ Crear Usuario", type="primary", use_container_width=True, key="admin_btn_create_user"):
                if not n_nombre.strip() or not n_user.strip() or not n_pass.strip():
                    st.error("Completá todos los campos.")
                else:
                    try:
                        create_user(
                            username=n_user.strip(),
                            password=n_pass,
                            nombre_completo=n_nombre.strip(),
                            rol=n_rol,
                        )
                        st.success(f"¡Usuario '{n_user}' creado exitosamente!")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Error al crear usuario: {exc}")

    st.markdown("<div style='border-top: 1px solid #1F2937; margin: 2rem 0 1.5rem 0;'></div>", unsafe_allow_html=True)

    # Herramientas de Mantenimiento y Reinicio de Base de Datos
    st.markdown("<h4 style='color: #F43F5E;'>⚙️ Mantenimiento y Purgado de Base de Datos (Clean Reset)</h4>", unsafe_allow_html=True)
    st.markdown(
        """
        <p style="color: #9CA3AF; font-size: 0.85rem;">
            Podes reiniciar los datos de órdenes de trabajo a cero para arrancar una producción limpia, o repoblar con datos de prueba sintéticos.
        </p>
        """,
        unsafe_allow_html=True,
    )

    c_rst1, c_rst2 = st.columns(2)
    with c_rst1:
        st.markdown(
            """
            <div style="background: rgba(244, 63, 94, 0.08); border: 1px solid rgba(244, 63, 94, 0.3); padding: 1rem; border-radius: 8px;">
                <b style="color: #F43F5E;">Limpiar Base de Datos a CERO</b>
                <p style="color: #9CA3AF; font-size: 0.8rem; margin: 0.4rem 0 0.8rem 0;">
                    Borra todas las órdenes de trabajo para arrancar de cero. Las cuentas de usuarios se conservan.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        confirmar_purge = st.checkbox("Confirmo que deseo purgar todas las órdenes a cero", key="chk_confirm_purge")
        if st.button("🚨 Purgar Órdenes a CERO", type="secondary", disabled=not confirmar_purge, key="btn_purge_db"):
            purge_database(keep_users=True)
            st.toast("Base de datos purgada a cero. Estadísticas limpias.", icon="🧹")
            st.rerun()

    with c_rst2:
        st.markdown(
            """
            <div style="background: rgba(0, 240, 255, 0.08); border: 1px solid rgba(0, 240, 255, 0.3); padding: 1rem; border-radius: 8px;">
                <b style="color: #00F0FF;">Cargar Datos de Prueba (Seed Demo)</b>
                <p style="color: #9CA3AF; font-size: 0.8rem; margin: 0.4rem 0 0.8rem 0;">
                    Inserta 180 órdenes sintéticas de microelectrónica para demostración o análisis.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("🌱 Sembrar 180 Órdenes de Prueba", type="primary", key="btn_seed_demo_admin"):
            seed_database(num_records=180, force=True)
            st.toast("Se insertaron 180 órdenes de prueba.", icon="🌱")
            st.rerun()

