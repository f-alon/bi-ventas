"""KPI and aggregation helpers for the sales dashboard."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.db import Filters, fetch_facts, fetch_first_order_dates


@dataclass
class KpiSet:
    ingreso: float
    unidades: int
    margen: float
    ticket_medio: float
    pedidos: int
    ingreso_delta: float | None
    unidades_delta: float | None
    margen_delta: float | None
    ticket_delta: float | None


def _safe_delta(current: float, previous: float) -> float | None:
    if previous == 0:
        return None if current == 0 else 1.0
    return (current - previous) / previous


def summarize(df: pd.DataFrame) -> dict:
    if df.empty:
        return {
            "ingreso": 0.0,
            "unidades": 0,
            "margen": 0.0,
            "pedidos": 0,
            "ticket_medio": 0.0,
        }
    ingreso = float(df["ingreso"].sum())
    pedidos = int(df["id_pedido"].nunique())
    return {
        "ingreso": ingreso,
        "unidades": int(df["cantidad"].sum()),
        "margen": float(df["margen"].sum()),
        "pedidos": pedidos,
        "ticket_medio": ingreso / pedidos if pedidos else 0.0,
    }


def compute_kpis(current: pd.DataFrame, previous: pd.DataFrame) -> KpiSet:
    now = summarize(current)
    prev = summarize(previous)
    return KpiSet(
        ingreso=now["ingreso"],
        unidades=now["unidades"],
        margen=now["margen"],
        ticket_medio=now["ticket_medio"],
        pedidos=now["pedidos"],
        ingreso_delta=_safe_delta(now["ingreso"], prev["ingreso"]),
        unidades_delta=_safe_delta(now["unidades"], prev["unidades"]),
        margen_delta=_safe_delta(now["margen"], prev["margen"]),
        ticket_delta=_safe_delta(now["ticket_medio"], prev["ticket_medio"]),
    )


def revenue_over_time(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["fecha", "ingreso", "margen"])
    out = (
        df.groupby("fecha", as_index=False)[["ingreso", "margen"]]
        .sum()
        .sort_values("fecha")
    )
    return out


def mix_by_region(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["region", "ingreso"])
    return (
        df.groupby("region", as_index=False)["ingreso"]
        .sum()
        .sort_values("ingreso", ascending=False)
    )


def top_products(df: pd.DataFrame, n: int = 8) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["producto", "ingreso", "unidades", "margen"])
    out = (
        df.groupby("producto", as_index=False)
        .agg(ingreso=("ingreso", "sum"), unidades=("cantidad", "sum"), margen=("margen", "sum"))
        .sort_values("ingreso", ascending=False)
        .head(n)
    )
    return out


def product_ranking(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            columns=["producto", "categoria", "ingreso", "unidades", "margen", "margen_pct"]
        )
    out = (
        df.groupby(["producto", "categoria"], as_index=False)
        .agg(ingreso=("ingreso", "sum"), unidades=("cantidad", "sum"), margen=("margen", "sum"))
    )
    out["margen_pct"] = out.apply(
        lambda row: row["margen"] / row["ingreso"] if row["ingreso"] else 0.0, axis=1
    )
    return out.sort_values("ingreso", ascending=False)


def margin_by_category(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["categoria", "ingreso", "margen", "margen_pct"])
    out = df.groupby("categoria", as_index=False).agg(
        ingreso=("ingreso", "sum"), margen=("margen", "sum")
    )
    out["margen_pct"] = out.apply(
        lambda row: row["margen"] / row["ingreso"] if row["ingreso"] else 0.0, axis=1
    )
    return out.sort_values("ingreso", ascending=False)


def customer_ranking(df: pd.DataFrame, first_orders: pd.DataFrame, filters: Filters) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            columns=["cliente", "segmento", "ingreso", "pedidos", "tipo"]
        )
    clients = (
        df.groupby(["cliente", "segmento", "id_cliente"], as_index=False)
        .agg(ingreso=("ingreso", "sum"), pedidos=("id_pedido", "nunique"))
    )
    merged = clients.merge(first_orders, on="id_cliente", how="left")
    def _tipo(value) -> str:
        if pd.isna(value):
            return "Recurrente"
        first = pd.Timestamp(value).date()
        if filters.start <= first <= filters.end:
            return "Nuevo"
        return "Recurrente"

    merged["tipo"] = merged["primera_compra"].apply(_tipo)
    return merged.sort_values("ingreso", ascending=False)


def customer_mix(ranking: pd.DataFrame) -> pd.DataFrame:
    if ranking.empty:
        return pd.DataFrame(columns=["tipo", "clientes", "ingreso"])
    return (
        ranking.groupby("tipo", as_index=False)
        .agg(clientes=("cliente", "nunique"), ingreso=("ingreso", "sum"))
        .sort_values("tipo")
    )


def load_period_frames(filters: Filters) -> tuple[pd.DataFrame, pd.DataFrame]:
    current = fetch_facts(filters)
    previous = fetch_facts(
        Filters(
            start=filters.prev_start,
            end=filters.prev_end,
            regions=filters.regions,
            categories=filters.categories,
        )
    )
    return current, previous
