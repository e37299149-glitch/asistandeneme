import streamlit as st
from google import genai
from google.genai import types
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

# --- YAN MENÜ (API ANAHTARI VE HAK BİLGİSİ) ---
with st.sidebar:
    st.header("🎓 BAÜN Asistan Ayarları")
    
    # Streamlit Secrets varsa otomatik alır, yoksa kullanıcıdan ister
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
        st.success("API Anahtarı sistemden yüklendi.")
    else:
        api_key = st.text_input("Gemini API Key Giriniz:", type="password")
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

# --- GEÇMİŞ MESAJLARI EKRANA YAZDIRMA ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- KULLANICI GİRDİSİ VE YANIT ÜRETME ---
if prompt := st.chat_input("Örn: 2026-2027 güz dönemi akademik takvimi ne zaman başlıyor?"):
    
    # 1. API Anahtarı Kontrolü
    if not api_key:
        st.error("Lütfen sol menüden geçerli bir Gemini API Anahtarı girin.")
        st.stop()

    # 2. Günlük Limit Kontrolü
    if st.session_state.question_count >= DAILY_LIMIT:
        st.warning("🚫 Bugünkü 3 soru hakkınızı doldurdunuz.
