"""Reusable Streamlit UI pieces: KPIs, charts, and tables."""

from __future__ import annotations

from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.theme import plot_layout

MONTHS_ES = [
    "ene", "feb", "mar", "abr", "may", "jun",
    "jul", "ago", "sep", "oct", "nov", "dic",
]


def format_date(value) -> str:
    d = pd.Timestamp(value).date()
    return f"{d.day:02d} {MONTHS_ES[d.month - 1]} {d.year}"


def format_currency(value: float) -> str:
    rounded = f"{value:,.0f}"
    return "$ " + rounded.replace(",", ".")


def format_number(value: float, digits: int = 0) -> str:
    formatted = f"{value:,.{digits}f}"
    if digits:
        whole, frac = formatted.split(".")
        return whole.replace(",", ".") + "," + frac
    return formatted.replace(",", ".")


def format_pct(value: float | None) -> str | None:
    if value is None:
        return None
    sign = "+" if value > 0 else ""
    return f"{sign}{value * 100:.1f}%".replace(".", ",")


def delta_type(value: float | None) -> str:
    if value is None or value == 0:
        return "warn"
    return "up" if value > 0 else "down"


def metric_card(label: str, value: str, delta: str | None = None, kind: str = "warn") -> None:
    arrow = "↑" if kind == "up" else ("↓" if kind == "down" else "→")
    delta_html = (
        f'<div class="metric-delta delta-{kind}">{arrow} {escape(delta)}</div>' if delta else ""
    )
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{escape(label)}</div>
            <div class="metric-value">{escape(value)}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def empty_state(message: str) -> None:
    st.markdown(
        f'<div class="empty-state">{escape(message)}</div>',
        unsafe_allow_html=True,
    )


def error_state(message: str) -> None:
    st.markdown(
        f'<div class="error-state">{escape(message)}</div>',
        unsafe_allow_html=True,
    )


def chart_card(title: str, subtitle: str, fig: go.Figure) -> None:
    st.markdown(
        f"""
        <div class="chart-wrap">
            <div class="chart-title">{escape(title)}</div>
            <div class="chart-subtitle">{escape(subtitle)}</div>
        """,
        unsafe_allow_html=True,
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)


def data_table(title: str, subtitle: str, headers: list[tuple[str, str]], rows: list[list[str]]) -> None:
    head = "".join(
        f'<th class="{escape(align)}">{escape(label)}</th>' for label, align in headers
    )
    body = []
    for row in rows:
        cells = []
        for (label, align), cell in zip(headers, row):
            cells.append(f'<td class="{escape(align)}">{cell}</td>')
        body.append("<tr>" + "".join(cells) + "</tr>")
    st.markdown(
        f"""
        <div class="table-wrap">
            <div class="chart-title">{escape(title)}</div>
            <div class="chart-subtitle">{escape(subtitle)}</div>
            <table class="data-table">
                <thead><tr>{head}</tr></thead>
                <tbody>{''.join(body)}</tbody>
            </table>
        </div>
        """,
        unsafe_allow_html=True,
    )


def badge(text: str, kind: str) -> str:
    return f'<span class="badge badge-{escape(kind)}">{escape(text)}</span>'


def margin_badge(pct: float) -> str:
    if pct >= 0.30:
        kind = "green"
    elif pct >= 0.15:
        kind = "amber"
    else:
        kind = "red"
    return badge(f"{pct * 100:.0f}%".replace(".", ","), kind)


def line_chart(df: pd.DataFrame, x: str, y_cols: list[tuple[str, str]]) -> go.Figure:
    fig = go.Figure()
    for col, name in y_cols:
        fig.add_trace(
            go.Scatter(
                x=df[x],
                y=df[col],
                name=name,
                mode="lines",
                line=dict(width=2),
                hovertemplate="%{x|%d %b %Y}<br>%{y:,.0f}<extra>" + name + "</extra>",
            )
        )
    fig.update_layout(**plot_layout())
    fig.update_xaxes(tickformat="%d %b")
    return fig


def bar_chart(df: pd.DataFrame, x: str, y: str, name: str, horizontal: bool = False) -> go.Figure:
    fig = go.Figure()
    layout = plot_layout()
    if horizontal:
        fig.add_trace(
            go.Bar(
                y=df[x],
                x=df[y],
                orientation="h",
                name=name,
                marker_color="#2563eb",
                hovertemplate="%{y}<br>%{x:,.0f}<extra></extra>",
            )
        )
        yaxis = dict(layout.get("yaxis", {}))
        yaxis["autorange"] = "reversed"
        layout["yaxis"] = yaxis
    else:
        fig.add_trace(
            go.Bar(
                x=df[x],
                y=df[y],
                name=name,
                marker_color="#2563eb",
                hovertemplate="%{x}<br>%{y:,.0f}<extra></extra>",
            )
        )
    fig.update_layout(**layout)
    return fig


def donut_chart(df: pd.DataFrame, names: str, values: str) -> go.Figure:
    fig = go.Figure(
        go.Pie(
            labels=df[names],
            values=df[values],
            hole=0.62,
            textinfo="percent",
            hovertemplate="%{label}<br>%{value:,.0f}<extra></extra>",
        )
    )
    fig.update_layout(**plot_layout(), showlegend=True)
    return fig
