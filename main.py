# main.py
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

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

st.markdown("""
<style>
    .stApp { background-color: #0f1117; }
    [data-testid="metric-container"] {
        background: #1a1d27;
        border: 1px solid #2d3144;
        border-radius: 12px;
        padding: 16px;
    }
    div[data-testid="stButton"] > button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
        font-size: 14px;
        padding: 10px 0;
        border: none;
        transition: opacity .2s;
    }
    div[data-testid="stButton"] > button:hover { opacity: 0.85; }
    .section-title {
        font-size: 13px;
        font-weight: 700;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        color: #00FF94;
        margin-bottom: 8px;
    }
    .red-line-box {
        background: rgba(255,75,75,0.12);
        border-left: 3px solid #FF4B4B;
        border-radius: 6px;
        padding: 10px 14px;
        margin: 6px 0;
        font-size: 13px;
    }
    .green-box {
        background: rgba(0,255,148,0.08);
        border-left: 3px solid #00FF94;
        border-radius: 6px;
        padding: 10px 14px;
        margin: 6px 0;
        font-size: 13px;
    }
    .product-card {
        background: #1a1d27;
        border: 1px solid #2d3144;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
    }
    hr { border-color: #2d3144; }
</style>
""", unsafe_allow_html=True)


# ── Cache Katmanı ─────────────────────────────────────────────────────
@st.cache_resource
def get_graph():
    return build_graph()

@st.cache_data
def load_mock_data() -> dict:
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Statik Render Fonksiyonları ───────────────────────────────────────
def render_static_inventory(data: dict) -> None:
    """
    JSON'dan ürünleri okur, analiz beklenmeksizin ekrana basar.
    Sayfa açıldığında her zaman görünür.
    """
    st.markdown('<p class="section-title">📦 Mevcut Envanter</p>', unsafe_allow_html=True)
    products = data.get("products", [])

    cols = st.columns(len(products))
    for i, product in enumerate(products):
        with cols[i]:
            if product.get("logo_url"):
                st.image(product["logo_url"], width=56)
            st.markdown(f"**{product['name']}**")
            st.metric("Satış Fiyatı", f"{product['our_price_tl']:,} TL")
            st.metric("Stok",         f"{product['stock_qty']} adet")
            st.caption(f"`{product['sku']}`")


def render_static_charts(data: dict) -> None:
    """
    sales_history verisinden grafikleri analiz beklenmeksizin çizer.
    Sayfa açıldığında her zaman görünür.
    """
    sales_history = data.get("sales_history", [])
    if not sales_history:
        return

    df = pd.DataFrame(sales_history)

    fig_kar = go.Figure()
    fig_kar.add_trace(go.Scatter(
        x=df["ay"], y=df["net_kar_tl"],
        mode="lines+markers",
        line=dict(color="#00FF94", width=3),
        marker=dict(size=8, color="#00FF94",
                    line=dict(color="#0f1117", width=2)),
        fill="tozeroy",
        fillcolor="rgba(0,255,148,0.07)",
        name="Net Kâr (TL)",
    ))
    fig_kar.update_layout(
        title=dict(text="Aylık Net Kâr Gelişimi", font=dict(color="#ffffff")),
        paper_bgcolor="#1a1d27", plot_bgcolor="#1a1d27",
        font=dict(color="#aaaaaa"),
        xaxis=dict(gridcolor="#2d3144"),
        yaxis=dict(gridcolor="#2d3144", tickformat=",.0f"),
        margin=dict(l=40, r=20, t=50, b=40),
    )

    fig_enf = go.Figure()
    fig_enf.add_trace(go.Bar(
        x=df["ay"], y=df["enflasyon_yuzdesi"],
        marker_color="#FF4B4B", opacity=0.85,
        name="Enflasyon (%)",
    ))
    fig_enf.update_layout(
        title=dict(text="Aylık Enflasyon Etkisi (%)", font=dict(color="#ffffff")),
        paper_bgcolor="#1a1d27", plot_bgcolor="#1a1d27",
        font=dict(color="#aaaaaa"),
        xaxis=dict(gridcolor="#2d3144"),
        yaxis=dict(gridcolor="#2d3144", ticksuffix="%"),
        margin=dict(l=40, r=20, t=50, b=40),
    )

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(fig_kar, use_container_width=True)
    with col2:
        st.plotly_chart(fig_enf, use_container_width=True)


