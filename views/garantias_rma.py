"""Módulo 6: Gestión de Garantías (RMA) y Órdenes Derivadas sin Costo ($0) (ERP LABFIX)."""

import pandas as pd
import streamlit as st
from components.cards import empty_state, format_currency, format_number, metric_card
from core.config import ESTADOS_GARANTIA
from database import create_warranty_claim, get_connection, load_orders_df, resolve_warranty_claim


def render_garantias_view() -> None:
    """Renderiza el módulo integral de garantías, resolución de reclamos y generación de OTs $0."""
    user = st.session_state.get("username", "admin")
    org_id = st.session_state.get("organizacion_id", 1)

    st.markdown(
        """
        <div style="margin-bottom: 1.25rem;">
            <h2 style="color: #FFFFFF; font-weight: 800; margin: 0; font-size: 1.6rem; letter-spacing: -0.02em;">
                🛡️ Gestión de Garantías & Reclamos (RMA)
            </h2>
            <span style="color: #9CA3AF; font-size: 0.85rem;">
                Control de reclamos posventa, trazabilidad de piezas y derivación a órdenes de garantía a costo $0
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    conn = get_connection()

    t_list, t_new = st.tabs(["📋 Reclamos Registrados", "➕ Ingresar Nuevo Reclamo"])

    with t_new:
        st.markdown("<b style='color: #00F0FF; font-size: 1rem;'>Registro de Reclamo Posventa</b>", unsafe_allow_html=True)
        df_orders = load_orders_df(org_id=org_id)
        ots_cerradas = df_orders[df_orders["estado"].isin(["COMPLETADA", "ENTREGADA", "Listo para Retiro", "Entregado"])]

        ot_dict = {"Sin Orden de Servicio Asociada": None}
        for _, r in ots_cerradas.iterrows():
            ot_dict[f"{r['ot_codigo']} - {r['marca']} {r['modelo']} ({r['cliente_nombre']})"] = int(r["id"])

        with st.form(key="form_nuevo_reclamo_rma"):
            sel_ot_str = st.selectbox("Vincular Orden de Servicio Previa:", list(ot_dict.keys()), key="rma_ot_sel")
            sel_ot_id = ot_dict[sel_ot_str]

            motivo_reclamo = st.text_area(
                "Motivo Detallado del Reclamo / Falla *",
                placeholder="Ej: El cliente indica que a los 15 días la pantalla dejó de responder en la esquina inferior izquierda...",
                height=100,
                key="rma_motivo_in",
            )

            submit_claim = st.form_submit_button("🛡️ Registrar Reclamo RMA", use_container_width=True)
            if submit_claim:
                if not motivo_reclamo.strip():
                    st.error("El motivo del reclamo es obligatorio.")
                else:
                    cid = create_warranty_claim(
                        motivo=motivo_reclamo,
                        orden_id=sel_ot_id,
                        user=user,
                        org_id=org_id,
                    )
                    st.toast(f"✅ Reclamo de garantía #{cid} registrado con éxito", icon="🛡️")
                    st.rerun()

    with t_list:
        sql_claims = """
            SELECT g.*, o.ot_codigo, o.marca, o.modelo, o.fecha_egreso,
                   c.nombre as cliente_nombre, c.telefono as cliente_telefono,
                   o_der.ot_codigo as ot_derivada_codigo
            FROM garantias_reclamos g
            LEFT JOIN ordenes_servicio o ON g.orden_id = o.id
            LEFT JOIN clientes c ON o.cliente_id = c.id
            LEFT JOIN ordenes_servicio o_der ON g.orden_derivada_id = o_der.id
            WHERE g.organizacion_id = ?
            ORDER BY g.id DESC
        """
        rows = conn.execute(sql_claims, (org_id,)).fetchall()

        if not rows:
            empty_state("No hay reclamos de garantía.", "Los reclamos posventa registrados aparecerán en esta bandeja de gestión.")
            return

        df_claims = pd.DataFrame([dict(r) for r in rows])

        # KPIs
        pendientes = len(df_claims[df_claims["estado"].isin(["PENDIENTE", "EN REVISIÓN"])])
        aceptados = len(df_claims[df_claims["estado"] == "ACEPTADO"])
        rechazados = len(df_claims[df_claims["estado"] == "RECHAZADO"])
        resueltos = len(df_claims[df_claims["estado"] == "RESUELTO"])

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            metric_card("Reclamos en Revisión", f"{pendientes} casos", glow_color="yellow" if pendientes > 0 else "neutral")
        with k2:
            metric_card("Garantías Aceptadas", f"{aceptados} casos", glow_color="green")
        with k3:
            metric_card("Reclamos Rechazados", f"{rechazados} casos", glow_color="red" if rechazados > 0 else "neutral")
        with k4:
            metric_card("Casos Resueltos", f"{resueltos} cerrados", glow_color="cyan")

        st.markdown("<hr style='border-color: #1F2937; margin: 1.5rem 0;'>", unsafe_allow_html=True)

        for _, cl in df_claims.iterrows():
            c_id = int(cl["id"])
            est = cl["estado"]

            color_tag = "#F59E0B" if est in ["PENDIENTE", "EN REVISIÓN"] else ("#10B981" if est in ["ACEPTADO", "RESUELTO"] else "#F43F5E")

            with st.expander(f"🛡️ Reclamo #{c_id} | {cl['ot_codigo'] or 'Sin OT'} - {cl['marca'] or ''} {cl['modelo'] or ''} | Estado: {est}", expanded=(est in ["PENDIENTE", "EN REVISIÓN"])):
                c_det, c_action = st.columns([3, 2])

                with c_det:
                    st.markdown(
                        f"""
                        <div style="background: #111827; padding: 12px; border-radius: 8px; border-left: 3px solid {color_tag};">
                            <div style="font-size: 0.95rem; font-weight: bold; color: #FFFFFF;">
                                Cliente: {cl['cliente_nombre'] or 'Consumidor Final'} ({cl['cliente_telefono'] or 'S/D'})
                            </div>
                            <div style="color: #9CA3AF; font-size: 0.8rem; margin-top: 4px;">
                                <b>Equipo Original:</b> {cl['marca'] or ''} {cl['modelo'] or ''} | <b>OT Ref:</b> {cl['ot_codigo'] or 'N/A'}<br>
                                <b>Fecha Reclamo:</b> {cl['created_at']}
                            </div>
                            <div style="margin-top: 8px; font-size: 0.85rem; color: #E5E7EB;">
                                <b>Motivo Declarado:</b><br>
                                <span style="color: #F87171;">{cl['motivo']}</span>
                            </div>
                            {f'<div style="margin-top: 6px; font-size: 0.82rem; color: #10B981;"><b>OT de Garantía Derivada ($0):</b> <code>{cl["ot_derivada_codigo"]}</code></div>' if cl['ot_derivada_codigo'] else ''}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                with c_action:
                    st.markdown("<b style='color: #00F0FF; font-size: 0.85rem;'>Resolución de Garantía</b>", unsafe_allow_html=True)
                    with st.form(key=f"form_rma_res_{c_id}"):
                        nuevo_est = st.selectbox(
                            "Actualizar Dictamen:",
                            ESTADOS_GARANTIA,
                            index=ESTADOS_GARANTIA.index(est) if est in ESTADOS_GARANTIA else 0,
                            key=f"rma_st_sel_{c_id}",
                        )
                        notas_dictamen = st.text_area("Notas Técnicas / Conclusiones:", value=str(cl["resolucion_notas"] or ""), height=70, key=f"rma_notas_{c_id}")

                        crear_cero = False
                        if not cl["orden_derivada_id"] and cl["orden_id"]:
                            crear_cero = st.checkbox("¿Crear automáticamente una nueva OT por Garantía ($0 costo cliente)?", value=True, key=f"rma_chk_cero_{c_id}")

                        submit_res = st.form_submit_button("💾 Guardar Resolución", use_container_width=True)
                        if submit_res:
                            nueva_ot = resolve_warranty_claim(
                                claim_id=c_id,
                                nuevo_estado=nuevo_est,
                                resolucion_notas=notas_dictamen,
                                crear_orden_cero=crear_cero,
                                user=user,
                                org_id=org_id,
                            )
                            if nueva_ot:
                                st.toast(f"✅ Se creó la orden por garantía {nueva_ot}", icon="🔧")
                            else:
                                st.toast("✅ Reclamo actualizado", icon="💾")
                            st.rerun()

