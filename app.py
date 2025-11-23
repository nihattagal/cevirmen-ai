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
    page_title="LinguaFlow Edu",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS TASARIM ---
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; font-family: 'Inter', sans-serif; }
    
    /* Başlık */
    .header-logo { 
        font-size: 2rem; font-weight: 800; color: #1e1b4b; 
        text-align: center; margin-top: -20px;
    }
    
    /* Metin Alanı */
    .stTextArea textarea {
        border: 1px solid #cbd5e1; border-radius: 12px;
        font-size: 1.1rem; height: 250px !important; padding: 15px;
        background: white; resize: none;
    }
    .stTextArea textarea:focus { border-color: #4f46e5; box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.2); }
    
    /* Sonuç Kutusu */
    .result-box {
        background-color: white; border: 1px solid #cbd5e1; border-radius: 12px;
        min-height: 250px; padding: 20px; font-size: 1.1rem; color: #334155;
        white-space: pre-wrap; position: relative;
    }
    
    /* Kaydedilen Kelime Kartı */
    .vocab-card {
        background: white; padding: 10px; border-radius: 8px; 
        border-left: 4px solid #f59e0b; margin-bottom: 8px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05); font-size: 0.9rem;
    }
    
    /* Butonlar */
    div.stButton > button {
        background-color: #1e1b4b; color: white; border: none; border-radius: 8px;
        padding: 12px; font-weight: 600; width: 100%; transition: all 0.2s;
    }
    div.stButton > button:hover { background-color: #312e81; transform: translateY(-1px); }
    
    /* İkincil Buton (Kaydet) */
    .save-btn div.stButton > button {
        background-color: #f59e0b; color: white;
    }
    .save-btn div.stButton > button:hover { background-color: #d97706; }
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
if "saved_vocab" not in st.session_state: st.session_state.saved_vocab = [] # Kelime Defteri
if "res_text" not in st.session_state: st.session_state.res_text = ""
if "input_val" not in st.session_state: st.session_state.input_val = ""
if "idiom_mode" not in st.session_state: st.session_state.idiom_mode = False

# --- 5. MOTOR ---
def ai_engine(text, task, target_lang="English", tone="Normal", glossary="", idiom_active=False):
    if not text: return ""
    
    glossary_prompt = f"TERMİNOLOJİ: \n{glossary}" if glossary else ""
    
    # Deyim Modu Ekstra Emri
    idiom_prompt = ""
    if idiom_active:
        idiom_prompt = f"""
        DİKKAT: Metin içindeki deyimleri, atasözlerini veya argoyu tespit et.
        Çeviriyi yaparken parantez içinde orijinal anlamını ve kültürel karşılığını açıkla.
        Örn: "It's raining cats and dogs" -> "Bardaktan boşalırcasına yağmur yağıyor (İngilizce deyim: Kediler ve köpekler yağıyor)"
        """

    if task == "translate":
        sys_msg = f"""
        Sen uzman tercümansın. Hedef: {target_lang}. Ton: {tone}.
        {glossary_prompt}
        {idiom_prompt}
        GÖREV: Kaynak dili algıla ve çevir. Sadece çeviriyi ver.
        """
    elif task == "improve":
        sys_msg = "Editörsün. Metni düzelt. Format: [DİL] ||| METİN"
    elif task == "summarize":
        sys_msg = f"Analistsin. Metni {target_lang} dilinde özetle."

    try:
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": text[:15000]}]
        )
        full_res = res.choices[0].message.content
        
        if "|||" in full_res:
            lang_tag, content = full_res.split("|||", 1)
            return content.strip()
        else:
            return full_res

    except Exception as e: return f"Hata: {str(e)}"

def create_audio(text, lang_name, speed=False):
    code_map = {"Türkçe": "tr", "İngilizce": "en", "Almanca": "de", "Fransızca": "fr", "Español": "es", "Rusça": "ru", "Arapça": "ar", "Çince": "zh"}
    lang_code = code_map.get(lang_name, "en")
    try:
        fp = io.BytesIO()
        gTTS(text=text, lang=lang_code, slow=speed).write_to_fp(fp)
        return fp.getvalue()
    except: return None

def render_share(text):
    if not text: return
    encoded = urllib.parse.quote(text)
    wa = f"https://api.whatsapp.com/send?text={encoded}"
    st.markdown(f"<a href='{wa}' target='_blank' style='text-decoration:none; color:#25D366; font-weight:bold; font-size:0.85rem;'>📲 WhatsApp</a>", unsafe_allow_html=True)

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
    st.markdown("### ⭐ Kelime Defterim")
    if st.session_state.saved_vocab:
        for i, v in enumerate(st.session_state.saved_vocab[::-1][:10]): # Son 10 kayıt
            st.markdown(f"<div class='vocab-card'><b>{v['src']}</b><br>↳ {v['trg']}</div>", unsafe_allow_html=True)
        
        # Defteri İndir
        vocab_text = "\n".join([f"{v['src']} = {v['trg']}" for v in st.session_state.saved_vocab])
        st.download_button("💾 Defteri İndir", vocab_text, "kelime_defterim.txt")
        
        if st.button("🗑️ Defteri Sil", type="secondary"):
            st.session_state.saved_vocab = []
            st.rerun()
    else:
        st.info("Henüz kelime kaydetmedin.")

    st.divider()
    
    st.markdown("### ⚙️ Ayarlar")
    idiom_mode = st.checkbox("🧐 Deyim/Kültür Modu", value=False, help="Deyimlerin anlamlarını açıklar.")
    speech_slow = st.checkbox("🐢 Yavaş Okuma", value=False)
    
    with st.expander("📚 Sözlük"):
        glossary_txt = st.text_area("Örn: AI=Yapay Zeka", height=80)

# --- BAŞLIK ---
st.markdown('<div class="header-logo">LinguaFlow Edu</div>', unsafe_allow_html=True)

# --- SEKMELER ---
tab_text, tab_voice, tab_files, tab_web = st.tabs(["📝 Metin", "🎙️ Ses", "📂 Dosya", "🔗 Web"])
LANG_OPTIONS = ["English", "Türkçe", "Deutsch", "Français", "Español", "Italiano", "Русский", "العربية", "中文"]

# --- 1. METİN ---
with tab_text:
    c1, c2, c3 = st.columns([3, 1, 3])
    with c1: st.markdown("**Giriş**")
    with c3: target_lang = st.selectbox("Hedef", LANG_OPTIONS, label_visibility="collapsed")

    col_in, col_out = st.columns(2)
    
    with col_in:
        with st.form(key="trans_form"):
            input_text = st.text_area("Metin", value=st.session_state.input_val, height=250, placeholder="Yazın...", label_visibility="collapsed")
            
            b1, b2 = st.columns([3, 1])
            with b1: submit_btn = st.form_submit_button("Çevir ➔", type="primary", use_container_width=True)
            with b2: tone = st.selectbox("Ton", ["Normal", "Resmi", "Samimi"], label_visibility="collapsed")
        
        if submit_btn and input_text:
            with st.spinner("..."):
                st.session_state.res_text = ai_engine(input_text, "translate", target_lang, tone, glossary_txt, idiom_mode)
                st.session_state.input_val = input_text

    with col_out:
        res = st.session_state.res_text
        
        st.markdown(f"""
        <div class="result-box">
            {res if res else '...'}
        </div>
        """, unsafe_allow_html=True)
        
        if res:
            st.write("")
            ca, cb, cc = st.columns([2, 2, 2])
            with ca:
                aud = create_audio(res, target_lang, speech_slow)
                if aud: st.audio(aud, format="audio/mp3")
            
            with cb:
                # KAYDET BUTONU
                st.markdown('<div class="save-btn">', unsafe_allow_html=True)
                if st.button("⭐ Kaydet"):
                    entry = {"src": input_text[:30], "trg": res[:30]}
                    st.session_state.saved_vocab.append(entry)
                    st.toast("Kelime Defterine Eklendi!", icon="📚")
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
                
            with cc: render_share(res)

# --- 2. SES ---
with tab_voice:
    mode = st.radio("Mod:", ["🗣️ Sohbet", "🎙️ Konferans"], horizontal=True)
    st.divider()
    
    if "Sohbet" in mode:
        c1, c2 = st.columns(2)
        with c1:
            st.info("SİZ")
            a1 = audio_recorder(text="", icon_size="3x", key="v1", recording_color="#3b82f6", neutral_color="#dbeafe")
            if a1:
                txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(a1)), model="whisper-large-v3").text
                res = ai_engine(txt, "translate", target_lang, glossary=glossary_txt, idiom_active=idiom_mode)
                aud = create_audio(res, target_lang, speech_slow)
                st.markdown(f"<div class='result-box' style='min-height:100px; border-left:4px solid #3b82f6'>{txt}<br><br><b>{res}</b></div>", unsafe_allow_html=True)
                if aud: st.audio(aud, format="audio/mp3", autoplay=True)
        with c2:
            st.warning(f"MİSAFİR ({target_lang})")
            a2 = audio_recorder(text="", icon_size="3x", key="v2", recording_color="#ec4899", neutral_color="#fce7f3")
            if a2:
                txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(a2)), model="whisper-large-v3").text
                res = ai_engine(txt, "translate", "Türkçe", glossary=glossary_txt, idiom_active=idiom_mode)
                aud = create_audio(res, "Türkçe", speech_slow)
                st.markdown(f"<div class='result-box' style='min-height:100px; border-right:4px solid #ec4899; text-align:right'>{txt}<br><br><b>{res}</b></div>", unsafe_allow_html=True)
                if aud: st.audio(aud, format="audio/mp3", autoplay=True)

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
                        trans = ai_engine(txt, "translate", target_lang, glossary=glossary_txt, idiom_active=idiom_mode)
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
                    res = ai_engine(raw, mode, target_lang, glossary=glossary_txt)
                    st.markdown(f"<div class='result-box'>{res}</div>", unsafe_allow_html=True)
                    st.download_button("İndir", res, "sonuc.txt")
                else: st.error("Okunamadı.")

# --- 4. WEB ---
with tab_web:
    url = st.text_input("URL")
    if st.button("Analiz") and url:
        with st.spinner("..."):
            txt = local_read_web(url)
            if txt:
                res = ai_engine(txt, "summarize", target_lang)
                st.markdown(f"<div class='result-box'>{res}</div>", unsafe_allow_html=True)
                st.download_button("İndir", res, "web.txt")
            else: st.error("Hata.")

st.divider()
