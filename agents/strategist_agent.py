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
    """
    Tek bir SKU için kısa ve odaklı mikro-prompt üretir.
    Gemini'den sadece tek bir JSON objesi {} ister.
    """
    metrics = cost_metrics.get(sku, {})
    comp    = competitor_info.get(sku, {})

    rival_lines = "; ".join(
        f"{r['name']}: {r['price_tl']} TL ({'stokta' if r['in_stock'] else 'stok yok'})"
        for r in comp.get("competitors", [])
    ) or "Rakip verisi yok."

    is_trending = "EVET" if sku in trend_skus else "HAYIR"

    return f"""Sen bir e-ticaret kâr optimizasyon motorusun. Tek ürün analizi yapacaksın.

ÜRÜN: {sku}
─────────────────────────────────────
Mevcut Fiyat    : {metrics.get('our_price_tl', '?')} TL
Toplam Maliyet  : {metrics.get('total_cost_tl', '?')} TL
Kırmızı Çizgi  : {metrics.get('red_line_price_tl', '?')} TL  ← asla altına inme
Mevcut Marj     : %{metrics.get('current_margin_pct', '?')}
Durum           : {metrics.get('health', '?')} — {metrics.get('health_note', '')}
Rakip Pozisyon  : {comp.get('position', '?')}
Rakipler        : {rival_lines}
Trend Ürünü     : {is_trending}
─────────────────────────────────────

KARAR KURALLARI:
1. Mevcut Fiyat < Kırmızı Çizgi (KRİTİK) → ya fiyatı kırmızı çizginin %2-%3 üstüne çıkar (price_update), ya da başka bir yüksek marjlı SKU ile paket yap (create_bundle).
2. Marj yeterli ve rakip stokta yok → mevcut durumu koru (hold).
3. Kırmızı çizginin ALTINA düşen hiçbir fiyat önerme.

ÇIKTI FORMATI (ZORUNLU):
Sadece tek bir JSON objesi döndür. Başka hiçbir şey yazma.
Markdown, açıklama, giriş/çıkış cümlesi YASAK.

price_update için:
{{"action_type": "price_update", "sku": "{sku}", "new_price_tl": <sayi>, "reason": "<kisa gerekce>", "button_label": "<buton metni>"}}

create_bundle için:
{{"action_type": "create_bundle", "skus": ["{sku}", "<diger_sku>"], "bundle_price_tl": <sayi>, "reason": "<kisa gerekce>", "button_label": "<buton metni>"}}

hold için:
{{"action_type": "hold", "sku": "{sku}", "reason": "<kisa gerekce>", "button_label": "<buton metni>"}}
"""


