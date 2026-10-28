"""Módulo 4.1: Caja Diaria, Arqueo Físico, Gastos Recurrentes y Control de Deuda (ERP LABFIX)."""

import base64
from datetime import date
from typing import Any, Dict
import pandas as pd
import streamlit as st
from components.cards import empty_state, format_currency, format_number, metric_card
from core.config import FRECUENCIAS_GASTO, METODOS_PAGO
from database import (
    add_cash_movement,
    close_cash_session,
    execute_recurring_expenses,
    get_active_cash_session,
    get_connection,
    load_orders_df,
    log_audit,
    open_cash_session,
)


def render_caja_view() -> None:
    """Renderiza el módulo financiero de caja diaria, arqueo de fondos y gastos recurrentes."""
    user = st.session_state.get("username", "cajero")
    user_id = st.session_state.get("user_id", 1)
    org_id = st.session_state.get("organizacion_id", 1)

    st.markdown(
        """
        <div style="margin-bottom: 1.25rem;">
            <h2 style="color: #FFFFFF; font-weight: 800; margin: 0; font-size: 1.6rem; letter-spacing: -0.02em;">
                💵 Control de Caja Diaria, Arqueo & Gastos
            </h2>
            <span style="color: #9CA3AF; font-size: 0.85rem;">
                Apertura formal de turno, arqueo ciego, gastos periódicos y órdenes impagas
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    conn = get_connection()
    sesion_activa = get_active_cash_session(org_id=org_id)

    t_actual, t_gastos_rec, t_deuda, t_hist = st.tabs([
        "⚡ Sesión Actual de Caja",
        "🔄 Gastos Recurrentes",
        "⚠️ Control de Deuda / OTs Impagas",
        "📋 Historial de Cierres de Turno",
    ])

    # 1. PESTAÑA GASTOS RECURRENTES
    with t_gastos_rec:
        st.markdown("<b style='color: #00F0FF; font-size: 1rem;'>🔄 Gastos Periódicos Programados (Alquiler, Servicios, Abonos)</b>", unsafe_allow_html=True)
        col_exec, col_dummy = st.columns([1.5, 2])
        with col_exec:
            if st.button("⚡ Ejecutar y Asentar Gastos Vencidos a Caja", type="primary", use_container_width=True, key="btn_exec_rec_exp"):
                cant_gen = execute_recurring_expenses(org_id=org_id, user=user)
                if cant_gen > 0:
                    st.toast(f"✅ Se aplicaron {cant_gen} gastos vencidos a la caja diaria", icon="💸")
                else:
                    st.info("No hay gastos recurrentes vencidos a la fecha.")
                st.rerun()

        # Lista de gastos recurrentes
        sql_rec = """
            SELECT g.*, c.nombre as cat_nombre
            FROM gastos_recurrentes g
            JOIN categorias_gasto c ON g.categoria_id = c.id
            WHERE g.organizacion_id = ?
            ORDER BY g.proximo_vencimiento ASC
        """
        rows_rec = conn.execute(sql_rec, (org_id,)).fetchall()
        if not rows_rec:
            st.caption("No hay gastos recurrentes configurados.")
        else:
            df_rec = pd.DataFrame([dict(r) for r in rows_rec])
            st.dataframe(
                df_rec[["id", "concepto", "cat_nombre", "monto", "frecuencia", "metodo_pago", "proximo_vencimiento", "pausado"]],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "monto": st.column_config.NumberColumn("Monto ($)", format="$%d"),
                    "proximo_vencimiento": st.column_config.TextColumn("Próximo Vencimiento"),
                },
            )

        # Formulario para nuevo gasto recurrente
        with st.expander("➕ Programar Nuevo Gasto Recurrente"):
            cats_db = conn.execute("SELECT id, nombre FROM categorias_gasto WHERE organizacion_id = ?", (org_id,)).fetchall()
            cat_dict = {c["nombre"]: c["id"] for c in cats_db}
            with st.form(key="form_nuevo_gasto_rec"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    conc_r = st.text_input("Concepto:", placeholder="Alquiler local comercial", key="gr_conc_in")
                    monto_r = st.number_input("Monto ($):", min_value=1.0, value=85000.0, step=1000.0, key="gr_monto_in")
                with c2:
                    cat_r = st.selectbox("Categoría de Gasto:", list(cat_dict.keys()), key="gr_cat_in")
                    frec_r = st.selectbox("Frecuencia:", FRECUENCIAS_GASTO, index=1, key="gr_frec_in")
                with c3:
                    met_r = st.selectbox("Medio de Pago habitual:", METODOS_PAGO, key="gr_met_in")
                    venc_r = st.date_input("Primer Vencimiento:", value=date.today(), key="gr_venc_in")

                if st.form_submit_button("Guardar Gasto Programado", use_container_width=True):
                    if not conc_r.strip():
                        st.error("El concepto es obligatorio.")
                    else:
                        with conn:
                            conn.execute(
                                """
                                INSERT INTO gastos_recurrentes (organizacion_id, concepto, monto, metodo_pago, categoria_id, frecuencia, proximo_vencimiento)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                                """,
                                (org_id, conc_r.strip(), monto_r, met_r, cat_dict[cat_r], frec_r, str(venc_r)),
                            )
                        st.toast("✅ Gasto programado con éxito", icon="🔄")
                        st.rerun()

    # 2. PESTAÑA CONTROL DE DEUDA
    with t_deuda:
        st.markdown("<b style='color: #F43F5E; font-size: 1rem;'>⚠️ Órdenes Reparadas / Entregadas con Saldo Pendiente</b>", unsafe_allow_html=True)
        df_all_orders = load_orders_df(org_id=org_id)
        df_deudores = df_all_orders[
            df_all_orders["estado"].isin(["COMPLETADA", "ENTREGADA", "Listo para Retiro", "Entregado"])
            & (df_all_orders["saldo_pendiente"] > 0)
        ]

        if df_deudores.empty:
            st.success("✅ No existen órdenes completadas o entregadas con saldos pendientes por cobrar.")
        else:
            total_deuda = df_deudores["saldo_pendiente"].sum()
            st.warning(f"Monto Total Pendiente de Cobro: **{format_currency(total_deuda)}** en **{len(df_deudores)}** órdenes.")
            st.dataframe(
                df_deudores[["ot_codigo", "cliente_nombre", "cliente_telefono", "marca", "modelo", "estado", "total", "monto_senado", "saldo_pendiente"]],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "total": st.column_config.NumberColumn("Total", format="$%d"),
                    "monto_senado": st.column_config.NumberColumn("Seña Previa", format="$%d"),
                    "saldo_pendiente": st.column_config.NumberColumn("Saldo a Cobrar", format="$%d"),
                },
            )

    # 3. PESTAÑA HISTORIAL DE CIERRES
    with t_hist:
        sql_hist = """
            SELECT s.id, s.fecha_apertura, s.fecha_cierre, s.saldo_inicial_efectivo, s.conteo_fisico_efectivo,
                   s.efectivo_esperado, s.diferencia, s.observaciones,
                   u_ap.nombre as apertura_por, u_cl.nombre as cierre_por
            FROM caja_sesiones s
            LEFT JOIN usuarios u_ap ON s.usuario_apertura_id = u_ap.id
            LEFT JOIN usuarios u_cl ON s.usuario_cierre_id = u_cl.id
            WHERE s.organizacion_id = ? AND s.estado = 'CERRADA'
            ORDER BY s.id DESC
        """
        rows_hist = conn.execute(sql_hist, (org_id,)).fetchall()
        if not rows_hist:
            empty_state("No hay cierres de caja registrados.", "Al cerrar un turno, quedará archivado aquí con sus conciliaciones auditadas.")
        else:
            df_hist_caja = pd.DataFrame([dict(r) for r in rows_hist])
            st.dataframe(
                df_hist_caja[["id", "fecha_apertura", "fecha_cierre", "apertura_por", "cierre_por", "saldo_inicial_efectivo", "conteo_fisico_efectivo", "efectivo_esperado", "diferencia", "observaciones"]],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "saldo_inicial_efectivo": st.column_config.NumberColumn("Fondo Fijo", format="$%d"),
                    "conteo_fisico_efectivo": st.column_config.NumberColumn("Conteo Físico", format="$%d"),
                    "efectivo_esperado": st.column_config.NumberColumn("Teórico", format="$%d"),
                    "diferencia": st.column_config.NumberColumn("Diferencia", format="$%d"),
                },
            )

    # 4. PESTAÑA SESIÓN ACTUAL
    with t_actual:
        if not sesion_activa:
            st.warning("⚠️ La caja se encuentra actualmente CERRADA.")
            st.markdown("<b style='color: #00F0FF; font-size: 1rem;'>Apertura Obligatoria de Turno</b>", unsafe_allow_html=True)
            with st.form(key="form_apertura_caja"):
                m_ini = st.number_input("Fondo Fijo Inicial de Efectivo / Cambio ($):", min_value=0.0, value=25000.0, step=1000.0, key="caja_apertura_monto")
                submit_ap = st.form_submit_button("🚀 Abrir Turno de Caja", type="primary", use_container_width=True)
                if submit_ap:
                    s_id = open_cash_session(user_id, m_ini, org_id=org_id)
                    log_audit(user, "caja_sesiones", str(s_id), "APERTURA_CAJA", f"Fondo inicial: ${m_ini:,.0f}", org_id=org_id)
                    st.toast(f"✅ Sesión de caja #{s_id} iniciada", icon="💵")
                    st.rerun()
            return

        ses_id = int(sesion_activa["id"])
        st.markdown(
            f"""
            <div style="background: #111827; border: 1px solid #10B981; border-radius: 8px; padding: 12px 18px; margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span style="background: #10B981; color: #111827; font-weight: 800; font-size: 0.72rem; padding: 2px 8px; border-radius: 4px; text-transform: uppercase;">Caja Abierta (Turno #{ses_id})</span>
                    <h3 style="color: #FFFFFF; margin: 4px 0 0 0; font-size: 1.1rem;">Responsable: {sesion_activa.get('usuario_nombre', user)}</h3>
                    <span style="color: #9CA3AF; font-size: 0.8rem;">Iniciada el: {sesion_activa['fecha_apertura']}</span>
                </div>
                <div style="text-align: right;">
                    <span style="color: #9CA3AF; font-size: 0.75rem;">Fondo Inicial en Gaveta:</span><br>
                    <b style="color: #00F0FF; font-size: 1.25rem;">{format_currency(sesion_activa['saldo_inicial_efectivo'])}</b>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        sql_movs = """
            SELECT m.*, c.nombre as categoria_nombre
            FROM caja_movimientos m
            LEFT JOIN categorias_gasto c ON m.categoria_id = c.id
            WHERE m.sesion_id = ?
            ORDER BY m.id DESC
        """
        movs = conn.execute(sql_movs, (ses_id,)).fetchall()
        df_movs = pd.DataFrame([dict(r) for r in movs]) if movs else pd.DataFrame()

        ingresos_efectivo = 0.0
        egresos_efectivo = 0.0
        ingresos_digitales = 0.0

        if not df_movs.empty:
            ingresos_efectivo = df_movs[(df_movs["tipo"] == "INGRESO") & (df_movs["metodo_pago"] == "Efectivo")]["monto"].sum()
            egresos_efectivo = df_movs[(df_movs["tipo"] == "EGRESO") & (df_movs["metodo_pago"] == "Efectivo")]["monto"].sum()
            ingresos_digitales = df_movs[(df_movs["tipo"] == "INGRESO") & (df_movs["metodo_pago"] != "Efectivo")]["monto"].sum()

        saldo_efectivo_en_caja = ingresos_efectivo - egresos_efectivo

        kc1, kc2, kc3, kc4 = st.columns(4)
        with kc1:
            metric_card("Efectivo Teórico en Gaveta", format_currency(saldo_efectivo_en_caja), glow_color="green")
        with kc2:
            metric_card("Cobros Digitales / Bancarios", format_currency(ingresos_digitales), glow_color="cyan")
        with kc3:
            metric_card("Egresos / Gastos", format_currency(egresos_efectivo), glow_color="red" if egresos_efectivo > 0 else "neutral")
        with kc4:
            metric_card("Asientos del Turno", f"{len(df_movs)} op.", glow_color="purple")

        st.markdown("<hr style='border-color: #1F2937; margin: 1.5rem 0;'>", unsafe_allow_html=True)

        col_ledger, col_actions = st.columns([3, 2])

        with col_ledger:
            st.markdown("<b style='color: #00F0FF; font-size: 1rem;'>📋 Asientos del Turno</b>", unsafe_allow_html=True)
            if df_movs.empty:
                st.caption("No hay movimientos registrados en este turno.")
            else:
                st.dataframe(
                    df_movs[["fecha", "tipo", "concepto", "categoria_nombre", "metodo_pago", "monto", "comprobante_ref"]],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "monto": st.column_config.NumberColumn("Monto", format="$%d"),
                        "categoria_nombre": st.column_config.TextColumn("Categoría"),
                    },
                )

        with col_actions:
            # Asentar gasto/ingreso con comprobante
            with st.expander("💸 Asentar Gasto o Ingreso Manual", expanded=False):
                cats_db = conn.execute("SELECT id, nombre FROM categorias_gasto WHERE organizacion_id = ?", (org_id,)).fetchall()
                cat_dict = {c["nombre"]: c["id"] for c in cats_db}

                with st.form(key="form_mov_extra_con_file"):
                    t_mov = st.selectbox("Tipo:", ["EGRESO (Gasto / Insumo / Retiro)", "INGRESO Extraordinario"], key="extra_t_in")
                    conc = st.text_input("Concepto:", placeholder="Taxi de urgencia, café, flete...", key="extra_conc_in")
                    sel_cat_name = st.selectbox("Categoría de Gasto:", list(cat_dict.keys()), key="extra_cat_in")
                    c_m1, c_m2 = st.columns(2)
                    with c_m1:
                        monto_ex = st.number_input("Monto ($):", min_value=1.0, value=3500.0, step=500.0, key="extra_monto_in")
                    with c_m2:
                        met_ex = st.selectbox("Medio:", METODOS_PAGO, key="extra_met_in")

                    file_comp = st.file_uploader("Adjuntar Comprobante (JPG/PNG/PDF):", type=["jpg", "png", "pdf"], key="extra_file_in")

                    submit_ex = st.form_submit_button("💾 Asentar en Caja", use_container_width=True)
                    if submit_ex:
                        if not conc.strip():
                            st.error("El concepto es obligatorio.")
                        else:
                            tipo_str = "EGRESO" if "EGRESO" in t_mov else "INGRESO"
                            b64_file = ""
                            if file_comp:
                                b64_file = f"data:{file_comp.type};base64,{base64.b64encode(file_comp.read()).decode('utf-8')}"

                            add_cash_movement(
                                tipo=tipo_str,
                                concepto=conc.strip(),
                                monto=monto_ex,
                                metodo_pago=met_ex,
                                categoria_id=cat_dict[sel_cat_name],
                                comprobante_archivo=b64_file,
                                org_id=org_id,
                            )
                            st.toast("✅ Asiento registrado en caja", icon="💸")
                            st.rerun()

            # Arqueo y Cierre Ciego
            with st.expander("🔒 Arqueo Físico y Cierre de Turno", expanded=True):
                st.markdown("<span style='color: #9CA3AF; font-size: 0.82rem;'>Ingresa el <b>conteo físico real de efectivo</b> que tienes en la gaveta:</span>", unsafe_allow_html=True)
                conteo_in = st.number_input("Total Físico en Gaveta ($):", min_value=0.0, value=float(saldo_efectivo_en_caja), step=1000.0, key="cierre_decl_in")
                dif_live = conteo_in - saldo_efectivo_en_caja

                if dif_live == 0:
                    st.success("🎯 Caja exacta sin diferencias.")
                elif dif_live > 0:
                    st.info(f"🟢 Sobrante en gaveta: +{format_currency(dif_live)}")
                else:
                    st.error(f"🔴 Faltante en gaveta: {format_currency(dif_live)}")

                obs_cierre = st.text_input("Observaciones de Cierre / Diferencias:", placeholder="Sin novedades...", key="cierre_obs_in")

                if st.button("🔒 Confirmar Cierre de Turno", type="primary", use_container_width=True, key="btn_confirm_cierre"):
                    res = close_cash_session(
                        sesion_id=ses_id,
                        usuario_cierre_id=user_id,
                        conteo_fisico=conteo_in,
                        observaciones=obs_cierre,
                        org_id=org_id,
                    )
                    st.toast("✅ Turno de caja cerrado exitosamente", icon="🔒")
                    st.rerun()
