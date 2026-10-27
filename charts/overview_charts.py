"""Gráficos y agregaciones para el Panel Ejecutivo y Operativo (Tab 1)."""

import pandas as pd
import plotly.graph_objects as go
from charts.theme import apply_chart_theme
from core.config import COLORS, ESTADOS_ORDEN, ESTADOS_WIP


def build_operational_funnel_chart(df: pd.DataFrame) -> go.Figure:
    """Genera gráfico de embudo horizontal del ciclo de vida de las reparaciones."""
    counts = df["estado"].value_counts().to_dict()
    stages = [st for st in ESTADOS_ORDEN if st in counts]
    values = [counts.get(st, 0) for st in stages]

    color_map = {
        "Ingresado": "#3B82F6",
        "En Diagnóstico": "#8B5CF6",
        "Esperando Repuesto": "#F59E0B",
        "En Reparación": "#00F0FF",
        "Listo para Entrega": "#10B981",
        "Entregado": "#059669",
        "Sin Reparación / Rechazado": "#F43F5E",
    }
    colors = [color_map.get(st, "#6B7280") for st in stages]

    fig = go.Figure(
        go.Funnel(
            y=stages,
            x=values,
            textinfo="value+percent initial",
            marker=dict(color=colors),
            connector=dict(line=dict(color="#1F2937", width=1.5)),
            hovertemplate="<b>%{y}</b><br>Equipos: %{x}<br>% del total: %{percentInitial}<extra></extra>",
        )
    )
    fig.update_layout(
        title=dict(text="Ciclo de Vida de Órdenes (Funnel Operativo)", font=dict(size=14, color="#F3F4F6")),
        margin=dict(l=140, r=25, t=40, b=25),
    )
    return apply_chart_theme(fig, height=360)


def build_wip_by_tech_chart(df: pd.DataFrame) -> go.Figure:
    """Distribución de equipos activos en banco de trabajo por técnico asignado."""
    wip_df = df[df["estado"].isin(ESTADOS_WIP)]
    if wip_df.empty:
        fig = go.Figure()
        return apply_chart_theme(fig)

    counts = wip_df.groupby("tecnico").size().reset_index(name="ordenes_activas")
    counts = counts.sort_values(by="ordenes_activas", ascending=True)

    fig = go.Figure(
        go.Bar(
            y=counts["tecnico"],
            x=counts["ordenes_activas"],
            orientation="h",
            marker=dict(
                color=counts["ordenes_activas"],
                colorscale=[[0, "#3B82F6"], [1, "#00F0FF"]],
                line=dict(color="#00F0FF", width=1),
            ),
            text=counts["ordenes_activas"],
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>Equipos activos: %{x}<extra></extra>",
        )
    )
    fig.update_layout(
        title=dict(text="Carga de Trabajo Activa por Técnico (WIP)", font=dict(size=14, color="#F3F4F6")),
        xaxis=dict(title="Órdenes en proceso"),
        margin=dict(l=160, r=40, t=40, b=30),
    )
    return apply_chart_theme(fig, height=360)


def get_delayed_orders(df: pd.DataFrame, days_threshold: int = 5) -> pd.DataFrame:
    """Filtra órdenes activas en WIP con más de X días sin avance de estado."""
    wip_df = df[df["estado"].isin(ESTADOS_WIP)].copy()
    if wip_df.empty:
        return pd.DataFrame()
    delayed = wip_df[wip_df["dias_en_estado"] >= days_threshold].sort_values(
        by="dias_en_estado", ascending=False
    )
    return delayed

