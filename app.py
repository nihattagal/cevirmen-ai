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
    page_title="LinguaFlow Ultimate",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. STATE YÖNETİMİ (HATAYI ÇÖZEN KISIM BURASI) ---
# Tüm hafıza değişkenlerini en başta tanımlıyoruz ki 'bulunamadı' hatası vermesin.
if "theme" not in st.session_state: st.session_state.theme = "Light"
if "history" not in st.session_state: st.session_state.history = []
if "res_text" not in st.session_state: st.session_state.res_text = ""
if "input_val" not in st.session_state: st.session_state.input_val = ""
if "detected_lang" not in st.session_state: st.session_state.detected_lang = "" # <-- EKSİK OLAN BUYDU
if "stats_trans" not in st.session_state: st.session_state.stats_trans = 0
if "target_lang_idx" not in st.session_state: st.session_state.target_lang_idx = 0

# --- 3. DINAMIK CSS ---
def get_css(theme):
    if theme == "Dark":
        bg_color = "#0e1117"
        txt_color = "#fafafa"
        box_bg = "#262730"
        border_color = "#4a4a4a"
        btn_bg = "#4f46e5"
        btn_hover = "#4338ca"
    else:
        bg_color = "#f8fafc"
        txt_color = "#0f172a"
        box_bg = "#ffffff"
        border_color = "#e2e8f0"
        btn_bg = "#0f172a"
        btn_hover = "#334155"

    return f"""
    <style>
    .stApp {{ background-color: {bg_color}; color: {txt_color}; font-family: 'Inter', sans-serif; }}
    
    .header-logo {{ 
        font-size: 2.2rem; font-weight: 800; color: {txt_color}; 
        text-align: center; margin-top: -20px; letter-spacing: -1px;
    }}
    
    .stTextArea textarea {{
        border: 1px solid {border_color}; border-radius: 12px;
        font-size: 1.1rem; height: 250px !important; padding: 15px;
        background: {box_bg}; color: {txt_color}; resize: none;
    }}
    
    .result-box {{
        background-color: {box_bg}; border: 1px solid {border_color}; border-radius: 12px;
        min-height: 250px; padding: 20px; font-size: 1.1rem; color: {txt_color};
        white-space: pre-wrap; box-shadow: 0 2px 4px rgba(0,0,0,0.05); position: relative;
    }}
    
    div.stButton > button {{
        background-color: {btn_bg}; color: white; border: none; border-radius: 8px;
        padding: 10px; font-weight: 600; width: 100%; transition: all 0.2s;
    }}
    div.stButton > button:hover {{ background-color: {btn_hover}; transform: translateY(-1px); }}
    
    .secondary-btn div.stButton > button {{ background-color: #64748b; }}
    
    .history-item {{
        padding: 10px; margin-bottom: 8px; background: {box_bg}; border-radius: 8px;
        font-size: 0.85rem; border-left: 4px solid #6366f1; color: {txt_color};
        border: 1px solid {border_color};
    }}
    </style>
    """

st.markdown(get_css(st.session_state.theme), unsafe_allow_html=True)

# --- 4. API ---
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("⚠️ API Key Eksik!")
    st.stop()

