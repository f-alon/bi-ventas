"""Vista de Exploración y Auditoría de Datos (Tab 4: Data Explorer)."""

import io
from datetime import date
import pandas as pd
import streamlit as st
from components.cards import empty_state, format_currency


def render_tab_explorer(df: pd.DataFrame) -> None:
    """Tabla dinámica con filtros combinados, búsqueda global y exportación CSV/XLSX."""
    if df.empty:
        empty_state("No hay datos cargados para explorar.")
        return

    st.markdown("<h4 style='color: #F3F4F6; margin-bottom: 0.5rem;'>Auditoría y Exploración Avanzada</h4>", unsafe_allow_html=True)

    # Barra de búsqueda global
    search_query = st.text_input(
        "🔎 Búsqueda Rápida (ID Orden, IMEI, Nombre de Cliente o Modelo):",
        placeholder="Ej: OT-1042, 354891..., iPhone 13, Gómez...",
        key="explorer_input_search",
    )

    # Filtros avanzados en columnas colapsables
    with st.expander("⚙️ Filtros Combinados de Auditoría", expanded=True):
        f1, f2, f3 = st.columns(3)
        with f1:
            all_brands = sorted(df["marca"].dropna().unique().tolist())
            selected_brands = st.multiselect(
                "Marca de Dispositivo:",
                options=all_brands,
                default=all_brands,
                key="explorer_filter_brand",
            )
        with f2:
            all_statuses = df["estado"].dropna().unique().tolist()
            selected_statuses = st.multiselect(
                "Estado de la Orden:",
                options=all_statuses,
                default=all_statuses,
                key="explorer_filter_status",
            )
        with f3:
            all_techs = sorted(df["tecnico"].dropna().unique().tolist())
            selected_techs = st.multiselect(
                "Técnico Asignado:",
                options=all_techs,
                default=all_techs,
                key="explorer_filter_tech",
            )

        f4, f5 = st.columns([1.5, 1])
        with f4:
            all_categories = sorted(df["categoria_falla"].dropna().unique().tolist())
            selected_categories = st.multiselect(
                "Categoría de Falla:",
                options=all_categories,
                default=all_categories,
                key="explorer_filter_category",
            )
        with f5:
            min_p = float(df["valor_cobrado"].min())
            max_p = float(df["valor_cobrado"].max())
            if min_p < max_p:
                price_range = st.slider(
                    "Rango de Facturación ($):",
                    min_value=min_p,
                    max_value=max_p,
                    value=(min_p, max_p),
                    step=1000.0,
                    key="explorer_filter_price",
                )
            else:
                price_range = (min_p, max_p)

    # Aplicación de filtros
    filtered = df.copy()

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

    # Búsqueda por texto libre
    if search_query.strip():
        q = search_query.strip().lower()
        filtered = filtered[
            filtered["id_orden"].str.lower().str.contains(q, na=False)
            | filtered["imei"].str.lower().str.contains(q, na=False)
            | filtered["cliente_nombre"].str.lower().str.contains(q, na=False)
            | filtered["modelo"].str.lower().str.contains(q, na=False)
            | filtered["diagnostico"].str.lower().str.contains(q, na=False)
        ]

    # Resumen de resultados filtrados
    col_count, col_exp_csv, col_exp_excel = st.columns([2, 1, 1])
    with col_count:
        st.markdown(
            f"<div style='color: #00F0FF; font-weight: 700; margin-top: 0.6rem;'>"
            f"Mostrando {len(filtered)} de {len(df)} órdenes | Facturación Filtrada: {format_currency(filtered['valor_cobrado'].sum())} | Margen: {format_currency(filtered['margen_neto'].sum())}"
            f"</div>",
            unsafe_allow_html=True,
        )

    # Preparación de datos para exportación
    export_cols = [
        "id_orden",
        "fecha_ingreso",
        "fecha_egreso",
        "marca",
        "modelo",
        "imei",
        "cliente_nombre",
        "cliente_telefono",
        "categoria_falla",
        "diagnostico",
        "costo_repuesto",
        "valor_cobrado",
        "margen_neto",
        "estado",
        "tecnico",
        "garantia_dias",
        "es_retorno_garantia",
    ]
    export_df = filtered[[c for c in export_cols if c in filtered.columns]]

    # Botones de exportación
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
            # En caso de que openpyxl no esté instalado
            st.caption("Excel: Instalar openpyxl")

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

