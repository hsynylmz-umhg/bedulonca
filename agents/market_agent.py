# agents/market_agent.py
import json
import random
import time
from pathlib import Path
from state import AgentState

DATA_PATH  = Path(__file__).parent.parent / "data" / "mock_data.json"
DEMO_MODE  = True   # False → canlı scraping aktif olur (bkz. TODO bloğu)

def market_agent(state: AgentState) -> dict:
    """
    Piyasa Ajanı (PriceOps): Rakip fiyatları ile kendi fiyatlarımızı
    karşılaştırır. Her SKU için pozisyon analizi üretir.
    DEMO_MODE=True → mock veri + gecikme simülasyonu
    DEMO_MODE=False → canlı scraping (TODO)
    """
    errors              = []
    competitor_analysis = {}
    crawl_log_lines     = []

    # ── Veri Kaynağı Seçimi ───────────────────────────────────────────
    if not DEMO_MODE:
        # TODO: BeautifulSoup veya Selenium ile canlı e-ticaret scraping
        # işlemleri buraya eklenecek.
        pass
    else:
        crawl_log_lines.append("$ priceops --mode=demo --target=mock_data")
        crawl_log_lines.append("  [SİSTEM] DEMO MODU AKTİF — Cloudflare bypass riski yok.")
        crawl_log_lines.append("")

    # ── Mock Veri Yükleme ─────────────────────────────────────────────
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        errors.append("market_agent: mock_data.json bulunamadı.")
        return {"competitor_analysis": {}, "crawl_log": "", "errors": errors}
    except json.JSONDecodeError as e:
        errors.append(f"market_agent: JSON parse hatası — {e}")
        return {"competitor_analysis": {}, "crawl_log": "", "errors": errors}

    # ── Rakip Tarama (Demo Simülasyonu) ──────────────────────────────
    try:
        our_products = {p["sku"]: p for p in data["products"]}
        competitors  = data["competitors"]

        for competitor in competitors:
            if DEMO_MODE:
                delay = round(random.uniform(1.2, 2.5), 2)
                time.sleep(delay)
                found = len(competitor["listings"])
                crawl_log_lines.append(
                    f"  [TARAMA] {competitor['name']} mock verisi tarandı... "
                    f"{found} ürün bulundu. "
                    f"(simüle gecikme: {delay}s)"
                )

        crawl_log_lines.append("")
        crawl_log_lines.append("  [PİYASA] SKU bazlı fiyat analizi başlıyor...")

        # ── Fiyat Karşılaştırma ───────────────────────────────────────
        for sku, product in our_products.items():
            our_price    = product["our_price_tl"]
            sku_analysis = {
                "our_price_tl": our_price,
                "our_stock":    product["stock_qty"],
                "competitors":  [],
                "position":     None,
                "opportunity":  None,
            }

            rival_prices = []
            for competitor in competitors:
                listing = next(
                    (l for l in competitor["listings"] if l["sku"] == sku), None
                )
                if listing is None:
                    continue

                rival_price = listing["price_tl"]
                in_stock    = listing["stock"] == "var"
                diff_tl     = our_price - rival_price
                diff_pct    = round((diff_tl / rival_price) * 100, 1)

                sku_analysis["competitors"].append({
                    "name":     competitor["name"],
                    "price_tl": rival_price,
                    "in_stock": in_stock,
                    "diff_tl":  diff_tl,
                    "diff_pct": diff_pct,
                })

                if in_stock:
                    rival_prices.append(rival_price)

            if not rival_prices:
                sku_analysis["position"]    = "rakipsiz"
                sku_analysis["opportunity"] = "Stokta rakip yok — fiyat artırım fırsatı."
            elif our_price < min(rival_prices):
                sku_analysis["position"]    = "en_ucuz"
                sku_analysis["opportunity"] = "En düşük fiyat sahibiyiz — marjı koruyarak fiyat artışı değerlendirilebilir."
            elif our_price > max(rival_prices):
                sku_analysis["position"]    = "en_pahali"
                sku_analysis["opportunity"] = "Tüm rakiplerden pahalıyız — fiyat baskısı veya bundle ile değer artırımı gerekli."
            else:
                sku_analysis["position"]    = "rekabetci"
                sku_analysis["opportunity"] = "Fiyat orta bantta — trend veya stok avantajıyla öne çıkılabilir."

            competitor_analysis[sku] = sku_analysis

            if DEMO_MODE:
                crawl_log_lines.append(
                    f"  [SKU] {sku[:32]:<32} → pozisyon: {sku_analysis['position']}"
                )

        crawl_log_lines.append("")
        crawl_log_lines.append("  [✓] PriceOps tarama tamamlandı.")

    except KeyError as e:
        errors.append(f"market_agent: Beklenmeyen veri yapısı, eksik anahtar — {e}")
        return {
            "competitor_analysis": competitor_analysis,
            "crawl_log":           "\n".join(crawl_log_lines),
            "errors":              errors,
        }

    return {
        "competitor_analysis": competitor_analysis,
        "crawl_log":           "\n".join(crawl_log_lines),
        "errors":              errors,
    }