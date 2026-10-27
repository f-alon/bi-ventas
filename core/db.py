"""Acceso a datos y persistencia SQLite para el taller de celulares."""

from datetime import datetime, date
from pathlib import Path
import sqlite3
from typing import Optional
import pandas as pd

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "repairs.db"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Crea las tablas necesarias si no existen y actualiza el esquema."""
    conn = get_connection()
    with conn:
        # Tabla de usuarios y autenticación
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                nombre_completo TEXT NOT NULL,
                rol TEXT NOT NULL CHECK(rol IN ('admin', 'tecnico')),
                activo INTEGER DEFAULT 1,
                creado_en TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_usuarios_user ON usuarios(username);")

        # Tabla de órdenes de trabajo
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ordenes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_orden TEXT UNIQUE NOT NULL,
                fecha_ingreso TEXT NOT NULL,
                fecha_egreso TEXT,
                fecha_ultimo_estado TEXT NOT NULL,
                cliente_nombre TEXT DEFAULT '',
                cliente_telefono TEXT DEFAULT '',
                imei TEXT DEFAULT '',
                marca TEXT NOT NULL,
                modelo TEXT NOT NULL,
                categoria_falla TEXT NOT NULL,
                diagnostico TEXT DEFAULT '',
                costo_repuesto REAL NOT NULL DEFAULT 0.0,
                valor_cobrado REAL NOT NULL DEFAULT 0.0,
                margen_neto REAL NOT NULL DEFAULT 0.0,
                estado TEXT NOT NULL,
                tecnico TEXT NOT NULL,
                garantia_dias INTEGER DEFAULT 30,
                es_retorno_garantia INTEGER DEFAULT 0,
                proveedor_repuesto TEXT DEFAULT '',
                guia_repuesto TEXT DEFAULT '',
                notas_tecnicas TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ordenes_fecha ON ordenes(fecha_ingreso);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ordenes_estado ON ordenes(estado);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ordenes_marca ON ordenes(marca);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ordenes_tecnico ON ordenes(tecnico);")

        # Comprobar columnas adicionales para instalaciones previas
        existing_cols = [r[1] for r in conn.execute("PRAGMA table_info(ordenes)").fetchall()]
        if "proveedor_repuesto" not in existing_cols:
            conn.execute("ALTER TABLE ordenes ADD COLUMN proveedor_repuesto TEXT DEFAULT '';")
        if "guia_repuesto" not in existing_cols:
            conn.execute("ALTER TABLE ordenes ADD COLUMN guia_repuesto TEXT DEFAULT '';")
        if "notas_tecnicas" not in existing_cols:
            conn.execute("ALTER TABLE ordenes ADD COLUMN notas_tecnicas TEXT DEFAULT '';")


def get_next_order_id() -> str:
    """Genera el próximo ID alfanumérico secuencial OT-XXXX."""
    conn = get_connection()
    row = conn.execute("SELECT id FROM ordenes ORDER BY id DESC LIMIT 1").fetchone()
    if row is None:
        return "OT-1001"
    next_num = 1001 + int(row["id"])
    return f"OT-{next_num}"


def insert_order(data: dict) -> bool:
    """Inserta o actualiza una orden individual en la base de datos."""
    conn = get_connection()
    costo = float(data.get("costo_repuesto", 0.0))
    cobrado = float(data.get("valor_cobrado", 0.0))
    margen = cobrado - costo

    fecha_ingreso = str(data["fecha_ingreso"])
    fecha_egreso = str(data["fecha_egreso"]) if data.get("fecha_egreso") else None
    fecha_ultimo_estado = str(data.get("fecha_ultimo_estado") or fecha_ingreso)

    with conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO ordenes (
                id_orden, fecha_ingreso, fecha_egreso, fecha_ultimo_estado,
                cliente_nombre, cliente_telefono, imei, marca, modelo,
                categoria_falla, diagnostico, costo_repuesto, valor_cobrado,
                margen_neto, estado, tecnico, garantia_dias, es_retorno_garantia,
                proveedor_repuesto, guia_repuesto, notas_tecnicas
            ) VALUES (
                ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?
            )
            """,
            (
                data["id_orden"],
                fecha_ingreso,
                fecha_egreso,
                fecha_ultimo_estado,
                data.get("cliente_nombre", ""),
                data.get("cliente_telefono", ""),
                data.get("imei", ""),
                data["marca"],
                data["modelo"],
                data["categoria_falla"],
                data.get("diagnostico", ""),
                costo,
                cobrado,
                margen,
                data["estado"],
                data["tecnico"],
                int(data.get("garantia_dias", 30)),
                int(data.get("es_retorno_garantia", 0)),
                data.get("proveedor_repuesto", ""),
                data.get("guia_repuesto", ""),
                data.get("notas_tecnicas", ""),
            ),
        )
    return True


