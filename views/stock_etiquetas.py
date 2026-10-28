"""Módulo 3.3: Impresión de Etiquetas Térmicas y Códigos de Barras Code 128 (ERP LABFIX)."""

import pandas as pd
import streamlit as st
from components.barcode import generate_code128_svg, render_thermal_label_html
from components.cards import empty_state, format_currency
from database import get_connection, load_stock_df


def render_etiquetas_view() -> None:
    """Renderiza el generador e impresor de etiquetas térmicas para productos y repuestos."""
    org_id = st.session_state.get("organizacion_id", 1)

    st.markdown(
        """
        <div style="margin-bottom: 1.25rem;">
            <h2 style="color: #FFFFFF; font-weight: 800; margin: 0; font-size: 1.6rem; letter-spacing: -0.02em;">
                🏷️ Impresión de Etiquetas Térmicas & Código de Barras
            </h2>
            <span style="color: #9CA3AF; font-size: 0.85rem;">
                Diseñador de etiquetas para impresoras de rollo continuo (58mm, 80mm, 40x25mm, 50x30mm)
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    df_stock = load_stock_df(org_id=org_id)

    if df_stock.empty:
        empty_state("No hay productos en inventario.", "Registra productos en el inventario para imprimir sus etiquetas.")
        return

    col_setup, col_preview = st.columns([1.2, 1])

    with col_setup:
        st.markdown("<b style='color: #00F0FF; font-size: 1rem;'>⚙️ Parámetros de la Etiqueta</b>", unsafe_allow_html=True)

        prods_dict = {f"{r['codigo_sku']} - {r['nombre']} (${r['precio_venta']:,.0f})": r["id"] for _, r in df_stock.iterrows()}
        sel_prod_str = st.selectbox("Seleccionar Producto:", list(prods_dict.keys()), key="lbl_prod_sel")
        p_id = prods_dict[sel_prod_str]
        p_data = df_stock[df_stock["id"] == p_id].iloc[0]

        preset = st.selectbox(
            "Formato de Rollo / Etiqueta Térmica:",
            ["58mm", "80mm", "40x25mm", "50x30mm"],
            index=0,
            key="lbl_preset_sel",
        )

        c1, c2 = st.columns(2)
        with c1:
            titulo_lbl = st.text_input("Título a imprimir:", value=str(p_data["nombre"])[:35], key="lbl_title_in")
            sku_lbl = st.text_input("Código de Barras / SKU:", value=str(p_data["codigo_sku"]), key="lbl_sku_in")
        with c2:
            precio_lbl = st.number_input("Precio Venta ($):", min_value=0.0, value=float(p_data["precio_venta"]), step=500.0, key="lbl_price_in")
            sub_lbl = st.text_input("Subtexto (Categoría / Modelo):", value=str(p_data["categoria"]), key="lbl_sub_in")

        inc_gremio = st.checkbox("¿Incluir Precio Gremio / Técnicos?", value=False, key="lbl_inc_gremio")
        precio_tec = float(p_data.get("precio_venta_tecnicos", 0.0)) if inc_gremio else None

        cant_etiquetas = st.number_input("Cantidad de copias a generar:", min_value=1, max_value=50, value=1, step=1, key="lbl_cant_copies")

    with col_preview:
        st.markdown("<b style='color: #10B981; font-size: 1rem;'>👁️ Vista Previa en Tiempo Real</b>", unsafe_allow_html=True)

        label_single_html = render_thermal_label_html(
            titulo=titulo_lbl,
            codigo_sku=sku_lbl,
            precio=precio_lbl,
            subtexto=sub_lbl,
            preset=preset,
            precio_tecnicos=precio_tec,
        )

        # Generar HTML con hojas repetidas para impresión
        labels_sheet_html = f"""
        <html>
        <head>
            <style>
                @media print {{
                    body {{ margin: 0; padding: 0; background: #FFFFFF; }}
                    .thermal-label-container {{ page-break-after: always; margin: 0 auto !important; border: none !important; }}
                }}
            </style>
        </head>
        <body style="background: transparent;">
            {''.join([label_single_html for _ in range(cant_etiquetas)])}
        </body>
        </html>
        """

        st.components.v1.html(labels_sheet_html, height=360, scrolling=True)

        st.download_button(
            label=f"🖨️ Descargar Archivo de Impresión ({cant_etiquetas} u.)",
            data=labels_sheet_html,
            file_name=f"Etiquetas_{sku_lbl}_{preset}.html",
            mime="text/html",
            use_container_width=True,
            key="lbl_btn_download_html",
        )

