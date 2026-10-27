# BI Ventas

Dashboard de ventas (MVP) con almacén local DuckDB y datos de ejemplo.

## Requisitos

- Python 3.11+

## Arranque

En PowerShell, desde la carpeta del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python scripts\seed_data.py
.\.venv\Scripts\streamlit run app.py
```

El seed es idempotente: se puede volver a ejecutar sin duplicar hechos.

## Qué incluye

- Esquema estrella: `dim_fecha`, `dim_producto`, `dim_cliente`, `dim_region`, `fact_ventas`
- Filtros de período, región y categoría
- KPIs con variación vs. el período anterior
- Pestañas Resumen, Productos y Clientes
- Tema claro / oscuro

## Datos

Los CSV se generan en `data/raw/` y el almacén queda en `data/bi.duckdb` (no versionado). Para conectar datos reales más adelante, reemplazá el seed o adjuntá otra base al mismo esquema.
