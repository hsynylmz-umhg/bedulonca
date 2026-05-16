# agents/strategist_agent.py
import os
import json
import re
import time
from dotenv import load_dotenv
import google.generativeai as genai
from state import AgentState

load_dotenv()


def _build_micro_prompt(
    sku: str,
    cost_metrics: dict,
    competitor_info: dict,
    trend_skus: list,
) -> str:
    metrics       = cost_metrics.get(sku, {})
    comp          = competitor_info.get(sku, {})
    current_price = metrics.get("our_price_tl", 0)
    fifo_cost     = metrics.get("fifo_cost_tl", metrics.get("total_cost_tl", 0))
    weekly_sales  = metrics.get("sales_per_week", 0)

    rival_lines = "; ".join(
        f"{r['name']}: {r['price_tl']} TL ({'stokta' if r['in_stock'] else 'stok yok'})"
        for r in comp.get("competitors", [])
    ) or "Rakip verisi yok."

    is_trending = "EVET" if sku in trend_skus else "HAYIR"

    # Ölü stok tespiti (4 haftada <4 adet)
    monthly_sales = weekly_sales * 4 if weekly_sales else 0
    is_dead_stock = monthly_sales < 4

    return f"""Sen bir e-ticaret kâr ve stok optimizasyon motorusun. Tek ürün analizi yapacaksın.

ÜRÜN: {sku}
─────────────────────────────────────
Mevcut Fiyat     : {current_price} TL
FIFO Birim Maliyet: {fifo_cost} TL
Toplam Maliyet   : {metrics.get('total_cost_tl', '?')} TL
Kırmızı Çizgi   : {metrics.get('red_line_price_tl', '?')} TL  ← asla altına inme
Mevcut Marj      : %{metrics.get('current_margin_pct', '?')}
Durum            : {metrics.get('health', '?')} — {metrics.get('health_note', '')}
Rakip Pozisyon   : {comp.get('position', '?')}
Rakipler         : {rival_lines}
Trend Ürünü      : {is_trending}
Ölü Stok mu?     : {"EVET — aylık {monthly_sales} adet satış" if is_dead_stock else "HAYIR"}
─────────────────────────────────────

KARAR KURALLARI:
1. KRİTİK durum (fiyat < kırmızı çizgi): price_update ile kırmızı çizginin %2-3 üstüne çıkar.
2. Ölü stok (aylık <4 adet, sağlıklı marj): smart_bundle veya gift_with_purchase öner.
3. Ölü stok (aylık <4 adet, düşük marj): dynamic_markdown ile %2-5 kademeli düşür.
4. Ölü stok + KRİTİK: liquidate (B2B toptancıya zararına sat, stoğu temizle).
5. Marj yeterli + rakip stokta yok: hold.
6. Kırmızı çizginin ALTINA düşen hiçbir fiyat önerme (liquidate hariç — o ayrı kanal).

ÇIKTI FORMATI (ZORUNLU):
Sadece tek bir JSON objesi döndür. Markdown, açıklama YASAK.

Seçenekler:

price_update:
{{"action_type":"price_update","sku":"{sku}","old_price_tl":{current_price},"new_price_tl":<sayi>,"price_change_pct":<float>,"reason":"<gerekce>","button_label":"<metin>"}}

smart_bundle:
{{"action_type":"smart_bundle","sku":"{sku}","bundle_with_sku":"<lokomotif_sku>","old_price_tl":{current_price},"bundle_price_tl":<sayi>,"reason":"<gerekce>","button_label":"<metin>"}}

dynamic_markdown:
{{"action_type":"dynamic_markdown","sku":"{sku}","old_price_tl":{current_price},"new_price_tl":<sayi>,"markdown_pct":<float_2_ile_5_arasi>,"steps":3,"reason":"<gerekce>","button_label":"<metin>"}}

gift_with_purchase:
{{"action_type":"gift_with_purchase","sku":"{sku}","trigger_basket_tl":50000,"old_price_tl":{current_price},"reason":"<gerekce>","button_label":"<metin>"}}

liquidate:
{{"action_type":"liquidate","sku":"{sku}","old_price_tl":{current_price},"b2b_price_tl":<maliyet_altı_fiyat>,"reason":"<gerekce>","button_label":"<metin>"}}

hold:
{{"action_type":"hold","sku":"{sku}","old_price_tl":{current_price},"reason":"<gerekce>","button_label":"<metin>"}}
"""


