"""Módulo de Ingesta y Gestión de Datos (Carga Manual y Batch Upload CSV/XLSX)."""

from datetime import date, timedelta
import io
import pandas as pd
import streamlit as st
from core.config import (
    CATEGORIAS_FALLA,
    ESTADOS_ORDEN,
    GARANTIAS_DIAS,
    MARCAS,
    MODELOS_POR_MARCA,
    TECNICOS,
)
from core.db import bulk_insert_orders, get_next_order_id, insert_order


def render_tab_ingestion() -> None:
    """Renderiza el formulario de carga individual y el asistente de carga masiva."""
    st.markdown("<h4 style='color: #F3F4F6;'>Gestión Operativa de Órdenes de Trabajo (OT)</h4>", unsafe_allow_html=True)

    method = st.radio(
        "Seleccionar método de ingreso de datos:",
        options=["📝 Carga Manual (Nueva Orden de Trabajo)", "📁 Carga Masiva (Batch Upload CSV / Excel)"],
        horizontal=True,
        key="ingestion_radio_method",
    )

    if method.startswith("📝"):
        render_manual_form()
    else:
        render_batch_upload()


def render_manual_form() -> None:
    """Formulario interactivo para registrar una nueva orden de servicio técnico."""
    next_id = get_next_order_id()

    with st.form("form_nueva_orden", clear_on_submit=True):
        st.markdown(
            f"""
            <div style="background: rgba(0, 240, 255, 0.08); border-left: 3px solid #00F0FF; padding: 0.6rem 1rem; border-radius: 6px; margin-bottom: 1.25rem;">
                <b style="color: #00F0FF;">Nueva Orden de Trabajo:</b> <span class="tech-mono" style="color: #FFFFFF; font-weight: 700;">{next_id}</span>
                <span style="color: #9CA3AF; font-size: 0.8rem; margin-left: 1rem;">Completá los datos técnicos y financieros del equipo.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_id, col_fingreso, col_fegreso = st.columns([1, 1.2, 1.2])
        with col_id:
            ot_id_input = st.text_input("ID Orden:", value=next_id, key="form_in_id_orden")
        with col_fingreso:
            fecha_ingreso = st.date_input("Fecha de Ingreso:", value=date.today(), key="form_in_fecha_ingreso")
        with col_fegreso:
            tiene_egreso = st.checkbox("¿Ya fue entregado/egresado?", value=False, key="form_chk_tiene_egreso")
            fecha_egreso = st.date_input("Fecha de Egreso:", value=date.today(), key="form_in_fecha_egreso") if tiene_egreso else None

        st.markdown("<div style='border-top: 1px solid #1F2937; margin: 0.75rem 0;'></div>", unsafe_allow_html=True)

        # Datos del Dispositivo y Cliente
        col_m1, col_m2, col_cli, col_tel = st.columns(4)
        with col_m1:
            marca = st.selectbox("Marca:", options=MARCAS, index=0, key="form_sel_marca")
        with col_m2:
            modelos_sugeridos = MODELOS_POR_MARCA.get(marca, ["Otro"])
            modelo = st.selectbox("Modelo:", options=modelos_sugeridos, key="form_sel_modelo")
        with col_cli:
            cliente_nombre = st.text_input("Nombre de Cliente:", placeholder="Ej: Marcelo Gómez", key="form_in_cliente")
        with col_tel:
            cliente_telefono = st.text_input("Teléfono de Contacto:", placeholder="Ej: +54 9 11 5555-1234", key="form_in_tel")

        col_imei, col_falla, col_tec = st.columns([1.2, 1.8, 1.5])
        with col_imei:
            imei = st.text_input("IMEI / Nro de Serie (15 dígitos):", placeholder="358492019485721", key="form_in_imei")
        with col_falla:
            categoria_falla = st.selectbox("Categoría de Falla:", options=CATEGORIAS_FALLA, key="form_sel_falla")
        with col_tec:
            tecnico = st.selectbox("Técnico Asignado:", options=TECNICOS, key="form_sel_tecnico")

        diagnostico = st.text_area(
            "Diagnóstico Preliminar & Notas de Microelectrónica:",
            placeholder="Ej: Consumo de 120mA fijo en VDD_MAIN. Corto en capacitor C2401. Reemplazo de IC PMIC.",
            key="form_txt_diagnostico",
        )

        st.markdown("<div style='border-top: 1px solid #1F2937; margin: 0.75rem 0;'></div>", unsafe_allow_html=True)

        # Métricas Financieras y Estado
        col_costo, col_cobrado, col_estado, col_garantia = st.columns(4)
        with col_costo:
            costo_repuesto = st.number_input(
                "Costo Repuesto / Insumo ($):",
                min_value=0.0,
                value=15000.0,
                step=1000.0,
                key="form_num_costo",
            )
        with col_cobrado:
            valor_cobrado = st.number_input(
                "Valor Cobrado / Presupuesto ($):",
                min_value=0.0,
                value=45000.0,
                step=1000.0,
                key="form_num_cobrado",
            )
        with col_estado:
            estado = st.selectbox("Estado Actual:", options=ESTADOS_ORDEN, index=0, key="form_sel_estado")
        with col_garantia:
            garantia_dias = st.selectbox("Garantía Otorgada (Días):", options=GARANTIAS_DIAS, index=1, key="form_sel_garantia")

        # Margen calculado en tiempo real
        margen_calculado = valor_cobrado - costo_repuesto
        margen_pct_calc = (margen_calculado / valor_cobrado * 100.0) if valor_cobrado > 0 else 0.0

        col_es_retorno, col_margen_prev = st.columns([1.5, 2.5])
        with col_es_retorno:
            es_retorno = st.checkbox("¿Es reingreso por garantía previa?", value=False, key="form_chk_garantia")
        with col_margen_prev:
            st.markdown(
                f"""
                <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); padding: 0.4rem 0.8rem; border-radius: 6px; text-align: right;">
                    <span style="color: #9CA3AF; font-size: 0.75rem;">Margen Neto Estimado: </span>
                    <b style="color: #10B981; font-size: 1.05rem;">${margen_calculado:,.0f} ({margen_pct_calc:.1f}%)</b>
                </div>
                """,
                unsafe_allow_html=True,
            )

        btn_submit = st.form_submit_button(
            "💾 Guardar Orden en Base de Datos",
            type="primary",
            use_container_width=True,
        )

        if btn_submit:
            if not ot_id_input.strip():
                st.error("El ID de la orden no puede estar vacío.")
                return

            order_data = {
                "id_orden": ot_id_input.strip().upper(),
                "fecha_ingreso": str(fecha_ingreso),
                "fecha_egreso": str(fecha_egreso) if fecha_egreso else "",
                "fecha_ultimo_estado": str(date.today()),
                "cliente_nombre": cliente_nombre.strip(),
                "cliente_telefono": cliente_telefono.strip(),
                "imei": imei.strip(),
                "marca": marca,
                "modelo": modelo,
                "categoria_falla": categoria_falla,
                "diagnostico": diagnostico.strip(),
                "costo_repuesto": costo_repuesto,
                "valor_cobrado": valor_cobrado,
                "estado": estado,
                "tecnico": tecnico,
                "garantia_dias": garantia_dias,
                "es_retorno_garantia": 1 if es_retorno else 0,
            }

            try:
                insert_order(order_data)
                st.success(f"✅ ¡Orden {order_data['id_orden']} registrada exitosamente en la base de datos!")
                st.rerun()
            except Exception as exc:
                st.error(f"Error al guardar la orden: {exc}")


def render_batch_upload() -> None:
    """Carga masiva de órdenes mediante archivo CSV o Excel con validación de esquema."""
    st.markdown(
        """
        <div style="background: #111827; border: 1px solid #1F2937; border-radius: 8px; padding: 1rem; margin-bottom: 1rem;">
            <b style="color: #00F0FF;">Pipeline de Validación Masiva:</b>
            <p style="color: #9CA3AF; font-size: 0.85rem; margin-top: 0.3rem;">
                Sube tu archivo <code class="tech-mono">.csv</code> o <code class="tech-mono">.xlsx</code> con las columnas obligatorias:
                <br><b>id_orden, fecha_ingreso, marca, modelo, categoria_falla, costo_repuesto, valor_cobrado, estado, tecnico</b>
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Descarga de plantilla CSV
    sample_df = pd.DataFrame(
        [
            {
                "id_orden": "OT-2001",
                "fecha_ingreso": "2026-10-01",
                "fecha_egreso": "2026-10-03",
                "marca": "Apple",
                "modelo": "iPhone 13",
                "imei": "354920194857211",
                "cliente_nombre": "Carlos Valenzuela",
                "cliente_telefono": "+54 9 11 4444-1234",
                "categoria_falla": "Pantalla / Módulo",
                "diagnostico": "Cambio de display OLED y TrueTone.",
                "costo_repuesto": 35000,
                "valor_cobrado": 75000,
                "estado": "Entregado",
                "tecnico": "Sofía G. (Hardware & Displays)",
                "garantia_dias": 90,
                "es_retorno_garantia": 0,
            }
        ]
    )
    csv_template = sample_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📄 Descargar Plantilla de Ejemplo (.CSV)",
        data=csv_template,
        file_name="plantilla_carga_taller.csv",
        mime="text/csv",
        key="ingestion_btn_sample_csv",
    )

    uploaded_file = st.file_uploader(
        "Arrastra o selecciona un archivo (.csv o .xlsx):",
        type=["csv", "xlsx"],
        key="ingestion_file_uploader",
    )

    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith(".csv"):
                df_upload = pd.read_csv(uploaded_file)
            else:
                df_upload = pd.read_excel(uploaded_file)

            st.write(f"Archivo cargado: `{uploaded_file.name}` ({len(df_upload)} filas encontradas).")

            # Validación de columnas obligatorias
            required_cols = [
                "id_orden",
                "fecha_ingreso",
                "marca",
                "modelo",
                "categoria_falla",
                "costo_repuesto",
                "valor_cobrado",
                "estado",
                "tecnico",
            ]
            missing_cols = [c for c in required_cols if c not in df_upload.columns]

            if missing_cols:
                st.error(f"❌ Error de esquema: Faltan las siguientes columnas obligatorias: {missing_cols}")
                return

            # Validación de fechas
            df_upload["fecha_ingreso"] = pd.to_datetime(df_upload["fecha_ingreso"], errors="coerce")
            invalid_dates = df_upload["fecha_ingreso"].isna().sum()
            if invalid_dates > 0:
                st.warning(f"⚠️ Atención: Se detectaron {invalid_dates} registros con fechas de ingreso no válidas o nulas.")

            # Vista previa
            st.markdown("<b>Vista previa de los primeros 10 registros validados:</b>", unsafe_allow_html=True)
            st.dataframe(df_upload.head(10), use_container_width=True)

            if st.button("🚀 Confirmar e Importar Registros a la Base de Datos", type="primary", key="ingestion_btn_confirm"):
                inserted_count = bulk_insert_orders(df_upload)
                st.success(f"🎉 ¡Se insertaron/actualizaron exitosamente {inserted_count} órdenes en la base de datos!")
                st.rerun()

        except Exception as exc:
            st.error(f"Error al procesar el archivo: {exc}")

