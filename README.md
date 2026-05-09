# ⚡ Bedülonca (Artış Teşkilatı)

**Otonom Kâr Marjı Optimizasyonu ve Dinamik Fiyatlandırma Ajanı**  
*BTK Akademi, Google & Girvak AI Hackathon 2026 Başvurusu*

Bedülonca, e-ticaret platformlarında satış yapan KOBİ'ler için geliştirilmiş, **Google Gemini API** ve **LangGraph** destekli çoklu-ajan (Multi-Agent) finans ve strateji sistemidir. Rakiplerin fiyatlarını takip eder, gizli depo ve kargo maliyetlerini hesaplar ve işletmeyi "kırmızı çizginin" (zarar noktasının) altına düşmekten koruyarak otonom çapraz satış (cross-sell) stratejileri üretir.

---

## 🚀 Proje Vizyonu

KOBİ'ler e-ticarette sadece rakiplerin fiyatlarına bakarak indirim yaptıklarında, komisyon ve desi maliyetleri yüzünden görünmez zararlar edebilirler. Bedülonca; Trend, Piyasa, Maliyet ve Strateji ajanlarını eşgüdümlü çalıştırarak fiyat indirmek yerine **"Elde kalan 2TB SSD ile yüksek marjlı Oyuncu Mouse'unu 4.999 TL'ye paket yap"** gibi zeki finansal kararlar alır.

---

## 🧠 Agentic Mimari (LangGraph StateGraph)

```
START → trend_agent → market_agent → cost_agent → strategist_agent → END
```

Sistem doğrusal bir StateGraph mimarisinde, paylaşılan bir bellek (`AgentState`) üzerinden birbirine pas atan 4 ajandan oluşur:

| Ajan | Görev |
|---|---|
| **Trend Ajanı** | Gündemdeki oyunları ve donanım ihtiyaçlarını tespit eder |
| **Piyasa Ajanı (PriceOps)** | Rakip fiyat/stok durumunu analiz eder, pozisyon belirler |
| **Maliyet Ajanı** | Kargo desisi, enflasyon, komisyon ve depo payını hesaplar; kırmızı çizgiyi çizer |
| **Stratejist Ajan (Gemini)** | Tüm verileri sentezler; fiyat güncelleme, bundle ve bekleme kararları üretir |

---

## 🛠️ Teknoloji Yığını

- **Ana Zeka:** Google Gemini API (`gemini-2.0-flash`)
- **Orkestrasyon:** LangChain & LangGraph
- **Arayüz:** Streamlit (Custom CSS Dark Theme)
- **Dil:** Python 3.10+

---

## ⚙️ Kurulum (Jüri İçin)

```bash
# 1. Repoyu klonla
git clone https://github.com/kullaniciadi/bedulonca.git
cd bedulonca

# 2. Gereksinimleri yükle
pip install -r requirements.txt

# 3. API anahtarını tanımla
cp .env.example .env
# .env dosyasını aç ve GEMINI_API_KEY değerini gir

# 4. Uygulamayı başlat
streamlit run main.py
```

---

## 📁 Proje Yapısı

```
bedulonca/
├── main.py                  # Streamlit arayüzü
├── agent_graph.py           # LangGraph StateGraph
├── state.py                 # Paylaşılan AgentState
├── agents/
│   ├── trend_agent.py
│   ├── market_agent.py
│   ├── cost_agent.py
│   └── strategist_agent.py
├── data/
│   └── mock_data.json       # Simüle ürün, rakip, maliyet verileri
├── .env.example
├── .gitignore
└── requirements.txt
```

---

## 🎬 Demo Videosu

*[YouTube / Drive linki buraya eklenecek]*
