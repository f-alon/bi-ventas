"""Módulo 8: Terminal Kiosco de Autoservicio y Gestión de Leads CRM (ERP LABFIX)."""

import pandas as pd
import streamlit as st
from components.cards import empty_state, format_currency, format_number, get_status_badge_html, metric_card
from core.config import ESTADOS_LEADS
from database import create_lead, get_connection, load_orders_df, update_lead_status


def render_kiosco_leads_view() -> None:
    """Renderiza el Kiosco de consulta para clientes y el CRM de leads."""
    user = st.session_state.get("username", "admin")
    org_id = st.session_state.get("organizacion_id", 1)

    st.markdown(
        """
        <div style="margin-bottom: 1.25rem;">
            <h2 style="color: #FFFFFF; font-weight: 800; margin: 0; font-size: 1.6rem; letter-spacing: -0.02em;">
                📱 Leads Comerciales & Kiosco de Autoservicio
            </h2>
            <span style="color: #9CA3AF; font-size: 0.85rem;">
                Pipeline de oportunidades de venta (Chatbot Santi/Web) y terminal de consulta de mostrador
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    conn = get_connection()

    t_crm, t_kiosco, t_new_lead = st.tabs(["📊 Embudo de Leads / CRM", "🖥️ Terminal Kiosco de Autoservicio", "➕ Nuevo Lead"])

    # 1. PESTAÑA ALTA MANUAL DE LEAD
    with t_new_lead:
        st.markdown("<b style='color: #00F0FF; font-size: 1rem;'>Registrar Nueva Oportunidad Comercial</b>", unsafe_allow_html=True)
        with st.form(key="form_alta_lead"):
            c1, c2 = st.columns(2)
            with c1:
                nom_l = st.text_input("Nombre del Interesado *", placeholder="María Elena Rossi", key="lead_nom_in")
                tel_l = st.text_input("Teléfono / WhatsApp *", placeholder="+54 9 11 4444-2222", key="lead_tel_in")
            with c2:
                em_l = st.text_input("Email:", placeholder="maria@gmail.com", key="lead_em_in")
                orig_l = st.selectbox("Canal de Ingreso / Origen:", ["CHATBOT_SANTI", "MANUAL", "WEB"], key="lead_orig_in")

            msg_l = st.text_area("Consulta / Dispositivo que desea reparar:", placeholder="Consulta por cambio de módulo de iPhone 13 Pro y cotización...", height=90, key="lead_msg_in")

            submit_l = st.form_submit_button("🚀 Guardar Lead en CRM", use_container_width=True)
            if submit_l:
                if not nom_l.strip() or not tel_l.strip():
                    st.error("El nombre y teléfono son obligatorios.")
                else:
                    lid = create_lead(nom_l, tel_l, em_l, msg_l, orig_l, org_id=org_id)
                    st.toast(f"✅ Lead #{lid} registrado", icon="📱")
                    st.rerun()

    # 2. PESTAÑA EMBUDO DE LEADS
    with t_crm:
        sql_leads = "SELECT * FROM leads WHERE organizacion_id = ? ORDER BY id DESC"
        rows_l = conn.execute(sql_leads, (org_id,)).fetchall()

        if not rows_l:
            empty_state("No hay leads registrados en el CRM.", "Los contactos captados por el Chatbot Santi o de forma manual aparecerán aquí.")
        else:
            df_leads = pd.DataFrame([dict(r) for r in rows_l])

            tot_leads = len(df_leads)
            nuevos = len(df_leads[df_leads["estado"] == "NUEVO"])
            contactados = len(df_leads[df_leads["estado"] == "CONTACTADO"])
            convertidos = len(df_leads[df_leads["estado"] == "CONVERTIDO"])

            kl1, kl2, kl3, kl4 = st.columns(4)
            with kl1:
                metric_card("Total Oportunidades", f"{tot_leads} leads", glow_color="cyan")
            with kl2:
                metric_card("Nuevos sin Contactar", f"{nuevos} pendientes", glow_color="yellow" if nuevos > 0 else "neutral")
            with kl3:
                metric_card("En Negociación", f"{contactados} en curso", glow_color="purple")
            with kl4:
                metric_card("Convertidos en OT", f"{convertidos} clientes", glow_color="green")

            st.markdown("<hr style='border-color: #1F2937; margin: 1.5rem 0;'>", unsafe_allow_html=True)

            for _, ld in df_leads.iterrows():
                l_id = int(ld["id"])
                st_lead = ld["estado"]

                with st.expander(f"👤 {ld['nombre']} ({ld['telefono']}) | Canal: {ld['origen']} | Estado: {st_lead}", expanded=(st_lead == "NUEVO")):
                    c_info, c_action = st.columns([3, 2])
                    with c_info:
                        st.markdown(
                            f"""
                            <div style="background: #111827; padding: 12px; border-radius: 6px; border-left: 3px solid #00F0FF;">
                                <b>Teléfono:</b> <a href="https://wa.me/{ld['telefono'].replace('+', '').replace(' ', '')}" target="_blank" style="color: #10B981;">💬 Abrir WhatsApp</a><br>
                                <b>Email:</b> {ld['email'] or 'S/D'}<br>
                                <b>Fecha de Ingreso:</b> {ld['created_at']}<br>
                                <div style="margin-top: 6px; color: #E5E7EB; font-size: 0.85rem;">
                                    <b>Mensaje del Cliente:</b><br>{ld['mensaje']}
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                    with c_action:
                        st.markdown("<b style='color: #00F0FF; font-size: 0.85rem;'>Etapa en el Pipeline</b>", unsafe_allow_html=True)
                        new_st = st.selectbox(
                            "Avanzar Estado:",
                            ESTADOS_LEADS,
                            index=ESTADOS_LEADS.index(st_lead) if st_lead in ESTADOS_LEADS else 0,
                            key=f"lead_st_sel_{l_id}",
                        )
                        if st.button("Actualizar Estado", key=f"btn_lead_up_{l_id}", use_container_width=True):
                            update_lead_status(l_id, new_st, org_id=org_id)
                            st.toast("✅ Lead actualizado", icon="📱")
                            st.rerun()

    # 3. PESTAÑA KIOSCO DE AUTOSERVICIO (TERMINAL DE MOSTRADOR)
    with t_kiosco:
        st.markdown(
            """
            <div style="background: linear-gradient(135deg, rgba(0, 240, 255, 0.1), rgba(16, 185, 129, 0.1)); border: 1px solid #00F0FF; padding: 25px; border-radius: 12px; text-align: center; margin-bottom: 20px;">
                <h1 style="color: #FFFFFF; font-size: 2rem; margin: 0; font-weight: 900; letter-spacing: -0.03em;">
                    ⚡ TERMINAL DE CONSULTA DE EQUIPO
                </h1>
                <p style="color: #9CA3AF; font-size: 0.95rem; margin-top: 8px;">
                    Introduce el número de tu Orden de Trabajo (ej. <b>OT-1001</b>) o tu código de seguimiento público:
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        c_srch1, c_srch2 = st.columns([3, 1])
        with c_srch1:
            q_kiosco = st.text_input("Código de OT o Token:", placeholder="Ej: OT-1001", label_visibility="collapsed", key="kiosco_q_input")
        with c_srch2:
            btn_kiosco = st.button("🔍 Consultar Estado", type="primary", use_container_width=True, key="kiosco_btn_search")

        if q_kiosco.strip():
            df_all = load_orders_df(org_id=org_id)
            clean_q = q_kiosco.strip().upper()

            match = df_all[
                (df_all["ot_codigo"].str.upper() == clean_q)
                | (df_all["hash_seguimiento_publico"] == q_kiosco.strip())
            ]

            if match.empty:
                st.error("❌ No encontramos ninguna orden que coincida con ese código. Por favor verifica tu remito o consulta en mostrador.")
            else:
                row_k = match.iloc[0]
                est_k = row_k["estado"]

                # Renderizado estilo Pantalla Grande Kiosco
                st.markdown(
                    f"""
                    <div style="background: #111827; border: 2px solid #10B981; border-radius: 12px; padding: 25px; margin-top: 15px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1F2937; padding-bottom: 15px;">
                            <div>
                                <span style="font-size: 0.85rem; color: #9CA3AF; text-transform: uppercase;">Orden de Servicio</span>
                                <h2 style="color: #00F0FF; margin: 0; font-size: 1.8rem;">{row_k['ot_codigo']}</h2>
                            </div>
                            <div>
                                {get_status_badge_html(est_k)}
                            </div>
                        </div>

                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px; font-size: 0.95rem;">
                            <div>
                                <b style="color: #9CA3AF;">Dispositivo:</b><br>
                                <span style="font-size: 1.2rem; color: #FFFFFF; font-weight: bold;">{row_k['marca']} {row_k['modelo']}</span><br><br>
                                <b style="color: #9CA3AF;">Falla / Trabajo Solicitado:</b><br>
                                <span style="color: #E5E7EB;">{row_k['problema']}</span>
                            </div>
                            <div style="background: #1F2937; padding: 15px; border-radius: 8px;">
                                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                                    <span style="color: #9CA3AF;">Presupuesto Total:</span>
                                    <b style="color: #FFFFFF;">{format_currency(row_k['total'])}</b>
                                </div>
                                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                                    <span style="color: #9CA3AF;">Seña Previa Abonada:</span>
                                    <b style="color: #10B981;">- {format_currency(row_k['monto_senado'])}</b>
                                </div>
                                <hr style="border-color: #374151; margin: 10px 0;">
                                <div style="display: flex; justify-content: space-between; font-size: 1.15rem;">
                                    <b style="color: #F43F5E;">Saldo a Pagar al Retirar:</b>
                                    <b style="color: #F43F5E;">{format_currency(row_k['saldo_pendiente'])}</b>
                                </div>
                            </div>
                        </div>

                        <div style="margin-top: 25px; text-align: center; border-top: 1px solid #1F2937; padding-top: 15px;">
                            <span style="color: #9CA3AF; font-size: 0.85rem;">Fecha de Ingreso: {row_k['fecha_ingreso']} | Fecha Estimada de Entrega: {row_k['fecha_entrega_estimada'] or 'A coordinar'}</span><br><br>
                            <a href="https://wa.me/5491155550199?text=Hola,%20consulto%20por%20mi%20equipo%20orden%20{row_k['ot_codigo']}" target="_blank" style="background: #10B981; color: #FFFFFF; text-decoration: none; padding: 10px 20px; border-radius: 8px; font-weight: bold; font-size: 0.95rem;">
                                💬 Consultar por WhatsApp al Taller
                            </a>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

