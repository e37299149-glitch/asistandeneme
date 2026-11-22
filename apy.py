import streamlit as st
import requests
from datetime import date

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="BAÜN Öğrenci Asistanı",
    page_icon="🎓",
    layout="centered"
)

# --- SİSTEM TALİMATI ---
SYSTEM_INSTRUCTION = """
Sen Balıkesir Üniversitesi (BAÜN) öğrencileri için geliştirilmiş resmi olmayan, yardımsever ve güvenilir bir yapay zeka öğrenci asistanısın.
Görevin; BAÜN bölümleri, akademik takvim, öğretim görevlileri, kampüs olanakları (Çağış Kampüsü, Balıkesir MYO vb.), öğrenci işleri ve üniversite duyuruları hakkında doğru bilgi vermektir.

KESİN KURALLAR:
1. ASLA UYDURMA (SALLAMA): Emin olmadığın, web aramasında güncel ve doğrulanabilir bir karşılığını bulamadığın hiçbir bilgiyi uydurma.
2. BİLMİYORSAN NET SÖYLE: Bilgiye ulaşamıyorsan "Bu konuda güncel ve kesin bir bilgiye ulaşamadım. Yanlış yönlendirmemek adına Balıkesir Üniversitesi resmi web sitesini (balikesir.edu.tr) kontrol etmeni öneririm." de.
3. WEB ARAMASINI KULLAN: Akademik takvim, duyurular ve akademisyenler için web araması yaparak güncel verileri doğrula.
4. ÜSLUP: Öğrenci dostu, net ve kibar Türkçe yanıtlar ver.
"""

# --- GÜNLÜK LİMİT ---
DAILY_LIMIT = 3
today_str = str(date.today())

if "usage_date" not in st.session_state or st.session_state.usage_date != today_str:
    st.session_state.usage_date = today_str
    st.session_state.question_count = 0

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Merhaba! Ben BAÜN Öğrenci Asistanı. Bölümler, akademik takvim, öğretim görevlileri veya kampüs hakkında merak ettiklerini sorabilirsin. (Bugün kalan soru hakkın: 3)"
        }
    ]

# --- YAN MENÜ ---
with st.sidebar:
    st.header("🎓 BAÜN Asistan Ayarları")
    
    api_key = ""
    try:
        if "GEMINI_API_KEY" in st.secrets:
            api_key = str(st.secrets["GEMINI_API_KEY"]).strip()
            st.success("API Anahtarı sistemden yüklendi.")
    except Exception:
        pass

    if not api_key:
        raw_key = st.text_input("Gemini API Key Giriniz:", type="password")
        api_key = raw_key.strip() if raw_key else ""

    st.divider()
    remaining = max(0, DAILY_LIMIT - st.session_state.question_count)
    st.metric(label="Bugünkü Kalan Soru Hakkınız", value=f"{remaining} / {DAILY_LIMIT}")
    
    if st.button("Sohbet Geçmişini Temizle"):
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": f"Sohbet temizlendi. Yeni sorunuzu sorabilirsiniz. (Kalan hak: {remaining})"
            }
        ]
        st.rerun()

# --- ANA EKRAN ---
st.title("🎓 BAÜN Öğrenci Asistanı")
st.caption("Balıkesir Üniversitesi Bilgi Sistemi • Web Arama Destekli • Halüsinasyon Korumalı")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- API ÇAĞRISI ---
def ask_gemini(api_key, messages):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    contents = []
    for m in messages[-6:]:
        role = "user" if m["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
        "contents": contents,
        "tools": [{"google_search": {}}],
        "generationConfig": {"temperature": 0.1}
    }

    res = requests.post(url, json=payload, timeout=30)
    
    # Eğer gemini-2.5-flash 404 verirse otomatik gemini-2.0-flash dener
    if res.status_code == 404:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
        res = requests.post(url, json=payload, timeout=30)

    if res.status_code != 200:
        raise Exception(f"Hata Kodu {res.status_code}: {res.text}")

    data = res.json()
    candidate = data["candidates"][0]
    answer_text = candidate["content"]["parts"][0]["text"]

    # Web arama kaynaklarını ekle
    chunks = candidate.get("groundingMetadata", {}).get("groundingChunks", [])
    sources = []
    for chunk in chunks:
        web = chunk.get("web", {})
        if web.get("uri") and web.get("title"):
            sources.append(f"- [{web['title']}]({web['uri']})")
            
    if sources:
        unique_sources = list(dict.fromkeys(sources))
        answer_text += "\n\n**📚 Yararlanılan Kaynaklar:**\n" + "\n".join(unique_sources[:3])

    return answer_text

# --- KULLANICI GİRDİSİ ---
if prompt := st.chat_input("Örn: 2026-2027 güz dönemi akademik takvimi ne zaman başlıyor?"):
    if not api_key:
        st.error("Lütfen sol menüden geçerli bir Gemini API Anahtarı girin.")
        st.stop()

    if st.session_state.question_count >= DAILY_LIMIT:
        st.warning("🚫 Bugünkü 3 soru hakkınızı doldurdunuz. Yarın tekrar soru sorabilirsiniz.")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("BAÜN kaynakları ve web taranıyor..."):
            try:
                answer_text = ask_gemini(api_key, st.session_state.messages)
                st.markdown(answer_text)
                
                st.session_state.question_count += 1
                st.session_state.messages.append({"role": "assistant", "content": answer_text})
                st.rerun()

            except Exception as e:
                st.error(f"{str(e)}")
