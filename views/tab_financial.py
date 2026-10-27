"""Vista de Análisis Financiero y Rentabilidad (Tab 2)."""

import pandas as pd
import streamlit as st
from charts.financial_charts import (
    build_financial_timeline_chart,
    build_profitability_scatter_chart,
    build_ticket_distribution_chart,
)
from components.cards import empty_state, format_currency, format_number, format_pct, metric_card


def render_tab_financial(df: pd.DataFrame) -> None:
    """Renderiza gráficos de facturación, costos, margen y ticket promedio."""
    if df.empty:
        empty_state("No hay datos financieros para el período seleccionado.")
        return

    # Métricas agregadas
    total_facturado = df["valor_cobrado"].sum()
    total_costo = df["costo_repuesto"].sum()
    total_margen = df["margen_neto"].sum()
    margen_global_pct = (total_margen / total_facturado * 100.0) if total_facturado > 0 else 0.0

    valid_tickets = df[df["valor_cobrado"] > 0]["valor_cobrado"]
    ticket_promedio = valid_tickets.mean() if not valid_tickets.empty else 0.0

    # Tarjetas financieras superiores
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card(
            title="Facturación Bruta",
            value=format_currency(total_facturado),
            delta_text=f"{len(df)} reparaciones",
            delta_positive=True,
            glow_color="cyan",
            subtext="Total cobrado acumulado",
        )
    with c2:
        metric_card(
            title="Costo de Repuestos",
            value=format_currency(total_costo),
            delta_text=format_pct((total_costo / total_facturado * 100.0) if total_facturado > 0 else 0),
            delta_positive=None,
            glow_color="rose",
            subtext="% de la facturación en insumos",
        )
    with c3:
        metric_card(
            title="Margen Neto Total",
            value=format_currency(total_margen),
            delta_text=f"{margen_global_pct:.1f}% margen",
            delta_positive=(margen_global_pct >= 40),
            glow_color="emerald",
            subtext="Ganancia operativa neta",
        )
    with c4:
        metric_card(
            title="Ticket Medio por OT",
            value=format_currency(ticket_promedio),
            delta_text="Promedio cobrado",
            delta_positive=None,
            glow_color="purple",
            subtext="Mano de obra + repuesto",
        )

    st.markdown("<div style='margin-top: 1.25rem;'></div>", unsafe_allow_html=True)

    # Control de granularidad de la serie temporal
    col_title, col_freq = st.columns([3, 1])
    with col_freq:
        freq_option = st.selectbox(
            "Agrupación temporal:",
            options=["Semanal", "Mensual", "Diaria"],
            index=0,
            key="financial_select_freq",
        )
    freq_map = {"Semanal": "W", "Mensual": "M", "Diaria": "D"}
    selected_freq = freq_map[freq_option]

    # Gráfico de Serie Temporal
    st.plotly_chart(
        build_financial_timeline_chart(df, freq=selected_freq),
        use_container_width=True,
        key="financial_chart_timeline",
    )

    st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)

    # Gráficos de Rentabilidad y Distribución de Ticket
    col_matrix, col_ticket = st.columns([1.2, 1])
    with col_matrix:
        st.plotly_chart(
            build_profitability_scatter_chart(df),
            use_container_width=True,
            key="financial_chart_scatter",
        )
    with col_ticket:
        st.plotly_chart(
            build_ticket_distribution_chart(df),
            use_container_width=True,
            key="financial_chart_ticket_hist",
        )

    # Tabla resumen de rentabilidad por categoría
    st.markdown("<h4 style='color: #F3F4F6; margin-top: 1.2rem;'>Desglose de Rentabilidad por Categoría de Servicio</h4>", unsafe_allow_html=True)
    summary_df = (
        df.groupby("categoria_falla")
        .agg(
            ordenes=("id_orden", "count"),
            facturado=("valor_cobrado", "sum"),
            costo=("costo_repuesto", "sum"),
            margen=("margen_neto", "sum"),
            margen_prom=("margen_neto", "mean"),
        )
        .reset_index()
    )
    summary_df["margen_pct"] = summary_df.apply(
        lambda r: (r["margen"] / r["facturado"] * 100.0) if r["facturado"] > 0 else 0.0,
        axis=1,
    )
    summary_df = summary_df.sort_values(by="margen", ascending=False)

    st.dataframe(
        summary_df.rename(
            columns={
                "categoria_falla": "Categoría de Falla",
                "ordenes": "Cant. OTs",
                "facturado": "Facturado ($)",
                "costo": "Costo Insumos ($)",
                "margen": "Margen Neto ($)",
                "margen_prom": "Margen Prom / OT ($)",
                "margen_pct": "% Margen",
            }
        ),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Facturado ($)": st.column_config.NumberColumn(format="$%d"),
            "Costo Insumos ($)": st.column_config.NumberColumn(format="$%d"),
            "Margen Neto ($)": st.column_config.NumberColumn(format="$%d"),
            "Margen Prom / OT ($)": st.column_config.NumberColumn(format="$%d"),
            "% Margen": st.column_config.ProgressColumn(
                "% Margen",
                format="%.1f%%",
                min_value=0,
                max_value=100,
            ),
        },
    )

