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
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS TASARIM (PERFORMANS & SADELİK) ---
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; font-family: 'Inter', sans-serif; }
    
    /* Başlık */
    .header-logo { 
        font-size: 2rem; font-weight: 800; color: #0f172a; 
        text-align: center; letter-spacing: -0.5px; margin-top: -20px;
    }
    
    /* Metin Alanı */
    .stTextArea textarea {
        border: 1px solid #cbd5e1; border-radius: 12px;
        font-size: 1.1rem; height: 250px !important; padding: 15px;
        background: white; resize: none; box-shadow: 0 2px 4px rgba(0,0,0,0.01);
    }
    .stTextArea textarea:focus { border-color: #6366f1; box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15); }
    
    /* Sonuç Kutusu */
    .result-box {
        background-color: white; border: 1px solid #cbd5e1; border-radius: 12px;
        min-height: 250px; padding: 20px; font-size: 1.1rem; color: #334155;
        white-space: pre-wrap; box-shadow: 0 2px 4px rgba(0,0,0,0.01); position: relative;
    }
    
    /* Model Etiketi (Sağ Üst) */
    .model-badge {
        position: absolute; top: 10px; right: 10px;
        background: #f1f5f9; color: #64748b; padding: 4px 8px;
        border-radius: 4px; font-size: 0.7rem; font-weight: 600; border: 1px solid #e2e8f0;
    }
    
    /* Butonlar */
    div.stButton > button {
        background-color: #0f172a; color: white; border: none; border-radius: 8px;
        padding: 12px; font-weight: 600; width: 100%; transition: all 0.2s;
    }
    div.stButton > button:hover { background-color: #334155; transform: translateY(-1px); }
    
    /* Geçmiş Öğeleri */
    .history-item {
        padding: 8px; margin-bottom: 6px; background: white; border-radius: 6px;
        font-size: 0.8rem; border-left: 3px solid #6366f1; color: #475569;
        border: 1px solid #f1f5f9;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. API BAĞLANTISI ---
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("⚠️ API Key Eksik! Secrets ayarlarını kontrol edin.")
    st.stop()

# --- 4. STATE YÖNETİMİ ---
if "history" not in st.session_state: st.session_state.history = []
if "res_text" not in st.session_state: st.session_state.res_text = ""
if "input_val" not in st.session_state: st.session_state.input_val = ""
if "stats_trans" not in st.session_state: st.session_state.stats_trans = 0

# --- 5. MOTOR (MODEL SEÇİMLİ) ---
def ai_engine(text, task, target_lang="English", tone="Normal", glossary="", model_id="llama-3.3-70b-versatile"):
    if not text: return ""
    
    st.session_state.stats_trans += 1
    glossary_prompt = f"TERMİNOLOJİ: \n{glossary}" if glossary else ""

    if task == "translate":
        sys_msg = f"""
        Sen uzman tercümansın. Hedef: {target_lang}. Ton: {tone}.
        {glossary_prompt}
        GÖREV: Kaynak dili algıla ve çevir. Sadece çeviriyi ver.
        """
    elif task == "improve":
        sys_msg = "Editörsün. Metni düzelt. Format: [DİL] ||| METİN"
    elif task == "summarize":
        sys_msg = f"Analistsin. Metni {target_lang} dilinde özetle."

    try:
        res = client.chat.completions.create(
            model=model_id, # Dinamik model seçimi
            messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": text[:20000]}]
        )
        return res.choices[0].message.content
    except Exception as e: return f"Hata: {str(e)}"

def create_audio(text, lang_name, speed=False):
    code_map = {"Türkçe": "tr", "İngilizce": "en", "Almanca": "de", "Fransızca": "fr", "İspanyolca": "es", "Rusça": "ru", "Arapça": "ar", "Çince": "zh"}
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

def local_read_web(url):
    try:
        h = {'User-Agent': 'Mozilla/5.0'}
        soup = BeautifulSoup(requests.get(url, headers=h, timeout=10).content, 'html.parser')
        return " ".join([p.get_text() for p in soup.find_all(['p', 'h1', 'h2'])])[:15000]
    except: return None

# ==========================================
# ARAYÜZ
# ==========================================

# --- YAN MENÜ ---
with st.sidebar:
    st.markdown("### 🚀 Motor Ayarı")
    
    # MODEL SEÇİCİ (HIZ VS ZEKA)
    model_choice = st.radio(
        "AI Gücü:",
        ["⚡ Flash (Hızlı)", "🧠 Pro (Zeki)"],
        captions=["Llama 3.1 8b - Anlık", "Llama 3.3 70b - Detaylı"]
    )
    model_id = "llama-3.1-8b-instant" if "Flash" in model_choice else "llama-3.3-70b-versatile"
    active_badge = "Flash ⚡" if "Flash" in model_choice else "Pro 🧠"

    st.divider()
    st.markdown(f"**Toplam Çeviri:** {st.session_state.stats_trans}")
    speech_slow = st.checkbox("🐢 Yavaş Okuma", value=False)
    
    with st.expander("📚 Sözlük"):
        glossary_txt = st.text_area("Örn: AI=Yapay Zeka", height=80)

    st.divider()
    st.markdown("### 🕒 Geçmiş")
    if st.session_state.history:
        for item in st.session_state.history[:6]:
            st.markdown(f"<div class='history-item'>{item['src']}</div>", unsafe_allow_html=True)
        if st.button("Temizle", type="secondary"): st.session_state.history = []; st.rerun()

# --- BAŞLIK ---
st.markdown('<div class="header-logo">LinguaFlow Pro</div>', unsafe_allow_html=True)

# --- SEKMELER ---
tab_text, tab_voice, tab_files, tab_web = st.tabs(["📝 Metin & Yazım", "🎙️ Ses & Toplantı", "📂 Dosya & Belge", "🔗 Web Analiz"])
LANG_OPTIONS = ["English", "Türkçe", "Deutsch", "Français", "Español", "Italiano", "Русский", "العربية", "中文"]

# --- 1. METİN (FORM YAPISI) ---
with tab_text:
    c1, c2, c3 = st.columns([3, 1, 3])
    with c1: st.markdown("**Giriş**")
    with c3: target_lang = st.selectbox("Hedef", LANG_OPTIONS, label_visibility="collapsed")

    col_in, col_out = st.columns(2)
    
    # SOL (GİRİŞ)
    with col_in:
        # FORM BAŞLANGICI (Ctrl+Enter için)
        with st.form(key="trans_form"):
            input_text = st.text_area("Metin", value=st.session_state.input_val, height=250, placeholder="Yazın...", label_visibility="collapsed")
            
            b1, b2 = st.columns([3, 1])
            with b1:
                submit_btn = st.form_submit_button("Çevir ➔", type="primary", use_container_width=True)
            with b2:
                tone = st.selectbox("Ton", ["Normal", "Resmi", "Samimi"], label_visibility="collapsed")
        
        # Düzeltme butonu form dışında (Opsiyonel)
        if st.button("✨ Metni Düzelt (Write Mode)"):
            if input_text:
                with st.spinner("..."):
                    st.session_state.res_text = ai_engine(input_text, "improve", model_id=model_id)
                    st.session_state.input_val = input_text

        if submit_btn and input_text:
            with st.spinner("..."):
                st.session_state.res_text = ai_engine(input_text, "translate", target_lang, tone, glossary_txt, model_id)
                st.session_state.input_val = input_text
                # Geçmiş
                ts = datetime.datetime.now().strftime("%H:%M")
                st.session_state.history.insert(0, {"time": ts, "src": input_text[:20]+"..", "res": st.session_state.res_text})

    # SAĞ (ÇIKTI)
    with col_out:
        res = st.session_state.res_text
        
        st.markdown(f"""
        <div class="result-box">
            <span class="model-badge">{active_badge}</span>
            {res if res else '...'}
        </div>
        """, unsafe_allow_html=True)
        
        if res:
            st.write("")
            ca, cb, cc = st.columns([1, 3, 1])
            with ca:
                aud = create_audio(res, target_lang, speech_slow)
                if aud: st.audio(aud, format="audio/mp3")
            with cb: render_share(res)
            with cc:
                if st.button("🔄 Al"): # Swap
                    st.session_state.input_val = res
                    st.session_state.res_text = ""
                    st.rerun()

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
                lang, res = ai_engine(txt, "translate", target_lang, glossary=glossary_txt, model_id=model_id).split("|||")[-1], ai_engine(txt, "translate", target_lang, glossary=glossary_txt, model_id=model_id)
                aud = create_audio(res, target_lang, speech_slow)
                st.markdown(f"<div class='result-box' style='min-height:100px; border-left:4px solid #3b82f6'>{txt}<br><br><b>{res}</b></div>", unsafe_allow_html=True)
                if aud: st.audio(aud, format="audio/mp3", autoplay=True)
        with c2:
            st.warning(f"MİSAFİR ({target_lang})")
            a2 = audio_recorder(text="", icon_size="3x", key="v2", recording_color="#ec4899", neutral_color="#fce7f3")
            if a2:
                txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(a2)), model="whisper-large-v3").text
                res = ai_engine(txt, "translate", "Türkçe", glossary=glossary_txt, model_id=model_id)
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
                        trans = ai_engine(txt, "translate", target_lang, glossary=glossary_txt, model_id=model_id)
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
                    res = ai_engine(raw, mode, target_lang, glossary=glossary_txt, model_id=model_id)
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
                res = ai_engine(txt, "summarize", target_lang, model_id=model_id)
                st.markdown(f"<div class='result-box'>{res}</div>", unsafe_allow_html=True)
                st.download_button("İndir", res, "web.txt")
            else: st.error("Hata.")

st.divider()
