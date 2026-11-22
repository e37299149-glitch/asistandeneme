import streamlit as st
import requests
from datetime import date

st.set_page_config(page_title="BAÜN Öğrenci Asistanı", page_icon="🎓", layout="centered")

SYSTEM_INSTRUCTION = """
Sen Balıkesir Üniversitesi (BAÜN) öğrencileri için geliştirilmiş resmi olmayan, yardımsever ve güvenilir bir yapay zeka öğrenci asistanısın.
Görevin; BAÜN bölümleri, akademik takvim, öğretim görevlileri, kampüs olanakları (Çağış Kampüsü, Balıkesir MYO vb.), öğrenci işleri ve üniversite duyuruları hakkında doğru bilgi vermektir.

KESİN KURALLAR:
1. ASLA UYDURMA (SALLAMA): Emin olmadığın, kesin olarak bilmediğin hiçbir tarihi, akademisyen ismini veya duyuruyu uydurma.
2. BİLMİYORSAN NET SÖYLE: Güncel akademik takvim tarihleri veya bilmediğin detaylar sorulursa; "Bu konuda kesin veya güncel bir bilgiye sahip değilim. Yanlış yönlendirmemek adına Balıkesir Üniversitesi resmi web sitesini (balikesir.edu.tr) veya ilgili birimin duyurular sayfasını kontrol etmeni öneririm." de.
3. ÜSLUP: Öğrenci dostu, net, kibar ve Türkçe yanıtlar ver.
"""

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
            {"role": "assistant", "content": f"Sohbet temizlendi. Yeni sorunuzu sorabilirsiniz. (Kalan hak: {remaining})"}
        ]
        st.rerun()

st.title("🎓 BAÜN Öğrenci Asistanı")
st.caption("Balıkesir Üniversitesi Bilgi Sistemi • Halüsinasyon Korumalı")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

def run_chat(key, msgs):
    # 1. Anahtarın gerçekten erişebildiği modelleri Google'dan çek
    r = requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={key}", timeout=15)
    if r.status_code != 200:
        return False, f"API Anahtarı Hatası ({r.status_code}): {r.json().get('error', {}).get('message', r.text)}"

    models = [
        m["name"] for m in r.json().get("models", [])
        if "generateContent" in m.get("supportedGenerationMethods", [])
        and ("gemini" in m["name"] or "gemma" in m["name"])
    ]
    if not models:
        return False, "Bu API anahtarına tanımlı hiçbir aktif sohbet modeli bulunamadı."

    # Flash modellerini en öne al
    models.sort(key=lambda x: (0 if "flash" in x else 1, x))

    # Mesajları hazırla
    contents = []
    for i, m in enumerate(msgs[-6:]):
        role = "user" if m["role"] == "user" else "model"
        txt = f"{SYSTEM_INSTRUCTION}\n\nSoru: {m['content']}" if (i == 0 and role == "user") else m["content"]
        contents.append({"role": role, "parts": [{"text": txt}]})

    payload = {"contents": contents, "generationConfig": {"temperature": 0.1}}

    # Çalışan ilk modelden yanıt al
    errors = []
    for model_id in models:
        res = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/{model_id}:generateContent?key={key}",
            json=payload,
            timeout=30
        )
        if res.status_code == 200:
            return True, res.json()["candidates"][0]["content"]["parts"][0]["text"]
        errors.append(f"{model_id} -> {res.status_code}")

    return False, f"Denenen modeller yanıt vermedi: {', '.join(errors)}"

if prompt := st.chat_input("Örn: Çağış kampüsünde hangi fakülteler var?"):
    if not api_key:
        st.error("Lütfen sol menüden geçerli bir Gemini API Anahtarı girip Enter'a basın.")
        st.stop()

    if st.session_state.question_count >= DAILY_LIMIT:
        st.warning("🚫 Bugünkü 3 soru hakkınızı doldurdunuz. Yarın tekrar soru sorabilirsiniz.")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Yanıt hazırlanıyor..."):
            ok, result = run_chat(api_key, st.session_state.messages)
            if ok:
                st.markdown(result)
                st.session_state.question_count += 1
                st.session_state.messages.append({"role": "assistant", "content": result})
                st.rerun()
            else:
                st.error(result)
