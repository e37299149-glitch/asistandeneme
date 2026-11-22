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
Görevin; BAÜN bölümleri, akademik yapı, kampüs olanakları (Çağış Kampüsü, Balıkesir MYO vb.), öğrenci işleri süreçleri ve genel üniversite rehberliği hakkında doğru bilgi vermektir.

KESİN KURALLAR:
1. ASLA UYDURMA (SALLAMA): Emin olmadığın, kendi eğitim verinde kesin olarak bulunmayan hiçbir tarihi, akademisyen ismini veya duyuruyu uydurma. Tahmin yürütme.
2. BİLMİYORSAN NET SÖYLE: Güncel akademik takvim tarihleri, anlık duyurular veya bilmediğin detaylar sorulursa; "Bu konuda kesin veya güncel bir bilgiye sahip değilim. Yanlış yönlendirmemek adına Balıkesir Üniversitesi resmi web sitesini (balikesir.edu.tr) veya ilgili birimin duyurular sayfasını kontrol etmeni öneririm." şeklinde dürüstçe cevap ver.
3. ÜSLUP: Öğrenci dostu, net, kibar ve Türkçe dil kurallarına uygun yanıtlar ver. Gereksiz uzun giriş cümlelerinden kaçın, doğrudan bilgiyi sun.
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
            "content": "Merhaba! Ben BAÜN Öğrenci Asistanı. Bölümler, kampüs yaşamı, öğrenci işleri veya üniversite hakkında merak ettiklerini sorabilirsin. (Bugün kalan soru hakkın: 3)"
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
st.caption("Balıkesir Üniversitesi Bilgi Sistemi • Halüsinasyon Korumalı")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- API ÇAĞRISI (WEB ARAMASIZ - DOĞRUDAN YANIT) ---
def ask_gemini(api_key, messages):
    contents = []
    for m in messages[-6:]:
        role = "user" if m["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
        "contents": contents,
        "generationConfig": {"temperature": 0.1}
    }

    # Sırasıyla kararlı modelleri dener
    models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
    last_response = None

    for model_name in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        res = requests.post(url, json=payload, timeout=30)
        last_response = res
        if res.status_code == 200:
            data = res.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        elif res.status_code == 404:
            continue
        else:
            break

    raise Exception(f"Hata Kodu {last_response.status_code}: {last_response.text}")

# --- KULLANICI GİRDİSİ ---
if prompt := st.chat_input("Örn: Çağış kampüsünde hangi fakülteler var?"):
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
        with st.spinner("Yanıt hazırlanıyor..."):
            try:
                answer_text = ask_gemini(api_key, st.session_state.messages)
                st.markdown(answer_text)
                
                st.session_state.question_count += 1
                st.session_state.messages.append({"role": "assistant", "content": answer_text})
                st.rerun()

            except Exception as e:
                st.error(f"{str(e)}")
