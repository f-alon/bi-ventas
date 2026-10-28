"""Capa de Persistencia Relacional SQLite, Multi-Tenancy (RLS) y Lógica Transaccional (ERP LABFIX)."""

from datetime import date, datetime, timedelta
import json
from pathlib import Path
import secrets
import sqlite3
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

DB_PATH = Path(__file__).resolve().parent / "data" / "repairs.db"


def get_connection() -> sqlite3.Connection:
    """Crea y retorna conexión con llaves foráneas activadas, WAL mode y timeout configurado."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30.0, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 10000;")
    except Exception:
        pass
    conn.row_factory = sqlite3.Row
    return conn


def _migrate_legacy_schema(conn: sqlite3.Connection) -> None:
    """Migra tablas legacy y asegura compatibilidad hacia adelante con nuevas columnas y vistas."""
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    
    # Si existen como tablas físicas que colisionan con las nuevas vistas, eliminarlas
    for legacy_tbl in ["dispositivos_ordenes", "productos_stock", "ordenes_repuestos_usados", "ordenes"]:
        if legacy_tbl in tables:
            try:
                conn.execute(f"DROP TABLE IF EXISTS {legacy_tbl};")
            except Exception:
                pass

    # Asegurar columnas en usuarios si la tabla ya existía
    if "usuarios" in tables:
        row_u = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='usuarios'").fetchone()
        if row_u and "'admin'" in row_u[0]:
            # Tiene constraint legacy en minúsculas. Migrar preservando datos a constraint en mayúsculas
            conn.execute("ALTER TABLE usuarios RENAME TO usuarios_old;")
            conn.execute(
                """
                CREATE TABLE usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    organizacion_id INTEGER NOT NULL DEFAULT 1,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    nombre TEXT NOT NULL,
                    rol TEXT NOT NULL CHECK(rol IN ('ADMIN', 'TECNICO', 'VENDEDOR')),
                    comision_pct REAL DEFAULT 0.0,
                    totp_secret TEXT DEFAULT '',
                    totp_enabled INTEGER DEFAULT 0,
                    backup_codes_json TEXT DEFAULT '[]',
                    activo INTEGER DEFAULT 1,
                    creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (organizacion_id) REFERENCES organizaciones(id)
                );
                """
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO usuarios (id, organizacion_id, username, password_hash, nombre, rol, comision_pct, activo, creado_en)
                SELECT id, 1, username, password_hash, nombre, UPPER(rol), comision_pct, activo, creado_en
                FROM usuarios_old;
                """
            )
            conn.execute("DROP TABLE IF EXISTS usuarios_old;")
        else:
            usr_cols = [r[1] for r in conn.execute("PRAGMA table_info(usuarios)").fetchall()]
            if "organizacion_id" not in usr_cols:
                conn.execute("ALTER TABLE usuarios ADD COLUMN organizacion_id INTEGER NOT NULL DEFAULT 1;")
            if "totp_secret" not in usr_cols:
                conn.execute("ALTER TABLE usuarios ADD COLUMN totp_secret TEXT DEFAULT '';")
            if "totp_enabled" not in usr_cols:
                conn.execute("ALTER TABLE usuarios ADD COLUMN totp_enabled INTEGER DEFAULT 0;")
            if "backup_codes_json" not in usr_cols:
                conn.execute("ALTER TABLE usuarios ADD COLUMN backup_codes_json TEXT DEFAULT '[]';")
            try:
                conn.execute("UPDATE usuarios SET rol = UPPER(rol) WHERE rol IN ('admin', 'tecnico', 'vendedor');")
            except Exception:
                pass

    # Asegurar columnas en clientes
    if "clientes" in tables:
        cli_cols = [r[1] for r in conn.execute("PRAGMA table_info(clientes)").fetchall()]
        if "organizacion_id" not in cli_cols:
            conn.execute("ALTER TABLE clientes ADD COLUMN organizacion_id INTEGER NOT NULL DEFAULT 1;")
        if "saldo_cuenta_corriente" not in cli_cols:
            conn.execute("ALTER TABLE clientes ADD COLUMN saldo_cuenta_corriente REAL DEFAULT 0.0;")

    # Asegurar columnas en proveedores
    if "proveedores" in tables:
        prov_cols = [r[1] for r in conn.execute("PRAGMA table_info(proveedores)").fetchall()]
        if "organizacion_id" not in prov_cols:
            conn.execute("ALTER TABLE proveedores ADD COLUMN organizacion_id INTEGER NOT NULL DEFAULT 1;")


