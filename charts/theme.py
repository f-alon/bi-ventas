"""Configuración de tema y estética visual para gráficos de Plotly."""

import plotly.graph_objects as go
from core.config import COLORS

PLOTLY_TEMPLATE = go.layout.Template(
    layout=go.Layout(
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        font=dict(
            family="Plus Jakarta Sans, sans-serif",
            size=12,
            color="#D1D5DB",
        ),
        xaxis=dict(
            gridcolor="#1F2937",
            zerolinecolor="#374151",
            tickfont=dict(color="#9CA3AF", size=11),
            linecolor="#1F2937",
        ),
        yaxis=dict(
            gridcolor="#1F2937",
            zerolinecolor="#374151",
            tickfont=dict(color="#9CA3AF", size=11),
            linecolor="#1F2937",
        ),
        hoverlabel=dict(
            bgcolor="#0B0F19",
            bordercolor="#00F0FF",
            font=dict(family="JetBrains Mono, monospace", size=12, color="#FFFFFF"),
        ),
        legend=dict(
            bgcolor="rgba(17, 24, 39, 0.7)",
            bordercolor="#1F2937",
            font=dict(color="#9CA3AF", size=11),
        ),
        margin=dict(l=30, r=25, t=35, b=30),
    )
)


def apply_chart_theme(fig: go.Figure, height: int = 340) -> go.Figure:
    """Aplica la plantilla oscura personalizada a cualquier figura de Plotly."""
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        height=height,
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
    )
    return fig

