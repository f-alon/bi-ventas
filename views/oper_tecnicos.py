"""Módulo 1.4: Banco de Trabajo Técnico, Gestión de Microelectrónica y Autoasignación (ERP LABFIX)."""

from datetime import date
from typing import Any, Dict
import pandas as pd
import streamlit as st
from components.cards import empty_state, format_currency, format_number, format_pct, get_status_badge_html, metric_card
from core.config import ESTADOS_OT, ESTADOS_WIP
from database import (
    claim_unassigned_work_order,
    consume_part_for_order,
    get_connection,
    get_workshop_config,
    load_orders_df,
    update_work_order_status,
)


def render_tecnicos_view() -> None:
    """Renderiza el banco de trabajo interactivo, notas de placa y toma de órdenes sin asignar."""
    user_role = st.session_state.get("user_role", "TECNICO").upper()
    current_username = st.session_state.get("username", "admin")
    current_tec_nombre = st.session_state.get("tecnico_nombre", "Técnico")
    current_user_id = st.session_state.get("user_id")
    org_id = st.session_state.get("organizacion_id", 1)

    st.markdown(
        """
        <div style="margin-bottom: 1.25rem;">
            <h2 style="color: #FFFFFF; font-weight: 800; margin: 0; font-size: 1.6rem; letter-spacing: -0.02em;">
                🔬 Banco de Trabajo & Microelectrónica
            </h2>
            <span style="color: #9CA3AF; font-size: 0.85rem;">
                Espacio técnico operativo, diagnóstico en placa, consumo de insumos y autoasignación de órdenes
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    conn = get_connection()
    df_orders = load_orders_df(org_id=org_id)
    config = get_workshop_config(org_id=org_id)
    autoasig_habilitada = bool(config.get("autoasignacion_tecnicos", 1))

    # Obtener lista de técnicos registrados
    rows_tec = conn.execute(
        "SELECT id, nombre, comision_pct FROM usuarios WHERE organizacion_id = ? AND rol IN ('TECNICO', 'ADMIN') ORDER BY nombre ASC",
        (org_id,),
    ).fetchall()
    tecnicos_dict = {r["nombre"]: (r["id"], float(r["comision_pct"])) for r in rows_tec}

    c_filt, c_blank = st.columns([2, 2])
    with c_filt:
        if user_role == "ADMIN":
            opciones_tec = ["Todos"] + list(tecnicos_dict.keys())
            idx_def = opciones_tec.index(current_tec_nombre) if current_tec_nombre in opciones_tec else 0
            tec_seleccionado = st.selectbox("Filtrar por Técnico:", opciones_tec, index=idx_def, key="tec_filter_select")
        else:
            tec_seleccionado = current_tec_nombre
            st.info(f"Técnico en Banco: **{current_tec_nombre}**")

    # Órdenes sin asignar disponibles
    df_sin_asignar = df_orders[df_orders["tecnico_id"].isna() & df_orders["estado"].isin(ESTADOS_WIP)] if not df_orders.empty else pd.DataFrame()

    df_view = df_orders.copy()
    if tec_seleccionado != "Todos" and not df_view.empty:
        df_view = df_view[df_view["tecnico_nombre"] == tec_seleccionado]

    # KPIs del Técnico
    wip_count = len(df_view[df_view["estado"].isin(ESTADOS_WIP)]) if not df_view.empty else 0
    resueltas = len(df_view[df_view["estado"].isin(["COMPLETADA", "ENTREGADA", "Listo para Retiro", "Entregado"])]) if not df_view.empty else 0
    rechazadas = len(df_view[df_view["estado"].isin(["CANCELADA", "Sin Reparación / Rechazado"])]) if not df_view.empty else 0
    total_cerradas = resueltas + rechazadas
    efectividad = (resueltas / total_cerradas * 100.0) if total_cerradas > 0 else 100.0

    comision_pct = 15.0
    if tec_seleccionado in tecnicos_dict:
        comision_pct = tecnicos_dict[tec_seleccionado][1]
    mano_obra_resueltas = df_view[df_view["estado"].isin(["COMPLETADA", "ENTREGADA", "Listo para Retiro", "Entregado"])]["mano_obra"].sum() if not df_view.empty else 0.0
    comision_estimada = mano_obra_resueltas * (comision_pct / 100.0)

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        metric_card("Órdenes en Banco (WIP)", f"{wip_count} equipos", glow_color="cyan")
    with k2:
        metric_card("Reparaciones Exitosas", f"{resueltas} equipos", glow_color="green")
    with k3:
        metric_card("Tasa de Éxito", format_pct(efectividad, show_sign=False), glow_color="yellow" if efectividad < 70 else "green")
    with k4:
        metric_card(f"Comisión ({comision_pct:.0f}%)", format_currency(comision_estimada), glow_color="purple", subtext="Sobre mano de obra")

    st.markdown("<hr style='border-color: #1F2937; margin: 1.5rem 0;'>", unsafe_allow_html=True)

    # Tabs
    tab_titles = ["⚡ Equipos en Banco de Trabajo", "📋 Historial Resuelto"]
    if autoasig_habilitada:
        tab_titles.insert(1, f"📥 Órdenes sin Asignar ({len(df_sin_asignar)})")

    tabs = st.tabs(tab_titles)

    # 1. BANCO ACTIVO
    with tabs[0]:
        df_wip = df_view[df_view["estado"].isin(ESTADOS_WIP)].sort_values(by="fecha_ultimo_dt", ascending=True) if not df_view.empty else pd.DataFrame()

        if df_wip.empty:
            empty_state("¡Banco despejado!", "No tienes equipos pendientes de reparación en este momento.")
        else:
            st.markdown(f"<span style='color: #9CA3AF; font-size: 0.85rem;'><b>{len(df_wip)}</b> equipos en proceso de trabajo:</span>", unsafe_allow_html=True)

            for _, row_ot in df_wip.iterrows():
                ot_id = int(row_ot["id"])
                ot_cod = str(row_ot["ot_codigo"])
                estado_actual = str(row_ot["estado"])
                dias_estado = int(row_ot["dias_en_estado"]) if pd.notna(row_ot["dias_en_estado"]) else 0

                border_color = "#374151"
                if dias_estado >= 5:
                    border_color = "#F43F5E"
                elif dias_estado >= 3:
                    border_color = "#F59E0B"

                with st.expander(f"🔧 {ot_cod} - {row_ot['marca']} {row_ot['modelo']} | Estado: {estado_actual} ({dias_estado}d en etapa)", expanded=False):
                    c_info, c_action = st.columns([3, 2])

                    with c_info:
                        st.markdown(
                            f"""
                            <div style="background: #111827; padding: 12px; border-radius: 6px; border-left: 3px solid {border_color}; margin-bottom: 10px;">
                                <div style="display: flex; justify-content: space-between;">
                                    <span style="color: #00F0FF; font-weight: bold; font-size: 1.05rem;">{row_ot['marca']} {row_ot['modelo']} ({row_ot.get('tipo_dispositivo', 'Smartphone')})</span>
                                    <span>{get_status_badge_html(estado_actual)}</span>
                                </div>
                                <div style="color: #9CA3AF; font-size: 0.82rem; margin-top: 4px;">
                                    <b>Cliente:</b> {row_ot['cliente_nombre']} | <b>Ingreso:</b> {row_ot['fecha_ingreso']}<br>
                                    <b>IMEI/Serie:</b> {row_ot['imei_serie'] or 'S/D'} | <b>PIN/Patrón:</b> <code>{row_ot['patron_desbloqueo'] or 'Sin bloqueo'}</code>
                                </div>
                                <div style="margin-top: 8px; font-size: 0.85rem; color: #E5E7EB;">
                                    <b>Falla Declarada:</b><br>
                                    <span style="color: #F87171;">{row_ot['problema']}</span>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                        # Formulario de Diagnóstico y Microelectrónica
                        with st.form(key=f"form_tecnico_diag_{ot_id}"):
                            diag_val = st.text_area(
                                "Diagnóstico Técnico:",
                                value=str(row_ot["diagnostico_tecnico"] or ""),
                                height=70,
                                key=f"tec_diag_input_{ot_id}",
                            )
                            micro_val = st.text_area(
                                "Notas de Microelectrónica (Voltajes, líneas VDD/VCC, componentes reemplazados):",
                                value=str(row_ot["notas_microelectronica"] or ""),
                                height=80,
                                help="Registra valores óhmicos, caídas de tensión en diodo o ICs reboleados.",
                                key=f"tec_micro_input_{ot_id}",
                            )
                            c_b1, c_b2 = st.columns([1, 1])
                            with c_b1:
                                nuevo_est = st.selectbox(
                                    "Actualizar Estado:",
                                    ESTADOS_OT,
                                    index=ESTADOS_OT.index(estado_actual) if estado_actual in ESTADOS_OT else 0,
                                    key=f"tec_next_status_{ot_id}",
                                )
                            with c_b2:
                                st.write("")
                                st.write("")
                                submit_diag = st.form_submit_button("💾 Guardar Avance", use_container_width=True)

                            if submit_diag:
                                update_work_order_status(
                                    ot_codigo=ot_cod,
                                    nuevo_estado=nuevo_est,
                                    user=current_username,
                                    diagnostico=diag_val,
                                    notas_micro=micro_val,
                                    org_id=org_id,
                                )
                                st.toast(f"✅ Avance registrado en {ot_cod}", icon="🔬")
                                st.rerun()

                    with c_action:
                        st.markdown("<b style='color: #E5E7EB; font-size: 0.85rem;'>📦 Imputar Repuesto de Laboratorio</b>", unsafe_allow_html=True)
                        stock_prods = conn.execute(
                            "SELECT id, codigo_sku, nombre, precio_venta, stock_actual FROM productos WHERE organizacion_id = ? AND stock_actual > 0 ORDER BY nombre ASC",
                            (org_id,),
                        ).fetchall()

                        if stock_prods:
                            dict_prods = {f"{p['codigo_sku']} - {p['nombre']} (Disp: {p['stock_actual']})": (p["id"], float(p["precio_venta"])) for p in stock_prods}
                            with st.form(key=f"form_tecnico_part_{ot_id}"):
                                sel_p_str = st.selectbox("Seleccionar Repuesto:", list(dict_prods.keys()), key=f"tec_p_sel_{ot_id}")
                                c_q, c_pr = st.columns(2)
                                with c_q:
                                    cant_p = st.number_input("Cantidad:", min_value=1, value=1, step=1, key=f"tec_p_qty_{ot_id}")
                                with c_pr:
                                    p_id, p_sug = dict_prods[sel_p_str]
                                    precio_cob = st.number_input("Precio Cobro ($):", min_value=0.0, value=p_sug, step=500.0, key=f"tec_p_price_{ot_id}")

                                submit_part = st.form_submit_button("➕ Descontar e Imputar", use_container_width=True)
                                if submit_part:
                                    ok = consume_part_for_order(
                                        ot_id=ot_id,
                                        ot_codigo=ot_cod,
                                        producto_id=p_id,
                                        cantidad=cant_p,
                                        precio_cobrado=precio_cob,
                                        user=current_username,
                                        org_id=org_id,
                                    )
                                    if ok:
                                        st.toast(f"✅ Insumo imputado a {ot_cod}", icon="📦")
                                        st.rerun()
                                    else:
                                        st.error("Error al imputar repuesto.")
                        else:
                            st.caption("No hay repuestos con stock disponible en el catálogo.")

    # 2. ÓRDENES SIN ASIGNAR (SI AUTOASIGNACIÓN HABILITADA)
    if autoasig_habilitada:
        with tabs[1]:
            if df_sin_asignar.empty:
                empty_state("No hay órdenes sin asignar en cola.", "Todos los equipos que ingresaron cuentan con un técnico asignado.")
            else:
                st.markdown("<b style='color: #00F0FF;'>Órdenes de servicio en espera de asignación de técnico:</b>", unsafe_allow_html=True)
                for _, r_un in df_sin_asignar.iterrows():
                    ot_un_id = int(r_un["id"])
                    c_txt, c_btn_take = st.columns([3, 1.2])
                    with c_txt:
                        st.markdown(
                            f"""
                            <div style="background: #111827; border: 1px solid #1F2937; padding: 10px; border-radius: 6px; margin-bottom: 6px;">
                                <b style="color: #FFFFFF;">{r_un['ot_codigo']}</b> - {r_un['marca']} {r_un['modelo']} ({r_un.get('tipo_dispositivo', 'Smartphone')})<br>
                                <span style="color: #9CA3AF; font-size: 0.8rem;">Cliente: {r_un['cliente_nombre']} | Falla: {r_un['problema']}</span>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    with c_btn_take:
                        st.write("")
                        if st.button("📥 Tomar esta Orden", key=f"btn_take_ot_{ot_un_id}", use_container_width=True):
                            ok = claim_unassigned_work_order(ot_un_id, current_user_id, current_username, org_id=org_id)
                            if ok:
                                st.toast(f"✅ ¡Has tomado la orden {r_un['ot_codigo']}!", icon="🔬")
                                st.rerun()
                            else:
                                st.error("⚠️ La orden fue tomada por otro técnico hace unos instantes.")

    # 3. HISTORIAL RESUELTO
    tab_hist_idx = 2 if autoasig_habilitada else 1
    with tabs[tab_hist_idx]:
        df_hist = df_view[~df_view["estado"].isin(ESTADOS_WIP)] if not df_view.empty else pd.DataFrame()
        if df_hist.empty:
            empty_state("Sin historial previo", "Las reparaciones finalizadas se listarán aquí.")
        else:
            cols_show = ["ot_codigo", "cliente_nombre", "marca", "modelo", "problema", "estado", "mano_obra", "total", "fecha_ingreso", "fecha_egreso"]
            st.dataframe(
                df_hist[cols_show],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "ot_codigo": st.column_config.TextColumn("Código OT", width="small"),
                    "cliente_nombre": st.column_config.TextColumn("Cliente", width="medium"),
                    "marca": st.column_config.TextColumn("Marca", width="small"),
                    "modelo": st.column_config.TextColumn("Modelo", width="medium"),
                    "problema": st.column_config.TextColumn("Falla", width="medium"),
                    "estado": st.column_config.TextColumn("Estado Final", width="small"),
                    "mano_obra": st.column_config.NumberColumn("Mano de Obra", format="$%.0f"),
                    "total": st.column_config.NumberColumn("Total", format="$%.0f"),
                    "fecha_ingreso": st.column_config.TextColumn("Ingreso", width="small"),
                    "fecha_egreso": st.column_config.TextColumn("Egreso", width="small"),
                },
            )
