import streamlit as st
from groq import Groq
from audio_recorder_streamlit import audio_recorder
from gtts import gTTS
import io
import requests
from bs4 import BeautifulSoup
import PyPDF2
import datetime
import urllib.parse

# --- 1. GENEL AYARLAR ---
st.set_page_config(
    page_title="LinguaFlow Master",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS TASARIM (PREMIUM) ---
st.markdown("""
    <style>
    .stApp { background-color: #f1f5f9; font-family: 'Segoe UI', sans-serif; }
    
    /* Başlık */
    .header-logo { 
        font-size: 2.2rem; font-weight: 800; color: #1e3a8a; 
        text-align: center; margin-bottom: 5px; letter-spacing: -0.5px;
    }
    .header-sub { text-align: center; color: #64748b; margin-bottom: 25px; }
    
    /* Metin Alanı */
    .stTextArea textarea {
        border: 1px solid #cbd5e1; border-radius: 12px;
        font-size: 1.1rem; height: 250px !important; padding: 15px;
        background: white; resize: none;
    }
    .stTextArea textarea:focus { border-color: #3b82f6; box-shadow: 0 0 0 2px rgba(59,130,246,0.2); }
    
    /* Sonuç Kutusu */
    .result-box {
        background-color: white; border: 1px solid #cbd5e1; border-radius: 12px;
        min-height: 250px; padding: 20px; font-size: 1.1rem; color: #334155;
        white-space: pre-wrap; position: relative;
    }
    
    /* Açıklama Kutusu (AI Hoca) */
    .explain-box {
        background-color: #fff7ed; border-left: 5px solid #f97316;
        padding: 15px; border-radius: 8px; margin-top: 15px;
        font-size: 0.95rem; color: #9a3412;
    }
    
    /* Butonlar */
    div.stButton > button {
        background-color: #1e293b; color: white; border: none; border-radius: 8px;
        padding: 12px; font-weight: 600; width: 100%; transition: all 0.2s;
    }
    div.stButton > button:hover { background-color: #334155; transform: translateY(-1px); }
    
    /* Sohbet Balonları */
    .chat-me { background: #dbeafe; border-radius: 12px 12px 0 12px; padding: 12px; margin: 5px 0; text-align: right; margin-left: auto; max-width: 80%; }
    .chat-you { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px 12px 12px 0; padding: 12px; margin: 5px 0; max-width: 80%; }
    
    /* Geçmiş Öğesi */
    .history-item {
        font-size: 0.8rem; padding: 8px; border-bottom: 1px solid #e2e8f0;
        color: #475569;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. API ---
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("⚠️ API Key Hatası!")
    st.stop()

# --- 4. STATE ---
if "history" not in st.session_state: st.session_state.history = []
if "res_text" not in st.session_state: st.session_state.res_text = ""
if "explanation" not in st.session_state: st.session_state.explanation = ""
if "input_val" not in st.session_state: st.session_state.input_val = ""

# --- 5. MOTOR (AI HOCA EKLENDİ) ---
def ai_engine(text, task, target_lang="English", tone="Normal"):
    if not text: return "", ""
    
    explanation = ""
    
    if task == "translate":
        # Eğer çok kısaysa sözlük gibi davran
        if len(text.split()) < 4:
            sys_msg = f"Sen bir sözlüksün. '{text}' kelimesini {target_lang} diline çevir. 1. Anlam, 2. Tür, 3. Örnek Cümle ver."
        else:
            sys_msg = f"Sen tercümansın. Hedef: {target_lang}. Ton: {tone}. Sadece çeviriyi ver."
            
    elif task == "improve":
        sys_msg = "Sen editörsün. Metni düzelt. Sadece düzeltilmiş hali ver."
        
    elif task == "explain": # YENİ MOD: AI HOCA
        sys_msg = f"Sen bir dil öğretmenisin. Bu metindeki gramer hatalarını bul, düzelt ve NEDEN yanlış olduğunu {target_lang} dilinde açıkla. Kısa ve öz ol."
    
    elif task == "summarize":
        sys_msg = f"Sen analistsin. Metni {target_lang} dilinde özetle."

    try:
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": text[:15000]}]
        )
        result = res.choices[0].message.content
        
        # Geçmişe Ekle (Sadece ana işlemler)
        if task in ["translate", "improve"]:
            ts = datetime.datetime.now().strftime("%H:%M")
            short = (text[:20] + '..') if len(text) > 20 else text
            st.session_state.history.insert(0, f"[{ts}] {short}")
            
        return result
    except Exception as e: return f"Hata: {e}"

def create_audio(text, lang_name):
    code_map = {"Türkçe": "tr", "İngilizce": "en", "Almanca": "de", "Fransızca": "fr", "İspanyolca": "es", "Rusça": "ru", "Arapça": "ar", "Çince": "zh"}
    lang_code = code_map.get(lang_name, "en")
    try:
        fp = io.BytesIO()
        gTTS(text=text, lang=lang_code, slow=False).write_to_fp(fp)
        return fp.getvalue()
    except: return None

def render_share(text):
    if not text: return
    encoded = urllib.parse.quote(text)
    wa = f"https://api.whatsapp.com/send?text={encoded}"
    st.markdown(f"<a href='{wa}' target='_blank' style='text-decoration:none; color:#25D366; font-weight:bold;'>📲 WhatsApp ile Paylaş</a>", unsafe_allow_html=True)

def local_read_file(file):
    try:
        if file.name.endswith('.pdf'):
            reader = PyPDF2.PdfReader(file)
            return "".join([page.extract_text() for page in reader.pages])
        else: return client.audio.transcriptions.create(file=("a.wav", file), model="whisper-large-v3").text
    except: return None

# ==========================================
# ARAYÜZ
# ==========================================

# --- YAN MENÜ ---
with st.sidebar:
    st.title("LinguaFlow")
    st.caption("v11.0 Master Class")
    
    st.markdown("### ⚙️ Ayarlar")
    auto_speak = st.checkbox("🔊 Otomatik Okuma", value=True)
    
    st.divider()
    st.markdown("### 🕒 Geçmiş")
    if st.session_state.history:
        for item in st.session_state.history[:10]:
            st.markdown(f"<div class='history-item'>{item}</div>", unsafe_allow_html=True)
        
        # TÜM GEÇMİŞİ İNDİR
        full_history = "\n".join(st.session_state.history)
        st.download_button("💾 Tüm Geçmişi İndir", full_history, "gecmis.txt")
        
        if st.button("Temizle", type="secondary"):
            st.session_state.history = []
            st.rerun()

# --- BAŞLIK ---
st.markdown('<div class="header-logo">LinguaFlow Master</div><div class="header-sub">Öğreten Yapay Zeka Çevirmeni</div>', unsafe_allow_html=True)

# --- SEKMELER ---
tab_text, tab_voice, tab_files, tab_web = st.tabs(["👨‍🏫 Metin & Hoca", "🎙️ Ses & Konferans", "📂 Dosya", "🔗 Web"])
LANG_OPTIONS = ["English", "Türkçe", "Deutsch", "Français", "Español", "Italiano", "Русский", "العربية", "中文"]

# --- 1. METİN & HOCA ---
with tab_text:
    c1, c2, c3 = st.columns([3, 1, 3])
    with c1: st.markdown("**Giriş**")
    with c3: target_lang = st.selectbox("Hedef", LANG_OPTIONS, label_visibility="collapsed")

    col_in, col_out = st.columns(2)
    with col_in:
        input_text = st.text_area("Giriş", value=st.session_state.input_val, height=280, placeholder="Metni buraya yazın...", label_visibility="collapsed")
        
        b1, b2, b3, b4 = st.columns([3, 3, 2, 1])
        with b1:
            if st.button("Çevir ➔"):
                if input_text:
                    with st.spinner("..."):
                        st.session_state.res_text = ai_engine(input_text, "translate", target_lang)
                        st.session_state.explanation = "" # Açıklamayı sıfırla
                        st.session_state.input_val = input_text
        with b2:
            if st.button("✨ Düzelt & Açıkla"):
                if input_text:
                    with st.spinner("Hoca inceliyor..."):
                        st.session_state.res_text = ai_engine(input_text, "improve")
                        # Ayrıca açıklama iste
                        st.session_state.explanation = ai_engine(input_text, "explain", target_lang="Türkçe") # Açıklamalar Türkçe olsun
        with b3: tone = st.selectbox("Ton", ["Normal", "Resmi", "Samimi"], label_visibility="collapsed")
        with b4: 
            if st.button("🗑️"): st.session_state.input_val=""; st.session_state.res_text=""; st.session_state.explanation=""; st.rerun()

    with col_out:
        res = st.session_state.res_text
        st.markdown(f"""<div class="result-box">{res if res else '...'}</div>""", unsafe_allow_html=True)
        
        # AI Hoca Açıklaması (Varsa Göster)
        if st.session_state.explanation:
            st.markdown(f"""<div class="explain-box"><b>👨‍🏫 Hoca'nın Notları:</b><br>{st.session_state.explanation}</div>""", unsafe_allow_html=True)
        
        if res:
            st.write("")
            ca, cb = st.columns([1, 3])
            with ca:
                aud = create_audio(res, target_lang)
                if aud: 
                    st.audio(aud, format="audio/mp3")
                    if auto_speak and not st.session_state.explanation: # Sadece çeviride otomatik oku
                        st.audio(aud, format="audio/mp3", autoplay=True)
            with cb: render_share(res)

# --- 2. SES ---
with tab_voice:
    mode = st.radio("Mod:", ["🗣️ Karşılıklı Sohbet", "🎙️ Konferans"], horizontal=True)
    st.divider()
    
    if "Sohbet" in mode:
        c1, c2 = st.columns(2)
        with c1:
            st.info("SİZ (Sol)")
            a1 = audio_recorder(text="", icon_size="3x", key="v1", recording_color="#3b82f6", neutral_color="#dbeafe")
            if a1:
                txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(a1)), model="whisper-large-v3").text
                res = ai_engine(txt, "translate", target_lang)
                aud = create_audio(res, target_lang)
                st.markdown(f"<div class='chat-me'>{txt}<br><b>{res}</b></div>", unsafe_allow_html=True)
                if aud and auto_speak: st.audio(aud, format="audio/mp3", autoplay=True)
        
        with c2:
            st.warning(f"MİSAFİR ({target_lang})")
            a2 = audio_recorder(text="", icon_size="3x", key="v2", recording_color="#ec4899", neutral_color="#fce7f3")
            if a2:
                txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(a2)), model="whisper-large-v3").text
                res = ai_engine(txt, "translate", "Türkçe")
                aud = create_audio(res, "Türkçe")
                st.markdown(f"<div class='chat-you'>{txt}<br><b>{res}</b></div>", unsafe_allow_html=True)
                if aud and auto_speak: st.audio(aud, format="audio/mp3", autoplay=True)

    else: # Konferans
        c1, c2 = st.columns([1, 3])
        with c1:
            st.write("Sürekli Dinleme")
            ac = audio_recorder(text="BAŞLAT / DURDUR", icon_size="2x", recording_color="#dc2626", pause_threshold=20.0)
        with c2:
            if ac:
                with st.spinner("Analiz..."):
                    try:
                        txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(ac)), model="whisper-large-v3").text
                        trans = ai_engine(txt, "translate", target_lang)
                        st.success(f"Orijinal: {txt}")
                        st.info(f"Çeviri: {trans}")
                        st.download_button("İndir", f"{txt}\n{trans}", "kayit.txt")
                    except: st.error("Ses yok.")

