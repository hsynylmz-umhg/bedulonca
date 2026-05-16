# agents/cost_agent.py
"""
FIFO Maliyet Ajanı
- inventory_batches dizisini okur
- Satılan adetleri en eski partiden başlayarak düşer
- FIFO maliyeti, kırmızı çizgiyi ve marjı hesaplar
"""
import json
from pathlib import Path
from state import AgentState

DATA_PATH = Path(__file__).parent.parent / "data" / "mock_data.json"


def _load_data() -> dict:
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _fifo_cost(product: dict, current_usd_rate: float) -> dict:
    """
    FIFO algoritması:
    - inventory_batches dizisini tarihsel sıraya göre işler.
    - Toplam stok içinden satılmış kabul edilen miktarı (sales_per_week * 4)
      en eski partilerden düşerek kalan stoğun gerçek FIFO maliyetini bulur.
    - Kalan stok tamamen en eski partide ise onun maliyetini,
      birden fazla partiye yayılıyorsa ağırlıklı ortalama kullanır.
    """
    batches      = product.get("inventory_batches", [])
    buy_currency = product.get("buy_currency", "USD")
    is_usd       = buy_currency == "USD"

    if not batches:
        # Eski veri uyumluluğu: inventory_batches yoksa cost_price_tl kullan
        cost_tl = product.get("cost_price_tl", 0)
        return {
            "fifo_unit_cost_tl": cost_tl,
            "fifo_method":       "legacy",
            "batches_detail":    [],
        }

    # Satılmış kabul edilen adet (son 4 haftalık satış)
    sold_qty = product.get("sales_per_week", 0) * 4

    # Kalan stoğu FIFO ile takip et
    remaining_sold = sold_qty
    remaining_batches = []

    for batch in batches:
        qty = batch["qty"]
        if remaining_sold <= 0:
            remaining_batches.append({"qty": qty, "buy_price_usd": batch["buy_price_usd"]})
            continue
        if remaining_sold >= qty:
            remaining_sold -= qty
            # Bu parti tamamen satıldı, kalan stoka katılmaz
        else:
            leftover = qty - remaining_sold
            remaining_batches.append({"qty": leftover, "buy_price_usd": batch["buy_price_usd"]})
            remaining_sold = 0

    # Kalan partilerin ağırlıklı ortalama maliyetini hesapla
    total_qty  = sum(b["qty"] for b in remaining_batches)
    if total_qty == 0:
        # Tüm stok satılmış, son partinin maliyetini al
        last = batches[-1]
        raw_price = last["buy_price_usd"]
    else:
        raw_price = sum(b["buy_price_usd"] * b["qty"] for b in remaining_batches) / total_qty

    # TL'ye çevir
    if is_usd:
        fifo_cost_tl = raw_price * current_usd_rate
    else:
        fifo_cost_tl = raw_price  # TRY ise zaten TL

    return {
        "fifo_unit_cost_tl": round(fifo_cost_tl, 2),
        "fifo_method":       "fifo_weighted",
        "batches_detail":    remaining_batches,
    }


def cost_agent(state: AgentState) -> dict:
    data         = _load_data()
    cfg          = data["market_config"]
    usd_rate     = cfg.get("current_usd_rate", 38.50)
    min_margin   = cfg.get("min_margin_pct", 12.0) / 100
    commission   = cfg.get("marketplace_commission_pct", 8.5) / 100
    cargo_base   = cfg.get("cargo_base_tl", 45)
    cargo_desi   = cfg.get("cargo_per_desi_tl", 12)

    cost_metrics: dict = {}

    for p in data["products"]:
        sku       = p["sku"]
        sell_price = p["our_price_tl"]
        desi      = p.get("desi", 1)

        fifo_info    = _fifo_cost(p, usd_rate)
        fifo_cost_tl = fifo_info["fifo_unit_cost_tl"]

        cargo_cost   = cargo_base + (cargo_desi * desi)
        commission_c = sell_price * commission
        total_cost   = fifo_cost_tl + cargo_cost + commission_c

        # Kırmızı çizgi: min_margin karşılayan en düşük satış fiyatı
        # total_cost / (1 - min_margin)
        red_line     = round(total_cost / (1 - min_margin), 2)
        current_margin = round(((sell_price - total_cost) / sell_price) * 100, 2) if sell_price else 0

        if sell_price < red_line:
            health      = "KRİTİK"
            health_note = f"Fiyat kırmızı çizginin {fmt(red_line - sell_price)} altında"
        elif current_margin < min_margin * 100 * 1.2:
            health      = "UYARI"
            health_note = f"Marj hedefin %20 yakınında ({current_margin:.1f}%)"
        else:
            health      = "SAĞLIKLI"
            health_note = f"Marj hedefin üzerinde ({current_margin:.1f}%)"

        cost_metrics[sku] = {
            "our_price_tl":       sell_price,
            "fifo_cost_tl":       fifo_cost_tl,
            "total_cost_tl":      round(total_cost, 2),
            "red_line_price_tl":  red_line,
            "current_margin_pct": current_margin,
            "health":             health,
            "health_note":        health_note,
            "fifo_method":        fifo_info["fifo_method"],
        }

    return {"cost_metrics": cost_metrics}


def fmt(v: float) -> str:
    return f"₺{v:,.0f}".replace(",", ".")