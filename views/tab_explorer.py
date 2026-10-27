"""Vista de Exploración y Auditoría de Datos (Tab 4: Data Explorer)."""

import io
from datetime import date
import pandas as pd
import streamlit as st
from components.cards import empty_state, format_currency


def render_tab_explorer(df_all: pd.DataFrame) -> None:
    """Tabla dinámica con filtros combinados, búsqueda global y exportación CSV/XLSX."""
    if df_all.empty:
        empty_state("No hay datos cargados en la base de datos.")
        return

    st.markdown("<h4 style='color: #F3F4F6; margin-bottom: 0.5rem;'>Auditoría y Exploración Avanzada</h4>", unsafe_allow_html=True)

    def _clear_search_callback() -> None:
        st.session_state["explorer_input_search"] = ""

    # 1. Búsqueda Global Directa (Prioritaria)
    col_search, col_clear = st.columns([4, 1])
    with col_search:
        search_query = st.text_input(
            "🔎 Búsqueda Rápida Directa (ID Orden, IMEI, Nombre de Cliente, Teléfono o Modelo):",
            placeholder="Ej: OT-1366, 354891..., iPhone 14, Samarra...",
            key="explorer_input_search",
        )
    with col_clear:
        st.markdown("<div style='margin-top: 1.75rem;'></div>", unsafe_allow_html=True)
        st.button(
            "✖ Limpiar",
            on_click=_clear_search_callback,
            key="btn_clear_search",
            use_container_width=True,
        )

    # Si hay término de búsqueda, priorizamos la búsqueda global en TODO el dataset
    is_searching = bool(search_query.strip())

    if is_searching:
        q = search_query.strip().lower()
        filtered = df_all[
            df_all["id_orden"].astype(str).str.lower().str.contains(q, na=False)
            | df_all["imei"].astype(str).str.lower().str.contains(q, na=False)
            | df_all["cliente_nombre"].astype(str).str.lower().str.contains(q, na=False)
            | df_all["cliente_telefono"].astype(str).str.lower().str.contains(q, na=False)
            | df_all["modelo"].astype(str).str.lower().str.contains(q, na=False)
            | df_all["diagnostico"].astype(str).str.lower().str.contains(q, na=False)
            | df_all["marca"].astype(str).str.lower().str.contains(q, na=False)
        ]
        st.markdown(
            f"""
            <div style="background: rgba(0, 240, 255, 0.1); border-left: 3px solid #00F0FF; padding: 0.5rem 1rem; border-radius: 6px; margin: 0.5rem 0 1rem 0;">
                <b style="color: #00F0FF;">Búsqueda Global:</b> Mostrando <b style="color: #FFFFFF;">{len(filtered)}</b> resultado(s) para <code class="tech-mono" style="color: #00F0FF;">"{search_query}"</code> en toda la base de datos.
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        # 2. Filtros Combinados de Exploración (cuando no se busca un ID específico)
        with st.expander("⚙️ Filtros Combinados de Auditoría", expanded=False):
            c_date1, c_date2 = st.columns([2, 1])
            with c_date1:
                ver_todo = st.checkbox("Ver todo el historial completo (sin límite de fecha)", value=True, key="explorer_chk_vertodo")
            
            if not ver_todo and "fecha_ingreso_dt" in df_all:
                min_d = df_all["fecha_ingreso_dt"].min().date()
                max_d = df_all["fecha_ingreso_dt"].max().date()
                rango_fechas = st.date_input("Rango de fechas:", value=(min_d, max_d), min_value=min_d, max_value=max_d, key="explorer_date_range")
            else:
                rango_fechas = None

            f1, f2, f3 = st.columns(3)
            with f1:
                all_brands = sorted(df_all["marca"].dropna().unique().tolist())
                selected_brands = st.multiselect("Marca de Dispositivo:", options=all_brands, default=all_brands, key="explorer_filter_brand")
            with f2:
                all_statuses = df_all["estado"].dropna().unique().tolist()
                selected_statuses = st.multiselect("Estado de la Orden:", options=all_statuses, default=all_statuses, key="explorer_filter_status")
            with f3:
                all_techs = sorted(df_all["tecnico"].dropna().unique().tolist())
                selected_techs = st.multiselect("Técnico Asignado:", options=all_techs, default=all_techs, key="explorer_filter_tech")

            f4, f5 = st.columns([1.5, 1])
            with f4:
                all_categories = sorted(df_all["categoria_falla"].dropna().unique().tolist())
                selected_categories = st.multiselect("Categoría de Falla:", options=all_categories, default=all_categories, key="explorer_filter_category")
            with f5:
                min_p = float(df_all["valor_cobrado"].min())
                max_p = float(df_all["valor_cobrado"].max())
                if min_p < max_p:
                    price_range = st.slider("Rango Facturación ($):", min_value=min_p, max_value=max_p, value=(min_p, max_p), step=1000.0, key="explorer_filter_price")
                else:
                    price_range = (min_p, max_p)

        filtered = df_all.copy()

        # Aplicar rango de fechas si no está marcado "ver todo"
        if not ver_todo and isinstance(rango_fechas, (tuple, list)) and len(rango_fechas) == 2:
            s_d, e_d = rango_fechas
            filtered = filtered[
                (filtered["fecha_ingreso_dt"].dt.date >= s_d)
                & (filtered["fecha_ingreso_dt"].dt.date <= e_d)
            ]

        if selected_brands:
            filtered = filtered[filtered["marca"].isin(selected_brands)]
        if selected_statuses:
            filtered = filtered[filtered["estado"].isin(selected_statuses)]
        if selected_techs:
            filtered = filtered[filtered["tecnico"].isin(selected_techs)]
        if selected_categories:
            filtered = filtered[filtered["categoria_falla"].isin(selected_categories)]

        filtered = filtered[
            (filtered["valor_cobrado"] >= price_range[0])
            & (filtered["valor_cobrado"] <= price_range[1])
        ]

    # Barra de resumen y botones de exportación
    col_count, col_exp_csv, col_exp_excel = st.columns([2.2, 1, 1])
    with col_count:
        fact_filtrada = filtered["valor_cobrado"].sum() if not filtered.empty else 0
        margen_filtrado = filtered["margen_neto"].sum() if not filtered.empty else 0
        st.markdown(
            f"<div style='color: #00F0FF; font-weight: 700; margin-top: 0.6rem; font-size: 0.9rem;'>"
            f"Mostrando {len(filtered)} de {len(df_all)} órdenes | Facturación: {format_currency(fact_filtrada)} | Margen: {format_currency(margen_filtrado)}"
            f"</div>",
            unsafe_allow_html=True,
        )

    # Preparación de datos para exportación
    export_cols = [
        "id_orden", "fecha_ingreso", "fecha_egreso", "marca", "modelo", "imei",
        "cliente_nombre", "cliente_telefono", "categoria_falla", "diagnostico",
        "costo_repuesto", "valor_cobrado", "margen_neto", "estado", "tecnico",
        "garantia_dias", "es_retorno_garantia",
    ]
    export_df = filtered[[c for c in export_cols if c in filtered.columns]]

    with col_exp_csv:
        csv_data = export_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Exportar CSV",
            data=csv_data,
            file_name=f"ordenes_taller_{date.today()}.csv",
            mime="text/csv",
            key="explorer_btn_export_csv",
            use_container_width=True,
        )

    with col_exp_excel:
        try:
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
                export_df.to_excel(writer, index=False, sheet_name="Ordenes")
            excel_data = excel_buffer.getvalue()
            st.download_button(
                label="📊 Exportar Excel",
                data=excel_data,
                file_name=f"ordenes_taller_{date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="explorer_btn_export_excel",
                use_container_width=True,
            )
        except Exception:
            st.caption("Excel no disponible")

    # Tabla interactiva
    st.markdown("<div style='margin-top: 0.75rem;'></div>", unsafe_allow_html=True)
    if filtered.empty:
        empty_state("No hay órdenes que coincidan con la búsqueda o filtros aplicados.")
    else:
        display_cols = [
            "id_orden",
            "fecha_ingreso",
            "estado",
            "marca",
            "modelo",
            "categoria_falla",
            "diagnostico",
            "costo_repuesto",
            "valor_cobrado",
            "margen_neto",
            "tecnico",
            "cliente_nombre",
            "cliente_telefono",
            "imei",
        ]
        st.dataframe(
            filtered[display_cols].rename(
                columns={
                    "id_orden": "Orden",
                    "fecha_ingreso": "Ingreso",
                    "estado": "Estado",
                    "marca": "Marca",
                    "modelo": "Modelo",
                    "categoria_falla": "Categoría Falla",
                    "diagnostico": "Diagnóstico Técnico",
                    "costo_repuesto": "Costo Insumo ($)",
                    "valor_cobrado": "Cobrado ($)",
                    "margen_neto": "Margen ($)",
                    "tecnico": "Técnico",
                    "cliente_nombre": "Cliente",
                    "cliente_telefono": "Contacto",
                    "imei": "IMEI",
                }
            ),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Costo Insumo ($)": st.column_config.NumberColumn(format="$%d"),
                "Cobrado ($)": st.column_config.NumberColumn(format="$%d"),
                "Margen ($)": st.column_config.NumberColumn(format="$%d"),
            },
        )
