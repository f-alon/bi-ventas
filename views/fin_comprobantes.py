"""Módulo 4.2: Comprobantes Oficiales, Remitos y Notas de Crédito con Compensación (ERP LABFIX)."""

from typing import Any, Dict
import pandas as pd
import streamlit as st
from components.cards import empty_state, format_currency, format_number, metric_card
from database import create_credit_note, get_all_clients, get_connection, load_stock_df


def render_comprobantes_view() -> None:
    """Renderiza el libro oficial de comprobantes y notas de crédito con compensación de cuenta corriente."""
    user = st.session_state.get("username", "admin")
    org_id = st.session_state.get("organizacion_id", 1)

    st.markdown(
        """
        <div style="margin-bottom: 1.25rem;">
            <h2 style="color: #FFFFFF; font-weight: 800; margin: 0; font-size: 1.6rem; letter-spacing: -0.02em;">
                📑 Remitos Oficiales & Notas de Crédito (NC)
            </h2>
            <span style="color: #9CA3AF; font-size: 0.85rem;">
                Registro de remitos de entrega y emisión de notas de crédito con compensación automática de deuda
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    conn = get_connection()

    t_list, t_nc = st.tabs(["📋 Libro de Comprobantes", "🔄 Emitir Nota de Crédito / Devolución"])

    # 1. PESTAÑA EMISIÓN NOTA DE CRÉDITO
    with t_nc:
        st.markdown("<b style='color: #F43F5E; font-size: 1rem;'>Emisión de Nota de Crédito</b>", unsafe_allow_html=True)
        st.markdown(
            """
            <div style="background: rgba(244, 63, 94, 0.08); border: 1px solid rgba(244, 63, 94, 0.3); padding: 10px; border-radius: 6px; font-size: 0.82rem; color: #E5E7EB; margin-bottom: 12px;">
                💡 <b>Regla Financiera de Compensación:</b> Si el cliente posee deuda en cuenta corriente, la Nota de Crédito 
                compensará y descontará prioritariamente ese saldo antes de registrar cualquier salida física de efectivo en caja.
            </div>
            """,
            unsafe_allow_html=True,
        )

        clients = get_all_clients(org_id=org_id)
        client_dict = {f"{c['nombre']} (Saldo cta: {format_currency(c['saldo_cuenta_corriente'])})": c for c in clients}

        df_stock = load_stock_df(org_id=org_id)
        stock_dict = {f"{r['codigo_sku']} - {r['nombre']}": r["id"] for _, r in df_stock.iterrows()} if not df_stock.empty else {}

        with st.form(key="form_emitir_nc_comp"):
            c_e1, c_e2 = st.columns(2)
            with c_e1:
                t_entidad = st.selectbox("Origen de la Devolución:", ["VENTA", "ORDEN"], key="nc_entidad_type")
                entidad_id_in = st.number_input("ID o Nº de Referencia:", min_value=1, value=1, step=1, key="nc_ref_id")
            with c_e2:
                sel_cli_str = st.selectbox("Cliente Beneficiario:", list(client_dict.keys()) if client_dict else ["Sin clientes"], key="nc_cli_sel")
                monto_nc = st.number_input("Monto a Reintegrar ($):", min_value=0.0, value=5000.0, step=500.0, key="nc_monto_in")

            motivo_nc = st.text_input("Motivo Detallado de la Devolución *", placeholder="Ej: Falla de fábrica dentro de las 72hs de retiro...", key="nc_motivo_in")

            reintegra = st.checkbox("¿Reponer artículo devuelto al inventario de stock?", value=False, key="nc_reintegra_chk")
            prod_sel_id = None
            cant_dev = 1

            if reintegra and stock_dict:
                c_p1, c_p2 = st.columns([3, 1])
                with c_p1:
                    sel_prod_nc = st.selectbox("Producto a Reingresar:", list(stock_dict.keys()), key="nc_prod_sel")
                    prod_sel_id = stock_dict[sel_prod_nc]
                with c_p2:
                    cant_dev = st.number_input("Cantidad:", min_value=1, value=1, step=1, key="nc_prod_cant")

            submit_nc = st.form_submit_button("🔄 Confirmar y Emitir Nota de Crédito", use_container_width=True)
            if submit_nc:
                if not motivo_nc.strip():
                    st.error("El motivo de la devolución es obligatorio.")
                else:
                    cli_id = client_dict[sel_cli_str]["id"] if client_dict else None
                    nc_code = create_credit_note(
                        entidad_tipo=t_entidad,
                        entidad_id=entidad_id_in,
                        cliente_id=cli_id,
                        monto=monto_nc,
                        motivo=motivo_nc.strip(),
                        reintegra_stock=reintegra,
                        producto_id=prod_sel_id,
                        cantidad=cant_dev,
                        user=user,
                        org_id=org_id,
                    )
                    st.toast(f"✅ Nota de Crédito {nc_code} emitida", icon="🔄")
                    st.rerun()

    # 2. PESTAÑA LISTADO DE COMPROBANTES
    with t_list:
        sub_t1, sub_t2 = st.tabs(["📑 Remitos Oficiales", "🔄 Notas de Crédito Emitidas"])

        with sub_t1:
            sql_rem = """
                SELECT r.*, c.nombre as cliente_nombre, o.ot_codigo, o.marca, o.modelo
                FROM remitos r
                LEFT JOIN clientes c ON r.cliente_id = c.id
                LEFT JOIN ordenes_servicio o ON r.orden_id = o.id
                WHERE r.organizacion_id = ?
                ORDER BY r.id DESC
            """
            rows_rem = conn.execute(sql_rem, (org_id,)).fetchall()
            if not rows_rem:
                empty_state("No hay remitos oficiales emitidos.")
            else:
                df_rem = pd.DataFrame([dict(r) for r in rows_rem])
                st.dataframe(
                    df_rem[["codigo_remito", "created_at", "cliente_nombre", "ot_codigo", "total", "saldo_pendiente", "estado_pago"]],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "total": st.column_config.NumberColumn("Total", format="$%d"),
                        "saldo_pendiente": st.column_config.NumberColumn("Saldo Pendiente", format="$%d"),
                    },
                )

        with sub_t2:
            sql_nc = """
                SELECT nc.*, c.nombre as cliente_nombre
                FROM notas_credito nc
                LEFT JOIN clientes c ON nc.cliente_id = c.id
                WHERE nc.organizacion_id = ?
                ORDER BY nc.id DESC
            """
            rows_nc = conn.execute(sql_nc, (org_id,)).fetchall()
            if not rows_nc:
                empty_state("No se han emitido notas de crédito.")
            else:
                df_nc = pd.DataFrame([dict(r) for r in rows_nc])
                st.dataframe(
                    df_nc[["codigo_nc", "created_at", "cliente_nombre", "entidad_tipo", "monto", "monto_compensado_cta_cte", "monto_efectivo_devuelto", "motivo"]],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "monto": st.column_config.NumberColumn("Total NC ($)", format="$%d"),
                        "monto_compensado_cta_cte": st.column_config.NumberColumn("Compensado Deuda ($)", format="$%d"),
                        "monto_efectivo_devuelto": st.column_config.NumberColumn("Efectivo Devuelto ($)", format="$%d"),
                    },
                )