def _parse_single_action(raw: str) -> dict | None:
    cleaned = re.sub(r"^```json\s*", "", raw.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"^```\s*",     "", cleaned,     flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$",     "", cleaned,     flags=re.MULTILINE)
    cleaned = cleaned.strip()

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    obj_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if obj_match:
        try:
            parsed = json.loads(obj_match.group(0))
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    return None


def strategist_agent(state: AgentState) -> dict:
    errors            = []
    suggested_actions = []

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        errors.append("strategist_agent: GEMINI_API_KEY bulunamadı.")
        return {"final_strategy": "", "suggested_actions": [], "errors": errors}

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name="gemini-2.5-flash-lite")
    except Exception as e:
        errors.append(f"strategist_agent: Gemini yapılandırma hatası — {e}")
        return {"final_strategy": "", "suggested_actions": [], "errors": errors}

    competitor_analysis = state.get("competitor_analysis", {})
    cost_metrics        = state.get("cost_metrics", {})
    trending_skus       = state.get("trending_skus", [])

    if not competitor_analysis:
        errors.append("strategist_agent: competitor_analysis boş.")
        return {"final_strategy": "", "suggested_actions": [], "errors": errors}

    print("\n" + "=" * 55)
    print("🤖 BEDÜLONCA STRATEJİST V9 BAŞLADI")
    print(f"   Model: gemini-1.5-flash | Ürün: {len(competitor_analysis)}")
    print("=" * 55)

    for sku in competitor_analysis:
        print(f"\n🔄 {sku} analiz ediliyor...")

        micro_prompt = _build_micro_prompt(
            sku=sku,
            cost_metrics=cost_metrics,
            competitor_info=competitor_analysis,
            trend_skus=trending_skus,
        )

        try:
            response = model.generate_content(
                micro_prompt,
                generation_config={"temperature": 0.2},
            )
            raw_text = response.text
            print(f"   📥 {raw_text[:100].strip()}{'...' if len(raw_text) > 100 else ''}")
        except Exception as e:
            err_msg = f"strategist_agent: {sku} API hatası — {e}"
            errors.append(err_msg)
            print(f"   ❌ {err_msg}")
            time.sleep(4)
            continue

        action = _parse_single_action(raw_text)
        if action is None:
            err_msg = f"strategist_agent: {sku} parse başarısız. Ham: {raw_text[:200]}"
            errors.append(err_msg)
            time.sleep(4)
            continue

        suggested_actions.append(action)
        print(f"   ✅ → action_type: {action.get('action_type', '?')}")
        time.sleep(4)

    print("\n" + "=" * 55)
    print(f"🏁 {len(suggested_actions)}/{len(competitor_analysis)} ürün işlendi.")
    print("=" * 55 + "\n")

    kritik   = sum(1 for a in suggested_actions if a.get("action_type") == "price_update")
    bundle   = sum(1 for a in suggested_actions if a.get("action_type") == "smart_bundle")
    markdown = sum(1 for a in suggested_actions if a.get("action_type") == "dynamic_markdown")
    gift     = sum(1 for a in suggested_actions if a.get("action_type") == "gift_with_purchase")
    liq      = sum(1 for a in suggested_actions if a.get("action_type") == "liquidate")
    hold     = sum(1 for a in suggested_actions if a.get("action_type") == "hold")

    final_strategy = (
        f"**Otonom motor {len(competitor_analysis)} ürünü taradı, "
        f"{len(suggested_actions)} karar üretti.**\n\n"
        f"| Strateji | Ürün Sayısı |\n|---|---|\n"
        f"| 🔴 Fiyat Düzeltme | {kritik} |\n"
        f"| 🟢 Smart Bundle | {bundle} |\n"
        f"| 🟡 Kademeli İndirim | {markdown} |\n"
        f"| 🎁 Sepet Büyütücü Hediye | {gift} |\n"
        f"| 💀 Tasfiye (B2B) | {liq} |\n"
        f"| ⚫ Pozisyon Koru | {hold} |\n\n"
        f"FIFO maliyet algoritması aktifti: her ürünün gerçek stok maliyeti hesaplandı."
    )

    return {
        "final_strategy":    final_strategy,
        "suggested_actions": suggested_actions,
        "errors":            errors,
    }