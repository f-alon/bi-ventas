"""Módulo de conexión y acceso a base de datos (puente raíz modular)."""

from core.db import (
    bulk_insert_orders,
    get_connection,
    get_next_order_id,
    init_db,
    insert_order,
    load_orders_df,
    purge_database,
    reassign_order_technician,
    update_order_status,
)

__all__ = [
    "get_connection",
    "init_db",
    "get_next_order_id",
    "insert_order",
    "update_order_status",
    "reassign_order_technician",
    "bulk_insert_orders",
    "load_orders_df",
    "purge_database",
]

