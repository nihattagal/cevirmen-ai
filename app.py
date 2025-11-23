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
import difflib
import random

# --- 1. GENEL AYARLAR ---
st.set_page_config(
    page_title="LinguaFlow Academy",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS TASARIM ---
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; font-family: 'Inter', sans-serif; }
    
    .header-logo { 
        font-size: 2.2rem; font-weight: 800; color: #1e293b; 
        text-align: center; letter-spacing: -0.5px; margin-top: -20px;
    }
    
    .stTextArea textarea {
        border: 1px solid #cbd5e1; border-radius: 12px;
        font-size: 1.1rem; height: 250px !important; padding: 15px;
        background: white; resize: none;
    }
    .stTextArea textarea:focus { border-color: #4f46e5; box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.2); }
    
    .result-box {
        background-color: white; border: 1px solid #cbd5e1; border-radius: 12px;
        min-height: 250px; padding: 20px; font-size: 1.1rem; color: #334155;
        white-space: pre-wrap; box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    
    .diff-container { background: white; padding: 20px; border-radius: 12px; border: 1px solid #cbd5e1; font-family: monospace; }
    .diff-del { background-color: #fecaca; text-decoration: line-through; color: #991b1b; padding: 2px 4px; border-radius: 4px; }
    .diff-add { background-color: #bbf7d0; color: #166534; padding: 2px 4px; border-radius: 4px; font-weight: bold; }
    
    .flashcard {
        background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
        color: white; padding: 40px; border-radius: 20px; text-align: center;
        font-size: 1.5rem; font-weight: bold; box-shadow: 0 10px 25px -5px rgba(79, 70, 229, 0.4);
        margin-bottom: 20px; cursor: pointer;
    }
    .flashcard-reveal {
        background: white; color: #1e293b; border: 2px solid #e2e8f0;
    }

    div.stButton > button {
        background-color: #0f172a; color: white; border: none; border-radius: 8px;
        padding: 12px; font-weight: 600; width: 100%; transition: all 0.2s;
    }
    div.stButton > button:hover { background-color: #334155; transform: translateY(-1px); }
    </style>
""", unsafe_allow_html=True)

# --- 3. API ---
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("⚠️ API Key Eksik!")
    st.stop()

# --- 4. STATE ---
if "history" not in st.session_state: st.session_state.history = []
if "res_text" not in st.session_state: st.session_state.res_text = ""
if "input_val" not in st.session_state: st.session_state.input_val = ""
if "diff_html" not in st.session_state: st.session_state.diff_html = ""
if "flashcard_idx" not in st.session_state: st.session_state.flashcard_idx = -1
if "show_answer" not in st.session_state: st.session_state.show_answer = False

# --- 5. MOTOR ---
def ai_engine(text, task, target_lang="English", tone="Normal", glossary=""):
    if not text: return ""
    
    glossary_prompt = f"TERMİNOLOJİ: \n{glossary}" if glossary else ""

    if task == "translate":
        sys_msg = f"Sen uzman tercümansın. Hedef: {target_lang}. Ton: {tone}. {glossary_prompt}. Sadece çeviriyi ver."
    elif task == "improve":
        sys_msg = "Editörsün. Metni düzelt. Sadece düzeltilmiş metni ver. Açıklama yapma."
    elif task == "summarize":
        # GÜNCELLENEN KISIM: Çeviri vurgusu yapıldı
        sys_msg = f"""
        Sen bir analiz uzmanısın.
        GÖREV: Verilen metni analiz et ve {target_lang} diline çevirerek özetle.
        ÇIKTI FORMATI:
        1. 📋 Genel Özet ({target_lang})
        2. 💡 Önemli Noktalar ({target_lang})
        NOT: Çıktı tamamen {target_lang} dilinde olmalı.
        """

    try:
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": text[:15000]}]
        )
        result = res.choices[0].message.content
        
        if task == "translate":
            ts = datetime.datetime.now().strftime("%d/%m")
            st.session_state.history.insert(0, {"ts": ts, "src": text, "trg": result})
            
        return result
    except Exception as e: return f"Hata: {e}"

def generate_diff(original, corrected):
    d = difflib.Differ()
    diff = list(d.compare(original.split(), corrected.split()))
    html = []
    for token in diff:
        if token.startswith("- "):
            html.append(f"<span class='diff-del'>{token[2:]}</span>")
        elif token.startswith("+ "):
            html.append(f"<span class='diff-add'>{token[2:]}</span>")
        elif token.startswith("  "):
            html.append(token[2:])
    return " ".join(html)

def create_audio(text, lang_name, speed=False):
    code_map = {"Türkçe": "tr", "İngilizce": "en", "Almanca": "de", "Fransızca": "fr", "Español": "es", "Rusça": "ru", "Arapça": "ar", "Çince": "zh"}
    lang_code = code_map.get(lang_name, "en")
    try:
        fp = io.BytesIO()
        gTTS(text=text, lang=lang_code, slow=speed).write_to_fp(fp)
        return fp.getvalue()
    except: return None

def local_read_file(file):
    try:
        if file.name.endswith('.pdf'):
            reader = PyPDF2.PdfReader(file)
            return "".join([page.extract_text() for page in reader.pages])
        else: return client.audio.transcriptions.create(file=("a.wav", file), model="whisper-large-v3").text
    except: return None

def local_read_web(url):
    try:
        h = {'User-Agent': 'Mozilla/5.0'}
        soup = BeautifulSoup(requests.get(url, headers=h, timeout=10).content, 'html.parser')
        return " ".join([p.get_text() for p in soup.find_all(['p', 'h1', 'h2'])])[:10000]
    except: return None

# ==========================================
# ARAYÜZ
# ==========================================

with st.sidebar:
    st.title("LinguaFlow")
    st.caption("Academy Edition v26.2")
    
    st.markdown("### ⚙️ Ayarlar")
    speed_opt = st.select_slider("Konuşma Hızı", options=["Yavaş", "Normal"], value="Normal")
    is_slow = True if speed_opt == "Yavaş" else False
    
    with st.expander("📚 Sözlük"):
        glossary_txt = st.text_area("Örn: AI=Yapay Zeka", height=70)

    st.divider()
    st.markdown("### 🕒 Son Çeviriler")
    if st.session_state.history:
        for item in st.session_state.history[:5]:
            st.caption(f"{item['src'][:20]}.. → {item['trg'][:20]}..")
        if st.button("Temizle"): st.session_state.history = []; st.rerun()

st.markdown('<div class="header-logo">LinguaFlow Academy</div>', unsafe_allow_html=True)

tab_text, tab_practice, tab_voice, tab_files, tab_web = st.tabs(["📝 Metin & Analiz", "🧠 Alıştırma", "🎙️ Ses", "📂 Dosya", "🔗 Web"])
LANG_OPTIONS = ["Türkçe", "English", "Deutsch", "Français", "Español", "Italiano", "Русский", "العربية", "中文"]

# --- 1. METİN ---
with tab_text:
    c1, c2, c3 = st.columns([3, 1, 3])
    with c1: st.markdown("**Giriş**")
    with c3: target_lang = st.selectbox("Hedef", LANG_OPTIONS, label_visibility="collapsed")

    col_in, col_out = st.columns(2)
    
    with col_in:
        input_text = st.text_area("Metin", value=st.session_state.input_val, height=250, placeholder="Yazın...", label_visibility="collapsed")
        
        b1, b2, b3 = st.columns([2, 2, 1])
        with b1:
            if st.button("Çevir ➔"):
                if input_text:
                    with st.spinner("..."):
                        st.session_state.res_text = ai_engine(input_text, "translate", target_lang, "Normal", glossary_txt)
                        st.session_state.diff_html = ""
                        st.session_state.input_val = input_text
        with b2:
            if st.button("🔍 Hataları Bul (Diff)"):
                if input_text:
                    with st.spinner("İnceleniyor..."):
                        corrected = ai_engine(input_text, "improve")
                        st.session_state.res_text = corrected
                        st.session_state.diff_html = generate_diff(input_text, corrected)
        with b3: tone = st.selectbox("Ton", ["Normal", "Resmi"], label_visibility="collapsed")

    with col_out:
        if st.session_state.diff_html:
            st.markdown(f"<div class='diff-container'>{st.session_state.diff_html}</div>", unsafe_allow_html=True)
            st.caption("🔴 Silinen  🟢 Eklenen")
        else:
            res = st.session_state.res_text
            st.markdown(f"""<div class="result-box">{res if res else '...'}</div>""", unsafe_allow_html=True)
            
            if res:
                st.write("")
                ca, cb = st.columns([1, 4])
                with ca:
                    aud = create_audio(res, target_lang, is_slow)
                    if aud: st.audio(aud, format="audio/mp3")
                with cb: st.code(res, language=None)

# --- 2. ALIŞTIRMA ---
with tab_practice:
    if len(st.session_state.history) < 3:
        st.info("🧠 Alıştırma için 'Metin' sekmesinde en az 3 çeviri yapın.")
    else:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            if st.button("🎲 Yeni Kart Çek", use_container_width=True):
                st.session_state.flashcard_idx = random.randint(0, len(st.session_state.history)-1)
                st.session_state.show_answer = False
                st.rerun()
            
            if st.session_state.flashcard_idx >= 0:
                card = st.session_state.history[st.session_state.flashcard_idx]
                st.markdown(f"<div class='flashcard'>{card['src']}</div>", unsafe_allow_html=True)
                if st.button("👁️ Cevabı Göster"):
                    st.session_state.show_answer = True
                    st.rerun()
                if st.session_state.show_answer:
                    st.markdown(f"<div class='flashcard flashcard-reveal'>{card['trg']}</div>", unsafe_allow_html=True)

# --- 3. SES ---
with tab_voice:
    mode = st.radio("Mod:", ["🗣️ Sohbet", "🎙️ Konferans"], horizontal=True)
    st.divider()
    if "Sohbet" in mode:
        c1, c2 = st.columns(2)
        with c1:
            st.info("SİZ")
            a1 = audio_recorder(text="", icon_size="3x", key="v1", recording_color="#3b82f6")
            if a1:
                txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(a1)), model="whisper-large-v3").text
                res = ai_engine(txt, "translate", target_lang, glossary=glossary_txt)
                st.success(f"{txt} -> {res}")
                aud = create_audio(res, target_lang, is_slow)
                if aud: st.audio(aud, format="audio/mp3", autoplay=True)
        with c2:
            st.warning(f"MİSAFİR ({target_lang})")
            a2 = audio_recorder(text="", icon_size="3x", key="v2", recording_color="#ec4899")
            if a2:
                txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(a2)), model="whisper-large-v3").text
                res = ai_engine(txt, "translate", "Türkçe", glossary=glossary_txt)
                st.info(f"{txt} -> {res}")
                aud = create_audio(res, "Türkçe", is_slow)
                if aud: st.audio(aud, format="audio/mp3", autoplay=True)
    else:
        c1, c2 = st.columns([1, 3])
        with c1:
            ac = audio_recorder(text="BAŞLAT / DURDUR", icon_size="2x", recording_color="#dc2626", pause_threshold=20.0)
        with c2:
            if ac:
                with st.spinner("Analiz..."):
                    txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(ac)), model="whisper-large-v3").text
                    trans = ai_engine(txt, "translate", target_lang, glossary=glossary_txt)
                    st.success(f"Orijinal: {txt}")
                    st.info(f"Çeviri: {trans}")
                    st.download_button("İndir", f"{txt}\n{trans}", "kayit.txt")

# --- 4. DOSYA ---
with tab_files:
    u_file = st.file_uploader("Dosya", type=['pdf', 'mp3', 'wav', 'm4a'])
    if u_file:
        if st.button("İşle"):
            with st.spinner("..."):
                raw = local_read_file(u_file)
                if raw:
                    mode = "translate" if len(raw) < 3000 else "summarize"
                    res = ai_engine(raw, mode, target_lang, glossary=glossary_txt)
                    st.markdown(f"<div class='result-box'>{res}</div>", unsafe_allow_html=True)
                    st.download_button("İndir", res, "sonuc.txt")
                else: st.error("Hata.")

# --- 5. WEB (DİL SEÇİMİ EKLENDİ) ---
with tab_web:
    c_url, c_lang = st.columns([3, 1])
    with c_url:
        url = st.text_input("URL", placeholder="https://...")
    with c_lang:
        web_lang = st.selectbox("Rapor Dili", LANG_OPTIONS, key="w_lang") # Dil Seçimi Eklendi

    if st.button("Siteyi Analiz Et") and url:
        with st.spinner("Site okunuyor ve çevriliyor..."):
            txt = local_read_web(url)
            if txt:
                res = ai_engine(txt, "summarize", target_lang=web_lang) # Seçili dil gönderiliyor
                st.markdown(f"<div class='result-box'>{res}</div>", unsafe_allow_html=True)
                st.download_button("İndir", res, "web.txt")
            else: st.error("Siteye erişilemedi (Güvenlik duvarı olabilir).")

st.divider()