def init_db() -> None:
    """Crea y migra el esquema relacional completo normalizado con soporte multi-taller."""
    conn = get_connection()
    with conn:
        _migrate_legacy_schema(conn)

        # 1. Organizaciones (Multi-Tenancy)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS organizaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                cuit_rut TEXT DEFAULT '',
                logo_base64 TEXT DEFAULT '',
                moneda_principal TEXT DEFAULT 'ARS',
                pais TEXT DEFAULT 'Argentina',
                alicuota_iva_defecto REAL DEFAULT 21.0,
                autoasignacion_tecnicos INTEGER DEFAULT 1,
                direccion TEXT DEFAULT '',
                telefono TEXT DEFAULT '',
                email TEXT DEFAULT '',
                terminos_legales TEXT DEFAULT '',
                creado_en TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        # Sembrar organización por defecto si está vacía
        row_org = conn.execute("SELECT id FROM organizaciones WHERE id = 1").fetchone()
        if not row_org:
            conn.execute(
                """
                INSERT INTO organizaciones (id, nombre, cuit_rut, moneda_principal, pais, alicuota_iva_defecto, autoasignacion_tecnicos, terminos_legales)
                VALUES (1, 'LABFIX Microelectrónica & Smartphone Lab', '30-71829401-9', 'ARS', 'Argentina', 21.0, 1, 
                'Garantía legal cubre exclusivamente los componentes reemplazados y la mano de obra aplicada. No cubre golpes, caídas o daño por líquidos posteriores.');
                """
            )

        # 2. Usuarios con RBAC y 2FA
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organizacion_id INTEGER NOT NULL DEFAULT 1,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                nombre TEXT NOT NULL,
                rol TEXT NOT NULL CHECK(rol IN ('ADMIN', 'TECNICO', 'VENDEDOR')),
                comision_pct REAL DEFAULT 0.0,
                totp_secret TEXT DEFAULT '',
                totp_enabled INTEGER DEFAULT 0,
                backup_codes_json TEXT DEFAULT '[]',
                activo INTEGER DEFAULT 1,
                creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organizacion_id) REFERENCES organizaciones(id)
            );
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_usr_org ON usuarios(organizacion_id);")

        # 3. Clientes con Cuenta Corriente
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organizacion_id INTEGER NOT NULL DEFAULT 1,
                nombre TEXT NOT NULL,
                dni_cuit TEXT DEFAULT '',
                telefono TEXT NOT NULL,
                email TEXT DEFAULT '',
                direccion TEXT DEFAULT '',
                saldo_cuenta_corriente REAL DEFAULT 0.0,
                creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organizacion_id) REFERENCES organizaciones(id)
            );
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cli_org_tel ON clientes(organizacion_id, telefono);")

        # 4. Proveedores
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS proveedores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organizacion_id INTEGER NOT NULL DEFAULT 1,
                razon_social TEXT NOT NULL,
                contacto TEXT DEFAULT '',
                telefono TEXT DEFAULT '',
                email TEXT DEFAULT '',
                direccion TEXT DEFAULT '',
                rubro TEXT DEFAULT 'General',
                creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organizacion_id) REFERENCES organizaciones(id)
            );
            """
        )

        # 5. Productos e Inventario con Soporte de Variantes
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organizacion_id INTEGER NOT NULL DEFAULT 1,
                codigo_sku TEXT UNIQUE NOT NULL,
                codigo_barras TEXT DEFAULT '',
                nombre TEXT NOT NULL,
                descripcion TEXT DEFAULT '',
                categoria TEXT NOT NULL DEFAULT 'Repuestos',
                subcategoria TEXT DEFAULT '',
                tipo_dispositivo TEXT DEFAULT 'Smartphone',
                proveedor_id INTEGER,
                precio_compra REAL NOT NULL DEFAULT 0.0,
                precio_venta REAL NOT NULL DEFAULT 0.0,
                precio_venta_tecnicos REAL DEFAULT 0.0,
                stock_actual INTEGER NOT NULL DEFAULT 0,
                stock_minimo INTEGER NOT NULL DEFAULT 2,
                tiene_variantes INTEGER DEFAULT 0,
                producto_padre_id INTEGER,
                atributos_json TEXT DEFAULT '{}',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organizacion_id) REFERENCES organizaciones(id),
                FOREIGN KEY (proveedor_id) REFERENCES proveedores(id),
                FOREIGN KEY (producto_padre_id) REFERENCES productos(id) ON DELETE SET NULL
            );
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_prod_org_sku ON productos(organizacion_id, codigo_sku);")

        # 6. Movimientos de Stock (Kardex)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS movimientos_stock (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organizacion_id INTEGER NOT NULL DEFAULT 1,
                producto_id INTEGER NOT NULL,
                tipo TEXT NOT NULL,
                cantidad INTEGER NOT NULL,
                ot_id INTEGER,
                venta_id INTEGER,
                notas TEXT DEFAULT '',
                fecha TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organizacion_id) REFERENCES organizaciones(id),
                FOREIGN KEY (producto_id) REFERENCES productos(id)
            );
            """
        )

        # 7. Órdenes de Servicio (OT)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ordenes_servicio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organizacion_id INTEGER NOT NULL DEFAULT 1,
                ot_codigo TEXT UNIQUE NOT NULL,
                cliente_id INTEGER NOT NULL,
                tecnico_id INTEGER,
                vendedor_id INTEGER,
                tipo_dispositivo TEXT NOT NULL DEFAULT 'Smartphone',
                marca TEXT NOT NULL,
                modelo TEXT NOT NULL,
                imei_serie TEXT DEFAULT '',
                patron_desbloqueo TEXT DEFAULT '',
                problema TEXT NOT NULL,
                diagnostico_tecnico TEXT DEFAULT '',
                notas_microelectronica TEXT DEFAULT '',
                presupuesto_estimado REAL DEFAULT 0.0,
                fecha_entrega_estimada TEXT DEFAULT '',
                estado TEXT NOT NULL DEFAULT 'PENDIENTE' CHECK(estado IN ('PENDIENTE', 'EN REPARACIÓN', 'ESPERANDO REPUESTOS', 'COMPLETADA', 'ENTREGADA', 'CANCELADA')),
                checklist_json TEXT DEFAULT '{}',
                hash_seguimiento_publico TEXT UNIQUE NOT NULL,
                costo_repuestos REAL NOT NULL DEFAULT 0.0,
                mano_obra REAL NOT NULL DEFAULT 0.0,
                total REAL NOT NULL DEFAULT 0.0,
                monto_senado REAL NOT NULL DEFAULT 0.0,
                saldo_pendiente REAL NOT NULL DEFAULT 0.0,
                garantia_dias INTEGER DEFAULT 60,
                fecha_ingreso TEXT NOT NULL,
                fecha_egreso TEXT DEFAULT '',
                fecha_ultimo_estado TEXT NOT NULL,
                es_retorno_garantia INTEGER DEFAULT 0,
                orden_garantia_origen_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organizacion_id) REFERENCES organizaciones(id),
                FOREIGN KEY (cliente_id) REFERENCES clientes(id),
                FOREIGN KEY (tecnico_id) REFERENCES usuarios(id) ON DELETE SET NULL,
                FOREIGN KEY (vendedor_id) REFERENCES usuarios(id) ON DELETE SET NULL
            );
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ot_org_cod ON ordenes_servicio(organizacion_id, ot_codigo);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ot_org_est ON ordenes_servicio(organizacion_id, estado);")

        # 8. Fotos de Órdenes (Ingreso, Reparación, Entrega)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ordenes_fotos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organizacion_id INTEGER NOT NULL DEFAULT 1,
                orden_id INTEGER NOT NULL,
                momento TEXT NOT NULL CHECK(momento IN ('INGRESO', 'REPARACION', 'ENTREGA')),
                url_archivo TEXT NOT NULL,
                notas TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organizacion_id) REFERENCES organizaciones(id),
                FOREIGN KEY (orden_id) REFERENCES ordenes_servicio(id) ON DELETE CASCADE
            );
            """
        )

        # 9. Repuestos Imputados a OTs con Snapshot Histórico
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ordenes_repuestos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organizacion_id INTEGER NOT NULL DEFAULT 1,
                orden_id INTEGER NOT NULL,
                producto_id INTEGER NOT NULL,
                cantidad INTEGER NOT NULL DEFAULT 1,
                costo_compra_snapshot REAL NOT NULL DEFAULT 0.0,
                precio_cobrado REAL NOT NULL DEFAULT 0.0,
                fecha TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organizacion_id) REFERENCES organizaciones(id),
                FOREIGN KEY (orden_id) REFERENCES ordenes_servicio(id) ON DELETE CASCADE,
                FOREIGN KEY (producto_id) REFERENCES productos(id)
            );
            """
        )

        # 10. Cotizaciones con Firma Digital y Alícuotas
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cotizaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organizacion_id INTEGER NOT NULL DEFAULT 1,
                codigo_cotizacion TEXT UNIQUE NOT NULL,
                cliente_id INTEGER NOT NULL,
                ot_id INTEGER,
                subtotal REAL NOT NULL DEFAULT 0.0,
                descuento REAL DEFAULT 0.0,
                alicuota_iva REAL DEFAULT 21.0,
                tipo_cambio_usd REAL DEFAULT 1200.0,
                total REAL NOT NULL DEFAULT 0.0,
                estado TEXT NOT NULL DEFAULT 'BORRADOR' CHECK(estado IN ('BORRADOR', 'ENVIADA', 'ACEPTADA', 'RECHAZADA')),
                firma_digital_base64 TEXT DEFAULT '',
                hash_publico TEXT UNIQUE NOT NULL,
                validez_dias INTEGER DEFAULT 15,
                notas TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organizacion_id) REFERENCES organizaciones(id),
                FOREIGN KEY (cliente_id) REFERENCES clientes(id),
                FOREIGN KEY (ot_id) REFERENCES ordenes_servicio(id) ON DELETE SET NULL
            );
            """
        )

        # 11. Remitos Oficiales
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS remitos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organizacion_id INTEGER NOT NULL DEFAULT 1,
                codigo_remito TEXT UNIQUE NOT NULL,
                cliente_id INTEGER NOT NULL,
                orden_id INTEGER,
                total REAL NOT NULL DEFAULT 0.0,
                saldo_pendiente REAL NOT NULL DEFAULT 0.0,
                estado_pago TEXT NOT NULL DEFAULT 'PENDIENTE' CHECK(estado_pago IN ('PENDIENTE', 'PAGADO PARCIAL', 'PAGADO')),
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organizacion_id) REFERENCES organizaciones(id),
                FOREIGN KEY (cliente_id) REFERENCES clientes(id),
                FOREIGN KEY (orden_id) REFERENCES ordenes_servicio(id) ON DELETE SET NULL
            );
            """
        )

        # 12. Ventas de Mostrador (POS)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ventas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organizacion_id INTEGER NOT NULL DEFAULT 1,
                numero_ticket TEXT UNIQUE NOT NULL,
                cliente_id INTEGER,
                vendedor_id INTEGER,
                subtotal REAL NOT NULL DEFAULT 0.0,
                descuento REAL DEFAULT 0.0,
                recargo REAL DEFAULT 0.0,
                total REAL NOT NULL DEFAULT 0.0,
                metodo_pago TEXT NOT NULL DEFAULT 'Efectivo',
                notas TEXT DEFAULT '',
                creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organizacion_id) REFERENCES organizaciones(id),
                FOREIGN KEY (cliente_id) REFERENCES clientes(id),
                FOREIGN KEY (vendedor_id) REFERENCES usuarios(id)
            );
            """
        )

        # 13. Ítems de Ventas con Snapshot de Costo
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ventas_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                venta_id INTEGER NOT NULL,
                producto_id INTEGER NOT NULL,
                cantidad INTEGER NOT NULL DEFAULT 1,
                costo_compra_snapshot REAL NOT NULL DEFAULT 0.0,
                precio_unitario REAL NOT NULL DEFAULT 0.0,
                subtotal REAL NOT NULL DEFAULT 0.0,
                FOREIGN KEY (venta_id) REFERENCES ventas(id) ON DELETE CASCADE,
                FOREIGN KEY (producto_id) REFERENCES productos(id)
            );
            """
        )

        # 14. Notas de Crédito
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notas_credito (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organizacion_id INTEGER NOT NULL DEFAULT 1,
                codigo_nc TEXT UNIQUE NOT NULL,
                entidad_tipo TEXT NOT NULL CHECK(entidad_tipo IN ('VENTA', 'ORDEN')),
                entidad_id INTEGER NOT NULL,
                cliente_id INTEGER,
                monto REAL NOT NULL DEFAULT 0.0,
                monto_compensado_cta_cte REAL DEFAULT 0.0,
                monto_efectivo_devuelto REAL DEFAULT 0.0,
                motivo TEXT NOT NULL,
                reintegra_stock INTEGER DEFAULT 0,
                producto_id INTEGER,
                cantidad INTEGER DEFAULT 1,
                estado TEXT DEFAULT 'EMITIDA',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organizacion_id) REFERENCES organizaciones(id),
                FOREIGN KEY (cliente_id) REFERENCES clientes(id)
            );
            """
        )

        # 15. Categorías de Gasto (P&L)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS categorias_gasto (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organizacion_id INTEGER NOT NULL DEFAULT 1,
                nombre TEXT NOT NULL,
                tipo TEXT NOT NULL CHECK(tipo IN ('FIJO', 'VARIABLE')),
                color TEXT DEFAULT '#00F0FF',
                afecta_resultado INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (organizacion_id) REFERENCES organizaciones(id)
            );
            """
        )

        # Sembrar categorías de gasto iniciales si no existen
        row_cat = conn.execute("SELECT id FROM categorias_gasto WHERE organizacion_id = 1 LIMIT 1").fetchone()
        if not row_cat:
            conn.execute(
                """
                INSERT INTO categorias_gasto (organizacion_id, nombre, tipo, color, afecta_resultado) VALUES
                (1, 'Alquiler y Expensas', 'FIJO', '#F43F5E', 1),
                (1, 'Servicios (Luz, Internet, Agua)', 'FIJO', '#F59E0B', 1),
                (1, 'Insumos de Soldadura y Limpieza', 'VARIABLE', '#00F0FF', 1),
                (1, 'Sueldos y Honorarios', 'FIJO', '#8B5CF6', 1),
                (1, 'Publicidad y Marketing', 'VARIABLE', '#10B981', 1),
                (1, 'Retiros de Socios / Dividendos', 'VARIABLE', '#6B7280', 0);
                """
            )

        # 16. Gastos Recurrentes Programados
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS gastos_recurrentes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organizacion_id INTEGER NOT NULL DEFAULT 1,
                concepto TEXT NOT NULL,
                monto REAL NOT NULL,
                metodo_pago TEXT NOT NULL DEFAULT 'Efectivo',
                categoria_id INTEGER NOT NULL,
                frecuencia TEXT NOT NULL CHECK(frecuencia IN ('SEMANAL', 'MENSUAL', 'ANUAL')),
                proximo_vencimiento TEXT NOT NULL,
                pausado INTEGER DEFAULT 0,
                FOREIGN KEY (organizacion_id) REFERENCES organizaciones(id),
                FOREIGN KEY (categoria_id) REFERENCES categorias_gasto(id)
            );
            """
        )

        # 17. Sesiones de Caja Diaria
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS caja_sesiones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organizacion_id INTEGER NOT NULL DEFAULT 1,
                usuario_apertura_id INTEGER NOT NULL,
                usuario_cierre_id INTEGER,
                fecha_apertura TEXT NOT NULL,
                fecha_cierre TEXT DEFAULT '',
                saldo_inicial_efectivo REAL NOT NULL DEFAULT 0.0,
                conteo_fisico_efectivo REAL DEFAULT 0.0,
                efectivo_esperado REAL DEFAULT 0.0,
                diferencia REAL DEFAULT 0.0,
                observaciones TEXT DEFAULT '',
                estado TEXT NOT NULL DEFAULT 'ABIERTA' CHECK(estado IN ('ABIERTA', 'CERRADA')),
                FOREIGN KEY (organizacion_id) REFERENCES organizaciones(id),
                FOREIGN KEY (usuario_apertura_id) REFERENCES usuarios(id),
                FOREIGN KEY (usuario_cierre_id) REFERENCES usuarios(id)
            );
            """
        )

        # 18. Movimientos de Caja Diaria
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS caja_movimientos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organizacion_id INTEGER NOT NULL DEFAULT 1,
                sesion_id INTEGER,
                tipo TEXT NOT NULL CHECK(tipo IN ('INGRESO', 'EGRESO')),
                concepto TEXT NOT NULL,
                categoria_id INTEGER,
                monto REAL NOT NULL,
                metodo_pago TEXT NOT NULL DEFAULT 'Efectivo',
                comprobante_archivo TEXT DEFAULT '',
                comprobante_ref TEXT DEFAULT '',
                ot_id INTEGER,
                venta_id INTEGER,
                fecha TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organizacion_id) REFERENCES organizaciones(id),
                FOREIGN KEY (sesion_id) REFERENCES caja_sesiones(id),
                FOREIGN KEY (categoria_id) REFERENCES categorias_gasto(id)
            );
            """
        )

        # 19. Garantías (RMA) y Reclamos
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS garantias_reclamos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organizacion_id INTEGER NOT NULL DEFAULT 1,
                orden_id INTEGER,
                venta_id INTEGER,
                motivo TEXT NOT NULL,
                estado TEXT NOT NULL DEFAULT 'PENDIENTE' CHECK(estado IN ('PENDIENTE', 'EN REVISIÓN', 'ACEPTADO', 'RECHAZADO', 'RESUELTO')),
                orden_derivada_id INTEGER,
                resolucion_notas TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organizacion_id) REFERENCES organizaciones(id),
                FOREIGN KEY (orden_id) REFERENCES ordenes_servicio(id) ON DELETE SET NULL,
                FOREIGN KEY (venta_id) REFERENCES ventas(id) ON DELETE SET NULL,
                FOREIGN KEY (orden_derivada_id) REFERENCES ordenes_servicio(id) ON DELETE SET NULL
            );
            """
        )

        # 20. Leads y CRM (Chatbot Santi / Kiosco / Manual)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organizacion_id INTEGER NOT NULL DEFAULT 1,
                nombre TEXT NOT NULL,
                telefono TEXT NOT NULL,
                email TEXT DEFAULT '',
                mensaje TEXT DEFAULT '',
                origen TEXT NOT NULL DEFAULT 'MANUAL' CHECK(origen IN ('CHATBOT_SANTI', 'MANUAL', 'WEB')),
                estado TEXT NOT NULL DEFAULT 'NUEVO' CHECK(estado IN ('NUEVO', 'CONTACTADO', 'CALIFICADO', 'CONVERTIDO', 'DESCARTADO')),
                usuario_asignado_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organizacion_id) REFERENCES organizaciones(id),
                FOREIGN KEY (usuario_asignado_id) REFERENCES usuarios(id)
            );
            """
        )

        # 21. Auditoría Inmutable
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS auditoria_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organizacion_id INTEGER NOT NULL DEFAULT 1,
                usuario TEXT NOT NULL,
                entidad TEXT NOT NULL,
                entidad_id TEXT NOT NULL,
                accion TEXT NOT NULL,
                detalle TEXT DEFAULT '',
                fecha TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        # 22. Tickets de Soporte Interno
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS soporte_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organizacion_id INTEGER NOT NULL DEFAULT 1,
                usuario_id INTEGER,
                titulo TEXT NOT NULL,
                descripcion TEXT NOT NULL,
                prioridad TEXT DEFAULT 'media',
                estado TEXT DEFAULT 'abierto',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        # 23. VISTAS DE COMPATIBILIDAD CON VISTAS LEGACY
        conn.execute("DROP VIEW IF EXISTS dispositivos_ordenes;")
        conn.execute("CREATE VIEW dispositivos_ordenes AS SELECT * FROM ordenes_servicio;")

        conn.execute("DROP VIEW IF EXISTS productos_stock;")
        conn.execute("CREATE VIEW productos_stock AS SELECT * FROM productos;")

        conn.execute("DROP VIEW IF EXISTS ordenes_repuestos_usados;")
        conn.execute("CREATE VIEW ordenes_repuestos_usados AS SELECT * FROM ordenes_repuestos;")


# ==============================================================================
# AUDITORÍA Y TRAZABILIDAD
# ==============================================================================

def log_audit(usuario: str, entidad: str, entidad_id: str, accion: str, detalle: str = "", org_id: int = 1, conn: Optional[sqlite3.Connection] = None) -> None:
    """Registra un evento inmutable en el historial de auditoría de la organización."""
    c = conn or get_connection()
    sql = """
        INSERT INTO auditoria_logs (organizacion_id, usuario, entidad, entidad_id, accion, detalle)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    params = (org_id, usuario, entidad, str(entidad_id), accion, detalle)
    if conn:
        c.execute(sql, params)
    else:
        with c:
            c.execute(sql, params)


