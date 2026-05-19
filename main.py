# main.py
import json
import io
import os
import random
import base64
from pathlib import Path
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
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

# ── Global CSS ────────────────────────────────────────────────────────
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
   LAYER 3 — Sticky Top Navbar (Flexbox Redesign)
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

/* ══════════════════════════════════════════════════════
   LAYER 4 — Popover Fixes
══════════════════════════════════════════════════════ */
/* Tablo yanındaki 3 nokta (2. sütun) için oku gizle ve butonu kare yap */
div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2) [data-testid="stPopover"] button svg {
    display: none !important;
    width: 0 !important; height: 0 !important; opacity: 0 !important;
}
div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2) [data-testid="stPopover"] > div > button {
    background: transparent !important;
    border: 1px solid rgba(128,128,128,0.22) !important;
    border-radius: 7px !important;
    font-size: 20px !important;
    font-weight: 700 !important;
    padding: 2px 12px !important;
    line-height: 1.5 !important;
}
/* Genel popover body tasarımı */
[data-testid="stPopoverBody"] {
    border-radius: 12px !important;
    box-shadow: 0 8px 30px rgba(0,0,0,0.14) !important;
    min-width: 270px !important;
    padding: 10px 4px !important;
}
.popover-section-title {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.4px;
    text-transform: uppercase;
    opacity: 0.5;
    margin-bottom: 6px;
    margin-top: 4px;
}
/* Master checkbox kalın yazsın */
.master-checkbox label {
    font-weight: 700 !important;
    opacity: 0.9 !important;
}

/* ══════════════════════════════════════════════════════
   LAYER 5 — Section Labels
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
.chart-title {
    font-size: 11px; font-weight: 700; letter-spacing: 1px;
    text-transform: uppercase; opacity: 0.55;
    margin-bottom: 6px; margin-top: 14px; text-align: center;
}
.custom-label {
    font-size: 12px; font-weight: 600; opacity: 0.7;
    margin-bottom: 4px; font-family: 'Inter', sans-serif;
}

/* ══════════════════════════════════════════════════════
   LAYER 6 — st.dataframe & Metrics
══════════════════════════════════════════════════════ */
[data-testid="stDataFrame"] { border-radius: 10px !important; overflow: hidden !important; }
[data-testid="stDataFrame"] a { font-weight: 600 !important; text-decoration: none !important; }
[data-testid="stDataFrame"] a:hover { color: inherit !important; opacity: 0.75 !important; }

[data-testid="stMetric"] {
    border: 1px solid rgba(128,128,128,0.16) !important;
    border-radius: 12px !important;
    padding: 14px 18px !important;
}
[data-testid="stMetricLabel"] {
    font-size: 10px !important; font-weight: 700 !important;
    text-transform: uppercase !important; letter-spacing: 0.8px !important; opacity: 0.55 !important;
}
[data-testid="stMetricValue"] { font-size: 22px !important; font-weight: 700 !important; }
[data-testid="stMetricDelta"] {
    display: flex !important; flex-direction: row !important;
    align-items: center !important; white-space: nowrap !important; font-size: 11px !important;
}