def update_order_status(
    id_orden: str,
    nuevo_estado: str,
    notas_tecnicas: Optional[str] = None,
    proveedor_repuesto: Optional[str] = None,
    guia_repuesto: Optional[str] = None,
) -> bool:
    """Actualiza en un clic el estado y detalles operativos de una orden."""
    conn = get_connection()
    hoy_str = str(date.today())

    # Si se marca como Entregado o Listo para Entrega, fijar fecha de egreso si no existía
    query_parts = ["estado = ?", "fecha_ultimo_estado = ?"]
    params = [nuevo_estado, hoy_str]

    if nuevo_estado in ["Listo para Entrega", "Entregado"]:
        query_parts.append("fecha_egreso = COALESCE(fecha_egreso, ?)")
        params.append(hoy_str)

    if notas_tecnicas is not None:
        query_parts.append("notas_tecnicas = ?")
        params.append(notas_tecnicas)

    if proveedor_repuesto is not None:
        query_parts.append("proveedor_repuesto = ?")
        params.append(proveedor_repuesto)

    if guia_repuesto is not None:
        query_parts.append("guia_repuesto = ?")
        params.append(guia_repuesto)

    params.append(id_orden)
    set_clause = ", ".join(query_parts)

    with conn:
        conn.execute(f"UPDATE ordenes SET {set_clause} WHERE id_orden = ?", params)
    return True


def reassign_order_technician(id_orden: str, nuevo_tecnico: str) -> bool:
    """Reasigna o deriva una orden a otro técnico."""
    conn = get_connection()
    with conn:
        conn.execute(
            "UPDATE ordenes SET tecnico = ?, fecha_ultimo_estado = ? WHERE id_orden = ?",
            (nuevo_tecnico, str(date.today()), id_orden),
        )
    return True


def bulk_insert_orders(df: pd.DataFrame) -> int:
    """Inserta un conjunto masivo de órdenes validado."""
    conn = get_connection()
    inserted = 0
    with conn:
        for _, row in df.iterrows():
            costo = float(row.get("costo_repuesto", 0.0))
            cobrado = float(row.get("valor_cobrado", 0.0))
            margen = cobrado - costo
            f_ingreso = str(row["fecha_ingreso"])
            f_egreso = str(row["fecha_egreso"]) if pd.notna(row.get("fecha_egreso")) and str(row["fecha_egreso"]).strip() != "" else None
            f_ultimo = str(row.get("fecha_ultimo_estado") or f_ingreso)

            conn.execute(
                """
                INSERT OR REPLACE INTO ordenes (
                    id_orden, fecha_ingreso, fecha_egreso, fecha_ultimo_estado,
                    cliente_nombre, cliente_telefono, imei, marca, modelo,
                    categoria_falla, diagnostico, costo_repuesto, valor_cobrado,
                    margen_neto, estado, tecnico, garantia_dias, es_retorno_garantia,
                    proveedor_repuesto, guia_repuesto, notas_tecnicas
                ) VALUES (
                    ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?
                )
                """,
                (
                    str(row["id_orden"]),
                    f_ingreso,
                    f_egreso,
                    f_ultimo,
                    str(row.get("cliente_nombre", "") or ""),
                    str(row.get("cliente_telefono", "") or ""),
                    str(row.get("imei", "") or ""),
                    str(row["marca"]),
                    str(row["modelo"]),
                    str(row["categoria_falla"]),
                    str(row.get("diagnostico", "") or ""),
                    costo,
                    cobrado,
                    margen,
                    str(row["estado"]),
                    str(row["tecnico"]),
                    int(row.get("garantia_dias", 30) or 30),
                    int(row.get("es_retorno_garantia", 0) or 0),
                    str(row.get("proveedor_repuesto", "") or ""),
                    str(row.get("guia_repuesto", "") or ""),
                    str(row.get("notas_tecnicas", "") or ""),
                ),
            )
            inserted += 1
    return inserted


