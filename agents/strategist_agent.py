# agents/strategist_agent.py
import os
import json
import re
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai
from state import AgentState

load_dotenv()

def _build_prompt(state: AgentState) -> str:
    """State verilerini Gemini'ye gönderilecek prompt'a dönüştürür."""

    trend_block = state.get("trend_insights", "Veri yok.")

    # Rakip analizini okunabilir metne çevir
    competitor_lines = []
    for sku, analysis in state.get("competitor_analysis", {}).items():
        rivals = analysis.get("competitors", [])
        rival_summary = "; ".join(
            f"{r['name']}: {r['price_tl']} TL ({'stokta' if r['in_stock'] else 'stok yok'})"
            for r in rivals
        ) or "Rakip bulunamadı."
        competitor_lines.append(
            f"- {sku}: Bizim fiyatımız {analysis['our_price_tl']} TL | "
            f"Pozisyon: {analysis['position']} | Rakipler: {rival_summary} | "
            f"Fırsat: {analysis['opportunity']}"
        )
    competitor_block = "\n".join(competitor_lines) or "Veri yok."

    # Maliyet özetini hazırla
    cost_lines = []
    for sku, metrics in state.get("cost_metrics", {}).items():
        cost_lines.append(
            f"- {sku}: Toplam maliyet {metrics['total_cost_tl']} TL | "
            f"Kırmızı çizgi {metrics['red_line_price_tl']} TL | "
            f"Mevcut fiyat {metrics['our_price_tl']} TL | "
            f"Durum: {metrics['health']} — {metrics['health_note']}"
        )
    cost_block = "\n".join(cost_lines) or "Veri yok."

    return f"""Sen Bedülonca'nın baş e-ticaret stratejistisin. \
Aşağıdaki verileri analiz ederek KOBİ sahibine somut, uygulanabilir kararlar üret.

KURAL: Kırmızı çizginin (red_line_price_tl) ALTINA düşen hiçbir fiyat önerme. \
Zararına satışa kesinlikle izin verme.

=== TREND ANALİZİ ===
{trend_block}

=== PİYASA & RAKİP ANALİZİ ===
{competitor_block}

=== MALİYET & KIRMIZI ÇİZGİ ===
{cost_block}

=== ÇIKTI FORMATI (ZORUNLU) ===
Yanıtını TAM OLARAK aşağıdaki yapıda ver. Başka hiçbir şey yazma.

<strategy>
Buraya jüriye ve KOBİ sahibine hitap eden, 3-5 cümlelik Türkçe stratejik analiz yaz.
</strategy>

<actions>
[
  {{
    "action_type": "price_update",
    "sku": "SKU_KODU",
    "new_price_tl": 0000,
    "reason": "Kısa gerekçe",
    "button_label": "Butonda görünecek metin"
  }}
]
</actions>

action_type değerleri yalnızca şunlar olabilir: price_update, create_bundle, hold
create_bundle için "skus" (array) ve "bundle_price_tl" alanlarını ekle.
hold için "sku" ve "reason" yeterli; new_price_tl ekleme.
"""


def _parse_response(raw: str) -> tuple[str, list[dict]]:
    """
    Gemini çıktısından <strategy> ve <actions> bloklarını ayıklar.
    Hatalı JSON durumunda güvenli fallback döner.
    """
    strategy_match = re.search(r"<strategy>(.*?)</strategy>", raw, re.DOTALL)
    actions_match  = re.search(r"<actions>(.*?)</actions>",   raw, re.DOTALL)

    strategy_text = strategy_match.group(1).strip() if strategy_match else raw.strip()

    actions = []
    if actions_match:
        raw_json = actions_match.group(1).strip()
        # Gemini bazen ```json ... ``` ekler — temizle
        raw_json = re.sub(r"```json|```", "", raw_json).strip()
        try:
            parsed = json.loads(raw_json)
            if isinstance(parsed, list):
                actions = parsed
        except json.JSONDecodeError:
            pass  # Hata caller'da errors'a yazılacak

    return strategy_text, actions


def strategist_agent(state: AgentState) -> dict:
    """
    Stratejist Ajan: Tüm ajan çıktılarını Gemini API'ye gönderir,
    strateji metni ve aksiyon listesi üretir.
    """
    errors = []

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        errors.append("strategist_agent: GEMINI_API_KEY bulunamadı. .env dosyasını kontrol et.")
        return {"final_strategy": "", "suggested_actions": [], "errors": errors}

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            generation_config=genai.GenerationConfig(
                temperature=0.4,   # Düşük: tutarlı, halüsinasyonsuz karar
                max_output_tokens=1024,
            ),
        )
    except Exception as e:
        errors.append(f"strategist_agent: Gemini yapılandırma hatası — {e}")
        return {"final_strategy": "", "suggested_actions": [], "errors": errors}

    prompt = _build_prompt(state)

    try:
        response     = model.generate_content(prompt)
        raw_text     = response.text
    except Exception as e:
        errors.append(f"strategist_agent: Gemini API çağrısı başarısız — {e}")
        return {"final_strategy": "", "suggested_actions": [], "errors": errors}

    final_strategy, suggested_actions = _parse_response(raw_text)

    # Parse başarısız olduysa logla ama uygulamayı durdurma
    if not suggested_actions:
        errors.append(
            "strategist_agent: <actions> bloğu parse edilemedi veya boş döndü. "
            "Ham çıktı state'e yazıldı."
        )

    return {
        "final_strategy":    final_strategy,
        "suggested_actions": suggested_actions,
        "errors":            errors,
    }