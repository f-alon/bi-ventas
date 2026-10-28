"""Generación de Gráficos Analíticos e Interactivos (Plotly) para el ERP LABFIX."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from charts.theme import apply_chart_theme
from core.config import COLORS, ESTADOS_OT


def build_weekly_revenue_trend(df_orders: pd.DataFrame) -> go.Figure:
    """Curva interactiva de facturación semanal (Mano de Obra vs. Repuestos)."""
    if df_orders.empty or "fecha_ingreso_dt" not in df_orders:
        return apply_chart_theme(go.Figure())

    df_valid = df_orders.dropna(subset=["fecha_ingreso_dt"]).copy()
    if df_valid.empty:
        return apply_chart_theme(go.Figure())

    df_valid["semana"] = df_valid["fecha_ingreso_dt"].dt.to_period("W").dt.to_timestamp()
    grouped = df_valid.groupby("semana")[["mano_obra", "costo_repuestos", "total"]].sum().reset_index()

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=grouped["semana"],
            y=grouped["mano_obra"],
            name="Mano de Obra",
            marker=dict(color="rgba(0, 240, 255, 0.65)", line=dict(color="#00F0FF", width=1.5)),
            hovertemplate="Mano de Obra: $%{y:,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=grouped["semana"],
            y=grouped["costo_repuestos"],
            name="Costo Repuestos",
            marker=dict(color="rgba(244, 63, 94, 0.55)", line=dict(color="#F43F5E", width=1.5)),
            hovertemplate="Repuestos: $%{y:,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=grouped["semana"],
            y=grouped["total"],
            name="Facturación Total",
            mode="lines+markers",
            line=dict(color="#10B981", width=3),
            marker=dict(size=8, color="#10B981"),
            hovertemplate="Total: $%{y:,.0f}<extra></extra>",
        )
    )

    fig.update_layout(
        barmode="stack",
        title=dict(text="Curva Semanal de Facturación & Costos de Taller", font=dict(size=14, color="#F3F4F6")),
        xaxis=dict(title="Semana"),
        yaxis=dict(title="Monto ($)", tickprefix="$"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return apply_chart_theme(fig, height=360)


def build_orders_status_funnel(df_orders: pd.DataFrame) -> go.Figure:
    """Distribución de equipos en el ciclo de vida completo del taller."""
    if df_orders.empty:
        return apply_chart_theme(go.Figure())

    counts = df_orders["estado"].value_counts().to_dict()
    stages = [st for st in ESTADOS_OT if st in counts or counts.get(st, 0) > 0]
    values = [counts.get(st, 0) for st in stages]

    color_map = {
        "Ingresado": "#3B82F6",
        "En Diagnóstico": "#8B5CF6",
        "Esperando Presupuesto": "#EC4899",
        "Esperando Repuesto": "#F59E0B",
        "En Reparación": "#00F0FF",
        "Control de Calidad": "#6366F1",
        "Listo para Retiro": "#10B981",
        "Entregado": "#059669",
        "Sin Reparación / Rechazado": "#F43F5E",
    }
    colors = [color_map.get(st, "#6B7280") for st in stages]

    fig = go.Figure(
        go.Bar(
            y=stages,
            x=values,
            orientation="h",
            marker=dict(color=colors, line=dict(color="#1F2937", width=1.5)),
            text=values,
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>Equipos: %{x}<extra></extra>",
        )
    )
    fig.update_layout(
        title=dict(text="Distribución de Equipos según Estado de Servicio", font=dict(size=14, color="#F3F4F6")),
        xaxis=dict(title="Cantidad de Dispositivos"),
        margin=dict(l=170, r=40, t=40, b=30),
    )
    return apply_chart_theme(fig, height=380)


def build_pareto_failures_chart(df_orders: pd.DataFrame) -> go.Figure:
    """Diagrama de Pareto 80/20 de causas de falla recurrentes."""
    if df_orders.empty or "falla_declarada" not in df_orders:
        return apply_chart_theme(go.Figure())

    counts = df_orders["falla_declarada"].value_counts().reset_index()
    counts.columns = ["falla", "cantidad"]
    counts = counts.sort_values(by="cantidad", ascending=False)

    total = counts["cantidad"].sum()
    if total == 0:
        return apply_chart_theme(go.Figure())

    counts["acumulado"] = counts["cantidad"].cumsum()
    counts["pct_acumulado"] = counts["acumulado"] / total * 100.0
    counts["falla_corta"] = counts["falla"].apply(lambda s: s.split("(")[0].strip()[:24])

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=counts["falla_corta"],
            y=counts["cantidad"],
            name="Cantidad de OTs",
            marker=dict(color="rgba(0, 240, 255, 0.7)", line=dict(color="#00F0FF", width=1.5)),
            hovertemplate="<b>%{x}</b><br>Casos: %{y}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=counts["falla_corta"],
            y=counts["pct_acumulado"],
            name="% Acumulado (Pareto)",
            mode="lines+markers",
            yaxis="y2",
            line=dict(color="#F59E0B", width=2.5),
            marker=dict(size=7, color="#F59E0B"),
            hovertemplate="Acumulado: %{y:.1f}%<extra></extra>",
        )
    )
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
        title=dict(text="Análisis de Pareto 80/20 de Fallas en Banco", font=dict(size=14, color="#F3F4F6")),
        xaxis=dict(tickangle=-25),
        yaxis=dict(title="Cantidad de Fallas"),
        yaxis2=dict(title="% Acumulado", overlaying="y", side="right", range=[0, 105], ticksuffix="%"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return apply_chart_theme(fig, height=380)


def build_technician_performance_bar(df_orders: pd.DataFrame) -> go.Figure:
    """Comparativa de efectividad y carga de trabajo por técnico."""
    if df_orders.empty or "tecnico_nombre" not in df_orders:
        return apply_chart_theme(go.Figure())

    valid_tech = df_orders.dropna(subset=["tecnico_nombre"]).copy()
    if valid_tech.empty:
        return apply_chart_theme(go.Figure())

    grouped = valid_tech.groupby("tecnico_nombre").agg(
        total_ots=("id", "count"),
        mano_obra=("mano_obra", "sum"),
    ).reset_index().sort_values(by="total_ots", ascending=True)

    fig = go.Figure(
        go.Bar(
            y=grouped["tecnico_nombre"],
            x=grouped["total_ots"],
            orientation="h",
            marker=dict(color=grouped["total_ots"], colorscale=[[0, "#8B5CF6"], [1, "#00F0FF"]]),
            text=grouped["total_ots"],
            textposition="outside",
            customdata=grouped["mano_obra"],
            hovertemplate="<b>%{y}</b><br>Reparaciones: %{x}<br>Mano de Obra: $%{customdata:,.0f}<extra></extra>",
        )
    )
    fig.update_layout(
        title=dict(text="Carga de Trabajo Asignada por Técnico", font=dict(size=14, color="#F3F4F6")),
        xaxis=dict(title="Órdenes de Trabajo"),
        margin=dict(l=180, r=40, t=40, b=30),
    )
    return apply_chart_theme(fig, height=320)


# Aliases explícitos para compatibilidad
build_pareto_chart = build_pareto_failures_chart
build_technician_performance = build_technician_performance_bar


