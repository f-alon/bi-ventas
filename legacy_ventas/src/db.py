"""DuckDB access layer for the sales warehouse."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "bi.duckdb"


class WarehouseMissingError(FileNotFoundError):
    pass


def warehouse_exists() -> bool:
    return DB_PATH.exists()


@st.cache_resource
def get_connection() -> duckdb.DuckDBPyConnection:
    if not warehouse_exists():
        raise WarehouseMissingError(str(DB_PATH))
    return duckdb.connect(str(DB_PATH), read_only=True)


@st.cache_data(ttl=300)
def load_filter_options() -> dict:
    con = get_connection()
    bounds = con.execute(
        "SELECT MIN(fecha)::DATE, MAX(fecha)::DATE FROM fact_ventas"
    ).fetchone()
    regions = [
        row[0]
        for row in con.execute(
            "SELECT region FROM dim_region ORDER BY region"
        ).fetchall()
    ]
    categories = [
        row[0]
        for row in con.execute(
            "SELECT DISTINCT categoria FROM dim_producto ORDER BY categoria"
        ).fetchall()
    ]
    return {
        "min_date": bounds[0],
        "max_date": bounds[1],
        "regions": regions,
        "categories": categories,
    }


@dataclass(frozen=True)
class Filters:
    start: date
    end: date
    regions: tuple[str, ...]
    categories: tuple[str, ...]

    @property
    def prev_end(self) -> date:
        return self.start - timedelta(days=1)

    @property
    def prev_start(self) -> date:
        span = (self.end - self.start).days
        return self.prev_end - timedelta(days=span)


def _placeholders(values: tuple[str, ...], prefix: str) -> tuple[str, dict]:
    params = {f"{prefix}_{i}": value for i, value in enumerate(values)}
    sql = ", ".join(f"${k}" for k in params)
    return sql, params


def fetch_facts(filters: Filters) -> pd.DataFrame:
    con = get_connection()
    region_sql, region_params = _placeholders(filters.regions, "r")
    cat_sql, cat_params = _placeholders(filters.categories, "c")
    params = {
        "start": filters.start,
        "end": filters.end,
        **region_params,
        **cat_params,
    }
    return con.execute(
        f"""
        SELECT
            f.id_venta,
            f.id_pedido,
            f.id_cliente,
            f.fecha,
            f.cantidad,
            f.ingreso,
            f.costo,
            f.ingreso - f.costo AS margen,
            p.producto,
            p.categoria,
            c.cliente,
            c.segmento,
            r.region
        FROM fact_ventas f
        JOIN dim_producto p ON p.id_producto = f.id_producto
        JOIN dim_cliente c ON c.id_cliente = f.id_cliente
        JOIN dim_region r ON r.id_region = f.id_region
        WHERE f.fecha BETWEEN $start AND $end
          AND r.region IN ({region_sql})
          AND p.categoria IN ({cat_sql})
        """,
        params,
    ).df()


def fetch_first_order_dates() -> pd.DataFrame:
    con = get_connection()
    return con.execute(
        """
        SELECT id_cliente, MIN(fecha)::DATE AS primera_compra
        FROM fact_ventas
        GROUP BY 1
        """
    ).df()