# --- 5. MOTOR ---
def ai_engine(text, task, target_lang="English", tone="Normal", glossary="", idiom_active=False):
    if not text: return "", ""
    
    st.session_state.stats_trans += 1
    
    glossary_prompt = f"TERMİNOLOJİ: \n{glossary}" if glossary else ""
    idiom_prompt = "Deyim varsa açıkla." if idiom_active else ""

    if task == "translate":
        sys_msg = f"""
        Sen uzman tercümansın. Hedef: {target_lang}. Ton: {tone}.
        {glossary_prompt} {idiom_prompt}
        GÖREV: Kaynak dili algıla ve çevir.
        ÇIKTI: [ALGILANAN_DİL] ||| METİN
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
            return lang_tag.strip().replace("[", "").replace("]", ""), content.strip()
        else:
            return "Otomatik", full_res

    except Exception as e: return "Hata", str(e)

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

def local_read_web(url):
    try:
        h = {'User-Agent': 'Mozilla/5.0'}
        soup = BeautifulSoup(requests.get(url, headers=h, timeout=10).content, 'html.parser')
        return " ".join([p.get_text() for p in soup.find_all(['p', 'h1', 'h2'])])[:10000]
    except: return None

# ==========================================
# ARAYÜZ
# ==========================================

# --- YAN MENÜ ---
with st.sidebar:
    st.title("LinguaFlow")
    
    sb_tab1, sb_tab2 = st.tabs(["⚙️ Ayarlar", "🕒 Geçmiş"])
    
    with sb_tab1:
        st.subheader("Görünüm")
        theme_sel = st.radio("Tema", ["Light", "Dark"], horizontal=True)
        if theme_sel != st.session_state.theme:
            st.session_state.theme = theme_sel
            st.rerun()
            
        st.divider()
        idiom_mode = st.checkbox("🧐 Deyim Modu", value=False)
        speech_slow = st.checkbox("🐢 Yavaş Okuma", value=False)
        glossary_txt = st.text_area("Özel Terimler (Sözlük)", placeholder="Örn: AI=Yapay Zeka", height=60)

    with sb_tab2:
        if st.session_state.history:
            for item in st.session_state.history[:8]:
                st.markdown(f"<div class='history-item'><small>{item['time']}</small><br>{item['src']}</div>", unsafe_allow_html=True)
            if st.button("Temizle"):
                st.session_state.history = []
                st.rerun()
        else:
            st.info("Geçmiş boş.")

# --- BAŞLIK ---
st.markdown('<div class="header-logo">LinguaFlow Pro</div>', unsafe_allow_html=True)

# --- SEKMELER ---
tab_text, tab_voice, tab_files, tab_web = st.tabs(["📝 Metin & Dikte", "🎙️ Sesli Sohbet", "📂 Dosya", "🔗 Web"])
LANG_OPTIONS = ["English", "Türkçe", "Deutsch", "Français", "Español", "Italiano", "Русский", "العربية", "中文"]

# --- 1. METİN ---
with tab_text:
    c1, c2, c3, c4 = st.columns([3, 1, 3, 1])
    with c1: st.markdown("**Giriş (Otomatik)**")
    with c3: 
        if "target_lang_idx" not in st.session_state: st.session_state.target_lang_idx = 0
        target_lang = st.selectbox("Hedef", LANG_OPTIONS, index=st.session_state.target_lang_idx, label_visibility="collapsed")
    
    with c2:
        st.markdown('<div class="secondary-btn">', unsafe_allow_html=True)
        if st.button("⇄"):
             st.session_state.target_lang_idx = 1 if st.session_state.target_lang_idx == 0 else 0
             st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    col_in, col_out = st.columns(2)
    
    with col_in:
        mc, tc = st.columns([1, 8])
        with mc: audio_in = audio_recorder(text="", icon_size="2x", recording_color="#ef4444", neutral_color="#333", key="dict")
        with tc: st.caption("Konuşarak yaz")
        
        if audio_in:
            with st.spinner("✍️..."):
                txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(audio_in)), model="whisper-large-v3").text
                st.session_state.input_val = txt
                st.rerun()

        with st.form(key="t_form"):
            input_text = st.text_area("Metin", value=st.session_state.input_val, height=250, label_visibility="collapsed")
            c_b1, c_b2 = st.columns([3, 2])
            with c_b1: submit = st.form_submit_button("Çevir ➔", type="primary", use_container_width=True)
            with c_b2: tone = st.selectbox("Ton", ["Normal", "Resmi", "Samimi"], label_visibility="collapsed")
        
        if submit and input_text:
            with st.spinner("..."):
                lang, txt = ai_engine(input_text, "translate", target_lang, tone, glossary_txt, idiom_mode)
                st.session_state.res_text = txt
                st.session_state.detected_lang = lang
                st.session_state.input_val = input_text
                ts = datetime.datetime.now().strftime("%H:%M")
                st.session_state.history.insert(0, {"time": ts, "src": input_text[:20]+".."})

    with col_out:
        st.write("") 
        st.write("")
        res = st.session_state.res_text
        d_lang = st.session_state.detected_lang
        
        st.markdown(f"""
        <div class="result-box">
            {f'<span style="color:#888; font-size:0.8rem;">[{d_lang}]</span>' if d_lang else ''}
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
                st.markdown('<div class="secondary-btn">', unsafe_allow_html=True)
                if st.button("🗑️ Temizle"):
                    st.session_state.input_val = ""
                    st.session_state.res_text = ""
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
            a1 = audio_recorder(text="", icon_size="3x", key="v1", recording_color="#3b82f6")
            if a1:
                txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(a1)), model="whisper-large-v3").text
                lang, res = ai_engine(txt, "translate", target_lang, glossary=glossary_txt, idiom_active=idiom_mode)
                st.success(f"{txt} -> {res}")
                aud = create_audio(res, target_lang, speech_slow)
                if aud: st.audio(aud, format="audio/mp3", autoplay=True)
        with c2:
            st.warning(f"MİSAFİR ({target_lang})")
            a2 = audio_recorder(text="", icon_size="3x", key="v2", recording_color="#ec4899")
            if a2:
                txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(a2)), model="whisper-large-v3").text
                lang, res = ai_engine(txt, "translate", "Türkçe", glossary=glossary_txt, idiom_active=idiom_mode)
                st.info(f"{txt} -> {res}")
                aud = create_audio(res, "Türkçe", speech_slow)
                if aud: st.audio(aud, format="audio/mp3", autoplay=True)

    else: # Konferans
        c1, c2 = st.columns([1, 3])
        with c1:
            ac = audio_recorder(text="BAŞLAT / DURDUR", icon_size="2x", recording_color="#dc2626", pause_threshold=20.0)
        with c2:
            if ac:
                with st.spinner("Analiz..."):
                    txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(ac)), model="whisper-large-v3").text
                    lang, trans = ai_engine(txt, "translate", target_lang, glossary=glossary_txt)
                    st.success(f"Orijinal: {txt}")
                    st.info(f"Çeviri: {trans}")
                    st.download_button("İndir", f"{txt}\n{trans}", "kayit.txt")

# --- 3. DOSYA ---
with tab_files:
    u_file = st.file_uploader("Dosya", type=['pdf', 'mp3', 'wav', 'm4a'])
    if u_file:
        if st.button("İşle"):
            with st.spinner("..."):
                raw = local_read_file(u_file)
                if raw:
                    mode = "translate" if len(raw) < 3000 else "summarize"
                    lang, res = ai_engine(raw, mode, target_lang, glossary=glossary_txt)
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
                lang, res = ai_engine(txt, "summarize", target_lang)
                st.markdown(f"<div class='result-box'>{res}</div>", unsafe_allow_html=True)
                st.download_button("İndir", res, "web.txt")
            else: st.error("Hata.")

st.divider()
