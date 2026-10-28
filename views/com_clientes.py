"""Módulo 2.3: Directorio de Clientes y Ficha 360° Integral (ERP LABFIX)."""

from typing import Any, Dict
import pandas as pd
import streamlit as st
from components.cards import empty_state, format_currency, format_number, get_status_badge_html, metric_card
from database import get_all_clients, get_connection, get_or_create_client


def render_clientes_view() -> None:
    """Renderiza el directorio de clientes, ficha 360° e historial cruzado de OTs y compras."""
    st.markdown(
        """
        <div style="margin-bottom: 1.25rem;">
            <h2 style="color: #FFFFFF; font-weight: 800; margin: 0; font-size: 1.6rem; letter-spacing: -0.02em;">
                👥 Directorio & Ficha 360° de Clientes
            </h2>
            <span style="color: #9CA3AF; font-size: 0.85rem;">
                Control integral de clientes, historial de reparaciones, compras en mostrador y saldos
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    conn = get_connection()
    clients = get_all_clients()

    t_list, t_new = st.tabs(["📋 Directorio & Ficha de Cliente", "➕ Nuevo Cliente"])

    with t_new:
        st.markdown("<b style='color: #00F0FF; font-size: 1rem;'>Alta Rápida de Cliente</b>", unsafe_allow_html=True)
        with st.form(key="form_nuevo_cliente"):
            c_n1, c_n2 = st.columns(2)
            with c_n1:
                nom = st.text_input("Nombre y Apellido / Razón Social *", key="cli_nom_input")
                dni = st.text_input("DNI / CUIT / Pasaporte", key="cli_dni_input")
            with c_n2:
                tel = st.text_input("Teléfono / WhatsApp *", key="cli_tel_input")
                email = st.text_input("Correo Electrónico", key="cli_email_input")
            dir_c = st.text_input("Dirección / Localidad", key="cli_dir_input")

            submit_cli = st.form_submit_button("💾 Guardar Cliente", use_container_width=True)
            if submit_cli:
                if not nom.strip():
                    st.error("El nombre del cliente es obligatorio.")
                else:
                    cid = get_or_create_client(nom, dni, tel, email, dir_c)
                    st.toast(f"✅ Cliente registrado con ID #{cid}", icon="👤")
                    st.rerun()

    with t_list:
        if not clients:
            empty_state("No hay clientes registrados.", "Utiliza la pestaña 'Nuevo Cliente' para dar de alta el primero.")
            return

        df_c = pd.DataFrame(clients)

        q_cli = st.text_input("🔍 Buscar cliente por Nombre, DNI o Teléfono:", placeholder="Juan, 34888..., 11-...", key="cli_search_box")
        if q_cli.strip():
            term = q_cli.strip().lower()
            df_c = df_c[
                df_c["nombre"].str.lower().str.contains(term, na=False)
                | df_c["dni_cuit"].str.lower().str.contains(term, na=False)
                | df_c["telefono"].str.lower().str.contains(term, na=False)
            ]

        c_col_table, c_col_ficha = st.columns([1, 1])

        with c_col_table:
            st.markdown(f"<span style='color: #9CA3AF; font-size: 0.85rem;'><b>{len(df_c)}</b> clientes encontrados:</span>", unsafe_allow_html=True)
            st.dataframe(
                df_c[["id", "nombre", "dni_cuit", "telefono", "email"]],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "id": st.column_config.NumberColumn("ID", width="small"),
                    "nombre": st.column_config.TextColumn("Nombre", width="medium"),
                    "dni_cuit": st.column_config.TextColumn("DNI/CUIT", width="small"),
                    "telefono": st.column_config.TextColumn("Teléfono", width="small"),
                    "email": st.column_config.TextColumn("Email", width="medium"),
                },
            )

        with c_col_ficha:
            cli_ids = df_c["id"].tolist()
            if cli_ids:
                sel_id = st.selectbox("Seleccionar Cliente para Ficha 360°:", cli_ids, format_func=lambda x: f"#{x} - {df_c[df_c['id'] == x].iloc[0]['nombre']}", key="cli_inspect_sel")
                c_data = df_c[df_c["id"] == sel_id].iloc[0]

                # Consultar OTs de este cliente
                ots_cli = conn.execute(
                    """
                    SELECT ot_codigo, marca, modelo, falla_declarada, estado, total, saldo_pendiente, fecha_ingreso
                    FROM dispositivos_ordenes
                    WHERE cliente_id = ?
                    ORDER BY id DESC
                    """,
                    (sel_id,),
                ).fetchall()

                # Consultar compras POS de este cliente
                compras_cli = conn.execute(
                    """
                    SELECT numero_ticket, total, metodo_pago, creado_en
                    FROM ventas
                    WHERE cliente_id = ?
                    ORDER BY id DESC
                    """,
                    (sel_id,),
                ).fetchall()

                # Balances
                total_gastado_taller = sum(float(r["total"]) for r in ots_cli)
                saldo_pendiente_taller = sum(float(r["saldo_pendiente"]) for r in ots_cli)
                total_compras_pos = sum(float(r["total"]) for r in compras_cli)
                total_historico = total_gastado_taller + total_compras_pos

                st.markdown(
                    f"""
                    <div style="background: #111827; border: 1px solid #1F2937; border-radius: 8px; padding: 15px; margin-bottom: 12px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <h3 style="color: #00F0FF; margin: 0; font-size: 1.2rem;">{c_data['nombre']}</h3>
                            <span style="background: #1F2937; color: #9CA3AF; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem;">ID #{sel_id}</span>
                        </div>
                        <div style="color: #D1D5DB; font-size: 0.82rem; margin-top: 6px;">
                            <b>DNI/CUIT:</b> {c_data['dni_cuit'] or 'S/D'} | <b>Tel:</b> {c_data['telefono'] or 'S/D'}<br>
                            <b>Email:</b> {c_data['email'] or 'S/D'} | <b>Dirección:</b> {c_data['direccion'] or 'S/D'}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                kf1, kf2, kf3 = st.columns(3)
                with kf1:
                    metric_card("Total Facturado", format_currency(total_historico), glow_color="green")
                with kf2:
                    metric_card("Saldo Deudor", format_currency(saldo_pendiente_taller), glow_color="red" if saldo_pendiente_taller > 0 else "neutral")
                with kf3:
                    metric_card("Equipos en Taller", f"{len(ots_cli)} OTs", glow_color="cyan")

                # Sub-pestañas de la Ficha
                tab_ots, tab_pos = st.tabs([f"🔧 Reparaciones ({len(ots_cli)})", f"🛍️ Compras ({len(compras_cli)})"])
                with tab_ots:
                    if not ots_cli:
                        st.caption("No registra órdenes de servicio.")
                    else:
                        for ot in ots_cli:
                            st.markdown(
                                f"""
                                <div style="background: #1F2937; border-radius: 6px; padding: 8px 12px; margin-bottom: 6px; font-size: 0.8rem; display: flex; justify-content: space-between; align-items: center;">
                                    <div>
                                        <b style="color: #FFFFFF;">{ot['ot_codigo']}</b> - {ot['marca']} {ot['modelo']}<br>
                                        <span style="color: #9CA3AF;">Falla: {ot['falla_declarada']} | {ot['fecha_ingreso']}</span>
                                    </div>
                                    <div style="text-align: right;">
                                        {get_status_badge_html(ot['estado'])}<br>
                                        <b style="color: #10B981;">{format_currency(ot['total'])}</b>
                                        {f'<br><span style="color: #F43F5E;">Resta: {format_currency(ot["saldo_pendiente"])}</span>' if ot['saldo_pendiente'] > 0 else ''}
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                with tab_pos:
                    if not compras_cli:
                        st.caption("No registra compras en mostrador.")
                    else:
                        for v in compras_cli:
                            st.markdown(
                                f"""
                                <div style="background: #1F2937; border-radius: 6px; padding: 8px 12px; margin-bottom: 6px; font-size: 0.8rem; display: flex; justify-content: space-between;">
                                    <div>
                                        <b style="color: #FFFFFF;">Ticket #{v['numero_ticket']}</b> ({v['metodo_pago']})<br>
                                        <span style="color: #9CA3AF;">{v['creado_en']}</span>
                                    </div>
                                    <div style="color: #10B981; font-weight: bold; font-size: 0.9rem;">
                                        {format_currency(v['total'])}
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

