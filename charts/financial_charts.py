"""Gráficos y análisis financiero de rentabilidad, márgenes y ticket medio (Tab 2)."""

import pandas as pd
import plotly.graph_objects as go
from charts.theme import apply_chart_theme
from core.config import COLORS


def build_financial_timeline_chart(df: pd.DataFrame, freq: str = "W") -> go.Figure:
    """Serie temporal combinada de Facturación, Costos y Margen Neto."""
    if df.empty or "fecha_ingreso_dt" not in df:
        return apply_chart_theme(go.Figure())

    df_valid = df.dropna(subset=["fecha_ingreso_dt"]).copy()
    if df_valid.empty:
        return apply_chart_theme(go.Figure())

    # Agrupación temporal
    df_valid["periodo"] = df_valid["fecha_ingreso_dt"].dt.to_period(freq).dt.to_timestamp()
    grouped = (
        df_valid.groupby("periodo")[["valor_cobrado", "costo_repuesto", "margen_neto"]]
        .sum()
        .reset_index()
    )

    fig = go.Figure()

    # Barra: Facturación Total
    fig.add_trace(
        go.Bar(
            x=grouped["periodo"],
            y=grouped["valor_cobrado"],
            name="Facturación Bruta",
            marker=dict(color="rgba(0, 240, 255, 0.45)", line=dict(color="#00F0FF", width=1.5)),
            hovertemplate="Facturación: $%{y:,.0f}<extra></extra>",
        )
    )

    # Barra: Costo Repuestos
    fig.add_trace(
        go.Bar(
            x=grouped["periodo"],
            y=grouped["costo_repuesto"],
            name="Costo Repuestos",
            marker=dict(color="rgba(244, 63, 94, 0.45)", line=dict(color="#F43F5E", width=1.5)),
            hovertemplate="Costo: $%{y:,.0f}<extra></extra>",
        )
    )

    # Línea: Margen Neto
    fig.add_trace(
        go.Scatter(
            x=grouped["periodo"],
            y=grouped["margen_neto"],
            name="Margen Neto",
            mode="lines+markers",
            line=dict(color="#10B981", width=3),
            marker=dict(size=7, color="#10B981"),
            hovertemplate="Margen Neto: $%{y:,.0f}<extra></extra>",
        )
    )

    fig.update_layout(
        barmode="group",
        title=dict(text="Evolución Financiera (Facturación vs. Costos vs. Margen Neto)", font=dict(size=14, color="#F3F4F6")),
        xaxis=dict(title="Período"),
        yaxis=dict(title="Monto ($)", tickprefix="$"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return apply_chart_theme(fig, height=380)


def build_profitability_scatter_chart(df: pd.DataFrame) -> go.Figure:
    """Gráfico de dispersión/burbujas: Volumen vs. Margen Neto Promedio por Tipo de Reparación."""
    if df.empty:
        return apply_chart_theme(go.Figure())

    grouped = (
        df.groupby("categoria_falla")
        .agg(
            volumen=("id_orden", "count"),
            margen_promedio=("margen_neto", "mean"),
            facturacion_total=("valor_cobrado", "sum"),
            margen_total=("margen_neto", "sum"),
        )
        .reset_index()
    )

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=grouped["volumen"],
            y=grouped["margen_promedio"],
            mode="markers+text",
            text=grouped["categoria_falla"].apply(lambda s: s.split("(")[0].strip()),
            textposition="top center",
            textfont=dict(size=10, color="#D1D5DB"),
            marker=dict(
                size=grouped["margen_total"],
                sizemode="area",
                sizeref=2.0 * max(grouped["margen_total"]) / (45.0**2) if max(grouped["margen_total"]) > 0 else 1,
                sizemin=10,
                color=grouped["margen_promedio"],
                colorscale=[[0, "#3B82F6"], [0.5, "#8B5CF6"], [1, "#00F0FF"]],
                showscale=True,
                colorbar=dict(title=dict(text="Margen Prom ($)", font=dict(size=10, color="#9CA3AF")), tickprefix="$"),
                line=dict(color="#FFFFFF", width=1),
            ),
            customdata=grouped[["categoria_falla", "facturacion_total", "margen_total"]],
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Volumen: %{x} reparaciones<br>"
                "Margen Promedio: $%{y:,.0f}<br>"
                "Facturación Total: $%{customdata[1]:,.0f}<br>"
                "Margen Acumulado: $%{customdata[2]:,.0f}<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        title=dict(text="Matriz de Rentabilidad: Volumen vs. Margen Unitario Promedio", font=dict(size=14, color="#F3F4F6")),
        xaxis=dict(title="Volumen de Reparaciones (Cant. OTs)"),
        yaxis=dict(title="Margen Neto Promedio ($)", tickprefix="$"),
    )
    return apply_chart_theme(fig, height=380)


def build_ticket_distribution_chart(df: pd.DataFrame) -> go.Figure:
    """Histograma y distribución del valor facturado por reparación."""
    if df.empty or "valor_cobrado" not in df:
        return apply_chart_theme(go.Figure())

    cobrado = df[df["valor_cobrado"] > 0]["valor_cobrado"]
    if cobrado.empty:
        return apply_chart_theme(go.Figure())

    median_val = cobrado.median()
    mean_val = cobrado.mean()

    fig = go.Figure()
    fig.add_trace(
        go.Histogram(
            x=cobrado,
            nbinsx=25,
            marker=dict(color="rgba(139, 92, 246, 0.6)", line=dict(color="#8B5CF6", width=1.5)),
            hovertemplate="Rango: %{x}<br>Cantidad OTs: %{y}<extra></extra>",
        )
    )

    # Línea vertical de la media y mediana
    fig.add_vline(
        x=mean_val,
        line_width=2,
        line_dash="dash",
        line_color="#00F0FF",
        annotation_text=f"Media: ${mean_val:,.0f}",
        annotation_position="top right",
        annotation_font_color="#00F0FF",
    )
    fig.add_vline(
        x=median_val,
        line_width=2,
        line_dash="dot",
        line_color="#10B981",
        annotation_text=f"Mediana: ${median_val:,.0f}",
        annotation_position="top left",
        annotation_font_color="#10B981",
    )

    fig.update_layout(
        title=dict(text="Distribución de Ticket Facturado ($)", font=dict(size=14, color="#F3F4F6")),
        xaxis=dict(title="Valor Cobrado ($)", tickprefix="$"),
        yaxis=dict(title="Frecuencia (Reparaciones)"),
    )
    return apply_chart_theme(fig, height=340)

