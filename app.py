import streamlit as st
from groq import Groq
from audio_recorder_streamlit import audio_recorder
from gtts import gTTS
import io
import requests
from bs4 import BeautifulSoup
import PyPDF2

# --- 1. GENEL AYARLAR ---
st.set_page_config(
    page_title="LinguaFlow AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. CSS TASARIM (Modern ve Temiz) ---
st.markdown("""
    <style>
    /* Genel */
    .stApp { background-color: #ffffff; font-family: 'Helvetica Neue', sans-serif; }
    
    /* Başlık Alanı */
    .hero-box {
        text-align: center; padding: 40px 20px;
        background: linear-gradient(120deg, #2b5876 0%, #4e4376 100%);
        color: white; border-radius: 0 0 30px 30px; margin-bottom: 30px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .hero-title { font-size: 3rem; font-weight: 800; margin: 0; }
    .hero-sub { font-size: 1.2rem; opacity: 0.9; font-weight: 300; }
    
    /* Kart Butonlar (Menü) */
    div.stButton > button {
        width: 100%; height: 160px;
        display: flex; flex-direction: column; justify-content: center; align-items: center;
        background: #f8f9fa; border: 1px solid #eee; border-radius: 20px;
        color: #333; box-shadow: 0 4px 6px rgba(0,0,0,0.05); transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        transform: translateY(-5px); box-shadow: 0 10px 20px rgba(0,0,0,0.1);
        border-color: #4e4376; color: #4e4376; background: #fff;
    }
    
    /* Sohbet Balonları */
    .chat-row { padding: 15px; border-radius: 12px; margin-bottom: 10px; line-height: 1.5; }
    .source-box { background: #e3f2fd; border-left: 5px solid #2196F3; color: #0d47a1; }
    .target-box { background: #f3e5f5; border-right: 5px solid #9c27b0; text-align: right; color: #4a148c; }
    
    /* Geri Dön Butonu */
    .back-btn div.stButton > button {
        height: auto; width: auto; padding: 8px 20px; background: #eee; border: none; font-size: 0.9rem;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. API BAĞLANTISI ---
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("Sistem Bakımda (API Key Hatası).")
    st.stop()

# --- 4. STATE YÖNETİMİ ---
if "page" not in st.session_state: st.session_state.page = "home"
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "app_lang" not in st.session_state: st.session_state.app_lang = "Türkçe"

# Dil Paketi
TEXTS = {
    "Türkçe": {
        "hero_title": "LinguaFlow AI",
        "hero_sub": "Yapay Zeka Destekli Dil ve Analiz Merkezi",
        "m1": "🗣️\n\nKARŞILIKLI\nSOHBET",
        "m2": "📂\n\nDOSYA & BELGE\nANALİZİ",
        "m3": "🎙️\n\nSİMÜLTANE\nÇEVİRİ",
        "m4": "🔗\n\nWEB SİTESİ\nOKUYUCU",
        "back": "⬅️ Ana Menü",
        "mic_me": "BEN (Konuş)", "mic_you": "MİSAFİR (Konuş)",
        "proc": "İşleniyor...", "listening": "Dinleniyor...",
        "download": "İndir", "clear": "Temizle",
        "target": "Hedef Dil", "tone": "Ton"
    },
    "English": {
        "hero_title": "LinguaFlow AI",
        "hero_sub": "AI Powered Language & Analysis Hub",
        "m1": "🗣️\n\nDUAL\nCHAT",
        "m2": "📂\n\nFILE & DOC\nANALYSIS",
        "m3": "🎙️\n\nSIMULTANEOUS\nTRANSLATION",
        "m4": "🔗\n\nWEB PAGE\nREADER",
        "back": "⬅️ Main Menu",
        "mic_me": "ME (Speak)", "mic_you": "GUEST (Speak)",
        "proc": "Processing...", "listening": "Listening...",
        "download": "Download", "clear": "Clear",
        "target": "Target Lang", "tone": "Tone"
    }
}
T = TEXTS[st.session_state.app_lang]

# --- 5. MOTOR (BEYİN & ARAÇLAR) ---
def ai_engine(text, task, target_lang="Turkish", tone="Normal"):
    """Tek Merkezli AI Fonksiyonu"""
    if not text: return ""
    
    if task == "translate":
        sys = f"Sen profesyonel tercümansın. Metni {target_lang} diline çevir. Ton: {tone}. Sadece çeviriyi ver."
    elif task == "summarize":
        sys = f"Sen bir analiz uzmanısın. Metni {target_lang} dilinde özetle. Format: 1. Özet, 2. Önemli Noktalar."
    else:
        sys = "Yardımcı ol."

    try:
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys}, {"role": "user", "content": text[:15000]}]
        )
        return res.choices[0].message.content
    except Exception as e: return f"Hata: {e}"

def local_read_pdf(file):
    reader = PyPDF2.PdfReader(file)
    return "".join([page.extract_text() for page in reader.pages])

def local_read_web(url):
    try:
        h = {'User-Agent': 'Mozilla/5.0'}
        soup = BeautifulSoup(requests.get(url, headers=h, timeout=10).content, 'html.parser')
        return " ".join([p.get_text() for p in soup.find_all(['p', 'h1', 'h2'])])[:15000]
    except: return None

def create_audio(text, lang_name):
    code_map = {"Türkçe": "tr", "İngilizce": "en", "Almanca": "de", "Fransızca": "fr", "İspanyolca": "es", "Rusça": "ru", "Arapça": "ar", "Çince": "zh"}
    try:
        fp = io.BytesIO()
        gTTS(text=text, lang=code_map.get(lang_name, "en"), slow=False).write_to_fp(fp)
        return fp.getvalue()
    except: return None

# ==========================================
# EKRANLAR
# ==========================================

# --- GİRİŞ EKRANI ---
def show_home():
    # Dil Seçimi
    c1, c2 = st.columns([9, 1])
    with c2:
        sl = st.selectbox("", ["Türkçe", "English"], label_visibility="collapsed")
        if sl != st.session_state.app_lang: st.session_state.app_lang = sl; st.rerun()

    # Hero
    st.markdown(f"""
    <div class="hero-box">
        <div class="hero-title">{T['hero_title']}</div>
        <div class="hero-sub">{T['hero_sub']}</div>
    </div>
    """, unsafe_allow_html=True)

    # Kartlar (2x2 Grid)
    c1, c2 = st.columns(2)
    with c1:
        if st.button(T["m1"], use_container_width=True): st.session_state.page = "chat"; st.rerun()
        st.write("") # Boşluk
        if st.button(T["m3"], use_container_width=True): st.session_state.page = "conf"; st.rerun()
        
    with c2:
        if st.button(T["m2"], use_container_width=True): st.session_state.page = "file"; st.rerun()
        st.write("") # Boşluk
        if st.button(T["m4"], use_container_width=True): st.session_state.page = "web"; st.rerun()

# --- 1. SOHBET MODU ---
def show_chat():
    st.markdown('<div class="back-btn">', unsafe_allow_html=True)
    if st.button(T["back"]): st.session_state.page = "home"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    with st.sidebar:
        st.header("⚙️ Ayarlar")
        langs = ["English", "Türkçe", "Deutsch", "Français", "Español", "Russian", "Arabic", "Chinese"]
        my_lang = st.selectbox("Ben / Me", langs, index=1 if st.session_state.app_lang=="Türkçe" else 0)
        target_lang = st.selectbox("Misafir / Guest", langs, index=0 if st.session_state.app_lang=="Türkçe" else 1)
        tone = st.select_slider(T["tone"], ["Resmi", "Normal", "Samimi"], value="Normal")
        
        if st.button(T["clear"], type="primary"): st.session_state.chat_history = []; st.rerun()
        
        if st.session_state.chat_history:
            log = "\n".join([f"{m['src']} -> {m['trg']}" for m in st.session_state.chat_history])
            st.download_button(T["download"], log, "chat.txt")

    c1, c2 = st.columns(2)
    with c1:
        st.info(f"👤 {my_lang}")
        a1 = audio_recorder(text="", icon_size="3x", key="m1", recording_color="#2196F3", neutral_color="#e3f2fd")
        if a1:
            with st.spinner(T["proc"]):
                txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(a1)), model="whisper-large-v3").text
                res = ai_engine(txt, "translate", target_lang, tone)
                aud = create_audio(res, target_lang)
                st.session_state.chat_history.append({"src": txt, "trg": res, "dir": "me", "audio": aud})

    with c2:
        st.warning(f"👤 {target_lang}")
        a2 = audio_recorder(text="", icon_size="3x", key="m2", recording_color="#FF5722", neutral_color="#fbe9e7")
        if a2:
            with st.spinner(T["proc"]):
                txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(a2)), model="whisper-large-v3").text
                res = ai_engine(txt, "translate", my_lang, tone)
                aud = create_audio(res, my_lang)
                st.session_state.chat_history.append({"src": txt, "trg": res, "dir": "you", "audio": aud})

    st.divider()
    for i, m in enumerate(reversed(st.session_state.chat_history)):
        align = "source-box" if m["dir"] == "me" else "target-box"
        icon = "🗣️" if m["dir"] == "me" else "🤖"
        st.markdown(f'<div class="chat-row {align}"><small>{icon} {m["src"]}</small><br><strong>{m["trg"]}</strong></div>', unsafe_allow_html=True)
        if m["audio"]: 
            c_a, c_d = st.columns([4,1])
            with c_a: st.audio(m["audio"], format="audio/mp3")
            with c_d: st.download_button("⬇", m["audio"], f"s_{i}.mp3", "audio/mp3", key=f"d_{i}")

# --- 2. DOSYA/PDF MODU ---
def show_file():
    st.markdown('<div class="back-btn">', unsafe_allow_html=True)
    if st.button(T["back"]): st.session_state.page = "home"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    with st.sidebar:
        target = st.selectbox(T["target"], ["Türkçe", "English", "Deutsch"])
    
    st.info("PDF, MP3 veya WAV yükleyin.")
    f = st.file_uploader("Dosya Seç", type=['pdf', 'mp3', 'wav', 'm4a'])
    
    if f:
        ftype = f.name.split('.')[-1].lower()
        if ftype == 'pdf':
            if st.button("📄 PDF Analiz Et"):
                with st.spinner(T["proc"]):
                    txt = local_read_pdf(f)
                    res = ai_engine(txt, "summarize", target)
                    st.markdown(f"### 📄 Analiz Sonucu\n{res}")
                    st.download_button(T["download"], res, "ozet.txt")
        else:
            st.audio(f)
            if st.button("🎧 Sesi Çevir"):
                with st.spinner(T["listening"]):
                    txt = client.audio.transcriptions.create(file=("a.wav", f), model="whisper-large-v3").text
                    res = ai_engine(txt, "translate", target)
                    st.info(f"Orijinal: {txt}")
                    st.success(f"Çeviri: {res}")
                    st.download_button(T["download"], res, "ceviri.txt")

# --- 3. KONFERANS MODU ---
def show_conf():
    st.markdown('<div class="back-btn">', unsafe_allow_html=True)
    if st.button(T["back"]): st.session_state.page = "home"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    with st.sidebar:
        target = st.selectbox(T["target"], ["Türkçe", "English", "Deutsch"])
        tone = st.selectbox(T["tone"], ["Resmi", "Normal"])
    
    st.info("Sürekli Dinleme (5 dakikaya kadar).")
    aud = audio_recorder(text="REC / STOP", icon_size="4x", recording_color="red", pause_threshold=300.0)
    
    if aud:
        with st.spinner(T["proc"]):
            txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(aud)), model="whisper-large-v3").text
            res = ai_engine(txt, "translate", target, tone)
            st.session_state.chat_history.append({"src": txt, "trg": res})
            
    st.divider()
    for m in reversed(st.session_state.chat_history):
        st.markdown(f"**Kaynak:** {m['src']}")
        st.success(f"**Çeviri:** {m['trg']}")
        st.divider()

# --- 4. WEB MODU ---
def show_web():
    st.markdown('<div class="back-btn">', unsafe_allow_html=True)
    if st.button(T["back"]): st.session_state.page = "home"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    with st.sidebar: target = st.selectbox(T["target"], ["Türkçe", "English"])
    
    url = st.text_input("URL (Haber, Blog, Makale)")
    if st.button("Analiz Et") and url:
        with st.spinner(T["proc"]):
            txt = local_read_web(url)
            if txt:
                res = ai_engine(txt, "summarize", target)
                st.markdown(f"### 🌐 Site Raporu\n{res}")
                st.download_button(T["download"], res, "web_analiz.txt")
            else: st.error("Site okunamadı.")

# --- ROUTER ---
if st.session_state.page == "home": show_home()
elif st.session_state.page == "chat": show_chat()
elif st.session_state.page == "conf": show_conf()
elif st.session_state.page == "file": show_file()
elif st.session_state.page == "web": show_web()
elif st.session_state.page == "doc": st.session_state.page = "file"; st.rerun() # Doc, File ile birleşik
