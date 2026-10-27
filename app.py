"""Dashboard Operativo y BI para Servicio Técnico de Celulares (LABFIX BI)."""

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

from auth import (
    get_user_count,
    init_session_state,
    logout_user,
    render_login_view,
)
from components.ui import inject_custom_css
from core.db import init_db, load_orders_df
from views.admin_view import render_admin_dashboard
from views.tecnico_view import render_tecnico_workspace

# Inyección de estilos visuales dark / cyberpunk
inject_custom_css()

# Inicialización de esquema de base de datos y control de sesión
init_db()
init_session_state()


def main() -> None:
    # 1. Puerta de Enlace de Autenticación
    if not st.session_state.get("authenticated", False):
        render_login_view()
        return

    # 2. Carga de dataset desde SQLite
    df_all = load_orders_df()

    # Usuario y Rol actual en sesión
    current_username = st.session_state.get("username", "")
    current_tech_name = st.session_state.get("tecnico_nombre", "")
    current_role = st.session_state.get("user_role", "tecnico")

    # 3. Barra Lateral de Navegación y Control de Sesión
    with st.sidebar:
        st.markdown(
            """
            <div style="padding: 0.25rem 0 0.8rem 0; border-bottom: 1px solid #1F2937; margin-bottom: 0.8rem;">
                <h3 style="color: #00F0FF; margin: 0; font-weight: 800; letter-spacing: -0.02em;">⚡ LABFIX BI</h3>
                <span style="color: #9CA3AF; font-size: 0.76rem;">Microelectrónica & Smartphone BI v2.5</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Perfil del usuario activo
        role_label = "👑 Administrador" if current_role == "admin" else "🔬 Técnico de Lab"
        role_color = "#00F0FF" if current_role == "admin" else "#8B5CF6"

        st.markdown(
            f"""
            <div style="background: rgba(17, 24, 39, 0.9); border: 1px solid #1F2937; border-left: 3px solid {role_color}; padding: 0.6rem 0.8rem; border-radius: 8px; margin-bottom: 1rem;">
                <div style="color: #9CA3AF; font-size: 0.72rem; text-transform: uppercase;">Sesión Activa</div>
                <div style="color: #FFFFFF; font-weight: 700; font-size: 0.95rem;">{current_tech_name}</div>
                <div style="color: {role_color}; font-size: 0.78rem; font-weight: 600;">{role_label} (<span class="tech-mono">@{current_username}</span>)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("🚪 Cerrar Sesión", key="sidebar_btn_logout", use_container_width=True):
            logout_user()

        st.markdown("<div style='border-top: 1px solid #1F2937; margin: 1rem 0;'></div>", unsafe_allow_html=True)

        # Filtros temporales generales (activos principalmente para la vista de análisis)
        st.markdown("<b style='color: #E5E7EB; font-size: 0.85rem;'>Filtro Temporal General:</b>", unsafe_allow_html=True)

        if not df_all.empty and df_all["fecha_ingreso_dt"].notna().any():
            min_date = df_all["fecha_ingreso_dt"].min().date()
            max_date = df_all["fecha_ingreso_dt"].max().date()
        else:
            min_date = date.today() - timedelta(days=90)
            max_date = date.today()

        default_start = max(min_date, max_date - timedelta(days=90))

        date_range = st.date_input(
            "Rango de Fechas (Ingreso):",
            value=(default_start, max_date),
            min_value=min_date,
            max_value=max_date,
            key="sidebar_date_range",
        )

        st.markdown("<div style='margin-top: 0.75rem;'></div>", unsafe_allow_html=True)

        # Filtro rápido de marcas
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

        st.markdown(
            """
            <div style="margin-top: 3rem; color: #6B7280; font-size: 0.72rem; text-align: center;">
                Microelectrónica & Smartphone BI<br>
                Persistencia: SQLite (<code class="tech-mono">data/repairs.db</code>)
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Filtrar dataset para vistas analíticas
    df_filtered = df_all.copy()
    if not df_all.empty and isinstance(date_range, (tuple, list)) and len(date_range) == 2:
        start_d, end_d = date_range
        df_filtered = df_filtered[
            (df_filtered["fecha_ingreso_dt"].dt.date >= start_d)
            & (df_filtered["fecha_ingreso_dt"].dt.date <= end_d)
        ]

    if not df_all.empty and selected_marcas:
        df_filtered = df_filtered[df_filtered["marca"].isin(selected_marcas)]

    # 4. Enrutamiento según Rol del Usuario
    if current_role == "admin":
        render_admin_dashboard(df_all=df_all, df_filtered=df_filtered)
    else:
        render_tecnico_workspace(df_all=df_all, current_tech_name=current_tech_name)


if __name__ == "__main__":
    main()
