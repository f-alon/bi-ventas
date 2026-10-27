"""Dashboard Operativo y BI para Servicio Técnico de Reparación de Celulares (LABFIX BI)."""

from datetime import date, timedelta
from pathlib import Path
import sys

# Asegurar path de importación
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

st.set_page_config(
    page_title="LABFIX BI | Reparación de Celulares",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

from components.cards import empty_state, render_header
from components.ui import inject_custom_css
from core.config import ESTADOS_WIP
from core.db import init_db, load_orders_df
from core.seed import seed_database
from views.tab_diagnostics import render_tab_diagnostics
from views.tab_explorer import render_tab_explorer
from views.tab_financial import render_tab_financial
from views.tab_ingestion import render_tab_ingestion
from views.tab_overview import render_tab_overview

# Inyección de estilos visuales dark / cyberpunk
inject_custom_css()

# Inicialización y verificación de base de datos
init_db()
seed_database(num_records=180, force=False)


def main() -> None:
    # Carga de dataset desde SQLite
    df_all = load_orders_df()

    # Barra lateral de filtros globales y control
    with st.sidebar:
        st.markdown(
            """
            <div style="padding: 0.5rem 0 1rem 0; border-bottom: 1px solid #1F2937; margin-bottom: 1rem;">
                <h3 style="color: #00F0FF; margin: 0; font-weight: 800; letter-spacing: -0.02em;">⚡ LABFIX BI</h3>
                <span style="color: #9CA3AF; font-size: 0.76rem;">Panel de Inteligencia Técnica v2.0</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<b style='color: #E5E7EB; font-size: 0.85rem;'>Filtro Temporal General:</b>", unsafe_allow_html=True)

        if not df_all.empty and df_all["fecha_ingreso_dt"].notna().any():
            min_date = df_all["fecha_ingreso_dt"].min().date()
            max_date = df_all["fecha_ingreso_dt"].max().date()
        else:
            min_date = date.today() - timedelta(days=90)
            max_date = date.today()

        # Rango por defecto: últimos 90 días
        default_start = max(min_date, max_date - timedelta(days=90))

        date_range = st.date_input(
            "Rango de Fechas (Ingreso):",
            value=(default_start, max_date),
            min_value=min_date,
            max_value=max_date,
            key="sidebar_date_range",
        )

        st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)

        # Filtro de marcas rápido en sidebar
        if not df_all.empty:
            marcas_disp = sorted(df_all["marca"].dropna().unique().tolist())
            selected_marcas = st.multiselect(
                "Filtrar Marcas:",
                options=marcas_disp,
                default=marcas_disp,
                key="sidebar_sel_marcas",
            )
        else:
            selected_marcas = []

        st.markdown("<div style='border-top: 1px solid #1F2937; margin: 1.5rem 0 1rem 0;'></div>", unsafe_allow_html=True)

        # Utilidades del taller
        with st.expander("🛠️ Opciones de Laboratorio", expanded=False):
            if st.button("🔄 Regenerar Datos de Prueba (Seed)", key="btn_reseed_db", use_container_width=True):
                seed_database(num_records=180, force=True)
                st.toast("Base de datos regenerada con 180 órdenes de ejemplo.", icon="⚡")
                st.rerun()

        st.markdown(
            """
            <div style="margin-top: 2rem; color: #6B7280; font-size: 0.72rem; text-align: center;">
                Microelectrónica & Smartphone BI<br>
                Persistencia: SQLite Local (<code class="tech-mono">repairs.db</code>)
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Filtrado según sidebar
    df_filtered = df_all.copy()
    if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
        start_d, end_d = date_range
        df_filtered = df_filtered[
            (df_filtered["fecha_ingreso_dt"].dt.date >= start_d)
            & (df_filtered["fecha_ingreso_dt"].dt.date <= end_d)
        ]

    if selected_marcas:
        df_filtered = df_filtered[df_filtered["marca"].isin(selected_marcas)]

    # Cálculo de métricas para el header
    total_orders = len(df_all)
    active_wip = len(df_all[df_all["estado"].isin(ESTADOS_WIP)])

    # Render Header principal
    render_header(total_orders=total_orders, active_wip=active_wip)

    # Pestañas principales del dashboard
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "📊 Panel Ejecutivo y Operativo",
            "💰 Análisis Financiero & Rentabilidad",
            "🔬 Métricas de Dispositivos & Fallas",
            "🔍 Explorador & Auditoría",
            "➕ Ingesta & Carga de OTs",
        ]
    )

    with tab1:
        render_tab_overview(df_filtered)

    with tab2:
        render_tab_financial(df_filtered)

    with tab3:
        render_tab_diagnostics(df_filtered)

    with tab4:
        render_tab_explorer(df_filtered)

    with tab5:
        render_tab_ingestion()


if __name__ == "__main__":
    main()

