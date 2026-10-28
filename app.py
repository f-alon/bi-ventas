"""LABFIX ERP - Sistema de Gestión Integral para Taller de Microelectrónica y Reparaciones."""

from datetime import date
from pathlib import Path
import sys

# Asegurar path de importación
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

st.set_page_config(
    page_title="LABFIX ERP | Taller de Reparaciones & POS",
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
from core.config import NAV_MODULES
from database import init_db

# Vistas de los 5 Bloques ERP
from views.admin_config import render_config_view
from views.admin_emails import render_emails_view
from views.admin_soporte import render_soporte_view
from views.com_clientes import render_clientes_view
from views.com_pos import render_pos_view
from views.com_vendedores import render_vendedores_view
from views.com_ventas import render_ventas_view
from views.fin_caja import render_caja_view
from views.fin_comprobantes import render_comprobantes_view
from views.fin_reportes import render_reportes_view
from views.garantias_rma import render_garantias_view
from views.kiosco_leads import render_kiosco_leads_view
from views.oper_cotizaciones import render_cotizaciones_view
from views.oper_dashboard import render_dashboard_view
from views.oper_ordenes import render_ordenes_view
from views.oper_tecnicos import render_tecnicos_view
from views.stock_etiquetas import render_etiquetas_view
from views.stock_inventario import render_inventario_view
from views.stock_proveedores import render_proveedores_view

# Inyección de estilos visuales dark / cyberpunk
inject_custom_css()

# Inicialización de base de datos relacional y estado de sesión
init_db()
init_session_state()

# Mapeo de despachadores de vistas
VIEW_DISPATCHER = {
    "oper_dashboard": render_dashboard_view,
    "oper_ordenes": render_ordenes_view,
    "oper_cotizaciones": render_cotizaciones_view,
    "oper_tecnicos": render_tecnicos_view,
    "garantias_rma": render_garantias_view,
    "com_pos": render_pos_view,
    "com_ventas": render_ventas_view,
    "com_clientes": render_clientes_view,
    "com_vendedores": render_vendedores_view,
    "kiosco_leads": render_kiosco_leads_view,
    "stock_inventario": render_inventario_view,
    "stock_etiquetas": render_etiquetas_view,
    "stock_proveedores": render_proveedores_view,
    "fin_caja": render_caja_view,
    "fin_comprobantes": render_comprobantes_view,
    "fin_reportes": render_reportes_view,
    "admin_config": render_config_view,
    "admin_emails": render_emails_view,
    "admin_soporte": render_soporte_view,
}


def main() -> None:
    # 1. Control de Autenticación
    if not st.session_state.get("authenticated", False):
        render_login_view()
        return

    # Usuario y Rol en Sesión normalizado a mayúsculas
    current_username = st.session_state.get("username", "")
    current_nombre = st.session_state.get("tecnico_nombre", "")
    current_role = str(st.session_state.get("user_role", "TECNICO")).upper()

    # 2. Barra Lateral Jerárquica ERP
    with st.sidebar:
        st.markdown(
            """
            <div style="padding: 0.25rem 0 0.8rem 0; border-bottom: 1px solid #1F2937; margin-bottom: 0.8rem;">
                <h3 style="color: #00F0FF; margin: 0; font-weight: 800; letter-spacing: -0.02em;">⚡ LABFIX ERP</h3>
                <span style="color: #9CA3AF; font-size: 0.76rem;">Microelectrónica, POS & Gestión Operativa v3.0</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Badge de usuario activo
        if current_role == "ADMIN":
            role_label = "👑 Administrador General"
            role_color = "#00F0FF"
        elif current_role == "VENDEDOR":
            role_label = "💳 Mostrador / Comercial"
            role_color = "#10B981"
        else:
            role_label = "🔬 Técnico de Laboratorio"
            role_color = "#8B5CF6"

        st.markdown(
            f"""
            <div style="background: rgba(17, 24, 39, 0.9); border: 1px solid #1F2937; border-left: 3px solid {role_color}; padding: 0.6rem 0.8rem; border-radius: 8px; margin-bottom: 0.75rem;">
                <div style="color: #9CA3AF; font-size: 0.72rem; text-transform: uppercase;">Usuario Conectado</div>
                <div style="color: #FFFFFF; font-weight: 700; font-size: 0.95rem;">{current_nombre}</div>
                <div style="color: {role_color}; font-size: 0.78rem; font-weight: 600;">{role_label} (<span class="tech-mono">@{current_username}</span>)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        c_out1, c_out2 = st.columns([1, 1])
        with c_out1:
            if st.button("🚪 Salir", key="sidebar_btn_logout", use_container_width=True):
                logout_user()
        with c_out2:
            if st.button("📱 Kiosco", key="sidebar_btn_kiosco", use_container_width=True, help="Abrir Terminal de Autoservicio"):
                st.session_state["active_nav_key"] = "kiosco_leads"
                st.rerun()

        st.markdown("<div style='border-top: 1px solid #1F2937; margin: 0.8rem 0;'></div>", unsafe_allow_html=True)

        # Filtrar bloques y secciones según el rol estricto RBAC
        allowed_modules = {}
        for block_name, items in NAV_MODULES.items():
            if current_role == "TECNICO":
                # Técnicos ven Operaciones, Stock, y Soporte (sin configuración general ni finanzas)
                if block_name in ["1. Operaciones & Taller", "3. Logística & Stock", "5. Administración & Sistema"]:
                    allowed_items = [it for it in items if it[0] not in ["admin_config", "stock_etiquetas"]]
                    if allowed_items:
                        allowed_modules[block_name] = allowed_items
            elif current_role == "VENDEDOR":
                # Vendedores ven Mostrador, Operaciones (OTs, Cotizaciones, Garantías), Caja y Stock
                if block_name in ["2. Mostrador & Comercial", "1. Operaciones & Taller", "4. Finanzas & Caja", "3. Logística & Stock", "5. Administración & Sistema"]:
                    allowed_items = [it for it in items if it[0] not in ["oper_tecnicos", "admin_config", "admin_emails", "fin_reportes"]]
                    if allowed_items:
                        allowed_modules[block_name] = allowed_items
            else:
                # ADMIN tiene acceso irrestricto a todos los módulos
                allowed_modules[block_name] = items

        st.markdown("<b style='color: #E5E7EB; font-size: 0.85rem;'>📂 Módulo del Sistema:</b>", unsafe_allow_html=True)
        block_keys = list(allowed_modules.keys())

        # Determinar bloque seleccionado
        default_block_idx = 0
        current_nav_key = st.session_state.get("active_nav_key", "oper_dashboard")
        for i, (b_name, b_items) in enumerate(allowed_modules.items()):
            if any(item[0] == current_nav_key for item in b_items):
                default_block_idx = i
                break

        sel_block = st.selectbox(
            "Seleccionar Módulo:",
            options=block_keys,
            index=default_block_idx,
            label_visibility="collapsed",
            key="erp_nav_block_select",
        )

        # Submódulos del bloque activo
        sub_items = allowed_modules.get(sel_block, [])
        sub_dict = {label: (key, desc) for key, label, desc in sub_items}

        # Índice por defecto para el radio
        default_sub_idx = 0
        for i, (key, label, desc) in enumerate(sub_items):
            if key == current_nav_key:
                default_sub_idx = i
                break

        st.markdown("<b style='color: #9CA3AF; font-size: 0.8rem; margin-top: 0.5rem; display: block;'>Sección:</b>", unsafe_allow_html=True)
        sel_label = st.radio(
            "Seleccionar Sección:",
            options=list(sub_dict.keys()),
            index=default_sub_idx if default_sub_idx < len(sub_dict) else 0,
            label_visibility="collapsed",
            key=f"erp_nav_sub_{sel_block}",
        )

        active_key = sub_dict[sel_label][0]
        st.session_state["active_nav_key"] = active_key

        st.markdown(
            """
            <div style="margin-top: 2rem; color: #6B7280; font-size: 0.72rem; text-align: center; border-top: 1px solid #1F2937; padding-top: 0.8rem;">
                LABFIX Enterprise ERP v3.0<br>
                Motor: SQLite WAL Mode (<code class="tech-mono">repairs.db</code>)
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 3. Enrutamiento y Renderizado del Módulo Activo
    view_func = VIEW_DISPATCHER.get(active_key, render_dashboard_view)
    view_func()


if __name__ == "__main__":
    main()
