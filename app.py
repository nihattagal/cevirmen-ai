import streamlit as st
from groq import Groq
from audio_recorder_streamlit import audio_recorder
from gtts import gTTS
import io
import requests
from bs4 import BeautifulSoup
import PyPDF2

# --- 1. GENEL AYARLAR ---
st.set_page_config(page_title="LinguaFlow AI", page_icon="🌐", layout="wide")

# --- CSS TASARIM ---
st.markdown("""
    <style>
    .stApp { background-color: #F7F9FB; }
    .header-title { font-size: 2.5rem; font-weight: 800; color: #0F2B46; text-align: center; }
    .sub-header { text-align: center; color: #666; margin-bottom: 20px; }
    
    /* Metin Kutuları */
    .stTextArea textarea { border-radius: 8px; border: 1px solid #ddd; min-height: 200px; font-size: 16px; }
    .stTextArea textarea:focus { border-color: #0F2B46; box-shadow: 0 0 0 1px #0F2B46; }
    
    /* Sonuç Kutusu */
    .result-box {
        background-color: #ffffff; padding: 20px; border-radius: 8px;
        border: 1px solid #ddd; min-height: 200px; font-size: 16px; color: #333;
        white-space: pre-wrap; /* Satır sonlarını koru */
    }
    
    /* Butonlar */
    div.stButton > button {
        background-color: #0F2B46; color: white; border-radius: 6px;
        font-weight: bold; border: none; padding: 10px; width: 100%;
        transition: 0.2s;
    }
    div.stButton > button:hover { background-color: #1A4D7A; transform: scale(1.01); }
    </style>
""", unsafe_allow_html=True)

# --- API BAĞLANTISI ---
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("API Key Hatası! Lütfen Secrets ayarlarını kontrol edin.")
    st.stop()

# --- STATE (HAFIZA) YÖNETİMİ ---
# Bu kısım, sekmeler arası geçişte verilerin kaybolmamasını sağlar
if "text_input_val" not in st.session_state: st.session_state.text_input_val = ""
if "trans_result" not in st.session_state: st.session_state.trans_result = ""
if "history" not in st.session_state: st.session_state.history = []

# --- FONKSİYONLAR ---
def ai_process(text, task, target_lang="Turkish", tone="Normal"):
    if not text: return ""
    
    if task == "translate":
        prompt = f"""
        Sen profesyonel tercümansın.
        GÖREV: Metni {target_lang} diline çevir.
        AYAR: Ton {tone} olsun.
        KURAL: Sadece çeviriyi yaz, yorum yapma.
        """
    elif task == "improve":
        prompt = "Sen bir editörsün. Metni dil bilgisi ve akıcılık açısından düzelt (Dili değiştirme). Sadece sonucu yaz."
    elif task == "summarize":
        prompt = f"Sen bir asistansın. Metni {target_lang} dilinde özetle."
    else:
        prompt = "Yardımcı ol."

    try:
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": prompt}, {"role": "user", "content": text}]
        )
        result_text = res.choices[0].message.content
        
        # Geçmişe kaydet (Sadece çeviri ise)
        if task == "translate":
            st.session_state.history.insert(0, f"{text[:20]}... -> {result_text[:20]}...")
            
        return result_text
    except Exception as e: return f"Hata: {e}"

def create_audio(text, lang_name):
    if not text: return None
    code_map = {"Türkçe": "tr", "İngilizce": "en", "Almanca": "de", "Fransızca": "fr", "İspanyolca": "es", "Rusça": "ru", "Arapça": "ar", "Çince": "zh"}
    lang_code = code_map.get(lang_name, "en")
    try:
        fp = io.BytesIO()
        gTTS(text=text, lang=lang_code, slow=False).write_to_fp(fp)
        return fp.getvalue()
    except: return None

def local_read_pdf(file):
    reader = PyPDF2.PdfReader(file)
    return "".join([page.extract_text() for page in reader.pages])

def local_read_web(url):
    try:
        h = {'User-Agent': 'Mozilla/5.0'}
        soup = BeautifulSoup(requests.get(url, headers=h, timeout=10).content, 'html.parser')
        return " ".join([p.get_text() for p in soup.find_all(['p', 'h1', 'h2'])])[:10000]
    except: return None

# ==========================================
# ARAYÜZ
# ==========================================

st.markdown('<div class="header-title">LinguaFlow</div><div class="sub-header">AI Powered Translation & Assistant</div>', unsafe_allow_html=True)

# --- YAN MENÜ (GEÇMİŞ) ---
with st.sidebar:
    st.header("🕒 Son İşlemler")
    if st.session_state.history:
        for item in st.session_state.history[:5]: # Son 5 işlem
            st.caption(f"• {item}")
        if st.button("Geçmişi Temizle"):
            st.session_state.history = []
            st.rerun()
    else:
        st.info("Henüz işlem yok.")

