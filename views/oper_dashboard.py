"""Módulo 1.1: Dashboard Principal Ejecutivo, Operativo y Alertas Proactivas (ERP LABFIX)."""

from datetime import date, timedelta
import pandas as pd
import streamlit as st
from charts.erp_charts import build_orders_status_funnel, build_weekly_revenue_trend
from components.cards import empty_state, format_currency, format_number, format_pct, metric_card
from core.config import ESTADOS_WIP
from database import get_connection, load_orders_df, load_stock_df


def render_dashboard_view() -> None:
    """Renderiza el panel principal con KPIs según rol, alertas proactivas y gráficos."""
    user_role = st.session_state.get("user_role", "ADMIN").upper()
    current_username = st.session_state.get("username", "admin")
    current_tec_nombre = st.session_state.get("tecnico_nombre", "")
    current_user_id = st.session_state.get("user_id")
    org_id = st.session_state.get("organizacion_id", 1)

    st.markdown(
        """
        <div style="margin-bottom: 1.25rem;">
            <h2 style="color: #FFFFFF; font-weight: 800; margin: 0; font-size: 1.6rem; letter-spacing: -0.02em;">
                ⚡ Panel de Control & Alertas Proactivas
            </h2>
            <span style="color: #9CA3AF; font-size: 0.85rem;">
                Métricas operativas en tiempo real, equipos con retiro vencido y estado del laboratorio
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    df_orders = load_orders_df(org_id=org_id)
    df_stock = load_stock_df(org_id=org_id)
    conn = get_connection()

    # Cálculos globales
    total_wip = len(df_orders[df_orders["estado"].isin(ESTADOS_WIP)]) if not df_orders.empty else 0
    listos_entrega = len(df_orders[df_orders["estado"].isin(["COMPLETADA", "Listo para Retiro"])]) if not df_orders.empty else 0
    saldo_pendiente_total = df_orders["saldo_pendiente"].sum() if not df_orders.empty else 0.0

    today = date.today()
    mes_actual = today.month
    anio_actual = today.year

    # Facturación del mes
    ventas_mes = conn.execute(
        """
        SELECT COALESCE(SUM(total), 0) FROM ventas 
        WHERE organizacion_id = ? AND strftime('%m', creado_en) = ? AND strftime('%Y', creado_en) = ?
        """,
        (org_id, f"{mes_actual:02d}", str(anio_actual)),
    ).fetchone()[0]

    taller_mes = 0.0
    if not df_orders.empty and "fecha_ingreso_dt" in df_orders:
        df_mes = df_orders[
            (df_orders["fecha_ingreso_dt"].dt.month == mes_actual)
            & (df_orders["fecha_ingreso_dt"].dt.year == anio_actual)
        ]
        taller_mes = df_mes["total"].sum()

    facturacion_mes_total = ventas_mes + taller_mes
    stock_bajo_count = len(df_stock[df_stock["alerta_reposicion"]]) if not df_stock.empty and "alerta_reposicion" in df_stock else 0

    # 1. TARJETAS KPI ADAPTATIVAS SEGÚN ROL
    if user_role == "TECNICO":
        # KPIs específicos de Técnico
        df_my_orders = df_orders[df_orders["tecnico_nombre"] == current_tec_nombre] if not df_orders.empty else pd.DataFrame()
        my_wip = len(df_my_orders[df_my_orders["estado"].isin(ESTADOS_WIP)]) if not df_my_orders.empty else 0
        my_vencidos = len(df_my_orders[df_my_orders["retiro_vencido"]]) if not df_my_orders.empty and "retiro_vencido" in df_my_orders else 0
        my_resueltas = len(df_my_orders[df_my_orders["estado"].isin(["COMPLETADA", "ENTREGADA", "Listo para Retiro", "Entregado"])]) if not df_my_orders.empty else 0
        my_rechazadas = len(df_my_orders[df_my_orders["estado"].isin(["CANCELADA", "Sin Reparación / Rechazado"])]) if not df_my_orders.empty else 0
        total_my_closed = my_resueltas + my_rechazadas
        my_efectividad = (my_resueltas / total_my_closed * 100.0) if total_my_closed > 0 else 100.0

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            metric_card("Mis Equipos en Banco", f"{my_wip} OTs", glow_color="cyan", subtext="Asignados activos")
        with c2:
            metric_card("Retiro Vencido en Banco", f"{my_vencidos} OTs", glow_color="red" if my_vencidos > 0 else "neutral", subtext="Promesa expirada")
        with c3:
            metric_card("Efectividad en Reparaciones", format_pct(my_efectividad, show_sign=False), glow_color="green", subtext=f"{my_resueltas} equipos exitosos")
        with c4:
            metric_card("Repuestos en Stock", f"{len(df_stock)} ítems", glow_color="purple", subtext=f"{stock_bajo_count} bajo mínimo")

    elif user_role == "VENDEDOR":
        # KPIs específicos de Vendedor
        sql_ven_today = """
            SELECT COALESCE(SUM(total), 0) FROM ventas
            WHERE organizacion_id = ? AND vendedor_id = ? AND date(creado_en) = ?
        """
        ventas_hoy_ven = conn.execute(sql_ven_today, (org_id, current_user_id, str(today))).fetchone()[0]

        sql_ven_mes = """
            SELECT COALESCE(SUM(total), 0) FROM ventas
            WHERE organizacion_id = ? AND vendedor_id = ? AND strftime('%m', creado_en) = ? AND strftime('%Y', creado_en) = ?
        """
        ventas_mes_ven = conn.execute(sql_ven_mes, (org_id, current_user_id, f"{mes_actual:02d}", str(anio_actual))).fetchone()[0]

        # Comisión acumulada estimada
        comision_acumulada = ventas_mes_ven * 0.05

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            metric_card("Ventas de Mostrador Hoy", format_currency(ventas_hoy_ven), glow_color="green")
        with c2:
            metric_card("Ventas de Mostrador del Mes", format_currency(ventas_mes_ven), glow_color="cyan")
        with c3:
            metric_card("Comisiones Estimadas", format_currency(comision_acumulada), glow_color="purple", subtext="Sobre ventas cerradas")
        with c4:
            metric_card("Equipos Listos para Cobro", f"{listos_entrega} OTs", glow_color="yellow", subtext=f"Saldo: {format_currency(saldo_pendiente_total)}")

    else:
        # Rol ADMIN: Panorama integral
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            metric_card("Equipos en Banco (WIP)", str(total_wip), glow_color="cyan", subtext="Taller activo")
        with c2:
            metric_card("Listos para Retiro", str(listos_entrega), delta_positive=True if listos_entrega > 0 else None, glow_color="green", subtext="Esperando al cliente")
        with c3:
            metric_card("Facturación del Mes", format_currency(facturacion_mes_total), glow_color="purple", subtext=f"Taller + POS ({format_currency(ventas_mes)})")
        with c4:
            metric_card("Saldos por Cobrar", format_currency(saldo_pendiente_total), glow_color="yellow", subtext="Equipos entregados/listos")
        with c5:
            metric_card("Bajo Stock Mínimo", str(stock_bajo_count), glow_color="red" if stock_bajo_count > 0 else "neutral", subtext="Alertas de reposición")

    st.markdown("<hr style='border-color: #1F2937; margin: 1.25rem 0;'>", unsafe_allow_html=True)

    # 2. BLOQUE DE ALERTAS PROACTIVAS
    st.markdown("<b style='color: #F59E0B; font-size: 1.05rem;'>🚨 Alertas Proactivas del Sistema</b>", unsafe_allow_html=True)

    al1, al2, al3 = st.columns(3)

    # Alerta 1: Retiro vencido
    equipos_vencidos = df_orders[df_orders["retiro_vencido"]] if not df_orders.empty and "retiro_vencido" in df_orders else pd.DataFrame()
    with al1:
        if not equipos_vencidos.empty:
            st.markdown(
                f"""
                <div style="background: rgba(244, 63, 94, 0.1); border: 1px solid #F43F5E; border-radius: 8px; padding: 12px;">
                    <div style="color: #F43F5E; font-weight: bold; font-size: 0.9rem;">⚠️ {len(equipos_vencidos)} Equipos con Retiro Vencido</div>
                    <div style="color: #9CA3AF; font-size: 0.78rem; margin-top: 4px;">La fecha prometida de entrega expiró y el equipo sigue en taller:</div>
                    <ul style="font-size: 0.75rem; color: #E5E7EB; margin: 6px 0 0 12px; padding: 0;">
                        {''.join([f"<li><b>{r['ot_codigo']}</b>: {r['marca']} {r['modelo']} ({r['cliente_nombre']})</li>" for _, r in equipos_vencidos.head(3).iterrows()])}
                    </ul>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 8px; padding: 12px; font-size: 0.82rem; color: #10B981;">
                    ✅ No hay órdenes con fecha de retiro vencida.
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Alerta 2: Garantías próximas a vencer
    # Órdenes entregadas entre 45 y 60 días atrás
    hoy_dt = pd.Timestamp(today)
    if not df_orders.empty and "fecha_egreso_dt" in df_orders:
        df_entregados = df_orders[df_orders["estado"].isin(["ENTREGADA", "Entregado"])].dropna(subset=["fecha_egreso_dt"]).copy()
        df_entregados["dias_desde_entrega"] = (hoy_dt - df_entregados["fecha_egreso_dt"]).dt.days
        garantias_por_vencer = df_entregados[(df_entregados["dias_desde_entrega"] >= 45) & (df_entregados["dias_desde_entrega"] <= 60)]
    else:
        garantias_por_vencer = pd.DataFrame()

    with al2:
        if not garantias_por_vencer.empty:
            st.markdown(
                f"""
                <div style="background: rgba(245, 158, 11, 0.1); border: 1px solid #F59E0B; border-radius: 8px; padding: 12px;">
                    <div style="color: #F59E0B; font-weight: bold; font-size: 0.9rem;">⏳ {len(garantias_por_vencer)} Garantías Próximas a Vencer</div>
                    <div style="color: #9CA3AF; font-size: 0.78rem; margin-top: 4px;">Equipos entregados hace 45-60 días:</div>
                    <ul style="font-size: 0.75rem; color: #E5E7EB; margin: 6px 0 0 12px; padding: 0;">
                        {''.join([f"<li><b>{r['ot_codigo']}</b> ({r['cliente_nombre']}) - {r['dias_desde_entrega']} días</li>" for _, r in garantias_por_vencer.head(3).iterrows()])}
                    </ul>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 8px; padding: 12px; font-size: 0.82rem; color: #10B981;">
                    ✅ Sin garantías críticas en ventana de vencimiento.
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Alerta 3: Stock bajo mínimo
    with al3:
        if stock_bajo_count > 0:
            criticos = df_stock[df_stock["alerta_reposicion"]].head(3)
            st.markdown(
                f"""
                <div style="background: rgba(244, 63, 94, 0.1); border: 1px solid #F43F5E; border-radius: 8px; padding: 12px;">
                    <div style="color: #F43F5E; font-weight: bold; font-size: 0.9rem;">📦 {stock_bajo_count} Repuestos Bajo Stock Mínimo</div>
                    <div style="color: #9CA3AF; font-size: 0.78rem; margin-top: 4px;">Punto de pedido alcanzado:</div>
                    <ul style="font-size: 0.75rem; color: #E5E7EB; margin: 6px 0 0 12px; padding: 0;">
                        {''.join([f"<li><b>{r['nombre'][:25]}</b> ({r['stock_actual']} de {r['stock_minimo']} min)</li>" for _, r in criticos.iterrows()])}
                    </ul>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 8px; padding: 12px; font-size: 0.82rem; color: #10B981;">
                    ✅ Todo el stock se encuentra con disponibilidad suficiente.
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<hr style='border-color: #1F2937; margin: 1.25rem 0;'>", unsafe_allow_html=True)

    # 3. GRÁFICOS ANALÍTICOS (EVOLUCIÓN Y EMBUDO)
    col_chart_left, col_chart_right = st.columns([1.3, 1])
    with col_chart_left:
        st.plotly_chart(build_weekly_revenue_trend(df_orders), use_container_width=True, key="dash_chart_weekly")
    with col_chart_right:
        st.plotly_chart(build_orders_status_funnel(df_orders), use_container_width=True, key="dash_chart_funnel")

    st.markdown("<hr style='border-color: #1F2937; margin: 1.25rem 0;'>", unsafe_allow_html=True)

    # 4. FEED DE ACTIVIDAD / AUDITORÍA EN TIEMPO REAL
    st.markdown("<b style='color: #00F0FF; font-size: 1.05rem;'>⚡ Bitácora de Auditoría en Tiempo Real</b>", unsafe_allow_html=True)
    recent_logs = conn.execute(
        """
        SELECT usuario, entidad, entidad_id, accion, detalle, fecha
        FROM auditoria_logs
        WHERE organizacion_id = ?
        ORDER BY id DESC LIMIT 8
        """,
        (org_id,),
    ).fetchall()

    if not recent_logs:
        empty_state("No hay registros recientes en la bitácora de auditoría.")
    else:
        for log in recent_logs:
            icon = "🔧" if "orden" in log["entidad"].lower() else ("💳" if "venta" in log["entidad"].lower() else "📑")
            st.markdown(
                f"""
                <div style="background: #111827; border: 1px solid #1F2937; border-left: 3px solid #00F0FF; padding: 0.55rem 0.85rem; border-radius: 6px; margin-bottom: 0.45rem; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <span style="font-size: 0.85rem; color: #FFFFFF;">{icon} <b>@{log['usuario']}</b>: {log['detalle']}</span><br>
                        <span style="color: #6B7280; font-size: 0.72rem;">{log['entidad'].upper()} #{log['entidad_id']} · Acción: {log['accion']}</span>
                    </div>
                    <span style="color: #9CA3AF; font-size: 0.72rem; font-family: monospace;">{str(log['fecha'])[:16]}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
