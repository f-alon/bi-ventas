"""Generador de datos sintéticos hiperrealistas para el ERP LABFIX (Taller, POS, Stock y Caja)."""

from datetime import date, datetime, timedelta
import json
import random
import secrets
from auth import hash_password
from database import get_connection, init_db, purge_all_tables


def seed_database(force: bool = False) -> int:
    """Siembra el ecosistema relacional completo del ERP normalizado con multi-tenancy."""
    init_db()
    conn = get_connection()
    count_ot = conn.execute("SELECT COUNT(*) FROM ordenes_servicio").fetchone()[0]
    if count_ot > 0 and not force:
        return count_ot

    if force:
        purge_all_tables(keep_users=False)
        init_db()

    conn = get_connection()
    with conn:
        # 1. Organización Principal
        conn.execute(
            """
            INSERT OR REPLACE INTO organizaciones (
                id, nombre, cuit_rut, logo_base64, moneda_principal, pais, alicuota_iva_defecto,
                autoasignacion_tecnicos, direccion, telefono, email, terminos_legales
            ) VALUES (
                1, 'LABFIX Microelectrónica & Smartphone Lab', '30-71829401-9', '', 'ARS', 'Argentina', 21.0,
                1, 'Av. Corrientes 1250, CABA', '+54 9 11 5555-0199', 'contacto@labfix.com.ar',
                'La garantía cubre exclusivamente las piezas sustituidas y la mano de obra aplicada durante el plazo estipulado. Quedan excluidos daños por caídas, golpes, sobretensión o contacto con fluidos posterior a la entrega.'
            );
            """
        )

        # 2. Usuarios del Sistema (Roles Normalizados RBAC)
        pw_hash = hash_password("admin123")
        conn.execute(
            """
            INSERT OR REPLACE INTO usuarios (id, organizacion_id, username, password_hash, nombre, rol, comision_pct, totp_enabled, activo)
            VALUES 
                (1, 1, 'admin', ?, 'Administrador General', 'ADMIN', 0.0, 0, 1),
                (2, 1, 'lucas_tec', ?, 'Lucas M. (Microelectrónica)', 'TECNICO', 15.0, 0, 1),
                (3, 1, 'gonzalo_tec', ?, 'Gonzalo R. (Reballing & Soldadura)', 'TECNICO', 15.0, 0, 1),
                (4, 1, 'camila_pos', ?, 'Camila Mostrador', 'VENDEDOR', 5.0, 0, 1),
                (5, 1, 'matias_pos', ?, 'Matías Ventas', 'VENDEDOR', 5.0, 0, 1);
            """,
            (pw_hash, pw_hash, pw_hash, pw_hash, pw_hash),
        )

        # 3. Proveedores
        conn.execute(
            """
            INSERT OR REPLACE INTO proveedores (id, organizacion_id, razon_social, contacto, telefono, email, direccion, rubro)
            VALUES
                (1, 1, 'FixParts Argentina S.R.L.', 'Esteban Ruiz', '+54 11 4321-8899', 'ventas@fixparts.com.ar', 'Av. Warnes 1100, CABA', 'Módulos & Displays'),
                (2, 1, 'SMD Microelectronics Lab', 'Nicolás Páez', '+54 11 5544-2211', 'pedidos@smdlab.com', 'Paraná 450, CABA', 'ICs & Componentes SMD'),
                (3, 1, 'Baterías del Plata S.A.', 'Valeria Gómez', '+54 11 4789-3322', 'info@bateriasplata.com', 'Av. San Martín 2300, Vicente López', 'Baterías & Celdas'),
                (4, 1, 'Accesorios Phone Mayorista', 'Martín Silva', '+54 11 6012-3456', 'mayorista@phoneacc.com', 'Florida 550, CABA', 'Accesorios & Insumos');
            """
        )

        # 4. Clientes con Saldo en Cuenta Corriente
        clientes_data = [
            (1, 1, "Alejandro Gómez", "34589120", "+54 9 11 4455-1234", "agomez@gmail.com", "Av. Santa Fe 3400, CABA", 0.0),
            (2, 1, "Valeria Rossi", "29874512", "+54 9 11 5566-7890", "vrossi@hotmail.com", "Calle Corrientes 1250, CABA", 0.0),
            (3, 1, "Federico Benítez", "38120455", "+54 9 11 6677-4321", "fede.benitez@yahoo.com", "Belgrano 450, Quilmes", 15000.0),  # Debe 15000 en cta cte
            (4, 1, "Camila Fernández", "41258963", "+54 9 11 7788-9900", "camif@gmail.com", "Av. Rivadavia 8800, CABA", 0.0),
            (5, 1, "Esteban Morales", "32987410", "+54 9 11 3344-5566", "esteban.m@empresa.com", "Paseo Colón 700, CABA", 0.0),
            (6, 1, "Lucía Díaz", "36451289", "+54 9 11 2233-4455", "lucia.diaz@gmail.com", "Mitre 120, Avellaneda", 0.0),
            (7, 1, "Mariano Castro", "30147852", "+54 9 11 8899-0011", "mcastro@live.com", "Cabildo 2100, CABA", 0.0),
            (8, 1, "Florencia Romero", "39874125", "+54 9 11 9900-1122", "flor.romero@gmail.com", "Triunvirato 3900, CABA", 0.0),
        ]
        for c in clientes_data:
            conn.execute(
                """
                INSERT OR REPLACE INTO clientes (id, organizacion_id, nombre, dni_cuit, telefono, email, direccion, saldo_cuenta_corriente)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                c,
            )

        # 5. Categorías de Gasto Operativo (P&L)
        conn.execute(
            """
            INSERT OR REPLACE INTO categorias_gasto (id, organizacion_id, nombre, tipo, color, afecta_resultado) VALUES
                (1, 1, 'Alquiler y Expensas', 'FIJO', '#F43F5E', 1),
                (2, 1, 'Servicios (Luz, Internet, Agua)', 'FIJO', '#F59E0B', 1),
                (3, 1, 'Insumos de Soldadura y Limpieza', 'VARIABLE', '#00F0FF', 1),
                (4, 1, 'Sueldos y Honorarios', 'FIJO', '#8B5CF6', 1),
                (5, 1, 'Publicidad y Marketing', 'VARIABLE', '#10B981', 1),
                (6, 1, 'Retiros de Socios / Dividendos', 'VARIABLE', '#6B7280', 0);
            """
        )

        # 6. Gastos Recurrentes Programados
        conn.execute(
            """
            INSERT OR REPLACE INTO gastos_recurrentes (id, organizacion_id, concepto, monto, metodo_pago, categoria_id, frecuencia, proximo_vencimiento, pausado)
            VALUES
                (1, 1, 'Alquiler Taller y Laboratorio', 180000.0, 'Transferencia / Alias', 1, 'MENSUAL', date('now', '+5 days'), 0),
                (2, 1, 'Internet Fibra Óptica 500Mbps', 14500.0, 'Débito', 2, 'MENSUAL', date('now', '+10 days'), 0),
                (3, 1, 'Servicio Limpieza Especializada', 25000.0, 'Efectivo', 2, 'SEMANAL', date('now', '+3 days'), 0);
            """
        )

        # 7. Productos con Variantes y Precios
        prods = [
            (1, 1, "REP-OLED-IP13", "779123400101", "Módulo OLED iPhone 13 Service Pack", "Display original ensamblado con soporte TrueTone", "Repuestos", "Módulos / Displays OLED", "Smartphone", 1, 42000.0, 95000.0, 78000.0, 6, 2, 0, None, "{}"),
            (2, 1, "REP-OLED-S22U", "779123400102", "Módulo AMOLED Samsung Galaxy S22 Ultra", "Panel curvo original con marco metálico", "Repuestos", "Módulos / Displays OLED", "Smartphone", 1, 58000.0, 138000.0, 115000.0, 3, 2, 0, None, "{}"),
            (3, 1, "REP-DISP-A54", "779123400103", "Display Samsung Galaxy A54 5G Original", "Panel Super AMOLED 120Hz", "Repuestos", "Módulos / Displays OLED", "Smartphone", 1, 26000.0, 62000.0, 51000.0, 8, 3, 0, None, "{}"),
            (4, 1, "REP-DISP-G84", "779123400104", "Módulo Motorola Moto G84 5G", "Display pOLED con marco original", "Repuestos", "Módulos / Displays OLED", "Smartphone", 1, 22000.0, 52000.0, 43000.0, 5, 2, 0, None, "{}"),
            (5, 1, "BAT-IP12", "779123400105", "Batería iPhone 12 / 12 Pro 2815mAh", "Celda nueva Grado A con flex TI original", "Repuestos", "Baterías", "Smartphone", 3, 12500.0, 32000.0, 24000.0, 12, 4, 0, None, "{}"),
            (6, 1, "BAT-IP13", "779123400106", "Batería iPhone 13 3227mAh Alta Capacidad", "Batería certificada sin ciclos de carga", "Repuestos", "Baterías", "Smartphone", 3, 14000.0, 36000.0, 28000.0, 9, 3, 0, None, "{}"),
            (7, 1, "BAT-SAM-S21", "779123400107", "Batería Samsung S21 4000mAh", "Batería original Samsung EB-BG991ABY", "Repuestos", "Baterías", "Smartphone", 3, 11000.0, 29000.0, 22000.0, 7, 3, 0, None, "{}"),
            (8, 1, "PIN-USBC-SAM", "779123400108", "Flex Sub-Main Placa de Carga Galaxy A54", "Placa con micrófono y conector Type-C", "Repuestos", "Pines / Flex de Carga", "Smartphone", 1, 4500.0, 18000.0, 12000.0, 15, 5, 0, None, "{}"),
            (9, 1, "IC-TRISTAR-1610", "779123400109", "IC de Carga Tristar / Hydra 1612A1 Apple", "Circuito integrado de control USB BGA", "Repuestos", "ICs & Componentes SMD", "Smartphone", 2, 8500.0, 48000.0, 32000.0, 18, 5, 0, None, "{}"),
            (10, 1, "ACC-CARG-20W", "779123400110", "Cargador Rápido USB-C 20W PD", "Cargador para iPhone / Samsung Fast Charge", "Accesorios", "Cargadores de Pared", "Otro", 4, 6500.0, 17500.0, 13000.0, 24, 6, 0, None, "{}"),
            (11, 1, "ACC-CBL-TYPEC", "779123400111", "Cable Blindado Type-C a Type-C 60W 1.2m", "Cable mallado reforzado con Kevlar", "Accesorios", "Cables USB & Adaptadores", "Otro", 4, 2800.0, 7900.0, 5500.0, 35, 10, 0, None, "{}"),
            (12, 1, "ACC-CBL-LIGHT", "779123400112", "Cable USB-C a Lightning MFi 1m", "Cable certificado Apple resistente a tirones", "Accesorios", "Cables USB & Adaptadores", "Otro", 4, 3400.0, 9500.0, 7000.0, 20, 8, 0, None, "{}"),
            (13, 1, "INS-FLUX-AMTECH", "779123400113", "Flux Amtech NC-559-ASM Jeringa 10cc", "Flux original para microsoldadura SMD/BGA", "Herramientas/Insumos", "Flux & Estaño en Pasta", "Otro", 2, 9500.0, 19000.0, 16000.0, 12, 3, 0, None, "{}"),
            # Producto Padre con Variantes
            (14, 1, "ACC-FUNDA-PADRE", "", "Funda Antigolpes ShockProof Silicona", "Funda protectora con interior aterciopelado", "Accesorios", "Fundas & Carcasas", "Smartphone", 4, 3000.0, 8500.0, 6000.0, 45, 10, 1, None, "{}"),
            (15, 1, "ACC-FUNDA-IP13-BLK", "779123400115", "Funda ShockProof iPhone 13 - Negro Mate", "Color Negro Mate", "Accesorios", "Fundas & Carcasas", "Smartphone", 4, 3000.0, 8500.0, 6000.0, 20, 5, 0, 14, json.dumps({"Color": "Negro", "Modelo": "iPhone 13"})),
            (16, 1, "ACC-FUNDA-IP13-BLU", "779123400116", "Funda ShockProof iPhone 13 - Azul Sierra", "Color Azul Sierra", "Accesorios", "Fundas & Carcasas", "Smartphone", 4, 3000.0, 8500.0, 6000.0, 15, 5, 0, 14, json.dumps({"Color": "Azul", "Modelo": "iPhone 13"})),
            (17, 1, "ACC-FUNDA-S22-BLK", "779123400117", "Funda ShockProof Galaxy S22 - Negro Mate", "Color Negro Mate", "Accesorios", "Fundas & Carcasas", "Smartphone", 4, 3000.0, 8500.0, 6000.0, 10, 5, 0, 14, json.dumps({"Color": "Negro", "Modelo": "Galaxy S22"})),
        ]
        for p in prods:
            conn.execute(
                """
                INSERT OR REPLACE INTO productos (
                    id, organizacion_id, codigo_sku, codigo_barras, nombre, descripcion, categoria,
                    subcategoria, tipo_dispositivo, proveedor_id, precio_compra, precio_venta,
                    precio_venta_tecnicos, stock_actual, stock_minimo, tiene_variantes,
                    producto_padre_id, atributos_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                p,
            )

        # 8. Sesión de Caja Activa
        hoy_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            """
            INSERT OR REPLACE INTO caja_sesiones (id, organizacion_id, usuario_apertura_id, fecha_apertura, saldo_inicial_efectivo, estado)
            VALUES (1, 1, 1, ?, 35000.0, 'ABIERTA');
            """,
            (hoy_str,),
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO caja_movimientos (id, organizacion_id, sesion_id, tipo, concepto, monto, metodo_pago, comprobante_ref)
            VALUES (1, 1, 1, 'INGRESO', 'Apertura de Caja Diaria (Fondo Inicial de Cambio)', 35000.0, 'Efectivo', 'APERTURA-01');
            """
        )

        # 9. Órdenes de Servicio (Normalizadas en ordenes_servicio)
        today = date.today()
        ordenes = [
            # OT-1001: Entregada con Repuesto Consumido y Cobrado
            (
                1, 1, "OT-1001", 1, 2, 4, "Smartphone", "Apple", "iPhone 13", "354920194857211", "1234",
                "Impacto severo. Pantalla rota sin imagen.", "Se reemplazó módulo OLED Service Pack y TrueTone reprogramado.",
                "Sin corto en VDD_MAIN. Consumo en arranque: 380mA pico.", 95000.0,
                str(today - timedelta(days=10)), "ENTREGADA", json.dumps({"Enciende": True, "Pantalla / Touch": False, "Chasis / Curvo": True, "Puerto de Carga": True}),
                secrets.token_urlsafe(16), 42000.0, 53000.0, 95000.0, 30000.0, 0.0, 60,
                str(today - timedelta(days=12)), str(today - timedelta(days=10)), str(today - timedelta(days=10)), 0, None
            ),
            # OT-1002: Entregada (Cambio de Batería)
            (
                2, 1, "OT-1002", 2, 2, 4, "Smartphone", "Apple", "iPhone 12", "358741029384756", "",
                "Batería agotada, reinicios al 20%.", "Degradación de celda al 68%. Cambio por batería nueva Grado A.",
                "Consumo en reposo normal: 8mA.", 32000.0,
                str(today - timedelta(days=7)), "ENTREGADA", json.dumps({"Enciende": True, "Batería Hinchada": True}),
                secrets.token_urlsafe(16), 12500.0, 19500.0, 32000.0, 10000.0, 0.0, 60,
                str(today - timedelta(days=8)), str(today - timedelta(days=7)), str(today - timedelta(days=7)), 0, None
            ),
            # OT-1003: Completada / Lista para Retiro (Reballing SoC)
            (
                3, 1, "OT-1003", 3, 3, 5, "Smartphone", "Xiaomi", "Poco X3 Pro", "351209384756102", "Patrón Z",
                "Apagado súbito. Qcom 9008 en PC.", "Falla clásica de soldadura fría en SoC Snapdragon 860. Reballing conjunto CPU+RAM con estaño 183°C.",
                "Estabilizado en test térmico 100%. Memoria UFS OK.", 80000.0,
                str(today + timedelta(days=1)), "COMPLETADA", json.dumps({"Enciende": False, "Daño Líquido / Humedad": False}),
                secrets.token_urlsafe(16), 15000.0, 65000.0, 80000.0, 20000.0, 60000.0, 90,
                str(today - timedelta(days=5)), "", str(today - timedelta(days=1)), 0, None
            ),
            # OT-1004: En Reparación (Samsung S22 Ultra)
            (
                4, 1, "OT-1004", 4, 2, 5, "Smartphone", "Samsung", "Galaxy S22 Ultra", "359910283746501", "0000",
                "Display quebrado con manchas negras.", "Cambio de display AMOLED curvo ensamblado con marco original.",
                "Placa base intacta.", 118000.0,
                str(today + timedelta(days=2)), "EN REPARACIÓN", json.dumps({"Enciende": True, "Pantalla / Touch": False}),
                secrets.token_urlsafe(16), 58000.0, 60000.0, 118000.0, 40000.0, 78000.0, 60,
                str(today - timedelta(days=3)), "", str(today - timedelta(days=1)), 0, None
            ),
            # OT-1005: En Reparación (iPhone 11 - Microelectrónica IC Tristar)
            (
                5, 1, "OT-1005", 5, 2, 4, "Smartphone", "Apple", "iPhone 11", "356610293847561", "",
                "No carga ni conecta a PC. Batería muere rápido.", "Equipo no carga. Se diagnosticó IC Tristar en fuga.",
                "Consumo de 120mA en fuente previo a pulsar power. Reemplazo de IC 1612A1.", 53500.0,
                str(today + timedelta(days=1)), "EN REPARACIÓN", json.dumps({"Enciende": True, "Puerto de Carga": False}),
                secrets.token_urlsafe(16), 8500.0, 45000.0, 53500.0, 0.0, 53500.0, 60,
                str(today - timedelta(days=2)), "", str(today), 0, None
            ),
            # OT-1006: Esperando Repuestos (Moto G84)
            (
                6, 1, "OT-1006", 6, 3, 4, "Smartphone", "Motorola", "Moto G84 5G", "357710293847111", "4321",
                "Pin de carga sulfatado no ajusta cable.", "Humedad y pines destruidos en conector Type-C.",
                "A la espera de arribo de subplaca original.", 20200.0,
                str(today + timedelta(days=3)), "ESPERANDO REPUESTOS", json.dumps({"Enciende": True, "Puerto de Carga": False}),
                secrets.token_urlsafe(16), 4200.0, 16000.0, 20200.0, 5000.0, 15200.0, 30,
                str(today - timedelta(days=4)), "", str(today), 0, None
            ),
            # OT-1007: PENDIENTE / SIN ASIGNAR (Para testear autoasignación concurrente de técnicos)
            (
                7, 1, "OT-1007", 7, None, 5, "Notebook", "Dell", "Inspiron 15 5000", "DELL99218204", "",
                "No enciende tras corte de luz.", "",
                "", 45000.0,
                str(today + timedelta(days=4)), "PENDIENTE", json.dumps({"Enciende / Da Video": False, "Cargador Original Dejado": True}),
                secrets.token_urlsafe(16), 0.0, 45000.0, 45000.0, 10000.0, 35000.0, 60,
                str(today - timedelta(days=1)), "", str(today - timedelta(days=1)), 0, None
            ),
            # OT-1008: PENDIENTE / SIN ASIGNAR
            (
                8, 1, "OT-1008", 8, None, 4, "Consola / Placa de Video", "Sony", "PlayStation 5", "PS5-00918231", "",
                "Luz azul de la muerte (BLOD).", "",
                "", 65000.0,
                str(today + timedelta(days=5)), "PENDIENTE", json.dumps({"Enciende / Luces LED": True, "Salida de Video HDMI": False}),
                secrets.token_urlsafe(16), 0.0, 65000.0, 65000.0, 0.0, 65000.0, 90,
                str(today), "", str(today), 0, None
            ),
        ]

        for ot in ordenes:
            conn.execute(
                """
                INSERT OR REPLACE INTO ordenes_servicio (
                    id, organizacion_id, ot_codigo, cliente_id, tecnico_id, vendedor_id, tipo_dispositivo,
                    marca, modelo, imei_serie, patron_desbloqueo, problema, diagnostico_tecnico,
                    notas_microelectronica, presupuesto_estimado, fecha_entrega_estimada, estado,
                    checklist_json, hash_seguimiento_publico, costo_repuestos, mano_obra, total,
                    monto_senado, saldo_pendiente, garantia_dias, fecha_ingreso, fecha_egreso,
                    fecha_ultimo_estado, es_retorno_garantia, orden_garantia_origen_id
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?
                )
                """,
                ot,
            )

        # 10. Repuestos Usados con Snapshot de Costo Histórico
        repuestos_usados = [
            (1, 1, 1, 1, 1, 42000.0, 42000.0),  # Módulo OLED IP13 en OT-1001
            (2, 1, 2, 5, 1, 12500.0, 12500.0),  # Batería IP12 en OT-1002
            (3, 1, 5, 9, 1, 8500.0, 8500.0),    # IC Tristar en OT-1005
        ]
        for ru in repuestos_usados:
            conn.execute(
                """
                INSERT OR REPLACE INTO ordenes_repuestos (
                    id, organizacion_id, orden_id, producto_id, cantidad, costo_compra_snapshot, precio_cobrado
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ru,
            )

        # 11. Fotos de Órdenes
        conn.execute(
            """
            INSERT OR REPLACE INTO ordenes_fotos (id, organizacion_id, orden_id, momento, url_archivo, notas)
            VALUES
                (1, 1, 1, 'INGRESO', 'https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=400', 'Vidrio astillado en esquina superior derecha'),
                (2, 1, 1, 'REPARACION', 'https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=400', 'Desarme y aislamiento de blindajes'),
                (3, 1, 1, 'ENTREGA', 'https://images.unsplash.com/photo-1511707171634-5f897ff02560?w=400', 'Equipo ensamblado y funcionando al 100%');
            """
        )

        # 12. Ventas Mostrador (POS) y sus Ítems con Snapshot de Costo
        ventas_data = [
            (1, 1, "TCK-2001", 1, 4, 25400.0, 0.0, 0.0, 25400.0, "Efectivo", "Venta rápida mostrador", str(today - timedelta(days=2))),
            (2, 1, "TCK-2002", 3, 5, 17500.0, 0.0, 0.0, 17500.0, "Transferencia / Alias", "Cargador 20W Fast Charge", str(today - timedelta(days=1))),
            (3, 1, "TCK-2003", 2, 4, 34800.0, 2000.0, 0.0, 32800.0, "Débito", "Funda y cables reforzados", str(today)),
        ]
        for v in ventas_data:
            conn.execute(
                """
                INSERT OR REPLACE INTO ventas (
                    id, organizacion_id, numero_ticket, cliente_id, vendedor_id, subtotal,
                    descuento, recargo, total, metodo_pago, notas, creado_en
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                v,
            )

        # Ítems de Ventas con costo_compra_snapshot
        v_items = [
            (1, 1, 10, 1, 6500.0, 17500.0, 17500.0),   # Cargador 20W en Venta 1
            (2, 1, 11, 1, 2800.0, 7900.0, 7900.0),     # Cable USB-C en Venta 1
            (3, 2, 10, 1, 6500.0, 17500.0, 17500.0),   # Cargador 20W en Venta 2
            (4, 3, 15, 2, 3000.0, 8500.0, 17000.0),    # Fundas en Venta 3
            (5, 3, 12, 1, 3400.0, 9500.0, 9500.0),     # Cable Lightning en Venta 3
        ]
        for vi in v_items:
            conn.execute(
                """
                INSERT OR REPLACE INTO ventas_items (
                    id, venta_id, producto_id, cantidad, costo_compra_snapshot, precio_unitario, subtotal
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                vi,
            )

        # 13. Movimientos de Caja Diaria (Ingresos y Gastos Deducibles)
        movimientos = [
            (2, 1, 1, 'INGRESO', 'Venta POS TCK-2001 (Cargador y Cable USB-C)', None, 25400.0, 'Efectivo', '', 'TCK-2001', None, 1),
            (3, 1, 1, 'INGRESO', 'Cobro Saldo Final OT-1001 (iPhone 13)', None, 65000.0, 'Efectivo', '', 'REM-3001', 1, None),
            (4, 1, 1, 'INGRESO', 'Seña Ingreso OT-1004 (Samsung S22U)', None, 40000.0, 'Efectivo', '', 'REC-1004', 4, None),
            (5, 1, 1, 'EGRESO', 'Compra insumos limpieza y alcohol isopropílico', 3, 8500.0, 'Efectivo', '', 'GASTO-01', None, None),
            (6, 1, 1, 'EGRESO', 'Pago servicio publicidad en redes Meta Ads', 5, 12000.0, 'Transferencia / Alias', '', 'PUB-FEB', None, None),
        ]
        for m in movimientos:
            conn.execute(
                """
                INSERT OR REPLACE INTO caja_movimientos (
                    id, organizacion_id, sesion_id, tipo, concepto, categoria_id, monto,
                    metodo_pago, comprobante_archivo, comprobante_ref, ot_id, venta_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                m,
            )

        # 14. Remitos y Comprobantes
        conn.execute(
            """
            INSERT OR REPLACE INTO remitos (id, organizacion_id, codigo_remito, cliente_id, orden_id, total, saldo_pendiente, estado_pago)
            VALUES (1, 1, 'REM-3001', 1, 1, 95000.0, 0.0, 'PAGADO');
            """
        )

        # 15. Cotizaciones
        conn.execute(
            """
            INSERT OR REPLACE INTO cotizaciones (
                id, organizacion_id, codigo_cotizacion, cliente_id, ot_id, subtotal,
                descuento, alicuota_iva, tipo_cambio_usd, total, estado, firma_digital_base64,
                hash_publico, validez_dias, notas
            ) VALUES
                (1, 1, 'COT-4001', 5, 5, 53500.0, 0.0, 21.0, 1250.0, 64735.0, 'ACEPTADA', 'FIRMA_DIGITAL_SAMPLE', 'COT_HASH_4001', 15, 'Reemplazo de IC Tristar de carga'),
                (2, 1, 'COT-4002', 7, 7, 45000.0, 3000.0, 21.0, 1250.0, 50820.0, 'ENVIADA', '', 'COT_HASH_4002', 15, 'Diagnóstico de fuente de alimentación Notebook Dell'),
                (3, 1, 'COT-4003', 1, NULL, 18000.0, 0.0, 21.0, 1250.0, 21780.0, 'BORRADOR', '', 'COT_HASH_4003', 10, 'Mantenimiento preventivo general');
            """
        )

        # 16. Garantías RMA
        conn.execute(
            """
            INSERT OR REPLACE INTO garantias_reclamos (id, organizacion_id, orden_id, venta_id, motivo, estado, orden_derivada_id, resolucion_notas)
            VALUES
                (1, 1, 1, NULL, 'Línea vertical leve en esquina izquierda tras 5 días de uso.', 'RESUELTO', NULL, 'Se verificó ajuste de flex FPC en banco. Sin costo para el cliente.');
            """
        )

        # 17. Leads / CRM (Chatbot Santi, Web, Manual)
        conn.execute(
            """
            INSERT OR REPLACE INTO leads (id, organizacion_id, nombre, telefono, email, mensaje, origen, estado, usuario_asignado_id)
            VALUES
                (1, 1, 'Ignacio Peralta', '+54 9 11 3210-9876', 'iperalta@gmail.com', 'Hola Santi, se me cayó el iPhone 14 y no da imagen pero vibra. Cuánto sale?', 'CHATBOT_SANTI', 'CALIFICADO', 4),
                (2, 1, 'Lorena Méndez', '+54 9 11 8765-4321', 'lore.mendez@outlook.com', 'Buenas tardes, cambian batería de MacBook Pro M1?', 'WEB', 'NUEVO', 4),
                (3, 1, 'Rodrigo Torres', '+54 9 11 9876-1234', 'rtorres@empresa.com', 'Presupuesto por lote de 5 celulares corporativos Motorola.', 'MANUAL', 'CONTACTADO', 5);
            """
        )

        # 18. Auditoría
        conn.execute(
            """
            INSERT OR REPLACE INTO auditoria_logs (id, organizacion_id, usuario, entidad, entidad_id, accion, detalle)
            VALUES
                (1, 1, 'admin', 'sistema', '1', 'INICIALIZACION', 'Base de datos ERP inicializada con catálogo normalizado y multi-tenancy'),
                (2, 1, 'camila_pos', 'ordenes_servicio', 'OT-1004', 'CREACION', 'Ingreso de equipo Samsung Galaxy S22 Ultra'),
                (3, 1, 'lucas_tec', 'ordenes_servicio', 'OT-1001', 'CAMBIO_ESTADO', 'Orden finalizada y entregada con garantía de 60 días');
            """
        )

    return len(ordenes)
