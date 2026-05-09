# state.py
from typing import TypedDict, List, Dict, Any, Annotated
import operator

class AgentState(TypedDict):
    """
    Bedülonca ajan ağının paylaşılan durum (state) nesnesi.
    Her ajan bu dict yapısını güncelleyerek bir sonrakine iletir.
    """
    
    # 1. Başlangıç Durumu
    trigger_event: str  # Örn: "Haftalık fiyat güncellemesi" veya "Trend analizi"
    
    # 2. Trend Ajanı Çıktıları
    trending_skus: List[str]  # Trend olan ürün kodları
    trend_insights: str       # Trendlere dair sözel özet
    
    # 3. Piyasa Ajanı (PriceOps) Çıktıları
    competitor_analysis: Dict[str, Any]  # Rakiplerin fiyat ve stok durumları
    
    # 4. Maliyet Ajanı Çıktıları
    cost_metrics: Dict[str, Any]  # Ürün bazlı gerçek maliyetler ve kırmızı çizgiler (min_margin)
    
    # 5. Stratejist Ajan (Gemini API) Çıktıları
    final_strategy: str       # Jürinin göreceği, Gemini'nin ürettiği açıklayıcı strateji metni
    
    # Annotated ve operator.add kullanarak listeye yeni aksiyonlar eklenmesini sağlarız
    # Bu, ajanın sistemde yapacağı "Paket Oluştur", "Fiyat İndir" gibi somut komutlardır.
    suggested_actions: Annotated[List[Dict[str, Any]], operator.add] 
    
    # Hata ve Log Yönetimi
    errors: Annotated[List[str], operator.add]