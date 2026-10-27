"""Gráficos de diagnóstico técnico, fallas frecuentes, Pareto y garantías (Tab 3)."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from charts.theme import apply_chart_theme
from core.config import COLORS


def build_failures_sunburst_chart(df: pd.DataFrame) -> go.Figure:
    """Sunburst / Treemap jerárquico: Marca -> Modelo -> Tipo de Falla."""
    if df.empty:
        return apply_chart_theme(go.Figure())

    # Agrupamos por jerarquía
    grouped = (
        df.groupby(["marca", "modelo", "categoria_falla"])
        .size()
        .reset_index(name="cantidad")
    )

    fig = px.sunburst(
        grouped,
        path=["marca", "modelo", "categoria_falla"],
        values="cantidad",
        color="cantidad",
        color_continuous_scale=[[0, "#1E293B"], [0.5, "#3B82F6"], [1, "#00F0FF"]],
    )
    fig.update_traces(
        textinfo="label+value",
        hovertemplate="<b>%{label}</b><br>Reparaciones: %{value}<br>% de la rama: %{percentParent:.1%}<extra></extra>",
    )
    fig.update_layout(
        title=dict(text="Explorador Jerárquico de Fallas (Marca → Modelo → Falla)", font=dict(size=14, color="#F3F4F6")),
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return apply_chart_theme(fig, height=440)


def build_pareto_chart(df: pd.DataFrame) -> go.Figure:
    """Diagrama de Pareto (80/20) de categorías de falla."""
    if df.empty or "categoria_falla" not in df:
        return apply_chart_theme(go.Figure())

    counts = df["categoria_falla"].value_counts().reset_index()
    counts.columns = ["categoria", "cantidad"]
    counts = counts.sort_values(by="cantidad", ascending=False)

    total = counts["cantidad"].sum()
    if total == 0:
        return apply_chart_theme(go.Figure())

    counts["acumulado"] = counts["cantidad"].cumsum()
    counts["pct_acumulado"] = counts["acumulado"] / total * 100.0

    # Categorías abreviadas para mejor lectura en eje X
    counts["categoria_corta"] = counts["categoria"].apply(
        lambda s: s.split("(")[0].strip()
    )

    fig = go.Figure()

    # Barras de frecuencia
    fig.add_trace(
        go.Bar(
            x=counts["categoria_corta"],
            y=counts["cantidad"],
            name="Cantidad de OTs",
            marker=dict(
                color="rgba(0, 240, 255, 0.65)",
                line=dict(color="#00F0FF", width=1.5),
            ),
            hovertemplate="<b>%{x}</b><br>Casos: %{y}<extra></extra>",
        )
    )

    # Línea de % acumulado (Eje Y secundario)
    fig.add_trace(
        go.Scatter(
            x=counts["categoria_corta"],
            y=counts["pct_acumulado"],
            name="% Acumulado (Pareto)",
            mode="lines+markers",
            yaxis="y2",
            line=dict(color="#F59E0B", width=2.5),
            marker=dict(size=7, color="#F59E0B"),
            hovertemplate="Acumulado: %{y:.1f}%<extra></extra>",
        )
    )

    # Línea de referencia del 80%
    fig.add_shape(
        type="line",
        x0=-0.5,
        x1=len(counts) - 0.5,
        y0=80,
        y1=80,
        yref="y2",
        line=dict(color="#F43F5E", width=1.8, dash="dash"),
    )

    fig.update_layout(
        title=dict(text="Análisis de Pareto 80/20 de Fallas Más Recurrentes", font=dict(size=14, color="#F3F4F6")),
        xaxis=dict(tickangle=-25),
        yaxis=dict(title="Cantidad de Fallas"),
        yaxis2=dict(
            title="% Acumulado",
            overlaying="y",
            side="right",
            range=[0, 105],
            ticksuffix="%",
            gridcolor="rgba(0,0,0,0)",
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return apply_chart_theme(fig, height=380)


def build_warranty_return_chart(df: pd.DataFrame) -> go.Figure:
    """Tasa de retorno por garantía clasificada por categoría de servicio."""
    if df.empty or "es_retorno_garantia" not in df:
        return apply_chart_theme(go.Figure())

    grouped = (
        df.groupby("categoria_falla")
        .agg(
            total=("id_orden", "count"),
            garantias=("es_retorno_garantia", "sum"),
        )
        .reset_index()
    )

    grouped["tasa_garantia_pct"] = grouped.apply(
        lambda r: (r["garantias"] / r["total"] * 100.0) if r["total"] > 0 else 0.0,
        axis=1,
    )
    grouped = grouped.sort_values(by="tasa_garantia_pct", ascending=True)
    grouped["categoria_corta"] = grouped["categoria_falla"].apply(lambda s: s.split("(")[0].strip())

    fig = go.Figure(
        go.Bar(
            y=grouped["categoria_corta"],
            x=grouped["tasa_garantia_pct"],
            orientation="h",
            marker=dict(
                color=grouped["tasa_garantia_pct"],
                colorscale=[[0, "#10B981"], [0.5, "#F59E0B"], [1, "#F43F5E"]],
                line=dict(color="#1F2937", width=1),
            ),
            text=grouped["tasa_garantia_pct"].apply(lambda p: f"{p:.1f}%"),
            textposition="outside",
            customdata=grouped[["total", "garantias"]],
            hovertemplate="<b>%{y}</b><br>Tasa Retorno: %{x:.1f}%<br>Retornos: %{customdata[1]} de %{customdata[0]} reparaciones<extra></extra>",
        )
    )
    fig.update_layout(
        title=dict(text="Tasa de Retorno por Garantía según Tipo de Falla (%)", font=dict(size=14, color="#F3F4F6")),
        xaxis=dict(title="Porcentaje de Reingresos (%)", ticksuffix="%"),
        margin=dict(l=180, r=40, t=40, b=30),
    )
    return apply_chart_theme(fig, height=360)