# --- SEKMELER ---
tab_text, tab_files, tab_voice, tab_web = st.tabs(["✏️ Metin Çeviri", "📂 Dosya & Belge", "🎙️ Sesli Sohbet", "🔗 Web Analiz"])

# --- 1. METİN ÇEVİRİ ---
with tab_text:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Giriş")
        # Value parametresi ile hafızadaki veriyi geri yüklüyoruz
        text_val = st.text_area("Metin", value=st.session_state.text_input_val, height=250, label_visibility="collapsed", placeholder="Metni buraya yazın...")
        
        # Kullanıcı her harf yazdığında session state güncellensin
        st.session_state.text_input_val = text_val
        
        c1, c2 = st.columns(2)
        with c1: target_lang = st.selectbox("Hedef Dil", ["İngilizce", "Türkçe", "Almanca", "Fransızca", "İspanyolca", "Rusça", "Arapça", "Çince"])
        with c2: tone = st.selectbox("Ton", ["Normal", "Resmi", "Samimi"])
        
        b1, b2 = st.columns(2)
        with b1:
            if st.button("Çevir ➔", type="primary"):
                with st.spinner("Çevriliyor..."):
                    st.session_state.trans_result = ai_process(text_val, "translate", target_lang, tone)
        with b2:
            if st.button("✨ İyileştir"):
                with st.spinner("Düzenleniyor..."):
                    st.session_state.trans_result = ai_process(text_val, "improve")

    with col2:
        st.subheader("Sonuç")
        # Sonucu hafızadan çekip gösteriyoruz
        res = st.session_state.trans_result
        
        if res:
            st.markdown(f"<div class='result-box'>{res}</div>", unsafe_allow_html=True)
            st.divider()
            c_copy, c_play = st.columns([3, 1])
            with c_copy: st.code(res, language=None)
            with c_play:
                audio_data = create_audio(res, target_lang)
                if audio_data: st.audio(audio_data, format="audio/mp3")
        else:
            st.info("Çeviri sonucu burada görünecek.")

# --- 2. DOSYA & BELGE ---
with tab_files:
    uploaded_file = st.file_uploader("Dosya Yükle (PDF, MP3, WAV)", type=['pdf', 'mp3', 'wav', 'm4a'])
    
    if uploaded_file:
        ftype = uploaded_file.name.split('.')[-1].lower()
        
        if ftype == 'pdf':
            if st.button("PDF'i Oku ve Özetle"):
                with st.spinner("Okunuyor..."):
                    text = local_read_pdf(uploaded_file)
                    summ = ai_process(text, "summarize", target_lang="Türkçe")
                    st.success("✅ Analiz Tamamlandı")
                    st.markdown(summ)
        else:
            st.audio(uploaded_file)
            if st.button("Sesi Deşifre Et ve Çevir"):
                with st.spinner("Dinleniyor..."):
                    txt = client.audio.transcriptions.create(file=("a.wav", uploaded_file), model="whisper-large-v3").text
                    trans = ai_process(txt, "translate", target_lang="Türkçe")
                    st.info(f"Orijinal: {txt}")
                    st.success(f"Çeviri: {trans}")

# --- 3. SESLİ SOHBET ---
with tab_voice:
    c_conf, c_set = st.columns([3, 1])
    with c_set:
        v_lang = st.selectbox("Çıktı Dili", ["Türkçe", "İngilizce", "Almanca", "Fransızca"])
        
    with c_conf:
        st.write("Mikrofona konuşun:")
        audio_bytes = audio_recorder(text="Bas-Konuş", icon_size="3x", recording_color="#ef4444", neutral_color="#333")
        
        if audio_bytes:
            with st.spinner("İşleniyor..."):
                try:
                    txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(audio_bytes)), model="whisper-large-v3").text
                    res = ai_process(txt, "translate", target_lang=v_lang)
                    
                    st.success(f"🗣️ {txt}")
                    st.info(f"🤖 {res}")
                    
                    aud = create_audio(res, v_lang)
                    if aud: st.audio(aud, format="audio/mp3", autoplay=True)
                except Exception as e:
                    st.error(f"Hata: {e}")

# --- 4. WEB ANALİZ ---
with tab_web:
    url = st.text_input("URL Girin (Haber, Blog vs.)")
    if st.button("Siteyi Analiz Et") and url:
        with st.spinner("Site okunuyor..."):
            txt = local_read_web(url)
            if txt:
                summ = ai_process(txt, "summarize", target_lang="Türkçe")
                st.markdown(f"### 🌐 Site Özeti\n{summ}")
            else:
                st.error("Site içeriği alınamadı.")

st.divider()
st.caption("© 2024 LinguaFlow - All Rights Reserved")
