"""Generate sample sales CSVs and load them into DuckDB (idempotent)."""

from __future__ import annotations

import random
import sys
from datetime import date, timedelta
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
DB_PATH = ROOT / "data" / "bi.duckdb"

REGIONS = [
    (1, "AMBA"),
    (2, "Córdoba"),
    (3, "Litoral"),
    (4, "Cuyo"),
    (5, "Patagonia"),
    (6, "NOA"),
    (7, "NEA"),
]

PRODUCTS = [
    (1, "Auriculares Nova", "Electrónica", 28900, 14200),
    (2, "Teclado mecánico Pulse", "Electrónica", 42100, 21000),
    (3, "Monitor 27 4K", "Electrónica", 189000, 112000),
    (4, "Notebook 14 Air", "Electrónica", 890000, 610000),
    (5, "Mouse inalámbrico", "Electrónica", 18900, 7200),
    (6, "Lámpara LED escritorio", "Hogar", 24500, 9800),
    (7, "Silla ergonómica", "Hogar", 178000, 89000),
    (8, "Juego de sábanas", "Hogar", 39000, 16000),
    (9, "Cafetera espresso", "Hogar", 95000, 48000),
    (10, "Organizador cocina", "Hogar", 15600, 6100),
    (11, "Campera urbana", "Indumentaria", 72000, 31000),
    (12, "Zapatillas running", "Indumentaria", 68000, 29000),
    (13, "Remera básica pack x3", "Indumentaria", 21900, 8400),
    (14, "Mochila diaria", "Indumentaria", 34500, 14000),
    (15, "Café de especialidad 1kg", "Alimentos", 18900, 9200),
    (16, "Aceite de oliva 500ml", "Alimentos", 9800, 4100),
    (17, "Mix de frutos secos", "Alimentos", 7200, 3100),
    (18, "Barra proteica x12", "Alimentos", 12500, 5400),
    (19, "Kit yoga", "Deportes", 28900, 12100),
    (20, "Mancuernas 5kg par", "Deportes", 35600, 14800),
    (21, "Pelota fútbol", "Deportes", 18900, 7600),
    (22, "Bicicleta urbana", "Deportes", 245000, 148000),
    (23, "Botella térmica", "Deportes", 14200, 5100),
    (24, "Cinta de correr plegable", "Deportes", 410000, 255000),
]

FIRST_NAMES = [
    "Ana", "Bruno", "Camila", "Diego", "Elena", "Facundo", "Guillermina",
    "Hugo", "Inés", "Julián", "Karina", "Lautaro", "Marina", "Nicolás",
    "Olivia", "Pablo", "Rocío", "Santiago", "Valentina", "Tomás",
]
LAST_NAMES = [
    "García", "Fernández", "López", "Martínez", "Rodríguez", "Pérez",
    "Gómez", "Sánchez", "Álvarez", "Romero", "Suárez", "Torres",
    "Flores", "Benítez", "Acosta", "Castro", "Morales", "Silva",
]

START = date(2024, 1, 1)
END = date(2025, 12, 31)


def month_name(month: int) -> str:
    names = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    ]
    return names[month - 1]


def weekday_name(weekday: int) -> str:
    names = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    return names[weekday]


def build_dim_fecha() -> pd.DataFrame:
    rows = []
    current = START
    while current <= END:
        rows.append(
            {
                "id_fecha": int(current.strftime("%Y%m%d")),
                "fecha": current,
                "anio": current.year,
                "mes": current.month,
                "nombre_mes": month_name(current.month),
                "trimestre": (current.month - 1) // 3 + 1,
                "semana": int(current.strftime("%V")),
                "dia_semana": weekday_name(current.weekday()),
            }
        )
        current += timedelta(days=1)
    return pd.DataFrame(rows)


def build_dim_producto() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "id_producto": pid,
                "producto": name,
                "categoria": category,
                "precio_lista": price,
                "costo_unitario": cost,
            }
            for pid, name, category, price, cost in PRODUCTS
        ]
    )


def build_dim_region() -> pd.DataFrame:
    return pd.DataFrame(
        [{"id_region": rid, "region": name} for rid, name in REGIONS]
    )


