"""Módulo 2.2: Historial de Ventas POS y Reimpresión de Comprobantes (ERP LABFIX)."""

from datetime import date
from typing import Any, Dict
import pandas as pd
import streamlit as st
from components.cards import empty_state, format_currency, format_number, metric_card
from components.receipt import render_pos_ticket_receipt
from database import get_connection, get_workshop_config


def render_ventas_view() -> None:
    """Renderiza el libro histórico de ventas de mostrador con filtros y reimpresión."""
    st.markdown(
        """
        <div style="margin-bottom: 1.25rem;">
            <h2 style="color: #FFFFFF; font-weight: 800; margin: 0; font-size: 1.6rem; letter-spacing: -0.02em;">
                🧾 Historial de Ventas de Mostrador
            </h2>
            <span style="color: #9CA3AF; font-size: 0.85rem;">
                Registro histórico de comprobantes emitidos en el Punto de Venta y reimpresión térmica
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    conn = get_connection()
    config_taller = get_workshop_config()

    # Cargar ventas con clientes y vendedores
    sql_ventas = """
        SELECT 
            v.id, v.numero_ticket, v.subtotal, v.descuento, v.recargo, v.total,
            v.metodo_pago, v.notas, v.creado_en,
            c.nombre as cliente_nombre, c.dni_cuit as cliente_dni,
            u.nombre as vendedor_nombre
        FROM ventas v
        LEFT JOIN clientes c ON v.cliente_id = c.id
        LEFT JOIN usuarios u ON v.vendedor_id = u.id
        ORDER BY v.creado_en DESC, v.id DESC
    """
    df_ventas = pd.read_sql_query(sql_ventas, conn)

    if df_ventas.empty:
        empty_state("No hay ventas registradas todavía.", "Las ventas concretadas desde el Punto de Venta se listarán aquí.")
        return

    df_ventas["cliente_nombre"] = df_ventas["cliente_nombre"].fillna("Consumidor Final")
    df_ventas["vendedor_nombre"] = df_ventas["vendedor_nombre"].fillna("Sistema")
    df_ventas["fecha_dt"] = pd.to_datetime(df_ventas["creado_en"], errors="coerce")

    # Métricas
    total_facturado = df_ventas["total"].sum()
    total_tickets = len(df_ventas)
    ticket_promedio = total_facturado / total_tickets if total_tickets > 0 else 0.0

    k1, k2, k3 = st.columns(3)
    with k1:
        metric_card("Total Ventas Mostrador", format_currency(total_facturado), glow_color="green")
    with k2:
        metric_card("Tickets Emitidos", f"{total_tickets} ventas", glow_color="cyan")
    with k3:
        metric_card("Ticket Promedio", format_currency(ticket_promedio), glow_color="purple")

    st.markdown("<hr style='border-color: #1F2937; margin: 1.5rem 0;'>", unsafe_allow_html=True)

    # Filtros
    f1, f2, f3 = st.columns([2, 1, 1])
    with f1:
        q_text = st.text_input("Filtrar por Ticket o Cliente:", placeholder="TCK-..., Juan Perez...", key="ventas_filter_q")
    with f2:
        metodos = ["Todos"] + sorted(list(df_ventas["metodo_pago"].unique()))
        sel_metodo = st.selectbox("Medio de Pago:", metodos, key="ventas_filter_metodo")
    with f3:
        vendedores = ["Todos"] + sorted(list(df_ventas["vendedor_nombre"].unique()))
        sel_ven = st.selectbox("Vendedor:", vendedores, key="ventas_filter_ven")

    df_filtrado = df_ventas.copy()
    if q_text.strip():
        term = q_text.strip().lower()
        df_filtrado = df_filtrado[
            df_filtrado["numero_ticket"].str.lower().str.contains(term, na=False)
            | df_filtrado["cliente_nombre"].str.lower().str.contains(term, na=False)
        ]
    if sel_metodo != "Todos":
        df_filtrado = df_filtrado[df_filtrado["metodo_pago"] == sel_metodo]
    if sel_ven != "Todos":
        df_filtrado = df_filtrado[df_filtrado["vendedor_nombre"] == sel_ven]

    # Tabla interactiva
    st.dataframe(
        df_filtrado[["numero_ticket", "creado_en", "cliente_nombre", "vendedor_nombre", "metodo_pago", "subtotal", "descuento", "total"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "numero_ticket": st.column_config.TextColumn("Nº Ticket", width="small"),
            "creado_en": st.column_config.TextColumn("Fecha / Hora", width="medium"),
            "cliente_nombre": st.column_config.TextColumn("Cliente", width="medium"),
            "vendedor_nombre": st.column_config.TextColumn("Vendedor", width="small"),
            "metodo_pago": st.column_config.TextColumn("Medio de Pago", width="small"),
            "subtotal": st.column_config.NumberColumn("Subtotal", format="$%.0f"),
            "descuento": st.column_config.NumberColumn("Desc.", format="$%.0f"),
            "total": st.column_config.NumberColumn("Total", format="$%.0f"),
        },
    )

    # Detalle e Impresión de Ticket
    st.markdown("<b style='color: #00F0FF; font-size: 1rem;'>🔍 Detalle y Reimpresión de Comprobante</b>", unsafe_allow_html=True)
    list_tcks = df_filtrado["numero_ticket"].tolist()

    if list_tcks:
        sel_tck = st.selectbox("Seleccionar Ticket a Inspeccionar:", list_tcks, key="ventas_inspect_sel")
        row_sel = df_filtrado[df_filtrado["numero_ticket"] == sel_tck].iloc[0]
        v_id = int(row_sel["id"])

        items_rows = conn.execute(
            """
            SELECT i.cantidad, i.precio_unitario, i.subtotal, p.nombre, p.codigo_sku
            FROM ventas_items i
            JOIN productos_stock p ON i.producto_id = p.id
            WHERE i.venta_id = ?
            """,
            (v_id,),
        ).fetchall()

        c_det, c_print = st.columns([1, 1])
        with c_det:
            st.markdown(
                f"""
                <div style="background: #111827; border: 1px solid #1F2937; border-radius: 8px; padding: 15px;">
                    <div style="font-size: 1.1rem; font-weight: bold; color: #FFFFFF;">Ticket #{sel_tck}</div>
                    <div style="color: #9CA3AF; font-size: 0.85rem; margin-top: 4px;">
                        <b>Cliente:</b> {row_sel['cliente_nombre']}<br>
                        <b>Fecha:</b> {row_sel['creado_en']}<br>
                        <b>Medio de Pago:</b> {row_sel['metodo_pago']}<br>
                        <b>Atendido por:</b> {row_sel['vendedor_nombre']}
                    </div>
                    <div style="margin-top: 10px; border-top: 1px solid #374151; padding-top: 8px;">
                        <b style="color: #E5E7EB; font-size: 0.85rem;">Artículos ({len(items_rows)}):</b>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            for it in items_rows:
                st.markdown(
                    f"<div style='font-size: 0.82rem; color: #D1D5DB; background: #1F2937; padding: 5px 10px; border-radius: 4px; margin-top: 4px; display: flex; justify-content: space-between;'>"
                    f"<span>• {it['nombre']} (x{it['cantidad']})</span>"
                    f"<b style='color: #10B981;'>${it['subtotal']:,.0f}</b>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        with c_print:
            tck_html = render_pos_ticket_receipt(
                sale=dict(row_sel),
                items=[dict(r) for r in items_rows],
                config=config_taller,
            )
            st.components.v1.html(tck_html, height=380, scrolling=True)
            st.download_button(
                "📥 Descargar Copia Térmica",
                data=tck_html,
                file_name=f"Reimpresion_{sel_tck}.html",
                mime="text/html",
                key=f"ventas_dl_{sel_tck}",
            )

