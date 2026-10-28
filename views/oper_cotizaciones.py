"""Módulo 1.3: Cotizaciones Formales, Firma Digital y Conversión a Remito (ERP LABFIX)."""

import base64
from datetime import date
import pandas as pd
import streamlit as st
from components.cards import empty_state, format_currency
from core.config import ALICUOTAS_IVA, ESTADOS_COTIZACION
from database import (
    approve_quote,
    convert_quote_to_remito,
    create_quote,
    get_all_clients,
    get_connection,
    get_next_code,
    get_or_create_client,
    get_workshop_config,
    load_orders_df,
)


def render_cotizaciones_view() -> None:
    """Gestión integral de cotizaciones, firma digital y conversión a remito."""
    st.markdown(
        """
        <div style="margin-bottom: 1rem;">
            <h2 style="color: #FFFFFF; font-weight: 800; margin: 0; font-size: 1.5rem; letter-spacing: -0.02em;">
                📋 Cotizaciones, Firma Digital & Conversión a Remito
            </h2>
            <span style="color: #9CA3AF; font-size: 0.85rem;">
                Desglose impositivo con alícuotas de IVA, referencia en USD, captura de firma y paso a remito
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_list, tab_new = st.tabs(["📑 Listado de Cotizaciones", "➕ Emitir Nueva Cotización"])

    with tab_new:
        render_nueva_cotizacion_form()

    with tab_list:
        render_listado_cotizaciones()


def render_nueva_cotizacion_form() -> None:
    """Formulario para emitir cotización con IVA y cotización USD."""
    org_id = st.session_state.get("organizacion_id", 1)
    st.markdown("<b style='color: #00F0FF; font-size: 1rem;'>Nueva Cotización Formal</b>", unsafe_allow_html=True)

    df_orders = load_orders_df(org_id=org_id)
    all_clients = get_all_clients(org_id=org_id)

    c_link, c_val = st.columns([1.5, 1])
    with c_link:
        opciones_ot = ["Sin vincular a OT (Presupuesto Libre)"] + [f"{o['ot_codigo']} - {o['marca']} {o['modelo']} ({o['cliente_nombre']})" for _, o in df_orders.iterrows()]
        ot_choice = st.selectbox("Vincular a Orden de Servicio:", options=opciones_ot, key="cot_sel_ot")

    with c_val:
        validez = st.number_input("Validez del Presupuesto (Días):", min_value=1, max_value=90, value=15, key="cot_validez")

    ot_id = None
    cliente_id = None
    if ot_choice != "Sin vincular a OT (Presupuesto Libre)":
        ot_idx = opciones_ot.index(ot_choice) - 1
        sel_ot = df_orders.iloc[ot_idx]
        ot_id = int(sel_ot["id"])
        cliente_id = int(sel_ot["cliente_id"])
        st.info(f"Cliente vinculado: **{sel_ot['cliente_nombre']}** | Equipo: **{sel_ot['marca']} {sel_ot['modelo']}**")
    else:
        opciones_cli = [f"{c['nombre']} (Tel: {c['telefono']})" for c in all_clients]
        if opciones_cli:
            cli_sel = st.selectbox("Cliente:", options=opciones_cli, key="cot_sel_cli")
            cliente_id = all_clients[opciones_cli.index(cli_sel)]["id"]
        else:
            cli_nom = st.text_input("Nombre de Cliente:", key="cot_cli_new")
            cli_tel = st.text_input("Teléfono:", key="cot_cli_tel")
            if cli_nom and cli_tel:
                cliente_id = get_or_create_client(cli_nom, cli_tel, org_id=org_id)

    st.markdown("<div style='border-top: 1px solid #1F2937; margin: 0.75rem 0;'></div>", unsafe_allow_html=True)

    c_sub, c_desc, c_iva, c_usd = st.columns(4)
    with c_sub:
        subtotal_in = st.number_input("Subtotal Neto Gravado ($):", min_value=0.0, value=50000.0, step=1000.0, key="cot_subtotal")
    with c_desc:
        desc_in = st.number_input("Descuento Comercial ($):", min_value=0.0, value=0.0, step=500.0, key="cot_desc")
    with c_iva:
        alicuota_iva = st.selectbox("Alícuota de IVA (%):", ALICUOTAS_IVA, index=2, key="cot_iva_sel")
    with c_usd:
        usd_rate = st.number_input("Cotización Dólar Referencia (USD):", min_value=1.0, value=1250.0, step=10.0, key="cot_usd_rate")

    base_imp = max(0.0, subtotal_in - desc_in)
    iva_calc = base_imp * (alicuota_iva / 100.0)
    total_ars = base_imp + iva_calc
    total_usd = total_ars / usd_rate if usd_rate > 0 else 0.0

    st.markdown(
        f"""
        <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); padding: 0.8rem; border-radius: 6px; margin: 0.5rem 0 1rem 0; display: flex; justify-content: space-between; align-items: center;">
            <span>Base Imponible: <b>{format_currency(base_imp)}</b> | IVA ({alicuota_iva}%): <b>{format_currency(iva_calc)}</b></span>
            <span><b style="color: #10B981; font-size: 1.2rem;">TOTAL: {format_currency(total_ars)}</b> <span style="color: #00F0FF; margin-left: 10px;">(USD ~${total_usd:.2f})</span></span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    notas_cot = st.text_area("Detalle técnico / Cláusulas del presupuesto:", placeholder="Presupuesto para reemplazo de pantalla OLED y mantenimiento preventivo...", key="cot_notas")

    if st.button("📤 Guardar y Emitir Cotización", type="primary", use_container_width=True, key="cot_btn_submit"):
        if not cliente_id:
            st.error("Debes seleccionar o dar de alta un cliente.")
        else:
            payload = {
                "ot_id": ot_id,
                "cliente_id": cliente_id,
                "subtotal": subtotal_in,
                "descuento": desc_in,
                "alicuota_iva": alicuota_iva,
                "tipo_cambio_usd": usd_rate,
                "validez_dias": validez,
                "notas": notas_cot.strip(),
            }
            user_log = st.session_state.get("username", "admin")
            created_cot = create_quote(payload, user_log, org_id=org_id)
            st.success(f"¡Cotización {created_cot} generada con éxito!")
            st.rerun()


