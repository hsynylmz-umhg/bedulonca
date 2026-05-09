# agents/trend_agent.py
import json
from state import AgentState

def trend_agent(state: AgentState) -> dict:
    """
    Trend Ajanı: Mock trend verisini okur, hangi ürünlerin
    gündemdeki oyunlarla ilişkili olduğunu tespit eder.
    """
    with open("data/mock_data.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    trends = data["trends"]
    trending_skus = trends["trending_skus"]

    # Oyun → donanım → ürün eşleştirmesi
    insights_lines = []
    for game, hw_list in trends["recommended_hardware"].items():
        hw_str = ", ".join(hw_list)
        insights_lines.append(f"• {game} → Gereksinim: {hw_str}")

    # SSD 2TB hangi oyunlarda geçiyor?
    ssd_games = [
        game for game, hw in trends["recommended_hardware"].items()
        if any("SSD" in hw_item for hw_item in hw)
    ]
    if ssd_games:
        insights_lines.append(
            f"\n📦 2TB SSD ({', '.join(ssd_games)}) için kritik donanım — "
            "stok fazlası bundle fırsatı."
        )

    trend_insights = (
        f"🎮 Gündemdeki oyunlar: {', '.join(trends['hot_games'])}\n\n"
        + "\n".join(insights_lines)
    )

    return {
        "trending_skus": trending_skus,
        "trend_insights": trend_insights,
    }