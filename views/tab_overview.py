"""Vista del Panel Ejecutivo y Operativo (Tab 1: Overview en Tiempo Real)."""

from datetime import date
import pandas as pd
import streamlit as st
from charts.overview_charts import (
    build_operational_funnel_chart,
    build_wip_by_tech_chart,
    get_delayed_orders,
)
from components.cards import empty_state, format_currency, format_number, format_pct, metric_card
from core.config import ESTADOS_EXITOSOS, ESTADOS_TERMINADOS, ESTADOS_WIP


def render_tab_overview(df: pd.DataFrame) -> None:
    """Renderiza las métricas ejecutivas, funnel y alertas de órdenes demoradas."""
    if df.empty:
        empty_state("No hay órdenes registradas en la base de datos.")
        return

    # Cálculos ejecutivos para el mes actual y variación vs. mes anterior
    today = date.today()
    mes_actual = today.month
    anio_actual = today.year

    if mes_actual == 1:
        mes_prev = 12
        anio_prev = anio_actual - 1
    else:
        mes_prev = mes_actual - 1
        anio_prev = anio_actual

    df_current_month = df[
        (df["fecha_ingreso_dt"].dt.month == mes_actual)
        & (df["fecha_ingreso_dt"].dt.year == anio_actual)
    ]
    df_prev_month = df[
        (df["fecha_ingreso_dt"].dt.month == mes_prev)
        & (df["fecha_ingreso_dt"].dt.year == anio_prev)
    ]

    # Facturación y Ganancia Neta Mes Actual
    fact_actual = df_current_month["valor_cobrado"].sum()
    fact_prev = df_prev_month["valor_cobrado"].sum()
    fact_delta = ((fact_actual - fact_prev) / fact_prev * 100.0) if fact_prev > 0 else 0.0

    ganancia_actual = df_current_month["margen_neto"].sum()
    ganancia_prev = df_prev_month["margen_neto"].sum()
    ganancia_delta = ((ganancia_actual - ganancia_prev) / ganancia_prev * 100.0) if ganancia_prev > 0 else 0.0

    # Tasa de éxito en reparaciones (Exitosos / Terminados)
    terminados = df[df["estado"].isin(ESTADOS_TERMINADOS)]
    exitosos = df[df["estado"].isin(ESTADOS_EXITOSOS)]
    total_terminados = len(terminados)
    total_exitosos = len(exitosos)
    tasa_exito = (total_exitosos / total_terminados * 100.0) if total_terminados > 0 else 0.0

    # Tiempo promedio de resolución (días)
    lead_times = df["dias_resolucion"].dropna()
    avg_resolution = lead_times.mean() if not lead_times.empty else 0.0

    # Órdenes activas en banco de trabajo (WIP)
    active_wip = len(df[df["estado"].isin(ESTADOS_WIP)])

    # Fila de KPI Cards
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        metric_card(
            title="Facturación (Mes)",
            value=format_currency(fact_actual),
            delta_text=format_pct(fact_delta),
            delta_positive=(fact_delta >= 0),
            glow_color="cyan",
            subtext=f"vs. mes anterior ({format_currency(fact_prev)})",
        )
    with c2:
        metric_card(
            title="Ganancia Neta (Mes)",
            value=format_currency(ganancia_actual),
            delta_text=format_pct(ganancia_delta),
            delta_positive=(ganancia_delta >= 0),
            glow_color="emerald",
            subtext=f"Margen real del taller",
        )
    with c3:
        metric_card(
            title="Tasa de Éxito",
            value=f"{tasa_exito:.1f}%",
            delta_text=f"{total_exitosos}/{total_terminados}",
            delta_positive=(tasa_exito >= 85),
            glow_color="purple",
            subtext="Reparados exitosos / Total terminados",
        )
    with c4:
        metric_card(
            title="Resolución Promedio",
            value=f"{avg_resolution:.1f} días",
            delta_text="Lead Time",
            delta_positive=(avg_resolution <= 3.5),
            glow_color="amber",
            subtext="Desde ingreso hasta entrega",
        )
    with c5:
        metric_card(
            title="Equipos en Banco (WIP)",
            value=str(active_wip),
            delta_text="Órdenes activas",
            delta_positive=None,
            glow_color="rose",
            subtext="En diagnóstico / repuesto / taller",
        )

    st.markdown("<div style='margin-top: 1.25rem;'></div>", unsafe_allow_html=True)

    # Gráficos Operativos (Funnel + Distribución por Técnico)
    col_funnel, col_tech = st.columns([1.2, 1])
    with col_funnel:
        st.plotly_chart(
            build_operational_funnel_chart(df),
            use_container_width=True,
            key="overview_chart_funnel",
        )
    with col_tech:
        st.plotly_chart(
            build_wip_by_tech_chart(df),
            use_container_width=True,
            key="overview_chart_wip_tech",
        )

    # Sección de Alertas Críticas (> 5 días sin cambio de estado en WIP)
    st.markdown(
        """
        <div style="margin-top: 1.5rem; margin-bottom: 0.5rem; display: flex; align-items: center; justify-content: space-between;">
            <div style="font-weight: 700; font-size: 1.05rem; color: #F59E0B; display: flex; align-items: center; gap: 0.4rem;">
                <span>⚠️ Alertas Críticas: Órdenes Demoradas</span>
                <span style="font-size: 0.75rem; background: rgba(245, 158, 11, 0.15); border: 1px solid rgba(245, 158, 11, 0.3); padding: 0.15rem 0.5rem; border-radius: 4px; color: #FBBF24;">
                    > 5 días hábiles sin cambio de estado en banco
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    delayed_df = get_delayed_orders(df, days_threshold=5)
    if delayed_df.empty:
        st.success("✅ Excelente: No hay órdenes demoradas en el banco de trabajo actualmente.")
    else:
        cols_display = [
            "id_orden",
            "dias_en_estado",
            "estado",
            "marca",
            "modelo",
            "categoria_falla",
            "tecnico",
            "cliente_nombre",
            "cliente_telefono",
        ]
        display_table = delayed_df[cols_display].rename(
            columns={
                "id_orden": "Orden",
                "dias_en_estado": "Días Estancada",
                "estado": "Estado Actual",
                "marca": "Marca",
                "modelo": "Modelo",
                "categoria_falla": "Falla Diagnosticada",
                "tecnico": "Técnico a Cargo",
                "cliente_nombre": "Cliente",
                "cliente_telefono": "Contacto",
            }
        )
        st.dataframe(
            display_table,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Días Estancada": st.column_config.NumberColumn(
                    "Días Estancada",
                    help="Días transcurridos desde el último cambio de estado",
                    format="%d días",
                ),
            },
        )
