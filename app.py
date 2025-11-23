import streamlit as st
from groq import Groq
from audio_recorder_streamlit import audio_recorder
from gtts import gTTS
import io
import requests
from bs4 import BeautifulSoup
import PyPDF2
from youtube_transcript_api import YouTubeTranscriptApi

# --- 1. GENEL AYARLAR ---
st.set_page_config(page_title="LinguaFlow AI", page_icon="🧠", layout="wide")

# --- CSS TASARIM ---
st.markdown("""
    <style>
    .stApp { background-color: #F7F9FB; }
    .header-title { font-size: 2.5rem; font-weight: 800; color: #0F2B46; text-align: center; }
    .sub-header { text-align: center; color: #666; margin-bottom: 20px; }
    
    /* Metin Alanları */
    .stTextArea textarea { border-radius: 8px; border: 1px solid #ddd; min-height: 200px; }
    
    /* Sonuç Kutusu */
    .result-box {
        background-color: #ffffff; padding: 20px; border-radius: 8px;
        border: 1px solid #ddd; min-height: 200px; color: #333; white-space: pre-wrap;
    }
    
    /* Butonlar */
    div.stButton > button {
        background-color: #0F2B46; color: white; border-radius: 6px;
        font-weight: bold; border: none; padding: 10px; width: 100%; transition: 0.2s;
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

# --- STATE ---
if "text_input_val" not in st.session_state: st.session_state.text_input_val = ""
if "trans_result" not in st.session_state: st.session_state.trans_result = ""
if "history" not in st.session_state: st.session_state.history = []

# --- BEYİN: TEK MERKEZLİ AI FONKSİYONU ---
def ai_engine(text, task, target_lang="Turkish", tone="Normal"):
    """
    Bu fonksiyon uygulamanın TEK BEYNİDİR. 
    YouTube, Web, Ses veya Metin fark etmeksizin her şey buraya gelir.
    """
    if not text: return ""
    
    # Göreve göre talimat (Prompt) hazırla
    if task == "translate":
        sys_msg = f"Sen profesyonel tercümansın. Metni {target_lang} diline çevir. Ton: {tone}. Sadece çeviriyi yaz."
    elif task == "improve":
        sys_msg = "Sen bir editörsün. Metni dil bilgisi açısından düzelt. Dili değiştirme."
    elif task == "summarize":
        sys_msg = f"Sen bir analiz uzmanısın. Metni {target_lang} dilinde özetle. Format: 1. Özet, 2. Önemli Noktalar."
    else:
        sys_msg = "Yardımcı ol."

    try:
        # Llama 3 Modelini Kullan (Kendi Kaynağımız)
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": text[:15000]}] # Token limiti
        )
        result = res.choices[0].message.content
        
        # Çeviri işlemlerini geçmişe kaydet
        if task == "translate":
            st.session_state.history.insert(0, f"İşlem: {text[:30]}...")
            
        return result
    except Exception as e: return f"AI Hatası: {e}"

# --- ARAÇLAR: VERİ OKUYUCULAR (Local Parsers) ---
def read_pdf_local(file):
    reader = PyPDF2.PdfReader(file)
    return "".join([page.extract_text() for page in reader.pages])

def read_web_local(url):
    try:
        h = {'User-Agent': 'Mozilla/5.0'}
        soup = BeautifulSoup(requests.get(url, headers=h, timeout=10).content, 'html.parser')
        return " ".join([p.get_text() for p in soup.find_all(['p', 'h1', 'h2'])])[:15000]
    except: return None

def read_youtube_local(url):
    """
    Bu fonksiyon bir AI DEĞİLDİR. Sadece videonun altyazı dosyasını (Transcript) indirir.
    Analizi yine bizim 'ai_engine' fonksiyonumuz yapar.
    """
    try:
        video_id = ""
        if "v=" in url: video_id = url.split("v=")[1].split("&")[0]
        elif "youtu.be" in url: video_id = url.split("/")[-1]
        
        if not video_id: return None
        
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([i['text'] for i in transcript])
    except: return None

def create_audio(text, lang_name):
    if not text: return None
    code_map = {"Türkçe": "tr", "İngilizce": "en", "Almanca": "de", "Fransızca": "fr", "İspanyolca": "es", "Rusça": "ru", "Arapça": "ar", "Çince": "zh"}
    try:
        fp = io.BytesIO()
        gTTS(text=text, lang=code_map.get(lang_name, "en"), slow=False).write_to_fp(fp)
        return fp.getvalue()
    except: return None

# ==========================================
# ARAYÜZ (UI)
# ==========================================

st.markdown('<div class="header-title">LinguaFlow</div><div class="sub-header">Bütünleşik AI Çeviri & Analiz Merkezi</div>', unsafe_allow_html=True)

# Yan Menü (Geçmiş)
with st.sidebar:
    st.header("🕒 Geçmiş")
    if st.session_state.history:
        for item in st.session_state.history[:5]: st.caption(f"• {item}")
        if st.button("Temizle"): st.session_state.history = []; st.rerun()
    else: st.info("Henüz işlem yok.")

# Sekmeler
tabs = st.tabs(["✏️ Metin", "📂 Dosya/PDF", "🎙️ Sesli Sohbet", "🔗 Web", "📺 YouTube"])

# --- 1. METİN ---
with tabs[0]:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Giriş")
        txt_val = st.text_area("Metin", value=st.session_state.text_input_val, height=250, label_visibility="collapsed", placeholder="Yazın...")
        st.session_state.text_input_val = txt_val
        
        cc1, cc2 = st.columns(2)
        with cc1: t_lang = st.selectbox("Hedef", ["İngilizce", "Türkçe", "Almanca", "Fransızca", "İspanyolca", "Rusça", "Arapça", "Çince"])
        with cc2: tone = st.selectbox("Ton", ["Normal", "Resmi", "Samimi"])
        
        if st.button("Çevir ➔"):
            with st.spinner("AI Düşünüyor..."):
                st.session_state.trans_result = ai_engine(txt_val, "translate", t_lang, tone)
        if st.button("✨ Düzelt"):
            with st.spinner("AI Düzenliyor..."):
                st.session_state.trans_result = ai_engine(txt_val, "improve")

    with c2:
        st.subheader("Sonuç")
        res = st.session_state.trans_result
        if res:
            st.markdown(f"<div class='result-box'>{res}</div>", unsafe_allow_html=True)
            st.divider()
            ca, cd = st.columns([3,1])
            with ca: 
                aud = create_audio(res, t_lang)
                if aud: st.audio(aud, format="audio/mp3")
            with cd: st.download_button("İndir", res, "sonuc.txt")

# --- 2. DOSYA ---
with tabs[1]:
    f = st.file_uploader("Dosya (PDF, MP3)", type=['pdf', 'mp3', 'wav'])
    if f:
        ftype = f.name.split('.')[-1]
        if ftype == 'pdf':
            if st.button("PDF Analiz"):
                with st.spinner("Okunuyor..."):
                    raw = read_pdf_local(f)
                    summ = ai_engine(raw, "summarize", "Türkçe")
                    st.markdown(f"### 📄 Belge Özeti\n{summ}")
        else:
            st.audio(f)
            if st.button("Sesi Çevir"):
                with st.spinner("Dinleniyor..."):
                    raw = client.audio.transcriptions.create(file=("a.wav", f), model="whisper-large-v3").text
                    trans = ai_engine(raw, "translate", "Türkçe")
                    st.success(trans)

# --- 3. SESLİ SOHBET ---
with tabs[2]:
    c1, c2 = st.columns([3,1])
    with c2: v_lang = st.selectbox("Çıktı Dili", ["Türkçe", "İngilizce", "Almanca"])
    with c1:
        st.write("Konuşun:")
        aud = audio_recorder(text="Bas-Konuş", icon_size="3x", recording_color="#ef4444", neutral_color="#333")
        if aud:
            with st.spinner("İşleniyor..."):
                try:
                    raw = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(aud)), model="whisper-large-v3").text
                    res = ai_engine(raw, "translate", v_lang)
                    st.success(f"🗣️ {raw}")
                    st.info(f"🤖 {res}")
                    v_aud = create_audio(res, v_lang)
                    if v_aud: st.audio(v_aud, format="audio/mp3", autoplay=True)
                except: st.error("Ses anlaşılamadı.")

# --- 4. WEB ---
with tabs[3]:
    url = st.text_input("Web Linki")
    if st.button("Web Analiz") and url:
        with st.spinner("Site okunuyor..."):
            raw = read_web_local(url)
            if raw:
                res = ai_engine(raw, "summarize", "Türkçe")
                st.markdown(f"### 🌐 Site Raporu\n{res}")
            else: st.error("Site içeriği alınamadı.")

# --- 5. YOUTUBE (YEREL OKUYUCU + AI BEYİN) ---
with tabs[4]:
    yt_url = st.text_input("YouTube Linki")
    if st.button("Video Analiz") and yt_url:
        with st.spinner("Altyazılar çekiliyor..."):
            # 1. Adım: Yerel okuyucu ile metni al
            raw_text = read_youtube_local(yt_url)
            
            if raw_text:
                st.success("✅ Veri alındı, AI analiz ediyor...")
                st.video(yt_url)
                
                # 2. Adım: Bizim AI (Llama 3) analiz etsin
                summary = ai_engine(raw_text, "summarize", "Türkçe")
                
                st.markdown(f"### 📺 Video Özeti\n{summary}")
                st.download_button("Raporu İndir", summary, "video_analiz.txt")
            else:
                st.warning("Bu videonun altyazısı yok veya erişilemiyor.")

st.divider()
st.caption("© 2024 LinguaFlow AI - Powered by Groq & Llama 3")
