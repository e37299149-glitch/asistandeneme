import streamlit as st
import requests
from datetime import date

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="BAÜN Öğrenci Asistanı",
    page_icon="🎓",
    layout="centered"
)

# --- SİSTEM TALİMATI (HALÜSİNASYON ENGELLEME & ROL TANIMI) ---
SYSTEM_INSTRUCTION = """
Sen Balıkesir Üniversitesi (BAÜN) öğrencileri için geliştirilmiş resmi olmayan, yardımsever ve güvenilir bir yapay zeka öğrenci asistanısın.
Görevin; BAÜN bölümleri, akademik takvim, öğretim görevlileri, kampüs olanakları (Çağış Kampüsü, Balıkesir MYO vb.), öğrenci işleri ve üniversite duyuruları hakkında doğru bilgi vermektir.

KESİN KURALLAR:
1. ASLA UYDURMA (SALLAMA): Emin olmadığın, web aramasında (Google Search) güncel ve doğrulanabilir bir karşılığını bulamadığın hiçbir bilgiyi uydurma. Tahmin yürütme.
2. BİLMİYORSAN NET SÖYLE: Eğer sorduğu bilgiye ulaşamıyorsan veya bilgi güncel değilse; "Bu konuda güncel ve kesin bir bilgiye ulaşamadım. Yanlış yönlendirmemek adına Balıkesir Üniversitesi resmi web sitesini (balikesir.edu.tr) veya ilgili birimin duyurular sayfasını kontrol etmeni öneririm." şeklinde dürüstçe cevap ver.
3. WEB ARAMASINI KULLAN: Akademik takvim, güncel duyurular, öğretim görevlisi isimleri ve bölüm detayları için mutlaka Google Arama aracını kullanarak güncel verileri doğrula.
4. ÜSLUP: Öğrenci dostu, net, kibar ve Türkçe dil kurallarına uygun yanıtlar ver. Gereksiz uzun giriş cümlelerinden kaçın, doğrudan bilgiyi sun.
"""

# --- GÜNLÜK LİMİT VE OTURUM YÖNETİMİ ---
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
        st.caption("API anahtarınızı Google AI Studio'dan ücretsiz alabilirsiniz.")

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

# --- ANA EKRAN BAŞLIĞI ---
st.title("🎓 BAÜN Öğrenci Asistanı")
st.caption("Balıkesir Üniversitesi Bilgi Sistemi • Web Arama Destekli • Halüsinasyon Korumalı")

# --- GEÇMİŞ MESAJLARI YAZDIRMA ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- API ÇAĞRI FONKSİYONU (AKTİF MODELİ KENDİ BULUR) ---
def ask_gemini_with_search(api_key, messages):
    # 1. Önce API anahtarının erişebildiği aktif modelleri listeden çek
    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    list_res = requests.get(list_url, timeout=15)
    
    if list_res.status_code != 200:
        raise Exception(f"API Anahtarı Geçersiz veya Erişim Hatası ({list_res.status_code}): {list_res.text}")
    
    models_data = list_res.json().get("models", [])
    available_models = [
        m["name"] for m in models_data 
        if "generateContent" in m.get("supportedGenerationMethods", []) and "flash" in m["name"]
    ]
    
    # Öncelik sırasına göre sırala (2.5 -> 2.0 -> diğer flash modelleri)
    target_model = None
    for preferred in ["models/gemini-2.5-flash", "models/gemini-2.0-flash", "models/gemini-1.5-flash"]:
        if preferred in available_models:
            target_model = preferred
            break
    if not target_model and available_models:
        target_model = available_models[0]
    if not target_model:
        target_model = "models/gemini-2.0-flash"

    # 2. Sohbet geçmişini hazırla
    contents = []
    for m in messages[-6:]:
        role = "user" if m["role"] == "user" else "model"
        contents.append({
            "role": role,
            "parts": [{"text": m["content"]}]
        })

    # 3. İstek gövdesi (Web Arama + Halüsinasyon Önleme)
    payload = {
        "system_instruction": {
            "parts": [{"text": SYSTEM_INSTRUCTION}]
        },
        "contents": contents,
        "tools": [{"google_search": {}}],
        "generationConfig": {
            "temperature": 0.1
        }
    }

    gen_url = f"https://generativelanguage.googleapis.com/v1beta/{target_model}:generateContent?key={api_key}"
    response = requests.post(gen_url, json=payload, timeout=30)
    
    if response.status_code != 200:
        raise Exception(f"Model Hatası ({response.status_code}) - Kullanılan model: {target_model} | Detay: {response.text}")

    data = response.json()
    candidate = data["candidates"][0]
    answer_text = candidate["content"]["parts"][0]["text"]

    # Kaynak linklerini çıkar
    grounding_meta = candidate.get("groundingMetadata", {})
    chunks = grounding_meta.get("groundingChunks", [])
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
                answer_text = ask_gemini_with_search(api_key, st.session_state.messages)
                st.markdown(answer_text)
                
                st.session_state.question_count += 1
                st.session_state.messages.append({"role": "assistant", "content": answer_text})
                st.rerun()

            except Exception as e:
                st.error(f"Hata Detayı:\n{str(e)}")
