"""Módulo 3.2: Directorio de Proveedores y Control de Compras de Repuestos (ERP LABFIX)."""

from typing import Any, Dict
import pandas as pd
import streamlit as st
from components.cards import empty_state, format_currency, metric_card
from database import get_connection, log_audit


def render_proveedores_view() -> None:
    """Renderiza el directorio de proveedores de repuestos, insumos y compras."""
    user = st.session_state.get("username", "admin")

    st.markdown(
        """
        <div style="margin-bottom: 1.25rem;">
            <h2 style="color: #FFFFFF; font-weight: 800; margin: 0; font-size: 1.6rem; letter-spacing: -0.02em;">
                🚚 Proveedores & Gestión de Compras
            </h2>
            <span style="color: #9CA3AF; font-size: 0.85rem;">
                Directorio comercial de distribuidores de displays, componentes electrónicos y herramientas
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    conn = get_connection()
    rows_prov = conn.execute("SELECT * FROM proveedores ORDER BY razon_social ASC").fetchall()

    t_dir, t_new = st.tabs(["📋 Directorio de Proveedores", "➕ Alta de Proveedor"])

    with t_new:
        st.markdown("<b style='color: #00F0FF; font-size: 1rem;'>Registrar Nuevo Proveedor</b>", unsafe_allow_html=True)
        with st.form(key="form_alta_proveedor"):
            c1, c2 = st.columns(2)
            with c1:
                rs = st.text_input("Razón Social / Nombre Comercial *", placeholder="Distribuidora Celular S.A.", key="prov_rs_in")
                ct = st.text_input("Contacto / Asesor de Ventas", placeholder="Martín Gómez", key="prov_ct_in")
                tel = st.text_input("Teléfono / WhatsApp *", placeholder="+54 9 11 3456-7890", key="prov_tel_in")
            with c2:
                em = st.text_input("Email Comercial", placeholder="ventas@districel.com", key="prov_em_in")
                dir_p = st.text_input("Dirección / Depósito", placeholder="Av. Corrientes 1234, CABA", key="prov_dir_in")
                rubro = st.selectbox("Rubro Principal:", ["Módulos & Displays OLED", "Baterías & Cargas", "Microelectrónica & Stencils", "Herramientas de Banco", "Accesorios & Fundas", "Varios / General"], key="prov_rubro_in")

            submit_prov = st.form_submit_button("💾 Guardar Proveedor", use_container_width=True)
            if submit_prov:
                if not rs.strip() or not tel.strip():
                    st.error("Razón social y teléfono son requeridos.")
                else:
                    try:
                        with conn:
                            conn.execute(
                                """
                                INSERT INTO proveedores (razon_social, contacto, telefono, email, direccion, rubro)
                                VALUES (?, ?, ?, ?, ?, ?)
                                """,
                                (rs.strip(), ct.strip(), tel.strip(), em.strip(), dir_p.strip(), rubro),
                            )
                        log_audit(user, "proveedores", rs.strip(), "ALTA_PROVEEDOR", f"Rubro: {rubro}")
                        st.toast(f"✅ Proveedor {rs} guardado", icon="🚚")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar proveedor: {e}")

    with t_dir:
        if not rows_prov:
            empty_state("No hay proveedores registrados.", "Agrega proveedores desde la pestaña de alta.")
            return

        df_prov = pd.DataFrame([dict(r) for r in rows_prov])

        st.dataframe(
            df_prov[["id", "razon_social", "contacto", "telefono", "email", "rubro", "direccion"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": st.column_config.NumberColumn("ID", width="small"),
                "razon_social": st.column_config.TextColumn("Razón Social", width="medium"),
                "contacto": st.column_config.TextColumn("Contacto", width="small"),
                "telefono": st.column_config.TextColumn("Teléfono", width="small"),
                "email": st.column_config.TextColumn("Email", width="medium"),
                "rubro": st.column_config.TextColumn("Especialidad / Rubro", width="medium"),
                "direccion": st.column_config.TextColumn("Dirección", width="medium"),
            },
        )

        st.markdown("<hr style='border-color: #1F2937; margin: 1.5rem 0;'>", unsafe_allow_html=True)

        # Repuestos asociados a cada proveedor
        st.markdown("<b style='color: #00F0FF; font-size: 1rem;'>📦 Artículos Provistos por Distribuidor</b>", unsafe_allow_html=True)
        prov_dict = {f"#{p['id']} - {p['razon_social']}": p["id"] for _, p in df_prov.iterrows()}
        sel_prov_str = st.selectbox("Seleccionar Proveedor:", list(prov_dict.keys()), key="prov_inspect_sel")
        p_id = prov_dict[sel_prov_str]

        articulos_prov = conn.execute(
            """
            SELECT codigo_sku, nombre, categoria, costo_compra, precio_venta, stock_actual
            FROM productos_stock
            WHERE proveedor_id = ?
            ORDER BY nombre ASC
            """,
            (p_id,),
        ).fetchall()

        if not articulos_prov:
            st.caption("Este proveedor no tiene artículos vinculados actualmente.")
        else:
            df_art = pd.DataFrame([dict(r) for r in articulos_prov])
            st.dataframe(
                df_art,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "codigo_sku": st.column_config.TextColumn("SKU", width="small"),
                    "nombre": st.column_config.TextColumn("Descripción", width="large"),
                    "categoria": st.column_config.TextColumn("Categoría", width="small"),
                    "costo_compra": st.column_config.NumberColumn("Costo Compra", format="$%.0f"),
                    "precio_venta": st.column_config.NumberColumn("Precio Venta", format="$%.0f"),
                    "stock_actual": st.column_config.NumberColumn("Stock", width="small"),
                },
            )