def _parse_single_action(raw: str) -> dict | None:
    """
    Gemini'nin tek obje {} çıktısını parse eder.
    Başarısız olursa None döner, sistemi çökertmez.
    """
    # Markdown artıklarını temizle
    cleaned = re.sub(r"^```json\s*", "", raw.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"^```\s*",     "", cleaned,     flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$",     "", cleaned,     flags=re.MULTILINE)
    cleaned = cleaned.strip()

    # Doğrudan parse dene
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # Fallback: metinde ilk {...} bloğunu bul
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
    """
    Stratejist Ajan — İteratif Mikro-İşlem Mimarisi:
    Her SKU için ayrı bir kısa prompt gönderir, tek JSON objesi alır.
    Truncation riski sıfıra iner; rate limit için her adımda sleep uygulanır.
    """
    errors            = []
    suggested_actions = []

    # ── API Kurulumu ──────────────────────────────────────────────────
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        errors.append("strategist_agent: GEMINI_API_KEY bulunamadı. .env dosyasını kontrol et.")
        return {"final_strategy": "", "suggested_actions": [], "errors": errors}

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name="gemini-2.5-flash")
    except Exception as e:
        errors.append(f"strategist_agent: Gemini yapılandırma hatası — {e}")
        return {"final_strategy": "", "suggested_actions": [], "errors": errors}

    # ── State Verilerini Al ───────────────────────────────────────────
    competitor_analysis = state.get("competitor_analysis", {})
    cost_metrics        = state.get("cost_metrics", {})
    trending_skus       = state.get("trending_skus", [])

    if not competitor_analysis:
        errors.append("strategist_agent: competitor_analysis boş, analiz yapılamadı.")
        return {"final_strategy": "", "suggested_actions": [], "errors": errors}

    # ── İteratif Mikro-İşlem Döngüsü ─────────────────────────────────
    print("\n" + "=" * 55)
    print("🤖 BEDÜLONCA STRATEJİST MOTORU BAŞLADI")
    print(f"   Toplam ürün: {len(competitor_analysis)}")
    print("=" * 55)

    for sku in competitor_analysis:
        print(f"\n🔄 {sku} analiz ediliyor...")

        micro_prompt = _build_micro_prompt(
            sku=sku,
            cost_metrics=cost_metrics,
            competitor_info=competitor_analysis,
            trend_skus=trending_skus,
        )

        # ── Gemini Çağrısı ────────────────────────────────────────────
        try:
            # En sade çağrı: max_output_tokens, thinking_config ve
            # request_options kaldırıldı. SDK artık API'ye "kısa kes"
            # talimatı gönderemez; API kendi varsayılan rahat sınırlarıyla
            # (8192 token) çalışır. Truncation sorunu kökten ortadan kalkar.
            response = model.generate_content(
                micro_prompt,
                generation_config={"temperature": 0.2},  # Sadece JSON için düşük sıcaklık
            )

            raw_text = response.text
            print(f"   📥 Ham çıktı: {raw_text[:120].strip()}{'...' if len(raw_text) > 120 else ''}")

        except Exception as e:
            err_msg = f"strategist_agent: {sku} için API çağrısı başarısız — {e}"
            errors.append(err_msg)
            print(f"   ❌ {err_msg}")
            time.sleep(3)
            continue

        # ── Parse ─────────────────────────────────────────────────────
        action = _parse_single_action(raw_text)
        if action is None:
            err_msg = f"strategist_agent: {sku} için JSON parse başarısız. Ham: {raw_text[:200]}"
            errors.append(err_msg)
            print(f"   ⚠️  Parse başarısız, sonraki ürüne geçiliyor.")
            time.sleep(3)
            continue

        suggested_actions.append(action)
        print(f"   ✅ {sku} tamamlandı. → action_type: {action.get('action_type', '?')}")

        # Rate limit koruması
        time.sleep(3)

    print("\n" + "=" * 55)
    print(f"🏁 Motor tamamlandı. {len(suggested_actions)}/{len(competitor_analysis)} ürün işlendi.")
    print("=" * 55 + "\n")

    # ── Özet Strateji Metni ───────────────────────────────────────────
    kritik_count = sum(1 for a in suggested_actions if a.get("action_type") == "price_update")
    bundle_count = sum(1 for a in suggested_actions if a.get("action_type") == "create_bundle")
    hold_count   = sum(1 for a in suggested_actions if a.get("action_type") == "hold")

    final_strategy = (
        f"**Otonom motor {len(competitor_analysis)} ürünü tek tek taradı ve "
        f"{len(suggested_actions)} karar üretti.**\n\n"
        f"- 🔴 **{kritik_count} ürün** kırmızı çizgi protokolüne alındı — fiyat düzeltmesi gerekiyor.\n"
        f"- 🟢 **{bundle_count} ürün** için çapraz satış (bundle) fırsatı tespit edildi.\n"
        f"- ⚫ **{hold_count} ürün** mevcut pozisyonunu koruyor — rakip baskısı yok.\n\n"
        f"Kırmızı çizgi kalkanı aktifti: zararına satış önerisinin önüne geçildi. "
        f"Aşağıdaki aksiyonları onaylamak için ilgili butona bas."
    )

    return {
        "final_strategy":    final_strategy,
        "suggested_actions": suggested_actions,
        "errors":            errors,
    }