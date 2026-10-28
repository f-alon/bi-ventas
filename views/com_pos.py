"""Módulo 2.1: Punto de Venta (POS), Lector de Código de Barras y Cálculo de Vuelto (ERP LABFIX)."""

from datetime import date
from typing import Any, Dict, List
import streamlit as st
from components.cards import empty_state, format_currency, metric_card
from components.receipt import render_pos_ticket_receipt
from core.config import METODOS_PAGO
from database import (
    get_active_cash_session,
    get_all_clients,
    get_connection,
    get_workshop_config,
    open_cash_session,
    process_pos_sale,
)


def render_pos_view() -> None:
    """Renderiza el terminal POS de mostrador con lector de código de barras y cálculo de vuelto."""
    user_name = st.session_state.get("username", "cajero")
    user_id = st.session_state.get("user_id", 1)
    org_id = st.session_state.get("organizacion_id", 1)

    st.markdown(
        """
        <div style="margin-bottom: 1.25rem;">
            <h2 style="color: #FFFFFF; font-weight: 800; margin: 0; font-size: 1.6rem; letter-spacing: -0.02em;">
                💳 Punto de Venta (POS) & Mostrador
            </h2>
            <span style="color: #9CA3AF; font-size: 0.85rem;">
                Facturación ágil de accesorios, insumos, repuestos, cálculo de vuelto y tickets térmicos
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Validar sesión de caja activa
    sesion_activa = get_active_cash_session(org_id=org_id)
    if not sesion_activa:
        st.warning("⚠️ No hay una sesión de caja abierta en este momento. Es obligatorio abrir turno para registrar operaciones.")
        with st.expander("💵 Apertura Rápida de Turno de Caja", expanded=True):
            monto_ini = st.number_input("Fondo inicial de cambio en efectivo ($):", min_value=0.0, value=20000.0, step=1000.0, key="pos_quick_open_cash")
            if st.button("🚀 Abrir Turno de Caja Ahora", type="primary", key="pos_btn_open_cash"):
                open_cash_session(user_id, monto_ini, org_id=org_id)
                st.toast("✅ Caja abierta exitosamente", icon="💵")
                st.rerun()

    if "pos_cart" not in st.session_state:
        st.session_state["pos_cart"] = []

    conn = get_connection()
    config_taller = get_workshop_config(org_id=org_id)

    col_catalog, col_cart = st.columns([3, 2.2])

    with col_catalog:
        st.markdown("<b style='color: #00F0FF; font-size: 1rem;'>🔍 Búsqueda & Lector de Código de Barras</b>", unsafe_allow_html=True)
        q_search = st.text_input(
            "Buscar por Nombre, SKU o Código de Barras (Presiona Enter tras pistola láser):",
            placeholder="Escanea el código o tipea: Templado, Batería, CAB-IPH...",
            key="pos_search_input",
        )

        # Cargar productos disponibles
        sql_prod = """
            SELECT id, codigo_sku, codigo_barras, categoria, subcategoria, nombre, precio_venta, stock_actual
            FROM productos
            WHERE organizacion_id = ? AND stock_actual > 0
        """
        params_prod = [org_id]
        if q_search.strip():
            sql_prod += " AND (nombre LIKE ? OR codigo_sku LIKE ? OR codigo_barras LIKE ? OR categoria LIKE ?)"
            term = f"%{q_search.strip()}%"
            params_prod.extend([term, term, term, term])

        sql_prod += " ORDER BY nombre ASC LIMIT 25"
        prods_list = conn.execute(sql_prod, params_prod).fetchall()

        if not prods_list:
            empty_state("No se encontraron productos disponibles con stock.", "Revisa el término de búsqueda o repón stock en Inventario.")
        else:
            for p in prods_list:
                p_id = int(p["id"])
                p_sku = str(p["codigo_sku"])
                p_nom = str(p["nombre"])
                p_precio = float(p["precio_venta"])
                p_stock = int(p["stock_actual"])

                c_info, c_btn = st.columns([4, 1])
                with c_info:
                    st.markdown(
                        f"""
                        <div style="background: #111827; border: 1px solid #1F2937; border-radius: 6px; padding: 8px 12px; margin-bottom: 6px;">
                            <div style="display: flex; justify-content: space-between;">
                                <b style="color: #F9FAFB; font-size: 0.9rem;">{p_nom}</b>
                                <span style="color: #10B981; font-weight: 800; font-size: 0.95rem;">{format_currency(p_precio)}</span>
                            </div>
                            <div style="color: #9CA3AF; font-size: 0.75rem; margin-top: 2px;">
                                SKU: <code>{p_sku}</code> | Cat: {p['categoria']} | <b>Stock: {p_stock} u.</b>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with c_btn:
                    st.write("")
                    if st.button("➕ Agregar", key=f"pos_add_{p_id}", use_container_width=True):
                        cart = st.session_state["pos_cart"]
                        found = False
                        for it in cart:
                            if it["id"] == p_id:
                                if it["cantidad"] < p_stock:
                                    it["cantidad"] += 1
                                    st.toast(f"Sumado: {p_nom} (x{it['cantidad']})")
                                else:
                                    st.warning("Stock máximo alcanzado")
                                found = True
                                break
                        if not found:
                            cart.append({
                                "id": p_id,
                                "sku": p_sku,
                                "nombre": p_nom,
                                "precio": p_precio,
                                "cantidad": 1,
                                "stock_max": p_stock,
                            })
                            st.toast(f"Agregado: {p_nom}")
                        st.rerun()

    with col_cart:
        st.markdown("<b style='color: #10B981; font-size: 1rem;'>🛒 Carrito de Venta en Mostrador</b>", unsafe_allow_html=True)

        cart = st.session_state["pos_cart"]

        if not cart:
            st.markdown(
                """
                <div style="border: 2px dashed #374151; border-radius: 8px; padding: 25px; text-align: center; color: #6B7280;">
                    El carrito está vacío.<br>Selecciona artículos del catálogo a la izquierda.
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            subtotal = 0.0
            for idx, it in enumerate(cart):
                it_sub = it["precio"] * it["cantidad"]
                subtotal += it_sub

                c_item_desc, c_item_qty, c_item_del = st.columns([3, 1, 1])
                with c_item_desc:
                    st.markdown(f"<span style='font-size: 0.85rem; color: #FFFFFF;'><b>{it['nombre']}</b><br><span style='color: #9CA3AF; font-size: 0.75rem;'>{format_currency(it['precio'])} c/u</span></span>", unsafe_allow_html=True)
                with c_item_qty:
                    new_q = st.number_input("Cant", min_value=1, max_value=it["stock_max"], value=it["cantidad"], key=f"pos_qty_{it['id']}_{idx}", label_visibility="collapsed")
                    it["cantidad"] = new_q
                with c_item_del:
                    if st.button("🗑️", key=f"pos_del_{it['id']}_{idx}"):
                        cart.pop(idx)
                        st.rerun()

            st.markdown("<hr style='border-color: #374151; margin: 10px 0;'>", unsafe_allow_html=True)

            clients_list = get_all_clients(org_id=org_id)
            client_dict = {"Consumidor Final": None}
            for c in clients_list:
                client_dict[f"{c['nombre']} ({c['telefono'] or 'S/D'})"] = int(c["id"])

            sel_client_name = st.selectbox("Cliente:", list(client_dict.keys()), key="pos_client_sel")
            selected_client_id = client_dict[sel_client_name]

            vendedores_rows = conn.execute("SELECT id, nombre FROM usuarios WHERE organizacion_id = ? AND rol IN ('VENDEDOR', 'ADMIN')", (org_id,)).fetchall()
            ven_dict = {r["nombre"]: int(r["id"]) for r in vendedores_rows}
            ven_sel = st.selectbox("Atendido por:", list(ven_dict.keys()), key="pos_ven_sel")
            selected_ven_id = ven_dict.get(ven_sel)

            c_desc, c_rec = st.columns(2)
            with c_desc:
                descuento = st.number_input("Descuento ($):", min_value=0.0, value=0.0, step=100.0, key="pos_discount_input")
            with c_rec:
                recargo = st.number_input("Recargo ($):", min_value=0.0, value=0.0, step=100.0, key="pos_surcharge_input")

            metodo = st.selectbox("Medio de Pago:", METODOS_PAGO, key="pos_payment_method")

            total = max(0.0, subtotal - descuento + recargo)

            # Cálculo de vuelto en efectivo
            vuelto_html = ""
            if metodo == "Efectivo":
                paga_con = st.number_input("Paga con billetes de ($):", min_value=0.0, value=float(total), step=1000.0, key="pos_cash_tendered")
                vuelto = max(0.0, paga_con - total)
                vuelto_html = f"""
                <div style="display: flex; justify-content: space-between; font-size: 1rem; color: #00F0FF; margin-top: 4px;">
                    <span>VUELTO A ENTREGAR:</span>
                    <b>{format_currency(vuelto)}</b>
                </div>
                """

            st.markdown(
                f"""
                <div style="background: #1F2937; padding: 12px; border-radius: 8px; margin: 12px 0; border: 1px solid #374151;">
                    <div style="display: flex; justify-content: space-between; font-size: 0.85rem; color: #9CA3AF;">
                        <span>Subtotal:</span>
                        <span>{format_currency(subtotal)}</span>
                    </div>
                    {f'<div style="display: flex; justify-content: space-between; font-size: 0.85rem; color: #F43F5E;"><span>Descuento:</span><span>-{format_currency(descuento)}</span></div>' if descuento > 0 else ''}
                    {f'<div style="display: flex; justify-content: space-between; font-size: 0.85rem; color: #F59E0B;"><span>Recargo:</span><span>+{format_currency(recargo)}</span></div>' if recargo > 0 else ''}
                    <div style="display: flex; justify-content: space-between; font-size: 1.25rem; font-weight: 800; color: #10B981; border-top: 1px solid #4B5563; padding-top: 8px; margin-top: 6px;">
                        <span>TOTAL A COBRAR:</span>
                        <span>{format_currency(total)}</span>
                    </div>
                    {vuelto_html}
                </div>
                """,
                unsafe_allow_html=True,
            )

            c_cobrar, c_vaciar = st.columns([2, 1])
            with c_cobrar:
                if st.button("⚡ Cobrar y Emitir Ticket", type="primary", use_container_width=True, key="pos_btn_submit_sale"):
                    ticket_code = process_pos_sale(
                        cliente_id=selected_client_id,
                        vendedor_id=selected_ven_id,
                        items=cart,
                        metodo_pago=metodo,
                        descuento=descuento,
                        recargo=recargo,
                        user=user_name,
                        org_id=org_id,
                    )
                    st.session_state["pos_last_ticket"] = {
                        "ticket": ticket_code,
                        "cliente_nombre": sel_client_name,
                        "metodo_pago": metodo,
                        "subtotal": subtotal,
                        "descuento": descuento,
                        "recargo": recargo,
                        "total": total,
                        "items": list(cart),
                    }
                    st.session_state["pos_cart"] = []
                    st.toast(f"✅ Venta {ticket_code} concretada", icon="💳")
                    st.rerun()

            with c_vaciar:
                if st.button("🗑️ Vaciar", use_container_width=True, key="pos_btn_clear_cart"):
                    st.session_state["pos_cart"] = []
                    st.rerun()

    # Modal / Vista de ticket emitido recientemente
    if "pos_last_ticket" in st.session_state and st.session_state["pos_last_ticket"]:
        last = st.session_state["pos_last_ticket"]
        st.markdown("<hr style='border-color: #374151; margin: 2rem 0;'>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='color: #10B981;'>🧾 Ticket Emitido #{last['ticket']}</h3>", unsafe_allow_html=True)

        ticket_html = render_pos_ticket_receipt(
            sale={
                "numero_ticket": last["ticket"],
                "cliente_nombre": last["cliente_nombre"],
                "metodo_pago": last["metodo_pago"],
                "subtotal": last["subtotal"],
                "descuento": last["descuento"],
                "recargo": last["recargo"],
                "total": last["total"],
                "creado_en": str(date.today()),
            },
            items=[{"nombre": it["nombre"], "cantidad": it["cantidad"], "precio_unitario": it["precio"]} for it in last["items"]],
            config=config_taller,
        )

        c_tck, c_opts = st.columns([1, 1])
        with c_tck:
            st.components.v1.html(ticket_html, height=450, scrolling=True)
        with c_opts:
            st.info("Imprime o envía el ticket al cliente.")
            st.download_button(
                "📥 Descargar Ticket HTML",
                data=ticket_html,
                file_name=f"Ticket_{last['ticket']}.html",
                mime="text/html",
                key="pos_download_ticket_btn",
            )
            if st.button("Cerrar Vista de Ticket", key="pos_close_last_ticket"):
                st.session_state["pos_last_ticket"] = None
                st.rerun()
