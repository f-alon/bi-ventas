"""Módulo 1.2: Gestión Integral de Órdenes de Servicio, Checklist Dinámico, Fotos y Taller (ERP LABFIX)."""

import base64
from datetime import date, timedelta
import json
import urllib.parse
import pandas as pd
import streamlit as st
from auth import get_all_salespeople, get_all_technicians
from components.cards import empty_state, format_currency
from components.receipt import render_repair_delivery_remito
from core.config import (
    CHECKLIST_TEMPLATES,
    ESTADOS_OT,
    MARCAS,
    MODELOS_POR_MARCA,
    TIPOS_DISPOSITIVO,
)
from database import (
    consume_part_for_order,
    create_work_order,
    get_all_clients,
    get_connection,
    get_next_code,
    get_or_create_client,
    get_workshop_config,
    load_orders_df,
    load_stock_df,
    save_order_photo,
    update_work_order_status,
)


def render_ordenes_view() -> None:
    """Renderiza el módulo central de Órdenes de Servicio: creación, fotos, checklist e insumos."""
    st.markdown(
        """
        <div style="margin-bottom: 1rem;">
            <h2 style="color: #FFFFFF; font-weight: 800; margin: 0; font-size: 1.5rem; letter-spacing: -0.02em;">
                🔧 Órdenes de Servicio Técnico
            </h2>
            <span style="color: #9CA3AF; font-size: 0.85rem;">
                Trazabilidad del ciclo de vida, checklist dinámico por tipo de dispositivo, fotos y seguimiento público
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_list, tab_new = st.tabs(["📋 Listado y Gestión de Órdenes", "➕ Ingresar Nuevo Dispositivo"])

    with tab_new:
        render_nueva_orden_form()

    with tab_list:
        render_listado_ordenes()


def render_nueva_orden_form() -> None:
    """Formulario integral de ingreso con checklist adaptativo y asignación."""
    org_id = st.session_state.get("organizacion_id", 1)
    st.markdown("<b style='color: #00F0FF; font-size: 1rem;'>Registro de Ingreso a Laboratorio</b>", unsafe_allow_html=True)

    next_ot = get_next_code("OT", "ordenes_servicio", "ot_codigo", org_id=org_id)
    all_clients = get_all_clients(org_id=org_id)
    technicians = get_all_technicians(org_id=org_id)
    salespeople = get_all_salespeople(org_id=org_id)

    # 1. Datos del Cliente
    st.markdown("<div style='background: #111827; border: 1px solid #1F2937; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;'>", unsafe_allow_html=True)
    st.markdown("<b style='color: #F9FAFB;'>1. Datos del Cliente</b>", unsafe_allow_html=True)

    col_cli_sel, col_cli_name = st.columns([1.5, 2])
    with col_cli_sel:
        opciones_cli = ["Nuevo Cliente"] + [f"{c['nombre']} (Tel: {c['telefono']})" for c in all_clients]
        cli_choice = st.selectbox("Seleccionar Cliente:", options=opciones_cli, key="ot_new_sel_cli")

    if cli_choice == "Nuevo Cliente":
        c_n1, c_n2, c_n3 = st.columns(3)
        with c_n1:
            c_nombre = st.text_input("Nombre y Apellido *:", placeholder="Ej: Marcelo Gómez", key="ot_new_cli_nombre")
        with c_n2:
            c_dni = st.text_input("DNI / CUIT:", placeholder="Ej: 35123456", key="ot_new_cli_dni")
        with c_n3:
            c_tel = st.text_input("Teléfono / WhatsApp *:", placeholder="+54 9 11 ...", key="ot_new_cli_tel")
        c_mail = st.text_input("Email:", placeholder="cliente@correo.com", key="ot_new_cli_email")
        c_dir = st.text_input("Dirección:", placeholder="Calle 123, Localidad", key="ot_new_cli_dir")
    else:
        idx = opciones_cli.index(cli_choice) - 1
        sel_c = all_clients[idx]
        c_nombre, c_dni, c_tel, c_mail, c_dir = sel_c["nombre"], sel_c["dni_cuit"], sel_c["telefono"], sel_c["email"], sel_c["direccion"]
        st.caption(f"Cliente: **{c_nombre}** | Tel: {c_tel} | DNI: {c_dni}")

    st.markdown("</div>", unsafe_allow_html=True)

    # 2. Datos del Dispositivo y Checklist Dinámico
    st.markdown("<div style='background: #111827; border: 1px solid #1F2937; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;'>", unsafe_allow_html=True)
    st.markdown("<b style='color: #F9FAFB;'>2. Datos del Dispositivo & Checklist Físico Adaptativo</b>", unsafe_allow_html=True)

    c_dev, c_m1, c_m2 = st.columns(3)
    with c_dev:
        tipo_disp = st.selectbox("Tipo de Dispositivo *:", TIPOS_DISPOSITIVO, key="ot_new_tipo_disp")
    with c_m1:
        marca_sel = st.selectbox("Marca *:", options=MARCAS, key="ot_new_marca")
        marca = st.text_input("Otra Marca:", key="ot_new_marca_other") if marca_sel == "Otro" else marca_sel
    with c_m2:
        modelos_disp = MODELOS_POR_MARCA.get(marca_sel, ["Otro"])
        modelo_sel = st.selectbox("Modelo *:", options=modelos_disp, key="ot_new_modelo")
        modelo = st.text_input("Otro Modelo:", key="ot_new_modelo_other") if modelo_sel == "Otro" else modelo_sel

    c_imei, c_patron = st.columns(2)
    with c_imei:
        imei = st.text_input("IMEI / Serie / Service Tag:", placeholder="358491... o S/N", key="ot_new_imei")
    with c_patron:
        patron = st.text_input("PIN o Patrón de Desbloqueo:", placeholder="PIN / Patrón de puntos", key="ot_new_patron")

    # Checklist Dinámico según el tipo de dispositivo
    template_items = CHECKLIST_TEMPLATES.get(tipo_disp, CHECKLIST_TEMPLATES["Smartphone"])
    st.markdown(f"<b style='font-size: 0.85rem; color: #00F0FF;'>Checklist Físico ({tipo_disp}):</b>", unsafe_allow_html=True)

    chk_dict = {}
    cols_chk = st.columns(4)
    for idx, item in enumerate(template_items):
        col_target = cols_chk[idx % 4]
        with col_target:
            val_chk = st.checkbox(item, value=(item == "Enciende"), key=f"chk_{tipo_disp}_{idx}")
            chk_dict[item] = "OK" if val_chk else "FALLA / NO"

    falla = st.text_area("Falla Declarada por el Cliente *:", placeholder="Ej: No carga, calentamiento excesivo en zona superior. Touch intermitente.", key="ot_new_falla")
    st.markdown("</div>", unsafe_allow_html=True)

    # 3. Asignación, Presupuesto Inicial & Seña
    st.markdown("<div style='background: #111827; border: 1px solid #1F2937; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;'>", unsafe_allow_html=True)
    st.markdown("<b style='color: #F9FAFB;'>3. Asignación y Condiciones Económicas</b>", unsafe_allow_html=True)

    c_tec, c_ven, c_prom = st.columns(3)
    with c_tec:
        tech_opts = ["Sin Asignar"] + [f"{t['nombre']}" for t in technicians]
        tec_choice = st.selectbox("Técnico Asignado:", options=tech_opts, key="ot_new_tec")
        tecnico_id = technicians[tech_opts.index(tec_choice) - 1]["id"] if tec_choice != "Sin Asignar" else None
    with c_ven:
        ven_opts = ["Sin Asignar"] + [f"{v['nombre']}" for v in salespeople]
        ven_choice = st.selectbox("Recepción / Vendedor:", options=ven_opts, key="ot_new_ven")
        vendedor_id = salespeople[ven_opts.index(ven_choice) - 1]["id"] if ven_choice != "Sin Asignar" else None
    with c_prom:
        fecha_promesa = st.date_input("Fecha Promesa de Entrega:", value=date.today() + timedelta(days=2), key="ot_new_promesa")

    c_mo, c_rep, c_seña, c_met = st.columns(4)
    with c_mo:
        mano_obra = st.number_input("Mano de Obra Estimada ($):", min_value=0.0, value=35000.0, step=1000.0, key="ot_new_mo")
    with c_rep:
        costo_rep = st.number_input("Costo Repuestos Inicial ($):", min_value=0.0, value=0.0, step=1000.0, key="ot_new_rep")
    with c_seña:
        seña = st.number_input("Seña / Cobro Anticipado ($):", min_value=0.0, value=10000.0, step=1000.0, key="ot_new_seña")
    with c_met:
        metodo_seña = st.selectbox("Medio de Pago Seña:", options=["Efectivo", "Transferencia / Alias", "Débito", "Crédito"], key="ot_new_met_seña")

    total_est = mano_obra + costo_rep
    saldo_est = max(0.0, total_est - seña)
    st.markdown(
        f"""
        <div style="background: rgba(0, 240, 255, 0.08); padding: 0.6rem 1rem; border-radius: 6px; display: flex; justify-content: space-between; align-items: center;">
            <span>Total Presupuestado: <b>{format_currency(total_est)}</b> | Seña: <b style="color: #10B981;">{format_currency(seña)}</b></span>
            <span style="font-size: 1.05rem;">Saldo Pendiente al Retiro: <b style="color: #F59E0B;">{format_currency(saldo_est)}</b></span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("🚀 Confirmar Ingreso y Generar Orden de Servicio", type="primary", use_container_width=True, key="ot_new_btn_submit"):
        if not c_nombre.strip() or not falla.strip() or not marca.strip() or not modelo.strip() or not c_tel.strip():
            st.error("Completá los campos obligatorios (Nombre, Teléfono, Marca, Modelo y Falla).")
        else:
            cli_id = get_or_create_client(c_nombre, c_tel, c_dni, c_mail, c_dir, org_id=org_id)
            order_payload = {
                "ot_codigo": next_ot,
                "cliente_id": cli_id,
                "tecnico_id": tecnico_id,
                "vendedor_id": vendedor_id,
                "tipo_dispositivo": tipo_disp,
                "marca": marca.strip(),
                "modelo": modelo.strip(),
                "imei_serie": imei.strip(),
                "patron_desbloqueo": patron.strip(),
                "problema": falla.strip(),
                "checklist": chk_dict,
                "presupuesto_estimado": total_est,
                "fecha_entrega_estimada": str(fecha_promesa),
                "estado": "PENDIENTE",
                "mano_obra": mano_obra,
                "costo_repuestos": costo_rep,
                "monto_senado": seña,
                "metodo_pago_seña": metodo_seña,
                "fecha_ingreso": str(date.today()),
            }
            user_log = st.session_state.get("username", "admin")
            creada_ot = create_work_order(order_payload, user_log, org_id=org_id)
            st.success(f"🎉 ¡Orden de Servicio {creada_ot} creada exitosamente!")
            st.rerun()


def render_listado_ordenes() -> None:
    """Tabla de consulta, filtros, evidencia fotográfica y WhatsApp."""
    org_id = st.session_state.get("organizacion_id", 1)
    df_orders = load_orders_df(org_id=org_id)
    if df_orders.empty:
        empty_state("No hay órdenes de servicio registradas.")
        return

    col_q, col_est, col_tec = st.columns([2, 1.2, 1.2])
    with col_q:
        q_search = st.text_input("🔎 Buscar OT por Código, Cliente, IMEI o Modelo:", placeholder="Ej: OT-1004, 35492..., iPhone 13, Gómez...", key="ot_list_q")
    with col_est:
        opciones_estado = ["Todos los Estados"] + ESTADOS_OT
        filtro_estado = st.selectbox("Estado:", options=opciones_estado, key="ot_list_f_est")
    with col_tec:
        tech_list = ["Todos los Técnicos"] + sorted(df_orders["tecnico_nombre"].dropna().unique().tolist())
        filtro_tec = st.selectbox("Técnico:", options=tech_list, key="ot_list_f_tec")

    filtered = df_orders.copy()
    if filtro_estado != "Todos los Estados":
        filtered = filtered[filtered["estado"] == filtro_estado]
    if filtro_tec != "Todos los Técnicos":
        filtered = filtered[filtered["tecnico_nombre"] == filtro_tec]

    if q_search.strip():
        q = q_search.strip().lower()
        filtered = filtered[
            filtered["ot_codigo"].str.lower().str.contains(q, na=False)
            | filtered["cliente_nombre"].str.lower().str.contains(q, na=False)
            | filtered["imei_serie"].str.lower().str.contains(q, na=False)
            | filtered["modelo"].str.lower().str.contains(q, na=False)
        ]

    st.markdown(f"<span style='color: #00F0FF; font-weight: 700;'>Mostrando {len(filtered)} de {len(df_orders)} órdenes</span>", unsafe_allow_html=True)

    display_cols = ["ot_codigo", "tipo_dispositivo", "marca", "modelo", "cliente_nombre", "estado", "fecha_ingreso", "total", "saldo_pendiente"]
    st.dataframe(
        filtered[display_cols].rename(
            columns={
                "ot_codigo": "Código OT",
                "tipo_dispositivo": "Tipo",
                "marca": "Marca",
                "modelo": "Modelo",
                "cliente_nombre": "Cliente",
                "estado": "Estado",
                "fecha_ingreso": "Ingreso",
                "total": "Total ($)",
                "saldo_pendiente": "Saldo ($)",
            }
        ),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Total ($)": st.column_config.NumberColumn(format="$%d"),
            "Saldo ($)": st.column_config.NumberColumn(format="$%d"),
        },
    )

    st.markdown("<div style='border-top: 1px solid #1F2937; margin: 1.5rem 0;'></div>", unsafe_allow_html=True)
    st.markdown("<b style='color: #00F0FF; font-size: 1.05rem;'>⚡ Gestión del Ciclo de Vida, Fotos y Seguimiento Público</b>", unsafe_allow_html=True)

    lista_ots = filtered["ot_codigo"].tolist() if not filtered.empty else df_orders["ot_codigo"].tolist()
    ot_sel = st.selectbox("Seleccionar OT para gestionar:", options=lista_ots, key="ot_manage_sel")
    order_sel = df_orders[df_orders["ot_codigo"] == ot_sel].iloc[0]
    config = get_workshop_config(org_id=org_id)
    conn = get_connection()

    with st.expander(f"⚙️ Detalle Operativo de {ot_sel} - {order_sel['marca']} {order_sel['modelo']}", expanded=True):
        c_e1, c_e2 = st.columns([1.2, 1.5])
        with c_e1:
            st.markdown(f"**Cliente:** {order_sel['cliente_nombre']} ({order_sel['cliente_telefono']})")
            st.markdown(f"**IMEI/Serie:** `{order_sel['imei_serie'] or 'S/D'}` | **PIN/Patrón:** `{order_sel['patron_desbloqueo'] or 'Sin clave'}`")
            st.markdown(f"**Falla:** {order_sel['problema']}")

            # Token de seguimiento público y WhatsApp
            token_pub = order_sel.get("hash_seguimiento_publico", "")
            st.markdown(f"**Token Público de Tracking:** `kiosco?token={token_pub}`")

            # Botón WhatsApp
            tel_limpio = str(order_sel["cliente_telefono"]).replace("+", "").replace(" ", "").replace("-", "")
            msg_whatsapp = (
                f"Hola {order_sel['cliente_nombre']}, te saludamos de {config.get('nombre_taller', 'LABFIX')}. "
                f"Te informamos que tu equipo {order_sel['marca']} {order_sel['modelo']} (Orden #{order_sel['ot_codigo']}) "
                f"se encuentra en estado: *{order_sel['estado']}*. "
                f"Saldo a cancelar: {format_currency(order_sel['saldo_pendiente'])}."
            )
            wa_url = f"https://wa.me/{tel_limpio}?text={urllib.parse.quote(msg_whatsapp)}"

            st.markdown(
                f"""
                <a href="{wa_url}" target="_blank" style="display: inline-block; background: #10B981; color: #FFFFFF; text-decoration: none; padding: 6px 14px; border-radius: 6px; font-weight: bold; font-size: 0.85rem; margin-top: 6px;">
                    💬 Notificar por WhatsApp
                </a>
                """,
                unsafe_allow_html=True,
            )

            st.markdown("---")
            actual_idx = ESTADOS_OT.index(order_sel["estado"]) if order_sel["estado"] in ESTADOS_OT else 0
            nuevo_st = st.selectbox("Modificar Estado del Ciclo de Vida:", options=ESTADOS_OT, index=actual_idx, key=f"ot_st_update_{ot_sel}")
            diag_txt = st.text_area("Diagnóstico Técnico / Mediciones:", value=str(order_sel.get("diagnostico_tecnico", "") or ""), key=f"ot_diag_{ot_sel}")
            notas_m = st.text_input("Notas de Microelectrónica:", value=str(order_sel.get("notas_microelectronica", "") or ""), key=f"ot_micro_{ot_sel}")

            if st.button("💾 Guardar Nuevo Estado", type="primary", key=f"btn_save_st_{ot_sel}"):
                user_act = st.session_state.get("username", "admin")
                update_work_order_status(ot_sel, nuevo_st, user_act, diag_txt.strip(), notas_m.strip(), org_id=org_id)
                st.toast(f"¡Estado actualizado a '{nuevo_st}'!", icon="✅")
                st.rerun()

        with c_e2:
            st.markdown("<b style='color: #10B981;'>Imputar Repuesto de Stock a esta Orden</b>", unsafe_allow_html=True)
            df_stock = load_stock_df(org_id=org_id)
            if df_stock.empty:
                st.warning("No hay productos en inventario para imputar.")
            else:
                rep_list = [f"{p['nombre']} (Stock: {p['stock_actual']} | Precio: ${p['precio_venta']:,.0f})" for _, p in df_stock.iterrows()]
                sel_p = st.selectbox("Seleccionar Repuesto a Consumir:", options=rep_list, key=f"ot_part_sel_{ot_sel}")
                p_idx = rep_list.index(sel_p)
                prod_data = df_stock.iloc[p_idx]

                col_cant, col_precio, col_btn_part = st.columns([1, 1.2, 1.2])
                with col_cant:
                    cant_usar = st.number_input("Cant:", min_value=1, max_value=max(1, int(prod_data["stock_actual"])), value=1, key=f"ot_part_cant_{ot_sel}")
                with col_precio:
                    precio_cobr = st.number_input("Precio Cobrado ($):", min_value=0.0, value=float(prod_data["precio_venta"]), step=1000.0, key=f"ot_part_pr_{ot_sel}")
                with col_btn_part:
                    st.markdown("<div style='margin-top: 1.7rem;'></div>", unsafe_allow_html=True)
                    if st.button("➕ Consumir Repuesto", key=f"btn_part_add_{ot_sel}", use_container_width=True):
                        user_act = st.session_state.get("username", "admin")
                        consume_part_for_order(
                            ot_id=int(order_sel["id"]),
                            ot_codigo=ot_sel,
                            producto_id=int(prod_data["id"]),
                            cantidad=int(cant_usar),
                            precio_cobrado=float(precio_cobr),
                            user=user_act,
                            org_id=org_id,
                        )
                        st.toast(f"¡{cant_usar}x {prod_data['nombre']} imputado a la orden!", icon="📦")
                        st.rerun()

            st.markdown("---")
            st.markdown(
                f"""
                <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); padding: 0.8rem; border-radius: 6px;">
                    <div>Mano de Obra: <b>{format_currency(order_sel['mano_obra'])}</b></div>
                    <div>Repuestos Consumidos: <b>{format_currency(order_sel['costo_repuestos'])}</b></div>
                    <div style="font-size: 1.1rem; font-weight: bold; margin-top: 4px; color: #10B981;">TOTAL: {format_currency(order_sel['total'])}</div>
                    <div style="color: #F59E0B; font-weight: bold;">Saldo Pendiente: {format_currency(order_sel['saldo_pendiente'])}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Evidencia Fotográfica (Ingreso, Reparación, Entrega)
            st.markdown("<b style='color: #00F0FF; margin-top: 10px; display: block;'>📸 Evidencia Fotográfica del Dispositivo</b>", unsafe_allow_html=True)
            with st.form(key=f"form_foto_ot_{ot_sel}"):
                c_f1, c_f2 = st.columns([1, 2])
                with c_f1:
                    etapa_foto = st.selectbox("Momento:", ["INGRESO", "REPARACION", "ENTREGA"], key=f"foto_etapa_{ot_sel}")
                with c_f2:
                    subir_img = st.file_uploader("Adjuntar Foto (JPG/PNG):", type=["jpg", "jpeg", "png"], key=f"foto_file_{ot_sel}")

                notas_foto = st.text_input("Nota / Descripción de la foto:", placeholder="Detalle de rayón en pantalla...", key=f"foto_notas_{ot_sel}")
                btn_foto = st.form_submit_button("Subir Evidencia Fotográfica")

                if btn_foto and subir_img:
                    b64_img = base64.b64encode(subir_img.read()).decode("utf-8")
                    data_uri = f"data:{subir_img.type};base64,{b64_img}"
                    save_order_photo(int(order_sel["id"]), etapa_foto, data_uri, notas_foto, org_id=org_id)
                    st.toast("✅ Foto guardada", icon="📸")
                    st.rerun()

            # Galería de fotos existentes
            fotos_db = conn.execute(
                "SELECT momento, url_archivo, notas, created_at FROM ordenes_fotos WHERE orden_id = ? ORDER BY id DESC",
                (int(order_sel["id"]),),
            ).fetchall()
            if fotos_db:
                st.markdown("<b style='font-size: 0.8rem; color: #9CA3AF;'>Fotos guardadas:</b>", unsafe_allow_html=True)
                cols_gal = st.columns(min(3, len(fotos_db)))
                for f_idx, f_row in enumerate(fotos_db):
                    with cols_gal[f_idx % len(cols_gal)]:
                        st.image(f_row["url_archivo"], caption=f"{f_row['momento']}: {f_row['notas']}", use_column_width=True)

            # Botón de visualización del Remito de Garantía
            if st.button("📑 Ver Remito de Entrega & Garantía", key=f"btn_remito_view_{ot_sel}", use_container_width=True):
                st.markdown(render_repair_delivery_remito(dict(order_sel), config), unsafe_allow_html=True)
