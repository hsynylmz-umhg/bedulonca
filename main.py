# main.py
import json
import io
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
import requests

from agent_graph import build_graph
from state import AgentState

DATA_PATH = Path(__file__).parent / "data" / "mock_data.json"

# ── Sayfa Yapılandırması ──────────────────────────────────────────────
st.set_page_config(
    page_title="Bedülonca | Kâr Marjı Optimizasyonu",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Global CSS ────────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #0d0f18; }
    .block-container { padding: 2rem 3rem 3rem 3rem !important; }

    .brand-header { display: flex; align-items: center; gap: 14px; margin-bottom: 20px; }
    .brand-title  { font-size: 32px; font-weight: 800; color: #ffffff; letter-spacing: -0.5px; }
    .brand-sub    { font-size: 13px; color: #00FF94; letter-spacing: 1px;
                    text-transform: uppercase; font-weight: 600; }

    .section-label {
        font-size: 13px; font-weight: 700; letter-spacing: 1.5px;
        text-transform: uppercase; color: #f8fafc;
        margin-bottom: 15px; margin-top: 30px;
        border-bottom: 1px solid #1f2333; padding-bottom: 8px;
    }
    .divider { border: none; border-top: 1px solid #1f2333; margin: 20px 0; }

    [data-testid="stMetric"] {
        background: #141724;
        border: 1px solid #1f2333;
        border-radius: 10px;
        padding: 14px 18px;
    }
    [data-testid="stMetricLabel"] { color: #94a3b8 !important; font-size: 12px !important; }
    [data-testid="stMetricValue"] { color: #f1f5f9 !important; font-size: 22px !important; }

    .action-card     { border-radius: 10px; padding: 16px 18px; margin-bottom: 12px; }
    .action-critical { background: rgba(255,75,75,0.10); border: 1px solid rgba(255,75,75,0.35); }
    .action-bundle   { background: rgba(0,255,148,0.07); border: 1px solid rgba(0,255,148,0.30); }
    .action-hold     { background: rgba(100,116,139,0.12); border: 1px solid rgba(100,116,139,0.30); }
    .action-title    { font-size: 15px; font-weight: 700; color: #f1f5f9; margin-bottom: 4px; }
    .action-detail   { font-size: 13px; color: #cbd5e1; margin-bottom: 6px; }
    .action-reason   { font-size: 13px; color: #94a3b8; font-style: italic; margin-bottom: 10px; }
    .price-arrow     { color: #FF4B4B; font-weight: 700; }
    .price-up        { color: #FF4B4B; }
    .price-hold      { color: #94a3b8; }

    [data-testid="stDataFrame"]  { border: 1px solid #1f2333; border-radius: 10px; overflow: hidden; }
    [data-testid="stStatus"]     {
        background: #141724 !important;
        border: 1px solid #1f2333 !important;
        border-radius: 10px !important;
    }

    div[data-testid="stButton"] > button[kind="primary"] {
        background: #00FF94; color: #0d0f18; font-weight: 700;
        border: none; border-radius: 8px; padding: 10px 0;
        width: 100%; font-size: 14px; transition: opacity .2s;
    }
    div[data-testid="stButton"] > button[kind="primary"]:hover { opacity: 0.85; }

    [data-testid="stTabs"] [data-baseweb="tab-list"] {
        background: transparent;
        border-bottom: 1px solid #1f2333;
        gap: 4px;
    }
    [data-testid="stTabs"] [data-baseweb="tab"] {
        background: transparent !important;
        color: #94a3b8 !important;
        font-size: 13px !important;
        font-weight: 600 !important;
        border-radius: 6px 6px 0 0 !important;
        padding: 8px 16px !important;
    }
    [data-testid="stTabs"] [aria-selected="true"] {
        background: #1f2333 !important;
        color: #00FF94 !important;
        border-bottom: 2px solid #00FF94 !important;
    }

    .chart-title {
        font-size: 13px; font-weight: 700; color: #94a3b8;
        letter-spacing: 1px; text-transform: uppercase;
        margin-bottom: 8px; margin-top: 16px;
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


def _base_layout(height: int = 320, title_text: str = "") -> dict:
    """
    Her grafik için tekrar kullanılabilir temel layout dict'i döndürür.
    xaxis / yaxis BULUNDURMAZ — her fonksiyon kendi eksen ayarını
    update_layout'a ayrıca geçer. Böylece 'multiple values' hatası oluşmaz.
    """
    layout = dict(
        paper_bgcolor=BG_PAPER,
        plot_bgcolor=BG_PLOT,
        font=dict(color="#94a3b8", size=12),
        margin=dict(l=10, r=10, t=40, b=10),
        height=height,
        legend=dict(
            orientation="h",
            y=1.12,
            font=dict(color="#cbd5e1"),
            bgcolor="rgba(0,0,0,0)",
        ),
    )
    if title_text:
        layout["title"] = dict(
            text=title_text,
            font=dict(color="#cbd5e1", size=13),
            x=0,
        )
    return layout


# ── Cache ─────────────────────────────────────────────────────────────
@st.cache_resource
def get_graph():
    return build_graph()


@st.cache_data
def load_mock_data() -> dict:
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Canlı Kur Ajanı ──────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def fetch_live_usd_rate(fallback_rate: float) -> float:
    try:
        url = "https://open.er-api.com/v6/latest/USD"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        return float(resp.json()["rates"]["TRY"])
    except Exception as e:
        print(f"⚠️ Canlı kur ajanı başarısız: {e}")
        return fallback_rate


# ── Yardımcı Fonksiyonlar ─────────────────────────────────────────────
def fmt_tl(value: float) -> str:
    return f"₺{value:,.0f}".replace(",", ".")


def calc_fx_cost(product: dict, current_usd_rate: float) -> dict:
    if product.get("buy_currency") == "USD":
        buy_rate      = product["buy_exchange_rate"]
        buy_usd       = product["buy_price"]
        original_tl   = buy_usd * buy_rate
        current_tl    = buy_usd * current_usd_rate
        fx_diff       = current_tl - original_tl
        fx_diff_pct   = round((fx_diff / original_tl) * 100, 2) if original_tl else 0
        return {
            "original_cost_tl": round(original_tl, 2),
            "current_cost_tl":  round(current_tl, 2),
            "fx_diff_tl":       round(fx_diff, 2),
            "fx_diff_pct":      fx_diff_pct,
            "has_fx_risk":      fx_diff > 0,
        }
    return {
        "original_cost_tl": product["cost_price_tl"],
        "current_cost_tl":  product["cost_price_tl"],
        "fx_diff_tl":       0,
        "fx_diff_pct":      0.0,
        "has_fx_risk":      False,
    }


def build_inventory_df(data: dict, current_usd_rate: float) -> pd.DataFrame:
    rows = []
    for p in data["products"]:
        fx          = calc_fx_cost(p, current_usd_rate)
        monthly_qty = p.get("sales_per_week", 0) * 4
        profit_tl   = p["our_price_tl"] - fx["current_cost_tl"]
        rows.append({
            "SKU":             p["sku"],
            "Ürün Adı":        p["name"],
            "Kategori":        p["category"].replace("_", " ").title(),
            "Stok":            p["stock_qty"],
            "Aylık Satış":     monthly_qty,
            "Mevcut Fiyat":    p["our_price_tl"],
            "Satış Kârı (TL)": round(profit_tl, 0),
        })
    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════════════
# MODAL: ÜRÜN DETAY POP-UP
# ══════════════════════════════════════════════════════════════════════
@st.dialog("Ürün Analiz ve Detay Sayfası", width="large")
def show_product_modal(product: dict, current_usd_rate: float) -> None:
    fx           = calc_fx_cost(product, current_usd_rate)
    net_fiyat    = product["our_price_tl"] / 1.20
    kdv_tutari   = product["our_price_tl"] - net_fiyat
    history      = product.get("monthly_history", [])

    st.markdown(f"### {product['name']}")
    st.caption(
        f"**SKU:** `{product['sku']}` | "
        f"**Kategori:** {product['category'].replace('_', ' ').title()}"
    )
    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    # ── Stok & Satış Hızı ────────────────────────────────────────────
    st.markdown("**📦 Stok ve Satış Hızı Algoritması**")
    stock        = product["stock_qty"]
    weekly_sales = product.get("sales_per_week", 0)

    if weekly_sales > 0:
        weeks_left  = stock / weekly_sales
        days_left   = int(weeks_left * 7)
        runout_date = (datetime.now() + timedelta(days=days_left)).strftime("%d.%m.%Y")
        if weeks_left <= 2:
            stock_status = f"🔴 Acil Yenile (Tükenme: {runout_date})"
        elif weeks_left <= 4:
            stock_status = f"🟡 Yakında Yenile (Tükenme: {runout_date})"
        else:
            stock_status = f"🟢 Sağlıklı (Tükenme: {runout_date})"
    else:
        stock_status = "⚫ Yavaş Satış (Yenileme Önerilmiyor)"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Mevcut Stok",    f"{stock} adet")
    c2.metric("Stoka Giriş",    product.get("buy_date", "—"))
    c3.metric("Satış Hızı",     f"{weekly_sales} adet/hafta")
    c4.metric("Sistem Önerisi", stock_status)
    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    # ── Fiyat & Vergi ─────────────────────────────────────────────────
    st.markdown("**💰 Fiyat ve Vergi Dağılımı**")
    fc1, fc2, fc3 = st.columns(3)
    fc1.metric("Net Fiyat (KDV Hariç)", fmt_tl(net_fiyat))
    fc2.metric("%20 KDV Tutarı",        fmt_tl(kdv_tutari))
    fc3.metric("Müşteri Satış Fiyatı",  fmt_tl(product["our_price_tl"]))
    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    # ── Kur Koruması ──────────────────────────────────────────────────
    st.markdown("**💱 Kur Koruması ve Maliyet Analizi**")
    if product.get("buy_currency") == "USD":
        kc1, kc2, kc3, kc4 = st.columns(4)
        kc1.metric("Alım Kuru",        f"₺{product['buy_exchange_rate']:.2f}")
        kc2.metric("Güncel Kur",       f"₺{current_usd_rate:.2f}")
        kc3.metric("Orijinal Maliyet", fmt_tl(fx["original_cost_tl"]))
        delta_str = (
            f"{'+' if fx['fx_diff_tl'] > 0 else ''}"
            f"{fx['fx_diff_tl']:,.0f} TL "
            f"({fx['fx_diff_pct']:+.1f}%)"
        ).replace(",", ".")
        kc4.metric("Güncel TL Maliyet", fmt_tl(fx["current_cost_tl"]),
                   delta=delta_str, delta_color="inverse")
        if fx["has_fx_risk"]:
            st.warning(
                f"⚠️ Kur farkından dolayı maliyetiniz {fmt_tl(fx['fx_diff_tl'])} "
                "artmıştır. Fiyatlama yaparken **Güncel TL Maliyeti** baz alınmalıdır."
            )
    else:
        st.info("Bu ürün TL üzerinden alınmıştır. Doğrudan kur riski yoktur.")

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    # ── Tarihsel Grafikler ────────────────────────────────────────────
    if not history:
        st.info("Bu ürün için tarihsel grafik verisi bulunamadı.")
        return

    st.markdown("**📊 Geçmiş Performans Grafikleri**")

    months     = [h["month"]             for h in history]
    prices     = [h["price"]             for h in history]
    sales_qtys = [h["sales_qty"]         for h in history]
    margins    = [h["profit_margin_pct"] for h in history]

    tab_price, tab_sales, tab_margin = st.tabs([
        "📈 Fiyat Geçmişi",
        "📦 Satış Hacmi",
        "💹 Kâr Marjı",
    ])

    # Tab 1 — Fiyat Çizgi ─────────────────────────────────────────────
    with tab_price:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=months, y=prices,
            mode="lines+markers",
            name="Satış Fiyatı",
            line=dict(color=COLOR_GREEN, width=2.5),
            marker=dict(size=8, color=COLOR_GREEN,
                        line=dict(color="#0d0f18", width=2)),
            fill="tozeroy",
            fillcolor="rgba(0,255,148,0.06)",
            hovertemplate="<b>%{x}</b><br>Fiyat: ₺%{y:,.0f}<extra></extra>",
        ))
        fig.update_layout(
            paper_bgcolor=BG_PAPER,
            plot_bgcolor=BG_PLOT,
            font=dict(color="#94a3b8", size=12),
            margin=dict(l=10, r=10, t=40, b=10),
            height=260,
            showlegend=False,
            title=dict(text="Aylık Satış Fiyatı Değişimi",
                       font=dict(color="#cbd5e1", size=13), x=0),
            xaxis=dict(gridcolor=GRID_COLOR,
                       tickfont=dict(color="#cbd5e1")),
            yaxis=dict(gridcolor=GRID_COLOR,
                       tickprefix="₺", tickformat=",.0f",
                       tickfont=dict(color="#94a3b8")),
        )
        st.plotly_chart(fig, use_container_width=True)

    # Tab 2 — Satış Bar ───────────────────────────────────────────────
    with tab_sales:
        avg_sales  = sum(sales_qtys) / len(sales_qtys) if sales_qtys else 0
        bar_colors = [
            COLOR_GREEN  if q == max(sales_qtys)
            else COLOR_YELLOW if q >= avg_sales
            else COLOR_RED
            for q in sales_qtys
        ]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=months, y=sales_qtys,
            name="Satış Adedi",
            marker_color=bar_colors,
            text=sales_qtys,
            textposition="outside",
            textfont=dict(color="#e2e8f0", size=11),
            hovertemplate="<b>%{x}</b><br>Satış: %{y} adet<extra></extra>",
        ))
        fig.update_layout(
            paper_bgcolor=BG_PAPER,
            plot_bgcolor=BG_PLOT,
            font=dict(color="#94a3b8", size=12),
            margin=dict(l=10, r=10, t=40, b=10),
            height=260,
            showlegend=False,
            title=dict(text="Aylık Satış Adedi",
                       font=dict(color="#cbd5e1", size=13), x=0),
            xaxis=dict(gridcolor=GRID_COLOR,
                       tickfont=dict(color="#cbd5e1")),
            yaxis=dict(gridcolor=GRID_COLOR,
                       ticksuffix=" adet",
                       tickfont=dict(color="#94a3b8")),
        )
        st.plotly_chart(fig, use_container_width=True)

    # Tab 3 — Kâr Marjı Alan ──────────────────────────────────────────
    with tab_margin:
        marker_colors = [
            COLOR_RED    if m < 0
            else COLOR_YELLOW if m < 12
            else COLOR_GREEN
            for m in margins
        ]
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=months, y=margins,
            mode="lines+markers",
            name="Kâr Marjı %",
            line=dict(color=COLOR_PURPLE, width=2.5),
            marker=dict(size=9, color=marker_colors,
                        line=dict(color="#0d0f18", width=2)),
            fill="tozeroy",
            fillcolor="rgba(129,140,248,0.10)",
            hovertemplate="<b>%{x}</b><br>Marj: %{y:.1f}%<extra></extra>",
        ))
        fig.add_hline(
            y=0, line_dash="dash", line_color=COLOR_RED, opacity=0.6,
            annotation_text="Zarar Sınırı",
            annotation_font_color=COLOR_RED,
            annotation_position="bottom right",
        )
        fig.add_hline(
            y=12, line_dash="dot", line_color=COLOR_YELLOW, opacity=0.5,
            annotation_text="Min. Hedef (%12)",
            annotation_font_color=COLOR_YELLOW,
            annotation_position="top right",
        )
        fig.update_layout(
            paper_bgcolor=BG_PAPER,
            plot_bgcolor=BG_PLOT,
            font=dict(color="#94a3b8", size=12),
            margin=dict(l=10, r=10, t=40, b=10),
            height=260,
            showlegend=False,
            title=dict(text="Aylık Kâr Marjı Değişimi",
                       font=dict(color="#cbd5e1", size=13), x=0),
            xaxis=dict(gridcolor=GRID_COLOR,
                       tickfont=dict(color="#cbd5e1")),
            yaxis=dict(gridcolor=GRID_COLOR,
                       ticksuffix="%",
                       tickfont=dict(color="#94a3b8")),
        )
        st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════
# GRAFİK FONKSİYONLARI (ANA SAYFA)
# ══════════════════════════════════════════════════════════════════════

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
        name="Mevcut Fiyat",
        x=short_skus, y=our_prices,
        marker_color=bar_colors, opacity=0.9,
        text=[fmt_tl(v) for v in our_prices],
        textposition="outside",
        textfont=dict(color="#e2e8f0", size=11),
    ))
    fig.add_trace(go.Bar(
        name="Kırmızı Çizgi (Zarar)",
        x=short_skus, y=red_lines,
        marker_color="rgba(255,75,75,0.20)",
        marker_line=dict(color=COLOR_RED, width=2),
        text=[fmt_tl(v) for v in red_lines],
        textposition="outside",
        textfont=dict(color=COLOR_RED, size=11),
    ))
    fig.update_layout(
        paper_bgcolor=BG_PAPER,
        plot_bgcolor=BG_PLOT,
        font=dict(color="#94a3b8", size=12),
        margin=dict(l=10, r=10, t=40, b=10),
        height=370,
        barmode="group",
        legend=dict(orientation="h", y=1.12,
                    font=dict(color="#cbd5e1"),
                    bgcolor="rgba(0,0,0,0)"),
        title=dict(text="Mevcut Fiyat vs Kırmızı Çizgi",
                   font=dict(color="#cbd5e1", size=13), x=0),
        xaxis=dict(gridcolor=GRID_COLOR, tickfont=dict(color="#cbd5e1")),
        yaxis=dict(gridcolor=GRID_COLOR, tickprefix="₺",
                   tickformat=",.0f", tickfont=dict(color="#94a3b8")),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_sales_volume_pie(data: dict) -> None:
    products = data["products"]
    labels   = [" ".join(p["name"].split()[:2]) for p in products]
    values   = [p.get("sales_per_week", 0)       for p in products]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.42,
        marker=dict(
            colors=px.colors.qualitative.Dark24,
            line=dict(color="#0d0f18", width=2),
        ),
        textfont=dict(size=11, color="#e2e8f0"),
        hovertemplate=(
            "%{label}<br>"
            "Haftalık Satış: %{value} adet<br>"
            "%{percent}<extra></extra>"
        ),
    ))
    fig.update_layout(
        paper_bgcolor=BG_PAPER,
        showlegend=False,
        margin=dict(l=0, r=0, t=10, b=0),
        height=280,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_category_profit_bar(data: dict, current_usd_rate: float) -> None:
    cat_profit: dict[str, float] = {}
    for p in data["products"]:
        fx           = calc_fx_cost(p, current_usd_rate)
        unit_profit  = p["our_price_tl"] - fx["current_cost_tl"]
        monthly_qty  = p.get("sales_per_week", 0) * 4
        total_profit = unit_profit * monthly_qty
        cat          = p["category"].replace("_", " ").title()
        cat_profit[cat] = cat_profit.get(cat, 0) + total_profit

    sorted_items = sorted(cat_profit.items(), key=lambda x: x[1], reverse=True)
    cats         = [item[0] for item in sorted_items]
    profits      = [item[1] for item in sorted_items]
    bar_colors   = [
        COLOR_GREEN  if v > 50000
        else COLOR_YELLOW if v > 20000
        else COLOR_RED
        for v in profits
    ]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=cats,
        y=profits,
        marker_color=bar_colors,
        opacity=0.88,
        text=[fmt_tl(v) for v in profits],
        textposition="outside",
        textfont=dict(color="#e2e8f0", size=10),
        hovertemplate="<b>%{x}</b><br>Toplam Kâr: ₺%{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor=BG_PAPER,
        plot_bgcolor=BG_PLOT,
        font=dict(color="#94a3b8", size=12),
        margin=dict(l=10, r=10, t=40, b=30),
        height=320,
        showlegend=False,
        title=dict(text="Kategori Bazlı Aylık Toplam Kâr",
                   font=dict(color="#cbd5e1", size=13), x=0),
        xaxis=dict(
            gridcolor=GRID_COLOR,
            tickfont=dict(color="#cbd5e1", size=10),
            tickangle=-30,
        ),
        yaxis=dict(
            gridcolor=GRID_COLOR,
            tickprefix="₺",
            tickformat=",.0f",
            tickfont=dict(color="#94a3b8"),
        ),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_bcg_scatter(data: dict, current_usd_rate: float) -> None:
    names            = []
    monthly_qty_list = []
    unit_profit_list = []
    stock_list       = []
    category_list    = []

    for p in data["products"]:
        fx          = calc_fx_cost(p, current_usd_rate)
        unit_profit = p["our_price_tl"] - fx["current_cost_tl"]
        monthly_qty = p.get("sales_per_week", 0) * 4
        names.append(p["name"])
        monthly_qty_list.append(monthly_qty)
        unit_profit_list.append(unit_profit)
        stock_list.append(max(p["stock_qty"], 1))
        category_list.append(p["category"].replace("_", " ").title())

    max_stock    = max(stock_list)
    bubble_sizes = [max(8, int((s / max_stock) * 60)) for s in stock_list]

    unique_cats = list(set(category_list))
    palette     = px.colors.qualitative.Dark24
    color_map   = {c: palette[i % len(palette)] for i, c in enumerate(unique_cats)}

    fig = go.Figure()

    for cat in unique_cats:
        idx = [i for i, c in enumerate(category_list) if c == cat]
        fig.add_trace(go.Scatter(
            x=[monthly_qty_list[i] for i in idx],
            y=[unit_profit_list[i] for i in idx],
            mode="markers",
            name=cat,
            marker=dict(
                size=[bubble_sizes[i] for i in idx],
                color=color_map[cat],
                opacity=0.80,
                line=dict(color="#0d0f18", width=1),
            ),
            text=[names[i] for i in idx],
            customdata=[[stock_list[i], category_list[i]] for i in idx],
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Aylık Satış: %{x} adet<br>"
                "Birim Kâr: ₺%{y:,.0f}<br>"
                "Stok: %{customdata[0]} adet<br>"
                "Kategori: %{customdata[1]}"
                "<extra></extra>"
            ),
        ))

    # Quadrant referans çizgileri
    avg_x = sum(monthly_qty_list) / len(monthly_qty_list)
    avg_y = sum(unit_profit_list) / len(unit_profit_list)

    fig.add_vline(
        x=avg_x, line_dash="dot", line_color="#334155", opacity=0.7,
        annotation_text=f"Ort. Satış ({avg_x:.0f})",
        annotation_font_color="#64748b",
        annotation_position="top",
    )
    fig.add_hline(
        y=avg_y, line_dash="dot", line_color="#334155", opacity=0.7,
        annotation_text=f"Ort. Kâr ({fmt_tl(avg_y)})",
        annotation_font_color="#64748b",
        annotation_position="right",
    )

    # Quadrant etiketleri
    max_x = max(monthly_qty_list)
    max_y = max(unit_profit_list)
    min_y = min(unit_profit_list)

    fig.add_annotation(x=max_x * 0.88, y=max_y * 0.92,
                       text="⭐ YILDIZLAR", showarrow=False,
                       font=dict(color=COLOR_GREEN, size=11))
    fig.add_annotation(x=max_x * 0.88, y=avg_y * 0.3,
                       text="❓ SORU İŞARETLERİ", showarrow=False,
                       font=dict(color=COLOR_YELLOW, size=11))
    fig.add_annotation(x=avg_x * 0.12, y=max_y * 0.92,
                       text="🐄 NAKİT İNEKLERİ", showarrow=False,
                       font=dict(color=COLOR_BLUE, size=11))
    fig.add_annotation(x=avg_x * 0.12, y=min_y + abs(min_y) * 0.2,
                       text="🐶 KÖPEKLER", showarrow=False,
                       font=dict(color=COLOR_RED, size=11))

    fig.update_layout(
        paper_bgcolor=BG_PAPER,
        plot_bgcolor=BG_PLOT,
        font=dict(color="#94a3b8", size=12),
        margin=dict(l=10, r=10, t=40, b=10),
        height=440,
        title=dict(
            text="BCG Matrisi — Kâr / Hacim / Stok Konumlandırması",
            font=dict(color="#cbd5e1", size=13),
            x=0,
        ),
        legend=dict(
            orientation="v",
            x=1.02, y=1,
            font=dict(color="#cbd5e1", size=10),
            bgcolor="rgba(20,23,36,0.9)",
            bordercolor="#1f2333",
            borderwidth=1,
        ),
        xaxis=dict(
            title=dict(text="Aylık Satış Adedi",
                       font=dict(color="#94a3b8")),
            gridcolor=GRID_COLOR,
            tickfont=dict(color="#cbd5e1"),
        ),
        yaxis=dict(
            title=dict(text="Birim Kâr (TL)",
                       font=dict(color="#94a3b8")),
            gridcolor=GRID_COLOR,
            tickprefix="₺",
            tickformat=",.0f",
            tickfont=dict(color="#94a3b8"),
        ),
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Aksiyon Paneli ────────────────────────────────────────────────────
def render_action_panel(suggested_actions: list) -> None:
    if not suggested_actions:
        st.info("Gemini herhangi bir aksiyon önermedi.")
        return

    type_meta = {
        "price_update":  ("🔴", "Fiyat Düzelt",  "action-critical"),
        "create_bundle": ("🟢", "Bundle Oluştur", "action-bundle"),
        "hold":          ("⚫", "Durumu Koru",    "action-hold"),
    }

    for i, action in enumerate(suggested_actions):
        atype               = action.get("action_type", "hold")
        icon, type_label, css = type_meta.get(
            atype, ("⚪", "Bilinmiyor", "action-hold")
        )
        reason     = action.get("reason", "")
        old_price  = action.get("old_price_tl")
        new_price  = action.get("new_price_tl")
        change_pct = action.get("price_change_pct")
        label      = action.get("button_label", "Aksiyonu Uygula")

        if atype == "price_update" and old_price and new_price:
            sign        = "+" if change_pct and change_pct > 0 else ""
            detail_html = (
                f"<div class='action-detail'>"
                f"Eski: <b>{fmt_tl(old_price)}</b> "
                f"<span class='price-arrow'>➔</span> "
                f"Yeni: <b>{fmt_tl(new_price)}</b> "
                f"<span class='price-up'>({sign}{change_pct:.1f}%)</span>"
                f"</div>"
            )
        elif atype == "create_bundle":
            bp       = action.get("bundle_price_tl", 0)
            skus_str = " + ".join(action.get("skus", []))
            detail_html = (
                f"<div class='action-detail'>"
                f"Paket: <b>{skus_str}</b> → "
                f"Paket Fiyatı: <b>{fmt_tl(bp)}</b>"
                f"</div>"
            )
        else:
            detail_html = (
                f"<div class='action-detail price-hold'>"
                f"Fiyat korunuyor: <b>{fmt_tl(old_price)}</b>"
                f"</div>"
            ) if old_price else ""

        st.markdown(f"""
        <div class="action-card {css}">
            <div class="action-title">
                {icon} {type_label} &nbsp;·&nbsp;
                <code>{action.get('sku', '')}</code>
            </div>
            {detail_html}
            <div class="action-reason">"{reason}"</div>
        </div>
        """, unsafe_allow_html=True)

        if st.button(f"✅ {label}", key=f"act_{i}", use_container_width=True):
            st.success("Sistem emri onaylandı ve işleme alındı.")


# ══════════════════════════════════════════════════════════════════════
# SESSION STATE BAŞLATMA
# ══════════════════════════════════════════════════════════════════════
if "selected_sku" not in st.session_state:
    st.session_state["selected_sku"]      = None
if "modal_just_closed" not in st.session_state:
    st.session_state["modal_just_closed"] = False
if "df_selection_key" not in st.session_state:
    st.session_state["df_selection_key"]  = 0


# ══════════════════════════════════════════════════════════════════════
# VERİ YÜKLEME
# ══════════════════════════════════════════════════════════════════════
data          = load_mock_data()
fallback_rate = data["market_config"]["current_usd_rate"]
current_rate  = fetch_live_usd_rate(fallback_rate)
products_map  = {p["sku"]: p for p in data["products"]}


# ══════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="brand-header">
    <span style="font-size:36px;">⚡</span>
    <div>
        <div class="brand-title">Bedülonca SaaS</div>
        <div class="brand-sub">Otonom Kâr Marjı Optimizasyonu · V8</div>
    </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
# BÖLÜM 1: ENVANTER TABLOSU
# ══════════════════════════════════════════════════════════════════════
st.markdown(
    '<div class="section-label">📦 Mevcut Envanter (Detay için satıra tıklayın)</div>',
    unsafe_allow_html=True,
)

df_inv = build_inventory_df(data, current_rate)

# ── CSV İndirme ───────────────────────────────────────────────────────
csv_buffer = io.StringIO()
df_inv.to_csv(csv_buffer, index=False, encoding="utf-8-sig")
csv_bytes  = csv_buffer.getvalue().encode("utf-8-sig")

_, col_dl = st.columns([5, 1])
with col_dl:
    st.download_button(
        label="📥 CSV İndir",
        data=csv_bytes,
        file_name=f"bedülonca_envanter_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        use_container_width=True,
    )

# ── Seçim Sıfırlama — modal kapandıktan sonra tablo key'i artır ───────
if st.session_state["modal_just_closed"]:
    st.session_state["df_selection_key"] += 1
    st.session_state["modal_just_closed"] = False
    st.session_state["selected_sku"]      = None

table_key = f"inv_table_{st.session_state['df_selection_key']}"

selection_event = st.dataframe(
    df_inv.style.format({
        "Mevcut Fiyat":    "₺{:,.0f}",
        "Satış Kârı (TL)": "₺{:,.0f}",
    }),
    use_container_width=True,
    hide_index=True,
    height=520,
    on_select="rerun",
    selection_mode="single-row",
    key=table_key,
)

# Satır seçildiyse modal aç
if len(selection_event.selection.rows) > 0:
    row_idx      = selection_event.selection.rows[0]
    selected_sku = df_inv.iloc[row_idx]["SKU"]
    if st.session_state["selected_sku"] != selected_sku:
        st.session_state["selected_sku"] = selected_sku
        show_product_modal(products_map[selected_sku], current_rate)
        st.session_state["modal_just_closed"] = True

# ── Özet Metrikler ────────────────────────────────────────────────────
st.markdown("<hr class='divider'>", unsafe_allow_html=True)

total_monthly_profit = sum(
    (p["our_price_tl"] - calc_fx_cost(p, current_rate)["current_cost_tl"])
    * p.get("sales_per_week", 0) * 4
    for p in data["products"]
)
critical_stock_count = sum(
    1 for p in data["products"]
    if p.get("sales_per_week", 0) > 0
    and (p["stock_qty"] / p["sales_per_week"]) < 2
)

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Toplam Ürün Çeşidi",   len(data["products"]))
m2.metric("Depodaki Toplam Stok", sum(p["stock_qty"] for p in data["products"]))
m3.metric("Güncel USD/TRY",       f"₺{current_rate:.2f}")
m4.metric("Aylık Tahmini Kâr",    fmt_tl(total_monthly_profit))
m5.metric(
    "Kritik Stok Ürün",
    f"{critical_stock_count} ürün",
    delta="⚠️ acil yenile" if critical_stock_count > 0 else None,
    delta_color="inverse",
)

st.markdown("<hr class='divider'>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
# BÖLÜM 2: CEO DASHBOARD — KURUMSAL GRAFİKLER
# ══════════════════════════════════════════════════════════════════════
st.markdown(
    '<div class="section-label">📊 CEO Dashboard — Kurumsal Analitik</div>',
    unsafe_allow_html=True,
)

col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.markdown('<div class="chart-title">📦 Haftalık Satış Hızı Dağılımı</div>',
                unsafe_allow_html=True)
    render_sales_volume_pie(data)

    st.markdown('<div class="chart-title">📂 Kategori Bazlı Aylık Kâr</div>',
                unsafe_allow_html=True)
    render_category_profit_bar(data, current_rate)

with col_right:
    st.markdown(
        '<div class="chart-title">'
        '🎯 BCG Matrisi — Kâr / Hacim / Stok'
        '</div>',
        unsafe_allow_html=True,
    )
    render_bcg_scatter(data, current_rate)

st.markdown("<hr class='divider'>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
# BÖLÜM 3: YAPAY ZEKA ANALİZİ
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
    run_button = st.button(
        "⚡ Otonom Analizi Başlat",
        type="primary",
        use_container_width=True,
    )

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
        "errors":              [],
    }

    with st.status("🤖 Ajan zinciri başlatılıyor...", expanded=True) as status:
        st.write("📈 Trend verileri taranıyor...")
        st.write("🕸️ Rakip fiyatları çekiliyor...")
        st.write("💰 Kur korumalı maliyetler hesaplanıyor...")
        st.write("🧠 Gemini mikro-karar motoru devreye giriyor...")
        result = get_graph().invoke(initial_state)
        status.update(
            label="✅ Analiz tamamlandı.",
            state="complete",
            expanded=False,
        )

    if result.get("errors"):
        with st.expander("⚠️ Sistem Uyarıları", expanded=False):
            for err in result["errors"]:
                st.error(err)

    tab_str, tab_chart, tab_act = st.tabs([
        "📑 Strateji Özeti",
        "📊 Durum Grafikleri",
        "🎮 Aksiyon Paneli",
    ])

    with tab_str:
        st.markdown(result.get("final_strategy", "Strateji üretilemedi."))
        if result.get("trend_insights"):
            st.info(result["trend_insights"])

    with tab_chart:
        cost_metrics = result.get("cost_metrics", {})
        if cost_metrics:
            render_price_vs_redline(cost_metrics)
        else:
            st.info("Grafik için cost_metrics verisi bulunamadı.")

    with tab_act:
        render_action_panel(result.get("suggested_actions", []))