def render_analysis_results(result: dict, data: dict) -> None:
    """
    LangGraph çıktısını alır, analiz sonuçlarını ve aksiyon
    butonlarını ekrana basar. Sadece buton tıklandıktan sonra çalışır.
    """
    if result.get("errors"):
        with st.expander("⚠️ Sistem Uyarıları", expanded=False):
            for err in result["errors"]:
                st.error(err)

    # Trend
    st.markdown('<p class="section-title">📈 Trend Analizi</p>', unsafe_allow_html=True)
    st.info(result.get("trend_insights", "Veri alınamadı."))

    # PriceOps Logları
    st.markdown('<p class="section-title">🕸️ PriceOps Tarama Logları</p>', unsafe_allow_html=True)
    st.code(result.get("crawl_log", ""), language="bash")
    st.markdown("---")

    # Ürün bazlı maliyet + kırmızı çizgi
    st.markdown('<p class="section-title">💹 Ürün Bazlı Durum Tablosu</p>', unsafe_allow_html=True)
    cost_metrics        = result.get("cost_metrics", {})
    competitor_analysis = result.get("competitor_analysis", {})
    logo_map            = {p["sku"]: p.get("logo_url", "") for p in data["products"]}

    for sku, metrics in cost_metrics.items():
        comp      = competitor_analysis.get(sku, {})
        health    = metrics.get("health", "?")
        box_class = "green-box" if health == "SAĞLIKLI" else "red-line-box"

        with st.container():
            col_img, c1, c2, c3, c4 = st.columns([1, 2, 2, 2, 2])
            if logo_map.get(sku):
                col_img.image(logo_map[sku], width=56)
            c1.metric("Mevcut Fiyat",   f"{metrics['our_price_tl']:,} TL")
            c2.metric("Toplam Maliyet", f"{metrics['total_cost_tl']:,} TL")
            c3.metric("Kırmızı Çizgi",  f"{metrics['red_line_price_tl']:,} TL")
            c4.metric("Marj",            f"%{metrics['current_margin_pct']}")
            st.markdown(
                f'<div class="{box_class}"><b>{health}</b> · {metrics["health_note"]}<br>'
                f'<small>Pozisyon: <b>{comp.get("position","—")}</b> · '
                f'{comp.get("opportunity","")}</small></div>',
                unsafe_allow_html=True,
            )
            st.caption(f"SKU: `{sku}`")
            st.markdown("---")

    # Gemini Stratejisi
    st.markdown('<p class="section-title">🧠 Gemini Strateji Analizi</p>', unsafe_allow_html=True)
    st.markdown(result.get("final_strategy", "Strateji üretilemedi."))
    st.markdown("---")

    # Aksiyon Butonları
    st.markdown('<p class="section-title">🎮 Önerilen Aksiyonlar</p>', unsafe_allow_html=True)
    actions = result.get("suggested_actions", [])

    if not actions:
        st.info("Gemini herhangi bir aksiyon önermedi.")
    else:
        cols = st.columns(min(len(actions), 3))
        for i, action in enumerate(actions):
            atype  = action.get("action_type", "hold")
            label  = action.get("button_label", "Aksiyonu Uygula")
            reason = action.get("reason", "")
            icon   = {"price_update": "🔴", "create_bundle": "🟢",
                      "hold": "⚫"}.get(atype, "⚪")

            with cols[i % 3]:
                clicked = st.button(f"{icon} {label}", key=f"action_{i}")
                st.caption(reason)
                if clicked:
                    if atype == "price_update":
                        st.success(
                            f"✅ Fiyat güncelleme talebi iletildi: "
                            f"**{action.get('sku')}** → {action.get('new_price_tl'):,} TL"
                        )
                    elif atype == "create_bundle":
                        skus = " + ".join(action.get("skus", []))
                        st.success(
                            f"✅ Bundle oluşturma talebi iletildi: "
                            f"**{skus}** → {action.get('bundle_price_tl'):,} TL"
                        )
                    elif atype == "hold":
                        st.info(
                            f"⏸ **{action.get('sku')}** için bekleme kararı onaylandı."
                        )


