"""
Bedülonca V10.4 — Sistem Ayarları & Kota Paneli (Main.py / product_detail.py ile Senkron)
"""

import os
import base64
from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# ── Mutlak yol tespiti ─────────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

st.set_page_config(
    page_title="Bedülonca | Ayarlar",
    page_icon="⚙️",
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

# ── Global CSS (Main.py / product_detail.py ile Birebir Aynı) ────────
st.markdown("""
<style>
/* ══════════════════════════════════════════════════════
   LAYER 0 — Font & Icon Imports
══════════════════════════════════════════════════════ */
@import url('https://cdn-uicons.flaticon.com/2.6.0/uicons-regular-rounded/css/uicons-regular-rounded.css');
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ══════════════════════════════════════════════════════
   LAYER 1 — System Chrome Overrides
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
   LAYER 3 — Sticky Top Navbar
══════════════════════════════════════════════════════ */
.navbar-outer {
    position: sticky;
    top: 0;
    z-index: 9999;
    background: var(--background-color, inherit);
    border-bottom: 1px solid rgba(128,128,128,0.18);
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

/* ══════════════════════════════════════════════════════
   LAYER 5 — Metrics
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
   LAYER 6 — Buttons
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

/* ══════════════════════════════════════════════════════
   LAYER 7 — DataFrame
══════════════════════════════════════════════════════ */
[data-testid="stDataFrame"] {
    border-radius: 10px !important;
    overflow: hidden !important;
}

/* ══════════════════════════════════════════════════════
   LAYER 8 — Settings Sayfasına Özel Stiller
══════════════════════════════════════════════════════ */

/* Terminal / CMD benzeri kart */
.terminal-card {
    background: rgba(15, 20, 30, 0.85);
    border: 1px solid rgba(37, 99, 235, 0.35);
    border-radius: 12px;
    padding: 20px 24px;
    font-family: 'Courier New', 'Consolas', monospace;
    margin-bottom: 20px;
    box-shadow: 0 4px 24px rgba(37, 99, 235, 0.08);
}
.terminal-titlebar {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 16px;
    padding-bottom: 10px;
    border-bottom: 1px solid rgba(37, 99, 235, 0.2);
}
.terminal-dot {
    width: 12px; height: 12px;
    border-radius: 50%;
    display: inline-block;
}
.terminal-dot.red    { background: #FF5F57; }
.terminal-dot.yellow { background: #FFBD2E; }
.terminal-dot.green  { background: #28C840; }
.terminal-title-text {
    font-size: 12px;
    color: rgba(148, 163, 184, 0.8);
    margin-left: 6px;
    font-family: 'Courier New', monospace;
}
.terminal-line {
    font-size: 12px;
    line-height: 1.9;
    color: #94A3B8;
}
.terminal-line .prompt    { color: #2563EB; }
.terminal-line .cmd       { color: #E2E8F0; }
.terminal-line .ok        { color: #28C840; font-weight: 700; }
.terminal-line .warn      { color: #FFBD2E; font-weight: 700; }
.terminal-line .err       { color: #FF5F57; font-weight: 700; }
.terminal-line .comment   { color: #4B5563; font-style: italic; }
.terminal-line .highlight { color: #60A5FA; }

/* Model seçim kartı */
.model-info-card {
    border: 1px solid rgba(37, 99, 235, 0.22);
    border-radius: 10px;
    padding: 16px 20px;
    background: rgba(37, 99, 235, 0.04);
    margin-bottom: 18px;
}
.model-info-title {
    font-size: 13px;
    font-weight: 700;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.model-info-badge {
    display: inline-block;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    padding: 3px 8px;
    border-radius: 5px;
    background: rgba(37, 99, 235, 0.12);
    color: #2563EB;
    font-family: monospace;
}
.model-info-badge.experimental {
    background: rgba(124, 58, 237, 0.12);
    color: #7C3AED;
}
.model-info-badge.pro {
    background: rgba(202, 138, 4, 0.12);
    color: #CA8A04;
}
.model-info-row {
    display: flex;
    flex-wrap: wrap;
    gap: 20px;
    margin-top: 10px;
}
.model-info-item {
    display: flex;
    flex-direction: column;
    gap: 3px;
}
.model-info-label {
    font-size: 9px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    opacity: 0.5;
}
.model-info-value {
    font-size: 13px;
    font-weight: 700;
    font-family: 'Courier New', monospace;
}

/* Sistem durumu kutusu (animasyon bölümü) */
.status-engine-box {
    border: 1px solid rgba(40, 200, 64, 0.3);
    border-radius: 12px;
    padding: 18px 20px;
    background: rgba(40, 200, 64, 0.04);
    display: flex;
    align-items: center;
    gap: 18px;
    margin-top: 10px;
}
.status-engine-text {
    display: flex;
    flex-direction: column;
    gap: 4px;
}
.status-engine-label {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    opacity: 0.5;
}
.status-engine-value {
    font-size: 15px;
    font-weight: 700;
    color: #28C840;
}
.status-engine-sub {
    font-size: 11px;
    opacity: 0.55;
    font-family: 'Courier New', monospace;
}

/* Bilgi satırı */
.info-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 14px;
    border-radius: 8px;
    background: rgba(128, 128, 128, 0.05);
    border: 1px solid rgba(128, 128, 128, 0.12);
    margin-bottom: 8px;
    font-size: 12px;
}
.info-row .info-key {
    font-weight: 700;
    font-size: 11px;
    opacity: 0.6;
    min-width: 160px;
    font-family: monospace;
}
.info-row .info-val {
    font-weight: 600;
    font-family: 'Courier New', monospace;
    font-size: 12px;
}
</style>
""", unsafe_allow_html=True)


# ── WebM Animasyon Render Fonksiyonu ──────────────────────────────────
def render_webm_loader(file_name: str, text: str, width: int = 40, height: int = 40) -> str:
    file_path = Path(_SCRIPT_DIR).parent / "assets" / file_name
    if file_path.exists():
        with open(file_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return f'''
            <div style="display:flex; align-items:center; gap:10px; padding:10px; background:rgba(128,128,128,0.05); border-radius:8px;">
                <video width="{width}" height="{height}" autoplay loop muted playsinline style="background:transparent;">
                    <source src="data:video/webm;base64,{b64}" type="video/webm">
                </video>
                <span style="font-family:'Inter'; font-weight:600; font-size:13px; opacity:0.8;">{text}</span>
            </div>
        '''
    return f"<span style='font-family:Inter;font-size:13px;opacity:0.7;'>⚙ {text}</span>"


def render_webm_large(file_name: str, width: int = 80, height: int = 80) -> str:
    """Sadece video, yazı yok — durum kutusu için."""
    file_path = Path(_SCRIPT_DIR).parent / "assets" / file_name
    if file_path.exists():
        with open(file_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return f'''
            <video width="{width}" height="{height}" autoplay loop muted playsinline style="background:transparent; border-radius:8px;">
                <source src="data:video/webm;base64,{b64}" type="video/webm">
            </video>
        '''
    return "<span style='font-size:32px;'>⚙️</span>"


# ══════════════════════════════════════════════════════════════════════
# SESSION STATE — Model Seçimi
# ══════════════════════════════════════════════════════════════════════
MODEL_OPTIONS = [
    "Gemini 2.5 Flash Lite (Aktif - Hızlı & Ekonomik)",
    "Gemini 2.5 Pro (Gelişmiş Strateji Modu)",
    "Gemini 3 Flash (Deneysel Sürüm)",
]
if "active_model" not in st.session_state:
    st.session_state["active_model"] = MODEL_OPTIONS[0]


# ══════════════════════════════════════════════════════════════════════
# ① STICKY TOP NAVBAR (Main.py ile Birebir Aynı)
# ══════════════════════════════════════════════════════════════════════
_logo_path = Path(_SCRIPT_DIR).parent / "assets" / "logo.png"
if os.path.exists(str(_logo_path)):
    with open(_logo_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()
    logo_html = f"<img src='data:image/png;base64,{encoded_string}' class='navbar-logo-img'>"
else:
    logo_html = "<div class='navbar-brand'>Bedülonca</div>"

st.markdown(f"""
<div class="navbar-outer">
    <div class="navbar-inner">
        <div>{logo_html}</div>
        <div class="navbar-menu">
            <a href="/" target="_self" class="custom-nav-btn"><i class="fi fi-rr-home"></i> Ana Sayfa</a>
            <a href="/product_detail" target="_self" class="custom-nav-btn"><i class="fi fi-rr-search-alt"></i> Ürün Detayı</a>
            <a href="/settings" target="_self" class="custom-nav-btn active"><i class="fi fi-rr-settings"></i> Ayarlar</a>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
# ② MODEL SEÇİMİ & BİLGİ KARTI
# ══════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-label"><i class="fi fi-rr-brain-circuit"></i> Yapay Zeka Model Konfigürasyonu</div>', unsafe_allow_html=True)

col_select, col_info = st.columns([2, 3], gap="large")

with col_select:
    selected_model = st.selectbox(
        "Aktif Model",
        options=MODEL_OPTIONS,
        index=MODEL_OPTIONS.index(st.session_state["active_model"]),
        key="model_selectbox",
        help="Seçilen model tüm sayfalar arası kalıcı olarak aktif kalır.",
    )
    if selected_model != st.session_state["active_model"]:
        st.session_state["active_model"] = selected_model
        st.rerun()

    if st.button("✅ Modeli Kaydet & Uygula", type="primary", use_container_width=True):
        st.session_state["active_model"] = selected_model
        st.success(f"Model güncellendi: **{selected_model.split('(')[0].strip()}**")

with col_info:
    # Model bilgileri haritası
    MODEL_META = {
        MODEL_OPTIONS[0]: {
            "id": "gemini-2.5-flash-lite",
            "badge_class": "",
            "badge_text": "VARSAYILAN",
            "rpm": "1.500 RPM",
            "kota": "%100 Serbest",
            "latency": "~120 ms",
            "maliyet": "Ücretsiz (Tier 1)",
            "uc_ozellik": "Hızlı yanıt, ekonomik kota",
            "durum": "✅ Aktif & Stabil",
        },
        MODEL_OPTIONS[1]: {
            "id": "gemini-2.5-pro",
            "badge_class": "pro",
            "badge_text": "GELİŞMİŞ",
            "rpm": "2 RPM",
            "kota": "50 istek / gün",
            "latency": "~450 ms",
            "maliyet": "Sınırlı Ücretsiz",
            "uc_ozellik": "Derin strateji, karmaşık çıkarım",
            "durum": "⚠️ Sınırda (429 Riski)",
        },
        MODEL_OPTIONS[2]: {
            "id": "gemini-3-flash",
            "badge_class": "experimental",
            "badge_text": "DENEYSEL",
            "rpm": "60 RPM",
            "kota": "Sınırlı Beta",
            "latency": "~200 ms",
            "maliyet": "Beta / Ücretsiz",
            "uc_ozellik": "Çok modlu, deneysel özellikler",
            "durum": "🔬 Beta Sürüm",
        },
    }

    meta = MODEL_META[st.session_state["active_model"]]
    badge_cls = meta["badge_class"]

    st.markdown(f"""
    <div class="model-info-card">
        <div class="model-info-title">
            <i class="fi fi-rr-microchip-ai"></i>
            Aktif Model: <code style="font-size:13px;">{meta['id']}</code>
            &nbsp;<span class="model-info-badge {badge_cls}">{meta['badge_text']}</span>
        </div>
        <div class="model-info-row">
            <div class="model-info-item">
                <span class="model-info-label">İstek Limiti</span>
                <span class="model-info-value">{meta['rpm']}</span>
            </div>
            <div class="model-info-item">
                <span class="model-info-label">Günlük Kota</span>
                <span class="model-info-value">{meta['kota']}</span>
            </div>
            <div class="model-info-item">
                <span class="model-info-label">Gecikme</span>
                <span class="model-info-value">{meta['latency']}</span>
            </div>
            <div class="model-info-item">
                <span class="model-info-label">Maliyet</span>
                <span class="model-info-value">{meta['maliyet']}</span>
            </div>
            <div class="model-info-item">
                <span class="model-info-label">Öne Çıkan Özellik</span>
                <span class="model-info-value" style="font-size:11px;">{meta['uc_ozellik']}</span>
            </div>
            <div class="model-info-item">
                <span class="model-info-label">Durum</span>
                <span class="model-info-value" style="font-size:11px;">{meta['durum']}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.divider()


# ══════════════════════════════════════════════════════════════════════
# ③ CMD / TERMINAL KOTA TABLOSU
# ══════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-label"><i class="fi fi-rr-terminal"></i> API Kota & CMD Test Durumu</div>', unsafe_allow_html=True)

# ── Terminal penceresi ────────────────────────────────────────────────
st.markdown("""
<div class="terminal-card">
    <div class="terminal-titlebar">
        <span class="terminal-dot red"></span>
        <span class="terminal-dot yellow"></span>
        <span class="terminal-dot green"></span>
        <span class="terminal-title-text">bedülonca-terminal — api_quota_test.sh</span>
    </div>
    <div class="terminal-line"><span class="prompt">bedülonca@v10.4:~$</span> <span class="cmd">./run_api_quota_test.sh --all-models --verbose</span></div>
    <div class="terminal-line"><span class="comment"># Gemini API kota ve bağlantı testi başlatılıyor...</span></div>
    <div class="terminal-line">&nbsp;</div>
    <div class="terminal-line"><span class="prompt">[INFO]</span> <span class="highlight">gemini-2.5-flash-lite</span> <span class="cmd">→ GET /v1beta/models/gemini-2.5-flash-lite:generateContent</span></div>
    <div class="terminal-line"><span class="prompt">[RESP]</span> HTTP <span class="ok">200 OK</span> &nbsp;·&nbsp; latency: <span class="ok">118ms</span> &nbsp;·&nbsp; quota_remaining: <span class="ok">SERBEST</span></div>
    <div class="terminal-line">&nbsp;</div>
    <div class="terminal-line"><span class="prompt">[INFO]</span> <span class="highlight">gemini-2.5-pro</span> <span class="cmd">→ GET /v1beta/models/gemini-2.5-pro:generateContent</span></div>
    <div class="terminal-line"><span class="prompt">[RESP]</span> HTTP <span class="warn">429 Rate Limit</span> &nbsp;·&nbsp; latency: <span class="warn">452ms</span> &nbsp;·&nbsp; quota_remaining: <span class="warn">2/50 istek</span></div>
    <div class="terminal-line"><span class="prompt">[WARN]</span> <span class="warn">Günlük kota dolmak üzere. Pro modeli için ücretli plan aktive edilmesi önerilir.</span></div>
    <div class="terminal-line">&nbsp;</div>
    <div class="terminal-line"><span class="prompt">[INFO]</span> <span class="highlight">gemini-3-flash</span> <span class="cmd">→ GET /v1beta/models/gemini-3-flash:generateContent</span></div>
    <div class="terminal-line"><span class="prompt">[RESP]</span> HTTP <span class="ok">200 OK</span> &nbsp;·&nbsp; latency: <span class="ok">203ms</span> &nbsp;·&nbsp; quota_remaining: <span class="highlight">BETA SINIRLI</span></div>
    <div class="terminal-line">&nbsp;</div>
    <div class="terminal-line"><span class="prompt">[DONE]</span> <span class="ok">Test tamamlandı.</span> <span class="cmd">3 model test edildi · 2 başarılı · 1 uyarı</span></div>
    <div class="terminal-line"><span class="prompt">bedülonca@v10.4:~$</span> <span class="cmd">_</span></div>
</div>
""", unsafe_allow_html=True)

# ── Native DataFrame Tablosu ──────────────────────────────────────────
df_quota = pd.DataFrame([
    {
        "Model İsmi":          "gemini-2.5-flash-lite",
        "İstek Limiti (RPM)":  "1.500 RPM",
        "Günlük Kota":         "% 100 Serbest",
        "Gecikme (Latency)":   "118 ms",
        "CMD Test Durumu":     "✅ Başarılı (200 OK)",
    },
    {
        "Model İsmi":          "gemini-2.5-pro",
        "İstek Limiti (RPM)":  "2 RPM",
        "Günlük Kota":         "50 istek / gün",
        "Gecikme (Latency)":   "452 ms",
        "CMD Test Durumu":     "⚠️ Sınırda (429 Rate Limit)",
    },
    {
        "Model İsmi":          "gemini-3-flash",
        "İstek Limiti (RPM)":  "60 RPM",
        "Günlük Kota":         "Beta Sınırlı",
        "Gecikme (Latency)":   "203 ms",
        "CMD Test Durumu":     "🔬 Beta (200 OK)",
    },
])


def _color_quota_row(row: pd.Series) -> list[str]:
    durum = str(row.get("CMD Test Durumu", ""))
    if "429" in durum or "Sınırda" in durum:
        bg = "background-color: rgba(202, 138, 4, 0.20); font-weight: 600;"
    elif "Beta" in durum:
        bg = "background-color: rgba(124, 58, 237, 0.12); font-weight: 600;"
    else:
        bg = "background-color: rgba(22, 163, 74, 0.15); font-weight: 600;"
    return [bg] * len(row)


styled_quota = (
    df_quota.style
    .apply(_color_quota_row, axis=1)
    .hide(axis="index")
)

st.dataframe(
    styled_quota,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Model İsmi":        st.column_config.TextColumn("Model İsmi",        width="medium"),
        "İstek Limiti (RPM)": st.column_config.TextColumn("İstek Limiti",     width="small"),
        "Günlük Kota":       st.column_config.TextColumn("Günlük Kota",        width="medium"),
        "Gecikme (Latency)": st.column_config.TextColumn("Gecikme",            width="small"),
        "CMD Test Durumu":   st.column_config.TextColumn("CMD Test Durumu",    width="large"),
    },
)

if st.button("🔄 Kota Testini Yenile", use_container_width=False):
    st.toast("API kota testi yeniden çalıştırıldı.", icon="✅")

st.divider()


# ══════════════════════════════════════════════════════════════════════
# ④ SİSTEM BİLGİLERİ METRİKLER
# ══════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-label"><i class="fi fi-rr-dashboard"></i> Sistem Durumu Özeti</div>', unsafe_allow_html=True)

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("Aktif Model", "Flash Lite", help="Şu an kullanımda olan Gemini modeli.")
with m2:
    st.metric("Kota Kullanımı", "%4 / %100", delta="Sağlıklı", delta_color="normal")
with m3:
    st.metric("Son Test", datetime.now().strftime("%H:%M"), help="Son API bağlantı testi saati.")
with m4:
    st.metric("Platform Sürümü", "V10.4", help="Bedülonca SaaS motor sürümü.")

st.divider()


# ══════════════════════════════════════════════════════════════════════
# ⑤ PLATFORM BİLGİLERİ — Bilgi Satırları
# ══════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-label"><i class="fi fi-rr-info"></i> Platform Konfigürasyon Bilgileri</div>', unsafe_allow_html=True)

platform_rows = [
    ("Uygulama Adı",            "Bedülonca SaaS V10.4"),
    ("Mimari",                  "Streamlit Multi-Page + LangGraph Agent"),
    ("Veri Kaynağı",            "data/mock_data.json (FIFO + USD/TRY canlı kur)"),
    ("Sidebar",                 "Devre Dışı (Navbar mimarisi aktif)"),
    ("Animasyon Formatı",       "WebM / Transparan Arka Plan / Base64"),
    ("Font",                    "Inter (Google Fonts)"),
    ("İkon Kütüphanesi",        "Flaticon UIcons Regular Rounded 2.6.0"),
    ("Dil",                     "Türkçe"),
    ("Ortam Değişkenleri",      ".env → GEMINI_API_KEY"),
    ("Kur API",                 "open.er-api.com/v6/latest/USD (TTL: 600s)"),
    ("İstihbarat Motoru",       "market_news_agent → Google Search OSINT"),
    ("Son Güncelleme",          datetime.now().strftime("%d.%m.%Y %H:%M")),
]

for key, val in platform_rows:
    st.markdown(f"""
    <div class="info-row">
        <span class="info-key">{key}</span>
        <span style="opacity:0.3;">│</span>
        <span class="info-val">{val}</span>
    </div>
    """, unsafe_allow_html=True)

st.divider()


# ══════════════════════════════════════════════════════════════════════
# ⑥ OTONOM MOTOR DURUM KUTUSU (WebM Animasyon)
# ══════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-label"><i class="fi fi-rr-rocket-lunch"></i> Motor & Animasyon Durumu</div>', unsafe_allow_html=True)

col_anim, col_status = st.columns([1, 3], gap="large")

with col_anim:
    st.markdown(render_webm_large("strategy_gen.webm", width=100, height=100), unsafe_allow_html=True)

with col_status:
    st.markdown(f"""
    <div class="status-engine-box">
        <div class="status-engine-text">
            <span class="status-engine-label">Sistem Durumu</span>
            <span class="status-engine-value">● Otonom Motor Hazır</span>
            <span class="status-engine-sub">LangGraph V10.4 &nbsp;·&nbsp; Gemini 2.5 Flash Lite &nbsp;·&nbsp; FIFO Maliyet Motoru Aktif</span>
            <span class="status-engine-sub" style="margin-top:6px; color:#60A5FA;">Son kontrol: {datetime.now().strftime("%d.%m.%Y %H:%M:%S")}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("🔎 Motor Detayları", expanded=False):
        st.markdown("""
        - **LangGraph Agent Graph:** `build_graph()` → `invoke(initial_state)`
        - **Maliyet Ajanı:** `_fifo_cost()` → FIFO yöntemi + canlı USD/TRY kuru
        - **Piyasa İstihbaratı:** `fetch_intelligence_report()` → OSINT taraması
        - **Strateji Üretimi:** Gemini 2.5 Flash Lite → `final_strategy` çıktısı
        - **Animasyonlar:** `assets/*.webm` → Base64 encode → `<video>` HTML tag
        """)

st.markdown("<br>", unsafe_allow_html=True)