"""Theme toggle and CSS design system for the Streamlit dashboard."""

from __future__ import annotations

import streamlit as st

FONT_LINKS = (
    "https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;"
    "0,9..40,600;0,9..40,700;1,9..40,400&family=JetBrains+Mono:wght@400;500&display=swap"
)


def init_theme() -> None:
    if "theme" not in st.session_state:
        st.session_state.theme = "light"


def toggle_theme() -> None:
    st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"


def is_dark() -> bool:
    return st.session_state.get("theme", "light") == "dark"


def plot_layout(dark: bool | None = None) -> dict:
    dark = is_dark() if dark is None else dark
    grid = "rgba(255,255,255,0.04)" if dark else "rgba(0,0,0,0.04)"
    font_color = "#a1a1aa" if dark else "#71717a"
    return dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif", color=font_color, size=11),
        margin=dict(l=0, r=0, t=8, b=0),
        xaxis=dict(
            gridcolor=grid,
            zerolinecolor=grid,
            tickfont=dict(size=10, color="#71717a"),
        ),
        yaxis=dict(
            gridcolor=grid,
            zerolinecolor=grid,
            tickfont=dict(size=10, color="#71717a"),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            bgcolor="rgba(0,0,0,0)",
        ),
        hoverlabel=dict(font=dict(family="DM Sans, sans-serif", size=12)),
        colorway=["#2563eb", "#22c55e", "#f59e0b", "#a1a1aa", "#ef4444", "#7c3aed"],
    )


