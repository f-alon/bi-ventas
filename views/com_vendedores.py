"""Módulo 2.4: Vendedores & Liquidación de Comisiones Comerciales (ERP LABFIX)."""

from datetime import date
from typing import Any, Dict
import pandas as pd
import streamlit as st
from auth import hash_password
from components.cards import empty_state, format_currency, format_number, format_pct, metric_card
from database import get_connection, log_audit


def render_vendedores_view() -> None:
    """Renderiza el control comercial de vendedores, metas de mostrador y liquidación de comisiones."""
    current_user = st.session_state.get("username", "admin")
    user_role = st.session_state.get("user_role", "admin")

    st.markdown(
        """
        <div style="margin-bottom: 1.25rem;">
            <h2 style="color: #FFFFFF; font-weight: 800; margin: 0; font-size: 1.6rem; letter-spacing: -0.02em;">
                💼 Gestión de Vendedores & Liquidación de Comisiones
            </h2>
            <span style="color: #9CA3AF; font-size: 0.85rem;">
                Seguimiento de ventas por mostrador, recepción de reparaciones y cálculo de incentivos
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    conn = get_connection()

    # Cargar vendedores registrados
    vendedores_rows = conn.execute("SELECT id, username, nombre, rol, comision_pct, created_at FROM usuarios WHERE rol IN ('vendedor', 'admin') ORDER BY nombre ASC").fetchall()

    if not vendedores_rows:
        empty_state("No hay personal comercial registrado.", "Crea un usuario vendedor desde la pestaña de alta.")
        return

    t_rep, t_alta = st.tabs(["📊 Liquidación y Rendimiento", "➕ Registrar Vendedor / Ajustar %"])

    with t_alta:
        st.markdown("<b style='color: #00F0FF; font-size: 1rem;'>Alta de Nuevo Vendedor</b>", unsafe_allow_html=True)
        with st.form(key="form_alta_vendedor"):
            c1, c2 = st.columns(2)
            with c1:
                v_nom = st.text_input("Nombre Completo *", key="ven_nom_input")
                v_user = st.text_input("Usuario (Login) *", key="ven_user_input")
            with c2:
                v_pass = st.text_input("Contraseña Temporal *", type="password", key="ven_pass_input")
                v_pct = st.number_input("% Comisión en Ventas:", min_value=0.0, max_value=50.0, value=5.0, step=0.5, key="ven_pct_input")

            submit_v = st.form_submit_button("💾 Crear Vendedor", use_container_width=True)
            if submit_v:
                if not v_nom.strip() or not v_user.strip() or not v_pass.strip():
                    st.error("Todos los campos con (*) son requeridos.")
                else:
                    try:
                        p_hash = hash_password(v_pass.strip())
                        with conn:
                            conn.execute(
                                """
                                INSERT INTO usuarios (username, password_hash, nombre, rol, comision_pct)
                                VALUES (?, ?, ?, 'vendedor', ?)
                                """,
                                (v_user.strip().lower(), p_hash, v_nom.strip(), float(v_pct)),
                            )
                        log_audit(current_user, "usuarios", v_user.strip(), "ALTA_VENDEDOR", f"Vendedor {v_nom} ({v_pct}%)")
                        st.toast(f"✅ Vendedor {v_nom} dado de alta con éxito", icon="💼")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al registrar vendedor: {e}")

    with t_rep:
        # Selector de vendedor
        ven_dict = {f"{r['nombre']} ({r['username']}) - {r['comision_pct']:.1f}%": r for r in vendedores_rows}
        sel_str = st.selectbox("Seleccionar Vendedor a Evaluar:", list(ven_dict.keys()), key="ven_eval_sel")
        ven_data = ven_dict[sel_str]
        v_id = int(ven_data["id"])
        com_pct = float(ven_data["comision_pct"])

        # Período de liquidación
        c_p1, c_p2, c_p3 = st.columns(3)
        today = date.today()
        with c_p1:
            mes_sel = st.selectbox("Mes de Liquidación:", range(1, 13), index=today.month - 1, format_func=lambda m: f"Mes {m:02d}", key="ven_mes_sel")
        with c_p2:
            anio_sel = st.selectbox("Año:", [today.year - 1, today.year, today.year + 1], index=1, key="ven_anio_sel")
        with c_p3:
            st.metric(label="Tasa de Comisión Asignada", value=f"{com_pct:.1f}%")

        # 1. Ventas de Mostrador concretadas por este vendedor en el período
        sql_v = """
            SELECT numero_ticket, subtotal, total, metodo_pago, creado_en
            FROM ventas
            WHERE vendedor_id = ?
              AND strftime('%m', creado_en) = ?
              AND strftime('%Y', creado_en) = ?
            ORDER BY creado_en DESC
        """
        rows_v = conn.execute(sql_v, (v_id, f"{mes_sel:02d}", str(anio_sel))).fetchall()
        df_v_ven = pd.DataFrame([dict(r) for r in rows_v]) if rows_v else pd.DataFrame()

        total_ventas_mostrador = df_v_ven["total"].sum() if not df_v_ven.empty else 0.0
        comision_ventas = total_ventas_mostrador * (com_pct / 100.0)

        # 2. Órdenes de Servicio recibidas / vendidas en mostrador por este vendedor
        sql_ot = """
            SELECT ot_codigo, marca, modelo, total, estado, fecha_ingreso
            FROM dispositivos_ordenes
            WHERE vendedor_id = ?
              AND strftime('%m', fecha_ingreso) = ?
              AND strftime('%Y', fecha_ingreso) = ?
            ORDER BY fecha_ingreso DESC
        """
        rows_ot = conn.execute(sql_ot, (v_id, f"{mes_sel:02d}", str(anio_sel))).fetchall()
        df_ot_ven = pd.DataFrame([dict(r) for r in rows_ot]) if rows_ot else pd.DataFrame()

        total_ot_captadas = df_ot_ven["total"].sum() if not df_ot_ven.empty else 0.0
        # Supongamos incentivo del 2% por captación de OT
        comision_ot = total_ot_captadas * 0.02
        comision_total_periodo = comision_ventas + comision_ot

        st.markdown("<hr style='border-color: #1F2937; margin: 1rem 0;'>", unsafe_allow_html=True)

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            metric_card("Ventas POS del Mes", format_currency(total_ventas_mostrador), glow_color="green")
        with k2:
            metric_card(f"Comisión Ventas ({com_pct:.0f}%)", format_currency(comision_ventas), glow_color="purple")
        with k3:
            metric_card("OTs Captadas Mostrador", f"{len(df_ot_ven)} equipos", glow_color="cyan")
        with k4:
            metric_card("Liquidación Total Estimada", format_currency(comision_total_periodo), glow_color="yellow")

        # Desglose de Ventas del Período
        st.markdown("<b style='color: #E5E7EB; font-size: 0.95rem; margin-top: 1rem; display: block;'>Detalle de Tickets de Mostrador:</b>", unsafe_allow_html=True)
        if df_v_ven.empty:
            st.caption("No registra ventas en este período.")
        else:
            st.dataframe(
                df_v_ven[["numero_ticket", "creado_en", "metodo_pago", "subtotal", "total"]],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "numero_ticket": st.column_config.TextColumn("Nº Ticket", width="small"),
                    "creado_en": st.column_config.TextColumn("Fecha", width="medium"),
                    "metodo_pago": st.column_config.TextColumn("Medio", width="small"),
                    "subtotal": st.column_config.NumberColumn("Subtotal", format="$%.0f"),
                    "total": st.column_config.NumberColumn("Total", format="$%.0f"),
                },
            )

