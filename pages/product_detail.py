# pages/product_detail.py
"""
Bedülonca V10.4 — Ürün Detay Sayfası (Main.py ile Senkron)
"""

import os
import json
import base64
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import streamlit.components.v1 as components
import requests
import google.generativeai as genai
from dotenv import load_dotenv

# ── Mutlak yol ile .env yükleme ───────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_ENV_PATH   = os.path.join(_SCRIPT_DIR, "..", ".env")
if os.path.exists(_ENV_PATH):
    load_dotenv(dotenv_path=_ENV_PATH)
else:
    load_dotenv()

from agents.cost_agent        import _fifo_cost
from agents.market_news_agent import fetch_intelligence_report

DATA_PATH = Path(_SCRIPT_DIR).parent / "data" / "mock_data.json"

st.set_page_config(
    page_title="Bedülonca | Ürün Detayı",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── GÜVENLİ DEV MENU GİZLEME (JS ENJEKSİYONU) ─────────────────────────
components.html("""
<script>
    const parentDoc = window.parent.document;
    parentDoc.addEventListener('keydown', function(e) {
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'c') {
            const hasSelection = parentDoc.getSelection().toString().length > 0;
            const tag = e.target.tagName.toLowerCase();
            const isEditable = (tag === 'input' || tag === 'textarea' || e.target.isContentEditable);
            if (!hasSelection && !isEditable) {
                e.stopImmediatePropagation();
            }
        }
    }, true);
</script>
""", height=0, width=0)


# ── Global CSS (Main.py ile Birebir Aynı) ────────────────────────────
st.markdown("""
<style>
/* ══════════════════════════════════════════════════════
   LAYER 0 — Font & Icon Imports
══════════════════════════════════════════════════════ */
@import url('https://cdn-uicons.flaticon.com/2.6.0/uicons-regular-rounded/css/uicons-regular-rounded.css');
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ══════════════════════════════════════════════════════
   LAYER 1 — System Chrome Overrides (Main.py ile Aynı)
══════════════════════════════════════════════════════ */
#MainMenu                         { visibility: visible !important; }
footer                            { visibility: hidden  !important; }
[data-testid="stHeader"]          { visibility: hidden  !important; }
[data-testid="stSidebar"]         { display: none       !important; }
[data-testid="stSidebarNav"]      { display: none       !important; }
[data-testid="collapsedControl"]  { display: none       !important; }

/* ══════════════════════════════════════════════════════
   LAYER 2 — Theme-Agnostic Base
══════════════════════════════════════════════════════ */
html, body, .stApp {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}
.block-container {
    padding: 0 2.5rem 3rem 2.5rem !important;
    max-width: 100% !important;
}
a { text-decoration: none !important; }
a:hover { text-decoration: none !important; opacity: 0.75 !important; }

/* ══════════════════════════════════════════════════════
   LAYER 3 — Sticky Top Navbar (Flexbox Redesign)
══════════════════════════════════════════════════════ */
.navbar-outer {
    position: sticky;
    top: 0;
    z-index: 9999;
    background: var(--background-color, inherit);
    padding: 10px 0;
    margin-bottom: 22px;
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
}
.navbar-inner {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;
}
.navbar-logo-img {
    width: 80px;
    height: 80px;
    object-fit: contain;
}
.navbar-brand {
    font-size: 22px;
    font-weight: 800;
    letter-spacing: -0.4px;
    font-family: 'Inter', sans-serif;
}
.navbar-menu {
    display: flex;
    gap: 15px;
    align-items: center;
}
.custom-nav-btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    font-weight: 600;
    color: var(--text-color) !important;
    padding: 8px 14px;
    border-radius: 8px;
    transition: background 0.15s ease;
    font-family: 'Inter', sans-serif;
}
.custom-nav-btn:hover {
    background: rgba(128,128,128,0.1);
    opacity: 1 !important;
}
.custom-nav-btn.active {
    background: rgba(37,99,235,0.10);
    color: #2563EB !important;
}

/* ══════════════════════════════════════════════════════
   LAYER 4 — Section Labels
══════════════════════════════════════════════════════ */
.section-label {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.6px;
    text-transform: uppercase;
    opacity: 0.5;
    margin-bottom: 10px;
    margin-top: 6px;
    border-bottom: 1px solid rgba(128,128,128,0.15);
    padding-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 7px;
}
.section-label .fi { font-size: 14px; opacity: 0.8; }

.detail-header {
    border: 1px solid rgba(128,128,128,0.16);
    border-radius: 10px;
    padding: 16px 22px;
    margin-bottom: 20px;
    background: rgba(128,128,128,0.03);
}
.prod-name { font-size: 22px; font-weight: 800; }
.prod-sku  { font-size: 12px; opacity: 0.6; font-family: monospace; }
.prod-cat  { font-size: 12px; color: #2563EB; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }

/* ══════════════════════════════════════════════════════
   LAYER 5 — Metrics (Main.py ile Birebir Aynı)
══════════════════════════════════════════════════════ */
[data-testid="stMetric"] {
    border: 1px solid rgba(128,128,128,0.16) !important;
    border-radius: 12px !important;
    padding: 14px 18px !important;
}
[data-testid="stMetricLabel"] {
    font-size: 10px !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.8px !important;
    opacity: 0.55 !important;
}
[data-testid="stMetricValue"] { 
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

/* ══════════════════════════════════════════════════════
   LAYER 6 — Tabs
══════════════════════════════════════════════════════ */
[data-testid="stTabs"] [data-baseweb="tab-list"] { 
    background: transparent !important; 
    border-bottom: 1px solid rgba(128,128,128,0.18) !important; 
}
[data-testid="stTabs"] [data-baseweb="tab"] { 
    font-size: 12px !important; 
    font-weight: 600 !important; 
    opacity: 0.6; 
}
[data-testid="stTabs"] [aria-selected="true"] { 
    background: rgba(37,99,235,0.09) !important; 
    color: #2563EB !important; 
    border-bottom: 2px solid #2563EB !important; 
    opacity: 1 !important; 
}

/* ══════════════════════════════════════════════════════
   LAYER 7 — Batch Cards (Geliştirilmiş Tasarım)
══════════════════════════════════════════════════════ */
.batch-card {
    border: 1px solid rgba(128,128,128,0.16);
    background: linear-gradient(135deg, rgba(37,99,235,0.03) 0%, rgba(124,58,237,0.03) 100%);
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 12px;
    transition: all 0.2s ease;
}
.batch-card:hover {
    border-color: rgba(37,99,235,0.3);
    box-shadow: 0 2px 8px rgba(37,99,235,0.08);
    transform: translateY(-1px);
}

.batch-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid rgba(128,128,128,0.12);
}

.batch-id-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(37,99,235,0.1);
    color: #2563EB;
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 700;
    font-family: 'Courier New', monospace;
    letter-spacing: 0.5px;
}

.batch-date {
    font-size: 11px;
    opacity: 0.6;
    font-family: monospace;
}

.batch-details {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px;
}

.batch-detail-item {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.batch-detail-label {
    font-size: 9px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    opacity: 0.5;
}

.batch-detail-value {
    font-size: 14px;
    font-weight: 700;
}

.batch-detail-value.qty { color: #16A34A; }
.batch-detail-value.unit { color: #7C3AED; }
.batch-detail-value.total { color: #DC2626; }

/* ══════════════════════════════════════════════════════
   LAYER 8 — Buttons
══════════════════════════════════════════════════════ */
div[data-testid="stButton"] > button[kind="primary"] {
    background: #2563EB !important;
    color: #FFFFFF !important;
    font-weight: 700 !important;
    border-radius: 8px !important;
    transition: opacity .18s !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover { 
    opacity: 0.86 !important; 
}
div[data-testid="stButton"] > button { 
    font-weight: 600 !important; 
    border-radius: 8px !important; 
    font-size: 13px !important; 
}
</style>
""", unsafe_allow_html=True)

COLOR_GREEN  = "#16A34A"
COLOR_YELLOW = "#CA8A04"
COLOR_RED    = "#DC2626"
COLOR_PURPLE = "#7C3AED"
COLOR_BLUE   = "#2563EB"
BG_PAPER     = "rgba(0,0,0,0)"
BG_PLOT      = "rgba(0,0,0,0)"
GRID_COLOR   = "rgba(148,163,184,0.22)"

# ── WebM Animasyon Render Fonksiyonu ──────────────────────────────────
def render_webm_loader(file_name: str, text: str) -> str:
    """WebM animasyonunu base64 ile yükler ve HTML döndürür."""
    file_path = Path(_SCRIPT_DIR).parent / "assets" / file_name
    if file_path.exists():
        with open(file_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return f'''
            <div style="display:flex; align-items:center; gap:10px; padding:10px; background:rgba(128,128,128,0.05); border-radius:8px; margin-bottom:15px;">
                <video width="40" height="40" autoplay loop muted playsinline style="background:transparent;">
                    <source src="data:video/webm;base64,{b64}" type="video/webm">
                </video>
                <span style="font-family:'Inter'; font-weight:600; font-size:13px; opacity:0.8;">{text}</span>
            </div>
        '''
    return f"<span style='font-family:Inter; font-size:13px; opacity:0.7;'>{text}</span>"

@st.cache_data
def load_data() -> dict:
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

@st.cache_data(ttl=3600)
def fetch_usd_rate(fallback: float) -> float:
    try:
        r = requests.get("https://open.er-api.com/v6/latest/USD", timeout=5)
        r.raise_for_status()
        return float(r.json()["rates"]["TRY"])
    except Exception:
        return fallback

def fmt_tl(v: float) -> str: 
    return f"₺{v:,.0f}".replace(",", ".")

def _sma(series: list, window: int) -> list:
    result = []
    for i in range(len(series)):
        if i < window - 1: 
            result.append(None)
        else: 
            result.append(sum(series[i - window + 1: i + 1]) / window)
    return result

def _linreg_trend(x: list, y: list) -> tuple[list, list]:
    if len(x) < 2: 
        return x, y
    arr_x, arr_y = np.array(x, dtype=float), np.array(y, dtype=float)
    m, b  = np.polyfit(arr_x, arr_y, 1)
    return x, (m * arr_x + b).tolist()

@st.cache_resource
def get_gemini_model():
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key: 
        return None
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-2.0-flash-exp")

def _build_system_prompt(product: dict, fifo_info: dict, usd_rate: float, intel_report: str) -> str:
    batches_str = "\n".join(
        f"  Parti {b.get('batch_id','?')}: {b.get('qty','?')} adet, ${b.get('buy_price_usd','?')} (≈ ₺{b.get('buy_price_usd', 0) * usd_rate:,.0f} güncel kur)"
        for b in product.get("inventory_batches", [])
    ) or "  Parti verisi yok."
    history = product.get("monthly_history", [])
    hist_str = " | ".join(
        f"{h['month']}: ₺{h['price']:,.0f} / {h['sales_qty']} adet / %{h['profit_margin_pct']}" 
        for h in history
    ) or "Tarihsel veri yok."

    return f"""ÖNEMLİ KURAL: Eğer kullanıcının sorusu bir ürün fiyatlandırması, stok durumu, e-ticaret analizi veya maliyeti ile ilgili değilse (örn: 'Kayseri nerede?'), 'Bu soru ürün detayı veya analizi ile ilgili değildir, size e-ticaret verileriniz konusunda yardımcı olmak için buradayım.' diyerek nezaketle reddet.

Sen Bedülonca e-ticaret platformunun kıdemli fiyatlandırma danışmanısın.
Türkçe cevap ver. Kısa ve actionable ol (max 250 kelime). Sayısal veriyle destekle. Kırmızı çizginin altına düşen fiyat ASLA önerme.
SKU: {product['sku']} | Ad: {product['name']} | Mevcut Satış: ₺{product['our_price_tl']:,.0f} | Hız: {product.get('sales_per_week', 0)}/hafta | Stok: {product['stock_qty']}
FIFO Maliyet: ₺{fifo_info['fifo_unit_cost_tl']:,.0f}
Partiler:
{batches_str}
Tarihsel Performans: {hist_str}
Canlı Web İstihbaratı:
{intel_report}
Kullanıcının sorusuna yukarıdaki verileri kullanarak somut öneri sun."""

# ══════════════════════════════════════════════════════════════════════
# VERİ YÜKLEME
# ══════════════════════════════════════════════════════════════════════
data          = load_data()
fallback_rate = data["market_config"]["current_usd_rate"]
usd_rate      = fetch_usd_rate(fallback_rate)
products_map  = {p["sku"]: p for p in data["products"]}
sku_options   = [p["sku"] for p in data["products"]]

# ── Otomatik Ürün Seçimi ──────────────────────────────────────────────
query_sku = st.query_params.get("sku")
if query_sku and query_sku in products_map:
    st.session_state["detail_sku"] = query_sku
else:
    if "detail_sku" not in st.session_state or st.session_state["detail_sku"] not in products_map:
        st.session_state["detail_sku"] = sku_options[0]

selected_sku = st.session_state["detail_sku"]

# ══════════════════════════════════════════════════════════════════════
# ① STICKY TOP NAVBAR & ÜRÜN SEÇİCİ
# ══════════════════════════════════════════════════════════════════════
_logo_path = Path(_SCRIPT_DIR).parent / "assets" / "logo.png"
if os.path.exists(str(_logo_path)):
    with open(_logo_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()
    logo_html = f"<img src='data:image/png;base64,{encoded_string}' class='navbar-logo-img'>"
else:
    logo_html = "<div class='navbar-brand'>Bedülonca</div>"

st.markdown('<div class="navbar-outer"><div class="navbar-inner">', unsafe_allow_html=True)
col_logo, col_sku, col_nav = st.columns([1, 4, 3], vertical_alignment="center")

with col_logo:
    st.markdown(logo_html, unsafe_allow_html=True)

with col_sku:
    new_sku = st.selectbox(
        "İncelenen Ürün", 
        sku_options, 
        index=sku_options.index(selected_sku),
        label_visibility="collapsed"
    )
    if new_sku != selected_sku:
        st.session_state["detail_sku"] = new_sku
        st.rerun()

with col_nav:
    st.markdown("""
        <div class="navbar-menu" style="justify-content: flex-end;">
            <a href="/" target="_self" class="custom-nav-btn"><i class="fi fi-rr-home"></i> Ana Sayfa</a>
            <a href="/product_detail" target="_self" class="custom-nav-btn active"><i class="fi fi-rr-search-alt"></i> Ürün Detayı</a>
            <a href="/settings" target="_self" class="custom-nav-btn"><i class="fi fi-rr-settings"></i> Ayarlar</a>
        </div>
    """, unsafe_allow_html=True)

st.markdown('</div></div>', unsafe_allow_html=True)

# ── Ürün Değişkenleri ─────────────────────────────────────────────────
product      = products_map[selected_sku]
fifo_info    = _fifo_cost(product, usd_rate)
fifo_cost_tl = fifo_info["fifo_unit_cost_tl"]
sell_price   = product["our_price_tl"]
profit_tl    = sell_price - fifo_cost_tl
margin_pct   = round((profit_tl / sell_price) * 100, 2) if sell_price else 0
history      = product.get("monthly_history", [])
batches      = product.get("inventory_batches", [])
weekly_sales = product.get("sales_per_week", 0)
stock_qty    = product["stock_qty"]

chat_key  = f"chat_{selected_sku}"
intel_key = f"intel_{selected_sku}" 
if chat_key not in st.session_state: 
    st.session_state[chat_key] = []

# ══════════════════════════════════════════════════════════════════════
# HEADER (ÜRÜN KARTI)
# ══════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="detail-header">
    <div class="prod-cat">{product['category'].replace('_', ' ').upper()}</div>
    <div class="prod-name">{product['name']}</div>
    <div class="prod-sku">SKU: {product['sku']}</div>
</div>
""", unsafe_allow_html=True)

met1, met2, met3, met4, met5, met6 = st.columns(6)
met1.metric("Satış Fiyatı", fmt_tl(sell_price))
met2.metric("FIFO Maliyet", fmt_tl(fifo_cost_tl))
met3.metric("Birim Kâr",    fmt_tl(profit_tl))
met4.metric(
    "Kâr Marjı", 
    f"{margin_pct:.1f}%", 
    delta="✅ Sağlıklı" if margin_pct >= 12 else "⚠️ Dikkat" if margin_pct >= 0 else "❌ Zarar", 
    delta_color="normal" if margin_pct >= 12 else "inverse"
)
met5.metric("Stok", f"{stock_qty} adet")
met6.metric("Satış Hızı", f"{weekly_sales} adet/hafta")

st.divider()

# ══════════════════════════════════════════════════════════════════════
# ANA İÇERİK
# ══════════════════════════════════════════════════════════════════════
col_charts, col_chat = st.columns([3, 2], gap="large")

with col_charts:
    if not history:
        st.warning("Bu ürün için tarihsel veri bulunamadı.")
    else:
        months = [h["month"] for h in history]
        prices = [h["price"] for h in history]
        sales_qtys = [h["sales_qty"] for h in history]
        margins = [h["profit_margin_pct"] for h in history]
        avg_s = sum(sales_qtys) / len(sales_qtys) if sales_qtys else 1

        tab1, tab2, tab3 = st.tabs(["📈 Fiyat & Marj Geçmişi", "📦 Satış Hacmi + SMA", "💹 Fiyat Esnekliği"])

        with tab1:
            st.markdown('<div class="section-label"><i class="fi fi-rr-chart-line-up"></i> Fiyat ve Kâr Marjı Zaman Serisi</div>', unsafe_allow_html=True)
            fig = make_subplots(
                rows=2, cols=1, 
                shared_xaxes=True, 
                vertical_spacing=0.08, 
                subplot_titles=("Satış Fiyatı (TL)", "Kâr Marjı (%)"), 
                row_heights=[0.65, 0.35]
            )
            fig.add_trace(go.Scatter(
                x=months, y=prices, mode="lines+markers", name="Fiyat", 
                line=dict(color=COLOR_GREEN, width=2.5), 
                marker=dict(size=7, color=COLOR_GREEN, line=dict(color="rgba(0,0,0,0.5)", width=1)), 
                fill="tozeroy", fillcolor="rgba(22,163,74,0.1)", 
                hovertemplate="<b>%{x}</b><br>₺%{y:,.0f}<extra></extra>"
            ), row=1, col=1)
            
            marker_colors_m = [COLOR_RED if m < 0 else COLOR_YELLOW if m < 12 else COLOR_GREEN for m in margins]
            fig.add_trace(go.Scatter(
                x=months, y=margins, mode="lines+markers", name="Marj %", 
                line=dict(color=COLOR_PURPLE, width=2), 
                marker=dict(size=7, color=marker_colors_m, line=dict(color="rgba(0,0,0,0.5)", width=1)), 
                fill="tozeroy", fillcolor="rgba(124,58,237,0.1)", 
                hovertemplate="<b>%{x}</b><br>%{y:.1f}%<extra></extra>"
            ), row=2, col=1)
            
            fig.add_hline(
                y=12, line_dash="dot", line_color=COLOR_YELLOW, opacity=0.5, 
                row=2, col=1, annotation_text="Min. %12", 
                annotation_font_color=COLOR_YELLOW, annotation_position="top right"
            )
            fig.add_hline(y=0, line_dash="dash", line_color=COLOR_RED, opacity=0.4, row=2, col=1)
            
            fig.update_layout(
                paper_bgcolor=BG_PAPER, plot_bgcolor=BG_PLOT, 
                font=dict(family="Inter"), 
                margin=dict(l=10, r=10, t=50, b=10), 
                height=420, showlegend=True, 
                legend=dict(orientation="h", y=1.08, bgcolor="rgba(0,0,0,0)"), 
                xaxis=dict(
                    gridcolor=GRID_COLOR, 
                    rangeselector=dict(
                        buttons=[
                            dict(count=1, label="1A", step="month", stepmode="backward"), 
                            dict(count=3, label="3A", step="month", stepmode="backward"), 
                            dict(count=6, label="6A", step="month", stepmode="backward"), 
                            dict(step="all", label="Tümü")
                        ], 
                        bgcolor="rgba(128,128,128,0.1)", 
                        activecolor="rgba(37,99,235,0.2)", 
                        x=0, y=1.02
                    )
                ), 
                xaxis2=dict(gridcolor=GRID_COLOR), 
                yaxis=dict(gridcolor=GRID_COLOR, tickprefix="₺", tickformat=",.0f"), 
                yaxis2=dict(gridcolor=GRID_COLOR, ticksuffix="%")
            )
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            st.markdown('<div class="section-label"><i class="fi fi-rr-chart-histogram"></i> Satış Hacmi ve Hareketli Ortalamalar</div>', unsafe_allow_html=True)
            sma2, sma3 = _sma(sales_qtys, 2), _sma(sales_qtys, 3)
            bar_colors = [COLOR_GREEN if q == max(sales_qtys) else COLOR_YELLOW if q >= avg_s else COLOR_RED for q in sales_qtys]
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                x=months, y=sales_qtys, name="Satış Adedi", 
                marker_color=bar_colors, opacity=0.80, 
                text=sales_qtys, textposition="outside", 
                hovertemplate="<b>%{x}</b><br>%{y} adet<extra></extra>"
            ))
            fig2.add_trace(go.Scatter(
                x=months, y=sma2, mode="lines", name="SMA-2", 
                line=dict(color=COLOR_YELLOW, width=2, dash="dot"), 
                hovertemplate="SMA-2: %{y:.1f}<extra></extra>", 
                connectgaps=True
            ))
            fig2.add_trace(go.Scatter(
                x=months, y=sma3, mode="lines", name="SMA-3", 
                line=dict(color=COLOR_PURPLE, width=2, dash="dash"), 
                hovertemplate="SMA-3: %{y:.1f}<extra></extra>", 
                connectgaps=True
            ))
            fig2.update_layout(
                paper_bgcolor=BG_PAPER, plot_bgcolor=BG_PLOT, 
                font=dict(family="Inter"), 
                margin=dict(l=10, r=10, t=40, b=10), 
                height=320, barmode="overlay", 
                legend=dict(orientation="h", y=1.12, bgcolor="rgba(0,0,0,0)"), 
                title=dict(text="Aylık Satış + SMA Trend Çizgileri", font=dict(size=13), x=0), 
                xaxis=dict(gridcolor=GRID_COLOR), 
                yaxis=dict(gridcolor=GRID_COLOR, ticksuffix=" adet")
            )
            st.plotly_chart(fig2, use_container_width=True)
            st.caption("SMA-2: 2 aylık · SMA-3: 3 aylık hareketli ortalama")

        with tab3:
            st.markdown('<div class="section-label"><i class="fi fi-rr-chart-scatter-bubble"></i> Fiyat Esnekliği — Fiyat vs Satış Adedi</div>', unsafe_allow_html=True)
            if len(prices) < 2: 
                st.info("Fiyat esnekliği için en az 2 veri noktası gereklidir.")
            else:
                x_idx = list(range(len(prices)))
                _, trend_y = _linreg_trend(x_idx, sales_qtys)
                point_colors = [COLOR_GREEN if q == max(sales_qtys) else COLOR_YELLOW if q >= avg_s else COLOR_RED for q in sales_qtys]
                fig3 = go.Figure()
                fig3.add_trace(go.Scatter(
                    x=prices, y=sales_qtys, mode="markers+text", name="Veri Noktaları", 
                    marker=dict(size=14, color=point_colors, opacity=0.85, line=dict(color="rgba(0,0,0,0.3)", width=1)), 
                    text=months, textposition="top center", textfont=dict(size=10), 
                    hovertemplate="<b>%{text}</b><br>Fiyat: ₺%{x:,.0f}<br>Satış: %{y} adet<extra></extra>"
                ))
                sorted_pairs = sorted(zip(prices, trend_y), key=lambda t: t[0])
                fig3.add_trace(go.Scatter(
                    x=[p[0] for p in sorted_pairs], 
                    y=[p[1] for p in sorted_pairs], 
                    mode="lines", name="Regresyon Trendi", 
                    line=dict(color=COLOR_BLUE, width=2, dash="dot"), 
                    hovertemplate="Trend: %{y:.1f}<extra></extra>"
                ))
                corr = float(np.corrcoef(prices, sales_qtys)[0, 1])
                corr_label = "🟢 Zayıf negatif korelasyon" if corr > -0.3 else "🟡 Orta negatif korelasyon" if corr > -0.7 else "🔴 Güçlü negatif korelasyon"
                fig3.update_layout(
                    paper_bgcolor=BG_PAPER, plot_bgcolor=BG_PLOT, 
                    font=dict(family="Inter"), 
                    margin=dict(l=10, r=10, t=40, b=10), 
                    height=340, 
                    legend=dict(orientation="h", y=1.12, bgcolor="rgba(0,0,0,0)"), 
                    title=dict(text=f"Fiyat Esnekliği | Korelasyon: {corr:.2f}", font=dict(size=13), x=0), 
                    xaxis=dict(title="Satış Fiyatı (TL)", gridcolor=GRID_COLOR, tickprefix="₺", tickformat=",.0f"), 
                    yaxis=dict(title="Satış Adedi", gridcolor=GRID_COLOR)
                )
                st.plotly_chart(fig3, use_container_width=True)
                st.caption(corr_label)

    # ── BATCH CARDS ───────────────────────────────────────────────────
    st.markdown('<div class="section-label"><i class="fi fi-rr-boxes"></i> FIFO Parti (Batch) Detayı</div>', unsafe_allow_html=True)
    if not batches:
        st.info("Parti verisi bulunamadı.")
    else:
        for b in batches:
            batch_id     = b.get('batch_id', '?')
            batch_date   = b.get('buy_date', '?')
            qty          = b.get('qty', 0)
            price_usd    = b.get('buy_price_usd', 0)
            
            # USD ise TL'ye çevir
            if product.get("buy_currency") == "USD":
                unit_price_tl = price_usd * usd_rate
                total_price_tl = qty * unit_price_tl
                unit_display = f"${price_usd:,.0f} → {fmt_tl(unit_price_tl)}"
            else:
                unit_price_tl = price_usd
                total_price_tl = qty * unit_price_tl
                unit_display = fmt_tl(unit_price_tl)
            
            st.markdown(f"""
            <div class="batch-card">
                <div class="batch-header">
                    <div class="batch-id-badge">
                        <i class="fi fi-rr-box"></i> {batch_id}
                    </div>
                    <div class="batch-date">📅 {batch_date}</div>
                </div>
                <div class="batch-details">
                    <div class="batch-detail-item">
                        <div class="batch-detail-label">Miktar</div>
                        <div class="batch-detail-value qty">{qty} adet</div>
                    </div>
                    <div class="batch-detail-item">
                        <div class="batch-detail-label">Birim Fiyat</div>
                        <div class="batch-detail-value unit">{unit_display}</div>
                    </div>
                    <div class="batch-detail-item">
                        <div class="batch-detail-label">Toplam Tutar</div>
                        <div class="batch-detail-value total">{fmt_tl(total_price_tl)}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.caption(f"**FIFO Yöntemi:** `{fifo_info.get('fifo_method','?')}` · **FIFO Birim Maliyet:** {fmt_tl(fifo_cost_tl)}")

with col_chat:
    st.markdown('<div class="section-label"><i class="fi fi-rr-robot"></i> AI Danışman — Canlı İstihbarat + Gemini</div>', unsafe_allow_html=True)

    # ── Canlı İstihbarat Video Yükleyici ──
    if intel_key not in st.session_state:
        intel_loader_ph = st.empty()
        intel_loader_ph.markdown(render_webm_loader("web_intel.webm", "Canlı Web İstihbaratı taranıyor..."), unsafe_allow_html=True)
        st.session_state[intel_key] = fetch_intelligence_report(sku=selected_sku, product_name=product["name"])
        intel_loader_ph.empty()
    
    intel_report = st.session_state[intel_key]

    with st.expander("📡 Canlı Web İstihbaratı", expanded=False):
        st.markdown(intel_report, unsafe_allow_html=True)
        if st.button("🔄 İstihbaratı Yenile", key=f"refresh_intel_{selected_sku}", use_container_width=True):
            del st.session_state[intel_key]
            st.rerun()

    st.markdown("<hr style='margin: 18px 0; opacity: 0.2;'>", unsafe_allow_html=True)

    chat_container = st.container(height=360)
    with chat_container:
        if not st.session_state[chat_key]:
            st.markdown(f"""
                <div style="text-align:center; padding:30px; opacity:0.7;">
                    <div style="font-size:28px; margin-bottom:8px;">🤖</div>
                    <div style="font-size:13px;">
                        Merhaba! Ben Bedülonca AI danışmanıyım.<br>
                        <b>{product['name']}</b> hakkında soru sor.<br>
                        <span style="font-size:11px; opacity:0.8;">(Canlı Google verisi + FIFO maliyet ile yanıtlarım)</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        for msg in st.session_state[chat_key]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    if prompt := st.chat_input(f"{product['name'].split()[0]} hakkında sor...", key=f"chat_input_{selected_sku}"):
        st.session_state[chat_key].append({"role": "user", "content": prompt})
        with chat_container:
            with st.chat_message("user"): 
                st.markdown(prompt)

        model = get_gemini_model()
        if model is None:
            response_text = "⚠️ `GEMINI_API_KEY` `.env` dosyasında tanımlı değil."
        else:
            system_prompt = _build_system_prompt(product=product, fifo_info=fifo_info, usd_rate=usd_rate, intel_report=intel_report)
            full_prompt = f"{system_prompt}\n\nKULLANICI SORUSU: {prompt}"
            
            with chat_container:
                with st.chat_message("assistant"):
                    # ── AI Düşünüyor Video Yükleyici ──
                    ai_loader_ph = st.empty()
                    ai_loader_ph.markdown(render_webm_loader("ai_thinking.webm", "Bedülonca Gemini analiz ediyor..."), unsafe_allow_html=True)
                    
                    try:
                        resp = model.generate_content(full_prompt, generation_config={"temperature": 0.35})
                        response_text = resp.text
                    except Exception as e:
                        response_text = f"❌ API hatası: {e}"
                    
                    # Animasyonu temizle ve gerçek cevabı bas
                    ai_loader_ph.empty()
                    st.markdown(response_text)

        st.session_state[chat_key].append({"role": "assistant", "content": response_text})

    if st.button("🗑️ Sohbeti Temizle", key=f"clear_chat_{selected_sku}", use_container_width=True):
        st.session_state[chat_key] = []
        st.rerun()