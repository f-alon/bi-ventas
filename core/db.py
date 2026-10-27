"""Acceso a datos y persistencia SQLite para el taller de celulares."""

from datetime import datetime, date
from pathlib import Path
import sqlite3
import pandas as pd

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "repairs.db"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Crea las tablas necesarias si no existen."""
    conn = get_connection()
    with conn:
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
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ordenes_fecha ON ordenes(fecha_ingreso);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ordenes_estado ON ordenes(estado);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ordenes_marca ON ordenes(marca);")


def get_next_order_id() -> str:
    """Genera el próximo ID alfanumérico secuencial OT-XXXX."""
    conn = get_connection()
    row = conn.execute("SELECT id FROM ordenes ORDER BY id DESC LIMIT 1").fetchone()
    if row is None:
        return "OT-1001"
    next_num = 1001 + int(row["id"])
    return f"OT-{next_num}"


def insert_order(data: dict) -> bool:
    """Inserta una orden individual en la base de datos."""
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
            INSERT INTO ordenes (
                id_orden, fecha_ingreso, fecha_egreso, fecha_ultimo_estado,
                cliente_nombre, cliente_telefono, imei, marca, modelo,
                categoria_falla, diagnostico, costo_repuesto, valor_cobrado,
                margen_neto, estado, tecnico, garantia_dias, es_retorno_garantia
            ) VALUES (
                ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?, ?
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
            ),
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
                    margen_neto, estado, tecnico, garantia_dias, es_retorno_garantia
                ) VALUES (
                    ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?, ?
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
        return df

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