def inject_css() -> None:
    dark = is_dark()
    bg = "#09090b" if dark else "#ffffff"
    bg_subtle = "#0c0c0f" if dark else "#f9fafb"
    card = "#0c0c0f" if dark else "#ffffff"
    card_hover = "#131316" if dark else "#f4f4f5"
    border = "#1e1e24" if dark else "#e4e4e7"
    border_subtle = "#16161a" if dark else "#f0f0f2"
    text = "#fafafa" if dark else "#09090b"
    text_dim = "#52525b" if dark else "#a1a1aa"
    green = "#22c55e" if dark else "#16a34a"
    green_muted = "rgba(34,197,94,0.12)" if dark else "rgba(22,163,74,0.08)"
    red = "#ef4444" if dark else "#dc2626"
    red_muted = "rgba(239,68,68,0.12)" if dark else "rgba(220,38,54,0.08)"
    amber = "#f59e0b" if dark else "#d97706"
    amber_muted = "rgba(245,158,11,0.12)" if dark else "rgba(217,119,6,0.08)"
    shadow = "none" if dark else "0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.03)"

    st.markdown(
        f"""
        <link rel="stylesheet" href="{FONT_LINKS}">
        <style>
        :root {{
            --bg: {bg};
            --bg-subtle: {bg_subtle};
            --card: {card};
            --card-hover: {card_hover};
            --border: {border};
            --border-subtle: {border_subtle};
            --text: {text};
            --text-muted: #71717a;
            --text-dim: {text_dim};
            --accent: #2563eb;
            --accent-muted: #1d4ed8;
            --green: {green};
            --green-muted: {green_muted};
            --red: {red};
            --red-muted: {red_muted};
            --amber: {amber};
            --amber-muted: {amber_muted};
            --shadow: {shadow};
            --radius: 10px;
        }}
        header[data-testid="stHeader"], #MainMenu, footer, [data-testid="stToolbar"],
        [data-testid="stDecoration"], [data-testid="stStatusWidget"], .stDeployButton,
        div[data-testid="stSidebarCollapsedControl"] {{
            display: none !important;
        }}
        html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"], .main,
        .block-container, section[data-testid="stMain"] {{
            background-color: var(--bg) !important;
            color: var(--text) !important;
            font-family: 'DM Sans', -apple-system, sans-serif !important;
        }}
        .block-container {{
            padding: 2rem 2.5rem 3rem !important;
            max-width: 1360px !important;
        }}
        button[data-baseweb="tab"] {{
            background: transparent !important;
            color: var(--text-muted) !important;
            font-size: 0.835rem !important;
            font-weight: 500 !important;
            padding: 0.55rem 1rem !important;
            border: 1px solid transparent !important;
            border-radius: 7px !important;
        }}
        button[data-baseweb="tab"][aria-selected="true"] {{
            color: var(--text) !important;
            background: var(--card) !important;
            border-color: var(--border) !important;
        }}
        [data-baseweb="tab-highlight"], [data-baseweb="tab-border"] {{
            display: none !important;
        }}
        [data-baseweb="tab-list"] {{
            gap: 4px !important;
            background: var(--bg-subtle) !important;
            border: 1px solid var(--border) !important;
            border-radius: 10px !important;
            padding: 3px;
        }}
        .metric-card {{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 1.25rem 1.4rem;
            box-shadow: var(--shadow);
            transition: background 160ms ease, border-color 160ms ease;
        }}
        .metric-card:hover {{ background: var(--card-hover); }}
        .metric-label {{ font-size: 0.78rem; color: var(--text-muted); font-weight: 500; }}
        .metric-value {{
            font-size: 1.75rem;
            font-weight: 700;
            color: var(--text);
            letter-spacing: -0.03em;
            font-family: 'JetBrains Mono', ui-monospace, monospace;
        }}
        .metric-delta {{
            font-size: 0.75rem;
            font-weight: 500;
            margin-top: 0.4rem;
            padding: 2px 8px;
            border-radius: 6px;
            display: inline-flex;
            align-items: center;
            gap: 3px;
        }}
        .delta-up {{ color: var(--green); background: var(--green-muted); }}
        .delta-down {{ color: var(--red); background: var(--red-muted); }}
        .delta-warn {{ color: var(--amber); background: var(--amber-muted); }}
        .chart-wrap {{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 1.2rem 1.2rem 0.6rem;
            box-shadow: var(--shadow);
            margin-bottom: 0.25rem;
        }}
        .chart-title {{ font-size: 0.82rem; font-weight: 600; color: var(--text); }}
        .chart-subtitle {{ font-size: 0.72rem; color: var(--text-dim); margin-bottom: 0.8rem; }}
        .table-wrap {{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 1.2rem;
            box-shadow: var(--shadow);
            overflow-x: auto;
            position: relative;
            z-index: 1;
        }}
        .data-table {{
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            font-size: 0.8rem;
        }}
        .data-table th {{
            text-align: left;
            padding: 0.6rem 0.8rem;
            color: var(--text-muted);
            font-weight: 500;
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            border-bottom: 1px solid var(--border);
            position: sticky;
            top: 0;
            background: var(--card);
            z-index: 20;
        }}
        .data-table td {{
            padding: 0.65rem 0.8rem;
            color: var(--text);
            border-bottom: 1px solid var(--border-subtle);
        }}
        .data-table tr:last-child td {{ border-bottom: none; }}
        .data-table td.num {{
            font-family: 'JetBrains Mono', ui-monospace, monospace;
            text-align: right;
        }}
        .data-table th.num {{ text-align: right; }}
        .badge {{
            display: inline-block;
            padding: 2px 9px;
            border-radius: 6px;
            font-size: 0.72rem;
            font-weight: 500;
        }}
        .badge-green {{ color: var(--green); background: var(--green-muted); }}
        .badge-red {{ color: var(--red); background: var(--red-muted); }}
        .badge-amber {{ color: var(--amber); background: var(--amber-muted); }}
        .badge-blue {{ color: var(--accent); background: rgba(37,99,235,0.1); }}
        .brand {{ display: flex; flex-direction: column; gap: 0.15rem; }}
        .brand-name {{
            font-size: 1.15rem;
            font-weight: 700;
            letter-spacing: -0.03em;
            color: var(--text);
        }}
        .brand-sub {{ font-size: 0.78rem; color: var(--text-muted); }}
        .empty-state, .error-state {{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 2rem 1.5rem;
            text-align: center;
            color: var(--text-muted);
            box-shadow: var(--shadow);
        }}
        .error-state {{ color: var(--red); }}
        [data-testid="stHorizontalBlock"] {{ gap: 1.25rem !important; }}
        [data-testid="stVerticalBlock"] > div:has(> [data-testid="stHorizontalBlock"]) {{
            margin-bottom: 0.5rem !important;
        }}
        .stButton > button {{
            border: 1px solid var(--border) !important;
            background: var(--card) !important;
            color: var(--text) !important;
            border-radius: 8px !important;
            transition: background 160ms ease, border-color 160ms ease;
        }}
        .stButton > button:hover {{ background: var(--card-hover) !important; }}
        .stButton > button:disabled {{ opacity: 0.55; }}
        [data-testid="stSelectbox"] label, [data-testid="stMultiSelect"] label,
        [data-testid="stDateInput"] label {{
            color: var(--text-muted) !important;
            font-size: 0.78rem !important;
        }}
        @media (max-width: 900px) {{
            .block-container {{ padding: 1.25rem 1rem 2rem !important; }}
            .metric-value {{ font-size: 1.35rem; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
