# agents/market_agent.py
import json
from pathlib import Path
from state import AgentState

DATA_PATH = Path(__file__).parent.parent / "data" / "mock_data.json"

def market_agent(state: AgentState) -> dict:
    """
    Piyasa Ajanı (PriceOps): Rakip fiyatları ile kendi fiyatlarımızı
    karşılaştırır. Her SKU için pozisyon analizi üretir.
    """
    errors = []
    competitor_analysis = {}

    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        errors.append("market_agent: mock_data.json bulunamadı.")
        return {"competitor_analysis": {}, "errors": errors}
    except json.JSONDecodeError as e:
        errors.append(f"market_agent: JSON parse hatası — {e}")
        return {"competitor_analysis": {}, "errors": errors}

    try:
        # Kendi ürünlerimizi SKU bazlı index'le
        our_products = {p["sku"]: p for p in data["products"]}
        competitors  = data["competitors"]

        for sku, product in our_products.items():
            our_price = product["our_price_tl"]
            sku_analysis = {
                "our_price_tl": our_price,
                "our_stock":    product["stock_qty"],
                "competitors":  [],
                "position":     None,   # ucuz / pahalı / rakipsiz
                "opportunity":  None,   # stok avantajı notu
            }

            rival_prices = []
            for competitor in competitors:
                listing = next(
                    (l for l in competitor["listings"] if l["sku"] == sku),
                    None
                )
                if listing is None:
                    continue

                rival_price = listing["price_tl"]
                in_stock    = listing["stock"] == "var"
                diff_tl     = our_price - rival_price
                diff_pct    = round((diff_tl / rival_price) * 100, 1)

                sku_analysis["competitors"].append({
                    "name":       competitor["name"],
                    "price_tl":   rival_price,
                    "in_stock":   in_stock,
                    "diff_tl":    diff_tl,       # negatif = bizden ucuz
                    "diff_pct":   diff_pct,
                })

                if in_stock:
                    rival_prices.append(rival_price)

            # Pozisyon belirle (sadece stokta olan rakiplere göre)
            if not rival_prices:
                sku_analysis["position"]   = "rakipsiz"
                sku_analysis["opportunity"] = "Stokta rakip yok — fiyat artırım fırsatı."
            elif our_price < min(rival_prices):
                sku_analysis["position"]   = "en_ucuz"
                sku_analysis["opportunity"] = "En düşük fiyat sahibiyiz — marjı koruyarak fiyat artışı değerlendirilebilir."
            elif our_price > max(rival_prices):
                sku_analysis["position"]   = "en_pahali"
                sku_analysis["opportunity"] = "Tüm rakiplerden pahalıyız — fiyat baskısı veya bundle ile değer artırımı gerekli."
            else:
                sku_analysis["position"]   = "rekabetci"
                sku_analysis["opportunity"] = "Fiyat orta bantta — trend veya stok avantajıyla öne çıkılabilir."

            competitor_analysis[sku] = sku_analysis

    except KeyError as e:
        errors.append(f"market_agent: Beklenmeyen veri yapısı, eksik anahtar — {e}")
        return {"competitor_analysis": competitor_analysis, "errors": errors}

    return {
        "competitor_analysis": competitor_analysis,
        "errors": errors,
    }