def render_listado_cotizaciones() -> None:
    """Tabla de consulta de cotizaciones con firma digital y conversión a remito."""
    org_id = st.session_state.get("organizacion_id", 1)
    conn = get_connection()
    sql = """
        SELECT 
            c.*,
            cli.nombre as cliente_nombre,
            cli.telefono as cliente_telefono,
            o.ot_codigo,
            o.marca,
            o.modelo
        FROM cotizaciones c
        LEFT JOIN clientes cli ON c.cliente_id = cli.id
        LEFT JOIN ordenes_servicio o ON c.ot_id = o.id
        WHERE c.organizacion_id = ?
        ORDER BY c.id DESC
    """
    df_cot = pd.read_sql_query(sql, conn, params=(org_id,))
    if df_cot.empty:
        empty_state("No hay cotizaciones registradas.")
        return

    st.dataframe(
        df_cot[["codigo_cotizacion", "created_at", "estado", "cliente_nombre", "ot_codigo", "subtotal", "alicuota_iva", "total"]].rename(
            columns={
                "codigo_cotizacion": "Nro Cotización",
                "created_at": "Fecha",
                "estado": "Estado",
                "cliente_nombre": "Cliente",
                "ot_codigo": "OT Vinculada",
                "subtotal": "Subtotal ($)",
                "alicuota_iva": "IVA (%)",
                "total": "Total ($)",
            }
        ),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Subtotal ($)": st.column_config.NumberColumn(format="$%d"),
            "Total ($)": st.column_config.NumberColumn(format="$%d"),
        },
    )

    st.markdown("<div style='border-top: 1px solid #1F2937; margin: 1.5rem 0;'></div>", unsafe_allow_html=True)
    st.markdown("<b style='color: #00F0FF; font-size: 1rem;'>Acciones & Firma Digital de Presupuesto</b>", unsafe_allow_html=True)

    cot_ids = df_cot["codigo_cotizacion"].tolist()
    sel_cot_num = st.selectbox("Seleccionar Cotización:", options=cot_ids, key="cot_manage_sel")
    row_cot = df_cot[df_cot["codigo_cotizacion"] == sel_cot_num].iloc[0]
    c_id = int(row_cot["id"])

    c_info, c_action = st.columns([1.4, 1.2])
    with c_info:
        st.markdown(f"**Cliente:** {row_cot['cliente_nombre']} ({row_cot['cliente_telefono']})")
        st.markdown(f"**Equipo:** {row_cot['marca'] or ''} {row_cot['modelo'] or 'Presupuesto Libre'} | **OT:** `{row_cot['ot_codigo'] or 'Sin OT'}`")
        st.markdown(f"**Total:** <span style='color: #10B981; font-size: 1.15rem; font-weight: bold;'>{format_currency(row_cot['total'])}</span>", unsafe_allow_html=True)
        st.markdown(f"**Token de Firma / Aprobación Pública:** `cotizacion?token={row_cot['hash_publico']}`")

    with c_action:
        st.markdown(f"Estado Actual: **{row_cot['estado']}**")

        if row_cot["estado"] != "ACEPTADA":
            # Firma digital interactiva / confirmación
            with st.expander("✍️ Captura de Firma Digital del Cliente", expanded=False):
                firma_aclaracion = st.text_input("Aclaración de Firma:", value=str(row_cot["cliente_nombre"]), key=f"cot_firm_acl_{c_id}")
                firma_doc = st.text_input("DNI del Firmante:", key=f"cot_firm_dni_{c_id}")
                confirma_firma = st.checkbox("El cliente manifiesta su conformidad y aprobación", key=f"cot_chk_conf_{c_id}")

                if st.button("✅ Aprobar con Firma Digital", type="primary", disabled=not confirma_firma, key=f"btn_firm_{c_id}"):
                    firma_data = f"Firma digital verificada: {firma_aclaracion} (DNI {firma_doc}) - {date.today()}"
                    user_log = st.session_state.get("username", "admin")
                    approve_quote(c_id, user_log, firma_base64=firma_data, org_id=org_id)
                    st.toast(f"¡Cotización {sel_cot_num} aprobada!", icon="✍️")
                    st.rerun()

        else:
            st.success("✅ Presupuesto ya aprobado por el cliente.")
            if st.button("📄 Convertir a Remito Oficial", type="primary", use_container_width=True, key=f"btn_conv_rem_{c_id}"):
                user_log = st.session_state.get("username", "admin")
                rem_code = convert_quote_to_remito(c_id, user_log, org_id=org_id)
                st.toast(f"✅ ¡Remito {rem_code} generado con éxito!", icon="📄")
                st.rerun()
