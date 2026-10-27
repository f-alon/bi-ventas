from datetime import timedelta
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

st.set_page_config(
    page_title="BI Ventas",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from src.components import (
    bar_chart,
    chart_card,
    data_table,
    delta_type,
    donut_chart,
    empty_state,
    error_state,
    format_currency,
    format_date,
    format_number,
    format_pct,
    line_chart,
    margin_badge,
    metric_card,
    badge,
)
from src.db import Filters, WarehouseMissingError, load_filter_options, warehouse_exists
from src.metrics import (
    compute_kpis,
    customer_mix,
    customer_ranking,
    load_period_frames,
    margin_by_category,
    mix_by_region,
    product_ranking,
    revenue_over_time,
    top_products,
)
from src.db import fetch_first_order_dates
from src.theme import inject_css, init_theme, is_dark, toggle_theme

init_theme()
inject_css()


def render_header() -> None:
    head_left, head_right = st.columns([8, 1])
    with head_left:
        st.markdown(
            """
            <div class="brand">
                <span class="brand-name">BI Ventas</span>
                <span class="brand-sub">Panel de desempeño comercial · datos de ejemplo</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with head_right:
        theme_label = "Claro" if is_dark() else "Oscuro"
        st.button(
            theme_label,
            on_click=toggle_theme,
            width="stretch",
            help="Cambiar tema claro u oscuro",
        )


def render_filters(options: dict) -> Filters | None:
    default_end = options["max_date"]
    default_start = max(options["min_date"], default_end - timedelta(days=89))
    c1, c2, c3 = st.columns([1.2, 1.4, 1.4])
    with c1:
        date_range = st.date_input(
            "Período",
            value=(default_start, default_end),
            min_value=options["min_date"],
            max_value=options["max_date"],
        )
    with c2:
        regions = st.multiselect(
            "Región",
            options=options["regions"],
            default=options["regions"],
        )
    with c3:
        categories = st.multiselect(
            "Categoría",
            options=options["categories"],
            default=options["categories"],
        )

    if not isinstance(date_range, (list, tuple)) or len(date_range) != 2:
        empty_state("Elegí un rango de fechas con inicio y fin.")
        return None
    start, end = date_range
    if start > end:
        empty_state("La fecha de inicio no puede ser posterior a la de fin.")
        return None
    if not regions or not categories:
        empty_state("Seleccioná al menos una región y una categoría.")
        return None
    return Filters(
        start=start,
        end=end,
        regions=tuple(regions),
        categories=tuple(categories),
    )


def render_kpis(kpis) -> None:
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card(
            "Ingreso",
            format_currency(kpis.ingreso),
            format_pct(kpis.ingreso_delta),
            delta_type(kpis.ingreso_delta),
        )
    with c2:
        metric_card(
            "Unidades",
            format_number(kpis.unidades),
            format_pct(kpis.unidades_delta),
            delta_type(kpis.unidades_delta),
        )
    with c3:
        metric_card(
            "Margen",
            format_currency(kpis.margen),
            format_pct(kpis.margen_delta),
            delta_type(kpis.margen_delta),
        )
    with c4:
        metric_card(
            "Ticket medio",
            format_currency(kpis.ticket_medio),
            format_pct(kpis.ticket_delta),
            delta_type(kpis.ticket_delta),
        )


def tab_resumen(current, kpis) -> None:
    render_kpis(kpis)
    series = revenue_over_time(current)
    regions = mix_by_region(current)
    products = top_products(current)
    left, right = st.columns([1.6, 1])
    with left:
        if series.empty:
            empty_state("No hay ventas en el período seleccionado.")
        else:
            chart_card(
                "Ingreso en el tiempo",
                f"{format_date(series['fecha'].min())} — {format_date(series['fecha'].max())}",
                line_chart(series, "fecha", [("ingreso", "Ingreso"), ("margen", "Margen")]),
            )
    with right:
        if regions.empty:
            empty_state("Sin mix regional para estos filtros.")
        else:
            chart_card(
                "Mix por región",
                "Participación del ingreso",
                donut_chart(regions, "region", "ingreso"),
            )
    if products.empty:
        empty_state("Sin ranking de productos.")
    else:
        chart_card(
            "Top productos",
            "Por ingreso en el período",
            bar_chart(products.sort_values("ingreso"), "producto", "ingreso", "Ingreso", horizontal=True),
        )


def tab_productos(current) -> None:
    ranking = product_ranking(current)
    by_cat = margin_by_category(current)
    left, right = st.columns(2)
    with left:
        if ranking.empty:
            empty_state("No hay productos para mostrar.")
        else:
            chart_card(
                "Ranking de productos",
                "Ingreso acumulado",
                bar_chart(
                    ranking.head(12).sort_values("ingreso"),
                    "producto",
                    "ingreso",
                    "Ingreso",
                    horizontal=True,
                ),
            )
    with right:
        if by_cat.empty:
            empty_state("No hay margen por categoría.")
        else:
            chart_card(
                "Margen por categoría",
                "Ingreso total del grupo",
                bar_chart(by_cat, "categoria", "ingreso", "Ingreso"),
            )
    if ranking.empty:
        return
    rows = []
    for _, row in ranking.iterrows():
        rows.append(
            [
                row["producto"],
                badge(str(row["categoria"]), "blue"),
                format_currency(row["ingreso"]),
                format_number(row["unidades"]),
                format_currency(row["margen"]),
                margin_badge(float(row["margen_pct"])),
            ]
        )
    data_table(
        "Detalle de productos",
        "Margen verde ≥ 30%, ámbar ≥ 15%",
        [
            ("Producto", "text"),
            ("Categoría", "text"),
            ("Ingreso", "num"),
            ("Unidades", "num"),
            ("Margen", "num"),
            ("Margen %", "text"),
        ],
        rows,
    )


def tab_clientes(current, filters) -> None:
    first_orders = fetch_first_order_dates()
    ranking = customer_ranking(current, first_orders, filters)
    mix = customer_mix(ranking)
    left, right = st.columns([1, 1.4])
    with left:
        if mix.empty:
            empty_state("No hay clientes en el período.")
        else:
            chart_card(
                "Nuevos vs. recurrentes",
                "Ingreso según tipo de cliente",
                donut_chart(mix, "tipo", "ingreso"),
            )
    with right:
        if ranking.empty:
            empty_state("Sin ranking de clientes.")
        else:
            chart_card(
                "Top clientes",
                "Por ingreso",
                bar_chart(
                    ranking.head(10).sort_values("ingreso"),
                    "cliente",
                    "ingreso",
                    "Ingreso",
                    horizontal=True,
                ),
            )
    if ranking.empty:
        return
    rows = []
    for _, row in ranking.head(25).iterrows():
        kind = "green" if row["tipo"] == "Nuevo" else "blue"
        rows.append(
            [
                row["cliente"],
                badge(str(row["segmento"]), "amber"),
                format_currency(row["ingreso"]),
                format_number(row["pedidos"]),
                badge(str(row["tipo"]), kind),
            ]
        )
    data_table(
        "Detalle de clientes",
        "Nuevo: primera compra dentro del período filtrado",
        [
            ("Cliente", "text"),
            ("Segmento", "text"),
            ("Ingreso", "num"),
            ("Pedidos", "num"),
            ("Tipo", "text"),
        ],
        rows,
    )


def main() -> None:
    render_header()
    if not warehouse_exists():
        error_state(
            "No se encontró data/bi.duckdb. Ejecutá: python scripts/seed_data.py"
        )
        return

    try:
        options = load_filter_options()
    except WarehouseMissingError:
        error_state("El almacén no está disponible. Volvé a sembrar los datos de ejemplo.")
        return
    except Exception as exc:
        error_state(f"No se pudieron leer los filtros: {exc}")
        return

    filters = render_filters(options)
    if filters is None:
        return

    with st.spinner("Consultando el almacén…"):
        try:
            current, previous = load_period_frames(filters)
            kpis = compute_kpis(current, previous)
        except Exception as exc:
            error_state(f"Falló la consulta: {exc}")
            return

    period_label = f"{format_date(filters.start)} — {format_date(filters.end)}"
    st.caption(f"Comparado contra el período previo de igual duración · {period_label}")

    resumen, productos, clientes = st.tabs(["Resumen", "Productos", "Clientes"])
    with resumen:
        tab_resumen(current, kpis)
    with productos:
        tab_productos(current)
    with clientes:
        tab_clientes(current, filters)


main()
