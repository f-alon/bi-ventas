"""Módulo 5.3: Soporte Interno, Reporte de Bugs y Visor de Auditoría (ERP LABFIX)."""

from typing import Any, Dict
import pandas as pd
import streamlit as st
from components.cards import empty_state, format_number, metric_card
from database import get_connection, log_audit


def render_soporte_view() -> None:
    """Renderiza el centro de trazabilidad, logs inmutables y reporte interno de soporte."""
    user = st.session_state.get("username", "admin")
    user_id = st.session_state.get("user_id", 1)

    st.markdown(
        """
        <div style="margin-bottom: 1.25rem;">
            <h2 style="color: #FFFFFF; font-weight: 800; margin: 0; font-size: 1.6rem; letter-spacing: -0.02em;">
                🛡️ Soporte del Sistema & Trazabilidad
            </h2>
            <span style="color: #9CA3AF; font-size: 0.85rem;">
                Bitácora inmutable de auditoría forense, reporte de incidencias y estado de salud
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    conn = get_connection()

    t_audit, t_tickets, t_nuevo_ticket = st.tabs(["📜 Logs de Auditoría", "🎫 Tickets de Soporte", "➕ Reportar Incidencia"])

    # 1. PESTAÑA AUDITORÍA
    with t_audit:
        st.markdown("<b style='color: #00F0FF; font-size: 1rem;'>Visor de Trazabilidad y Auditoría Forense</b>", unsafe_allow_html=True)

        sql_logs = "SELECT * FROM auditoria_logs ORDER BY fecha DESC LIMIT 150"
        logs = conn.execute(sql_logs).fetchall()

        if not logs:
            empty_state("No hay registros de auditoría.", "Las acciones del sistema se grabarán aquí automáticamente.")
        else:
            df_logs = pd.DataFrame([dict(r) for r in logs])

            c_f1, c_f2 = st.columns([1, 1])
            with c_f1:
                users_list = ["Todos"] + sorted(list(df_logs["usuario"].dropna().unique()))
                sel_u = st.selectbox("Filtrar por Usuario:", users_list, key="audit_filter_user")
            with c_f2:
                q_det = st.text_input("Buscar en Acción / Detalle:", placeholder="OT-1001, VENTA, LOGIN...", key="audit_filter_q")

            df_show = df_logs.copy()
            if sel_u != "Todos":
                df_show = df_show[df_show["usuario"] == sel_u]
            if q_det.strip():
                t = q_det.strip().lower()
                df_show = df_show[
                    df_show["accion"].str.lower().str.contains(t, na=False)
                    | df_show["detalle"].str.lower().str.contains(t, na=False)
                    | df_show["entidad_id"].str.lower().str.contains(t, na=False)
                ]

            st.dataframe(
                df_show[["fecha", "usuario", "entidad", "entidad_id", "accion", "detalle"]],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "fecha": st.column_config.TextColumn("Marca de Tiempo", width="medium"),
                    "usuario": st.column_config.TextColumn("Usuario", width="small"),
                    "entidad": st.column_config.TextColumn("Entidad", width="small"),
                    "entidad_id": st.column_config.TextColumn("ID Ref.", width="small"),
                    "accion": st.column_config.TextColumn("Acción", width="medium"),
                    "detalle": st.column_config.TextColumn("Detalle Operativo", width="large"),
                },
            )

    # 2. PESTAÑA ALTA DE INCIDENCIA
    with t_nuevo_ticket:
        st.markdown("<b style='color: #F59E0B; font-size: 1rem;'>Reportar un Bug, Sugerencia o Incidencia Técnica</b>", unsafe_allow_html=True)
        with st.form(key="form_nuevo_ticket"):
            tit = st.text_input("Título Corto del Problema *", placeholder="Ej: Error al imprimir remito de OT...", key="tk_tit_in")
            c_p1, c_p2 = st.columns(2)
            with c_p1:
                prio = st.selectbox("Nivel de Urgencia / Prioridad:", ["Baja", "Media", "Alta", "Crítica (Bloqueante)"], index=1, key="tk_prio_in")
            with c_p2:
                mod_af = st.selectbox("Módulo Afectado:", ["Órdenes de Trabajo", "Punto de Venta", "Stock", "Caja Diaria", "Comprobantes", "Otro"], key="tk_mod_in")

            desc = st.text_area("Descripción Detallada y Pasos para Reproducir:", height=120, key="tk_desc_in")

            submit_tk = st.form_submit_button("🚀 Enviar Ticket a Soporte", use_container_width=True)
            if submit_tk:
                if not tit.strip() or not desc.strip():
                    st.error("El título y la descripción son requeridos.")
                else:
                    try:
                        with conn:
                            conn.execute(
                                """
                                INSERT INTO soporte_tickets (usuario_id, titulo, descripcion, prioridad, estado)
                                VALUES (?, ?, ?, ?, 'abierto')
                                """,
                                (user_id, f"[{mod_af}] {tit.strip()}", desc.strip(), prio.lower()),
                            )
                        log_audit(user, "soporte_tickets", "0", "CREAR_TICKET", f"Incidencia: {tit}")
                        st.toast("✅ Incidencia enviada al equipo técnico", icon="🎫")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al enviar ticket: {e}")

    # 3. PESTAÑA LISTADO TICKETS
    with t_tickets:
        sql_tk = """
            SELECT t.id, t.titulo, t.descripcion, t.prioridad, t.estado, t.created_at,
                   u.nombre as reportado_por
            FROM soporte_tickets t
            LEFT JOIN usuarios u ON t.usuario_id = u.id
            ORDER BY t.id DESC
        """
        rows_tk = conn.execute(sql_tk).fetchall()

        if not rows_tk:
            empty_state("No hay incidencias reportadas.", "El sistema funciona con normalidad y sin tickets abiertos.")
        else:
            df_tk = pd.DataFrame([dict(r) for r in rows_tk])
            st.dataframe(
                df_tk[["id", "created_at", "reportado_por", "titulo", "prioridad", "estado", "descripcion"]],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "id": st.column_config.NumberColumn("Ticket #", width="small"),
                    "created_at": st.column_config.TextColumn("Fecha", width="medium"),
                    "reportado_por": st.column_config.TextColumn("Reportado Por", width="small"),
                    "titulo": st.column_config.TextColumn("Título", width="medium"),
                    "prioridad": st.column_config.TextColumn("Prioridad", width="small"),
                    "estado": st.column_config.TextColumn("Estado", width="small"),
                    "descripcion": st.column_config.TextColumn("Detalle", width="large"),
                },
            )

