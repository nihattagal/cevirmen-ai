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
    page_title="LinguaFlow Pro",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS TASARIM (MODERN & ERGONOMİK) ---
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; font-family: 'Inter', sans-serif; }
    
    /* Başlık */
    .header-logo { 
        font-size: 2.2rem; font-weight: 800; color: #0f172a; 
        text-align: center; margin-top: -20px; letter-spacing: -1px;
    }
    
    /* Metin Alanı */
    .stTextArea textarea {
        border: 1px solid #cbd5e1; border-radius: 12px;
        font-size: 1.1rem; height: 250px !important; padding: 15px;
        background: white; resize: none; box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .stTextArea textarea:focus { border-color: #6366f1; box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15); }
    
    /* Sonuç Kutusu */
    .result-box {
        background-color: white; border: 1px solid #cbd5e1; border-radius: 12px;
        min-height: 250px; padding: 20px; font-size: 1.1rem; color: #334155;
        white-space: pre-wrap; box-shadow: 0 2px 4px rgba(0,0,0,0.02); position: relative;
    }
    
    /* Butonlar */
    div.stButton > button {
        background-color: #0f172a; color: white; border: none; border-radius: 8px;
        padding: 10px; font-weight: 600; width: 100%; transition: all 0.2s;
    }
    div.stButton > button:hover { background-color: #334155; transform: translateY(-1px); }
    
    /* Kaydet Butonu */
    .save-btn div.stButton > button { background-color: #f59e0b; color: white; }
    .save-btn div.stButton > button:hover { background-color: #d97706; }

    /* Swap Butonu */
    .swap-btn div.stButton > button { background-color: #e2e8f0; color: #333; }
    .swap-btn div.stButton > button:hover { background-color: #cbd5e1; }

    /* Kelime Kartı */
    .vocab-card {
        background: white; padding: 10px; border-radius: 8px; 
        border-left: 4px solid #f59e0b; margin-bottom: 8px; font-size: 0.9rem;
    }
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
if "saved_vocab" not in st.session_state: st.session_state.saved_vocab = []
if "res_text" not in st.session_state: st.session_state.res_text = ""
if "input_val" not in st.session_state: st.session_state.input_val = ""
if "target_lang_idx" not in st.session_state: st.session_state.target_lang_idx = 0 # İngilizce varsayılan

# --- 5. MOTOR ---
def ai_engine(text, task, target_lang="English", tone="Normal", glossary="", idiom_active=False):
    if not text: return ""
    
    glossary_prompt = f"TERMİNOLOJİ: \n{glossary}" if glossary else ""
    idiom_prompt = "Deyim varsa açıkla." if idiom_active else ""

    if task == "translate":
        sys_msg = f"""
        Sen uzman tercümansın. Hedef: {target_lang}. Ton: {tone}.
        {glossary_prompt} {idiom_prompt}
        GÖREV: Kaynak dili algıla ve çevir. Sadece çeviriyi ver.
        """
    elif task == "improve":
        sys_msg = "Editörsün. Metni düzelt. Dili koru."
    elif task == "summarize":
        sys_msg = f"Analistsin. Metni {target_lang} dilinde özetle."

    try:
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": text[:15000]}]
        )
        return res.choices[0].message.content
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
        for v in st.session_state.saved_vocab[::-1][:5]:
            st.markdown(f"<div class='vocab-card'><b>{v['src']}</b><br>↳ {v['trg']}</div>", unsafe_allow_html=True)
        vocab_text = "\n".join([f"{v['src']} = {v['trg']}" for v in st.session_state.saved_vocab])
        st.download_button("💾 Defteri İndir", vocab_text, "kelimeler.txt")
        if st.button("🗑️ Sil", type="secondary"): st.session_state.saved_vocab = []; st.rerun()
    else: st.info("Boş.")

    st.divider()
    st.markdown("### ⚙️ Ayarlar")
    idiom_mode = st.checkbox("🧐 Deyim Modu", value=False)
    speech_slow = st.checkbox("🐢 Yavaş Okuma", value=False)
    with st.expander("📚 Sözlük"):
        glossary_txt = st.text_area("Örn: AI=Yapay Zeka", height=70)

# --- BAŞLIK ---
st.markdown('<div class="header-logo">LinguaFlow Pro</div>', unsafe_allow_html=True)

# --- SEKMELER ---
tab_text, tab_voice, tab_files, tab_web = st.tabs(["📝 Metin & Dikte", "🎙️ Sesli Sohbet", "📂 Dosya", "🔗 Web"])
LANG_OPTIONS = ["English", "Türkçe", "Deutsch", "Français", "Español", "Italiano", "Русский", "العربية", "中文"]

# --- 1. METİN & DİKTE ---
with tab_text:
    c1, c2, c3, c4 = st.columns([3, 1, 3, 1])
    with c1: st.markdown("**Giriş (Otomatik)**")
    
    # HEDEF DİL SEÇİMİ (Session State ile Yönetilen)
    with c3: 
        # Eğer session'da index yoksa varsayılan (0) ata
        if "target_lang_index" not in st.session_state: st.session_state.target_lang_index = 0
        
        target_lang = st.selectbox(
            "Hedef", 
            LANG_OPTIONS, 
            index=st.session_state.target_lang_index,
            label_visibility="collapsed",
            key="target_select"
        )

    # SWAP BUTONU (Basit Mantık: İngilizce <-> Türkçe arası geçiş)
    with c2:
        st.markdown('<div class="swap-btn">', unsafe_allow_html=True)
        if st.button("⇄"):
            # Basit bir geçiş mantığı: Eğer İngilizceyse Türkçeye, değilse İngilizceye
            curr = st.session_state.target_select
            if curr == "English":
                st.session_state.target_lang_index = 1 # Türkçe indexi
            else:
                st.session_state.target_lang_index = 0 # İngilizce indexi
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    col_in, col_out = st.columns(2)
    
    # SOL (GİRİŞ)
    with col_in:
        # DİKTE (SESLE YAZMA) ÖZELLİĞİ
        mic_col, txt_col = st.columns([1, 8])
        with mic_col:
            # Küçük Mikrofon
            audio_in = audio_recorder(text="", icon_size="2x", recording_color="#ef4444", neutral_color="#333", key="dictation")
        with txt_col:
            st.caption("👆 Yazmak yerine konuşun")
        
        # Eğer ses kaydı varsa, metne dök ve kutuya yaz
        if audio_in:
            with st.spinner("✍️ Yazılıyor..."):
                transcribed_text = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(audio_in)), model="whisper-large-v3").text
                st.session_state.input_val = transcribed_text
                st.rerun()

        # Metin Kutusu (Form)
        with st.form(key="trans_form"):
            input_text = st.text_area("Metin", value=st.session_state.input_val, height=250, placeholder="Yazın veya dikte edin...", label_visibility="collapsed")
            
            b1, b2 = st.columns([3, 2])
            with b1: submit_btn = st.form_submit_button("Çevir ➔", type="primary", use_container_width=True)
            with b2: tone = st.selectbox("Ton", ["Normal", "Resmi", "Samimi"], label_visibility="collapsed")
        
        if submit_btn and input_text:
            with st.spinner("..."):
                st.session_state.res_text = ai_engine(input_text, "translate", target_lang, tone, glossary_txt, idiom_mode)
                st.session_state.input_val = input_text

    # SAĞ (ÇIKTI)
    with col_out:
        # Hizalamayı korumak için boşluk
        st.write("") 
        st.write("")
        
        res = st.session_state.res_text
        st.markdown(f"""<div class="result-box">{res if res else '...'}</div>""", unsafe_allow_html=True)
        
        if res:
            st.write("")
            ca, cb, cc = st.columns([2, 2, 2])
            with ca:
                aud = create_audio(res, target_lang, speech_slow)
                if aud: st.audio(aud, format="audio/mp3")
            with cb:
                st.markdown('<div class="save-btn">', unsafe_allow_html=True)
                if st.button("⭐ Kaydet"):
                    st.session_state.saved_vocab.append({"src": input_text[:30], "trg": res[:30]})
                    st.toast("Kaydedildi!")
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
            a1 = audio_recorder(text="", icon_size="3x", key="v1", recording_color="#3b82f6")
            if a1:
                txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(a1)), model="whisper-large-v3").text
                res = ai_engine(txt, "translate", target_lang, glossary=glossary_txt)
                st.success(f"{txt} \n\n👉 {res}")
                aud = create_audio(res, target_lang, speech_slow)
                if aud: st.audio(aud, format="audio/mp3", autoplay=True)
        with c2:
            st.warning(f"MİSAFİR ({target_lang})")
            a2 = audio_recorder(text="", icon_size="3x", key="v2", recording_color="#ec4899")
            if a2:
                txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(a2)), model="whisper-large-v3").text
                res = ai_engine(txt, "translate", "Türkçe", glossary=glossary_txt)
                st.info(f"{txt} \n\n👉 {res}")
                aud = create_audio(res, "Türkçe", speech_slow)
                if aud: st.audio(aud, format="audio/mp3", autoplay=True)

    else: # Konferans
        c1, c2 = st.columns([1, 3])
        with c1:
            audio_conf = audio_recorder(text="BAŞLAT / DURDUR", icon_size="2x", recording_color="#dc2626", pause_threshold=20.0)
        with c2:
            if audio_conf:
                with st.spinner("Analiz..."):
                    txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(audio_conf)), model="whisper-large-v3").text
                    trans = ai_engine(txt, "translate", target_lang, glossary=glossary_txt)
                    st.success(f"Orijinal: {txt}")
                    st.info(f"Çeviri: {trans}")
                    st.download_button("İndir", f"{txt}\n{trans}", "toplanti.txt")

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
                else: st.error("Hata.")

# --- 4. WEB ---
with tab_web:
    url = st.text_input("URL")
    if st.button("Analiz") and url:
        with st.spinner("..."):
            txt = local_read_web(url)
            if txt:
                res = ai_engine(txt, "summarize", target_lang)
                st.markdown(f"<div class='result-box'>{res}</div>", unsafe_allow_html=True)
            else: st.error("Hata.")

st.divider()
