"""Módulo 3.1: Control de Inventario, Variantes de Producto y Kardex (ERP LABFIX)."""

import io
import json
from typing import Any, Dict
import pandas as pd
import streamlit as st
from components.cards import empty_state, format_currency, format_number, metric_card
from core.config import CATEGORIAS_STOCK, SUBCATEGORIAS_STOCK, TIPOS_DISPOSITIVO
from database import get_connection, load_stock_df, log_audit


def render_inventario_view() -> None:
    """Renderiza el inventario, control de variantes y movimientos de stock."""
    user = st.session_state.get("username", "admin")
    org_id = st.session_state.get("organizacion_id", 1)

    st.markdown(
        """
        <div style="margin-bottom: 1.25rem;">
            <h2 style="color: #FFFFFF; font-weight: 800; margin: 0; font-size: 1.6rem; letter-spacing: -0.02em;">
                📦 Inventario de Repuestos, Variantes & Kardex
            </h2>
            <span style="color: #9CA3AF; font-size: 0.85rem;">
                Control de existencias, variantes por atributo (Color/Capacidad), semáforo y ajustes
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    conn = get_connection()
    df_stock = load_stock_df(org_id=org_id)

    t_list, t_var, t_adjust, t_new, t_import = st.tabs([
        "📊 Catálogo & Semáforo",
        "🧬 Variantes por Atributo",
        "⚡ Ajuste Manual / Kardex",
        "➕ Alta de Artículo",
        "📥 Importación Masiva",
    ])

    # 1. PESTAÑA CATÁLOGO & SEMÁFORO
    with t_list:
        if df_stock.empty:
            empty_state("Inventario vacío.", "Añade nuevos artículos desde la pestaña de alta.")
        else:
            val_costo = df_stock["valor_total_costo"].sum()
            val_venta = df_stock["valor_total_venta"].sum()
            utilidad_potencial = val_venta - val_costo
            criticos = len(df_stock[df_stock["alerta_reposicion"]])

            k1, k2, k3, k4 = st.columns(4)
            with k1:
                metric_card("Valorización (Costo)", format_currency(val_costo), glow_color="cyan")
            with k2:
                metric_card("Valorización (Venta)", format_currency(val_venta), glow_color="green")
            with k3:
                metric_card("Utilidad Teórica", format_currency(utilidad_potencial), glow_color="purple")
            with k4:
                metric_card("Bajo Stock Mínimo", f"{criticos} artículos", glow_color="red" if criticos > 0 else "neutral")

            st.markdown("<hr style='border-color: #1F2937; margin: 1.5rem 0;'>", unsafe_allow_html=True)

            c_f1, c_f2, c_f3 = st.columns([2, 1, 1])
            with c_f1:
                q_st = st.text_input("Filtrar por Nombre, SKU o Código de Barras:", placeholder="Display, Cable, Pin, 779...", key="stock_q_filter")
            with c_f2:
                cats = ["Todas"] + sorted(list(df_stock["categoria"].dropna().unique()))
                sel_cat = st.selectbox("Categoría:", cats, key="stock_cat_filter")
            with c_f3:
                solo_criticos = st.checkbox("⚠️ Solo bajo stock mínimo", key="stock_crit_filter")

            df_show = df_stock.copy()
            if q_st.strip():
                term = q_st.strip().lower()
                df_show = df_show[
                    df_show["nombre"].str.lower().str.contains(term, na=False)
                    | df_show["codigo_sku"].str.lower().str.contains(term, na=False)
                    | df_show["codigo_barras"].fillna("").str.lower().str.contains(term, na=False)
                ]
            if sel_cat != "Todas":
                df_show = df_show[df_show["categoria"] == sel_cat]
            if solo_criticos:
                df_show = df_show[df_show["alerta_reposicion"]]

            st.dataframe(
                df_show[[
                    "codigo_sku", "nombre", "categoria", "tipo_dispositivo",
                    "precio_compra", "precio_venta", "precio_venta_tecnicos", "stock_actual", "stock_minimo", "proveedor_nombre"
                ]],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "codigo_sku": st.column_config.TextColumn("SKU", width="small"),
                    "nombre": st.column_config.TextColumn("Descripción", width="large"),
                    "categoria": st.column_config.TextColumn("Categoría", width="small"),
                    "tipo_dispositivo": st.column_config.TextColumn("Dispositivo", width="small"),
                    "precio_compra": st.column_config.NumberColumn("Costo Compra", format="$%.0f"),
                    "precio_venta": st.column_config.NumberColumn("P. Venta", format="$%.0f"),
                    "precio_venta_tecnicos": st.column_config.NumberColumn("P. Técnicos", format="$%.0f"),
                    "stock_actual": st.column_config.NumberColumn("Stock", width="small"),
                    "stock_minimo": st.column_config.NumberColumn("Mín.", width="small"),
                    "proveedor_nombre": st.column_config.TextColumn("Proveedor", width="medium"),
                },
            )

    # 2. PESTAÑA MÓDULO DE VARIANTES
    with t_var:
        st.markdown("<b style='color: #00F0FF; font-size: 1rem;'>🧬 Gestión de Variantes por Atributo (Color / Capacidad / Versión)</b>", unsafe_allow_html=True)
        st.markdown("<span style='color: #9CA3AF; font-size: 0.82rem;'>Crea múltiples versiones de un producto base manteniendo proveedor y categoría pero con SKU, código de barras y precios independientes.</span>", unsafe_allow_html=True)

        if df_stock.empty:
            empty_state("No hay productos disponibles.", "Registra un producto base primero.")
        else:
            padres_disp = df_stock[df_stock["producto_padre_id"].isna()]
            dict_padres = {f"{r['codigo_sku']} - {r['nombre']}": r["id"] for _, r in padres_disp.iterrows()}

            with st.form(key="form_crear_variante"):
                sel_padre_str = st.selectbox("Seleccionar Producto Padre / Base:", list(dict_padres.keys()), key="var_padre_sel")
                padre_id = dict_padres[sel_padre_str]
                padre_row = df_stock[df_stock["id"] == padre_id].iloc[0]

                c_v1, c_v2, c_v3 = st.columns(3)
                with c_v1:
                    atrib_tipo = st.selectbox("Tipo de Atributo:", ["Color", "Capacidad / Almacenamiento", "Potencia / Wattage", "Calidad (OEM / Original)", "Otro"], key="var_attr_type")
                with c_v2:
                    atrib_valor = st.text_input("Valor del Atributo *:", placeholder="Ej: Negro / 128GB / 20W / OLED", key="var_attr_val")
                with c_v3:
                    sku_var = st.text_input("Nuevo SKU de la Variante *:", value=f"{padre_row['codigo_sku']}-", key="var_sku_in")

                c_p1, c_p2, c_p3, c_p4 = st.columns(4)
                with c_p1:
                    costo_var = st.number_input("Costo Compra ($):", min_value=0.0, value=float(padre_row["precio_compra"]), step=500.0, key="var_cost_in")
                with c_p2:
                    precio_var = st.number_input("Precio Venta ($):", min_value=0.0, value=float(padre_row["precio_venta"]), step=500.0, key="var_price_in")
                with c_p3:
                    precio_tec_var = st.number_input("Precio Gremio ($):", min_value=0.0, value=float(padre_row.get("precio_venta_tecnicos", 0.0)), step=500.0, key="var_ptec_in")
                with c_p4:
                    stock_var = st.number_input("Stock Inicial:", min_value=0, value=5, step=1, key="var_stk_in")

                submit_var = st.form_submit_button("🧬 Crear y Vincular Variante", use_container_width=True)
                if submit_var:
                    if not atrib_valor.strip() or not sku_var.strip():
                        st.error("El valor del atributo y el SKU son requeridos.")
                    else:
                        nom_variante = f"{padre_row['nombre']} ({atrib_tipo}: {atrib_valor.strip()})"
                        attr_data = json.dumps({atrib_tipo: atrib_valor.strip()}, ensure_ascii=False)
                        try:
                            with conn:
                                # Marcar al padre con tiene_variantes = 1
                                conn.execute("UPDATE productos SET tiene_variantes = 1 WHERE id = ?", (padre_id,))
                                # Crear la variante hija
                                conn.execute(
                                    """
                                    INSERT INTO productos (
                                        organizacion_id, codigo_sku, nombre, categoria, subcategoria,
                                        tipo_dispositivo, proveedor_id, precio_compra, precio_venta,
                                        precio_venta_tecnicos, stock_actual, stock_minimo, tiene_variantes,
                                        producto_padre_id, atributos_json
                                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 2, 0, ?, ?)
                                    """,
                                    (
                                        org_id, sku_var.strip().upper(), nom_variante, padre_row["categoria"],
                                        padre_row["subcategoria"], padre_row["tipo_dispositivo"], padre_row["proveedor_id"],
                                        costo_var, precio_var, precio_tec_var, stock_var, padre_id, attr_data,
                                    ),
                                )
                            log_audit(user, "productos", sku_var.strip().upper(), "CREAR_VARIANTE", f"Variante de {padre_row['codigo_sku']}", org_id=org_id)
                            st.toast(f"✅ Variante {sku_var} vinculada exitosamente", icon="🧬")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al crear variante (SKU duplicado): {e}")

    # 3. PESTAÑA AJUSTE MANUAL
    with t_adjust:
        st.markdown("<b style='color: #F59E0B; font-size: 1rem;'>⚡ Ajuste Manual de Inventario (Entrada / Merma)</b>", unsafe_allow_html=True)
        if df_stock.empty:
            empty_state("No hay productos en inventario.", "Agrega productos antes de realizar ajustes.")
        else:
            prods_dict = {f"{r['codigo_sku']} - {r['nombre']} (Stock actual: {r['stock_actual']})": r["id"] for _, r in df_stock.iterrows()}
            with st.form(key="form_ajuste_stock"):
                sel_item_str = st.selectbox("Seleccionar Producto:", list(prods_dict.keys()), key="adj_prod_sel")
                p_id_sel = prods_dict[sel_item_str]

                c_t, c_q = st.columns([1, 1])
                with c_t:
                    tipo_aj = st.selectbox("Tipo de Movimiento:", ["Ingreso por Compra / Reposición", "Egreso por Daño / Merma", "Ajuste de Conteo Físico"], key="adj_type_sel")
                with c_q:
                    cant_aj = st.number_input("Cantidad a Ajustar:", min_value=1, value=1, step=1, key="adj_qty_sel")

                motivo_aj = st.text_input("Motivo / Observación del Ajuste:", placeholder="Ej: Conteo mensual, rotura en banco...", key="adj_notes_in")

                submit_adj = st.form_submit_button("⚖️ Aplicar Ajuste en Base de Datos", use_container_width=True)
                if submit_adj:
                    delta = cant_aj if "Ingreso" in tipo_aj else -cant_aj
                    tipo_kardex = "INGRESO" if delta > 0 else "AJUSTE"
                    with conn:
                        conn.execute("UPDATE productos SET stock_actual = stock_actual + ? WHERE id = ?", (delta, p_id_sel))
                        conn.execute(
                            """
                            INSERT INTO movimientos_stock (organizacion_id, producto_id, tipo, cantidad, notas)
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            (org_id, p_id_sel, tipo_kardex, abs(delta), motivo_aj),
                        )
                    log_audit(user, "productos", str(p_id_sel), "AJUSTE_STOCK", f"{tipo_aj} ({delta:+d} u.) - {motivo_aj}", org_id=org_id)
                    st.toast("✅ Stock actualizado en Kardex", icon="⚖️")
                    st.rerun()

    # 4. PESTAÑA ALTA DE ARTÍCULO
    with t_new:
        st.markdown("<b style='color: #00F0FF; font-size: 1rem;'>Dar de Alta un Nuevo Producto o Repuesto Base</b>", unsafe_allow_html=True)
        proveedores = conn.execute("SELECT id, razon_social FROM proveedores WHERE organizacion_id = ? ORDER BY razon_social ASC", (org_id,)).fetchall()
        prov_dict = {p["razon_social"]: int(p["id"]) for p in proveedores}
        prov_options = ["Sin Proveedor Asignado"] + list(prov_dict.keys())

        with st.form(key="form_nuevo_producto_base"):
            c1, c2, c3 = st.columns([1, 2, 1])
            with c1:
                sku_in = st.text_input("Código SKU *", placeholder="MOD-SAM-A54", key="prod_sku_in")
            with c2:
                nom_in = st.text_input("Descripción del Producto *", placeholder="Módulo Samsung A54 5G Original con Marco", key="prod_nom_in")
            with c3:
                cat_in = st.selectbox("Categoría:", CATEGORIAS_STOCK, key="prod_cat_in")

            subcats = SUBCATEGORIAS_STOCK.get(cat_in, ["General"])
            c_s1, c_s2, c_s3 = st.columns(3)
            with c_s1:
                subcat_in = st.selectbox("Subcategoría:", subcats, key="prod_subcat_in")
            with c_s2:
                tipo_d_in = st.selectbox("Tipo de Dispositivo:", TIPOS_DISPOSITIVO, key="prod_dev_in")
            with c_s3:
                prov_in = st.selectbox("Proveedor Principal:", prov_options, key="prod_prov_in")

            c_costo, c_precio, c_tec, c_stock, c_min = st.columns(5)
            with c_costo:
                costo_comp = st.number_input("Costo Compra ($):", min_value=0.0, value=5000.0, step=500.0, key="prod_cost_in")
            with c_precio:
                precio_vta = st.number_input("P. Venta Público ($):", min_value=0.0, value=12000.0, step=500.0, key="prod_price_in")
            with c_tec:
                precio_tec = st.number_input("P. Gremio / Técnicos ($):", min_value=0.0, value=9500.0, step=500.0, key="prod_ptec_in")
            with c_stock:
                stock_ini = st.number_input("Stock Inicial:", min_value=0, value=5, step=1, key="prod_stock_in")
            with c_min:
                stock_min = st.number_input("Stock Mínimo:", min_value=1, value=2, step=1, key="prod_min_in")

            submit_p = st.form_submit_button("💾 Guardar Artículo en Catálogo", use_container_width=True)
            if submit_p:
                if not sku_in.strip() or not nom_in.strip():
                    st.error("El código SKU y la descripción son obligatorios.")
                else:
                    prov_id = prov_dict.get(prov_in) if prov_in != "Sin Proveedor Asignado" else None
                    try:
                        with conn:
                            conn.execute(
                                """
                                INSERT INTO productos (
                                    organizacion_id, codigo_sku, categoria, subcategoria, tipo_dispositivo,
                                    nombre, precio_compra, precio_venta, precio_venta_tecnicos,
                                    stock_actual, stock_minimo, proveedor_id
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    org_id, sku_in.strip().upper(), cat_in, subcat_in, tipo_d_in,
                                    nom_in.strip(), costo_comp, precio_vta, precio_tec,
                                    stock_ini, stock_min, prov_id,
                                ),
                            )
                        log_audit(user, "productos", sku_in.strip().upper(), "ALTA_PRODUCTO", f"{nom_in} (Stock: {stock_ini})", org_id=org_id)
                        st.toast(f"✅ Artículo {nom_in} guardado en stock", icon="📦")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar producto: {e}")

    # 5. PESTAÑA IMPORTACIÓN MASIVA
    with t_import:
        st.markdown("<b style='color: #00F0FF; font-size: 1rem;'>📥 Importación Masiva de Productos (CSV / Excel)</b>", unsafe_allow_html=True)
        st.markdown("<span style='color: #9CA3AF; font-size: 0.85rem;'>Sube una planilla con columnas: <code>codigo_sku</code>, <code>nombre</code>, <code>categoria</code>, <code>precio_compra</code>, <code>precio_venta</code>, <code>stock_actual</code></span>", unsafe_allow_html=True)

        uploaded_file = st.file_uploader("Seleccionar archivo Excel (.xlsx) o CSV (.csv):", type=["xlsx", "csv"], key="bulk_stock_upload")

        if uploaded_file:
            try:
                if uploaded_file.name.endswith(".csv"):
                    df_upload = pd.read_csv(uploaded_file)
                else:
                    df_upload = pd.read_excel(uploaded_file)

                st.markdown("<b style='color: #10B981;'>Vista Previa del Archivo a Importar:</b>", unsafe_allow_html=True)
                st.dataframe(df_upload.head(10), use_container_width=True)

                if st.button("🚀 Confirmar y Persistir en Base de Datos", type="primary", key="btn_confirm_bulk_import"):
                    count_imported = 0
                    with conn:
                        for _, row_u in df_upload.iterrows():
                            sku = str(row_u.get("codigo_sku", "")).strip().upper()
                            nom = str(row_u.get("nombre", "")).strip()
                            cat = str(row_u.get("categoria", "Repuestos")).strip()
                            p_comp = float(row_u.get("precio_compra", 0.0))
                            p_vta = float(row_u.get("precio_venta", 0.0))
                            stk = int(row_u.get("stock_actual", 1))

                            if sku and nom:
                                conn.execute(
                                    """
                                    INSERT OR REPLACE INTO productos (
                                        organizacion_id, codigo_sku, nombre, categoria,
                                        precio_compra, precio_venta, stock_actual, stock_minimo
                                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 2)
                                    """,
                                    (org_id, sku, nom, cat, p_comp, p_vta, stk),
                                )
                                count_imported += 1

                    log_audit(user, "productos", str(count_imported), "IMPORTACION_MASIVA", f"Se importaron {count_imported} productos", org_id=org_id)
                    st.toast(f"✅ ¡Se importaron {count_imported} productos exitosamente!", icon="📦")
                    st.rerun()

            except Exception as exc:
                st.error(f"Error al procesar el archivo: {exc}")
