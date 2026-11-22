import streamlit as st
import requests
from datetime import date

st.set_page_config(page_title="BAÜN Öğrenci Asistanı", page_icon="🎓", layout="centered")

SYSTEM_INSTRUCTION = """
Sen Balıkesir Üniversitesi (BAÜN) öğrencileri için geliştirilmiş güvenilir bir yapay zeka öğrenci asistanısın.
Görevin; BAÜN bölümleri, akademik takvim, öğretim görevlileri, kampüs olanakları (Çağış Kampüsü, Balıkesir MYO vb.) ve üniversite duyuruları hakkında SADECE doğrulanmış gerçek bilgi vermektir.

KESİN KURALLAR (ASLA İHLAL ETME):
1. WEB ARAMASINI ZORUNLU KULLAN: Akademik takvim, öğretim görevlisi isimleri, bölüm dersleri ve duyurular için mutlaka Google Arama sonucundaki güncel verilere dayan.
2. BULAMADIYSAN KESİNLİKLE UYDURMA: Web aramasında net bir sonuç bulamadıysan veya emin değilsen ASLA tahmin yürütme, isim veya tarih uydurma. Doğrudan şu cevabı ver:
"Bu konuda güncel ve kesin bir bilgiye ulaşamadım. Yanlış bilgi vermemek adına Balıkesir Üniversitesi resmi web sitesini (balikesir.edu.tr) veya ilgili bölümün sayfasını kontrol etmeni öneririm."
3. SADECE GERÇEKLERİ YAZ: Yorum katma, olmayan bir öğretim görevlisi veya tarih ekleme.
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
            "content": "Merhaba! Ben BAÜN Öğrenci Asistanı. Bölümler, akademik takvim, öğretim görevlileri veya kampüs hakkında merak ettiklerini sorabilirsin. (Bugün kalan soru hakkın: 3)"
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
st.caption("Balıkesir Üniversitesi Bilgi Sistemi • Canlı Web Arama Destekli")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

def run_chat_with_search(key, msgs):
    # 1. Erişilebilen modelleri çek
    r = requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={key}", timeout=15)
    if r.status_code != 200:
        return False, f"API Anahtarı Hatası ({r.status_code}): {r.json().get('error', {}).get('message', r.text)}"

    models = [
        m["name"] for m in r.json().get("models", [])
        if "generateContent" in m.get("supportedGenerationMethods", [])
        and "gemini" in m["name"]
        and "lite" not in m["name"]  # Lite modeller web araması desteklemez, eliyoruz
    ]
    # 2.5 ve 2.0 flash modellerini öne al
    models.sort(key=lambda x: (0 if "2.5-flash" in x else (1 if "2.0-flash" in x else 2), x))

    # Son mesajları hazırla
    contents = []
    for m in msgs[-6:]:
        role = "user" if m["role"] == "user" else "model"
        # Kullanıcının sorusuna otomatik Balıkesir Üniversitesi bağlamı ekle ki aramayı doğru yapsın
        text = f"Balıkesir Üniversitesi (BAÜN) ile ilgili soru: {m['content']}" if role == "user" else m["content"]
        contents.append({"role": role, "parts": [{"text": text}]})

    # Web araması açık + Temperature 0.0 (Sıfır yaratıcılık = Sıfır sallama)
    payload_with_search = {
        "system_instruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
        "contents": contents,
        "tools": [{"google_search": {}}],
        "generationConfig": {"temperature": 0.0}
    }

    for model_id in models:
        res = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/{model_id}:generateContent?key={key}",
            json=payload_with_search,
            timeout=30
        )
        if res.status_code == 200:
            data = res.json()
            candidate = data["candidates"][0]
            answer = candidate["content"]["parts"][0]["text"]

            # Web'den çekilen kaynak linklerini altına ekle (Kanıtlı bilgi)
            chunks = candidate.get("groundingMetadata", {}).get("groundingChunks", [])
            sources = []
            for chunk in chunks:
                web = chunk.get("web", {})
                if web.get("uri") and web.get("title"):
                    sources.append(f"- [{web['title']}]({web['uri']})")

            if sources:
                unique_sources = list(dict.fromkeys(sources))
                answer += "\n\n**📚 Doğrulanan Web Kaynakları:**\n" + "\n".join(unique_sources[:3])
            else:
                answer += "\n\n*(Not: Bu yanıt için canlı web kaynağı eşleşmedi; lütfen balikesir.edu.tr üzerinden teyit edin.)*"

            return True, answer

    return False, "Web arama destekli model yanıt vermedi. Lütfen birkaç saniye sonra tekrar deneyin."

if prompt := st.chat_input("Örn: Balıkesir Üniversitesi 2026-2027 akademik takvimi"):
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
        with st.spinner("balikesir.edu.tr ve web taranıyor..."):
            ok, result = run_chat_with_search(api_key, st.session_state.messages)
            if ok:
                st.markdown(result)
                st.session_state.question_count += 1
                st.session_state.messages.append({"role": "assistant", "content": result})
                st.rerun()
            else:
                st.error(result)
