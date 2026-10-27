"""Módulo de Ingesta y Gestión de Datos (Carga Manual y Batch Upload CSV/XLSX)."""

from datetime import date, timedelta
import io
import pandas as pd
import streamlit as st
from auth import get_available_technicians
from core.config import (
    CATEGORIAS_FALLA,
    ESTADOS_ORDEN,
    GARANTIAS_DIAS,
    MARCAS,
    MODELOS_POR_MARCA,
    TECNICOS,
)
from core.db import bulk_insert_orders, get_connection, get_next_order_id, insert_order


def render_tab_ingestion() -> None:
    """Renderiza el formulario de carga individual y el asistente de carga masiva."""
    st.markdown("<h4 style='color: #F3F4F6;'>Gestión Operativa de Órdenes de Trabajo (OT)</h4>", unsafe_allow_html=True)

    # Mostrar alerta de orden recién guardada si existe en session_state
    if "saved_order_alert" in st.session_state and st.session_state["saved_order_alert"]:
        ot_guardada = st.session_state["saved_order_alert"]
        st.markdown(
            f"""
            <div style="background: rgba(16, 185, 129, 0.15); border: 1px solid #10B981; border-left: 5px solid #10B981; padding: 0.85rem 1.25rem; border-radius: 8px; margin-bottom: 1.25rem;">
                <b style="color: #10B981; font-size: 1rem;">✅ ¡Orden {ot_guardada} guardada exitosamente en la Base de Datos!</b>
                <div style="color: #D1D5DB; font-size: 0.85rem; margin-top: 0.25rem;">
                    La orden ya está disponible en el sistema. Podés verla reflejada abajo en tiempo real o buscarla en la pestaña <b>Explorador & Auditoría</b>.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        del st.session_state["saved_order_alert"]

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

    # Tabla de verificación en vivo: Últimas 10 órdenes ingresadas
    render_recent_orders_table()


def render_manual_form() -> None:
    """Formulario dinámico y reactivo para registrar órdenes de servicio técnico."""
    next_id = get_next_order_id()

    with st.container():
        st.markdown(
            f"""
            <div style="background: rgba(0, 240, 255, 0.08); border: 1px solid rgba(0, 240, 255, 0.25); border-left: 4px solid #00F0FF; padding: 0.75rem 1.2rem; border-radius: 8px; margin-bottom: 1.25rem;">
                <b style="color: #00F0FF; font-size: 1.05rem;">Nueva Orden de Trabajo:</b> <span class="tech-mono" style="color: #FFFFFF; font-weight: 700; font-size: 1.1rem; margin-left: 0.5rem;">{next_id}</span>
                <span style="color: #9CA3AF; font-size: 0.8rem; margin-left: 1rem;">Seleccioná la marca para cargar automáticamente sus modelos disponibles.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Fila 1: ID y Fechas
        col_id, col_fingreso, col_fegreso = st.columns([1, 1.2, 1.2])
        with col_id:
            ot_id_input = st.text_input("ID Orden:", value=next_id, key="form_in_id_orden")
        with col_fingreso:
            fecha_ingreso = st.date_input("Fecha de Ingreso:", value=date.today(), key="form_in_fecha_ingreso")
        with col_fegreso:
            tiene_egreso = st.checkbox("¿Ya fue entregado/egresado?", value=False, key="form_chk_tiene_egreso")
            fecha_egreso = st.date_input("Fecha de Egreso:", value=date.today(), key="form_in_fecha_egreso") if tiene_egreso else None

        st.markdown("<div style='border-top: 1px solid #1F2937; margin: 0.75rem 0;'></div>", unsafe_allow_html=True)

        # Fila 2: Marca (Reactiva) y Modelo Dinámico
        col_m1, col_m2, col_cli, col_tel = st.columns(4)
        with col_m1:
            marcas_lista = MARCAS + ["Otra marca..."]
            marca_sel = st.selectbox("Marca del Dispositivo:", options=marcas_lista, index=0, key="form_sel_marca")
            if marca_sel == "Otra marca...":
                marca = st.text_input("Especificar Marca:", placeholder="Ej: OnePlus, TCL, ZTE", key="form_in_marca_custom")
            else:
                marca = marca_sel

        with col_m2:
            modelos_disponibles = MODELOS_POR_MARCA.get(marca_sel, []) + ["Otro (escribir manual)..."]
            modelo_sel = st.selectbox("Modelo:", options=modelos_disponibles, index=0, key="form_sel_modelo")
            if modelo_sel == "Otro (escribir manual)...":
                modelo = st.text_input("Especificar Modelo:", placeholder="Ej: Moto G84, A52, etc.", key="form_in_modelo_custom")
            else:
                modelo = modelo_sel

        with col_cli:
            cliente_nombre = st.text_input("Nombre de Cliente:", placeholder="Ej: Marcelo Gómez", key="form_in_cliente")
        with col_tel:
            cliente_telefono = st.text_input("Teléfono de Contacto:", placeholder="Ej: +54 9 11 5555-1234", key="form_in_tel")

        # Fila 3: Falla, Técnico e IMEI
        col_imei, col_falla, col_tec = st.columns([1.2, 1.8, 1.5])
        with col_imei:
            imei = st.text_input("IMEI / Nro de Serie:", placeholder="15 dígitos", key="form_in_imei")
        with col_falla:
            categoria_falla = st.selectbox("Categoría de Falla:", options=CATEGORIAS_FALLA, key="form_sel_falla")
        with col_tec:
            tecnicos_disponibles = get_available_technicians()
            opciones_tec = tecnicos_disponibles + ["Otro técnico (escribir manual)..."]
            usuario_actual = st.session_state.get("tecnico_nombre", "")
            idx_tec = opciones_tec.index(usuario_actual) if usuario_actual in opciones_tec else 0

            tec_sel = st.selectbox("Técnico Asignado:", options=opciones_tec, index=idx_tec, key="form_sel_tecnico")
            if tec_sel == "Otro técnico (escribir manual)...":
                tecnico = st.text_input("Especificar Nombre del Técnico:", placeholder="Ej: Juan Pérez / Mi Taller", key="form_in_tec_custom")
            else:
                tecnico = tec_sel

        diagnostico = st.text_area(
            "Diagnóstico Preliminar & Notas de Microelectrónica:",
            placeholder="Ej: Consumo de 120mA fijo en VDD_MAIN. Corto en capacitor C2401. Reemplazo de IC PMIC.",
            key="form_txt_diagnostico",
        )

        st.markdown("<div style='border-top: 1px solid #1F2937; margin: 0.75rem 0;'></div>", unsafe_allow_html=True)

        # Fila 4: Métricas Financieras y Estado (Cálculo de Margen en tiempo real)
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

        # Margen calculado en vivo
        margen_calculado = valor_cobrado - costo_repuesto
        margen_pct_calc = (margen_calculado / valor_cobrado * 100.0) if valor_cobrado > 0 else 0.0

        col_es_retorno, col_margen_prev = st.columns([1.5, 2.5])
        with col_es_retorno:
            es_retorno = st.checkbox("¿Es reingreso por garantía previa?", value=False, key="form_chk_garantia")
        with col_margen_prev:
            st.markdown(
                f"""
                <div style="background: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.35); padding: 0.45rem 0.9rem; border-radius: 6px; text-align: right; margin-top: 0.2rem;">
                    <span style="color: #9CA3AF; font-size: 0.78rem;">Margen Neto Estimado: </span>
                    <b style="color: #10B981; font-size: 1.1rem; margin-left: 0.3rem;">${margen_calculado:,.0f} ({margen_pct_calc:.1f}%)</b>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)

        btn_submit = st.button(
            "💾 Guardar Orden en Base de Datos",
            type="primary",
            use_container_width=True,
            key="btn_guardar_orden_manual",
        )

        if btn_submit:
            if not ot_id_input.strip():
                st.error("El ID de la orden no puede estar vacío.")
                return

            if not marca or not marca.strip():
                st.error("Debes indicar una marca para el dispositivo.")
                return

            if not modelo or not modelo.strip():
                st.error("Debes indicar un modelo para el dispositivo.")
                return

            if not tecnico or not tecnico.strip():
                st.error("Debes indicar el técnico a cargo de la orden.")
                return

            order_data = {
                "id_orden": ot_id_input.strip().upper(),
                "fecha_ingreso": str(fecha_ingreso),
                "fecha_egreso": str(fecha_egreso) if fecha_egreso else "",
                "fecha_ultimo_estado": str(date.today()),
                "cliente_nombre": cliente_nombre.strip(),
                "cliente_telefono": cliente_telefono.strip(),
                "imei": imei.strip(),
                "marca": marca.strip(),
                "modelo": modelo.strip(),
                "categoria_falla": categoria_falla,
                "diagnostico": diagnostico.strip(),
                "costo_repuesto": costo_repuesto,
                "valor_cobrado": valor_cobrado,
                "estado": estado,
                "tecnico": tecnico.strip(),
                "garantia_dias": garantia_dias,
                "es_retorno_garantia": 1 if es_retorno else 0,
            }

            try:
                insert_order(order_data)
                st.session_state["saved_order_alert"] = order_data["id_orden"]
                st.rerun()
            except Exception as exc:
                st.error(f"Error al guardar la orden: {exc}")


def render_recent_orders_table() -> None:
    """Muestra una tabla con las últimas 10 órdenes registradas directamente de SQLite."""
    st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)
    st.markdown(
        """
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.6rem;">
            <b style="color: #00F0FF; font-size: 1.05rem;">📋 Órdenes Recientes en el Taller (Últimas 10 Registradas)</b>
            <span style="color: #9CA3AF; font-size: 0.78rem;">Sincronizado en tiempo real con SQLite</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    conn = get_connection()
    recent_df = pd.read_sql_query(
        """
        SELECT id_orden, fecha_ingreso, marca, modelo, categoria_falla, 
               estado, valor_cobrado, margen_neto, cliente_nombre, imei, tecnico
        FROM ordenes 
        ORDER BY id DESC 
        LIMIT 10
        """,
        conn,
    )

    if recent_df.empty:
        st.info("No hay órdenes registradas.")
    else:
        st.dataframe(
            recent_df.rename(
                columns={
                    "id_orden": "ID Orden",
                    "fecha_ingreso": "Ingreso",
                    "marca": "Marca",
                    "modelo": "Modelo",
                    "categoria_falla": "Falla",
                    "estado": "Estado",
                    "valor_cobrado": "Cobrado ($)",
                    "margen_neto": "Margen ($)",
                    "cliente_nombre": "Cliente",
                    "imei": "IMEI",
                    "tecnico": "Técnico",
                }
            ),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Cobrado ($)": st.column_config.NumberColumn(format="$%d"),
                "Margen ($)": st.column_config.NumberColumn(format="$%d"),
            },
        )


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
                "marca": "Samsung",
                "modelo": "Galaxy S22 Ultra",
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
