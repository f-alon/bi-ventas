"""Módulo 4.3: Reportes Ejecutivos, BI, Estado de Resultados (P&L) y Exportación Contable (ERP LABFIX)."""

from datetime import date, timedelta
import io
import pandas as pd
import streamlit as st
from charts.erp_charts import (
    build_pareto_chart,
    build_technician_performance,
    build_weekly_revenue_trend,
)
from components.cards import empty_state, format_currency, format_number, format_pct, metric_card
from database import get_connection, load_orders_df, load_pnl_statement, load_stock_df


def render_reportes_view() -> None:
    """Renderiza el tablero analítico avanzado de Business Intelligence, P&L y exportador contable."""
    st.markdown(
        """
        <div style="margin-bottom: 1.25rem;">
            <h2 style="color: #FFFFFF; font-weight: 800; margin: 0; font-size: 1.6rem; letter-spacing: -0.02em;">
                📈 Reportes Financieros, Estado de Resultados & BI
            </h2>
            <span style="color: #9CA3AF; font-size: 0.85rem;">
                P&L con CMV histórico, análisis de Pareto 80/20, productividad de técnicos y libros contables
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    df_orders = load_orders_df()
    df_stock = load_stock_df()
    conn = get_connection()

    t_pnl, t_charts, t_export = st.tabs([
        "📑 Estado de Resultados (P&L)",
        "📊 Gráficos Analíticos & Pareto",
        "📥 Centro de Exportación (Excel / CSV)",
    ])

    # =========================================================================
    # TAB 1: ESTADO DE RESULTADOS (P&L)
    # =========================================================================
    with t_pnl:
        c_p1, c_p2 = st.columns([1, 2])
        with c_p1:
            filtro_periodo = st.selectbox(
                "Período de Análisis:",
                ["Todo el Histórico", "Este Mes", "Mes Anterior", "Rango Personalizado"],
                key="pnl_periodo_select",
            )

        start_d_str, end_d_str = "", ""
        today = date.today()
        if filtro_periodo == "Este Mes":
            start_d_str = today.replace(day=1).isoformat()
            end_d_str = today.isoformat()
        elif filtro_periodo == "Mes Anterior":
            first_this_month = today.replace(day=1)
            last_prev_month = first_this_month - timedelta(days=1)
            first_prev_month = last_prev_month.replace(day=1)
            start_d_str = first_prev_month.isoformat()
            end_d_str = last_prev_month.isoformat()
        elif filtro_periodo == "Rango Personalizado":
            with c_p2:
                rango_fechas = st.date_input(
                    "Seleccionar Rango de Fechas:",
                    value=(today - timedelta(days=30), today),
                    key="pnl_date_range",
                )
                if isinstance(rango_fechas, (tuple, list)) and len(rango_fechas) == 2:
                    start_d_str = rango_fechas[0].isoformat()
                    end_d_str = rango_fechas[1].isoformat()

        pnl = load_pnl_statement(org_id=1, start_date=start_d_str, end_date=end_d_str)

        # KPIs Principales
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            metric_card(
                "Ingresos Totales",
                format_currency(pnl["ingresos_totales"]),
                glow_color="cyan",
                subtext=f"Taller: {format_currency(pnl['ingresos_taller'])} | POS: {format_currency(pnl['ingresos_pos'])}",
            )
        with k2:
            metric_card(
                "Costo de Insumos (CMV)",
                format_currency(pnl["cmv_total"]),
                glow_color="red" if pnl["cmv_total"] > 0 else "neutral",
                subtext="Snapshot histórico real",
            )
        with k3:
            metric_card(
                "Ganancia Bruta",
                format_currency(pnl["ganancia_bruta"]),
                glow_color="green",
                subtext=f"Margen Bruto: {format_pct(pnl['margen_bruto_pct'], show_sign=False)}",
            )
        with k4:
            glow_net = "green" if pnl["ganancia_neta"] >= 0 else "red"
            metric_card(
                "Ganancia Neta Real",
                format_currency(pnl["ganancia_neta"]),
                glow_color=glow_net,
                subtext=f"Margen Neto: {format_pct(pnl['margen_neto_pct'], show_sign=False)}",
            )

        st.markdown("<hr style='border-color: #1F2937; margin: 1.25rem 0;'>", unsafe_allow_html=True)

        col_tabla, col_gastos = st.columns([3, 2])

        with col_tabla:
            st.markdown("<b style='color: #00F0FF; font-size: 1rem;'>Cascada de Ingresos y Egresos (P&L Formal)</b>", unsafe_allow_html=True)

            pnl_rows = [
                ("1. Facturación Taller (Mano de Obra y Repuestos OTs)", pnl["ingresos_taller"], "#FFFFFF", False),
                ("2. Ventas Mostrador (Punto de Venta POS)", pnl["ingresos_pos"], "#FFFFFF", False),
                ("(=) INGRESOS OPERATIVOS BRUTOS", pnl["ingresos_totales"], "#00F0FF", True),
                ("(-) Costo Repuestos Insumidos en OTs (CMV Snapshot)", -pnl["cmv_taller"], "#F43F5E", False),
                ("(-) Costo Mercaderías Vendidas Mostrador (CMV Snapshot)", -pnl["cmv_pos"], "#F43F5E", False),
                ("(=) GANANCIA BRUTA OPERATIVA", pnl["ganancia_bruta"], "#10B981", True),
                ("(-) Gastos Operativos Fijos (Alquiler, Servicios, Sueldos)", -pnl["gastos_fijos"], "#F59E0B", False),
                ("(-) Gastos Operativos Variables (Insumos, Marketing, etc.)", -pnl["gastos_variables"], "#F59E0B", False),
                ("(=) RESULTADO NETO DEL EJERCICIO", pnl["ganancia_neta"], "#10B981" if pnl["ganancia_neta"] >= 0 else "#F43F5E", True),
            ]

            html_table = """
            <table style="width: 100%; border-collapse: collapse; font-size: 0.88rem; margin-top: 0.5rem; background: #111827; border-radius: 8px; overflow: hidden; border: 1px solid #1F2937;">
                <thead>
                    <tr style="background: #1F2937; color: #9CA3AF; text-align: left;">
                        <th style="padding: 10px 14px;">Concepto Financiero</th>
                        <th style="padding: 10px 14px; text-align: right;">Importe</th>
                    </tr>
                </thead>
                <tbody>
            """
            for concepto, monto, color, is_bold in pnl_rows:
                weight = "700" if is_bold else "400"
                bg_style = "background: rgba(31, 41, 55, 0.4);" if is_bold else ""
                html_table += f"""
                    <tr style="border-bottom: 1px solid #1F2937; {bg_style}">
                        <td style="padding: 9px 14px; color: {color}; font-weight: {weight};">{concepto}</td>
                        <td style="padding: 9px 14px; text-align: right; color: {color}; font-weight: {weight}; font-family: monospace;">{format_currency(monto)}</td>
                    </tr>
                """
            html_table += "</tbody></table>"
            st.markdown(html_table, unsafe_allow_html=True)

        with col_gastos:
            st.markdown("<b style='color: #F59E0B; font-size: 1rem;'>Desglose de Gastos Deducibles</b>", unsafe_allow_html=True)
            desglose = pnl.get("gastos_desglose", [])
            if not desglose:
                empty_state("Sin gastos registrados", "No hay egresos que afecten el resultado en el período seleccionado.")
            else:
                df_g = pd.DataFrame(desglose)
                for _, r in df_g.iterrows():
                    color_tag = "#F43F5E" if r["tipo"] == "FIJO" else "#00F0FF"
                    st.markdown(
                        f"""
                        <div style="background: #111827; border: 1px solid #1F2937; padding: 8px 12px; border-radius: 6px; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <span style="font-weight: 600; color: #E5E7EB; font-size: 0.85rem;">{r['categoria']}</span>
                                <span style="background: rgba(255,255,255,0.06); color: {color_tag}; font-size: 0.7rem; padding: 2px 6px; border-radius: 4px; margin-left: 6px;">{r['tipo']}</span>
                            </div>
                            <span style="font-family: monospace; font-weight: 700; color: #F59E0B; font-size: 0.88rem;">
                                {format_currency(r['monto'])}
                            </span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

    # =========================================================================
    # TAB 2: GRÁFICOS ANALÍTICOS & PARETO
    # =========================================================================
    with t_charts:
        if df_orders.empty:
            empty_state("No hay suficientes datos para generar gráficos BI.", "Se requieren órdenes de servicio finalizadas para calcular márgenes y tendencias.")
        else:
            c_left, c_right = st.columns([1, 1])
            with c_left:
                st.markdown("<b style='color: #00F0FF; font-size: 0.95rem;'>📈 Evolución de Facturación Semanal</b>", unsafe_allow_html=True)
                fig_trend = build_weekly_revenue_trend(df_orders)
                st.plotly_chart(fig_trend, use_container_width=True)

            with c_right:
                st.markdown("<b style='color: #10B981; font-size: 0.95rem;'>🔬 Pareto 80/20 de Fallas Más Frecuentes</b>", unsafe_allow_html=True)
                fig_pareto = build_pareto_chart(df_orders)
                st.plotly_chart(fig_pareto, use_container_width=True)

            st.markdown("<hr style='border-color: #1F2937; margin: 1rem 0;'>", unsafe_allow_html=True)
            st.markdown("<b style='color: #F59E0B; font-size: 0.95rem;'>👨‍🔧 Desempeño y Carga por Técnico</b>", unsafe_allow_html=True)
            fig_tech = build_technician_performance(df_orders)
            st.plotly_chart(fig_tech, use_container_width=True)

    # =========================================================================
    # TAB 3: CENTRO DE EXPORTACIÓN (EXCEL / CSV)
    # =========================================================================
    with t_export:
        st.markdown("<b style='color: #00F0FF; font-size: 1rem;'>Exportador de Reportes Contables y Auditoría</b>", unsafe_allow_html=True)
        st.markdown("<span style='color: #9CA3AF; font-size: 0.85rem;'>Descarga los libros completos en formato CSV o libro Excel multipestaña para contabilidad externa.</span>", unsafe_allow_html=True)

        output_excel = io.BytesIO()
        with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
            # Hoja 1: Estado de Resultados
            df_pnl_export = pd.DataFrame([
                {"Concepto": "Facturación Taller (OTs)", "Monto": pnl["ingresos_taller"]},
                {"Concepto": "Ventas Mostrador (POS)", "Monto": pnl["ingresos_pos"]},
                {"Concepto": "Ingresos Operativos Totales", "Monto": pnl["ingresos_totales"]},
                {"Concepto": "CMV Repuestos Taller", "Monto": pnl["cmv_taller"]},
                {"Concepto": "CMV Ventas POS", "Monto": pnl["cmv_pos"]},
                {"Concepto": "Ganancia Bruta", "Monto": pnl["ganancia_bruta"]},
                {"Concepto": "Margen Bruto (%)", "Monto": pnl["margen_bruto_pct"]},
                {"Concepto": "Gastos Operativos Fijos", "Monto": pnl["gastos_fijos"]},
                {"Concepto": "Gastos Operativos Variables", "Monto": pnl["gastos_variables"]},
                {"Concepto": "Total Gastos Deducibles", "Monto": pnl["total_gastos_operativos"]},
                {"Concepto": "Ganancia Neta Real", "Monto": pnl["ganancia_neta"]},
                {"Concepto": "Margen Neto (%)", "Monto": pnl["margen_neto_pct"]},
            ])
            df_pnl_export.to_excel(writer, sheet_name="Estado_Resultados_PnL", index=False)

            # Hoja 2: Órdenes de Servicio
            if not df_orders.empty:
                df_orders_export = df_orders.drop(columns=["fecha_ingreso_dt", "fecha_egreso_dt", "fecha_ultimo_dt"], errors="ignore")
                df_orders_export.to_excel(writer, sheet_name="Ordenes_Servicio", index=False)

            # Hoja 3: Ventas POS
            df_ventas_export = pd.read_sql_query("SELECT * FROM ventas", conn)
            df_ventas_export.to_excel(writer, sheet_name="Ventas_Mostrador", index=False)

            # Hoja 4: Stock
            if not df_stock.empty:
                df_stock.to_excel(writer, sheet_name="Inventario_Stock", index=False)

            # Hoja 5: Movimientos de Caja
            df_caja_export = pd.read_sql_query("SELECT * FROM caja_movimientos", conn)
            df_caja_export.to_excel(writer, sheet_name="Caja_Movimientos", index=False)

        excel_data = output_excel.getvalue()

        c_exp1, c_exp2 = st.columns(2)
        with c_exp1:
            st.download_button(
                label="📥 Descargar Libro Excel Completo (.xlsx)",
                data=excel_data,
                file_name=f"Reporte_Integral_LABFIX_{date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="bi_download_excel_btn",
            )
        with c_exp2:
            csv_orders = df_orders.to_csv(index=False).encode("utf-8") if not df_orders.empty else b""
            st.download_button(
                label="📥 Descargar Órdenes en CSV (.csv)",
                data=csv_orders,
                file_name=f"Ordenes_Servicio_{date.today()}.csv",
                mime="text/csv",
                use_container_width=True,
                key="bi_download_csv_btn",
            )
