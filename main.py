# main.py
import json
import io
import os
import time
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
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
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Streamlit sistem UI gizleme (Deploy, GitHub vb.) */
    #MainMenu {visibility: hidden;}
    header    {visibility: hidden;}
    footer    {visibility: hidden;}

    .stApp { background-color: #0d0f18; }
    .block-container { padding: 1.5rem 2.5rem 3rem 2.5rem !important; }

    [data-testid="stSidebar"] {
        background: #0d0f18;
        border-right: 1px solid #1f2333;
    }
    [data-testid="stSidebar"] * { color: #cbd5e1 !important; }

    .global-header {
        display: flex; align-items: center; justify-content: space-between;
        background: #141724; border: 1px solid #1f2333;
        border-radius: 10px; padding: 10px 20px;
        margin-bottom: 20px;
    }
    .brand-area  { display: flex; align-items: center; gap: 12px; }
    .brand-title { font-size: 26px; font-weight: 800; color: #ffffff; }
    .brand-sub   { font-size: 11px; color: #00FF94; letter-spacing: 1px;
                   text-transform: uppercase; font-weight: 600; }
    .kur-badge   { background: #0d0f18; border: 1px solid #1f2333;
                   border-radius: 8px; padding: 6px 14px; text-align: right; }
    .kur-label   { font-size: 10px; color: #64748b; text-transform: uppercase;
                   letter-spacing: 1px; }
    .kur-value   { font-size: 18px; font-weight: 700; color: #00FF94; }

    .section-label {
        font-size: 12px; font-weight: 700; letter-spacing: 1.5px;
        text-transform: uppercase; color: #f8fafc;
        margin-bottom: 12px; margin-top: 24px;
        border-bottom: 1px solid #1f2333; padding-bottom: 6px;
    }
    .divider { border: none; border-top: 1px solid #1f2333; margin: 18px 0; }

    /* Metrik kutu eşit yükseklik */
    [data-testid="stMetric"] {
        background: #141724; border: 1px solid #1f2333;
        border-radius: 10px; padding: 12px 16px;
        height: 100%; display: flex;
        flex-direction: column; justify-content: center;
    }
    [data-testid="stMetricLabel"] { color: #94a3b8 !important; font-size: 11px !important; }
    [data-testid="stMetricValue"] { color: #f1f5f9 !important; font-size: 20px !important; }

    .action-card      { border-radius: 10px; padding: 14px 16px; margin-bottom: 10px; }
    .action-critical  { background: rgba(255,75,75,0.10); border: 1px solid rgba(255,75,75,0.35); }
    .action-bundle    { background: rgba(0,255,148,0.07); border: 1px solid rgba(0,255,148,0.30); }
    .action-markdown  { background: rgba(251,191,36,0.08); border: 1px solid rgba(251,191,36,0.30); }
    .action-gift      { background: rgba(56,189,248,0.08); border: 1px solid rgba(56,189,248,0.30); }
    .action-liquidate { background: rgba(168,85,247,0.08); border: 1px solid rgba(168,85,247,0.35); }
    .action-hold      { background: rgba(100,116,139,0.10); border: 1px solid rgba(100,116,139,0.25); }
    .action-title     { font-size: 14px; font-weight: 700; color: #f1f5f9; margin-bottom: 3px; }
    .action-detail    { font-size: 12px; color: #cbd5e1; margin-bottom: 5px; }
    .action-reason    { font-size: 12px; color: #94a3b8; font-style: italic; }
    .price-arrow      { color: #FF4B4B; font-weight: 700; }
    .price-up         { color: #FF4B4B; }
    .price-hold       { color: #94a3b8; }

    [data-testid="stDataFrame"] {
        border: 1px solid #1f2333; border-radius: 10px; overflow: hidden;
    }
    [data-testid="stStatus"] {
        background: #141724 !important;
        border: 1px solid #1f2333 !important;
        border-radius: 10px !important;
    }

    div[data-testid="stButton"] > button[kind="primary"] {
        background: #00FF94; color: #0d0f18; font-weight: 700;
        border: none; border-radius: 8px; padding: 8px 0;
        width: 100%; font-size: 13px; transition: opacity .2s;
    }
    div[data-testid="stButton"] > button[kind="primary"]:hover { opacity: 0.85; }

    div[data-testid="stButton"] > button[kind="secondary"] {
        background: #1f2333; color: #cbd5e1; font-weight: 600;
        border: 1px solid #334155; border-radius: 6px;
        font-size: 12px; padding: 4px 10px;
    }
    div[data-testid="stButton"] > button[kind="secondary"]:hover {
        background: #263044; border-color: #00FF94; color: #00FF94;
    }

    [data-testid="stTabs"] [data-baseweb="tab-list"] {
        background: transparent; border-bottom: 1px solid #1f2333; gap: 4px;
    }
    [data-testid="stTabs"] [data-baseweb="tab"] {
        background: transparent !important; color: #94a3b8 !important;
        font-size: 12px !important; font-weight: 600 !important;
        border-radius: 6px 6px 0 0 !important; padding: 7px 14px !important;
    }
    [data-testid="stTabs"] [aria-selected="true"] {
        background: #1f2333 !important; color: #00FF94 !important;
        border-bottom: 2px solid #00FF94 !important;
    }

    .chart-title {
        font-size: 12px; font-weight: 700; color: #94a3b8;
        letter-spacing: 1px; text-transform: uppercase;
        margin-bottom: 6px; margin-top: 14px;
    }

    [data-testid="stDataFrame"] a {
        color: #00FF94 !important;
        text-decoration: none !important;
        font-weight: 600;
    }
    [data-testid="stDataFrame"] a:hover {
        color: #ffffff !important;
        text-decoration: underline !important;
    }

    /* Popover / Tablo İşlemleri */
    [data-testid="stPopover"] {
        background: #141724 !important;
        border: 1px solid #1f2333 !important;
        border-radius: 10px !important;
    }

    /* Kritik stok linki */
    .critical-link a {
        color: #FF4B4B !important;
        font-weight: 700;
        text-decoration: underline;
    }
</style>
""", unsafe_allow_html=True)

# ── Renk Sabitleri ────────────────────────────────────────────────────
COLOR_GREEN  = "#00FF94"
COLOR_YELLOW = "#FBBF24"
COLOR_RED    = "#FF4B4B"
COLOR_PURPLE = "#818cf8"
COLOR_BLUE   = "#38bdf8"
BG_PAPER     = "rgba(0,0,0,0)"
BG_PLOT      = "rgba(0,0,0,0)"
GRID_COLOR   = "#1f2333"


# ── Cache ─────────────────────────────────────────────────────────────
@st.cache_resource
def get_graph():
    return build_graph()


@st.cache_data
def load_mock_data() -> dict:
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# Madde 8: TTL 600 saniye (10 dakika)
@st.cache_data(ttl=600)
def fetch_live_usd_rate(fallback: float) -> float:
    try:
        r = requests.get("https://open.er-api.com/v6/latest/USD", timeout=5)
        r.raise_for_status()
        return float(r.json()["rates"]["TRY"])
    except Exception as e:
        print(f"⚠️ Kur ajanı: {e}")
        return fallback


# ── Yardımcılar ───────────────────────────────────────────────────────
def fmt_tl(v: float) -> str:
    return f"₺{v:,.0f}".replace(",", ".")


def get_fifo_cost_tl(product: dict, usd_rate: float) -> float:
    return _fifo_cost(product, usd_rate)["fifo_unit_cost_tl"]


def _restock_recommendation(product: dict) -> str:
    """
    Madde 1: Tüketim hızına ve mevcut stoğa göre öneri üretir.
    """
    spw       = product.get("sales_per_week", 0)
    stock     = product.get("stock_qty", 0)
    monthly   = spw * 4

    if spw <= 0:
        return "⚫ Satış Yok"

    weeks_left = stock / spw

    if weeks_left <= 1:
        order_qty = max(monthly * 2, 1)
        return f"🚨 Acil {int(order_qty)} adet sipariş ver"
    elif weeks_left <= 2:
        order_qty = max(monthly, 1)
        return f"⚠️ {int(order_qty)} adet sipariş önerilir"
    elif weeks_left <= 6:
        return "✅ Stok Yeterli"
    elif weeks_left <= 12:
        return "📦 Stok Fazlası"
    else:
        return "🏭 Kritik Fazla — Tasfiye Düşün"


def build_inventory_df(data: dict, usd_rate: float) -> pd.DataFrame:
    """
    Envanter DataFrame'i oluşturur.
    Madde 1: 'Durum/Öneri' sütunu eklendi.
    """
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
            stock_flag = "🔴" if weeks <= 2 else "🟡" if weeks <= 4 else "🟢"
        else:
            stock_flag = "⚫"

        sku = p["sku"]
        rows.append({
            "Aksiyon":        f"/product_detail?sku={sku}",
            "SKU":            sku,
            "Ürün Adı":       p["name"],
            "Kategori":       p["category"].replace("_", " ").title(),
            "Stok":           f"{stock_flag} {p['stock_qty']}",
            "_stock_qty":     p["stock_qty"],          # gizli: filtre için
            "Aylık Satış":    monthly_qty,
            "Mevcut Fiyat":   p["our_price_tl"],
            "FIFO Maliyet":   round(fifo_cost, 0),
            "Satış Kârı (TL)":round(profit_tl, 0),
            "Marj %":         margin_pct,
            "_margin_raw":    margin_pct,              # gizli: filtre için
            "Durum/Öneri":    _restock_recommendation(p),
        })
    return pd.DataFrame(rows)


# ── Grafik Fonksiyonları ──────────────────────────────────────────────
def render_price_vs_redline(cost_metrics: dict) -> None:
    skus       = list(cost_metrics.keys())
    our_prices = [cost_metrics[s]["our_price_tl"]      for s in skus]
    red_lines  = [cost_metrics[s]["red_line_price_tl"] for s in skus]
    healths    = [cost_metrics[s]["health"]             for s in skus]
    short_skus = [s.split("-")[0] + "…"                for s in skus]
    bar_colors = [
        COLOR_RED    if h == "KRİTİK"
        else COLOR_YELLOW if h == "UYARI"
        else COLOR_GREEN
        for h in healths
    ]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Mevcut Fiyat", x=short_skus, y=our_prices,
        marker_color=bar_colors, opacity=0.9,
        text=[fmt_tl(v) for v in our_prices], textposition="outside",
        textfont=dict(color="#e2e8f0", size=10),
    ))
    fig.add_trace(go.Bar(
        name="Kırmızı Çizgi", x=short_skus, y=red_lines,
        marker_color="rgba(255,75,75,0.20)",
        marker_line=dict(color=COLOR_RED, width=2),
        text=[fmt_tl(v) for v in red_lines], textposition="outside",
        textfont=dict(color=COLOR_RED, size=10),
    ))
    fig.update_layout(
        paper_bgcolor=BG_PAPER, plot_bgcolor=BG_PLOT,
        font=dict(color="#94a3b8", size=11),
        margin=dict(l=10, r=10, t=40, b=10), height=360,
        barmode="group",
        legend=dict(orientation="h", y=1.12, font=dict(color="#cbd5e1"),
                    bgcolor="rgba(0,0,0,0)"),
        title=dict(text="Mevcut Fiyat vs Kırmızı Çizgi",
                   font=dict(color="#cbd5e1", size=13), x=0),
        xaxis=dict(gridcolor=GRID_COLOR, tickfont=dict(color="#cbd5e1")),
        yaxis=dict(gridcolor=GRID_COLOR, tickprefix="₺",
                   tickformat=",.0f", tickfont=dict(color="#94a3b8")),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_sales_volume_pie(data: dict, filtered_skus: list | None = None) -> None:
    products = data["products"]
    if filtered_skus:
        products = [p for p in products if p["sku"] in filtered_skus]
    labels = [" ".join(p["name"].split()[:2]) for p in products]
    values = [p.get("sales_per_week", 0) for p in products]
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.42,
        marker=dict(colors=px.colors.qualitative.Dark24,
                    line=dict(color="#0d0f18", width=2)),
        textfont=dict(size=10, color="#e2e8f0"),
        hovertemplate="%{label}<br>Haftalık: %{value} adet<br>%{percent}<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor=BG_PAPER, showlegend=False,
        margin=dict(l=0, r=0, t=10, b=0), height=270,
    )
    st.plotly_chart(fig, use_container_width=True)


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
        x=cats, y=profits, marker_color=bar_colors, opacity=0.88,
        text=[fmt_tl(v) for v in profits], textposition="outside",
        textfont=dict(color="#e2e8f0", size=9),
        hovertemplate="<b>%{x}</b><br>₺%{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor=BG_PAPER, plot_bgcolor=BG_PLOT,
        font=dict(color="#94a3b8", size=11),
        margin=dict(l=10, r=10, t=40, b=30), height=300,
        showlegend=False,
        title=dict(text="Kategori Bazlı Aylık Kâr",
                   font=dict(color="#cbd5e1", size=13), x=0),
        xaxis=dict(gridcolor=GRID_COLOR,
                   tickfont=dict(color="#cbd5e1", size=9), tickangle=-30),
        yaxis=dict(gridcolor=GRID_COLOR, tickprefix="₺",
                   tickformat=",.0f", tickfont=dict(color="#94a3b8")),
    )
    st.plotly_chart(fig, use_container_width=True)


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
        st.info("Filtre kriterlerine uyan ürün bulunamadı.")
        return

    max_stock    = max(stock_list)
    bubble_sizes = [max(8, int((s / max_stock) * 55)) for s in stock_list]
    unique_cats  = list(set(cat_list))
    palette      = px.colors.qualitative.Dark24
    color_map    = {c: palette[i % len(palette)] for i, c in enumerate(unique_cats)}

    fig = go.Figure()
    for cat in unique_cats:
        idx = [i for i, c in enumerate(cat_list) if c == cat]
        fig.add_trace(go.Scatter(
            x=[monthly_list[i] for i in idx],
            y=[profit_list[i]  for i in idx],
            mode="markers", name=cat,
            marker=dict(size=[bubble_sizes[i] for i in idx],
                        color=color_map[cat], opacity=0.80,
                        line=dict(color="#0d0f18", width=1)),
            text=[names[i] for i in idx],
            customdata=[[stock_list[i], cat_list[i]] for i in idx],
            hovertemplate=(
                "<b>%{text}</b><br>Aylık: %{x} adet<br>"
                "Kâr: ₺%{y:,.0f}<br>Stok: %{customdata[0]}<extra></extra>"
            ),
        ))

    avg_x = sum(monthly_list) / len(monthly_list)
    avg_y = sum(profit_list)  / len(profit_list)
    max_x = max(monthly_list)
    max_y = max(profit_list)
    min_y = min(profit_list)

    fig.add_vline(x=avg_x, line_dash="dot", line_color="#334155", opacity=0.7)
    fig.add_hline(y=avg_y, line_dash="dot", line_color="#334155", opacity=0.7)
    fig.add_annotation(x=max_x * 0.87, y=max_y * 0.90,
                       text="⭐ YILDIZLAR", showarrow=False,
                       font=dict(color=COLOR_GREEN, size=10))
    fig.add_annotation(x=max_x * 0.87, y=avg_y * 0.25,
                       text="❓ SORU İŞARETLERİ", showarrow=False,
                       font=dict(color=COLOR_YELLOW, size=10))
    fig.add_annotation(x=avg_x * 0.10, y=max_y * 0.90,
                       text="🐄 NAKİT İNEKLERİ", showarrow=False,
                       font=dict(color=COLOR_BLUE, size=10))
    fig.add_annotation(x=avg_x * 0.10, y=min_y + abs(min_y) * 0.15,
                       text="🐶 KÖPEKLER", showarrow=False,
                       font=dict(color=COLOR_RED, size=10))

    fig.update_layout(
        paper_bgcolor=BG_PAPER, plot_bgcolor=BG_PLOT,
        font=dict(color="#94a3b8", size=11),
        margin=dict(l=10, r=10, t=40, b=10), height=430,
        title=dict(text="BCG Matrisi — Kâr / Hacim / Stok",
                   font=dict(color="#cbd5e1", size=13), x=0),
        legend=dict(orientation="v", x=1.02, y=1,
                    font=dict(color="#cbd5e1", size=9),
                    bgcolor="rgba(20,23,36,0.9)",
                    bordercolor="#1f2333", borderwidth=1),
        xaxis=dict(title=dict(text="Aylık Satış Adedi",
                               font=dict(color="#94a3b8")),
                   gridcolor=GRID_COLOR, tickfont=dict(color="#cbd5e1")),
        yaxis=dict(title=dict(text="Birim Kâr (TL)",
                               font=dict(color="#94a3b8")),
                   gridcolor=GRID_COLOR, tickprefix="₺",
                   tickformat=",.0f", tickfont=dict(color="#94a3b8")),
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Madde 9: Yeni CEO Dashboard Grafikleri ────────────────────────────
def render_risk_scatter(
    data: dict,
    usd_rate: float,
    filtered_skus: list | None = None,
) -> None:
    """
    Risk Grafiği (Scatter):
    X = Marj %  |  Y = Stok Miktarı  |  Balon büyüklüğü = FIFO Maliyet
    """
    names_r, margin_r, stock_r, cost_r, cat_r = [], [], [], [], []
    for p in data["products"]:
        if filtered_skus and p["sku"] not in filtered_skus:
            continue
        fifo_cost   = get_fifo_cost_tl(p, usd_rate)
        profit_tl   = p["our_price_tl"] - fifo_cost
        margin_pct  = (
            round((profit_tl / p["our_price_tl"]) * 100, 1)
            if p["our_price_tl"] else 0
        )
        names_r.append(p["name"])
        margin_r.append(margin_pct)
        stock_r.append(p["stock_qty"])
        cost_r.append(max(fifo_cost, 1))
        cat_r.append(p["category"].replace("_", " ").title())

    if not names_r:
        st.info("Filtre kriterlerine uyan ürün bulunamadı.")
        return

    max_cost     = max(cost_r)
    bubble_sizes = [max(8, int((c / max_cost) * 60)) for c in cost_r]
    unique_cats  = list(set(cat_r))
    palette      = px.colors.qualitative.Pastel
    color_map    = {c: palette[i % len(palette)] for i, c in enumerate(unique_cats)}

    fig = go.Figure()
    for cat in unique_cats:
        idx = [i for i, c in enumerate(cat_r) if c == cat]
        fig.add_trace(go.Scatter(
            x=[margin_r[i] for i in idx],
            y=[stock_r[i]  for i in idx],
            mode="markers", name=cat,
            marker=dict(
                size=[bubble_sizes[i] for i in idx],
                color=color_map[cat], opacity=0.78,
                line=dict(color="#0d0f18", width=1),
            ),
            text=[names_r[i] for i in idx],
            customdata=[[cost_r[i]] for i in idx],
            hovertemplate=(
                "<b>%{text}</b><br>Marj: %{x:.1f}%<br>"
                "Stok: %{y} adet<br>FIFO Maliyet: ₺%{customdata[0]:,.0f}"
                "<extra></extra>"
            ),
        ))

    # Marj 0 çizgisi — zarar bölgesi ayrımı
    fig.add_vline(x=0, line_dash="dash", line_color=COLOR_RED, opacity=0.6)
    fig.add_vline(x=10, line_dash="dot", line_color=COLOR_YELLOW, opacity=0.5)

    fig.update_layout(
        paper_bgcolor=BG_PAPER, plot_bgcolor=BG_PLOT,
        font=dict(color="#94a3b8", size=11),
        margin=dict(l=10, r=10, t=40, b=10), height=380,
        title=dict(text="Risk Matrisi — Marj % vs Stok (Balon = FIFO Maliyet)",
                   font=dict(color="#cbd5e1", size=13), x=0),
        legend=dict(orientation="v", x=1.02, y=1,
                    font=dict(color="#cbd5e1", size=9),
                    bgcolor="rgba(20,23,36,0.9)",
                    bordercolor="#1f2333", borderwidth=1),
        xaxis=dict(title=dict(text="Marj %", font=dict(color="#94a3b8")),
                   gridcolor=GRID_COLOR, tickfont=dict(color="#cbd5e1"),
                   ticksuffix="%"),
        yaxis=dict(title=dict(text="Stok Miktarı (Adet)",
                               font=dict(color="#94a3b8")),
                   gridcolor=GRID_COLOR, tickfont=dict(color="#94a3b8")),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_sales_trend_line(
    data: dict,
    filtered_skus: list | None = None,
    period_weeks: int = 4,
) -> None:
    """
    Hareketli Ortalama / Trend:
    Gerçek geçmiş veri olmadığından sales_per_week'e ±%10 gürültü eklenerek
    simüle edilmiş haftalık trend çizgisi gösterilir.
    Gerçek projede bu fonksiyona zaman serisi verisi beslenir.
    """
    import random
    random.seed(42)

    products = data["products"]
    if filtered_skus:
        products = [p for p in products if p["sku"] in filtered_skus]

    # En fazla 6 ürün göster (grafik okunabilirliği)
    products = sorted(products,
                      key=lambda p: p.get("sales_per_week", 0),
                      reverse=True)[:6]

    fig    = go.Figure()
    weeks  = [f"H-{period_weeks - i}" for i in range(period_weeks)] + ["Bu Hafta"]
    palette = px.colors.qualitative.Dark24

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
            marker=dict(size=6),
            hovertemplate="<b>%{fullData.name}</b><br>%{x}: %{y} adet<extra></extra>",
        ))

    fig.update_layout(
        paper_bgcolor=BG_PAPER, plot_bgcolor=BG_PLOT,
        font=dict(color="#94a3b8", size=11),
        margin=dict(l=10, r=10, t=40, b=10), height=320,
        title=dict(text="Satış Hızı Trendi (Haftalık Simülasyon)",
                   font=dict(color="#cbd5e1", size=13), x=0),
        legend=dict(orientation="h", y=-0.25,
                    font=dict(color="#cbd5e1", size=9),
                    bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(gridcolor=GRID_COLOR, tickfont=dict(color="#cbd5e1")),
        yaxis=dict(title=dict(text="Haftalık Satış Adedi",
                               font=dict(color="#94a3b8")),
                   gridcolor=GRID_COLOR, tickfont=dict(color="#94a3b8")),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_projected_profit_bar(
    data: dict,
    usd_rate: float,
    filtered_skus: list | None = None,
) -> None:
    """
    Tahmini Kâr Grafiği:
    Mevcut satış hızıyla gidilirse ay sonu elde edilecek kâr projeksiyonu.
    """
    rows_proj = []
    for p in data["products"]:
        if filtered_skus and p["sku"] not in filtered_skus:
            continue
        fifo_cost    = get_fifo_cost_tl(p, usd_rate)
        unit_profit  = p["our_price_tl"] - fifo_cost
        monthly_qty  = p.get("sales_per_week", 0) * 4
        # Stok kısıtı: aylık satışı stok miktarıyla sınırla
        sellable     = min(monthly_qty, p["stock_qty"])
        proj_profit  = unit_profit * sellable
        rows_proj.append({
            "name":   " ".join(p["name"].split()[:3]),
            "profit": proj_profit,
        })

    rows_proj.sort(key=lambda r: r["profit"], reverse=True)
    names   = [r["name"]  for r in rows_proj]
    profits = [r["profit"] for r in rows_proj]
    colors  = [
        COLOR_GREEN  if v > 0  else COLOR_RED
        for v in profits
    ]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=names, y=profits,
        marker_color=colors, opacity=0.88,
        text=[fmt_tl(v) for v in profits], textposition="outside",
        textfont=dict(color="#e2e8f0", size=9),
        hovertemplate="<b>%{x}</b><br>Tahmini Kâr: ₺%{y:,.0f}<extra></extra>",
    ))
    fig.add_hline(y=0, line_color="#334155", line_width=1)

    fig.update_layout(
        paper_bgcolor=BG_PAPER, plot_bgcolor=BG_PLOT,
        font=dict(color="#94a3b8", size=11),
        margin=dict(l=10, r=10, t=40, b=40), height=320,
        showlegend=False,
        title=dict(text="Ay Sonu Tahmini Kâr Projeksiyonu (Stok Kısıtlı)",
                   font=dict(color="#cbd5e1", size=13), x=0),
        xaxis=dict(gridcolor=GRID_COLOR,
                   tickfont=dict(color="#cbd5e1", size=8), tickangle=-35),
        yaxis=dict(gridcolor=GRID_COLOR, tickprefix="₺",
                   tickformat=",.0f", tickfont=dict(color="#94a3b8")),
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Aksiyon Paneli ────────────────────────────────────────────────────
def render_action_panel(suggested_actions: list) -> None:
    if not suggested_actions:
        st.info("Gemini herhangi bir aksiyon önermedi.")
        return

    TYPE_META = {
        "price_update":       ("🔴", "Fiyat Düzelt",          "action-critical"),
        "smart_bundle":       ("🟢", "Smart Bundle",           "action-bundle"),
        "dynamic_markdown":   ("🟡", "Kademeli İndirim",       "action-markdown"),
        "gift_with_purchase": ("🎁", "Sepet Büyütücü Hediye",  "action-gift"),
        "liquidate":          ("💀", "B2B Tasfiye",            "action-liquidate"),
        "hold":               ("⚫", "Pozisyon Koru",          "action-hold"),
    }

    for i, action in enumerate(suggested_actions):
        atype            = action.get("action_type", "hold")
        icon, label, css = TYPE_META.get(atype, ("⚪", "Bilinmiyor", "action-hold"))
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
                f"<span class='price-arrow'>➔</span> "
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
                f"<code>{partner}</code> → <b>{fmt_tl(bp)}</b></div>"
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
                f"<b>{fmt_tl(trigger)}+</b> sepette bu ürün bedava eklensin.</div>"
            )
        elif atype == "liquidate":
            b2b    = action.get("b2b_price_tl", 0)
            detail = (
                f"<div class='action-detail'>"
                f"B2B Fiyatı: <b>{fmt_tl(b2b)}</b> (toptancı kanalı)</div>"
            )
        else:
            detail = (
                f"<div class='action-detail price-hold'>"
                f"Fiyat korunuyor: <b>{fmt_tl(old_price)}</b></div>"
            ) if old_price else ""

        st.markdown(f"""
        <div class="action-card {css}">
            <div class="action-title">
                {icon} {label} &nbsp;·&nbsp;
                <code>{action.get('sku', '')}</code>
            </div>
            {detail}
            <div class="action-reason">"{reason}"</div>
        </div>
        """, unsafe_allow_html=True)

        if st.button(f"✅ {btn_label}", key=f"act_{i}", use_container_width=True):
            st.success("Sistem emri onaylandı.")


def render_analysis_result(result: dict) -> None:
    if result.get("errors"):
        with st.expander("⚠️ Sistem Uyarıları", expanded=False):
            for err in result["errors"]:
                st.error(err)

    tab_str, tab_news, tab_chart, tab_act = st.tabs([
        "📑 Strateji Özeti",
        "📰 Piyasa Haberleri",
        "📊 Durum Grafikleri",
        "🎮 Aksiyon Paneli",
    ])

    with tab_str:
        st.markdown(result.get("final_strategy", "Strateji üretilemedi."))
        if result.get("trend_insights"):
            st.info(result["trend_insights"])

    with tab_news:
        news = result.get("market_news", "")
        if news:
            st.markdown(news)
        else:
            st.info("Piyasa haberi bulunamadı.")

    with tab_chart:
        cost_metrics = result.get("cost_metrics", {})
        if cost_metrics:
            render_price_vs_redline(cost_metrics)
        else:
            st.info("Grafik için cost_metrics verisi bulunamadı.")

    with tab_act:
        render_action_panel(result.get("suggested_actions", []))


# ══════════════════════════════════════════════════════════════════════
# SESSION STATE BAŞLATMA
# ══════════════════════════════════════════════════════════════════════
if "analysis_result" not in st.session_state:
    st.session_state["analysis_result"] = None


# ══════════════════════════════════════════════════════════════════════
# VERİ YÜKLEME  (Madde 7: Spinner)
# ══════════════════════════════════════════════════════════════════════
with st.spinner("Veriler yükleniyor..."):
    data          = load_mock_data()
    fallback_rate = data["market_config"]["current_usd_rate"]
    current_rate  = fetch_live_usd_rate(fallback_rate)
    products_map  = {p["sku"]: p for p in data["products"]}
    df_inv        = build_inventory_df(data, current_rate)

# Madde 6: detail_sku session_state başlatma — ilk ürün ile varsayılan
if "detail_sku" not in st.session_state:
    if not df_inv.empty:
        st.session_state["detail_sku"] = df_inv["SKU"].iloc[0]


# ══════════════════════════════════════════════════════════════════════
# SIDEBAR  (Madde 3: API Test bölümü kaldırıldı | Madde 10: Logo)
# ══════════════════════════════════════════════════════════════════════
with st.sidebar:
    # Madde 10: Logo — dosya yoksa metin fallback
    _logo_path = _BASE_DIR / "img" / "logo.png"
    if os.path.exists(_logo_path):
        st.image(str(_logo_path), use_container_width=True)
    else:
        st.markdown("### ⚡ Bedülonca V9")

    st.markdown("---")
    st.markdown("**📌 Hızlı Erişim**")
    st.page_link("main.py",                 label="🏠 Ana Dashboard")
    st.page_link("pages/product_detail.py", label="🔍 Ürün Detay")
    st.markdown("---")

    # Kur
    st.markdown("**📈 Kur**")
    st.markdown(f"`₺{current_rate:.4f}` / USD")
    st.markdown("---")

    # Stok özeti
    st.markdown("**📦 Stok**")
    st.markdown(f"Ürün: `{len(data['products'])}`")
    total_stock = sum(p["stock_qty"] for p in data["products"])
    st.markdown(f"Toplam: `{total_stock} adet`")


# ══════════════════════════════════════════════════════════════════════
# GLOBAL HEADER
# ══════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="global-header">
    <div class="brand-area">
        <span style="font-size:30px;">⚡</span>
        <div>
            <div class="brand-title">Bedülonca SaaS</div>
            <div class="brand-sub">Otonom Kâr Marjı Optimizasyonu · V9</div>
        </div>
    </div>
    <div style="display:flex; gap:12px;">
        <div class="kur-badge">
            <div class="kur-label">Canlı Kur</div>
            <div class="kur-value">₺{current_rate:.4f}</div>
        </div>
        <div class="kur-badge">
            <div class="kur-label">Güncelleme</div>
            <div class="kur-value" style="font-size:13px; padding-top:4px;">
                {datetime.now().strftime('%H:%M')}
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
# BÖLÜM 1: ENVANTER TABLOSU
# ══════════════════════════════════════════════════════════════════════
st.markdown(
    '<div class="section-label">📦 Mevcut Envanter</div>',
    unsafe_allow_html=True,
)

# ── Madde 2: Popover — Tablo İşlemleri ───────────────────────────────
all_categories = sorted(df_inv["Kategori"].unique().tolist())

with st.popover("⚙️ Tablo İşlemleri", use_container_width=False):
    st.markdown("**🗂️ Kategori Filtresi**")
    sel_categories = st.multiselect(
        "Kategori seç",
        options=all_categories,
        default=all_categories,
        key="cat_filter",
        label_visibility="collapsed",
    )

    st.markdown("**🔎 Durum Filtresi**")
    status_filter = st.selectbox(
        "Durum",
        options=[
            "Tümü",
            "Sadece kâr edenler",
            "Sadece zarar edenler",
            "Aylık satışı ortalamanın üstünde",
            "Kritik stok (≤2 hafta)",
            "Stok fazlası (≥12 hafta)",
        ],
        key="status_filter",
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown("**📥 CSV İndir**")

    # CSV için filtresiz tüm veriyi ver (isteğe göre filtrelenmiş de olabilir)
    df_csv_export = df_inv.copy()
    df_csv_export["Aksiyon"] = df_inv["SKU"].apply(
        lambda s: f"https://bedülonca.app/product_detail?sku={s}"
    )
    export_cols = [
        "Aksiyon", "SKU", "Ürün Adı", "Kategori", "Stok",
        "Aylık Satış", "Mevcut Fiyat", "FIFO Maliyet",
        "Satış Kârı (TL)", "Marj %", "Durum/Öneri",
    ]
    csv_buffer = io.StringIO()
    # Madde 2: sep=';' ve utf-8-sig encoding
    df_csv_export[export_cols].to_csv(
        csv_buffer, index=False, sep=";", encoding="utf-8-sig"
    )
    csv_bytes = csv_buffer.getvalue().encode("utf-8-sig")

    st.download_button(
        label="⬇️ Envanteri İndir (.csv)",
        data=csv_bytes,
        file_name=f"envanter_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        use_container_width=True,
    )

# ── Filtre uygulama ───────────────────────────────────────────────────
df_filtered = df_inv.copy()

# Kategori filtresi
if sel_categories:
    df_filtered = df_filtered[df_filtered["Kategori"].isin(sel_categories)]

# Durum filtresi
avg_monthly = df_filtered["Aylık Satış"].mean() if not df_filtered.empty else 0

if status_filter == "Sadece kâr edenler":
    df_filtered = df_filtered[df_filtered["_margin_raw"] > 0]
elif status_filter == "Sadece zarar edenler":
    df_filtered = df_filtered[df_filtered["_margin_raw"] <= 0]
elif status_filter == "Aylık satışı ortalamanın üstünde":
    df_filtered = df_filtered[df_filtered["Aylık Satış"] > avg_monthly]
elif status_filter == "Kritik stok (≤2 hafta)":
    df_filtered = df_filtered[
        df_filtered["Durum/Öneri"].str.contains("Acil|sipariş önerilir", na=False)
    ]
elif status_filter == "Stok fazlası (≥12 hafta)":
    df_filtered = df_filtered[
        df_filtered["Durum/Öneri"].str.contains("Fazla|Tasfiye", na=False)
    ]

# ── Görüntülenecek sütunlar ───────────────────────────────────────────
display_cols = [
    "Aksiyon", "SKU", "Ürün Adı", "Kategori",
    "Stok", "Aylık Satış", "Mevcut Fiyat",
    "FIFO Maliyet", "Satış Kârı (TL)", "Marj %",
    "Durum/Öneri",
]
df_display = df_filtered[display_cols].copy()


def _color_row(row):
    m = row["Marj %"]
    if m < 0:
        color = COLOR_RED
    elif m < 12:
        color = COLOR_YELLOW
    else:
        color = COLOR_GREEN
    return [f"color: {color}"] * len(row)


styled_df = (
    df_display.style
    .apply(_color_row, axis=1)
    .format({
        "Mevcut Fiyat":     "₺{:,.0f}",
        "FIFO Maliyet":     "₺{:,.0f}",
        "Satış Kârı (TL)":  "₺{:,.0f}",
        "Marj %":           "{:.1f}%",
    })
)

st.dataframe(
    styled_df,
    use_container_width=True,
    hide_index=True,
    height=480,
    column_config={
        "Aksiyon": st.column_config.LinkColumn(
            label="🔍 İncele",
            display_text="🔍 İncele",
            help="Ürün detay sayfasına git",
            validate=r"^/product_detail\?sku=.+$",
        ),
        "SKU":      st.column_config.TextColumn("SKU",      width="medium"),
        "Ürün Adı": st.column_config.TextColumn("Ürün Adı", width="large"),
        "Mevcut Fiyat": st.column_config.NumberColumn(
            "Mevcut Fiyat", format="₺%.0f"
        ),
        "FIFO Maliyet": st.column_config.NumberColumn(
            "FIFO Maliyet", format="₺%.0f"
        ),
        "Satış Kârı (TL)": st.column_config.NumberColumn(
            "Satış Kârı", format="₺%.0f"
        ),
        "Marj %": st.column_config.NumberColumn(
            "Marj %", format="%.1f%%"
        ),
        "Durum/Öneri": st.column_config.TextColumn(
            "Durum / Stok Önerisi", width="large"
        ),
    },
)

# ── Madde 4 & 5: Özet Metrikler (Tooltips + Kritik Stok Linkleri) ────
st.markdown("<hr class='divider'>", unsafe_allow_html=True)

total_monthly_profit = sum(
    (p["our_price_tl"] - get_fifo_cost_tl(p, current_rate))
    * p.get("sales_per_week", 0) * 4
    for p in data["products"]
)

# Kritik ürünleri tespit et
critical_products = [
    p for p in data["products"]
    if p.get("sales_per_week", 0) > 0
    and (p["stock_qty"] / p["sales_per_week"]) < 2
]
critical_count = len(critical_products)

m1, m2, m3, m4, m5 = st.columns(5)

with m1:
    st.metric(
        "Toplam Ürün",
        len(data["products"]),
        help="Sistemde kayıtlı toplam SKU sayısı.",
    )
with m2:
    st.metric(
        "Toplam Stok",
        sum(p["stock_qty"] for p in data["products"]),
        help="Tüm ürünlerin depodaki toplam stok adedi.",
    )
with m3:
    st.metric(
        "USD/TRY",
        f"₺{current_rate:.2f}",
        help="Open Exchange Rates'ten çekilen canlı kur. 10 dakikada bir güncellenir.",
    )
with m4:
    st.metric(
        "Aylık Tahmini Kâr",
        fmt_tl(total_monthly_profit),
        help="Bu hesaplama vergiler hariç brüt kârı gösterir. "
             "FIFO maliyet × mevcut satış hızı × 4 hafta formülü kullanılır.",
    )
with m5:
    st.metric(
        "Kritik Stok",
        f"{critical_count} ürün",
        delta="⚠️ acil" if critical_count > 0 else None,
        delta_color="inverse",
        help="Mevcut satış hızında 2 haftadan az stoğu kalan ürünler.",
    )

# Madde 5: Kritik ürünlerin isimleri ve linkleri
if critical_count > 0:
    link_parts = []
    for p in critical_products:
        sku  = p["sku"]
        name = p["name"]
        link_parts.append(
            f'<a href="/product_detail?sku={sku}" target="_self">{name}</a>'
        )
    links_html = " &nbsp;|&nbsp; ".join(link_parts)
    st.markdown(
        f'<div class="critical-link" style="font-size:12px; margin-top:-8px; '
        f'padding: 6px 0 0 0; color:#FF4B4B;">'
        f'⚠️ Kritik ürünler: {links_html}</div>',
        unsafe_allow_html=True,
    )

st.markdown("<hr class='divider'>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
# BÖLÜM 2: CEO DASHBOARD  (Madde 9: Filtre + yeni grafikler)
# ══════════════════════════════════════════════════════════════════════
st.markdown(
    '<div class="section-label">📊 CEO Dashboard — Kurumsal Analitik</div>',
    unsafe_allow_html=True,
)

# ── Dashboard filtre çubuğu ───────────────────────────────────────────
dash_col1, dash_col2, dash_col3 = st.columns([2, 2, 1])

with dash_col1:
    dash_categories = st.multiselect(
        "📂 Kategori Filtresi",
        options=all_categories,
        default=all_categories,
        key="dash_cat",
        placeholder="Tüm kategoriler",
    )

with dash_col2:
    dash_period = st.selectbox(
        "📅 Dönem (Trend Grafiği)",
        options=["Son 1 Hafta", "Son 4 Hafta", "Son 12 Hafta", "Tüm Zamanlar"],
        index=1,
        key="dash_period",
    )

with dash_col3:
    dash_top_n = st.number_input(
        "🔢 Trend'de maks ürün",
        min_value=2,
        max_value=12,
        value=6,
        step=1,
        key="dash_top_n",
    )

period_map = {
    "Son 1 Hafta": 1,
    "Son 4 Hafta": 4,
    "Son 12 Hafta": 12,
    "Tüm Zamanlar": 24,
}
period_weeks = period_map[dash_period]

# Kategoriye göre filtrelenmiş SKU listesi
if dash_categories:
    dash_skus = [
        p["sku"] for p in data["products"]
        if p["category"].replace("_", " ").title() in dash_categories
    ]
else:
    dash_skus = [p["sku"] for p in data["products"]]

# ── Grafik satırı 1 ───────────────────────────────────────────────────
col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.markdown('<div class="chart-title">📦 Haftalık Satış Hızı</div>',
                unsafe_allow_html=True)
    render_sales_volume_pie(data, filtered_skus=dash_skus)

    st.markdown('<div class="chart-title">📂 Kategori Kâr Dağılımı</div>',
                unsafe_allow_html=True)
    render_category_profit_bar(data, current_rate, filtered_skus=dash_skus)

with col_right:
    st.markdown('<div class="chart-title">🎯 BCG Matrisi</div>',
                unsafe_allow_html=True)
    render_bcg_scatter(data, current_rate, filtered_skus=dash_skus)

# ── Grafik satırı 2 (yeni) ────────────────────────────────────────────
st.markdown("<hr class='divider'>", unsafe_allow_html=True)

col_r1, col_r2 = st.columns([1, 1], gap="large")

with col_r1:
    st.markdown('<div class="chart-title">⚠️ Risk Matrisi — Marj vs Stok</div>',
                unsafe_allow_html=True)
    render_risk_scatter(data, current_rate, filtered_skus=dash_skus)

with col_r2:
    st.markdown('<div class="chart-title">📈 Satış Hızı Trendi</div>',
                unsafe_allow_html=True)
    render_sales_trend_line(
        data,
        filtered_skus=dash_skus,
        period_weeks=period_weeks,
    )

# ── Grafik satırı 3 (tahmini kâr) ────────────────────────────────────
st.markdown(
    '<div class="chart-title">💰 Ay Sonu Tahmini Kâr Projeksiyonu</div>',
    unsafe_allow_html=True,
)
render_projected_profit_bar(data, current_rate, filtered_skus=dash_skus)

st.markdown("<hr class='divider'>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
# BÖLÜM 3: YAPAY ZEKA ANALİZİ  (Madde 7: Spinner)
# ══════════════════════════════════════════════════════════════════════
st.markdown(
    '<div class="section-label">🎯 LangGraph & Gemini Karar Motoru</div>',
    unsafe_allow_html=True,
)

c_input, c_btn = st.columns([4, 1])
with c_input:
    trigger_event = st.text_input(
        "Olay",
        value="Haftalık fiyat ve kur optimizasyonu",
        label_visibility="collapsed",
    )
with c_btn:
    btn_label_ai = (
        "🔄 Analizi Yenile"
        if st.session_state["analysis_result"] is not None
        else "⚡ Otonom Analizi Başlat"
    )
    run_button = st.button(btn_label_ai, type="primary", use_container_width=True)

# ── Yeni analiz tetiklendi ────────────────────────────────────────────
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

    with st.spinner("🤖 Ajan zinciri çalışıyor, lütfen bekleyin..."):
        with st.status("Analiz aşamaları:", expanded=True) as status:
            st.write("📈 Trend verileri taranıyor...")
            st.write("📰 Piyasa haberleri çekiliyor...")
            st.write("🕸️ Rakip fiyatları analiz ediliyor...")
            st.write("💰 FIFO maliyet hesaplaması yapılıyor...")
            st.write("🧠 Gemini V9 strateji motoru devreye giriyor...")
            result = get_graph().invoke(initial_state)
            st.session_state["analysis_result"] = result
            status.update(
                label="✅ Analiz tamamlandı.",
                state="complete",
                expanded=False,
            )

# ── Hafızada sonuç varsa hemen çiz ───────────────────────────────────
if st.session_state["analysis_result"] is not None:
    render_analysis_result(st.session_state["analysis_result"])