# ==============================================================================
# ORGANIZACIÓN & CONFIGURACIÓN
# ==============================================================================

def get_workshop_config(org_id: int = 1) -> Dict[str, Any]:
    """Retorna los datos institucionales y de configuración de la organización."""
    init_db()
    conn = get_connection()
    row = conn.execute("SELECT * FROM organizaciones WHERE id = ?", (org_id,)).fetchone()
    if row:
        d = dict(row)
        d["nombre_taller"] = d["nombre"]  # alias para compatibilidad
        d["cuit"] = d["cuit_rut"]
        return d
    return {
        "id": 1,
        "nombre": "LABFIX Microelectrónica",
        "nombre_taller": "LABFIX Microelectrónica",
        "cuit_rut": "30-71829401-9",
        "cuit": "30-71829401-9",
        "moneda_principal": "ARS",
        "pais": "Argentina",
        "alicuota_iva_defecto": 21.0,
        "autoasignacion_tecnicos": 1,
        "direccion": "Av. Corrientes 1234, CABA",
        "telefono": "+54 9 11 5555-0199",
        "email": "contacto@labfix.com",
        "terminos_legales": "Garantía legal cubre fallas de componentes y mano de obra por 60 días corridos.",
    }


def update_workshop_config(data: Dict[str, Any], org_id: int = 1) -> bool:
    """Actualiza la configuración fiscal y operativa de la organización."""
    conn = get_connection()
    with conn:
        conn.execute(
            """
            UPDATE organizaciones SET
                nombre = ?, cuit_rut = ?, direccion = ?, telefono = ?, email = ?,
                moneda_principal = ?, pais = ?, alicuota_iva_defecto = ?,
                autoasignacion_tecnicos = ?, terminos_legales = ?
            WHERE id = ?
            """,
            (
                data.get("nombre", data.get("nombre_taller", "")),
                data.get("cuit_rut", data.get("cuit", "")),
                data.get("direccion", ""),
                data.get("telefono", ""),
                data.get("email", ""),
                data.get("moneda_principal", "ARS"),
                data.get("pais", "Argentina"),
                float(data.get("alicuota_iva_defecto", 21.0)),
                1 if data.get("autoasignacion_tecnicos", 1) else 0,
                data.get("terminos_legales", ""),
                org_id,
            ),
        )
    return True