def build_dim_cliente(rng: random.Random) -> pd.DataFrame:
    rows = []
    for i in range(1, 121):
        rows.append(
            {
                "id_cliente": i,
                "cliente": f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
                "segmento": rng.choices(
                    ["Consumo", "PyME", "Empresa"], weights=[0.62, 0.28, 0.10]
                )[0],
            }
        )
    return pd.DataFrame(rows)


def seasonal_multiplier(d: date) -> float:
    # Higher demand in May (Hot Sale-ish), November (Buen Fin / Cyber), December.
    month_boost = {5: 1.18, 11: 1.35, 12: 1.42, 1: 0.82, 2: 0.88}
    weekend = 1.12 if d.weekday() >= 5 else 1.0
    return month_boost.get(d.month, 1.0) * weekend


def build_fact_ventas(rng: random.Random) -> pd.DataFrame:
    rows = []
    sale_id = 1
    pedido_id = 1
    current = START
    while current <= END:
        base = 6 + int(4 * seasonal_multiplier(current))
        n_orders = max(3, int(rng.gauss(base, 2)))
        for _ in range(n_orders):
            region_id = rng.choices(
                [r[0] for r in REGIONS],
                weights=[0.38, 0.16, 0.12, 0.10, 0.08, 0.08, 0.08],
            )[0]
            customer_id = rng.randint(1, 120)
            n_lines = rng.choices([1, 2, 3, 4], weights=[0.45, 0.32, 0.16, 0.07])[0]
            products = rng.sample(PRODUCTS, k=n_lines)
            for pid, _name, _cat, price, cost in products:
                qty = rng.choices([1, 2, 3, 4], weights=[0.62, 0.24, 0.10, 0.04])[0]
                discount = rng.choice([0, 0, 0, 0.05, 0.08, 0.12])
                unit_price = round(price * (1 - discount), 2)
                ingreso = round(unit_price * qty, 2)
                costo = round(cost * qty, 2)
                rows.append(
                    {
                        "id_venta": sale_id,
                        "id_pedido": pedido_id,
                        "id_fecha": int(current.strftime("%Y%m%d")),
                        "fecha": current,
                        "id_producto": pid,
                        "id_cliente": customer_id,
                        "id_region": region_id,
                        "cantidad": qty,
                        "ingreso": ingreso,
                        "costo": costo,
                    }
                )
                sale_id += 1
            pedido_id += 1
        current += timedelta(days=1)
    return pd.DataFrame(rows)


def write_csvs(frames: dict[str, pd.DataFrame]) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for name, frame in frames.items():
        path = RAW_DIR / f"{name}.csv"
        frame.to_csv(path, index=False)
        print(f"Wrote {path} ({len(frame):,} rows)")


def load_duckdb(frames: dict[str, pd.DataFrame]) -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH))
    try:
        for name, frame in frames.items():
            con.register(f"df_{name}", frame)
            con.execute(f"CREATE OR REPLACE TABLE {name} AS SELECT * FROM df_{name}")
            con.unregister(f"df_{name}")
        counts = con.execute(
            """
            SELECT 'dim_fecha' AS tabla, COUNT(*) FROM dim_fecha
            UNION ALL SELECT 'dim_producto', COUNT(*) FROM dim_producto
            UNION ALL SELECT 'dim_cliente', COUNT(*) FROM dim_cliente
            UNION ALL SELECT 'dim_region', COUNT(*) FROM dim_region
            UNION ALL SELECT 'fact_ventas', COUNT(*) FROM fact_ventas
            """
        ).fetchall()
        for tabla, n in counts:
            print(f"Loaded {tabla}: {n:,} rows")
    finally:
        con.close()


def main() -> int:
    rng = random.Random(42)
    frames = {
        "dim_fecha": build_dim_fecha(),
        "dim_producto": build_dim_producto(),
        "dim_cliente": build_dim_cliente(rng),
        "dim_region": build_dim_region(),
        "fact_ventas": build_fact_ventas(rng),
    }
    write_csvs(frames)
    load_duckdb(frames)
    print(f"Warehouse ready: {DB_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