def load_orders_df() -> pd.DataFrame:
    """Carga todas las órdenes con columnas calculadas listas para análisis."""
    init_db()
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM ordenes ORDER BY fecha_ingreso DESC, id DESC", conn)
    if df.empty:
        # Retornar estructura de columnas vacías con tipos fecha válidos para evitar KeyError
        empty_cols = [
            "id", "id_orden", "fecha_ingreso", "fecha_egreso", "fecha_ultimo_estado",
            "cliente_nombre", "cliente_telefono", "imei", "marca", "modelo",
            "categoria_falla", "diagnostico", "costo_repuesto", "valor_cobrado",
            "margen_neto", "estado", "tecnico", "garantia_dias", "es_retorno_garantia",
            "proveedor_repuesto", "guia_repuesto", "notas_tecnicas", "created_at",
            "fecha_ingreso_dt", "fecha_egreso_dt", "fecha_ultimo_dt", "margen_pct",
            "dias_resolucion", "dias_en_estado",
        ]
        df_empty = pd.DataFrame(columns=empty_cols)
        df_empty["fecha_ingreso_dt"] = pd.to_datetime(df_empty["fecha_ingreso_dt"])
        df_empty["fecha_egreso_dt"] = pd.to_datetime(df_empty["fecha_egreso_dt"])
        df_empty["fecha_ultimo_dt"] = pd.to_datetime(df_empty["fecha_ultimo_dt"])
        return df_empty

    # Tipos de fechas
    df["fecha_ingreso_dt"] = pd.to_datetime(df["fecha_ingreso"], errors="coerce")
    df["fecha_egreso_dt"] = pd.to_datetime(df["fecha_egreso"], errors="coerce")
    df["fecha_ultimo_dt"] = pd.to_datetime(df["fecha_ultimo_estado"], errors="coerce")

    # Margen porcentual (evitando division por cero)
    df["margen_pct"] = df.apply(
        lambda r: (r["margen_neto"] / r["valor_cobrado"] * 100.0)
        if r["valor_cobrado"] > 0
        else 0.0,
        axis=1,
    )

    # Días de resolución (para órdenes terminadas con egreso)
    df["dias_resolucion"] = (df["fecha_egreso_dt"] - df["fecha_ingreso_dt"]).dt.days
    df["dias_resolucion"] = df["dias_resolucion"].apply(lambda d: max(d, 0) if pd.notna(d) else None)

    # Días sin cambio de estado
    hoy = pd.Timestamp(date.today())
    df["dias_en_estado"] = (hoy - df["fecha_ultimo_dt"]).dt.days.fillna(0).clip(lower=0)

    return df


def purge_database(keep_users: bool = True) -> None:
    """Purga o reinicia las tablas de la base de datos dejando las estadísticas en cero."""
    init_db()
    conn = get_connection()
    with conn:
        conn.execute("DELETE FROM ordenes;")
        conn.execute("DELETE FROM sqlite_sequence WHERE name='ordenes';")
        if not keep_users:
            conn.execute("DELETE FROM usuarios;")
            conn.execute("DELETE FROM sqlite_sequence WHERE name='usuarios';")
    conn.execute("VACUUM;")
