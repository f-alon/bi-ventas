"""Componentes visuales modulares de interfaz: cards, badges, alertas y formateadores."""

import streamlit as st
from core.config import COLORS


def format_currency(val: float | int) -> str:
    """Formatea valores monetarios en pesos/dólares con separadores de miles."""
    if val is None or val != val:
        return "$0"
    return f"${val:,.0f}".replace(",", ".")


def format_pct(val: float | int, show_sign: bool = True) -> str:
    """Formatea valores porcentuales con 1 decimal."""
    if val is None or val != val:
        return "0.0%"
    sign = "+" if show_sign and val > 0 else ""
    return f"{sign}{val:.1f}%"


def format_number(val: float | int) -> str:
    """Formatea números enteros o flotantes con separadores."""
    if val is None or val != val:
        return "0"
    return f"{val:,.0f}".replace(",", ".")


def render_header(total_orders: int, active_wip: int) -> None:
    """Renderiza el banner superior de comando del taller de celulares."""
    st.markdown(
        f"""
        <div class="tech-header">
            <div>
                <div class="tech-header-title">
                    <span>⚡ LABFIX BI</span>
                    <span class="tech-header-badge">Microelectrónica & Smartphone Lab</span>
                </div>
                <div class="tech-header-sub">
                    Sistema de Inteligencia Operativa, Trazabilidad de Reparaciones y Métricas Financieras
                </div>
            </div>
            <div style="text-align: right; display: flex; gap: 1rem; align-items: center;">
                <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); padding: 0.35rem 0.75rem; border-radius: 8px;">
                    <span style="color: #9CA3AF; font-size: 0.72rem; text-transform: uppercase;">WIP Activo</span><br>
                    <b style="color: #10B981; font-size: 1.1rem;">{active_wip} en banco</b>
                </div>
                <div style="background: rgba(0, 240, 255, 0.1); border: 1px solid rgba(0, 240, 255, 0.3); padding: 0.35rem 0.75rem; border-radius: 8px;">
                    <span style="color: #9CA3AF; font-size: 0.72rem; text-transform: uppercase;">Historial Total</span><br>
                    <b style="color: #00F0FF; font-size: 1.1rem;">{total_orders} OTs</b>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(
    title: str,
    value: str,
    delta_text: str | None = None,
    delta_positive: bool | None = None,
    glow_color: str = "cyan",
    subtext: str | None = None,
) -> None:
    """Renderiza una tarjeta KPI con borde superior de neón y chip de variación."""
    delta_html = ""
    if delta_text:
        if delta_positive is True:
            css_class = "delta-pos"
            arrow = "▲"
        elif delta_positive is False:
            css_class = "delta-neg"
            arrow = "▼"
        else:
            css_class = "delta-neutral"
            arrow = "■"
        delta_html = f'<span class="kpi-delta {css_class}">{arrow} {delta_text}</span>'

    sub_html = f'<div style="color: #6B7280; font-size: 0.72rem; margin-top: 0.25rem;">{subtext}</div>' if subtext else ""

    st.markdown(
        f"""
        <div class="kpi-card kpi-glow-{glow_color}">
            <div class="kpi-title">
                <span>{title}</span>
                {delta_html}
            </div>
            <div class="kpi-value">{value}</div>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_status_badge_html(status: str) -> str:
    """Devuelve un badge HTML estilizado para el estado de la orden."""
    mapping = {
        "Ingresado": "badge-ingresado",
        "En Diagnóstico": "badge-diagnostico",
        "Esperando Repuesto": "badge-repuesto",
        "En Reparación": "badge-reparacion",
        "Listo para Entrega": "badge-listo",
        "Entregado": "badge-entregado",
        "Sin Reparación / Rechazado": "badge-rechazado",
    }
    css = mapping.get(status, "badge-ingresado")
    return f'<span class="badge-status {css}">{status}</span>'


def empty_state(message: str = "No hay registros disponibles para los filtros seleccionados.") -> None:
    """Muestra un empty state visual profesional."""
    st.markdown(
        f"""
        <div class="empty-state-box">
            <div class="empty-state-icon">🔍</div>
            <div style="font-weight: 600; color: #E5E7EB; margin-bottom: 0.25rem;">Sin datos en el rango</div>
            <div style="font-size: 0.82rem;">{message}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

