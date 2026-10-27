"""Panel Individual y Banco de Trabajo del Técnico (Técnico Workspace)."""

from datetime import date
import pandas as pd
import plotly.express as px
import streamlit as st
from auth import get_all_technicians, get_available_technicians
from charts.theme import apply_chart_theme
from components.cards import empty_state, format_currency, format_number, format_pct, metric_card
from core.config import (
    CATEGORIAS_FALLA,
    ESTADOS_EXITOSOS,
    ESTADOS_ORDEN,
    ESTADOS_TERMINADOS,
    ESTADOS_WIP,
    GARANTIAS_DIAS,
    MARCAS,
    MODELOS_POR_MARCA,
    TECNICOS,
)
from core.db import (
    get_next_order_id,
    insert_order,
    reassign_order_technician,
    update_order_status,
)


def render_tecnico_workspace(df_all: pd.DataFrame, current_tech_name: str) -> None:
    """Renderiza el espacio de trabajo exclusivo para el técnico autenticado."""
    # Filtrar únicamente las órdenes del técnico actual
    df_tech = df_all[df_all["tecnico"] == current_tech_name].copy() if not df_all.empty else pd.DataFrame()

    # Header del Técnico
    wip_count = len(df_tech[df_tech["estado"].isin(ESTADOS_WIP)]) if not df_tech.empty else 0
    total_tech_orders = len(df_tech) if not df_tech.empty else 0

    st.markdown(
        f"""
        <div class="tech-header" style="border-left-color: #8B5CF6;">
            <div>
                <div class="tech-header-title">
                    <span>🔬 BANCO DE TRABAJO</span>
                    <span class="tech-header-badge" style="color: #A78BFA; background: rgba(139, 92, 246, 0.15); border-color: rgba(139, 92, 246, 0.4);">
                        Técnico: {current_tech_name}
                    </span>
                </div>
                <div class="tech-header-sub">
                    Gestión operativa de reparaciones asignadas, actualización de estados y trazabilidad de banco
                </div>
            </div>
            <div style="text-align: right; display: flex; gap: 1rem; align-items: center;">
                <div style="background: rgba(139, 92, 246, 0.15); border: 1px solid rgba(139, 92, 246, 0.35); padding: 0.35rem 0.75rem; border-radius: 8px;">
                    <span style="color: #9CA3AF; font-size: 0.72rem; text-transform: uppercase;">En Mi Banco</span><br>
                    <b style="color: #A78BFA; font-size: 1.1rem;">{wip_count} equipos</b>
                </div>
                <div style="background: rgba(0, 240, 255, 0.1); border: 1px solid rgba(0, 240, 255, 0.3); padding: 0.35rem 0.75rem; border-radius: 8px;">
                    <span style="color: #9CA3AF; font-size: 0.72rem; text-transform: uppercase;">Total Asignadas</span><br>
                    <b style="color: #00F0FF; font-size: 1.1rem;">{total_tech_orders} OTs</b>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Sub-pestañas del técnico
    tab_wip, tab_kpi, tab_nueva = st.tabs(
        [
            "⚡ Mi Banco Activo (Kanban WIP)",
            "📈 Mi Rendimiento Personal",
            "➕ Cargar Nueva Orden (Alta Rápida)",
        ]
    )

    with tab_wip:
        render_tecnico_wip_kanban(df_tech, current_tech_name)

    with tab_kpi:
        render_tecnico_performance(df_tech, current_tech_name)

    with tab_nueva:
        render_tecnico_quick_order(current_tech_name)


def render_tecnico_wip_kanban(df_tech: pd.DataFrame, current_tech_name: str) -> None:
    """Renderiza las órdenes activas en el banco de trabajo y formulario de actualización rápida."""
    st.markdown("<h4 style='color: #F3F4F6;'>Órdenes Activas en Banco de Trabajo</h4>", unsafe_allow_html=True)

    if df_tech.empty:
        empty_state(f"No tenés órdenes asignadas actualmente, {current_tech_name}.")
        return

    wip_df = df_tech[df_tech["estado"].isin(ESTADOS_WIP)].copy()
    if wip_df.empty:
        st.success("🎉 ¡Excelente trabajo! No tenés equipos pendientes en banco en este momento.")
        return

    # Visualización estilo Kanban segmentado
    stages = [
        ("Ingresado", "#3B82F6"),
        ("En Diagnóstico", "#8B5CF6"),
        ("Esperando Repuesto", "#F59E0B"),
        ("En Reparación", "#00F0FF"),
    ]

    cols = st.columns(len(stages))
    for i, (stage_name, color_hex) in enumerate(stages):
        with cols[i]:
            stage_orders = wip_df[wip_df["estado"] == stage_name]
            st.markdown(
                f"""
                <div style="background: rgba(17, 24, 39, 0.9); border: 1px solid #1F2937; border-top: 3px solid {color_hex}; border-radius: 8px; padding: 0.6rem 0.8rem; margin-bottom: 0.75rem; display: flex; justify-content: space-between; align-items: center;">
                    <b style="color: #F3F4F6; font-size: 0.85rem;">{stage_name}</b>
                    <span style="background: rgba(255,255,255,0.1); color: #FFF; font-size: 0.75rem; padding: 0.15rem 0.45rem; border-radius: 10px; font-weight: 700;">{len(stage_orders)}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if stage_orders.empty:
                st.markdown("<div style='color: #4B5563; font-size: 0.75rem; text-align: center; padding: 1rem;'>Sin equipos</div>", unsafe_allow_html=True)
            else:
                for _, order in stage_orders.iterrows():
                    ot_id = order["id_orden"]
                    dias_banco = int(order.get("dias_en_estado", 0))
                    alerta_demora = dias_banco >= 5
                    border_glow = "border-color: #F59E0B;" if alerta_demora else "border-color: #1F2937;"

                    st.markdown(
                        f"""
                        <div style="background: #111827; border: 1px solid #374151; {border_glow} border-radius: 8px; padding: 0.75rem; margin-bottom: 0.75rem;">
                            <div style="display: flex; justify-content: space-between; align-items: baseline;">
                                <b style="color: #00F0FF; font-size: 0.9rem;">{ot_id}</b>
                                <span style="font-size: 0.72rem; color: {'#F59E0B' if alerta_demora else '#9CA3AF'}; font-weight: 600;">⏱ {dias_banco} d en estado</span>
                            </div>
                            <div style="color: #F9FAFB; font-weight: 600; font-size: 0.85rem; margin-top: 0.2rem;">
                                {order['marca']} {order['modelo']}
                            </div>
                            <div style="color: #9CA3AF; font-size: 0.75rem; margin-top: 0.15rem;">
                                🔧 {order['categoria_falla']}
                            </div>
                            {f'<div style="color: #60A5FA; font-size: 0.72rem; margin-top: 0.2rem;">📦 Guía: {order.get("guia_repuesto")}</div>' if order.get("guia_repuesto") else ''}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

    # Panel de Acción Rápida: Actualización de Estado en 1 Clic
    st.markdown("<div style='border-top: 1px solid #1F2937; margin: 1.5rem 0;'></div>", unsafe_allow_html=True)
    st.markdown("<b style='color: #00F0FF; font-size: 1rem;'>⚡ Panel de Acción Rápida: Actualizar Orden en Banco</b>", unsafe_allow_html=True)

    lista_wip_ids = wip_df["id_orden"].tolist()
    col_sel, col_estado, col_btn = st.columns([1.2, 1.2, 1])
    with col_sel:
        orden_a_editar = st.selectbox(
            "Seleccionar OT de tu Banco:",
            options=lista_wip_ids,
            key="tech_sel_orden_edit",
        )
    with col_estado:
        nuevo_estado_sel = st.selectbox(
            "Nuevo Estado:",
            options=ESTADOS_ORDEN,
            index=3,  # Por defecto "En Reparación"
            key="tech_sel_nuevo_estado",
        )

    # Datos adicionales de la orden seleccionada
    order_data = wip_df[wip_df["id_orden"] == orden_a_editar].iloc[0]

    with st.expander(f"📝 Actualizar Diagnóstico, Notas de Microelectrónica y Repuesto ({orden_a_editar})", expanded=True):
        c_notes, c_repuesto = st.columns(2)
        with c_notes:
            notas_input = st.text_area(
                "Notas de Banco / Microelectrónica:",
                value=str(order_data.get("notas_tecnicas", "") or order_data.get("diagnostico", "")),
                placeholder="Ej: Se aisló consumo en VDD_MAIN. Soldado capacitor C302. Consumo normal en 1.1A.",
                key=f"tech_txt_notas_{orden_a_editar}",
            )
        with c_repuesto:
            prov_input = st.text_input(
                "Proveedor de Repuesto (si aplica):",
                value=str(order_data.get("proveedor_repuesto", "") or ""),
                placeholder="Ej: FixParts / MercadoLibre",
                key=f"tech_in_prov_{orden_a_editar}",
            )
            guia_input = st.text_input(
                "Nro de Guía / Tracking de Envío:",
                value=str(order_data.get("guia_repuesto", "") or ""),
                placeholder="Ej: OCA-84920194 / Andreani",
                key=f"tech_in_guia_{orden_a_editar}",
            )

        col_act, col_reassign = st.columns([1, 1])
        with col_act:
            if st.button("💾 Actualizar Estado y Notas", type="primary", use_container_width=True, key=f"btn_act_orden_{orden_a_editar}"):
                update_order_status(
                    id_orden=orden_a_editar,
                    nuevo_estado=nuevo_estado_sel,
                    notas_tecnicas=notas_input.strip(),
                    proveedor_repuesto=prov_input.strip(),
                    guia_repuesto=guia_input.strip(),
                )
                st.toast(f"¡Orden {orden_a_editar} actualizada a '{nuevo_estado_sel}'!", icon="✅")
                st.rerun()

        with col_reassign:
            otros_tecnicos = [t for t in get_available_technicians() if t != current_tech_name] + ["Otro técnico (escribir manual)..."]
            col_t_sel, col_t_btn = st.columns([1.5, 1])
            with col_t_sel:
                tec_dest_sel = st.selectbox("Derivar a Colega:", options=otros_tecnicos, key=f"reassign_sel_{orden_a_editar}")
                if tec_dest_sel == "Otro técnico (escribir manual)...":
                    tec_dest = st.text_input("Nombre del Colega:", placeholder="Ej: Lucas M.", key=f"reassign_txt_{orden_a_editar}")
                else:
                    tec_dest = tec_dest_sel
            with col_t_btn:
                st.markdown("<div style='margin-top: 1.7rem;'></div>", unsafe_allow_html=True)
                if st.button("↪ Derivar", key=f"btn_derivar_{orden_a_editar}", use_container_width=True):
                    if tec_dest and tec_dest.strip():
                        reassign_order_technician(orden_a_editar, tec_dest.strip())
                        st.toast(f"Orden {orden_a_editar} derivada a {tec_dest.strip()}.", icon="↪")
                        st.rerun()
                    else:
                        st.error("Ingresá un técnico de destino válido.")


def render_tecnico_performance(df_tech: pd.DataFrame, current_tech_name: str) -> None:
    """Métricas y KPIs individuales de rendimiento del técnico."""
    st.markdown("<h4 style='color: #F3F4F6;'>Métricas Personales de Rendimiento</h4>", unsafe_allow_html=True)

    if df_tech.empty:
        empty_state(f"Aún no tenés datos históricos de reparación, {current_tech_name}.")
        return

    today = date.today()
    mes_actual = today.month
    anio_actual = today.year

    df_mes = df_tech[
        (df_tech["fecha_ingreso_dt"].dt.month == mes_actual)
        & (df_tech["fecha_ingreso_dt"].dt.year == anio_actual)
    ]

    # Reparaciones completadas este mes
    terminadas_mes = df_mes[df_mes["estado"].isin(ESTADOS_TERMINADOS)]
    exitosas_mes = df_mes[df_mes["estado"].isin(ESTADOS_EXITOSOS)]
    completadas_mes_count = len(exitosas_mes)

    # Tasa de efectividad personal
    total_diag = len(terminadas_mes)
    tasa_efectividad = (completadas_mes_count / total_diag * 100.0) if total_diag > 0 else 0.0

    # Tiempo promedio de resolución
    lead_times = df_tech["dias_resolucion"].dropna()
    avg_dias = lead_times.mean() if not lead_times.empty else 0.0

    # Retorno por garantía de sus propias órdenes
    total_tech_all = len(df_tech)
    garantias_tech = df_tech["es_retorno_garantia"].sum()
    tasa_garantia_propia = (garantias_tech / total_tech_all * 100.0) if total_tech_all > 0 else 0.0

    # Mano de obra cobrada en sus reparaciones exitosas
    facturacion_mano_obra = exitosas_mes["valor_cobrado"].sum()

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        metric_card(
            title="Completadas (Mes)",
            value=format_number(completadas_mes_count),
            delta_text=f"{len(df_mes)} ingresadas",
            delta_positive=True,
            glow_color="emerald",
            subtext="Reparaciones entregadas",
        )
    with c2:
        metric_card(
            title="Efectividad Personal",
            value=f"{tasa_efectividad:.1f}%",
            delta_text=f"{completadas_mes_count}/{total_diag}",
            delta_positive=(tasa_efectividad >= 80),
            glow_color="purple",
            subtext="Éxito sobre diagnosticados",
        )
    with c3:
        metric_card(
            title="Resolución Promedio",
            value=f"{avg_dias:.1f} días",
            delta_text="Lead Time",
            delta_positive=(avg_dias <= 4.0),
            glow_color="cyan",
            subtext="Desde ingreso a entrega",
        )
    with c4:
        metric_card(
            title="Tasa de Garantía",
            value=f"{tasa_garantia_propia:.1f}%",
            delta_text=f"{int(garantias_tech)} retornos",
            delta_positive=(tasa_garantia_propia <= 5.0),
            glow_color="rose" if tasa_garantia_propia > 5.0 else "emerald",
            subtext="Calidad técnica personal",
        )
    with c5:
        metric_card(
            title="Mano de Obra Facturada",
            value=format_currency(facturacion_mano_obra),
            delta_text="Mes actual",
            glow_color="amber",
            subtext="Generado en tu banco",
        )

    st.markdown("<div style='margin-top: 1.25rem;'></div>", unsafe_allow_html=True)

    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        # Frecuencia de tipos de reparación resueltos por este técnico
        counts_falla = df_tech["categoria_falla"].value_counts().reset_index()
        counts_falla.columns = ["Falla", "Cantidad"]
        counts_falla["Falla_corta"] = counts_falla["Falla"].apply(lambda s: s.split("(")[0].strip())

        fig_fallas = px.bar(
            counts_falla,
            x="Cantidad",
            y="Falla_corta",
            orientation="h",
            color="Cantidad",
            color_continuous_scale=[[0, "#3B82F6"], [1, "#00F0FF"]],
        )
        fig_fallas.update_layout(title="Especialidades Más Frecuentes en tu Banco", yaxis=dict(title=""))
        st.plotly_chart(apply_chart_theme(fig_fallas, height=320), use_container_width=True, key="tech_chart_fallas")

    with col_chart2:
        # Historial de reparaciones entregadas por mes
        df_entregados = df_tech[df_tech["estado"].isin(ESTADOS_EXITOSOS)].copy()
        if not df_entregados.empty and "fecha_ingreso_dt" in df_entregados:
            df_entregados["mes_str"] = df_entregados["fecha_ingreso_dt"].dt.to_period("M").astype(str)
            monthly_rep = df_entregados.groupby("mes_str").size().reset_index(name="Reparaciones")
            fig_month = px.line(
                monthly_rep,
                x="mes_str",
                y="Reparaciones",
                markers=True,
                line_shape="linear",
            )
            fig_month.update_traces(line_color="#10B981", marker=dict(size=8, color="#00F0FF"))
            fig_month.update_layout(title="Evolución Mensual de Reparaciones Exitosas", xaxis=dict(title="Mes"))
            st.plotly_chart(apply_chart_theme(fig_month, height=320), use_container_width=True, key="tech_chart_monthly")
        else:
            empty_state("Sin historial mensual suficiente.")


def render_tecnico_quick_order(current_tech_name: str) -> None:
    """Formulario de alta rápida donde el técnico se asigna por defecto pero puede derivar."""
    st.markdown("<h4 style='color: #F3F4F6;'>Alta Rápida de Orden de Trabajo</h4>", unsafe_allow_html=True)

    next_id = get_next_order_id()
    todos_tecnicos = get_available_technicians()
    if current_tech_name not in todos_tecnicos:
        todos_tecnicos = [current_tech_name] + todos_tecnicos
    opciones_tec = todos_tecnicos + ["Otro técnico (escribir manual)..."]

    index_default_tech = opciones_tec.index(current_tech_name) if current_tech_name in opciones_tec else 0

    with st.container():
        st.markdown(
            f"""
            <div style="background: rgba(139, 92, 246, 0.1); border-left: 3px solid #8B5CF6; padding: 0.6rem 1rem; border-radius: 6px; margin-bottom: 1.25rem;">
                <b style="color: #A78BFA;">Registrar OT en Banco:</b> <span class="tech-mono" style="color: #FFF; font-weight: 700;">{next_id}</span>
                <span style="color: #9CA3AF; font-size: 0.8rem; margin-left: 1rem;">Técnico asignado por defecto: <b>{current_tech_name}</b></span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        c1, c2, c3 = st.columns([1, 1.2, 1.2])
        with c1:
            ot_id = st.text_input("ID Orden:", value=next_id, key="tech_form_id")
        with c2:
            fecha_in = st.date_input("Fecha Ingreso:", value=date.today(), key="tech_form_date")
        with c3:
            tecnico_sel = st.selectbox("Técnico a Cargo:", options=opciones_tec, index=index_default_tech, key="tech_form_tecnico")
            if tecnico_sel == "Otro técnico (escribir manual)...":
                tecnico_final = st.text_input("Especificar Nombre del Técnico:", placeholder="Ej: Juan Pérez", key="tech_form_tec_custom")
            else:
                tecnico_final = tecnico_sel

        st.markdown("<div style='border-top: 1px solid #1F2937; margin: 0.6rem 0;'></div>", unsafe_allow_html=True)

        c_m1, c_m2, c_cli, c_tel = st.columns(4)
        with c_m1:
            marca_sel = st.selectbox("Marca:", options=MARCAS + ["Otra marca..."], index=0, key="tech_form_marca")
            marca = st.text_input("Especificar Marca:", key="tech_form_marca_custom") if marca_sel == "Otra marca..." else marca_sel
        with c_m2:
            modelos_disp = MODELOS_POR_MARCA.get(marca_sel, []) + ["Otro modelo..."]
            modelo_sel = st.selectbox("Modelo:", options=modelos_disp, index=0, key="tech_form_modelo")
            modelo = st.text_input("Especificar Modelo:", key="tech_form_modelo_custom") if modelo_sel == "Otro modelo..." else modelo_sel
        with c_cli:
            cliente = st.text_input("Cliente:", placeholder="Nombre del cliente", key="tech_form_cli")
        with c_tel:
            telefono = st.text_input("Teléfono:", placeholder="+54 9 11 ...", key="tech_form_tel")

        c_imei, c_falla, c_est = st.columns([1.2, 1.8, 1.2])
        with c_imei:
            imei = st.text_input("IMEI:", placeholder="15 dígitos", key="tech_form_imei")
        with c_falla:
            categoria_falla = st.selectbox("Categoría de Falla:", options=CATEGORIAS_FALLA, key="tech_form_falla")
        with c_est:
            estado = st.selectbox("Estado:", options=ESTADOS_ORDEN, index=0, key="tech_form_estado")

        diag = st.text_area("Diagnóstico Técnico & Mediciones Iniciales:", placeholder="Ej: No enciende, consumo fijo 70mA. VDD_MAIN ok.", key="tech_form_diag")

        c_cost, c_cobr, c_gar = st.columns(3)
        with c_cost:
            costo = st.number_input("Costo Repuesto ($):", min_value=0.0, value=12000.0, step=1000.0, key="tech_form_costo")
        with c_cobr:
            cobrado = st.number_input("Valor Presupuesto / Cobrado ($):", min_value=0.0, value=38000.0, step=1000.0, key="tech_form_cobrado")
        with c_gar:
            garantia = st.selectbox("Garantía (Días):", options=GARANTIAS_DIAS, index=1, key="tech_form_gar")

        btn_save = st.button("💾 Registrar Orden en mi Banco", type="primary", use_container_width=True, key="tech_form_btn_save")

        if btn_save:
            if not ot_id.strip() or not marca.strip() or not modelo.strip() or not tecnico_final or not tecnico_final.strip():
                st.error("Completá los campos obligatorios (ID, Marca, Modelo y Técnico).")
            else:
                data = {
                    "id_orden": ot_id.strip().upper(),
                    "fecha_ingreso": str(fecha_in),
                    "fecha_egreso": "",
                    "fecha_ultimo_estado": str(date.today()),
                    "cliente_nombre": cliente.strip(),
                    "cliente_telefono": telefono.strip(),
                    "imei": imei.strip(),
                    "marca": marca.strip(),
                    "modelo": modelo.strip(),
                    "categoria_falla": categoria_falla,
                    "diagnostico": diag.strip(),
                    "costo_repuesto": costo,
                    "valor_cobrado": cobrado,
                    "estado": estado,
                    "tecnico": tecnico_final.strip(),
                    "garantia_dias": garantia,
                    "es_retorno_garantia": 0,
                    "notas_tecnicas": diag.strip(),
                }
                insert_order(data)
                st.toast(f"✅ ¡Orden {ot_id} registrada con éxito!", icon="⚡")
                st.rerun()

