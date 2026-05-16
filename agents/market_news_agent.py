"""
Bedülonca V9 — Market News & Competitor Intelligence Agent
- DuckDuckGo Search (ddgs) ile çift yönlü OSINT istihbaratı.
- Gemini AI entegrasyonu ile ham veriyi temizler, özetler ve kritik verileri (fiyat, zam) kırmızı ile vurgular.
- LangGraph state pipeline ve standalone chatbot kullanımı için ikili arayüz.
"""

import os
import time
from ddgs import DDGS
import google.generativeai as genai
from state import AgentState

# ── Gemini Temizleme Filtresi ─────────────────────────────────────────
def _clean_with_gemini(raw_text: str) -> str:
    """
    Kirli arama sonuçlarını Gemini AI'a göndererek temiz, yapılandırılmış
    ve okunabilir bir özet haline getirir. Kritik bilgiler kırmızıya boyanır.
    """
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return raw_text  # API yoksa mecburen ham veriyi dön
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash-lite")
    
    prompt = f"""Sen kıdemli bir piyasa istihbarat analistisin. 
Sana internetten çekilmiş "kirli ve düzensiz" web arama sonuçları veriyorum. Görevin bu veriyi temizleyip okunması çok kolay bir CEO özetine çevirmek.

KURALLAR:
1. Sadece net gerçekleri, fiyatları ve gelişmeleri madde işaretleriyle yaz. Reklam kokan veya gereksiz site açıklamalarını tamamen sil.
2. ÖNEMLİ: Fiyat rakamlarını ve zam kelimelerini KESİNLİKLE <span style='color:#FF4B4B;'> ve </span> etiketleri içine al. Markdown içinde HTML kullanımına izin verilmiştir.
3. Çıktı Markdown formatında olmalı ancak HTML tag'leri bozulmamalı.
4. Başlıkları şu şekilde kullan: "📰 Güncel Piyasa Haberleri" ve "🏪 Rakip Fiyat İstihbaratı".

HAM VERİ:
{raw_text}
"""
    try:
        response = model.generate_content(prompt, generation_config={"temperature": 0.2})
        return response.text
    except Exception as e:
        print(f"⚠️ Gemini Temizleme Hatası: {e}")
        return raw_text  # Hata olursa sistemi çökertme, ham veriyi dön


# ── Temel Arama Motoru ────────────────────────────────────────────────
def _raw_search(query: str, num: int = 3) -> list[dict]:
    """
    DuckDuckGo üzerinden sorgu yapar.
    Hata durumunda boş liste döner, sistemi patlatmaz.
    """
    try:
        with DDGS() as ddgs:
            results = ddgs.text(
                query,
                region="tr-tr",
                max_results=num,
            )
            return [
                {
                    "title":   item.get("title",  ""),
                    "snippet": item.get("body",   ""),
                    "link":    item.get("href",   ""),
                }
                for item in (results or [])
            ]
    except Exception as e:
        print(f"⚠️ DuckDuckGo arama hatası [{query[:40]}]: {e}")
        return []


# ── Çift Yönlü İstihbarat Raporu ─────────────────────────────────────
def fetch_intelligence_report(sku: str, product_name: str) -> str:
    """
    Çift yönlü istihbarat raporu üretir. Ham veriyi Gemini ile temizleyip döner.
    """
    words      = product_name.split()
    short_name = " ".join(words[:3]) if len(words) > 3 else product_name

    news_query   = f"{short_name} inceleme OR haber OR vergi OR zam"
    news_results = _raw_search(news_query, num=3)

    time.sleep(2)

    rival_query   = f"{short_name} fiyat site:cimri.com OR site:akakce.com"
    rival_results = _raw_search(rival_query, num=3)

    lines: list[str] = []

    if news_results:
        lines.append("### 📰 Güncel Haberler & Piyasa Sinyalleri")
        for r in news_results:
            lines.append(f"- **{r['title']}**\n  {r['snippet']}")
        lines.append("")
    else:
        lines.append("### 📰 Haber Araması")
        lines.append(f"- '{news_query}' için sonuç bulunamadı.\n")

    if rival_results:
        lines.append("### 🏪 Rakip Fiyat İstihbaratı (Cimri / Akakçe)")
        for r in rival_results:
            lines.append(f"- **{r['title']}**\n  {r['snippet']}")
        lines.append("")
    else:
        lines.append("### 🏪 Rakip Fiyat İstihbaratı")
        lines.append(f"- '{rival_query}' için sonuç bulunamadı.\n")

    raw_report = "\n".join(lines)
    
    # Ham veriyi Gemini'ye gönderip temizlenmiş halini döndürüyoruz
    clean_report = _clean_with_gemini(raw_report)
    return clean_report


# ── Geriye Dönük Uyumluluk Arayüzü ───────────────────────────────────
def search_product_news(product_name: str, num: int = 4) -> list[dict]:
    words      = product_name.split()
    short_name = " ".join(words[:3]) if len(words) > 3 else product_name

    news_query  = f"{short_name} fiyat piyasa haber 2025"
    news_results = _raw_search(news_query, num=num)

    time.sleep(2)

    rival_query   = f"{short_name} fiyat site:cimri.com OR site:akakce.com"
    rival_results = _raw_search(rival_query, num=num)

    seen  : set[str]   = set()
    merged: list[dict] = []
    for item in news_results + rival_results:
        if item["link"] not in seen:
            seen.add(item["link"])
            merged.append(item)

    return merged[: num * 2]


# ── LangGraph Ajan Arayüzü ────────────────────────────────────────────
def market_news_agent(state: AgentState) -> dict:
    trending = state.get("trending_skus", [])

    if not trending:
        return {"market_news": "Trend ürün bulunamadı, haber araması yapılmadı."}

    blocks: list[str] = []
    for sku in trending[:3]:
        readable = sku.replace("-", " ").title()
        report   = fetch_intelligence_report(sku=sku, product_name=readable)
        blocks.append(f"## 🔍 {readable}\n\n{report}")

        time.sleep(2)

    if not blocks:
        return {"market_news": "DuckDuckGo araması sonuç döndürmedi."}

    return {"market_news": "\n\n---\n\n".join(blocks)}