# --- 3. DOSYA ---
with tab_files:
    u_file = st.file_uploader("Dosya", type=['pdf', 'mp3', 'wav', 'm4a'])
    if u_file:
        if st.button("İşle"):
            with st.spinner("..."):
                raw = local_read_file(u_file)
                if raw:
                    mode = "translate" if len(raw) < 3000 else "summarize"
                    res = ai_engine(raw, mode, target_lang)
                    st.markdown(f"<div class='result-box'>{res}</div>", unsafe_allow_html=True)
                    st.download_button("İndir", res, "sonuc.txt")
                else: st.error("Okunamadı.")

# --- 4. WEB ---
with tab_web:
    url = st.text_input("URL")
    if st.button("Analiz") and url:
        with st.spinner("..."):
            try:
                h = {'User-Agent': 'Mozilla/5.0'}
                soup = BeautifulSoup(requests.get(url, headers=h, timeout=10).content, 'html.parser')
                raw = " ".join([p.get_text() for p in soup.find_all(['p', 'h1'])])[:10000]
                res = ai_engine(raw, "summarize", target_lang)
                st.markdown(f"<div class='result-box'>{res}</div>", unsafe_allow_html=True)
                st.download_button("İndir", res, "web.txt")
            except: st.error("Hata.")

st.divider()
