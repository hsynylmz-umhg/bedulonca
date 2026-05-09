# main.py
import streamlit as st
from agent_graph import build_graph
from state import AgentState

# ── Sayfa Yapılandırması ──────────────────────────────────────────────
st.set_page_config(
    page_title="Bedülonca | Kâr Marjı Optimizasyonu",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Stil ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Genel arka plan */
    .stApp { background-color: #0f1117; }

    /* Metrik kartları */
    [data-testid="metric-container"] {
        background: #1a1d27;
        border: 1px solid #2d3144;
        border-radius: 12px;
        padding: 16px;
    }

    /* Aksiyon butonları — genel */
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

    /* Renk sınıfları (JS yerine st.markdown ile inject) */
    .btn-green  { background: #00FF94 !important; color: #0f1117 !important; }
    .btn-red    { background: #FF4B4B !important; color: #ffffff !important; }
    .btn-gray   { background: #3a3f55 !important; color: #aaaaaa !important; }

    /* Bölüm başlıkları */
    .section-title {
        font-size: 13px;
        font-weight: 700;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        color: #00FF94;
        margin-bottom: 8px;
    }

    /* Kırmızı çizgi uyarı kutusu */
    .red-line-box {
        background: rgba(255,75,75,0.12);
        border-left: 3px solid #FF4B4B;
        border-radius: 6px;
        padding: 10px 14px;
        margin: 6px 0;
        font-size: 13px;
    }

    /* Sağlıklı metrik kutusu */
    .green-box {
        background: rgba(0,255,148,0.08);
        border-left: 3px solid #00FF94;
        border-radius: 6px;
        padding: 10px 14px;
        margin: 6px 0;
        font-size: 13px;
    }

    /* Divider */
    hr { border-color: #2d3144; }
</style>
""", unsafe_allow_html=True)


# ── Graph Cache ───────────────────────────────────────────────────────
@st.cache_resource
def get_graph():
    return build_graph()


# ── Header ────────────────────────────────────────────────────────────
col_logo, col_title = st.columns([1, 11])
with col_logo:
    st.markdown("## ⚡")
with col_title:
    st.markdown("## Bedülonca — Otonom Kâr Marjı Optimizasyonu")
    st.caption("KOBİ E-Ticaret Zeka Sistemi · BTK AI Hackathon 2026")

st.markdown("---")


# ── Tetikleyici Panel ─────────────────────────────────────────────────
st.markdown('<p class="section-title">🎯 Analiz Tetikleyici</p>', unsafe_allow_html=True)

col_input, col_btn = st.columns([4, 1])
with col_input:
    trigger_event = st.text_input(
        label="Tetikleyici Olay",
        value="Haftalık fiyat optimizasyonu",
        placeholder="Örn: Yeni oyun lansmanı sonrası stok analizi",
        label_visibility="collapsed",
    )
with col_btn:
    run_button = st.button("⚡ Analizi Başlat", use_container_width=True)

st.markdown("---")


# ── Ana Çalıştırma ────────────────────────────────────────────────────
if run_button:
    if not trigger_event.strip():
        st.warning("Lütfen bir tetikleyici olay girin.")
        st.stop()

    initial_state: AgentState = {
        "trigger_event":      trigger_event,
        "trending_skus":      [],
        "trend_insights":     "",
        "competitor_analysis": {},
        "cost_metrics":       {},
        "final_strategy":     "",
        "suggested_actions":  [],
        "errors":             [],
    }

    with st.spinner("Ajan zinciri çalışıyor… Trend → Piyasa → Maliyet → Strateji"):
        app   = get_graph()
        result = app.invoke(initial_state)

    # ── Hata Bildirimi ──────────────────────────────────────────────
    if result.get("errors"):
        with st.expander("⚠️ Sistem Uyarıları", expanded=False):
            for err in result["errors"]:
                st.error(err)

    # ── Trend Paneli ────────────────────────────────────────────────
    st.markdown('<p class="section-title">📈 Trend Analizi</p>', unsafe_allow_html=True)
    st.info(result.get("trend_insights", "Veri alınamadı."))
    st.markdown("---")

    # ── Piyasa + Maliyet Metrikleri ─────────────────────────────────
    st.markdown('<p class="section-title">💹 Ürün Bazlı Durum Tablosu</p>', unsafe_allow_html=True)

    cost_metrics       = result.get("cost_metrics", {})
    competitor_analysis = result.get("competitor_analysis", {})

    if cost_metrics:
        for sku, metrics in cost_metrics.items():
            comp = competitor_analysis.get(sku, {})
            health = metrics.get("health", "?")
            box_class = "red-line-box" if health == "KRİTİK" else (
                        "red-line-box" if health == "UYARI" else "green-box")

            with st.container():
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Mevcut Fiyat",  f"{metrics['our_price_tl']:,} TL")
                c2.metric("Toplam Maliyet", f"{metrics['total_cost_tl']:,} TL")
                c3.metric("Kırmızı Çizgi", f"{metrics['red_line_price_tl']:,} TL")
                c4.metric("Marj",           f"%{metrics['current_margin_pct']}")

                st.markdown(
                    f'<div class="{box_class}"><b>{health}</b> · {metrics["health_note"]}<br>'
                    f'<small>Pozisyon: <b>{comp.get("position", "—")}</b> · '
                    f'{comp.get("opportunity", "")}</small></div>',
                    unsafe_allow_html=True
                )
                st.caption(f"SKU: `{sku}`")
                st.markdown("---")
    else:
        st.warning("Maliyet verisi alınamadı.")

    # ── Gemini Stratejisi ───────────────────────────────────────────
    st.markdown('<p class="section-title">🧠 Gemini Strateji Analizi</p>', unsafe_allow_html=True)
    st.markdown(result.get("final_strategy", "Strateji üretilemedi."))
    st.markdown("---")

    # ── Aksiyon Butonları ───────────────────────────────────────────
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

            icon      = {"price_update": "🔴", "create_bundle": "🟢", "hold": "⚫"}.get(atype, "⚪")
            btn_class = {"price_update": "btn-red", "create_bundle": "btn-green", "hold": "btn-gray"}.get(atype, "btn-gray")

            with cols[i % 3]:
                st.markdown(f'<style>div:nth-of-type({i+1}) button{{}} </style>', unsafe_allow_html=True)
                clicked = st.button(f"{icon} {label}", key=f"action_{i}")
                st.caption(reason)

                if clicked:
                    if atype == "price_update":
                        st.success(f"✅ Fiyat güncelleme talebi iletildi: **{action.get('sku')}** → {action.get('new_price_tl'):,} TL")
                    elif atype == "create_bundle":
                        skus = " + ".join(action.get("skus", []))
                        st.success(f"✅ Bundle oluşturma talebi iletildi: **{skus}** → {action.get('bundle_price_tl'):,} TL")
                    elif atype == "hold":
                        st.info(f"⏸ **{action.get('sku')}** için bekleme kararı onaylandı.")

    st.markdown("---")
    st.caption("Bedülonca v0.1 · BTK AI Hackathon 2026 · Powered by Google Gemini + LangGraph")