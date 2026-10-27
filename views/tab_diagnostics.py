"""Vista de Métricas de Dispositivos y Fallas Frecuentes (Tab 3)."""

import pandas as pd
import streamlit as st
from charts.diagnostic_charts import (
    build_failures_sunburst_chart,
    build_pareto_chart,
    build_warranty_return_chart,
)
from components.cards import empty_state, format_number, format_pct, metric_card


def render_tab_diagnostics(df: pd.DataFrame) -> None:
    """Renderiza Sunburst jerárquico, Pareto 80/20 y métricas de garantías."""
    if df.empty:
        empty_state("No hay datos de dispositivos para analizar.")
        return

    # Métricas clave de calidad y hardware
    total_equipos = len(df)
    marcas_distintas = df["marca"].nunique()
    modelos_distintos = df["modelo"].nunique()
    total_garantias = df["es_retorno_garantia"].sum()
    tasa_garantia_global = (total_garantias / total_equipos * 100.0) if total_equipos > 0 else 0.0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card(
            title="Total Dispositivos",
            value=format_number(total_equipos),
            delta_text=f"{marcas_distintas} marcas",
            glow_color="cyan",
            subtext="En base histórica",
        )
    with c2:
        metric_card(
            title="Modelos Reparados",
            value=format_number(modelos_distintos),
            delta_text="Catálogo activo",
            glow_color="purple",
            subtext="Variedad en laboratorio",
        )
    with c3:
        metric_card(
            title="Reingresos por Garantía",
            value=format_number(total_garantias),
            delta_text="Retornos",
            delta_positive=(total_garantias == 0),
            glow_color="amber",
            subtext="Dentro del plazo otorgado",
        )
    with c4:
        metric_card(
            title="Tasa Global de Garantía",
            value=f"{tasa_garantia_global:.1f}%",
            delta_text="Control de Calidad",
            delta_positive=(tasa_garantia_global <= 5.0),
            glow_color="rose" if tasa_garantia_global > 5.0 else "emerald",
            subtext="Objetivo del taller: < 5%",
        )

    st.markdown("<div style='margin-top: 1.25rem;'></div>", unsafe_allow_html=True)

    # Gráfico Sunburst Jerárquico
    st.plotly_chart(
        build_failures_sunburst_chart(df),
        use_container_width=True,
        key="diag_chart_sunburst",
    )

    st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)

    # 2da Fila: Pareto 80/20 y Tasa de Retorno por Categoría
    col_pareto, col_warranty = st.columns(2)
    with col_pareto:
        st.plotly_chart(
            build_pareto_chart(df),
            use_container_width=True,
            key="diag_chart_pareto",
        )
    with col_warranty:
        st.plotly_chart(
            build_warranty_return_chart(df),
            use_container_width=True,
            key="diag_chart_warranty",
        )

    # Ranking de los 8 modelos con más reparaciones
    st.markdown("<h4 style='color: #F3F4F6; margin-top: 1.2rem;'>Top Modelos con Mayor Demanda en el Laboratorio</h4>", unsafe_allow_html=True)
    top_models = (
        df.groupby(["marca", "modelo"])
        .agg(
            total_reparaciones=("id_orden", "count"),
            falla_principal=("categoria_falla", lambda s: s.value_counts().index[0] if not s.empty else "N/A"),
            facturacion_modelo=("valor_cobrado", "sum"),
            margen_modelo=("margen_neto", "sum"),
        )
        .reset_index()
        .sort_values(by="total_reparaciones", ascending=False)
        .head(10)
    )

    st.dataframe(
        top_models.rename(
            columns={
                "marca": "Marca",
                "modelo": "Modelo",
                "total_reparaciones": "Reparaciones",
                "falla_principal": "Falla Más Común",
                "facturacion_modelo": "Facturado ($)",
                "margen_modelo": "Margen Neto ($)",
            }
        ),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Facturado ($)": st.column_config.NumberColumn(format="$%d"),
            "Margen Neto ($)": st.column_config.NumberColumn(format="$%d"),
        },
    )