/* ══════════════════════════════════════════════════════
   LAYER 7 — Buttons & Action Cards
══════════════════════════════════════════════════════ */
div[data-testid="stButton"] > button[kind="primary"] {
    background: #2563EB !important; color: #FFFFFF !important; font-weight: 700 !important;
    border-radius: 8px !important; transition: opacity .18s !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover { opacity: 0.86 !important; }

.action-card      { border-radius: 10px; padding: 14px 16px; margin-bottom: 10px; }
.action-critical  { background: rgba(239,68,68,0.08);  border: 1px solid rgba(239,68,68,0.28); }
.action-bundle    { background: rgba(34,197,94,0.08);  border: 1px solid rgba(34,197,94,0.28); }
.action-markdown  { background: rgba(234,179,8,0.08);  border: 1px solid rgba(234,179,8,0.28); }
.action-gift      { background: rgba(59,130,246,0.08); border: 1px solid rgba(59,130,246,0.28); }
.action-liquidate { background: rgba(168,85,247,0.08); border: 1px solid rgba(168,85,247,0.28); }
.action-hold      { background: rgba(100,116,139,0.07);border: 1px solid rgba(100,116,139,0.22); }
.action-title  { font-size: 13px; font-weight: 700; margin-bottom: 4px; }
.action-detail { font-size: 12px; margin-bottom: 5px; opacity: 0.82; }
.action-reason { font-size: 11px; opacity: 0.52; font-style: italic; }
.price-arrow { color: #EF4444; font-weight: 700; }
.price-up    { color: #EF4444; }
.price-hold  { opacity: 0.52; }
</style>
""", unsafe_allow_html=True)

# ── Plot colour constants ─────────────────────────────────────────────
COLOR_GREEN  = "#16A34A"
COLOR_YELLOW = "#CA8A04"
COLOR_RED    = "#DC2626"
COLOR_BLUE   = "#2563EB"
BG_PAPER     = "rgba(0,0,0,0)"
BG_PLOT      = "rgba(0,0,0,0)"
GRID_COLOR   = "rgba(148,163,184,0.22)"

def _lottie_html(url: str, height: int = 200) -> str:
    return (
        "<script src='https://unpkg.com/@lottiefiles/dotlottie-wc@0.9.14"
        "/dist/dotlottie-wc.js' type='module'></script>"
        f"<div style='display:flex;justify-content:center;"
        f"overflow:hidden;height:{height}px;'>"
        f"<dotlottie-wc src='{url}' autoplay loop "
        f"style='width:{height}px;height:{height}px;'></dotlottie-wc>"
        "</div>"
    )

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
    except Exception as exc:
        print(f"Kur ajanı hatası: {exc}")
        return fallback

def fmt_tl(v: float) -> str:
    return f"₺{v:,.0f}".replace(",", ".")

def get_fifo_cost_tl(product: dict, usd_rate: float) -> float:
    return _fifo_cost(product, usd_rate)["fifo_unit_cost_tl"]

def _restock_recommendation(product: dict) -> str:
    spw   = product.get("sales_per_week", 0)
    stock = product.get("stock_qty", 0)
    if spw <= 0: return "Satış Yok"
    weeks_left = stock / spw
    monthly    = spw * 4
    if weeks_left <= 1: return f"Acil {int(monthly * 2)} adet sipariş ver"
    elif weeks_left <= 2: return f"{int(monthly)} adet sipariş önerilir"
    elif weeks_left <= 6: return "Stok Yeterli"
    elif weeks_left <= 12: return "Stok Fazlası"
    else: return "Kritik Fazla — Tasfiye Düşün"

def _price_check_label(margin_pct: float) -> str:
    if margin_pct < 0: return "❌ Zarar/Hatalı"
    elif margin_pct > 100: return "⚠️ Aşırı Kâr"
    else: return "✅ Normal"

def build_inventory_df(data: dict, usd_rate: float) -> pd.DataFrame:
    rows = []
    for p in data["products"]:
        fifo_cost   = get_fifo_cost_tl(p, usd_rate)
        monthly_qty = p.get("sales_per_week", 0) * 4
        profit_tl   = p["our_price_tl"] - fifo_cost
        margin_pct  = round((profit_tl / p["our_price_tl"]) * 100, 1) if p["our_price_tl"] else 0
        spw = p.get("sales_per_week", 0)
        stock_flag = "Kritik" if (spw > 0 and (p["stock_qty"] / spw) <= 2) else "Dikkat" if (spw > 0 and (p["stock_qty"] / spw) <= 4) else "OK" if spw > 0 else "-"

        sku = p["sku"]
        rows.append({
            "_margin_raw":           margin_pct,
            "Aksiyon":               f"/product_detail?sku={sku}",
            "SKU":                   sku,
            "Ürün Adı":              p["name"],
            "Kategori":              p["category"].replace("_", " ").title(),
            "Stok Durumu":           stock_flag,
            "Stok Adet":             p["stock_qty"],
            "Aylık Satış":           monthly_qty,
            "Mevcut Fiyat":          p["our_price_tl"],
            "FIFO Maliyet":          round(fifo_cost, 0),
            "Satış Kârı TL":         round(profit_tl, 0),
            "Marj %":                margin_pct,
            "Hatalı Fiyat Kontrolü": _price_check_label(margin_pct),
            "Durum Önerisi":         _restock_recommendation(p),
        })
    return pd.DataFrame(rows)

def _color_row(row: pd.Series) -> list[str]:
    m = float(row.get("Marj %", row.get("_margin_raw", 0)))
    # Renk tonları (opacity) artırıldı, daha doygun hale getirildi.
    if m < 0:
        bg = "background-color: rgba(220, 38, 38, 0.40); font-weight:600;"
    elif m < 12:
        bg = "background-color: rgba(217, 119, 6, 0.35); font-weight:600;"
    else:
        bg = "background-color: rgba(22, 163, 74, 0.30); font-weight:600;"
    return [bg] * len(row)

# ══════════════════════════════════════════════════════════════════════
# DATA LOADING
# ══════════════════════════════════════════════════════════════════════
with st.spinner("Veriler yükleniyor..."):
    data          = load_mock_data()
    fallback_rate = data["market_config"]["current_usd_rate"]
    current_rate  = fetch_live_usd_rate(fallback_rate)
    products_map  = {p["sku"]: p for p in data["products"]}
    df_inv        = build_inventory_df(data, current_rate)

all_categories = sorted(df_inv["Kategori"].unique().tolist())
total_stock    = sum(p["stock_qty"] for p in data["products"])

# ══════════════════════════════════════════════════════════════════════
# SESSION STATE & CALLBACKS FOR CHECKBOX SYNC
# ══════════════════════════════════════════════════════════════════════
if "detail_sku" not in st.session_state and not df_inv.empty:
    st.session_state["detail_sku"] = df_inv["SKU"].iloc[0]
if "analysis_result" not in st.session_state: st.session_state["analysis_result"] = None
if "analysis_ran_at" not in st.session_state: st.session_state["analysis_ran_at"] = None
if "chart_index" not in st.session_state: st.session_state["chart_index"] = 0
if "status_filter" not in st.session_state: st.session_state["status_filter"] = "Tümü"

# Initialize Checkbox States
if "inv_master" not in st.session_state: st.session_state["inv_master"] = True
if "dash_master" not in st.session_state: st.session_state["dash_master"] = True

for cat in all_categories:
    if f"inv_cat_{cat}" not in st.session_state: st.session_state[f"inv_cat_{cat}"] = True
    if f"dash_cat_{cat}" not in st.session_state: st.session_state[f"dash_cat_{cat}"] = True

# Callbacks for INVENTORY Filters
def sync_inv_master():
    master = st.session_state["inv_master"]
    for c in all_categories: st.session_state[f"inv_cat_{c}"] = master

def sync_inv_children():
    st.session_state["inv_master"] = all(st.session_state[f"inv_cat_{c}"] for c in all_categories)

# Callbacks for DASHBOARD Filters
def sync_dash_master():
    master = st.session_state["dash_master"]
    for c in all_categories: st.session_state[f"dash_cat_{c}"] = master

def sync_dash_children():
    st.session_state["dash_master"] = all(st.session_state[f"dash_cat_{c}"] for c in all_categories)


# ══════════════════════════════════════════════════════════════════════
# ① STICKY TOP NAVBAR (Pure HTML/Flexbox - No Stats, Right Aligned)
# ══════════════════════════════════════════════════════════════════════
_logo_path = _BASE_DIR / "img" / "logo.png"
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
            <a href="/main" target="_self" class="custom-nav-btn"><i class="fi fi-rr-home"></i> Ana Sayfa</a>
            <a href="/product_detail" target="_self" class="custom-nav-btn"><i class="fi fi-rr-search-alt"></i> Ürün Detayı</a>
            <a href="/settings" target="_self" class="custom-nav-btn"><i class="fi fi-rr-settings"></i> Ayarlar</a>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
# ② INVENTORY TABLE
# ══════════════════════════════════════════════════════════════════════
hdr_col, dot_col = st.columns([11, 1])
with hdr_col:
    st.markdown('<div class="section-label"><i class="fi fi-rr-box-open"></i> Mevcut Envanter</div>', unsafe_allow_html=True)

with dot_col:
    with st.popover("⋮", use_container_width=True):
        st.markdown('<div class="popover-section-title">Kategori Filtresi</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="master-checkbox">', unsafe_allow_html=True)
        st.checkbox("Tümünü Seç / Hiçbirini Seç", key="inv_master", on_change=sync_inv_master)
        st.markdown('</div>', unsafe_allow_html=True)

        for cat in all_categories:
            st.checkbox(cat, key=f"inv_cat_{cat}", on_change=sync_inv_children)

        st.divider()
        st.markdown('<div class="popover-section-title">Durum Filtresi</div>', unsafe_allow_html=True)
        st.selectbox(
            "Durum",
            options=["Tümü", "Sadece kâr edenler", "Sadece zarar edenler", "Aylık satışı ortalama üstünde", "Kritik stok (2 hafta)", "Stok fazlası (12 hafta)"],
            key="status_filter", label_visibility="collapsed",
        )

        st.divider()
        st.markdown('<div class="popover-section-title">Dışa Aktar</div>', unsafe_allow_html=True)
        df_csv = df_inv.copy()
        df_csv["Aksiyon URL"] = df_inv["SKU"].apply(lambda s: f"https://bedülonca.app/product_detail?sku={s}")
        export_cols = ["Aksiyon URL", "SKU", "Ürün Adı", "Kategori", "Stok Durumu", "Stok Adet", "Aylık Satış", "Mevcut Fiyat", "FIFO Maliyet", "Satış Kârı TL", "Marj %", "Hatalı Fiyat Kontrolü", "Durum Önerisi"]
        export_cols = [c for c in export_cols if c in df_csv.columns]
        buf = io.StringIO()
        df_csv[export_cols].to_csv(buf, index=False, sep=";", encoding="utf-8-sig")
        st.download_button(label="Envanteri İndir (.csv)", data=buf.getvalue().encode("utf-8-sig"), file_name=f"envanter_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", mime="text/csv", use_container_width=True)

# Derive selected categories after callbacks execute
sel_inv_categories = [cat for cat in all_categories if st.session_state[f"inv_cat_{cat}"]]

df_filtered = df_inv.copy()
if sel_inv_categories: df_filtered = df_filtered[df_filtered["Kategori"].isin(sel_inv_categories)]
else: df_filtered = df_filtered.iloc[0:0]

avg_monthly = df_filtered["Aylık Satış"].mean() if not df_filtered.empty else 0
active_filter = st.session_state["status_filter"]

if active_filter == "Sadece kâr edenler": df_filtered = df_filtered[df_filtered["_margin_raw"] > 0]
elif active_filter == "Sadece zarar edenler": df_filtered = df_filtered[df_filtered["_margin_raw"] <= 0]
elif active_filter == "Aylık satışı ortalama üstünde": df_filtered = df_filtered[df_filtered["Aylık Satış"] > avg_monthly]
elif active_filter == "Kritik stok (2 hafta)": df_filtered = df_filtered[df_filtered["Durum Önerisi"].str.contains("Acil|sipariş önerilir", na=False)]
elif active_filter == "Stok fazlası (12 hafta)": df_filtered = df_filtered[df_filtered["Durum Önerisi"].str.contains("Fazla|Tasfiye", na=False)]

DISPLAY_COLS = ["Aksiyon", "SKU", "Ürün Adı", "Kategori", "Stok Durumu", "Stok Adet", "Aylık Satış", "Mevcut Fiyat", "FIFO Maliyet", "Satış Kârı TL", "Marj %", "Hatalı Fiyat Kontrolü", "Durum Önerisi", "_margin_raw"]
df_disp = df_filtered[[c for c in DISPLAY_COLS if c in df_filtered.columns]].copy()

styled = df_disp.style.apply(_color_row, axis=1).format({
    "Mevcut Fiyat": "₺{:,.0f}", "FIFO Maliyet": "₺{:,.0f}", "Satış Kârı TL": "₺{:,.0f}", "Marj %": "{:.1f}%"
}).hide(axis="index")

if df_filtered.empty:
    st.info("Seçili filtrelere uyan ürün bulunamadı.")
else:
    st.dataframe(
        styled, use_container_width=True, hide_index=True, height=460,
        column_config={
            "_margin_raw": None,
            "Aksiyon": st.column_config.LinkColumn(label="İncele", display_text="İncele", help="Ürün detay sayfasına git"),
            "SKU": st.column_config.TextColumn("SKU", width="small"),
            "Ürün Adı": st.column_config.TextColumn("Ürün Adı", width="large"),
            "Mevcut Fiyat": st.column_config.NumberColumn("Mevcut Fiyat", format="₺%.0f"),
            "FIFO Maliyet": st.column_config.NumberColumn("FIFO Maliyet", format="₺%.0f"),
            "Satış Kârı TL": st.column_config.NumberColumn("Satış Kârı", format="₺%.0f"),
            "Marj %": st.column_config.NumberColumn("Marj %", format="%.1f%%"),
            "Hatalı Fiyat Kontrolü": st.column_config.TextColumn("Fiyat Kontrolü", width="medium"),
            "Durum Önerisi": st.column_config.TextColumn("Stok Önerisi", width="large"),
        },
    )

# ── Summary Metrics ───────────────────────────────────────────────────
st.divider()
total_monthly_profit = sum((p["our_price_tl"] - get_fifo_cost_tl(p, current_rate)) * p.get("sales_per_week", 0) * 4 for p in data["products"])
critical_products = [p for p in data["products"] if p.get("sales_per_week", 0) > 0 and (p["stock_qty"] / p["sales_per_week"]) < 2]
critical_count = len(critical_products)

m1, m2, m3, m4, m5 = st.columns(5)
with m1: st.metric("Toplam Ürün", len(data["products"]), help="Sistemde kayıtlı toplam SKU sayısı.")
with m2: st.metric("Toplam Stok", total_stock, help="Tüm ürünlerin depodaki toplam stok adedi.")
with m3: st.metric("USD / TRY", f"₺{current_rate:.2f}", help="Open Exchange Rates canlı kur.")
with m4: st.metric("Aylık Tahmini Kâr", fmt_tl(total_monthly_profit), help="Vergiler hariç brüt kâr projeksiyonu.")
with m5: st.metric("Kritik Stok", f"{critical_count} ürün", delta="acil" if critical_count > 0 else None, delta_color="inverse", help="Mevcut satış hızında 2 haftadan az stok kalan ürünler.")

if critical_count > 0:
    links = " &nbsp;|&nbsp; ".join(f'<a href="/product_detail?sku={p["sku"]}" target="_self">{p["name"]}</a>' for p in critical_products)
    st.markdown(f'<div class="critical-link" style="font-size:12px;margin-top:6px;">Kritik stok: {links}</div>', unsafe_allow_html=True)
st.divider()

# ══════════════════════════════════════════════════════════════════════
# ③ CEO DASHBOARD — Carousel 
# ══════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-label"><i class="fi fi-rr-chart-pie-alt"></i> CEO Dashboard — Kurumsal Analitik</div>', unsafe_allow_html=True)

dash_filter_col, dash_period_col, dash_topn_col = st.columns([2, 2, 1])

with dash_filter_col:
    st.markdown('<div class="custom-label">Kategori Filtresi</div>', unsafe_allow_html=True)
    with st.popover("Filtre Seç", use_container_width=True):
        st.markdown('<div class="popover-section-title">CEO Dashboard — Kategori Seçimi</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="master-checkbox">', unsafe_allow_html=True)
        st.checkbox("Tümünü Seç / Hiçbirini Seç", key="dash_master", on_change=sync_dash_master)
        st.markdown('</div>', unsafe_allow_html=True)

        for cat in all_categories:
            st.checkbox(cat, key=f"dash_cat_{cat}", on_change=sync_dash_children)

    sel_dash_categories = [cat for cat in all_categories if st.session_state[f"dash_cat_{cat}"]]

with dash_period_col:
    st.markdown('<div class="custom-label">Dönem (Trend)</div>', unsafe_allow_html=True)
    dash_period = st.selectbox("Dönem (Trend)", options=["Son 1 Hafta", "Son 4 Hafta", "Son 12 Hafta", "Tüm Zamanlar"], index=1, key="dash_period", label_visibility="collapsed")

with dash_topn_col:
    st.markdown('<div class="custom-label">Trend maks ürün</div>', unsafe_allow_html=True)
    dash_top_n = st.number_input("Trend maks ürün", min_value=2, max_value=12, value=6, step=1, key="dash_top_n", label_visibility="collapsed")

period_map   = {"Son 1 Hafta": 1, "Son 4 Hafta": 4, "Son 12 Hafta": 12, "Tüm Zamanlar": 24}
period_weeks = period_map[dash_period]
dash_skus    = [p["sku"] for p in data["products"] if p["category"].replace("_", " ").title() in sel_dash_categories] if sel_dash_categories else [p["sku"] for p in data["products"]]

CHARTS = [
    ("Haftalık Satış Dağılımı", "pie"), ("Kategori Dönem Kârı", "cat_bar"), ("BCG Matrisi", "bcg"),
    ("Risk Matrisi", "risk"), ("Satış Hızı Trendi", "trend"), ("Dönem Sonu Kâr Projeksiyonu", "proj"),
]
N_CHARTS = len(CHARTS)

c_prev, c_dots, c_next = st.columns([1, 8, 1])
with c_prev:
    if st.button("←", key="chart_prev", use_container_width=True): st.session_state["chart_index"] = (st.session_state["chart_index"] - 1) % N_CHARTS
with c_next:
    if st.button("→", key="chart_next", use_container_width=True): st.session_state["chart_index"] = (st.session_state["chart_index"] + 1) % N_CHARTS
with c_dots:
    dots = "".join('<span style="font-size:15px;color:#2563EB;margin:0 3px;">●</span>' if i == st.session_state["chart_index"] else '<span style="font-size:15px;opacity:0.22;margin:0 3px;">○</span>' for i in range(N_CHARTS))
    st.markdown(f'<div style="text-align:center;line-height:2;padding-top:6px;">{dots}</div>', unsafe_allow_html=True)

chart_title, chart_key = CHARTS[st.session_state["chart_index"]]
st.markdown(f'<div class="chart-title">{chart_title}</div>', unsafe_allow_html=True)

def render_price_vs_redline(cost_metrics: dict) -> None:
    skus       = list(cost_metrics.keys())
    our_prices = [cost_metrics[s]["our_price_tl"] for s in skus]
    red_lines  = [cost_metrics[s]["red_line_price_tl"] for s in skus]
    healths    = [cost_metrics[s]["health"] for s in skus]
    short_skus = [s.split("-")[0] + "..." for s in skus]
    bar_colors = [COLOR_RED if h == "KRİTİK" else COLOR_YELLOW if h == "UYARI" else COLOR_GREEN for h in healths]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Mevcut Fiyat", x=short_skus, y=our_prices, marker_color=bar_colors, opacity=0.85,
        text=[fmt_tl(v) for v in our_prices], textposition="outside", textfont=dict(size=9)
    ))
    fig.add_trace(go.Bar(
        name="Kırmızı Çizgi", x=short_skus, y=red_lines, marker_color="rgba(220,38,38,0.15)",
        marker_line=dict(color=COLOR_RED, width=2), text=[fmt_tl(v) for v in red_lines], textposition="outside",
        textfont=dict(color=COLOR_RED, size=9)
    ))
    fig.update_layout(
        paper_bgcolor=BG_PAPER, plot_bgcolor=BG_PLOT, font=dict(size=11, family="Inter"),
        margin=dict(l=10, r=10, t=40, b=10), height=360, barmode="group",
        legend=dict(orientation="h", y=1.12, bgcolor="rgba(0,0,0,0)"),
        title=dict(text="Mevcut Fiyat vs Kırmızı Çizgi", font=dict(size=13, family="Inter"), x=0),
        xaxis=dict(gridcolor=GRID_COLOR), yaxis=dict(gridcolor=GRID_COLOR, tickprefix="₺", tickformat=",.0f")
    )
    st.plotly_chart(fig, use_container_width=True)

def render_sales_volume_pie(data: dict, filtered_skus: list | None = None, period_weeks: int = 4) -> None:
    products = [p for p in data["products"] if p["sku"] in filtered_skus] if filtered_skus else data["products"]
    labels   = [" ".join(p["name"].split()[:2]) for p in products]
    values   = [p.get("sales_per_week", 0) * period_weeks for p in products]
    colors_pie = ["#2563EB","#16A34A","#CA8A04","#DC2626","#7C3AED","#0891B2","#DB2777","#EA580C","#65A30D","#0284C7"]
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.45,
        marker=dict(colors=colors_pie, line=dict(color="rgba(255,255,255,0.35)", width=2)),
        textfont=dict(size=10, family="Inter"),
        hovertemplate="%{label}<br>Dönem Satış: %{value} adet<br>%{percent}<extra></extra>"
    ))
    fig.update_layout(
        paper_bgcolor=BG_PAPER, showlegend=False, margin=dict(l=0, r=0, t=10, b=0), height=270, font=dict(family="Inter")
    )
    st.plotly_chart(fig, use_container_width=True)

def render_category_profit_bar(data: dict, usd_rate: float, filtered_skus: list | None = None, period_weeks: int = 4) -> None:
    cat_profit: dict[str, float] = {}
    for p in data["products"]:
        if filtered_skus and p["sku"] not in filtered_skus: continue
        fifo_cost   = get_fifo_cost_tl(p, usd_rate)
        unit_profit = p["our_price_tl"] - fifo_cost
        cat         = p["category"].replace("_", " ").title()
        cat_profit[cat] = cat_profit.get(cat, 0) + unit_profit * (p.get("sales_per_week", 0) * period_weeks)
    items   = sorted(cat_profit.items(), key=lambda x: x[1], reverse=True)
    cats, profits = [i[0] for i in items], [i[1] for i in items]
    bar_colors = [COLOR_GREEN if v > 50_000 else COLOR_YELLOW if v > 20_000 else COLOR_RED for v in profits]
    fig = go.Figure(go.Bar(
        x=cats, y=profits, marker_color=bar_colors, opacity=0.85, text=[fmt_tl(v) for v in profits],
        textposition="outside", textfont=dict(size=9, family="Inter"), hovertemplate="<b>%{x}</b><br>₺%{y:,.0f}<extra></extra>"
    ))
    fig.update_layout(
        paper_bgcolor=BG_PAPER, plot_bgcolor=BG_PLOT, font=dict(size=11, family="Inter"),
        margin=dict(l=10, r=10, t=40, b=30), height=300, showlegend=False,
        title=dict(text="Kategori Bazlı Dönem Kârı", font=dict(size=13, family="Inter"), x=0),
        xaxis=dict(gridcolor=GRID_COLOR, tickfont=dict(size=9), tickangle=-30),
        yaxis=dict(gridcolor=GRID_COLOR, tickprefix="₺", tickformat=",.0f")
    )
    st.plotly_chart(fig, use_container_width=True)

def render_bcg_scatter(data: dict, usd_rate: float, filtered_skus: list | None = None, period_weeks: int = 4) -> None:
    names, period_list, profit_list, stock_list, cat_list = [], [], [], [], []
    for p in data["products"]:
        if filtered_skus and p["sku"] not in filtered_skus: continue
        fifo_cost   = get_fifo_cost_tl(p, usd_rate)
        unit_profit = p["our_price_tl"] - fifo_cost
        period_qty  = p.get("sales_per_week", 0) * period_weeks
        names.append(p["name"])
        period_list.append(period_qty)
        profit_list.append(unit_profit)
        stock_list.append(max(p["stock_qty"], 1))
        cat_list.append(p["category"].replace("_", " ").title())
    if not names:
        st.info("Filtre kriterlerine uyan ürün bulunamadı.")
        return
    max_stock    = max(stock_list)
    bubble_sizes = [max(8, int((s / max_stock) * 55)) for s in stock_list]
    unique_cats  = list(set(cat_list))
    palette      = ["#2563EB","#16A34A","#CA8A04","#DC2626","#7C3AED","#0891B2","#DB2777","#EA580C"]
    color_map = {c: palette[i % len(palette)] for i, c in enumerate(unique_cats)}
    fig = go.Figure()
    for cat in unique_cats:
        idx = [i for i, c in enumerate(cat_list) if c == cat]
        fig.add_trace(go.Scatter(
            x=[period_list[i] for i in idx], y=[profit_list[i] for i in idx],
            mode="markers", name=cat,
            marker=dict(size=[bubble_sizes[i] for i in idx], color=color_map[cat], opacity=0.75,
                        line=dict(color="rgba(255,255,255,0.4)", width=1.5)),
            text=[names[i] for i in idx], customdata=[[stock_list[i]] for i in idx],
            hovertemplate="<b>%{text}</b><br>Dönem Satış: %{x} adet<br>Kâr: ₺%{y:,.0f}<br>Stok: %{customdata[0]}<extra></extra>"
        ))
    avg_x, avg_y = sum(period_list)/len(period_list), sum(profit_list)/len(profit_list)
    max_x, max_y, min_y = max(period_list), max(profit_list), min(profit_list)
    fig.add_vline(x=avg_x, line_dash="dot", line_color=GRID_COLOR, opacity=0.9)
    fig.add_hline(y=avg_y, line_dash="dot", line_color=GRID_COLOR, opacity=0.9)
    for txt, xf, yf, col in [("YILDIZLAR", 0.87, 0.90, COLOR_GREEN), ("SORU İŞARETLERİ", 0.87, 0.25, COLOR_YELLOW),
                             ("NAKİT İNEKLERİ", 0.10, 0.90, COLOR_BLUE), ("KÖPEKLER", 0.10, None, COLOR_RED)]:
        y_val = max_y * yf if yf is not None else min_y + abs(min_y) * 0.15
        fig.add_annotation(x=max_x * xf, y=y_val, text=txt, showarrow=False, font=dict(color=col, size=10, family="Inter"))
    fig.update_layout(
        paper_bgcolor=BG_PAPER, plot_bgcolor=BG_PLOT, font=dict(size=11, family="Inter"),
        margin=dict(l=10, r=10, t=40, b=10), height=420,
        title=dict(text="BCG Matrisi — Kâr / Hacim / Stok", font=dict(size=13, family="Inter"), x=0),
        legend=dict(orientation="v", x=1.02, y=1, font=dict(size=9, family="Inter"), bgcolor="rgba(0,0,0,0)", bordercolor=GRID_COLOR, borderwidth=1),
        xaxis=dict(title="Dönem Satış Adedi", gridcolor=GRID_COLOR),
        yaxis=dict(title="Birim Kâr (TL)", gridcolor=GRID_COLOR, tickprefix="₺", tickformat=",.0f")
    )
    st.plotly_chart(fig, use_container_width=True)

def render_risk_scatter(data: dict, usd_rate: float, filtered_skus: list | None = None) -> None:
    names_r, margin_r, stock_r, cost_r, cat_r = [], [], [], [], []
    for p in data["products"]:
        if filtered_skus and p["sku"] not in filtered_skus: continue
        fifo_cost  = get_fifo_cost_tl(p, usd_rate)
        profit_tl  = p["our_price_tl"] - fifo_cost
        margin_pct = round((profit_tl / p["our_price_tl"]) * 100, 1) if p["our_price_tl"] else 0
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
    palette      = ["#2563EB","#16A34A","#CA8A04","#DC2626","#7C3AED","#0891B2","#DB2777","#EA580C"]
    color_map = {c: palette[i % len(palette)] for i, c in enumerate(unique_cats)}
    fig = go.Figure()
    for cat in unique_cats:
        idx = [i for i, c in enumerate(cat_r) if c == cat]
        fig.add_trace(go.Scatter(
            x=[margin_r[i] for i in idx], y=[stock_r[i]  for i in idx],
            mode="markers", name=cat,
            marker=dict(size=[bubble_sizes[i] for i in idx], color=color_map[cat], opacity=0.72,
                        line=dict(color="rgba(255,255,255,0.4)", width=1.5)),
            text=[names_r[i] for i in idx], customdata=[[cost_r[i]] for i in idx],
            hovertemplate="<b>%{text}</b><br>Marj: %{x:.1f}%<br>Stok: %{y} adet<br>FIFO: ₺%{customdata[0]:,.0f}<extra></extra>"
        ))
    fig.add_vline(x=0,  line_dash="dash", line_color=COLOR_RED,   opacity=0.5)
    fig.add_vline(x=10, line_dash="dot",  line_color=COLOR_YELLOW, opacity=0.4)
    fig.update_layout(
        paper_bgcolor=BG_PAPER, plot_bgcolor=BG_PLOT, font=dict(size=11, family="Inter"),
        margin=dict(l=10, r=10, t=40, b=10), height=370,
        title=dict(text="Risk Matrisi — Marj % vs Stok (Balon = FIFO Maliyet)", font=dict(size=13, family="Inter"), x=0),
        legend=dict(orientation="v", x=1.02, y=1, font=dict(size=9, family="Inter"), bgcolor="rgba(0,0,0,0)", bordercolor=GRID_COLOR, borderwidth=1),
        xaxis=dict(title="Marj %", gridcolor=GRID_COLOR, ticksuffix="%"), yaxis=dict(title="Stok Miktarı (Adet)", gridcolor=GRID_COLOR)
    )
    st.plotly_chart(fig, use_container_width=True)

def render_sales_trend_line(data: dict, filtered_skus: list | None = None, period_weeks: int = 4, top_n: int = 6) -> None:
    random.seed(42)
    products = [p for p in data["products"] if p["sku"] in filtered_skus] if filtered_skus else data["products"]
    products = sorted(products, key=lambda p: p.get("sales_per_week", 0), reverse=True)[:top_n]
    fig    = go.Figure()
    weeks  = [f"H-{period_weeks - i}" for i in range(period_weeks)] + ["Bu Hafta"]
    palette = ["#2563EB","#16A34A","#CA8A04","#DC2626","#7C3AED","#0891B2"]
    for idx, p in enumerate(products):
        spw    = p.get("sales_per_week", 0)
        series = [max(0, int(spw * (1 + random.uniform(-0.15, 0.15)))) for _ in range(period_weeks)] + [spw]
        fig.add_trace(go.Scatter(
            x=weeks, y=series, mode="lines+markers", name=" ".join(p["name"].split()[:2]),
            line=dict(color=palette[idx % len(palette)], width=2), marker=dict(size=5),
            hovertemplate="<b>%{fullData.name}</b><br>%{x}: %{y} adet<extra></extra>"
        ))
    fig.update_layout(
        paper_bgcolor=BG_PAPER, plot_bgcolor=BG_PLOT, font=dict(size=11, family="Inter"),
        margin=dict(l=10, r=10, t=40, b=10), height=310,
        title=dict(text="Satış Hızı Trendi (Haftalık Simülasyon)", font=dict(size=13, family="Inter"), x=0),
        legend=dict(orientation="h", y=-0.28, font=dict(size=9, family="Inter"), bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(gridcolor=GRID_COLOR), yaxis=dict(title="Haftalık Satış Adedi", gridcolor=GRID_COLOR)
    )
    st.plotly_chart(fig, use_container_width=True)

def render_projected_profit_bar(data: dict, usd_rate: float, filtered_skus: list | None = None, period_weeks: int = 4) -> None:
    rows_proj = []
    for p in data["products"]:
        if filtered_skus and p["sku"] not in filtered_skus: continue
        fifo_cost   = get_fifo_cost_tl(p, usd_rate)
        sellable    = min(p.get("sales_per_week", 0) * period_weeks, p["stock_qty"])
        rows_proj.append({"name": " ".join(p["name"].split()[:3]), "profit": (p["our_price_tl"] - fifo_cost) * sellable})
    rows_proj.sort(key=lambda r: r["profit"], reverse=True)
    names, profits = [r["name"] for r in rows_proj], [r["profit"] for r in rows_proj]
    colors  = [COLOR_GREEN if v > 0 else COLOR_RED for v in profits]
    fig = go.Figure(go.Bar(
        x=names, y=profits, marker_color=colors, opacity=0.85,
        text=[fmt_tl(v) for v in profits], textposition="outside", textfont=dict(size=8, family="Inter"),
        hovertemplate="<b>%{x}</b><br>Tahmini Kâr: ₺%{y:,.0f}<extra></extra>"
    ))
    fig.add_hline(y=0, line_color=GRID_COLOR, line_width=1.5)
    fig.update_layout(
        paper_bgcolor=BG_PAPER, plot_bgcolor=BG_PLOT, font=dict(size=11, family="Inter"),
        margin=dict(l=10, r=10, t=40, b=40), height=310, showlegend=False,
        title=dict(text="Dönem Sonu Tahmini Kâr Projeksiyonu (Stok Kısıtlı)", font=dict(size=13, family="Inter"), x=0),
        xaxis=dict(gridcolor=GRID_COLOR, tickfont=dict(size=8), tickangle=-35), yaxis=dict(gridcolor=GRID_COLOR, tickprefix="₺", tickformat=",.0f")
    )
    st.plotly_chart(fig, use_container_width=True)

if chart_key == "pie": render_sales_volume_pie(data, filtered_skus=dash_skus, period_weeks=period_weeks)
elif chart_key == "cat_bar": render_category_profit_bar(data, current_rate, filtered_skus=dash_skus, period_weeks=period_weeks)
elif chart_key == "bcg": render_bcg_scatter(data, current_rate, filtered_skus=dash_skus, period_weeks=period_weeks)
elif chart_key == "risk": render_risk_scatter(data, current_rate, filtered_skus=dash_skus)
elif chart_key == "trend": render_sales_trend_line(data, filtered_skus=dash_skus, period_weeks=period_weeks, top_n=int(dash_top_n))
elif chart_key == "proj": render_projected_profit_bar(data, current_rate, filtered_skus=dash_skus, period_weeks=period_weeks)
st.divider()

# ══════════════════════════════════════════════════════════════════════
# ACTION PANEL & AI RENDERING
# ══════════════════════════════════════════════════════════════════════
def render_action_panel(suggested_actions: list) -> None:
    if not suggested_actions:
        st.info("Gemini herhangi bir aksiyon önermedi.")
        return
    TYPE_META = {
        "price_update":       ("[FİYAT]",   "Fiyat Düzelt",     "action-critical"),
        "smart_bundle":       ("[BUNDLE]",  "Smart Bundle",     "action-bundle"),
        "dynamic_markdown":   ("[İNDİRİM]", "Kademeli İndirim", "action-markdown"),
        "gift_with_purchase": ("[HEDİYE]",  "Sepet Büyütucu",   "action-gift"),
        "liquidate":          ("[B2B]",     "B2B Tasfiye",      "action-liquidate"),
        "hold":               ("[BEKLE]",   "Pozisyon Koru",    "action-hold"),
    }
    for i, action in enumerate(suggested_actions):
        atype           = action.get("action_type", "hold")
        tag, label, css = TYPE_META.get(atype, ("[?]", "Bilinmiyor", "action-hold"))
        reason, old_price, btn_label = action.get("reason", ""), action.get("old_price_tl"), action.get("button_label", "Uygula")

        if atype == "price_update":
            new_p, chg_pct = action.get("new_price_tl", 0), action.get("price_change_pct", 0)
            sign = "+" if chg_pct > 0 else ""
            detail = f"<div class='action-detail'>Eski: <b>{fmt_tl(old_price)}</b> <span class='price-arrow'>&#8594;</span> Yeni: <b>{fmt_tl(new_p)}</b> <span class='price-up'>({sign}{chg_pct:.1f}%)</span></div>"
        elif atype == "smart_bundle":
            detail = f"<div class='action-detail'>Paket: <code>{action.get('sku','')}</code> + <code>{action.get('bundle_with_sku', '?')}</code> &#8594; <b>{fmt_tl(action.get('bundle_price_tl', 0))}</b></div>"
        elif atype == "dynamic_markdown":
            detail = f"<div class='action-detail'>Hedef: <b>{fmt_tl(action.get('new_price_tl', 0))}</b> ({action.get('markdown_pct', 0):.1f}% indirim, {action.get('steps', 3)} kademe)</div>"
        elif atype == "gift_with_purchase":
            detail = f"<div class='action-detail'><b>{fmt_tl(action.get('trigger_basket_tl', 50_000))}+</b> sepette bu ürün bedava eklensin.</div>"
        elif atype == "liquidate":
            detail = f"<div class='action-detail'>B2B Fiyatı: <b>{fmt_tl(action.get('b2b_price_tl', 0))}</b> (toptancı kanalı)</div>"
        else:
            detail = f"<div class='action-detail price-hold'>Fiyat korunuyor: <b>{fmt_tl(old_price)}</b></div>" if old_price else ""

        st.markdown(f"""
        <div class="action-card {css}">
            <div class="action-title">
                <span style="font-family:monospace;font-size:10px;opacity:0.6;padding:2px 6px;border-radius:4px;border:1px solid rgba(128,128,128,0.2);">{tag}</span>
                &nbsp;{label}&nbsp; <code style="font-size:11px;">{action.get('sku', '')}</code>
            </div>
            {detail}
            <div class="action-reason">"{reason}"</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button(f"Onayla: {btn_label}", key=f"act_{i}", use_container_width=True):
            st.success("Sistem emri onaylandı.")

def _build_report_markdown(result: dict) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# Bedülonca Piyasa İstihbarat Raporu",
        f"**Oluşturma tarihi:** {now}",
        "", "---", "",
        "## Strateji Özeti", "",
        result.get("final_strategy", "_Strateji üretilemedi._"), "",
    ]
    if result.get("trend_insights"):
        lines += ["## Trend İçgörüleri", "", result["trend_insights"], ""]
    if result.get("market_news"):
        lines += ["## Piyasa Haberleri", "", result["market_news"], ""]
    actions = result.get("suggested_actions", [])
    if actions:
        lines += ["## Önerilen Aksiyonlar", ""]
        for i, a in enumerate(actions, 1):
            lines.append(f"{i}. **{a.get('action_type','').upper()}** — `{a.get('sku','')}` — {a.get('reason','')}")
        lines.append("")
    if result.get("errors"):
        lines += ["## Sistem Uyarıları", ""]
        for err in result["errors"]:
            lines.append(f"- {err}")
        lines.append("")
    lines += ["---", "_Bu rapor Bedülonca V10.2 LangGraph + Gemini Motoru tarafından üretilmiştir._"]
    return "\n".join(lines)

def render_analysis_result(result: dict) -> None:
    report_md = _build_report_markdown(result)
    dl_col, info_col = st.columns([2, 5])
    with dl_col:
        st.download_button(
            label="Raporu İndir (.md)", data=report_md.encode("utf-8"),
            file_name=f"bedulonca_rapor_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
            mime="text/markdown", use_container_width=True, help="Strateji, haberler ve aksiyonları indir."
        )
    with info_col:
        st.markdown(f"Son analiz: **{st.session_state.get('analysis_ran_at', '—')}** &nbsp;·&nbsp; {len(result.get('suggested_actions', []))} aksiyon önerisi &nbsp;·&nbsp; {len(result.get('errors', []))} uyarı")
    st.divider()

    if result.get("errors"):
        with st.expander("Sistem Uyarıları", expanded=False):
            for err in result["errors"]: st.error(err)

    tab_str, tab_news, tab_chart, tab_act = st.tabs(["Strateji Özeti", "Piyasa Haberleri", "Durum Grafikleri", "Aksiyon Paneli"])
    with tab_str:
        st.markdown(result.get("final_strategy", "Strateji üretilemedi."))
        if result.get("trend_insights"): st.info(result["trend_insights"])
    with tab_news:
        news = result.get("market_news", "")
        st.markdown(news) if news else st.info("Piyasa haberi bulunamadı.")
    with tab_chart:
        cost_metrics = result.get("cost_metrics", {})
        if cost_metrics: render_price_vs_redline(cost_metrics)
        else: st.info("Grafik için cost_metrics verisi bulunamadı.")
    with tab_act:
        render_action_panel(result.get("suggested_actions", []))

# ══════════════════════════════════════════════════════════════════════
# ④ AI ANALYSIS ENGINE
# ══════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-label"><i class="fi fi-rr-brain-circuit"></i> LangGraph &amp; Gemini Karar Motoru · V10.2</div>', unsafe_allow_html=True)

if st.session_state["analysis_result"] is not None:
    st.success(f"Önbelleğe alınmış analiz mevcut ({st.session_state['analysis_ran_at']}) — Yenilemek için aşağıdaki butonu kullanın.")

c_input, c_btn = st.columns([4, 1])
with c_input:
    trigger_event = st.text_input("Tetikleyici olay", value="Haftalık fiyat ve kur optimizasyonu", label_visibility="collapsed")
with c_btn:
    btn_label_ai = "Analizi Yenile" if st.session_state["analysis_result"] is not None else "Otonom Analizi Başlat"
    run_button = st.button(btn_label_ai, type="primary", use_container_width=True)

if run_button:
    trending_skus_initial = [p["sku"] for p in sorted(data["products"], key=lambda p: p.get("sales_per_week", 0), reverse=True)][:15]
    initial_state: AgentState = {
        "trigger_event": trigger_event, "trending_skus": trending_skus_initial, "trend_insights": "",
        "competitor_analysis": {}, "cost_metrics": {}, "final_strategy": "", "suggested_actions": [],
        "crawl_log": "", "market_news": "", "errors": [],
    }

    lottie_ph = st.empty()
    lottie_ph.markdown(_lottie_html("https://lottie.host/0b1155c1-5ac5-4d9b-8cf0-f4d15313d505/QjT0LDsqon.lottie", 250), unsafe_allow_html=True)

    with st.status("Analiz aşamaları:", expanded=True) as status:
        st.write(f"Trend verileri taranıyor ({len(trending_skus_initial)} ürün)...")
        st.write("Piyasa haberleri ve rakip fiyatları çekiliyor...")
        st.write("FIFO maliyet hesaplaması yapılıyor...")
        st.write("Gemini V10.2 strateji motoru devreye giriyor...")

        result = get_graph().invoke(initial_state)

        st.session_state["analysis_result"] = result
        st.session_state["analysis_ran_at"] = datetime.now().strftime("%d.%m.%Y %H:%M")

        lottie_ph.empty()
        status.update(label="Analiz tamamlandı ve önbelleğe alındı.", state="complete", expanded=False)

if st.session_state["analysis_result"] is not None:
    render_analysis_result(st.session_state["analysis_result"])