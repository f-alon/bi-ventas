"""Estilos CSS y utilidades visuales (Tema Dark / Cyberpunk Slate)."""

import streamlit as st


def inject_custom_css() -> None:
    """Inyecta reglas CSS avanzadas para el dashboard de servicio técnico."""
    st.markdown(
        """
        <style>
        /* Tipografía e interfaz base */
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        }

        code, .stCodeBlock, .tech-mono {
            font-family: 'JetBrains Mono', monospace !important;
        }

        /* Fondo principal */
        .stApp {
            background-color: #0B0F19;
            color: #F9FAFB;
        }

        /* Header de Marca */
        .tech-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 1rem 1.5rem;
            margin-bottom: 1.5rem;
            background: linear-gradient(135deg, rgba(17, 24, 39, 0.95) 0%, rgba(15, 23, 42, 0.95) 100%);
            border: 1px solid #1F2937;
            border-left: 4px solid #00F0FF;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
        }

        .tech-header-title {
            font-size: 1.5rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            color: #FFFFFF;
            display: flex;
            align-items: center;
            gap: 0.6rem;
        }

        .tech-header-badge {
            background: rgba(0, 240, 255, 0.12);
            color: #00F0FF;
            border: 1px solid rgba(0, 240, 255, 0.35);
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            padding: 0.2rem 0.55rem;
            border-radius: 6px;
        }

        .tech-header-sub {
            color: #9CA3AF;
            font-size: 0.85rem;
            margin-top: 0.2rem;
        }

        /* Tarjetas de Métricas (KPI Cards) */
        .kpi-card {
            background: linear-gradient(180deg, #111827 0%, #0F172A 100%);
            border: 1px solid #1F2937;
            border-radius: 12px;
            padding: 1.15rem 1.25rem;
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.35);
            transition: transform 0.18s ease, border-color 0.18s ease;
            position: relative;
            overflow: hidden;
        }

        .kpi-card:hover {
            transform: translateY(-2px);
            border-color: #374151;
        }

        .kpi-glow-cyan {
            border-top: 2px solid #00F0FF;
        }
        .kpi-glow-emerald {
            border-top: 2px solid #10B981;
        }
        .kpi-glow-amber {
            border-top: 2px solid #F59E0B;
        }
        .kpi-glow-purple {
            border-top: 2px solid #8B5CF6;
        }
        .kpi-glow-rose {
            border-top: 2px solid #F43F5E;
        }

        .kpi-title {
            color: #9CA3AF;
            font-size: 0.78rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .kpi-value {
            color: #FFFFFF;
            font-size: 1.85rem;
            font-weight: 800;
            letter-spacing: -0.03em;
            margin: 0.35rem 0 0.25rem 0;
            font-feature-settings: "tnum";
        }

        .kpi-delta {
            font-size: 0.78rem;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 0.25rem;
            padding: 0.15rem 0.5rem;
            border-radius: 4px;
        }

        .delta-pos {
            background: rgba(16, 185, 129, 0.15);
            color: #10B981;
        }

        .delta-neg {
            background: rgba(244, 63, 94, 0.15);
            color: #F43F5E;
        }

        .delta-neutral {
            background: rgba(156, 163, 175, 0.15);
            color: #9CA3AF;
        }

        /* Contenedores de Tarjetas de Gráficos */
        .chart-container-card {
            background: #111827;
            border: 1px solid #1F2937;
            border-radius: 12px;
            padding: 1.25rem;
            margin-bottom: 1.25rem;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
        }

        .chart-header {
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            margin-bottom: 0.75rem;
            border-bottom: 1px solid #1F2937;
            padding-bottom: 0.5rem;
        }

        .chart-title {
            color: #F3F4F6;
            font-size: 0.98rem;
            font-weight: 700;
        }

        .chart-subtitle {
            color: #6B7280;
            font-size: 0.76rem;
        }

        /* Badges de Estado */
        .badge-status {
            display: inline-block;
            padding: 0.2rem 0.55rem;
            border-radius: 6px;
            font-size: 0.72rem;
            font-weight: 600;
            letter-spacing: 0.02em;
        }

        .badge-ingresado { background: rgba(59, 130, 246, 0.18); color: #60A5FA; border: 1px solid rgba(59, 130, 246, 0.3); }
        .badge-diagnostico { background: rgba(139, 92, 246, 0.18); color: #A78BFA; border: 1px solid rgba(139, 92, 246, 0.3); }
        .badge-repuesto { background: rgba(245, 158, 11, 0.18); color: #FBBF24; border: 1px solid rgba(245, 158, 11, 0.3); }
        .badge-reparacion { background: rgba(0, 240, 255, 0.18); color: #00F0FF; border: 1px solid rgba(0, 240, 255, 0.3); }
        .badge-listo { background: rgba(16, 185, 129, 0.18); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.3); }
        .badge-entregado { background: rgba(5, 150, 105, 0.25); color: #10B981; border: 1px solid rgba(5, 150, 105, 0.4); }
        .badge-rechazado { background: rgba(244, 63, 94, 0.18); color: #FB7185; border: 1px solid rgba(244, 63, 94, 0.3); }

        /* Alertas de demora */
        .alert-delayed-row {
            background: rgba(245, 158, 11, 0.08);
            border-left: 3px solid #F59E0B;
        }

        /* Pestañas (Tabs) */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: transparent;
            border-bottom: 1px solid #1F2937;
            padding-bottom: 4px;
        }

        .stTabs [data-baseweb="tab"] {
            background-color: #111827;
            border: 1px solid #1F2937;
            border-radius: 8px 8px 0px 0px;
            color: #9CA3AF;
            font-weight: 600;
            font-size: 0.88rem;
            padding: 8px 16px;
            transition: all 0.2s ease;
        }

        .stTabs [aria-selected="true"] {
            background-color: #1E293B !important;
            border-color: #00F0FF !important;
            color: #00F0FF !important;
            border-bottom: 2px solid #00F0FF !important;
        }

        /* Estilo de inputs y controles */
        div[data-baseweb="select"] > div {
            background-color: #111827;
            border-color: #1F2937;
        }

        .stTextInput > div > div > input,
        .stNumberInput > div > div > input {
            background-color: #111827;
            border-color: #1F2937;
            color: #F9FAFB;
        }

        /* Empty states */
        .empty-state-box {
            text-align: center;
            padding: 2.5rem 1.5rem;
            background: #111827;
            border: 1px dashed #374151;
            border-radius: 12px;
            color: #9CA3AF;
        }
        .empty-state-icon {
            font-size: 2.2rem;
            color: #4B5563;
            margin-bottom: 0.5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

