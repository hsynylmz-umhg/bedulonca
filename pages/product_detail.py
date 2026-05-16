# pages/product_detail.py
"""
Bedülonca V9 — Ürün Detay Sayfası
- Borsa terminali tarzı grafikler (rangeselector, SMA, Fiyat Esnekliği)
- AI Chatbot: Gemini + Google Dorks (Cimri/Akakçe) canlı istihbarat
- FIFO batch detayı
"""

import os
from dotenv import load_dotenv

# ── Mutlak yol ile .env yükleme ───────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_ENV_PATH   = os.path.join(_SCRIPT_DIR, "..", ".env")
if os.path.exists(_ENV_PATH):
    load_dotenv(dotenv_path=_ENV_PATH)
else:
    load_dotenv()  # fallback

import json
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import requests
import google.generativeai as genai

from agents.cost_agent        import _fifo_cost
from agents.market_news_agent import fetch_intelligence_report, search_product_news

DATA_PATH = Path(__file__).parent.parent / "data" / "mock_data.json"

st.set_page_config(
    page_title="Bedülonca | Ürün Detay",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #0d0f18; }
    .block-container { padding: 1.5rem 2.5rem 3rem 2.5rem !important; }

    [data-testid="stSidebar"] {
        background: #0d0f18; border-right: 1px solid #1f2333;
    }
    [data-testid="stSidebar"] * { color: #cbd5e1 !important; }

    .detail-header {
        background: #141724; border: 1px solid #1f2333;
        border-radius: 10px; padding: 16px 22px; margin-bottom: 20px;
    }
    .prod-name { font-size: 22px; font-weight: 800; color: #f1f5f9; }
    .prod-sku  { font-size: 12px; color: #64748b; font-family: monospace; }
    .prod-cat  { font-size: 12px; color: #00FF94; font-weight: 600;
                 text-transform: uppercase; letter-spacing: 1px; }

    .section-label {
        font-size: 12px; font-weight: 700; letter-spacing: 1.5px;
        text-transform: uppercase; color: #f8fafc;
        margin-bottom: 10px; margin-top: 22px;
        border-bottom: 1px solid #1f2333; padding-bottom: 6px;
    }
    .divider { border: none; border-top: 1px solid #1f2333; margin: 16px 0; }

    [data-testid="stMetric"] {
        background: #141724; border: 1px solid #1f2333;
        border-radius: 10px; padding: 10px 14px;
    }
    [data-testid="stMetricLabel"] { color: #94a3b8 !important; font-size: 11px !important; }
    [data-testid="stMetricValue"] { color: #f1f5f9 !important; font-size: 18px !important; }

    .batch-card {
        background: #141724; border: 1px solid #1f2333;
        border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;
    }
    .batch-id   { font-size: 11px; color: #64748b; font-family: monospace; }
    .batch-info { font-size: 13px; color: #e2e8f0; font-weight: 600; }

    [data-testid="stChatMessage"] {
        background: #141724 !important;
        border: 1px solid #1f2333 !important;
        border-radius: 10px !important;
    }

    [data-testid="stTabs"] [data-baseweb="tab-list"] {
        background: transparent; border-bottom: 1px solid #1f2333;
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

    div[data-testid="stButton"] > button[kind="secondary"] {
        background: #1f2333; color: #cbd5e1; font-weight: 600;
        border: 1px solid #334155; border-radius: 6px;
    }
    div[data-testid="stButton"] > button[kind="secondary"]:hover {
        background: #263044; border-color: #00FF94; color: #00FF94;
    }
</style>
""", unsafe_allow_html=True)

COLOR_GREEN  = "#00FF94"
COLOR_YELLOW = "#FBBF24"
COLOR_RED    = "#FF4B4B"
COLOR_PURPLE = "#818cf8"
COLOR_BLUE   = "#38bdf8"
BG_PAPER     = "rgba(0,0,0,0)"
BG_PLOT      = "rgba(0,0,0,0)"
GRID_COLOR   = "#1f2333"


# ── Veri yükleme ──────────────────────────────────────────────────────
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
    arr_x = np.array(x, dtype=float)
    arr_y = np.array(y, dtype=float)
    m, b  = np.polyfit(arr_x, arr_y, 1)
    return x, (m * arr_x + b).tolist()


# ── Gemini ────────────────────────────────────────────────────────────
@st.cache_resource
def get_gemini_model():
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return None
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-2.5-flash-lite")


def _build_system_prompt(
    product:     dict,
    fifo_info:   dict,
    usd_rate:    float,
    intel_report: str,
) -> str:
    """
    Gemini'ye enjekte edilecek sistem promptu.
    Ürün verisini + canlı Google istihbaratını içerir.
    """
    batches_str = "\n".join(
        f"  Parti {b.get('batch_id','?')}: {b.get('qty','?')} adet, "
        f"${b.get('buy_price_usd','?')} "
        f"(≈ ₺{b.get('buy_price_usd', 0) * usd_rate:,.0f} güncel kur)"
        for b in product.get("inventory_batches", [])
    ) or "  Parti verisi yok."

    history = product.get("monthly_history", [])
    hist_str = " | ".join(
        f"{h['month']}: ₺{h['price']:,.0f} / {h['sales_qty']} adet / %{h['profit_margin_pct']}"
        for h in history
    ) or "Tarihsel veri yok."

    return f"""Sen Bedülonca e-ticaret platformunun kıdemli fiyatlandırma danışmanısın.
Türkçe cevap ver. Kısa ve actionable ol (max 250 kelime).
Sayısal veriyle destekle. Kırmızı çizginin altına düşen fiyat ASLA önerme.

══════════════════════════════════════════════
ÜRÜN KARTI
══════════════════════════════════════════════
SKU          : {product['sku']}
Ad           : {product['name']}
Kategori     : {product['category']}
Satış Fiyatı : ₺{product['our_price_tl']:,.0f}
Satış Hızı   : {product.get('sales_per_week', 0)} adet/hafta
Stok         : {product['stock_qty']} adet

══════════════════════════════════════════════
FIFO MALİYET ANALİZİ
══════════════════════════════════════════════
FIFO Birim Maliyet : ₺{fifo_info['fifo_unit_cost_tl']:,.0f}
Yöntem             : {fifo_info['fifo_method']}
Parti Detayı:
{batches_str}

══════════════════════════════════════════════
TARİHSEL PERFORMANS (Son 6 Ay)
══════════════════════════════════════════════
{hist_str}

══════════════════════════════════════════════
CANLI WEB İSTİHBARATI (Google — Cimri / Akakçe / Haberler)
══════════════════════════════════════════════
{intel_report}

══════════════════════════════════════════════
GÜNCEL USD/TRY : ₺{usd_rate:.2f}
══════════════════════════════════════════════

Kullanıcının sorusuna yukarıdaki verileri kullanarak somut öneri sun."""


# ══════════════════════════════════════════════════════════════════════
# VERİ YÜKLEME
# ══════════════════════════════════════════════════════════════════════
data          = load_data()
fallback_rate = data["market_config"]["current_usd_rate"]
usd_rate      = fetch_usd_rate(fallback_rate)
products_map  = {p["sku"]: p for p in data["products"]}
sku_options   = [p["sku"] for p in data["products"]]

# ══════════════════════════════════════════════════════════════════════
# QUERY PARAMS İLE ÜRÜN YAKALAMA
# ══════════════════════════════════════════════════════════════════════
query_sku = st.query_params.get("sku")

if query_sku:
    if query_sku in products_map:
        st.session_state["detail_sku"] = query_sku
    else:
        st.error(f"❌ URL'deki SKU (`{query_sku}`) veritabanında bulunamadı.")
        st.stop()
else:
    has_valid = (
        "detail_sku" in st.session_state
        and st.session_state["detail_sku"]
        and st.session_state["detail_sku"] in products_map
    )
    if not has_valid:
        st.warning(
            "⚠️ Lütfen Ana Dashboard üzerinden bir ürün seçerek inceleyiniz.",
        )
        if st.button("🏠 Ana Dashboard'a Git"):
            st.switch_page("main.py")
        st.stop()

# ── Sidebar ───────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚡ Bedülonca V9")
    st.markdown("---")
    st.page_link("main.py",                 label="🏠 Ana Dashboard")
    st.page_link("pages/product_detail.py", label="🔍 Ürün Detay")
    st.markdown("---")
    st.markdown("**Ürün Seç:**")

    default_sku = st.session_state.get("detail_sku", sku_options[0])
    if default_sku not in sku_options:
        default_sku = sku_options[0]

    selected_sku = st.selectbox(
        "SKU",
        sku_options,
        index=sku_options.index(default_sku),
        label_visibility="collapsed",
    )
    st.session_state["detail_sku"] = selected_sku
    st.markdown(f"**Kur:** `₺{usd_rate:.2f}`")

    if st.button("🏠 Dashboard'a Dön", use_container_width=True):
        st.switch_page("main.py")

# ── Ürün Yükle ────────────────────────────────────────────────────────
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

# ── Session state anahtarları (ürüne özgü) ────────────────────────────
chat_key  = f"chat_{selected_sku}"
intel_key = f"intel_{selected_sku}"   # istihbarat raporu cache'i

if chat_key not in st.session_state:
    st.session_state[chat_key] = []   # [{"role": "user"|"assistant", "content": str}]

# ══════════════════════════════════════════════════════════════════════
# HEADER
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
    delta_color="normal" if margin_pct >= 12 else "inverse",
)
met5.metric("Stok",       f"{stock_qty} adet")
met6.metric("Satış Hızı", f"{weekly_sales} adet/hafta")

st.markdown("<hr class='divider'>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# ANA İÇERİK: Sol = Grafikler, Sağ = Chatbot
# ══════════════════════════════════════════════════════════════════════
col_charts, col_chat = st.columns([3, 2], gap="large")

# ──────────────────────────────────────────────────────────────────────
# SOL: GRAFİKLER
# ──────────────────────────────────────────────────────────────────────
with col_charts:

    if not history:
        st.warning("Bu ürün için tarihsel veri bulunamadı.")
    else:
        months     = [h["month"]             for h in history]
        prices     = [h["price"]             for h in history]
        sales_qtys = [h["sales_qty"]         for h in history]
        margins    = [h["profit_margin_pct"] for h in history]
        avg_s      = sum(sales_qtys) / len(sales_qtys) if sales_qtys else 1

        tab1, tab2, tab3 = st.tabs([
            "📈 Fiyat & Marj Geçmişi",
            "📦 Satış Hacmi + SMA",
            "💹 Fiyat Esnekliği",
        ])

        # ── Tab 1: Fiyat + Marj ──────────────────────────────────────
        with tab1:
            st.markdown(
                '<div class="section-label">Fiyat ve Kâr Marjı Zaman Serisi</div>',
                unsafe_allow_html=True,
            )
            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.08,
                subplot_titles=("Satış Fiyatı (TL)", "Kâr Marjı (%)"),
                row_heights=[0.65, 0.35],
            )
            fig.add_trace(go.Scatter(
                x=months, y=prices,
                mode="lines+markers", name="Fiyat",
                line=dict(color=COLOR_GREEN, width=2.5),
                marker=dict(size=7, color=COLOR_GREEN,
                            line=dict(color="#0d0f18", width=2)),
                fill="tozeroy", fillcolor="rgba(0,255,148,0.06)",
                hovertemplate="<b>%{x}</b><br>₺%{y:,.0f}<extra></extra>",
            ), row=1, col=1)

            marker_colors_m = [
                COLOR_RED if m < 0 else COLOR_YELLOW if m < 12 else COLOR_GREEN
                for m in margins
            ]
            fig.add_trace(go.Scatter(
                x=months, y=margins,
                mode="lines+markers", name="Marj %",
                line=dict(color=COLOR_PURPLE, width=2),
                marker=dict(size=7, color=marker_colors_m,
                            line=dict(color="#0d0f18", width=2)),
                fill="tozeroy", fillcolor="rgba(129,140,248,0.08)",
                hovertemplate="<b>%{x}</b><br>%{y:.1f}%<extra></extra>",
            ), row=2, col=1)

            fig.add_hline(y=12, line_dash="dot", line_color=COLOR_YELLOW,
                          opacity=0.5, row=2, col=1,
                          annotation_text="Min. %12",
                          annotation_font_color=COLOR_YELLOW,
                          annotation_position="top right")
            fig.add_hline(y=0, line_dash="dash", line_color=COLOR_RED,
                          opacity=0.4, row=2, col=1)

            fig.update_layout(
                paper_bgcolor=BG_PAPER, plot_bgcolor=BG_PLOT,
                font=dict(color="#94a3b8", size=11),
                margin=dict(l=10, r=10, t=50, b=10), height=420,
                showlegend=True,
                legend=dict(orientation="h", y=1.08,
                            font=dict(color="#cbd5e1"),
                            bgcolor="rgba(0,0,0,0)"),
                xaxis=dict(
                    gridcolor=GRID_COLOR, tickfont=dict(color="#cbd5e1"),
                    rangeselector=dict(
                        buttons=[
                            dict(count=1, label="1A",  step="month", stepmode="backward"),
                            dict(count=3, label="3A",  step="month", stepmode="backward"),
                            dict(count=6, label="6A",  step="month", stepmode="backward"),
                            dict(step="all", label="Tümü"),
                        ],
                        bgcolor="#1f2333", activecolor="#00FF94",
                        font=dict(color="#cbd5e1"), x=0, y=1.02,
                    ),
                ),
                xaxis2=dict(gridcolor=GRID_COLOR, tickfont=dict(color="#cbd5e1")),
                yaxis=dict(gridcolor=GRID_COLOR, tickprefix="₺",
                           tickformat=",.0f", tickfont=dict(color="#94a3b8")),
                yaxis2=dict(gridcolor=GRID_COLOR, ticksuffix="%",
                            tickfont=dict(color="#94a3b8")),
            )
            st.plotly_chart(fig, use_container_width=True)

        # ── Tab 2: Satış Hacmi + SMA ──────────────────────────────────
        with tab2:
            st.markdown(
                '<div class="section-label">Satış Hacmi ve Hareketli Ortalamalar</div>',
                unsafe_allow_html=True,
            )
            sma2 = _sma(sales_qtys, 2)
            sma3 = _sma(sales_qtys, 3)

            bar_colors = [
                COLOR_GREEN  if q == max(sales_qtys)
                else COLOR_YELLOW if q >= avg_s
                else COLOR_RED
                for q in sales_qtys
            ]
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                x=months, y=sales_qtys, name="Satış Adedi",
                marker_color=bar_colors, opacity=0.80,
                text=sales_qtys, textposition="outside",
                textfont=dict(color="#e2e8f0", size=10),
                hovertemplate="<b>%{x}</b><br>%{y} adet<extra></extra>",
            ))
            fig2.add_trace(go.Scatter(
                x=months, y=sma2, mode="lines", name="SMA-2",
                line=dict(color=COLOR_YELLOW, width=2, dash="dot"),
                hovertemplate="SMA-2: %{y:.1f}<extra></extra>",
                connectgaps=True,
            ))
            fig2.add_trace(go.Scatter(
                x=months, y=sma3, mode="lines", name="SMA-3",
                line=dict(color=COLOR_PURPLE, width=2, dash="dash"),
                hovertemplate="SMA-3: %{y:.1f}<extra></extra>",
                connectgaps=True,
            ))
            fig2.update_layout(
                paper_bgcolor=BG_PAPER, plot_bgcolor=BG_PLOT,
                font=dict(color="#94a3b8", size=11),
                margin=dict(l=10, r=10, t=40, b=10), height=320,
                barmode="overlay",
                legend=dict(orientation="h", y=1.12,
                            font=dict(color="#cbd5e1"),
                            bgcolor="rgba(0,0,0,0)"),
                title=dict(text="Aylık Satış + SMA Trend Çizgileri",
                           font=dict(color="#cbd5e1", size=13), x=0),
                xaxis=dict(gridcolor=GRID_COLOR, tickfont=dict(color="#cbd5e1")),
                yaxis=dict(gridcolor=GRID_COLOR, ticksuffix=" adet",
                           tickfont=dict(color="#94a3b8")),
            )
            st.plotly_chart(fig2, use_container_width=True)
            st.caption("SMA-2: 2 aylık · SMA-3: 3 aylık hareketli ortalama")

        # ── Tab 3: Fiyat Esnekliği ────────────────────────────────────
        with tab3:
            st.markdown(
                '<div class="section-label">Fiyat Esnekliği — Fiyat vs Satış Adedi</div>',
                unsafe_allow_html=True,
            )
            if len(prices) < 2:
                st.info("Fiyat esnekliği için en az 2 veri noktası gereklidir.")
            else:
                x_idx       = list(range(len(prices)))
                _, trend_y  = _linreg_trend(x_idx, sales_qtys)

                point_colors = [
                    COLOR_GREEN  if q == max(sales_qtys)
                    else COLOR_YELLOW if q >= avg_s
                    else COLOR_RED
                    for q in sales_qtys
                ]
                fig3 = go.Figure()
                fig3.add_trace(go.Scatter(
                    x=prices, y=sales_qtys,
                    mode="markers+text", name="Veri Noktaları",
                    marker=dict(size=14, color=point_colors, opacity=0.85,
                                line=dict(color="#0d0f18", width=2)),
                    text=months, textposition="top center",
                    textfont=dict(color="#cbd5e1", size=10),
                    hovertemplate=(
                        "<b>%{text}</b><br>"
                        "Fiyat: ₺%{x:,.0f}<br>"
                        "Satış: %{y} adet<extra></extra>"
                    ),
                ))

                sorted_pairs = sorted(zip(prices, trend_y), key=lambda t: t[0])
                fig3.add_trace(go.Scatter(
                    x=[p[0] for p in sorted_pairs],
                    y=[p[1] for p in sorted_pairs],
                    mode="lines", name="Regresyon Trendi",
                    line=dict(color=COLOR_BLUE, width=2, dash="dot"),
                    hovertemplate="Trend: %{y:.1f}<extra></extra>",
                ))

                corr = float(np.corrcoef(prices, sales_qtys)[0, 1])
                corr_label = (
                    "🟢 Zayıf negatif korelasyon"    if corr > -0.3
                    else "🟡 Orta negatif korelasyon" if corr > -0.7
                    else "🔴 Güçlü negatif korelasyon"
                )
                fig3.update_layout(
                    paper_bgcolor=BG_PAPER, plot_bgcolor=BG_PLOT,
                    font=dict(color="#94a3b8", size=11),
                    margin=dict(l=10, r=10, t=40, b=10), height=340,
                    legend=dict(orientation="h", y=1.12,
                                font=dict(color="#cbd5e1"),
                                bgcolor="rgba(0,0,0,0)"),
                    title=dict(text=f"Fiyat Esnekliği | Korelasyon: {corr:.2f}",
                               font=dict(color="#cbd5e1", size=13), x=0),
                    xaxis=dict(title=dict(text="Satış Fiyatı (TL)",
                                         font=dict(color="#94a3b8")),
                               gridcolor=GRID_COLOR, tickprefix="₺",
                               tickformat=",.0f", tickfont=dict(color="#cbd5e1")),
                    yaxis=dict(title=dict(text="Satış Adedi",
                                         font=dict(color="#94a3b8")),
                               gridcolor=GRID_COLOR,
                               tickfont=dict(color="#94a3b8")),
                )
                st.plotly_chart(fig3, use_container_width=True)
                st.caption(corr_label)

    # ── FIFO Batch Detayı ─────────────────────────────────────────────
    st.markdown(
        '<div class="section-label">📦 FIFO Parti (Batch) Detayı</div>',
        unsafe_allow_html=True,
    )
    if not batches:
        st.info("Parti verisi bulunamadı.")
    else:
        for b in batches:
            price_usd = b.get("buy_price_usd", 0)
            price_tl  = (
                price_usd * usd_rate
                if product.get("buy_currency") == "USD"
                else price_usd
            )
            currency_symbol = "$" if product.get("buy_currency") == "USD" else "₺"
            tl_note = (
                f" = {fmt_tl(price_tl)} (güncel kur)"
                if product.get("buy_currency") == "USD"
                else ""
            )
            st.markdown(f"""
            <div class="batch-card">
                <div class="batch-id">
                    Parti: {b.get('batch_id','?')} · Tarih: {b.get('buy_date','?')}
                </div>
                <div class="batch-info">
                    {b.get('qty','?')} adet · {currency_symbol}{price_usd:,.0f}{tl_note}
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.caption(
            f"FIFO Yöntemi: `{fifo_info.get('fifo_method','?')}` · "
            f"FIFO Birim Maliyet: **{fmt_tl(fifo_cost_tl)}**"
        )


# ──────────────────────────────────────────────────────────────────────
# SAĞ: AI CHATBOT (Google Dorks + Gemini)
# ──────────────────────────────────────────────────────────────────────
with col_chat:
    st.markdown(
        '<div class="section-label">🤖 AI Danışman — Canlı İstihbarat + Gemini</div>',
        unsafe_allow_html=True,
    )

    # ── İstihbarat Raporu (cache ile, ürün değişince yenilenir) ───────
    if intel_key not in st.session_state:
        with st.spinner("🔍 Google'dan canlı istihbarat çekiliyor..."):
            st.session_state[intel_key] = fetch_intelligence_report(
                sku=selected_sku,
                product_name=product["name"],
            )

    intel_report = st.session_state[intel_key]

    # İstihbarat raporunu göster
    with st.expander("📊 Canlı Web İstihbaratı (Haber + Cimri/Akakçe)", expanded=False):
        st.markdown(intel_report, unsafe_allow_html=True)

        # Yenile butonu
        if st.button("🔄 İstihbaratı Yenile", key=f"refresh_intel_{selected_sku}",
                     use_container_width=True):
            del st.session_state[intel_key]
            st.rerun()

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    # ── Chat Geçmişi ──────────────────────────────────────────────────
    chat_container = st.container(height=360)
    with chat_container:
        if not st.session_state[chat_key]:
            st.markdown(
                f"""
                <div style="text-align:center; padding:30px; color:#64748b;">
                    <div style="font-size:28px; margin-bottom:8px;">🤖</div>
                    <div style="font-size:13px;">
                        Merhaba! Ben Bedülonca AI danışmanıyım.<br>
                        <b>{product['name']}</b> hakkında soru sor.<br>
                        <span style="font-size:11px; color:#475569;">
                        (Canlı Google verisi + FIFO maliyet ile yanıtlarım)
                        </span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        for msg in st.session_state[chat_key]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # ── Chat Input ────────────────────────────────────────────────────
    if prompt := st.chat_input(
        f"{product['name'].split()[0]} hakkında sor...",
        key=f"chat_input_{selected_sku}",
    ):
        # 1. Kullanıcı mesajını state'e ekle ve göster
        st.session_state[chat_key].append({"role": "user", "content": prompt})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)

        # 2. Gemini yanıtı üret
        model = get_gemini_model()
        if model is None:
            response_text = (
                "⚠️ `GEMINI_API_KEY` `.env` dosyasında tanımlı değil. "
                "Lütfen API anahtarını ekleyin."
            )
        else:
            # Sistem promptu: ürün verisi + canlı istihbarat
            system_prompt = _build_system_prompt(
                product=product,
                fifo_info=fifo_info,
                usd_rate=usd_rate,
                intel_report=intel_report,
            )
            # Tam prompt = sistem + kullanıcı sorusu
            full_prompt = f"{system_prompt}\n\nKULLANICI SORUSU: {prompt}"

            try:
                with st.spinner("🧠 Gemini analiz ediyor..."):
                    resp = model.generate_content(
                        full_prompt,
                        generation_config={"temperature": 0.35},
                    )
                response_text = resp.text
            except Exception as e:
                response_text = f"❌ API hatası: {e}"

        # 3. Yanıtı state'e ekle ve göster
        st.session_state[chat_key].append(
            {"role": "assistant", "content": response_text}
        )
        with chat_container:
            with st.chat_message("assistant"):
                st.markdown(response_text)

    # ── Sohbet Temizle ────────────────────────────────────────────────
    if st.button(
        "🗑️ Sohbeti Temizle",
        key=f"clear_chat_{selected_sku}",
        use_container_width=True,
    ):
        st.session_state[chat_key] = []
        st.rerun()