# ==============================================================================
# GENERADORES DE CÓDIGOS CORRELATIVOS Y TOKENS PÚBLICOS
# ==============================================================================

def get_next_code(prefijo: str, tabla: str, columna: str, org_id: int = 1) -> str:
    """Genera el siguiente correlativo formateado (ej. OT-1001, COT-1001)."""
    conn = get_connection()
    sql = f"SELECT {columna} FROM {tabla} WHERE {columna} LIKE ? ORDER BY id DESC LIMIT 1"
    row = conn.execute(sql, (f"{prefijo}-%",)).fetchone()
    if row and row[0]:
        try:
            ultimo = int(row[0].split("-")[1])
            return f"{prefijo}-{ultimo + 1:04d}"
        except Exception:
            pass
    return f"{prefijo}-1001"


def generate_public_tracking_hash() -> str:
    """Genera un token hexadecimal criptográfico seguro para seguimiento público."""
    return secrets.token_urlsafe(16)


# ==============================================================================
# CLIENTES & CUENTA CORRIENTE
# ==============================================================================

def get_or_create_client(
    nombre: str,
    telefono: str,
    dni_cuit: str = "",
    email: str = "",
    direccion: str = "",
    org_id: int = 1,
) -> int:
    """Busca o crea un cliente garantizando unicidad de teléfono por organización."""
    conn = get_connection()
    clean_tel = telefono.strip()
    if clean_tel:
        row = conn.execute(
            "SELECT id FROM clientes WHERE organizacion_id = ? AND telefono = ?",
            (org_id, clean_tel),
        ).fetchone()
        if row:
            return int(row["id"])

    with conn:
        cur = conn.execute(
            """
            INSERT INTO clientes (organizacion_id, nombre, dni_cuit, telefono, email, direccion)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (org_id, nombre.strip(), dni_cuit.strip(), clean_tel, email.strip(), direccion.strip()),
        )
        return int(cur.lastrowid)


def get_all_clients(org_id: int = 1) -> List[Dict[str, Any]]:
    """Lista todos los clientes de la organización con su saldo."""
    init_db()
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM clientes WHERE organizacion_id = ? ORDER BY nombre ASC",
        (org_id,),
    ).fetchall()
    return [dict(r) for r in rows]


# ==============================================================================
# CAJA DIARIA, ARQUEOS Y GASTOS RECURRENTES
# ==============================================================================

def get_active_cash_session(org_id: int = 1) -> Optional[Dict[str, Any]]:
    """Retorna la sesión de caja abierta actualmente si existe."""
    init_db()
    conn = get_connection()
    row = conn.execute(
        """
        SELECT s.*, u.nombre as usuario_nombre
        FROM caja_sesiones s
        JOIN usuarios u ON s.usuario_apertura_id = u.id
        WHERE s.organizacion_id = ? AND s.estado = 'ABIERTA'
        ORDER BY s.id DESC LIMIT 1
        """,
        (org_id,),
    ).fetchone()
    if row:
        d = dict(row)
        d["monto_inicial"] = d["saldo_inicial_efectivo"]
        return d
    return None


def open_cash_session(usuario_id: int, monto_inicial: float, org_id: int = 1) -> int:
    """Abre la sesión de caja diaria de la organización (solo 1 activa en paralelo)."""
    conn = get_connection()
    activa = get_active_cash_session(org_id=org_id)
    if activa:
        return int(activa["id"])

    hoy_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with conn:
        cur = conn.execute(
            """
            INSERT INTO caja_sesiones (organizacion_id, usuario_apertura_id, fecha_apertura, saldo_inicial_efectivo, estado)
            VALUES (?, ?, ?, ?, 'ABIERTA')
            """,
            (org_id, usuario_id, hoy_str, float(monto_inicial)),
        )
        sesion_id = cur.lastrowid
        # Asiento de apertura en efectivo
        conn.execute(
            """
            INSERT INTO caja_movimientos (organizacion_id, sesion_id, tipo, concepto, monto, metodo_pago)
            VALUES (?, ?, 'INGRESO', 'Apertura de Turno (Fondo Fijo de Cambio)', ?, 'Efectivo')
            """,
            (org_id, sesion_id, float(monto_inicial)),
        )
        return int(sesion_id)


def close_cash_session(
    sesion_id: int,
    usuario_cierre_id: int,
    conteo_fisico: float,
    observaciones: str = "",
    org_id: int = 1,
) -> Dict[str, Any]:
    """Cierra la sesión de caja calculando diferencias auditadas frente al conteo físico."""
    conn = get_connection()
    # Calcular saldo teórico en efectivo de la sesión
    row_calc = conn.execute(
        """
        SELECT 
            COALESCE(SUM(CASE WHEN tipo = 'INGRESO' AND metodo_pago = 'Efectivo' THEN monto ELSE 0 END), 0) -
            COALESCE(SUM(CASE WHEN tipo = 'EGRESO' AND metodo_pago = 'Efectivo' THEN monto ELSE 0 END), 0) as saldo_teorico
        FROM caja_movimientos
        WHERE sesion_id = ?
        """,
        (sesion_id,),
    ).fetchone()
    saldo_teorico = float(row_calc["saldo_teorico"]) if row_calc else 0.0
    diferencia = float(conteo_fisico) - saldo_teorico
    hoy_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with conn:
        conn.execute(
            """
            UPDATE caja_sesiones SET
                fecha_cierre = ?, usuario_cierre_id = ?, conteo_fisico_efectivo = ?,
                efectivo_esperado = ?, diferencia = ?, observaciones = ?, estado = 'CERRADA'
            WHERE id = ?
            """,
            (hoy_str, usuario_cierre_id, float(conteo_fisico), saldo_teorico, diferencia, observaciones.strip(), sesion_id),
        )
    return {"saldo_teorico": saldo_teorico, "conteo_fisico": conteo_fisico, "diferencia": diferencia}


def add_cash_movement(
    tipo: str,
    concepto: str,
    monto: float,
    metodo_pago: str = "Efectivo",
    categoria_id: Optional[int] = None,
    comprobante_archivo: str = "",
    comprobante_ref: str = "",
    ot_id: Optional[int] = None,
    venta_id: Optional[int] = None,
    org_id: int = 1,
    conn: Optional[sqlite3.Connection] = None,
) -> bool:
    """Asienta un ingreso o egreso en la caja diaria."""
    c = conn or get_connection()
    row_s = c.execute(
        "SELECT id FROM caja_sesiones WHERE organizacion_id = ? AND estado = 'ABIERTA' ORDER BY id DESC LIMIT 1",
        (org_id,),
    ).fetchone()
    sesion_id = row_s["id"] if row_s else None

    sql = """
        INSERT INTO caja_movimientos (
            organizacion_id, sesion_id, tipo, concepto, categoria_id,
            monto, metodo_pago, comprobante_archivo, comprobante_ref, ot_id, venta_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    tipo_norm = "INGRESO" if "ingreso" in tipo.lower() else "EGRESO"
    params = (org_id, sesion_id, tipo_norm, concepto, float(monto), categoria_id, metodo_pago, comprobante_archivo, comprobante_ref, ot_id, venta_id)
    # Corrección de orden de parámetros
    params_fixed = (org_id, sesion_id, tipo_norm, concepto, categoria_id, float(monto), metodo_pago, comprobante_archivo, comprobante_ref, ot_id, venta_id)

    if conn:
        c.execute(sql, params_fixed)
    else:
        with c:
            c.execute(sql, params_fixed)
    return True


def execute_recurring_expenses(org_id: int = 1, user: str = "sistema") -> int:
    """Verifica gastos recurrentes vencidos, genera su asiento en caja y actualiza fecha."""
    conn = get_connection()
    hoy_str = str(date.today())
    rows = conn.execute(
        """
        SELECT g.*, c.nombre as cat_nombre
        FROM gastos_recurrentes g
        JOIN categorias_gasto c ON g.categoria_id = c.id
        WHERE g.organizacion_id = ? AND g.pausado = 0 AND g.proximo_vencimiento <= ?
        """,
        (org_id, hoy_str),
    ).fetchall()

    if not rows:
        return 0

    count = 0
    with conn:
        for r in rows:
            g_id = r["id"]
            monto = float(r["monto"])
            conc = f"Gasto Recurrente: {r['concepto']} ({r['cat_nombre']})"
            metodo = r["metodo_pago"]
            frec = r["frecuencia"]

            add_cash_movement(
                tipo="EGRESO",
                concepto=conc,
                monto=monto,
                metodo_pago=metodo,
                categoria_id=r["categoria_id"],
                comprobante_ref=f"REC-EXP-{g_id}",
                org_id=org_id,
                conn=conn,
            )

            # Calcular próxima fecha
            curr_d = datetime.strptime(r["proximo_vencimiento"], "%Y-%m-%d").date()
            if frec == "SEMANAL":
                next_d = curr_d + timedelta(days=7)
            elif frec == "MENSUAL":
                next_d = curr_d + timedelta(days=30)
            else:
                next_d = curr_d + timedelta(days=365)

            conn.execute(
                "UPDATE gastos_recurrentes SET proximo_vencimiento = ? WHERE id = ?",
                (str(next_d), g_id),
            )
            count += 1

    log_audit(user, "gastos_recurrentes", str(count), "GENERACION_VENCIDOS", f"Se aplicaron {count} gastos recurrentes a caja", org_id=org_id)
    return count


# ==============================================================================
# ÓRDENES DE SERVICIO (TALLER & FOTOS & CHECKLIST)
# ==============================================================================

def create_work_order(data: Dict[str, Any], user: str, org_id: int = 1) -> str:
    """Crea una orden de servicio con checklist dinámico, seña en caja y token de tracking."""
    conn = get_connection()
    ot_codigo = data.get("ot_codigo") or get_next_code("OT", "ordenes_servicio", "ot_codigo", org_id=org_id)
    tracking_hash = generate_public_tracking_hash()

    total = float(data.get("mano_obra", 0.0)) + float(data.get("costo_repuestos", 0.0))
    seña = float(data.get("monto_senado", 0.0))
    saldo = max(0.0, total - seña)
    hoy = str(date.today())

    checklist_str = json.dumps(data.get("checklist", {}), ensure_ascii=False)

    with conn:
        cur = conn.execute(
            """
            INSERT INTO ordenes_servicio (
                organizacion_id, ot_codigo, cliente_id, tecnico_id, vendedor_id,
                tipo_dispositivo, marca, modelo, imei_serie, patron_desbloqueo,
                problema, diagnostico_tecnico, notas_microelectronica, presupuesto_estimado,
                fecha_entrega_estimada, estado, checklist_json, hash_seguimiento_publico,
                costo_repuestos, mano_obra, total, monto_senado, saldo_pendiente,
                garantia_dias, fecha_ingreso, fecha_ultimo_estado, es_retorno_garantia,
                orden_garantia_origen_id
            ) VALUES (
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?
            )
            """,
            (
                org_id,
                ot_codigo,
                data["cliente_id"],
                data.get("tecnico_id"),
                data.get("vendedor_id"),
                data.get("tipo_dispositivo", "Smartphone"),
                data["marca"],
                data["modelo"],
                data.get("imei_serie", ""),
                data.get("patron_desbloqueo", ""),
                data["problema"],
                data.get("diagnostico_tecnico", ""),
                data.get("notas_microelectronica", ""),
                float(data.get("presupuesto_estimado", total)),
                str(data.get("fecha_entrega_estimada", "")),
                data.get("estado", "PENDIENTE"),
                checklist_str,
                tracking_hash,
                float(data.get("costo_repuestos", 0.0)),
                float(data.get("mano_obra", 0.0)),
                total,
                seña,
                saldo,
                int(data.get("garantia_dias", 60)),
                str(data.get("fecha_ingreso", hoy)),
                hoy,
                int(data.get("es_retorno_garantia", 0)),
                data.get("orden_garantia_origen_id"),
            ),
        )
        ot_id = cur.lastrowid

        # Si hubo seña, registrar remito/recibo y movimiento de caja
        if seña > 0:
            recibo_num = get_next_code("REC", "remitos", "codigo_remito", org_id=org_id)
            metodo = data.get("metodo_pago_seña", "Efectivo")
            conn.execute(
                """
                INSERT INTO remitos (organizacion_id, codigo_remito, cliente_id, orden_id, total, saldo_pendiente, estado_pago)
                VALUES (?, ?, ?, ?, ?, ?, 'PAGADO PARCIAL')
                """,
                (org_id, recibo_num, data["cliente_id"], ot_id, seña, saldo),
            )
            add_cash_movement(
                tipo="INGRESO",
                concepto=f"Cobro Seña {ot_codigo} ({data['marca']} {data['modelo']})",
                monto=seña,
                metodo_pago=metodo,
                comprobante_ref=recibo_num,
                ot_id=ot_id,
                org_id=org_id,
                conn=conn,
            )

    log_audit(user, "ordenes_servicio", ot_codigo, "CREACION", f"Ingreso OT {ot_codigo} ({data['marca']} {data['modelo']})", org_id=org_id)
    return ot_codigo


def claim_unassigned_work_order(ot_id: int, tecnico_id: int, user: str, org_id: int = 1) -> bool:
    """Toma una orden sin asignar con validación de concurrencia atómica."""
    conn = get_connection()
    with conn:
        cur = conn.execute(
            """
            UPDATE ordenes_servicio SET
                tecnico_id = ?,
                estado = CASE WHEN estado = 'PENDIENTE' THEN 'EN REPARACIÓN' ELSE estado END,
                fecha_ultimo_estado = ?
            WHERE id = ? AND organizacion_id = ? AND tecnico_id IS NULL
            """,
            (tecnico_id, str(date.today()), ot_id, org_id),
        )
        if cur.rowcount > 0:
            row_ot = conn.execute("SELECT ot_codigo FROM ordenes_servicio WHERE id = ?", (ot_id,)).fetchone()
            ot_cod = row_ot["ot_codigo"] if row_ot else str(ot_id)
            log_audit(user, "ordenes_servicio", ot_cod, "AUTOASIGNACION", f"El técnico tomó la orden {ot_cod}", org_id=org_id, conn=conn)
            return True
    return False


def save_order_photo(orden_id: int, momento: str, url_archivo: str, notas: str = "", org_id: int = 1) -> bool:
    """Guarda evidencia fotográfica vinculada a la orden."""
    conn = get_connection()
    with conn:
        conn.execute(
            """
            INSERT INTO ordenes_fotos (organizacion_id, orden_id, momento, url_archivo, notas)
            VALUES (?, ?, ?, ?, ?)
            """,
            (org_id, orden_id, momento.upper(), url_archivo, notas),
        )
    return True


def update_work_order_status(
    ot_codigo: str,
    nuevo_estado: str,
    user: str,
    diagnostico: Optional[str] = None,
    notas_micro: Optional[str] = None,
    org_id: int = 1,
) -> bool:
    """Actualiza el estado y detalles técnicos de la orden con trazabilidad."""
    conn = get_connection()
    hoy_str = str(date.today())
    updates = ["estado = ?", "fecha_ultimo_estado = ?"]
    params: List[Any] = [nuevo_estado, hoy_str]

    if nuevo_estado in ["COMPLETADA", "ENTREGADA"]:
        updates.append("fecha_egreso = COALESCE(NULLIF(fecha_egreso, ''), ?)")
        params.append(hoy_str)

    if diagnostico is not None:
        updates.append("diagnostico_tecnico = ?")
        params.append(diagnostico)

    if notas_micro is not None:
        updates.append("notas_microelectronica = ?")
        params.append(notas_micro)

    params.extend([ot_codigo, org_id])
    sql = f"UPDATE ordenes_servicio SET {', '.join(updates)} WHERE ot_codigo = ? AND organizacion_id = ?"

    with conn:
        conn.execute(sql, params)

    log_audit(user, "ordenes_servicio", ot_codigo, "CAMBIO_ESTADO", f"Nuevo estado: {nuevo_estado}", org_id=org_id)
    return True


def consume_part_for_order(
    ot_id: int,
    ot_codigo: str,
    producto_id: int,
    cantidad: int,
    precio_cobrado: float,
    user: str,
    org_id: int = 1,
) -> bool:
    """Imputa un repuesto a la OT tomando snapshot de su costo de compra histórico."""
    conn = get_connection()
    row_p = conn.execute("SELECT precio_compra, nombre FROM productos WHERE id = ? AND organizacion_id = ?", (producto_id, org_id)).fetchone()
    if not row_p:
        return False

    costo_snapshot = float(row_p["precio_compra"])

    with conn:
        # 1. Registrar imputación con snapshot
        conn.execute(
            """
            INSERT INTO ordenes_repuestos (organizacion_id, orden_id, producto_id, cantidad, costo_compra_snapshot, precio_cobrado)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (org_id, ot_id, producto_id, cantidad, costo_snapshot, float(precio_cobrado)),
        )
        # 2. Descontar inventario
        conn.execute("UPDATE productos SET stock_actual = stock_actual - ? WHERE id = ?", (cantidad, producto_id))
        # 3. Kardex
        conn.execute(
            """
            INSERT INTO movimientos_stock (organizacion_id, producto_id, tipo, cantidad, ot_id, notas)
            VALUES (?, ?, 'USADO_OT', ?, ?, ?)
            """,
            (org_id, producto_id, cantidad, ot_id, f"Insumo en OT {ot_codigo}"),
        )
        # 4. Actualizar costos de la orden
        conn.execute(
            """
            UPDATE ordenes_servicio SET
                costo_repuestos = costo_repuestos + ?,
                total = total + ?,
                saldo_pendiente = saldo_pendiente + ?
            WHERE id = ?
            """,
            (costo_snapshot * cantidad, precio_cobrado * cantidad, precio_cobrado * cantidad, ot_id),
        )

    log_audit(user, "ordenes_servicio", ot_codigo, "CONSUMO_REPUESTO", f"{cantidad}x {row_p['nombre']} (${precio_cobrado:,.0f} c/u)", org_id=org_id)
    return True


# ==============================================================================
# PUNTO DE VENTA (POS) Y VENTAS CON SNAPSHOT DE COSTO
# ==============================================================================

def process_pos_sale(
    cliente_id: Optional[int],
    vendedor_id: Optional[int],
    items: List[Dict[str, Any]],
    metodo_pago: str,
    descuento: float = 0.0,
    recargo: float = 0.0,
    user: str = "vendedor",
    notas: str = "",
    org_id: int = 1,
) -> str:
    """Procesa venta mostrador registrando snapshots de costo para el cálculo exacto de P&L."""
    conn = get_connection()
    tck_num = get_next_code("TCK", "ventas", "numero_ticket", org_id=org_id)
    subtotal = sum(float(it["precio"]) * int(it["cantidad"]) for it in items)
    total = max(0.0, subtotal - descuento + recargo)

    with conn:
        # 1. Crear venta
        cur_v = conn.execute(
            """
            INSERT INTO ventas (organizacion_id, numero_ticket, cliente_id, vendedor_id, subtotal, descuento, recargo, total, metodo_pago, notas)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (org_id, tck_num, cliente_id, vendedor_id, subtotal, descuento, recargo, total, metodo_pago, notas),
        )
        venta_id = cur_v.lastrowid

        # 2. Ítems, descuento de stock y snapshots de costo
        for it in items:
            p_id = int(it["id"])
            cant = int(it["cantidad"])
            p_unit = float(it["precio"])

            # Obtener costo de compra histórico del ítem
            row_c = conn.execute("SELECT precio_compra FROM productos WHERE id = ?", (p_id,)).fetchone()
            costo_snapshot = float(row_c["precio_compra"]) if row_c else 0.0

            conn.execute(
                """
                INSERT INTO ventas_items (venta_id, producto_id, cantidad, costo_compra_snapshot, precio_unitario, subtotal)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (venta_id, p_id, cant, costo_snapshot, p_unit, p_unit * cant),
            )
            conn.execute("UPDATE productos SET stock_actual = stock_actual - ? WHERE id = ?", (cant, p_id))
            conn.execute(
                """
                INSERT INTO movimientos_stock (organizacion_id, producto_id, tipo, cantidad, venta_id, notas)
                VALUES (?, ?, 'VENTA_POS', ?, ?, ?)
                """,
                (org_id, p_id, cant, venta_id, f"Venta ticket {tck_num}"),
            )

        # 3. Asentar en Caja Diaria
        add_cash_movement(
            tipo="INGRESO",
            concepto=f"Venta Mostrador {tck_num} ({len(items)} ítems)",
            monto=total,
            metodo_pago=metodo_pago,
            comprobante_ref=tck_num,
            venta_id=venta_id,
            org_id=org_id,
            conn=conn,
        )

        # 4. Si el pago fue con Cuenta Corriente y hay cliente, aumentar su saldo deudor
        if metodo_pago == "Cuenta Corriente" and cliente_id:
            conn.execute(
                "UPDATE clientes SET saldo_cuenta_corriente = saldo_cuenta_corriente + ? WHERE id = ?",
                (total, cliente_id),
            )

    log_audit(user, "ventas", tck_num, "VENTA_POS", f"Ticket {tck_num} por ${total:,.0f} ({metodo_pago})", org_id=org_id)
    return tck_num


# ==============================================================================
# NOTAS DE CRÉDITO CON COMPENSACIÓN DE DEUDA EN CUENTA CORRIENTE
# ==============================================================================

def create_credit_note(
    entidad_tipo: str,
    entidad_id: int,
    cliente_id: Optional[int],
    monto: float,
    motivo: str,
    reintegra_stock: bool = False,
    producto_id: Optional[int] = None,
    cantidad: int = 1,
    user: str = "admin",
    org_id: int = 1,
) -> str:
    """Emite una Nota de Crédito. Si el cliente tiene deuda en cuenta corriente, la compensa primero."""
    conn = get_connection()
    nc_codigo = get_next_code("NC", "notas_credito", "codigo_nc", org_id=org_id)
    monto_total = float(monto)
    monto_compensado = 0.0
    monto_efectivo = monto_total

    with conn:
        # Verificar si el cliente tiene saldo deudor en cuenta corriente
        if cliente_id:
            row_cli = conn.execute("SELECT saldo_cuenta_corriente FROM clientes WHERE id = ?", (cliente_id,)).fetchone()
            if row_cli and float(row_cli["saldo_cuenta_corriente"]) > 0:
                deuda_actual = float(row_cli["saldo_cuenta_corriente"])
                monto_compensado = min(deuda_actual, monto_total)
                monto_efectivo = max(0.0, monto_total - monto_compensado)

                # Descontar la deuda
                conn.execute(
                    "UPDATE clientes SET saldo_cuenta_corriente = saldo_cuenta_corriente - ? WHERE id = ?",
                    (monto_compensado, cliente_id),
                )

        # Registrar la Nota de Crédito
        conn.execute(
            """
            INSERT INTO notas_credito (
                organizacion_id, codigo_nc, entidad_tipo, entidad_id, cliente_id,
                monto, monto_compensado_cta_cte, monto_efectivo_devuelto, motivo,
                reintegra_stock, producto_id, cantidad
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                org_id, nc_codigo, entidad_tipo.upper(), entidad_id, cliente_id,
                monto_total, monto_compensado, monto_efectivo, motivo,
                1 if reintegra_stock else 0, producto_id, cantidad,
            ),
        )

        # Si hubo devolución física de dinero, impactar egreso en caja
        if monto_efectivo > 0:
            add_cash_movement(
                tipo="EGRESO",
                concepto=f"Reintegro NC {nc_codigo} ({motivo})",
                monto=monto_efectivo,
                metodo_pago="Efectivo",
                comprobante_ref=nc_codigo,
                org_id=org_id,
                conn=conn,
            )

        # Si se reincorpora el producto al stock
        if reintegra_stock and producto_id:
            conn.execute("UPDATE productos SET stock_actual = stock_actual + ? WHERE id = ?", (cantidad, producto_id))
            conn.execute(
                """
                INSERT INTO movimientos_stock (organizacion_id, producto_id, tipo, cantidad, notas)
                VALUES (?, ?, 'DEVOLUCION_NC', ?, ?)
                """,
                (org_id, producto_id, cantidad, f"Reintegro por NC {nc_codigo}"),
            )

    log_audit(
        user, "notas_credito", nc_codigo, "EMISION_NC",
        f"NC {nc_codigo} Total ${monto_total:,.0f} (Compensado cta/cte: ${monto_compensado:,.0f}, Efectivo: ${monto_efectivo:,.0f})",
        org_id=org_id,
    )
    return nc_codigo


# ==============================================================================
# COTIZACIONES CON FIRMA DIGITAL Y CONVERSIÓN A REMITO
# ==============================================================================

def create_quote(data: Dict[str, Any], user: str, org_id: int = 1) -> str:
    """Crea una cotización/presupuesto formal con desglose impositivo y token público."""
    conn = get_connection()
    num_cot = get_next_code("COT", "cotizaciones", "codigo_cotizacion", org_id=org_id)
    public_hash = generate_public_tracking_hash()

    subtotal = float(data.get("subtotal", 0.0))
    desc = float(data.get("descuento", 0.0))
    alicuota = float(data.get("alicuota_iva", 21.0))
    tipo_cambio = float(data.get("tipo_cambio_usd", 1200.0))

    base_imponible = max(0.0, subtotal - desc)
    iva_monto = base_imponible * (alicuota / 100.0)
    total = base_imponible + iva_monto

    with conn:
        conn.execute(
            """
            INSERT INTO cotizaciones (
                organizacion_id, codigo_cotizacion, cliente_id, ot_id,
                subtotal, descuento, alicuota_iva, tipo_cambio_usd, total,
                estado, hash_publico, validez_dias, notas
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'BORRADOR', ?, ?, ?)
            """,
            (
                org_id, num_cot, data["cliente_id"], data.get("ot_id"),
                subtotal, desc, alicuota, tipo_cambio, total,
                public_hash, int(data.get("validez_dias", 15)), data.get("notas", ""),
            ),
        )

    log_audit(user, "cotizaciones", num_cot, "CREACION_COTIZACION", f"Presupuesto {num_cot} por ${total:,.0f}", org_id=org_id)
    return num_cot


def approve_quote(cotizacion_id: int, user: str, firma_base64: str = "", org_id: int = 1) -> bool:
    """Aprueba la cotización, guarda la firma digital y pasa la OT a 'EN REPARACIÓN'."""
    conn = get_connection()
    row = conn.execute("SELECT ot_id, codigo_cotizacion FROM cotizaciones WHERE id = ? AND organizacion_id = ?", (cotizacion_id, org_id)).fetchone()
    if not row:
        return False

    with conn:
        conn.execute(
            "UPDATE cotizaciones SET estado = 'ACEPTADA', firma_digital_base64 = ? WHERE id = ?",
            (firma_base64, cotizacion_id),
        )
        ot_id = row["ot_id"]
        if ot_id:
            conn.execute(
                "UPDATE ordenes_servicio SET estado = 'EN REPARACIÓN', fecha_ultimo_estado = ? WHERE id = ?",
                (str(date.today()), ot_id),
            )

    log_audit(user, "cotizaciones", row["codigo_cotizacion"], "APROBACION_COTIZACION", f"Cotización aprobada por cliente", org_id=org_id)
    return True


def convert_quote_to_remito(cotizacion_id: int, user: str, org_id: int = 1) -> str:
    """Convierte una cotización aprobada en un Remito oficial de entrega."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM cotizaciones WHERE id = ? AND organizacion_id = ?", (cotizacion_id, org_id)).fetchone()
    if not row:
        return ""

    rem_cod = get_next_code("REM", "remitos", "codigo_remito", org_id=org_id)
    with conn:
        conn.execute(
            """
            INSERT INTO remitos (organizacion_id, codigo_remito, cliente_id, orden_id, total, saldo_pendiente, estado_pago)
            VALUES (?, ?, ?, ?, ?, ?, 'PENDIENTE')
            """,
            (org_id, rem_cod, row["cliente_id"], row["ot_id"], row["total"], row["total"]),
        )
    log_audit(user, "remitos", rem_cod, "CONVERSION_REMITO", f"Convertido desde cotización {row['codigo_cotizacion']}", org_id=org_id)
    return rem_cod


# ==============================================================================
# GARANTÍAS (RMA) Y ÓRDENES DERIVADAS ($0)
# ==============================================================================

def create_warranty_claim(
    motivo: str,
    orden_id: Optional[int] = None,
    venta_id: Optional[int] = None,
    user: str = "tecnico",
    org_id: int = 1,
) -> int:
    """Registra un reclamo de garantía."""
    conn = get_connection()
    with conn:
        cur = conn.execute(
            """
            INSERT INTO garantias_reclamos (organizacion_id, orden_id, venta_id, motivo, estado)
            VALUES (?, ?, ?, ?, 'PENDIENTE')
            """,
            (org_id, orden_id, venta_id, motivo.strip()),
        )
        claim_id = cur.lastrowid
    log_audit(user, "garantias_reclamos", str(claim_id), "NUEVO_RECLAMO", f"Reclamo de garantía registrado: {motivo[:40]}", org_id=org_id)
    return int(claim_id)


def resolve_warranty_claim(
    claim_id: int,
    nuevo_estado: str,
    resolucion_notas: str,
    crear_orden_cero: bool = False,
    user: str = "admin",
    org_id: int = 1,
) -> Optional[str]:
    """Resuelve un reclamo de garantía y opcionalmente crea una OT derivada con costo $0."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM garantias_reclamos WHERE id = ? AND organizacion_id = ?", (claim_id, org_id)).fetchone()
    if not row:
        return None

    nueva_ot_codigo = None

    with conn:
        if nuevo_estado == "ACEPTADO" and crear_orden_cero and row["orden_id"]:
            # Obtener datos de la orden original
            row_orig = conn.execute("SELECT * FROM ordenes_servicio WHERE id = ?", (row["orden_id"],)).fetchone()
            if row_orig:
                nueva_ot_codigo = get_next_code("OT", "ordenes_servicio", "ot_codigo", org_id=org_id)
                cur_ot = conn.execute(
                    """
                    INSERT INTO ordenes_servicio (
                        organizacion_id, ot_codigo, cliente_id, tecnico_id, vendedor_id,
                        tipo_dispositivo, marca, modelo, imei_serie, problema,
                        diagnostico_tecnico, estado, hash_seguimiento_publico,
                        costo_repuestos, mano_obra, total, monto_senado, saldo_pendiente,
                        garantia_dias, fecha_ingreso, fecha_ultimo_estado, es_retorno_garantia,
                        orden_garantia_origen_id
                    ) VALUES (
                        ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?,
                        ?, 'EN REPARACIÓN', ?,
                        0.0, 0.0, 0.0, 0.0, 0.0,
                        30, ?, ?, 1, ?
                    )
                    """,
                    (
                        org_id, nueva_ot_codigo, row_orig["cliente_id"], row_orig["tecnico_id"], row_orig["vendedor_id"],
                        row_orig["tipo_dispositivo"], row_orig["marca"], row_orig["modelo"], row_orig["imei_serie"],
                        f"[GARANTÍA] {row['motivo']}", f"Reparación por garantía de OT {row_orig['ot_codigo']}",
                        generate_public_tracking_hash(), str(date.today()), str(date.today()), row_orig["id"],
                    ),
                )
                conn.execute(
                    "UPDATE garantias_reclamos SET orden_derivada_id = ? WHERE id = ?",
                    (cur_ot.lastrowid, claim_id),
                )

        conn.execute(
            """
            UPDATE garantias_reclamos SET
                estado = ?, resolucion_notas = ?
            WHERE id = ?
            """,
            (nuevo_estado, resolucion_notas.strip(), claim_id),
        )

    log_audit(user, "garantias_reclamos", str(claim_id), "RESOLUCION_GARANTIA", f"Estado: {nuevo_estado}", org_id=org_id)
    return nueva_ot_codigo


# ==============================================================================
# LEADS & CRM
# ==============================================================================

def create_lead(nombre: str, telefono: str, email: str = "", mensaje: str = "", origen: str = "MANUAL", org_id: int = 1) -> int:
    """Registra una nueva oportunidad de venta o consulta."""
    conn = get_connection()
    with conn:
        cur = conn.execute(
            """
            INSERT INTO leads (organizacion_id, nombre, telefono, email, mensaje, origen, estado)
            VALUES (?, ?, ?, ?, ?, ?, 'NUEVO')
            """,
            (org_id, nombre.strip(), telefono.strip(), email.strip(), mensaje.strip(), origen),
        )
        return int(cur.lastrowid)


def update_lead_status(lead_id: int, nuevo_estado: str, org_id: int = 1) -> bool:
    """Actualiza el estado de un lead en el embudo comercial."""
    conn = get_connection()
    with conn:
        conn.execute(
            "UPDATE leads SET estado = ? WHERE id = ? AND organizacion_id = ?",
            (nuevo_estado, lead_id, org_id),
        )
    return True


# ==============================================================================
# REPORTES & ESTADO DE RESULTADOS (P&L STATEMENT)
# ==============================================================================

def load_pnl_statement(org_id: int = 1, start_date: str = "", end_date: str = "") -> Dict[str, Any]:
    """Calcula el Estado de Resultados (P&L) con CMV histórico y desglose de gastos."""
    init_db()
    conn = get_connection()

    date_filter_ot = ""
    date_filter_pos = ""
    date_filter_exp = ""
    params_ot = [org_id]
    params_pos = [org_id]
    params_exp = [org_id]

    if start_date and end_date:
        date_filter_ot = " AND fecha_ingreso BETWEEN ? AND ?"
        params_ot.extend([start_date, end_date])
        date_filter_pos = " AND date(creado_en) BETWEEN ? AND ?"
        params_pos.extend([start_date, end_date])
        date_filter_exp = " AND date(fecha) BETWEEN ? AND ?"
        params_exp.extend([start_date, end_date])

    # 1. Ingresos por Taller
    sql_ot = f"""
        SELECT 
            COALESCE(SUM(total), 0) as total_taller,
            COALESCE(SUM(mano_obra), 0) as mo_taller,
            COALESCE(SUM(costo_repuestos), 0) as rep_cobrado
        FROM ordenes_servicio
        WHERE organizacion_id = ? AND estado != 'CANCELADA' {date_filter_ot}
    """
    row_ot = conn.execute(sql_ot, params_ot).fetchone()
    ingresos_taller = float(row_ot["total_taller"]) if row_ot else 0.0

    # 2. CMV de Repuestos consumidos en Taller (costo_compra_snapshot)
    sql_cmv_ot = f"""
        SELECT COALESCE(SUM(r.cantidad * r.costo_compra_snapshot), 0) as cmv_repuestos
        FROM ordenes_repuestos r
        JOIN ordenes_servicio o ON r.orden_id = o.id
        WHERE r.organizacion_id = ? AND o.estado != 'CANCELADA' {date_filter_ot}
    """
    row_cmv_ot = conn.execute(sql_cmv_ot, params_ot).fetchone()
    cmv_taller = float(row_cmv_ot["cmv_repuestos"]) if row_cmv_ot else 0.0

    # 3. Ingresos por Ventas POS de Mostrador
    sql_pos = f"""
        SELECT COALESCE(SUM(total), 0) as total_pos
        FROM ventas
        WHERE organizacion_id = ? {date_filter_pos}
    """
    row_pos = conn.execute(sql_pos, params_pos).fetchone()
    ingresos_pos = float(row_pos["total_pos"]) if row_pos else 0.0

    # 4. CMV de Ventas Mostrador (costo_compra_snapshot)
    sql_cmv_pos = f"""
        SELECT COALESCE(SUM(i.cantidad * i.costo_compra_snapshot), 0) as cmv_pos
        FROM ventas_items i
        JOIN ventas v ON i.venta_id = v.id
        WHERE v.organizacion_id = ? {date_filter_pos}
    """
    row_cmv_pos = conn.execute(sql_cmv_pos, params_pos).fetchone()
    cmv_pos = float(row_cmv_pos["cmv_pos"]) if row_cmv_pos else 0.0

    # Ingresos Totales y CMV Total
    ingresos_totales = ingresos_taller + ingresos_pos
    cmv_total = cmv_taller + cmv_pos
    ganancia_bruta = ingresos_totales - cmv_total
    margen_bruto_pct = (ganancia_bruta / ingresos_totales * 100.0) if ingresos_totales > 0 else 0.0

    # 5. Gastos Operativos (Filtra solo categorías con afecta_resultado = 1)
    sql_exp = f"""
        SELECT 
            c.tipo as cat_tipo,
            c.nombre as cat_nombre,
            COALESCE(SUM(m.monto), 0) as total_gasto
        FROM caja_movimientos m
        JOIN categorias_gasto c ON m.categoria_id = c.id
        WHERE m.organizacion_id = ? AND m.tipo = 'EGRESO' AND c.afecta_resultado = 1 {date_filter_exp}
        GROUP BY c.tipo, c.nombre
    """
    rows_exp = conn.execute(sql_exp, params_exp).fetchall()
    gastos_fijos = 0.0
    gastos_variables = 0.0
    gastos_desglose = []

    for r in rows_exp:
        monto_g = float(r["total_gasto"])
        if r["cat_tipo"] == "FIJO":
            gastos_fijos += monto_g
        else:
            gastos_variables += monto_g
        gastos_desglose.append({"categoria": r["cat_nombre"], "tipo": r["cat_tipo"], "monto": monto_g})

    total_gastos_operativos = gastos_fijos + gastos_variables
    ganancia_neta = ganancia_bruta - total_gastos_operativos
    margen_neto_pct = (ganancia_neta / ingresos_totales * 100.0) if ingresos_totales > 0 else 0.0

    return {
        "ingresos_taller": ingresos_taller,
        "ingresos_pos": ingresos_pos,
        "ingresos_totales": ingresos_totales,
        "cmv_taller": cmv_taller,
        "cmv_pos": cmv_pos,
        "cmv_total": cmv_total,
        "ganancia_bruta": ganancia_bruta,
        "margen_bruto_pct": margen_bruto_pct,
        "gastos_fijos": gastos_fijos,
        "gastos_variables": gastos_variables,
        "total_gastos_operativos": total_gastos_operativos,
        "ganancia_neta": ganancia_neta,
        "margen_neto_pct": margen_neto_pct,
        "gastos_desglose": gastos_desglose,
    }


# ==============================================================================
# CARGA DE DATASETS PARA VISTAS (PANDAS DATAFRAMES)
# ==============================================================================

def load_orders_df(org_id: int = 1) -> pd.DataFrame:
    """Carga todas las órdenes de servicio unidas con datos de cliente y técnico."""
    init_db()
    conn = get_connection()
    sql = """
        SELECT 
            o.*,
            c.nombre as cliente_nombre,
            c.dni_cuit as cliente_dni,
            c.telefono as cliente_telefono,
            c.email as cliente_email,
            c.saldo_cuenta_corriente as cliente_saldo_cta,
            u_tec.nombre as tecnico_nombre,
            u_ven.nombre as vendedor_nombre
        FROM ordenes_servicio o
        LEFT JOIN clientes c ON o.cliente_id = c.id
        LEFT JOIN usuarios u_tec ON o.tecnico_id = u_tec.id
        LEFT JOIN usuarios u_ven ON o.vendedor_id = u_ven.id
        WHERE o.organizacion_id = ?
        ORDER BY o.fecha_ingreso DESC, o.id DESC
    """
    df = pd.read_sql_query(sql, conn, params=(org_id,))
    if df.empty:
        empty_cols = [
            "id", "organizacion_id", "ot_codigo", "cliente_id", "tecnico_id", "vendedor_id",
            "tipo_dispositivo", "marca", "modelo", "imei_serie", "patron_desbloqueo", "problema",
            "diagnostico_tecnico", "notas_microelectronica", "presupuesto_estimado", "fecha_entrega_estimada",
            "estado", "checklist_json", "hash_seguimiento_publico", "costo_repuestos", "mano_obra",
            "total", "monto_senado", "saldo_pendiente", "garantia_dias", "fecha_ingreso", "fecha_egreso",
            "fecha_ultimo_estado", "es_retorno_garantia", "orden_garantia_origen_id", "cliente_nombre",
            "cliente_dni", "cliente_telefono", "cliente_email", "cliente_saldo_cta", "tecnico_nombre",
            "vendedor_nombre", "fecha_ingreso_dt", "fecha_egreso_dt", "fecha_ultimo_dt", "margen_neto",
            "margen_pct", "dias_en_estado", "retiro_vencido", "falla_declarada",
        ]
        df_empty = pd.DataFrame(columns=empty_cols)
        df_empty["fecha_ingreso_dt"] = pd.to_datetime(df_empty["fecha_ingreso_dt"])
        df_empty["fecha_egreso_dt"] = pd.to_datetime(df_empty["fecha_egreso_dt"])
        df_empty["fecha_ultimo_dt"] = pd.to_datetime(df_empty["fecha_ultimo_dt"])
        return df_empty

    df["fecha_ingreso_dt"] = pd.to_datetime(df["fecha_ingreso"], errors="coerce")
    df["fecha_egreso_dt"] = pd.to_datetime(df["fecha_egreso"], errors="coerce")
    df["fecha_ultimo_dt"] = pd.to_datetime(df["fecha_ultimo_estado"], errors="coerce")
    df["falla_declarada"] = df["problema"]  # alias para compatibilidad
    df["margen_neto"] = df["total"] - df["costo_repuestos"]
    df["margen_pct"] = df.apply(lambda r: (r["margen_neto"] / r["total"] * 100.0) if r["total"] > 0 else 0.0, axis=1)

    hoy = pd.Timestamp(date.today())
    df["dias_en_estado"] = (hoy - df["fecha_ultimo_dt"]).dt.days.fillna(0).clip(lower=0)

    # Identificar retiros vencidos (equipos completados con fecha de entrega estimada pasada)
    def check_vencido(row):
        if row["estado"] in ["COMPLETADA", "Listo para Retiro"] and pd.notna(row["fecha_entrega_estimada"]) and row["fecha_entrega_estimada"]:
            try:
                promesa_dt = pd.to_datetime(row["fecha_entrega_estimada"])
                return promesa_dt < hoy
            except Exception:
                return False
        return False

    df["retiro_vencido"] = df.apply(check_vencido, axis=1)
    return df


def load_stock_df(org_id: int = 1) -> pd.DataFrame:
    """Carga catálogo de inventario con variantes y semáforo de reposición."""
    init_db()
    conn = get_connection()
    sql = """
        SELECT p.*, prov.razon_social as proveedor_nombre,
               padre.nombre as producto_padre_nombre
        FROM productos p
        LEFT JOIN proveedores prov ON p.proveedor_id = prov.id
        LEFT JOIN productos padre ON p.producto_padre_id = padre.id
        WHERE p.organizacion_id = ?
        ORDER BY (p.stock_actual <= p.stock_minimo) DESC, p.nombre ASC
    """
    df = pd.read_sql_query(sql, conn, params=(org_id,))
    if not df.empty:
        df["costo_compra"] = df["precio_compra"]  # alias
        df["valor_total_costo"] = df["stock_actual"] * df["precio_compra"]
        df["valor_total_venta"] = df["stock_actual"] * df["precio_venta"]
        df["alerta_reposicion"] = df["stock_actual"] <= df["stock_minimo"]
    return df


def purge_all_tables(keep_users: bool = False) -> None:
    """Purga y reinicia el ecosistema relacional del ERP a cero absoluto."""
    conn = get_connection()
    tables = [
        "ordenes_repuestos", "ordenes_fotos", "ordenes_servicio", "ventas_items",
        "ventas", "cotizaciones", "remitos", "notas_credito", "movimientos_stock",
        "caja_movimientos", "caja_sesiones", "garantias_reclamos", "leads",
        "gastos_recurrentes", "productos", "proveedores", "clientes",
        "auditoria_logs", "soporte_tickets", "taller_config", "organizaciones",
    ]
    legacy_tables = ["dispositivos_ordenes", "productos_stock", "ordenes_repuestos_usados", "ordenes"]

    with conn:
        for lt in legacy_tables:
            try:
                conn.execute(f"DROP VIEW IF EXISTS {lt};")
                conn.execute(f"DROP TABLE IF EXISTS {lt};")
            except Exception:
                pass

        for t in tables:
            try:
                conn.execute(f"DROP TABLE IF EXISTS {t};")
            except Exception:
                pass

        if not keep_users:
            conn.execute("DROP TABLE IF EXISTS usuarios;")

    init_db()
