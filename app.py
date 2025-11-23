import streamlit as st
from groq import Groq
from audio_recorder_streamlit import audio_recorder
from gtts import gTTS
import io
import requests
from bs4 import BeautifulSoup
import PyPDF2

# --- 1. GENEL AYARLAR ---
st.set_page_config(page_title="LinguaFlow", page_icon="🌐", layout="wide")

# --- CSS TASARIM ---
st.markdown("""
    <style>
    .stApp { background-color: #F7F9FB; }
    .header-container { text-align: center; padding: 20px; margin-bottom: 20px; }
    .header-title { font-size: 2.5rem; font-weight: 800; color: #0F2B46; }
    
    /* Metin Kutuları */
    .stTextArea textarea { border-radius: 8px; border: 1px solid #ddd; height: 200px; }
    .stTextArea textarea:focus { border-color: #0F2B46; box-shadow: 0 0 0 1px #0F2B46; }
    
    /* Sonuç Kutusu */
    .result-box {
        background-color: #ffffff; padding: 20px; border-radius: 8px;
        border: 1px solid #ddd; min-height: 200px; font-size: 1.1rem; color: #333;
    }
    
    /* Butonlar */
    div.stButton > button {
        background-color: #0F2B46; color: white; border-radius: 5px;
        font-weight: bold; border: none; padding: 10px; width: 100%;
    }
    div.stButton > button:hover { background-color: #1A4D7A; }
    </style>
""", unsafe_allow_html=True)

# --- API BAĞLANTISI ---
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("API Key Hatası! Secrets ayarlarını kontrol edin.")
    st.stop()

# --- FONKSİYONLAR ---
def ai_process(text, task, target_lang="Turkish", tone="Normal"):
    if task == "translate":
        prompt = f"""
        Sen profesyonel bir tercümansın.
        GÖREV: Metni {target_lang} diline çevir.
        AYAR: Ton {tone} olsun.
        KURAL: Sadece çeviriyi yaz, açıklama yapma.
        """
    elif task == "improve":
        prompt = f"Sen bir editörsün. Metni dil bilgisi ve akıcılık açısından düzelt (Dili değiştirme). Sadece sonucu yaz."
    elif task == "summarize":
        prompt = f"Sen bir asistansın. Metni {target_lang} dilinde özetle (Maddeler halinde)."
    else:
        prompt = "Yardımcı ol."

    try:
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": prompt}, {"role": "user", "content": text}]
        )
        return res.choices[0].message.content
    except Exception as e: return f"Hata: {e}"

def create_audio(text, lang_name):
    # Dil eşleştirme haritası
    code_map = {
        "Türkçe": "tr", "İngilizce": "en", "Almanca": "de", 
        "Fransızca": "fr", "İspanyolca": "es", "Rusça": "ru", 
        "Arapça": "ar", "Çince": "zh"
    }
    # Varsayılan dil İngilizce (en)
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

st.markdown('<div class="header-container"><div class="header-title">LinguaFlow</div><small>AI Powered Translation & Writing Assistant</small></div>', unsafe_allow_html=True)

# Sekmeler
tab_text, tab_files, tab_voice, tab_web = st.tabs(["✏️ Metin Çeviri", "📂 Dosya & Belge", "🎙️ Sesli Sohbet", "🔗 Web Analiz"])

# --- 1. METİN ÇEVİRİ ---
with tab_text:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Giriş")
        input_text = st.text_area("Metni buraya yapıştırın...", height=250)
        
        c1, c2 = st.columns(2)
        with c1: target_lang = st.selectbox("Hedef Dil", ["İngilizce", "Türkçe", "Almanca", "Fransızca", "İspanyolca", "Rusça"])
        with c2: tone = st.selectbox("Ton", ["Normal", "Resmi", "Samimi"])
        
        if st.button("Çevir ➔"):
            if input_text:
                st.session_state.trans_result = ai_process(input_text, "translate", target_lang, tone)
            else:
                st.warning("Lütfen metin girin.")
                
        if st.button("✨ Metni Güzelleştir (AI Editör)"):
            if input_text:
                st.session_state.trans_result = ai_process(input_text, "improve")

    with col2:
        st.subheader("Sonuç")
        result = st.session_state.get("trans_result", "")
        st.markdown(f"<div class='result-box'>{result}</div>", unsafe_allow_html=True)
        
        if result:
            st.divider()
            c_copy, c_play = st.columns(2)
            with c_copy: st.code(result, language=None)
            with c_play:
                audio_data = create_audio(result, target_lang)
                if audio_data: st.audio(audio_data, format="audio/mp3")

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
                    st.markdown(f"### 📄 Özet\n{summ}")
        else:
            st.audio(uploaded_file)
            if st.button("Sesi Çevir"):
                with st.spinner("Dinleniyor..."):
                    txt = client.audio.transcriptions.create(file=("a.wav", uploaded_file), model="whisper-large-v3").text
                    trans = ai_process(txt, "translate", target_lang="Türkçe")
                    st.success(trans)

# --- 3. SESLİ SOHBET (DÜZELTİLEN KISIM) ---
with tab_voice:
    c_conf, c_set = st.columns([3, 1])
    with c_set:
        v_lang = st.selectbox("Çıktı Dili", ["Türkçe", "İngilizce", "Almanca", "Fransızca"])
        
    with c_conf:
        st.write("Mikrofona tıklayın ve konuşun:")
        audio_bytes = audio_recorder(text="Bas-Konuş", icon_size="3x", recording_color="#ef4444", neutral_color="#333")
        
        # HATA BURADAYDI - ŞİMDİ DÜZELTİLDİ
        if audio_bytes:
            with st.spinner("Ses işleniyor..."):
                try:
                    # 1. Sesi yazıya dök
                    txt = client.audio.transcriptions.create(
                        file=("audio.wav", io.BytesIO(audio_bytes)), 
                        model="whisper-large-v3"
                    ).text
                    
                    # 2. Çevir
                    res = ai_process(txt, "translate", target_lang=v_lang)
                    
                    # 3. Sonucu göster
                    st.success(f"🗣️ Algılanan: {txt}")
                    st.info(f"🤖 Çeviri: {res}")
                    
                    # 4. Seslendir
                    aud = create_audio(res, v_lang)
                    if aud: st.audio(aud, format="audio/mp3", autoplay=True)
                    
                except Exception as e:
                    st.error(f"Ses işleme hatası: {e}")

# --- 4. WEB ANALİZ ---
with tab_web:
    url = st.text_input("URL Girin")
    if st.button("Siteyi Analiz Et") and url:
        with st.spinner("Site okunuyor..."):
            txt = local_read_web(url)
            if txt:
                summ = ai_process(txt, "summarize", target_lang="Türkçe")
                st.markdown(f"### 🌐 Site Analizi\n{summ}")
            else:
                st.error("Site içeriği alınamadı.")

st.divider()
st.caption("LinguaFlow AI © 2024")
