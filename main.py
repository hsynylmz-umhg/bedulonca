# main.py
import json
import io
import os
import time
import random
from pathlib import Path
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components
import requests
from dotenv import load_dotenv

# ── MUTLAK YOL İLE .env YÜKLEME ──────────────────────────────────────
_BASE_DIR = Path(__file__).parent.resolve()
load_dotenv(dotenv_path=_BASE_DIR / ".env", override=True)

from agent_graph import build_graph
from state import AgentState
from agents.cost_agent import _fifo_cost

DATA_PATH = _BASE_DIR / "data" / "mock_data.json"

# ── Sayfa Yapılandırması ──────────────────────────────────────────────
st.set_page_config(
    page_title="Bedülonca | Dashboard",
    page_icon="B",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS (Light Finance Theme) ─────────────────────────────────
st.markdown("""
<style>
/* ── Google Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ── Streamlit sistem UI gizleme ── */
#MainMenu {visibility: hidden;}
header    {visibility: hidden;}
footer    {visibility: hidden;}

/* ── Temel Uygulama ── */
html, body, [class*="st-"], [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}
.stApp {
    background-color: #F8FAFC !important;
}
.block-container {
    padding: 1.5rem 2.5rem 3rem 2.5rem !important;
    background-color: #F8FAFC !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #FFFFFF !important;
    border-right: 1px solid #E2E8F0 !important;
}
[data-testid="stSidebar"] * {
    color: #0F172A !important;
    font-family: 'Inter', sans-serif !important;
}
[data-testid="stSidebar"] .stMarkdown p {
    color: #64748B !important;
    font-size: 12px !important;
}
[data-testid="stSidebarNav"] { display: none; }

/* ── Global Header ── */
.global-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 12px 24px;
    margin-bottom: 24px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.brand-area  { display: flex; align-items: center; gap: 14px; }
.brand-title { font-size: 22px; font-weight: 800; color: #0F172A; letter-spacing: -0.5px; }
.brand-sub   {
    font-size: 10px; color: #2563EB; letter-spacing: 1.5px;
    text-transform: uppercase; font-weight: 600;
}
.kur-badge {
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 6px 16px;
    text-align: right;
}
.kur-label {
    font-size: 9px; color: #94A3B8; text-transform: uppercase;
    letter-spacing: 1.5px; font-weight: 600;
}
.kur-value { font-size: 16px; font-weight: 700; color: #2563EB; }

/* ── Section Label ── */
.section-label {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: #64748B;
    margin-bottom: 10px;
    margin-top: 8px;
    border-bottom: 1px solid #E2E8F0;
    padding-bottom: 8px;
}
.divider {
    border: none;
    border-top: 1px solid #E2E8F0;
    margin: 20px 0;
}

/* ── Metrik Kutular ── */
[data-testid="stMetric"] {
    background: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 12px !important;
    padding: 16px 20px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
    height: 100% !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: space-between !important;
}
[data-testid="stMetricLabel"] {
    color: #64748B !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.8px !important;
}
[data-testid="stMetricValue"] {
    color: #0F172A !important;
    font-size: 22px !important;
    font-weight: 700 !important;
}
[data-testid="stMetricDelta"] {
    display: flex !important;
    flex-direction: row !important;
    align-items: center !important;
    white-space: nowrap !important;
    font-size: 11px !important;
}

/* ── Aksiyon Kartları ── */
.action-card      { border-radius: 10px; padding: 14px 16px; margin-bottom: 10px; }
.action-critical  { background: rgba(239,68,68,0.06);  border: 1px solid rgba(239,68,68,0.25); }
.action-bundle    { background: rgba(34,197,94,0.06);  border: 1px solid rgba(34,197,94,0.25); }
.action-markdown  { background: rgba(234,179,8,0.06);  border: 1px solid rgba(234,179,8,0.25); }
.action-gift      { background: rgba(59,130,246,0.06); border: 1px solid rgba(59,130,246,0.25); }
.action-liquidate { background: rgba(168,85,247,0.06); border: 1px solid rgba(168,85,247,0.25); }
.action-hold      { background: rgba(100,116,139,0.06);border: 1px solid rgba(100,116,139,0.20); }
.action-title     { font-size: 13px; font-weight: 700; color: #0F172A; margin-bottom: 4px; }
.action-detail    { font-size: 12px; color: #475569; margin-bottom: 5px; }
.action-reason    { font-size: 11px; color: #94A3B8; font-style: italic; }
.price-arrow      { color: #EF4444; font-weight: 700; }
.price-up         { color: #EF4444; }
.price-hold       { color: #94A3B8; }

/* ── DataFrame ── */
[data-testid="stDataFrame"] {
    border: 1px solid #E2E8F0 !important;
    border-radius: 12px !important;
    overflow: hidden !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
}
[data-testid="stDataFrame"] a {
    color: #2563EB !important;
    text-decoration: none !important;
    font-weight: 600 !important;
}
[data-testid="stDataFrame"] a:hover {
    color: #1D4ED8 !important;
    text-decoration: underline !important;
}

/* ── Status kutusu ── */
[data-testid="stStatus"] {
    background: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 12px !important;
}

/* ── Primary Button ── */
div[data-testid="stButton"] > button[kind="primary"] {
    background: #2563EB !important;
    color: #FFFFFF !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 8px 0 !important;
    width: 100% !important;
    font-size: 13px !important;
    transition: opacity .2s !important;
    font-family: 'Inter', sans-serif !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover { opacity: 0.88 !important; }

/* ── Secondary Button ── */
div[data-testid="stButton"] > button[kind="secondary"] {
    background: #F8FAFC !important;
    color: #0F172A !important;
    font-weight: 600 !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 8px !important;
    font-size: 12px !important;
    font-family: 'Inter', sans-serif !important;
}
div[data-testid="stButton"] > button[kind="secondary"]:hover {
    background: #EFF6FF !important;
    border-color: #2563EB !important;
    color: #2563EB !important;
}

/* ── Tabs ── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid #E2E8F0 !important;
    gap: 4px !important;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    background: transparent !important;
    color: #64748B !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    border-radius: 6px 6px 0 0 !important;
    padding: 7px 14px !important;
    font-family: 'Inter', sans-serif !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
    background: #EFF6FF !important;
    color: #2563EB !important;
    border-bottom: 2px solid #2563EB !important;
}

/* ── Chart title ── */
.chart-title {
    font-size: 11px;
    font-weight: 700;
    color: #64748B;
    letter-spacing: 1px;
    text-transform: uppercase;
    margin-bottom: 6px;
    margin-top: 14px;
}

/* ── Popover 3-nokta butonu ── */
[data-testid="stPopover"] > div > button {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: #0F172A !important;
    font-size: 22px !important;
    font-weight: 700 !important;
    padding: 2px 8px !important;
    line-height: 1 !important;
}
[data-testid="stPopover"] > div > button:hover {
    background: #F1F5F9 !important;
    border-radius: 6px !important;
}
/* Popover panel */
[data-testid="stPopoverBody"] {
    background: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 12px !important;
    box-shadow: 0 8px 24px rgba(0,0,0,0.10) !important;
    min-width: 280px !important;
}

/* ── Kritik stok link ── */
.critical-link a {
    color: #EF4444 !important;
    font-weight: 600 !important;
    text-decoration: underline !important;
    font-size: 12px !important;
}

/* ── Carousel kontrol butonu ── */
.carousel-btn button {
    background: #F1F5F9 !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 8px !important;
    color: #0F172A !important;
    font-size: 18px !important;
    padding: 4px 12px !important;
}
.carousel-btn button:hover {
    background: #EFF6FF !important;
    border-color: #2563EB !important;
    color: #2563EB !important;
}

/* ── Genel input/select ── */
[data-testid="stSelectbox"] > div,
[data-testid="stMultiSelect"] > div {
    background: #FFFFFF !important;
    border-color: #E2E8F0 !important;
    border-radius: 8px !important;
}
input, textarea {
    background: #FFFFFF !important;
    border-color: #E2E8F0 !important;
    color: #0F172A !important;
    font-family: 'Inter', sans-serif !important;
}
label { color: #64748B !important; font-size: 12px !important; }
</style>
""", unsafe_allow_html=True)

# ── Renk Sabitleri (Light Finance) ───────────────────────────────────
COLOR_GREEN  = "#16A34A"
COLOR_YELLOW = "#CA8A04"
COLOR_RED    = "#DC2626"
COLOR_BLUE   = "#2563EB"
COLOR_PURPLE = "#7C3AED"
BG_PAPER     = "rgba(0,0,0,0)"
BG_PLOT      = "rgba(0,0,0,0)"
GRID_COLOR   = "#E2E8F0"
TEXT_MAIN    = "#0F172A"
TEXT_SEC     = "#64748B"


# ── Lottie Yardımcısı ─────────────────────────────────────────────────
def _lottie_html(url: str, height: int = 260) -> str:
    return f"""
    <script
        src="https://unpkg.com/@lottiefiles/dotlottie-wc@0.9.14/dist/dotlottie-wc.js"
        type="module">
    </script>
    <div style="display:flex;justify-content:center;align-items:center;
                background:#FFFFFF;border-radius:12px;
                border:1px solid #E2E8F0;padding:16px;margin:8px 0;">
        <dotlottie-wc
            src="{url}"
            autoplay
            loop
            style="width:100%;max-width:480px;height:{height}px;">
        </dotlottie-wc>
    </div>
    """


# ── Cache ─────────────────────────────────────────────────────────────
@st.cache_resource
def get_graph():
    return build_graph()


@st.cache_data
def load_mock_data() -> dict:
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(ttl=600)
def fetch_live_usd_rate(fallback: float) -> float:
    try:
        r = requests.get("https://open.er-api.com/v6/latest/USD", timeout=5)
        r.raise_for_status()
        return float(r.json()["rates"]["TRY"])
    except Exception as e:
        print(f"Kur ajanı hatası: {e}")
        return fallback


# ── Yardımcılar ───────────────────────────────────────────────────────
def fmt_tl(v: float) -> str:
    return f"₺{v:,.0f}".replace(",", ".")


def get_fifo_cost_tl(product: dict, usd_rate: float) -> float:
    return _fifo_cost(product, usd_rate)["fifo_unit_cost_tl"]


def _restock_recommendation(product: dict) -> str:
    spw   = product.get("sales_per_week", 0)
    stock = product.get("stock_qty", 0)

    if spw <= 0:
        return "Satış Yok"

    weeks_left = stock / spw
    monthly    = spw * 4

    if weeks_left <= 1:
        return f"Acil {int(monthly * 2)} adet sipariş ver"
    elif weeks_left <= 2:
        return f"{int(monthly)} adet sipariş önerilir"
    elif weeks_left <= 6:
        return "Stok Yeterli"
    elif weeks_left <= 12:
        return "Stok Fazlası"
    else:
        return "Kritik Fazla — Tasfiye Dusun"


def build_inventory_df(data: dict, usd_rate: float) -> pd.DataFrame:
    rows = []
    for p in data["products"]:
        fifo_cost   = get_fifo_cost_tl(p, usd_rate)
        monthly_qty = p.get("sales_per_week", 0) * 4
        profit_tl   = p["our_price_tl"] - fifo_cost
        margin_pct  = (
            round((profit_tl / p["our_price_tl"]) * 100, 1)
            if p["our_price_tl"] else 0
        )
        spw = p.get("sales_per_week", 0)
        if spw > 0:
            weeks      = p["stock_qty"] / spw
            stock_flag = "Kritik" if weeks <= 2 else "Dikkat" if weeks <= 4 else "OK"
        else:
            stock_flag = "-"

        sku = p["sku"]
        rows.append({
            "Aksiyon":         f"/product_detail?sku={sku}",
            "SKU":             sku,
            "Urun Adi":        p["name"],
            "Kategori":        p["category"].replace("_", " ").title(),
            "Stok Durumu":     stock_flag,
            "Stok Adet":       p["stock_qty"],
            "_stock_qty":      p["stock_qty"],
            "Aylik Satis":     monthly_qty,
            "Mevcut Fiyat":    p["our_price_tl"],
            "FIFO Maliyet":    round(fifo_cost, 0),
            "Satis Kari TL":   round(profit_tl, 0),
            "Marj":            margin_pct,
            "_margin_raw":     margin_pct,
            "Durum Oneri":     _restock_recommendation(p),
        })
    return pd.DataFrame(rows)


# ── Grafik: Fiyat vs Kırmızı Çizgi ───────────────────────────────────
def render_price_vs_redline(cost_metrics: dict) -> None:
    skus       = list(cost_metrics.keys())
    our_prices = [cost_metrics[s]["our_price_tl"]      for s in skus]
    red_lines  = [cost_metrics[s]["red_line_price_tl"] for s in skus]
    healths    = [cost_metrics[s]["health"]             for s in skus]
    short_skus = [s.split("-")[0] + "..."              for s in skus]
    bar_colors = [
        COLOR_RED    if h == "KRİTİK"
        else COLOR_YELLOW if h == "UYARI"
        else COLOR_GREEN
        for h in healths
    ]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Mevcut Fiyat", x=short_skus, y=our_prices,
        marker_color=bar_colors, opacity=0.85,
        text=[fmt_tl(v) for v in our_prices], textposition="outside",
        textfont=dict(color=TEXT_MAIN, size=9),
    ))
    fig.add_trace(go.Bar(
        name="Kirmizi Cizgi", x=short_skus, y=red_lines,
        marker_color="rgba(220,38,38,0.15)",
        marker_line=dict(color=COLOR_RED, width=2),
        text=[fmt_tl(v) for v in red_lines], textposition="outside",
        textfont=dict(color=COLOR_RED, size=9),
    ))
    fig.update_layout(
        paper_bgcolor=BG_PAPER, plot_bgcolor=BG_PLOT,
        font=dict(color=TEXT_SEC, size=11, family="Inter"),
        margin=dict(l=10, r=10, t=40, b=10), height=360,
        barmode="group",
        legend=dict(orientation="h", y=1.12, font=dict(color=TEXT_SEC),
                    bgcolor="rgba(0,0,0,0)"),
        title=dict(text="Mevcut Fiyat vs Kirmizi Cizgi",
                   font=dict(color=TEXT_MAIN, size=13, family="Inter"), x=0),
        xaxis=dict(gridcolor=GRID_COLOR, tickfont=dict(color=TEXT_SEC)),
        yaxis=dict(gridcolor=GRID_COLOR, tickprefix="₺",
                   tickformat=",.0f", tickfont=dict(color=TEXT_SEC)),
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Grafik: Satış Hacmi Pie ───────────────────────────────────────────
def render_sales_volume_pie(
    data: dict,
    filtered_skus: list | None = None,
) -> None:
    products = data["products"]
    if filtered_skus:
        products = [p for p in products if p["sku"] in filtered_skus]
    labels = [" ".join(p["name"].split()[:2]) for p in products]
    values = [p.get("sales_per_week", 0) for p in products]

    colors_pie = [
        "#2563EB", "#16A34A", "#CA8A04", "#DC2626", "#7C3AED",
        "#0891B2", "#DB2777", "#EA580C", "#65A30D", "#0284C7",
    ]
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.45,
        marker=dict(colors=colors_pie,
                    line=dict(color="#FFFFFF", width=2)),
        textfont=dict(size=10, color=TEXT_MAIN, family="Inter"),
        hovertemplate="%{label}<br>Haftalık: %{value} adet<br>%{percent}<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor=BG_PAPER, showlegend=False,
        margin=dict(l=0, r=0, t=10, b=0), height=270,
        font=dict(family="Inter"),
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Grafik: Kategori Kar Bar ──────────────────────────────────────────
def render_category_profit_bar(
    data: dict,
    usd_rate: float,
    filtered_skus: list | None = None,
) -> None:
    cat_profit: dict[str, float] = {}
    for p in data["products"]:
        if filtered_skus and p["sku"] not in filtered_skus:
            continue
        fifo_cost   = get_fifo_cost_tl(p, usd_rate)
        unit_profit = p["our_price_tl"] - fifo_cost
        monthly_qty = p.get("sales_per_week", 0) * 4
        cat         = p["category"].replace("_", " ").title()
        cat_profit[cat] = cat_profit.get(cat, 0) + unit_profit * monthly_qty

    items      = sorted(cat_profit.items(), key=lambda x: x[1], reverse=True)
    cats       = [i[0] for i in items]
    profits    = [i[1] for i in items]
    bar_colors = [
        COLOR_GREEN  if v > 50_000
        else COLOR_YELLOW if v > 20_000
        else COLOR_RED
        for v in profits
    ]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=cats, y=profits, marker_color=bar_colors, opacity=0.85,
        text=[fmt_tl(v) for v in profits], textposition="outside",
        textfont=dict(color=TEXT_MAIN, size=9, family="Inter"),
        hovertemplate="<b>%{x}</b><br>₺%{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor=BG_PAPER, plot_bgcolor=BG_PLOT,
        font=dict(color=TEXT_SEC, size=11, family="Inter"),
        margin=dict(l=10, r=10, t=40, b=30), height=300,
        showlegend=False,
        title=dict(text="Kategori Bazli Aylik Kar",
                   font=dict(color=TEXT_MAIN, size=13, family="Inter"), x=0),
        xaxis=dict(gridcolor=GRID_COLOR,
                   tickfont=dict(color=TEXT_SEC, size=9), tickangle=-30),
        yaxis=dict(gridcolor=GRID_COLOR, tickprefix="₺",
                   tickformat=",.0f", tickfont=dict(color=TEXT_SEC)),
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Grafik: BCG Scatter ───────────────────────────────────────────────
def render_bcg_scatter(
    data: dict,
    usd_rate: float,
    filtered_skus: list | None = None,
) -> None:
    names, monthly_list, profit_list, stock_list, cat_list = [], [], [], [], []
    for p in data["products"]:
        if filtered_skus and p["sku"] not in filtered_skus:
            continue
        fifo_cost   = get_fifo_cost_tl(p, usd_rate)
        unit_profit = p["our_price_tl"] - fifo_cost
        monthly_qty = p.get("sales_per_week", 0) * 4
        names.append(p["name"])
        monthly_list.append(monthly_qty)
        profit_list.append(unit_profit)
        stock_list.append(max(p["stock_qty"], 1))
        cat_list.append(p["category"].replace("_", " ").title())

    if not names:
        st.info("Filtre kriterlerine uyan urun bulunamadi.")
        return

    max_stock    = max(stock_list)
    bubble_sizes = [max(8, int((s / max_stock) * 55)) for s in stock_list]
    unique_cats  = list(set(cat_list))
    palette      = [
        "#2563EB", "#16A34A", "#CA8A04", "#DC2626",
        "#7C3AED", "#0891B2", "#DB2777", "#EA580C",
    ]
    color_map = {c: palette[i % len(palette)] for i, c in enumerate(unique_cats)}

    fig = go.Figure()
    for cat in unique_cats:
        idx = [i for i, c in enumerate(cat_list) if c == cat]
        fig.add_trace(go.Scatter(
            x=[monthly_list[i] for i in idx],
            y=[profit_list[i]  for i in idx],
            mode="markers", name=cat,
            marker=dict(size=[bubble_sizes[i] for i in idx],
                        color=color_map[cat], opacity=0.75,
                        line=dict(color="#FFFFFF", width=1.5)),
            text=[names[i] for i in idx],
            customdata=[[stock_list[i]] for i in idx],
            hovertemplate=(
                "<b>%{text}</b><br>Aylik: %{x} adet<br>"
                "Kar: ₺%{y:,.0f}<br>Stok: %{customdata[0]}<extra></extra>"
            ),
        ))

    avg_x = sum(monthly_list) / len(monthly_list)
    avg_y = sum(profit_list)  / len(profit_list)
    max_x = max(monthly_list)
    max_y = max(profit_list)
    min_y = min(profit_list)

    fig.add_vline(x=avg_x, line_dash="dot", line_color=GRID_COLOR, opacity=0.9)
    fig.add_hline(y=avg_y, line_dash="dot", line_color=GRID_COLOR, opacity=0.9)
    fig.add_annotation(x=max_x * 0.87, y=max_y * 0.90,
                       text="YILDIZLAR", showarrow=False,
                       font=dict(color=COLOR_GREEN, size=10, family="Inter"))
    fig.add_annotation(x=max_x * 0.87, y=avg_y * 0.25,
                       text="SORU ISARETLERI", showarrow=False,
                       font=dict(color=COLOR_YELLOW, size=10, family="Inter"))
    fig.add_annotation(x=avg_x * 0.10, y=max_y * 0.90,
                       text="NAKIT INEKLERI", showarrow=False,
                       font=dict(color=COLOR_BLUE, size=10, family="Inter"))
    fig.add_annotation(x=avg_x * 0.10, y=min_y + abs(min_y) * 0.15,
                       text="KOPEKLER", showarrow=False,
                       font=dict(color=COLOR_RED, size=10, family="Inter"))

    fig.update_layout(
        paper_bgcolor=BG_PAPER, plot_bgcolor=BG_PLOT,
        font=dict(color=TEXT_SEC, size=11, family="Inter"),
        margin=dict(l=10, r=10, t=40, b=10), height=420,
        title=dict(text="BCG Matrisi — Kar / Hacim / Stok",
                   font=dict(color=TEXT_MAIN, size=13, family="Inter"), x=0),
        legend=dict(orientation="v", x=1.02, y=1,
                    font=dict(color=TEXT_SEC, size=9, family="Inter"),
                    bgcolor="rgba(248,250,252,0.95)",
                    bordercolor=GRID_COLOR, borderwidth=1),
        xaxis=dict(title=dict(text="Aylik Satis Adedi",
                               font=dict(color=TEXT_SEC, family="Inter")),
                   gridcolor=GRID_COLOR, tickfont=dict(color=TEXT_SEC)),
        yaxis=dict(title=dict(text="Birim Kar (TL)",
                               font=dict(color=TEXT_SEC, family="Inter")),
                   gridcolor=GRID_COLOR, tickprefix="₺",
                   tickformat=",.0f", tickfont=dict(color=TEXT_SEC)),
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Grafik: Risk Scatter ──────────────────────────────────────────────
def render_risk_scatter(
    data: dict,
    usd_rate: float,
    filtered_skus: list | None = None,
) -> None:
    names_r, margin_r, stock_r, cost_r, cat_r = [], [], [], [], []
    for p in data["products"]:
        if filtered_skus and p["sku"] not in filtered_skus:
            continue
        fifo_cost  = get_fifo_cost_tl(p, usd_rate)
        profit_tl  = p["our_price_tl"] - fifo_cost
        margin_pct = (
            round((profit_tl / p["our_price_tl"]) * 100, 1)
            if p["our_price_tl"] else 0
        )
        names_r.append(p["name"])
        margin_r.append(margin_pct)
        stock_r.append(p["stock_qty"])
        cost_r.append(max(fifo_cost, 1))
        cat_r.append(p["category"].replace("_", " ").title())

    if not names_r:
        st.info("Filtre kriterlerine uyan urun bulunamadi.")
        return

    max_cost     = max(cost_r)
    bubble_sizes = [max(8, int((c / max_cost) * 60)) for c in cost_r]
    unique_cats  = list(set(cat_r))
    palette      = [
        "#2563EB", "#16A34A", "#CA8A04", "#DC2626",
        "#7C3AED", "#0891B2", "#DB2777", "#EA580C",
    ]
    color_map = {c: palette[i % len(palette)] for i, c in enumerate(unique_cats)}

    fig = go.Figure()
    for cat in unique_cats:
        idx = [i for i, c in enumerate(cat_r) if c == cat]
        fig.add_trace(go.Scatter(
            x=[margin_r[i] for i in idx],
            y=[stock_r[i]  for i in idx],
            mode="markers", name=cat,
            marker=dict(size=[bubble_sizes[i] for i in idx],
                        color=color_map[cat], opacity=0.72,
                        line=dict(color="#FFFFFF", width=1.5)),
            text=[names_r[i] for i in idx],
            customdata=[[cost_r[i]] for i in idx],
            hovertemplate=(
                "<b>%{text}</b><br>Marj: %{x:.1f}%<br>"
                "Stok: %{y} adet<br>FIFO: ₺%{customdata[0]:,.0f}<extra></extra>"
            ),
        ))

    fig.add_vline(x=0,  line_dash="dash", line_color=COLOR_RED,    opacity=0.5)
    fig.add_vline(x=10, line_dash="dot",  line_color=COLOR_YELLOW,  opacity=0.4)

    fig.update_layout(
        paper_bgcolor=BG_PAPER, plot_bgcolor=BG_PLOT,
        font=dict(color=TEXT_SEC, size=11, family="Inter"),
        margin=dict(l=10, r=10, t=40, b=10), height=370,
        title=dict(text="Risk Matrisi — Marj % vs Stok (Balon = FIFO Maliyet)",
                   font=dict(color=TEXT_MAIN, size=13, family="Inter"), x=0),
        legend=dict(orientation="v", x=1.02, y=1,
                    font=dict(color=TEXT_SEC, size=9, family="Inter"),
                    bgcolor="rgba(248,250,252,0.95)",
                    bordercolor=GRID_COLOR, borderwidth=1),
        xaxis=dict(title=dict(text="Marj %",
                               font=dict(color=TEXT_SEC, family="Inter")),
                   gridcolor=GRID_COLOR, tickfont=dict(color=TEXT_SEC),
                   ticksuffix="%"),
        yaxis=dict(title=dict(text="Stok Miktari (Adet)",
                               font=dict(color=TEXT_SEC, family="Inter")),
                   gridcolor=GRID_COLOR, tickfont=dict(color=TEXT_SEC)),
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Grafik: Satış Trend ───────────────────────────────────────────────
def render_sales_trend_line(
    data: dict,
    filtered_skus: list | None = None,
    period_weeks: int = 4,
) -> None:
    random.seed(42)
    products = data["products"]
    if filtered_skus:
        products = [p for p in products if p["sku"] in filtered_skus]
    products = sorted(
        products, key=lambda p: p.get("sales_per_week", 0), reverse=True
    )[:6]

    fig    = go.Figure()
    weeks  = [f"H-{period_weeks - i}" for i in range(period_weeks)] + ["Bu Hafta"]
    palette = [
        "#2563EB", "#16A34A", "#CA8A04", "#DC2626",
        "#7C3AED", "#0891B2",
    ]

    for idx, p in enumerate(products):
        spw    = p.get("sales_per_week", 0)
        series = [
            max(0, int(spw * (1 + random.uniform(-0.15, 0.15))))
            for _ in range(period_weeks)
        ] + [spw]
        fig.add_trace(go.Scatter(
            x=weeks, y=series,
            mode="lines+markers",
            name=" ".join(p["name"].split()[:2]),
            line=dict(color=palette[idx % len(palette)], width=2),
            marker=dict(size=5),
            hovertemplate="<b>%{fullData.name}</b><br>%{x}: %{y} adet<extra></extra>",
        ))

    fig.update_layout(
        paper_bgcolor=BG_PAPER, plot_bgcolor=BG_PLOT,
        font=dict(color=TEXT_SEC, size=11, family="Inter"),
        margin=dict(l=10, r=10, t=40, b=10), height=310,
        title=dict(text="Satis Hizi Trendi (Haftalik Simulasyon)",
                   font=dict(color=TEXT_MAIN, size=13, family="Inter"), x=0),
        legend=dict(orientation="h", y=-0.28,
                    font=dict(color=TEXT_SEC, size=9, family="Inter"),
                    bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(gridcolor=GRID_COLOR, tickfont=dict(color=TEXT_SEC)),
        yaxis=dict(title=dict(text="Haftalik Satis Adedi",
                               font=dict(color=TEXT_SEC, family="Inter")),
                   gridcolor=GRID_COLOR, tickfont=dict(color=TEXT_SEC)),
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Grafik: Tahmini Kar Bar ───────────────────────────────────────────
def render_projected_profit_bar(
    data: dict,
    usd_rate: float,
    filtered_skus: list | None = None,
) -> None:
    rows_proj = []
    for p in data["products"]:
        if filtered_skus and p["sku"] not in filtered_skus:
            continue
        fifo_cost   = get_fifo_cost_tl(p, usd_rate)
        unit_profit = p["our_price_tl"] - fifo_cost
        monthly_qty = p.get("sales_per_week", 0) * 4
        sellable    = min(monthly_qty, p["stock_qty"])
        rows_proj.append({
            "name":   " ".join(p["name"].split()[:3]),
            "profit": unit_profit * sellable,
        })

    rows_proj.sort(key=lambda r: r["profit"], reverse=True)
    names   = [r["name"]   for r in rows_proj]
    profits = [r["profit"] for r in rows_proj]
    colors  = [COLOR_GREEN if v > 0 else COLOR_RED for v in profits]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=names, y=profits,
        marker_color=colors, opacity=0.85,
        text=[fmt_tl(v) for v in profits], textposition="outside",
        textfont=dict(color=TEXT_MAIN, size=8, family="Inter"),
        hovertemplate="<b>%{x}</b><br>Tahmini Kar: ₺%{y:,.0f}<extra></extra>",
    ))
    fig.add_hline(y=0, line_color=GRID_COLOR, line_width=1.5)
    fig.update_layout(
        paper_bgcolor=BG_PAPER, plot_bgcolor=BG_PLOT,
        font=dict(color=TEXT_SEC, size=11, family="Inter"),
        margin=dict(l=10, r=10, t=40, b=40), height=310,
        showlegend=False,
        title=dict(text="Ay Sonu Tahmini Kar Projeksiyonu (Stok Kisitli)",
                   font=dict(color=TEXT_MAIN, size=13, family="Inter"), x=0),
        xaxis=dict(gridcolor=GRID_COLOR,
                   tickfont=dict(color=TEXT_SEC, size=8), tickangle=-35),
        yaxis=dict(gridcolor=GRID_COLOR, tickprefix="₺",
                   tickformat=",.0f", tickfont=dict(color=TEXT_SEC)),
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Aksiyon Paneli ────────────────────────────────────────────────────
def render_action_panel(suggested_actions: list) -> None:
    if not suggested_actions:
        st.info("Gemini herhangi bir aksiyon onermedi.")
        return

    TYPE_META = {
        "price_update":       ("[FIYAT]",   "Fiyat Duzelt",        "action-critical"),
        "smart_bundle":       ("[BUNDLE]",  "Smart Bundle",        "action-bundle"),
        "dynamic_markdown":   ("[INDIRIM]", "Kademeli Indirim",    "action-markdown"),
        "gift_with_purchase": ("[HEDIYE]",  "Sepet Buyutucu",      "action-gift"),
        "liquidate":          ("[B2B]",     "B2B Tasfiye",         "action-liquidate"),
        "hold":               ("[BEKLE]",   "Pozisyon Koru",       "action-hold"),
    }

    for i, action in enumerate(suggested_actions):
        atype            = action.get("action_type", "hold")
        tag, label, css  = TYPE_META.get(atype, ("[?]", "Bilinmiyor", "action-hold"))
        reason           = action.get("reason", "")
        old_price        = action.get("old_price_tl")
        btn_label        = action.get("button_label", "Uygula")

        if atype == "price_update":
            new_p   = action.get("new_price_tl", 0)
            chg_pct = action.get("price_change_pct", 0)
            sign    = "+" if chg_pct and chg_pct > 0 else ""
            detail  = (
                f"<div class='action-detail'>"
                f"Eski: <b>{fmt_tl(old_price)}</b> "
                f"<span class='price-arrow'>&#8594;</span> "
                f"Yeni: <b>{fmt_tl(new_p)}</b> "
                f"<span class='price-up'>({sign}{chg_pct:.1f}%)</span>"
                f"</div>"
            )
        elif atype == "smart_bundle":
            partner = action.get("bundle_with_sku", "?")
            bp      = action.get("bundle_price_tl", 0)
            detail  = (
                f"<div class='action-detail'>"
                f"Paket: <code>{action.get('sku','')}</code> + "
                f"<code>{partner}</code> &#8594; <b>{fmt_tl(bp)}</b></div>"
            )
        elif atype == "dynamic_markdown":
            new_p  = action.get("new_price_tl", 0)
            md_pct = action.get("markdown_pct", 0)
            steps  = action.get("steps", 3)
            detail = (
                f"<div class='action-detail'>"
                f"Hedef: <b>{fmt_tl(new_p)}</b> "
                f"({md_pct:.1f}% indirim, {steps} kademe)</div>"
            )
        elif atype == "gift_with_purchase":
            trigger = action.get("trigger_basket_tl", 50_000)
            detail  = (
                f"<div class='action-detail'>"
                f"<b>{fmt_tl(trigger)}+</b> sepette bu urun bedava eklensin.</div>"
            )
        elif atype == "liquidate":
            b2b    = action.get("b2b_price_tl", 0)
            detail = (
                f"<div class='action-detail'>"
                f"B2B Fiyati: <b>{fmt_tl(b2b)}</b> (toptanci kanali)</div>"
            )
        else:
            detail = (
                f"<div class='action-detail price-hold'>"
                f"Fiyat korunuyor: <b>{fmt_tl(old_price)}</b></div>"
            ) if old_price else ""

        st.markdown(f"""
        <div class="action-card {css}">
            <div class="action-title">
                <span style="font-family:monospace;font-size:11px;
                    background:#F1F5F9;padding:2px 6px;border-radius:4px;
                    color:#64748B;">{tag}</span>
                &nbsp;{label}&nbsp;
                <code style="font-size:11px;">{action.get('sku', '')}</code>
            </div>
            {detail}
            <div class="action-reason">"{reason}"</div>
        </div>
        """, unsafe_allow_html=True)

        if st.button(f"Onayla: {btn_label}", key=f"act_{i}",
                     use_container_width=True):
            st.success("Sistem emri onaylandi.")


def render_analysis_result(result: dict) -> None:
    if result.get("errors"):
        with st.expander("Sistem Uyarilari", expanded=False):
            for err in result["errors"]:
                st.error(err)

    tab_str, tab_news, tab_chart, tab_act = st.tabs([
        "Strateji Ozeti",
        "Piyasa Haberleri",
        "Durum Grafikleri",
        "Aksiyon Paneli",
    ])

    with tab_str:
        st.markdown(result.get("final_strategy", "Strateji uretilemedi."))
        if result.get("trend_insights"):
            st.info(result["trend_insights"])

    with tab_news:
        news = result.get("market_news", "")
        if news:
            st.markdown(news)
        else:
            st.info("Piyasa haberi bulunamadi.")

    with tab_chart:
        cost_metrics = result.get("cost_metrics", {})
        if cost_metrics:
            render_price_vs_redline(cost_metrics)
        else:
            st.info("Grafik icin cost_metrics verisi bulunamadi.")

    with tab_act:
        render_action_panel(result.get("suggested_actions", []))


# ══════════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════════
if "analysis_result" not in st.session_state:
    st.session_state["analysis_result"] = None
if "chart_index" not in st.session_state:
    st.session_state["chart_index"] = 0


# ══════════════════════════════════════════════════════════════════════
# VERİ YÜKLEME
# ══════════════════════════════════════════════════════════════════════
with st.spinner("Veriler yukleniyor..."):
    data          = load_mock_data()
    fallback_rate = data["market_config"]["current_usd_rate"]
    current_rate  = fetch_live_usd_rate(fallback_rate)
    products_map  = {p["sku"]: p for p in data["products"]}
    df_inv        = build_inventory_df(data, current_rate)

if "detail_sku" not in st.session_state:
    if not df_inv.empty:
        st.session_state["detail_sku"] = df_inv["SKU"].iloc[0]


# ══════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════
with st.sidebar:
    # Logo veya metin fallback
    _logo_path = _BASE_DIR / "img" / "logo.png"
    if os.path.exists(str(_logo_path)):
        st.image(str(_logo_path), use_container_width=True)
    else:
        st.markdown(
            "<div style='font-size:20px;font-weight:800;color:#0F172A;"
            "font-family:Inter,sans-serif;padding:8px 0;'>"
            "Bedülonca V9</div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        "<hr style='border:none;border-top:1px solid #E2E8F0;margin:12px 0;'>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div style='font-size:10px;font-weight:700;color:#94A3B8;"
        "letter-spacing:1.5px;text-transform:uppercase;margin-bottom:8px;'>"
        "Navigasyon</div>",
        unsafe_allow_html=True,
    )
    st.page_link("main.py",                 label="Ana Sayfa")
    st.page_link("pages/product_detail.py", label="Urun Detayi")

    st.markdown(
        "<hr style='border:none;border-top:1px solid #E2E8F0;margin:12px 0;'>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div style='font-size:10px;font-weight:700;color:#94A3B8;"
        "letter-spacing:1.5px;text-transform:uppercase;margin-bottom:8px;'>"
        "Kur</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div style='font-size:20px;font-weight:700;color:#2563EB;"
        f"font-family:Inter,sans-serif;'>₺{current_rate:.4f}</div>"
        f"<div style='font-size:11px;color:#94A3B8;margin-top:2px;'>per USD</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<hr style='border:none;border-top:1px solid #E2E8F0;margin:12px 0;'>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div style='font-size:10px;font-weight:700;color:#94A3B8;"
        "letter-spacing:1.5px;text-transform:uppercase;margin-bottom:8px;'>"
        "Stok</div>",
        unsafe_allow_html=True,
    )
    total_stock = sum(p["stock_qty"] for p in data["products"])
    st.markdown(
        f"<div style='font-size:13px;color:#0F172A;font-family:Inter,sans-serif;'>"
        f"<b>{len(data['products'])}</b> urun &nbsp;|&nbsp; "
        f"<b>{total_stock}</b> adet</div>",
        unsafe_allow_html=True,
    )

    # Copyright
    st.markdown(
        "<div style='font-size:10px;color:#94A3B8;text-align:center;"
        "margin-top:50px;font-family:Inter,sans-serif;'>"
        "© 2026 Tum haklari Bedualonca'ya aittir.</div>",
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════
# GLOBAL HEADER
# ══════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="global-header">
    <div class="brand-area">
        <div style="width:36px;height:36px;background:#2563EB;border-radius:8px;
                    display:flex;align-items:center;justify-content:center;">
            <span style="color:#fff;font-size:18px;font-weight:800;">B</span>
        </div>
        <div>
            <div class="brand-title">Bedülonca SaaS</div>
            <div class="brand-sub">Otonom Kar Marji Optimizasyonu · V9</div>
        </div>
    </div>
    <div style="display:flex;gap:12px;align-items:center;">
        <div class="kur-badge">
            <div class="kur-label">Canli Kur</div>
            <div class="kur-value">₺{current_rate:.4f}</div>
        </div>
        <div class="kur-badge">
            <div class="kur-label">Guncelleme</div>
            <div class="kur-value" style="font-size:14px;padding-top:2px;">
                {datetime.now().strftime('%H:%M')}
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
# BÖLÜM 1: ENVANTER TABLOSU
# ══════════════════════════════════════════════════════════════════════
all_categories = sorted(df_inv["Kategori"].unique().tolist())

# Başlık + 3-nokta popover (col yapısı)
hdr_col, dot_col = st.columns([11, 1])
with hdr_col:
    st.markdown(
        '<div class="section-label">Mevcut Envanter</div>',
        unsafe_allow_html=True,
    )
with dot_col:
    with st.popover("⋮", use_container_width=True):
        st.markdown(
            "<div style='font-size:11px;font-weight:700;color:#64748B;"
            "text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;'>"
            "Kategori Filtresi</div>",
            unsafe_allow_html=True,
        )
        sel_categories = st.multiselect(
            "Kategori",
            options=all_categories,
            default=all_categories,
            key="cat_filter",
            label_visibility="collapsed",
        )

        st.markdown(
            "<div style='font-size:11px;font-weight:700;color:#64748B;"
            "text-transform:uppercase;letter-spacing:1px;margin:10px 0 6px;'>"
            "Durum Filtresi</div>",
            unsafe_allow_html=True,
        )
        status_filter = st.selectbox(
            "Durum",
            options=[
                "Tumu",
                "Sadece kar edenler",
                "Sadece zarar edenler",
                "Aylik satisi ortalama ustunde",
                "Kritik stok (2 hafta)",
                "Stok fazlasi (12 hafta)",
            ],
            key="status_filter",
            label_visibility="collapsed",
        )

        st.markdown(
            "<hr style='border:none;border-top:1px solid #E2E8F0;margin:10px 0;'>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div style='font-size:11px;font-weight:700;color:#64748B;"
            "text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;'>"
            "CSV Indir</div>",
            unsafe_allow_html=True,
        )
        df_csv_export = df_inv.copy()
        df_csv_export["Aksiyon"] = df_inv["SKU"].apply(
            lambda s: f"https://bedualonca.app/product_detail?sku={s}"
        )
        export_cols = [
            "Aksiyon", "SKU", "Urun Adi", "Kategori",
            "Stok Durumu", "Stok Adet", "Aylik Satis",
            "Mevcut Fiyat", "FIFO Maliyet", "Satis Kari TL",
            "Marj", "Durum Oneri",
        ]
        # Sadece var olan sütunları al
        export_cols_avail = [c for c in export_cols if c in df_csv_export.columns]
        csv_buf = io.StringIO()
        df_csv_export[export_cols_avail].to_csv(
            csv_buf, index=False, sep=";", encoding="utf-8-sig"
        )
        csv_bytes = csv_buf.getvalue().encode("utf-8-sig")

        st.download_button(
            label="Envanteri Indir (.csv)",
            data=csv_bytes,
            file_name=f"envanter_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

# ── Filtre uygulama ───────────────────────────────────────────────────
df_filtered = df_inv.copy()
if sel_categories:
    df_filtered = df_filtered[df_filtered["Kategori"].isin(sel_categories)]

avg_monthly = df_filtered["Aylik Satis"].mean() if not df_filtered.empty else 0

if status_filter == "Sadece kar edenler":
    df_filtered = df_filtered[df_filtered["_margin_raw"] > 0]
elif status_filter == "Sadece zarar edenler":
    df_filtered = df_filtered[df_filtered["_margin_raw"] <= 0]
elif status_filter == "Aylik satisi ortalama ustunde":
    df_filtered = df_filtered[df_filtered["Aylik Satis"] > avg_monthly]
elif status_filter == "Kritik stok (2 hafta)":
    df_filtered = df_filtered[
        df_filtered["Durum Oneri"].str.contains("Acil|siparis onerilir", na=False)
    ]
elif status_filter == "Stok fazlasi (12 hafta)":
    df_filtered = df_filtered[
        df_filtered["Durum Oneri"].str.contains("Fazla|Tasfiye", na=False)
    ]

# ── Tablo gösterimi ───────────────────────────────────────────────────
display_cols = [
    "Aksiyon", "SKU", "Urun Adi", "Kategori",
    "Stok Durumu", "Stok Adet", "Aylik Satis",
    "Mevcut Fiyat", "FIFO Maliyet", "Satis Kari TL",
    "Marj", "Durum Oneri",
]
df_display = df_filtered[display_cols].copy()


def _color_row(row):
    m = row["Marj"]
    color = COLOR_RED if m < 0 else COLOR_YELLOW if m < 12 else COLOR_GREEN
    return [f"color: {color}"] * len(row)


styled_df = (
    df_display.style
    .apply(_color_row, axis=1)
    .format({
        "Mevcut Fiyat":  "₺{:,.0f}",
        "FIFO Maliyet":  "₺{:,.0f}",
        "Satis Kari TL": "₺{:,.0f}",
        "Marj":          "{:.1f}%",
    })
)

st.dataframe(
    styled_df,
    use_container_width=True,
    hide_index=True,
    height=460,
    column_config={
        "Aksiyon": st.column_config.LinkColumn(
            label="Incele",
            display_text="Incele",
            help="Urun detay sayfasina git",
            validate=r"^/product_detail\?sku=.+$",
        ),
        "SKU":      st.column_config.TextColumn("SKU",      width="medium"),
        "Urun Adi": st.column_config.TextColumn("Urun Adi", width="large"),
        "Mevcut Fiyat": st.column_config.NumberColumn(
            "Mevcut Fiyat", format="₺%.0f"
        ),
        "FIFO Maliyet": st.column_config.NumberColumn(
            "FIFO Maliyet", format="₺%.0f"
        ),
        "Satis Kari TL": st.column_config.NumberColumn(
            "Satis Kari", format="₺%.0f"
        ),
        "Marj": st.column_config.NumberColumn("Marj %", format="%.1f%%"),
        "Durum Oneri": st.column_config.TextColumn(
            "Stok Onerisi", width="large"
        ),
    },
)

# ── Özet Metrikler ────────────────────────────────────────────────────
st.markdown(
    "<hr style='border:none;border-top:1px solid #E2E8F0;margin:20px 0;'>",
    unsafe_allow_html=True,
)

total_monthly_profit = sum(
    (p["our_price_tl"] - get_fifo_cost_tl(p, current_rate))
    * p.get("sales_per_week", 0) * 4
    for p in data["products"]
)
critical_products = [
    p for p in data["products"]
    if p.get("sales_per_week", 0) > 0
    and (p["stock_qty"] / p["sales_per_week"]) < 2
]
critical_count = len(critical_products)

m1, m2, m3, m4, m5 = st.columns(5)
with m1:
    st.metric(
        "Toplam Urun",
        len(data["products"]),
        help="Sistemde kayitli toplam SKU sayisi.",
    )
with m2:
    st.metric(
        "Toplam Stok",
        sum(p["stock_qty"] for p in data["products"]),
        help="Tum urunlerin depodaki toplam stok adedi.",
    )
with m3:
    st.metric(
        "USD / TRY",
        f"₺{current_rate:.2f}",
        help="Open Exchange Rates canli kur. 10 dakikada bir guncellenir.",
    )
with m4:
    st.metric(
        "Aylik Tahmini Kar",
        fmt_tl(total_monthly_profit),
        help="Vergiler haric brut kar projeksiyonu. "
             "FIFO maliyet x satis hizi x 4 hafta formuluyle hesaplanir.",
    )
with m5:
    st.metric(
        "Kritik Stok",
        f"{critical_count} urun",
        delta="acil" if critical_count > 0 else None,
        delta_color="inverse",
        help="Mevcut satis hizinda 2 haftadan az stok kalan urunler.",
    )

# Kritik ürün linkleri
if critical_count > 0:
    link_parts = [
        f'<a href="/product_detail?sku={p["sku"]}" target="_self">{p["name"]}</a>'
        for p in critical_products
    ]
    st.markdown(
        f'<div class="critical-link" style="font-size:12px;margin-top:6px;">'
        f'Kritik stok: {" &nbsp;|&nbsp; ".join(link_parts)}</div>',
        unsafe_allow_html=True,
    )

st.markdown(
    "<hr style='border:none;border-top:1px solid #E2E8F0;margin:20px 0;'>",
    unsafe_allow_html=True,
)


# ══════════════════════════════════════════════════════════════════════
# BÖLÜM 2: CEO DASHBOARD — Carousel
# ══════════════════════════════════════════════════════════════════════
st.markdown(
    '<div class="section-label">CEO Dashboard — Kurumsal Analitik</div>',
    unsafe_allow_html=True,
)

# Dashboard filtre çubuğu
df1, df2, df3 = st.columns([2, 2, 1])
with df1:
    dash_categories = st.multiselect(
        "Kategori Filtresi",
        options=all_categories,
        default=all_categories,
        key="dash_cat",
        placeholder="Tum kategoriler",
    )
with df2:
    dash_period = st.selectbox(
        "Donem (Trend)",
        options=["Son 1 Hafta", "Son 4 Hafta", "Son 12 Hafta", "Tum Zamanlar"],
        index=1,
        key="dash_period",
    )
with df3:
    dash_top_n = st.number_input(
        "Trend maks urun",
        min_value=2, max_value=12, value=6, step=1,
        key="dash_top_n",
    )

period_map   = {"Son 1 Hafta": 1, "Son 4 Hafta": 4,
                "Son 12 Hafta": 12, "Tum Zamanlar": 24}
period_weeks = period_map[dash_period]

dash_skus = (
    [p["sku"] for p in data["products"]
     if p["category"].replace("_", " ").title() in dash_categories]
    if dash_categories
    else [p["sku"] for p in data["products"]]
)

# ── Carousel Tanımları ────────────────────────────────────────────────
CHARTS = [
    ("Haftalik Satis Dagilimi",        "pie"),
    ("Kategori Aylik Kar",             "cat_bar"),
    ("BCG Matrisi",                    "bcg"),
    ("Risk Matrisi",                   "risk"),
    ("Satis Hizi Trendi",              "trend"),
    ("Ay Sonu Kar Projeksiyonu",       "proj"),
]
N_CHARTS = len(CHARTS)

# Carousel: prev / dots / next
c_prev, c_dots, c_next = st.columns([1, 8, 1])

with c_prev:
    if st.button("&#8592;", key="chart_prev", use_container_width=True):
        st.session_state["chart_index"] = (
            st.session_state["chart_index"] - 1
        ) % N_CHARTS

with c_next:
    if st.button("&#8594;", key="chart_next", use_container_width=True):
        st.session_state["chart_index"] = (
            st.session_state["chart_index"] + 1
        ) % N_CHARTS

with c_dots:
    dots_str = "".join(
        '<span style="font-size:16px;color:#2563EB;margin:0 3px;">&#9679;</span>'
        if i == st.session_state["chart_index"] else
        '<span style="font-size:16px;color:#CBD5E1;margin:0 3px;">&#9675;</span>'
        for i in range(N_CHARTS)
    )
    st.markdown(
        f'<div style="text-align:center;line-height:2;padding-top:6px;">'
        f'{dots_str}</div>',
        unsafe_allow_html=True,
    )

# Aktif grafik başlığı
chart_title, chart_key = CHARTS[st.session_state["chart_index"]]
st.markdown(
    f'<div class="chart-title" style="text-align:center;'
    f'font-size:13px;color:{TEXT_MAIN};margin-bottom:10px;">'
    f'{chart_title}</div>',
    unsafe_allow_html=True,
)

# Aktif grafiği çiz
if chart_key == "pie":
    render_sales_volume_pie(data, filtered_skus=dash_skus)
elif chart_key == "cat_bar":
    render_category_profit_bar(data, current_rate, filtered_skus=dash_skus)
elif chart_key == "bcg":
    render_bcg_scatter(data, current_rate, filtered_skus=dash_skus)
elif chart_key == "risk":
    render_risk_scatter(data, current_rate, filtered_skus=dash_skus)
elif chart_key == "trend":
    render_sales_trend_line(data, filtered_skus=dash_skus,
                            period_weeks=period_weeks)
elif chart_key == "proj":
    render_projected_profit_bar(data, current_rate, filtered_skus=dash_skus)

st.markdown(
    "<hr style='border:none;border-top:1px solid #E2E8F0;margin:20px 0;'>",
    unsafe_allow_html=True,
)


# ══════════════════════════════════════════════════════════════════════
# BÖLÜM 3: YAPAY ZEKA ANALİZİ
# ══════════════════════════════════════════════════════════════════════
st.markdown(
    '<div class="section-label">LangGraph & Gemini Karar Motoru</div>',
    unsafe_allow_html=True,
)

c_input, c_btn = st.columns([4, 1])
with c_input:
    trigger_event = st.text_input(
        "Tetikleyici olay",
        value="Haftalik fiyat ve kur optimizasyonu",
        label_visibility="collapsed",
    )
with c_btn:
    btn_label_ai = (
        "Analizi Yenile"
        if st.session_state["analysis_result"] is not None
        else "Otonom Analizi Baslat"
    )
    run_button = st.button(
        btn_label_ai, type="primary", use_container_width=True
    )

# ── Analiz tetiklendi ─────────────────────────────────────────────────
if run_button:
    initial_state: AgentState = {
        "trigger_event":       trigger_event,
        "trending_skus":       [],
        "trend_insights":      "",
        "competitor_analysis": {},
        "cost_metrics":        {},
        "final_strategy":      "",
        "suggested_actions":   [],
        "crawl_log":           "",
        "market_news":         "",
        "errors":              [],
    }

    # Lottie — Ajan başlatma
    lottie_slot = st.empty()
    lottie_slot.markdown(
        _lottie_html(
            "https://lottie.host/0c0db29f-1e79-47f4-8897-bd1711a7abe6/ASzesxYWri.lottie",
            height=260,
        ),
        unsafe_allow_html=True,
    )

    status_slot = st.empty()
    with status_slot.status("Analiz asamalari:", expanded=True) as status:
        st.write("Trend verileri taranıyor...")

        # Lottie — Web istihbaratı
        intel_slot = st.empty()
        intel_slot.markdown(
            _lottie_html(
                "https://lottie.host/fcac4a45-2f96-4e1e-b819-8d5462770ebf/8wWQSIJQjO.lottie",
                height=200,
            ),
            unsafe_allow_html=True,
        )
        st.write("Piyasa haberleri ve rakip fiyatları çekiliyor...")
        st.write("FIFO maliyet hesaplaması yapılıyor...")
        st.write("Gemini V9 strateji motoru devreye giriyor...")

        result = get_graph().invoke(initial_state)
        st.session_state["analysis_result"] = result

        # Lottie'leri temizle
        lottie_slot.empty()
        intel_slot.empty()

        status.update(
            label="Analiz tamamlandi.",
            state="complete",
            expanded=False,
        )

# ── Sonuç varsa çiz ───────────────────────────────────────────────────
if st.session_state["analysis_result"] is not None:
    render_analysis_result(st.session_state["analysis_result"])