# ════════════════════════════════════════════════════════════════════
# SAYFA AKIŞI
# ════════════════════════════════════════════════════════════════════

# Header — her zaman görünür
col_logo, col_title = st.columns([1, 11])
with col_logo:
    st.markdown("## ⚡")
with col_title:
    st.markdown("## Bedülonca — Otonom Kâr Marjı Optimizasyonu")
    st.caption("KOBİ E-Ticaret Zeka Sistemi · BTK AI Hackathon 2026")

st.markdown("---")

tab1, tab2 = st.tabs(["🚀 Operasyonel Panel", "📊 Stratejik Dashboard"])

# ── TAB 1 ─────────────────────────────────────────────────────────────
with tab1:
    data = load_mock_data()

    # STATIK KATMAN — sayfa açılır açılmaz görünür, analiz beklenmez
    render_static_inventory(data)
    st.markdown("---")

    # Tetikleyici
    st.markdown('<p class="section-title">🎯 Analiz Tetikleyici</p>', unsafe_allow_html=True)
    col_input, col_btn = st.columns([4, 1])
    with col_input:
        trigger_event = st.text_input(
            label="Tetikleyici Olay",
            value="Haftalık fiyat optimizasyonu",
            label_visibility="collapsed",
        )
    with col_btn:
        run_button = st.button("⚡ Analizi Başlat", use_container_width=True)

    st.markdown("---")

    # DİNAMİK KATMAN — sadece buton tıklanınca çalışır
    if run_button:
        if not trigger_event.strip():
            st.warning("Lütfen bir tetikleyici olay girin.")
            st.stop()

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

        with st.spinner("Ajan zinciri çalışıyor… Trend → Piyasa → Maliyet → Strateji"):
            result = get_graph().invoke(initial_state)

        # Analiz sonuçlarını render et
        render_analysis_results(result, data)

    st.markdown("---")
    st.caption("Bedülonca v0.5 · BTK AI Hackathon 2026 · Powered by Google Gemini + LangGraph")

# ── TAB 2 ─────────────────────────────────────────────────────────────
with tab2:
    st.markdown('<p class="section-title">📊 Son 6 Ay Finansal Performans</p>',
                unsafe_allow_html=True)
    data = load_mock_data()

    # Grafikler de statik — sayfa açılır açılmaz görünür
    render_static_charts(data)

    st.markdown("---")
    m1, m2, m3, m4 = st.columns(4)
    df = pd.DataFrame(data.get("sales_history", []))
    if not df.empty:
        m1.metric("Toplam Net Kâr", f"{df['net_kar_tl'].sum():,.0f} TL")
        m2.metric("En Yüksek Ay",   df.loc[df['net_kar_tl'].idxmax(), 'ay'])
        m3.metric("Ort. Enflasyon", f"%{df['enflasyon_yuzdesi'].mean():.2f}")
        m4.metric("Kâr Trendi",
                  "📈 Yükseliş" if df['net_kar_tl'].iloc[-1] > df['net_kar_tl'].iloc[0]
                  else "📉 Düşüş")

    st.markdown("---")
    st.caption("Bedülonca v0.5 · BTK AI Hackathon 2026 · Powered by Google Gemini + LangGraph")