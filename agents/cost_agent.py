# agents/cost_agent.py
import json
from pathlib import Path
from state import AgentState

DATA_PATH = Path(__file__).parent.parent / "data" / "mock_data.json"

def cost_agent(state: AgentState) -> dict:
    """
    Maliyet Ajanı: Her SKU için gerçek maliyeti, kırmızı çizgiyi
    (minimum satış fiyatı) ve mevcut marj durumunu hesaplar.
    Asla zararına satışa izin vermez.
    """
    errors = []
    cost_metrics = {}

    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        errors.append("cost_agent: mock_data.json bulunamadı.")
        return {"cost_metrics": {}, "errors": errors}
    except json.JSONDecodeError as e:
        errors.append(f"cost_agent: JSON parse hatası — {e}")
        return {"cost_metrics": {}, "errors": errors}

    try:
        cfg      = data["market_config"]
        products = data["products"]

        commission_pct      = cfg["marketplace_commission_pct"] / 100
        cargo_base          = cfg["cargo_base_tl"]
        cargo_per_desi      = cfg["cargo_per_desi_tl"]
        inflation_pct       = cfg["monthly_inflation_pct"] / 100
        warehouse_monthly   = cfg["warehouse_monthly_cost_tl"]
        min_margin_pct      = cfg["min_margin_pct"] / 100

        # Depo maliyetini ürün başına dağıt (stok ağırlıklı)
        total_stock = sum(p["stock_qty"] for p in products)
        if total_stock == 0:
            errors.append("cost_agent: Toplam stok sıfır, depo maliyet dağılımı yapılamadı.")
            return {"cost_metrics": {}, "errors": errors}

        for product in products:
            sku        = product["sku"]
            cost_price = product["cost_price_tl"]
            our_price  = product["our_price_tl"]
            desi       = product["desi"]
            stock_qty  = product["stock_qty"]

            # --- Maliyet Bileşenleri ---
            cargo_cost       = cargo_base + (desi * cargo_per_desi)
            commission_cost  = round(our_price * commission_pct, 2)

            # Enflasyon etkisi: alış maliyetini gelecek aya project et
            inflation_adj_cost = round(cost_price * (1 + inflation_pct), 2)

            # Depo maliyeti: bu SKU'nun stok payı oranında
            stock_share        = stock_qty / total_stock
            warehouse_cost     = round(warehouse_monthly * stock_share, 2)

            # Toplam maliyet (satış başına)
            total_cost = round(
                inflation_adj_cost + cargo_cost + commission_cost + warehouse_cost, 2
            )

            # --- Kırmızı Çizgi ---
            # min_margin_pct hedef marjı koruyarak minimum satış fiyatı
            red_line_price = round(total_cost / (1 - min_margin_pct), 2)

            # --- Mevcut Durum ---
            current_margin_tl  = round(our_price - total_cost, 2)
            current_margin_pct = round((current_margin_tl / our_price) * 100, 1)
            is_above_red_line  = our_price >= red_line_price

            # --- Sağlık Durumu ---
            if not is_above_red_line:
                health = "KRİTİK"
                health_note = (
                    f"Mevcut fiyat kırmızı çizginin "
                    f"{round(red_line_price - our_price, 2)} TL ALTINDA. "
                    "Acil fiyat düzeltmesi gerekli."
                )
            elif current_margin_pct < min_margin_pct * 100 * 1.2:  # %20 tampon
                health = "UYARI"
                health_note = (
                    f"Marj kırmızı çizgiye yakın (%{current_margin_pct}). "
                    "Fiyat artışı veya maliyet optimizasyonu önerilir."
                )
            else:
                health = "SAĞLIKLI"
                health_note = f"Marj hedefin üzerinde (%{current_margin_pct}). Strateji esnekliği mevcut."

            cost_metrics[sku] = {
                # Ham bileşenler
                "cost_price_tl":        cost_price,
                "inflation_adj_cost_tl": inflation_adj_cost,
                "cargo_cost_tl":        cargo_cost,
                "commission_cost_tl":   commission_cost,
                "warehouse_cost_tl":    warehouse_cost,
                "total_cost_tl":        total_cost,
                # Kırmızı çizgi
                "red_line_price_tl":    red_line_price,
                # Mevcut durum
                "our_price_tl":         our_price,
                "current_margin_tl":    current_margin_tl,
                "current_margin_pct":   current_margin_pct,
                "is_above_red_line":    is_above_red_line,
                # Sağlık özeti (Gemini'ye ön-sindirilmiş)
                "health":               health,
                "health_note":          health_note,
            }

    except KeyError as e:
        errors.append(f"cost_agent: Eksik veri anahtarı — {e}")
        return {"cost_metrics": cost_metrics, "errors": errors}

    return {
        "cost_metrics": cost_metrics,
        "errors": errors,
    }