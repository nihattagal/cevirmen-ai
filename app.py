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

# --- 1. GENEL AYARLAR ---
st.set_page_config(
    page_title="LinguaFlow Ultimate",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. STATE YÖNETİMİ ---
if "theme" not in st.session_state: st.session_state.theme = "Light"
if "history" not in st.session_state: st.session_state.history = []
if "chat_messages" not in st.session_state: st.session_state.chat_messages = []
if "rp_history" not in st.session_state: st.session_state.rp_history = []
if "rp_scenario" not in st.session_state: st.session_state.rp_scenario = ""
if "res_text" not in st.session_state: st.session_state.res_text = ""
if "diff_html" not in st.session_state: st.session_state.diff_html = ""
if "input_val" not in st.session_state: st.session_state.input_val = ""
if "keywords" not in st.session_state: st.session_state.keywords = ""

# --- 3. DINAMIK CSS (DÜZELTİLMİŞ) ---
def get_css(theme):
    if theme == "Dark":
        bg_col = "#0e1117"
        txt_col = "#e0e0e0"
        box_bg = "#262730"
        border = "#444"
        primary = "#4f46e5"
        user_bubble = "#1e3a8a"
        ai_bubble = "#374151"
    else:
        bg_col = "#f8fafc"
        txt_col = "#1e293b"
        box_bg = "#ffffff"
        border = "#e2e8f0"
        primary = "#0f172a"
        user_bubble = "#dbeafe"
        ai_bubble = "#f1f5f9"

    # NOT: CSS blokları için çift {{ }} kullanıldı, Python değişkenleri için tek { } kullanıldı.
    return f"""
    <style>
    .stApp {{ background-color: {bg_col}; color: {txt_col}; font-family: 'Inter', sans-serif; }}
    
    /* Başlık */
    .header-logo {{ 
        font-size: 2.2rem; font-weight: 800; color: {txt_color}; 
        text-align: center; margin-top: -20px; letter-spacing: -0.5px;
    }}
    
    /* Metin Alanları */
    .stTextArea textarea {{
        background-color: {box_bg}; color: {txt_col};
        border: 1px solid {border}; border-radius: 10px;
        font-size: 1.1rem; height: 250px !important; padding: 15px; resize: none;
    }}
    .stTextArea textarea:focus {{ border-color: #6366f1; }}
    
    /* Sonuç Kutusu */
    .result-box {{
        background-color: {box_bg}; color: {txt_col};
        border: 1px solid {border}; border-radius: 10px;
        min-height: 250px; padding: 20px; font-size: 1.1rem;
        white-space: pre-wrap; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }}
    
    /* Diff Kutusu */
    .diff-box {{
        background-color: {box_bg}; border: 1px solid {border}; border-radius: 10px;
        padding: 20px; font-family: monospace; font-size: 1rem; color: {txt_col};
    }}
    .diff-del {{ background-color: #fca5a5; color: #7f1d1d; text-decoration: line-through; padding: 0 4px; border-radius: 4px; }}
    .diff-add {{ background-color: #86efac; color: #14532d; padding: 0 4px; border-radius: 4px; font-weight: bold; }}

    /* Butonlar */
    div.stButton > button {{
        background-color: {primary}; color: white; border: none; border-radius: 8px;
        padding: 12px; font-weight: 600; width: 100%; transition: all 0.2s;
    }}
    div.stButton > button:hover {{ opacity: 0.9; transform: translateY(-1px); }}
    
    /* Sohbet Balonları */
    .chat-me {{ background: {user_bubble}; border-left: 4px solid #3b82f6; padding: 10px; border-radius: 10px; margin-bottom: 8px; text-align: right; margin-left: 20%; color: {txt_col}; }}
    .chat-you {{ background: {ai_bubble}; border-right: 4px solid #ec4899; padding: 10px; border-radius: 10px; margin-bottom: 8px; text-align: left; margin-right: 20%; color: {txt_col}; }}
    
    /* Roleplay */
    .rp-ai {{ background: {ai_bubble}; padding: 15px; border-radius: 15px 15px 15px 0; margin-bottom: 10px; border-left: 4px solid #64748b; color: {txt_col}; }}
    .rp-user {{ background: {user_bubble}; padding: 15px; border-radius: 15px 15px 0 15px; margin-bottom: 10px; text-align: right; border-right: 4px solid #6366f1; color: {txt_col}; }}
    
    /* Geçmiş */
    .history-item {{
        padding: 8px; margin-bottom: 5px; background: {box_bg}; border-radius: 5px;
        font-size: 0.85rem; border-left: 3px solid #6366f1; color: {txt_col};
        border: 1px solid {border};
    }}
    </style>
    """

st.markdown(get_css(st.session_state.theme), unsafe_allow_html=True)

# --- 4. API ---
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("⚠️ API Key Eksik! Secrets ayarlarını kontrol edin.")
    st.stop()

# --- 5. MOTOR ---
def ai_engine(text, task, target_lang="English", tone="Normal", glossary="", extra_ctx="", format_style="Normal Metin"):
    if not text: return ""
    
    glossary_prompt = f"TERMİNOLOJİ: \n{glossary}" if glossary else ""

    if task == "translate":
        sys_msg = f"""
        Sen uzman tercümansın. Hedef: {target_lang}. Ton: {tone}. Çıktı Formatı: {format_style}.
        {glossary_prompt}
        GÖREV: 
        1. Çeviriyi yap.
        2. Metindeki en önemli 3 anahtar kelimeyi bul.
        FORMAT: [ÇEVİRİ] ||| [ANAHTAR_KELİMELER]
        """
    elif task == "improve":
        sys_msg = "Editörsün. Metni düzelt. Sadece düzeltilmiş metni ver."
    elif task == "summarize":
        sys_msg = f"Analistsin. Metni {target_lang} dilinde özetle. Format: {format_style}."
    elif task == "roleplay":
        sys_msg = f"Sen bir dil eğitmenisin. Senaryo: {extra_ctx}. Rol yap, cevap ver ve parantez içinde hataları düzelt. Dil: {target_lang}."

    try:
        msgs = [{"role": "system", "content": sys_msg}]
        if task == "roleplay":
            for msg in st.session_state.rp_history[-6:]: msgs.append(msg)
        
        msgs.append({"role": "user", "content": text[:15000]})

        res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=msgs)
        full_res = res.choices[0].message.content
        
        if task == "translate" and "|||" in full_res:
            parts = full_res.split("|||")
            st.session_state.keywords = parts[1].strip()
            return parts[0].strip()
        else:
            return full_res

    except Exception as e: return f"Hata: {e}"

def generate_diff(original, corrected):
    d = difflib.Differ()
    diff = list(d.compare(original.split(), corrected.split()))
    html = []
    for token in diff:
        if token.startswith("- "): html.append(f"<span class='diff-del'>{token[2:]}</span>")
        elif token.startswith("+ "): html.append(f"<span class='diff-add'>{token[2:]}</span>")
        elif token.startswith("  "): html.append(token[2:])
    return " ".join(html)

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
    
    sb1, sb2 = st.tabs(["Ayarlar", "Geçmiş"])
    
    with sb1:
        st.markdown("### 🎨 Görünüm")
        theme_mode = st.radio("Tema", ["Light", "Dark"], horizontal=True, label_visibility="collapsed")
        if theme_mode != st.session_state.theme:
            st.session_state.theme = theme_mode
            st.rerun()

        st.divider()
        st.markdown("### ⚙️ Tercihler")
        speed_opt = st.select_slider("Ses Hızı", options=["Yavaş", "Normal"], value="Normal")
        is_slow = True if speed_opt == "Yavaş" else False
        
        with st.expander("📚 Sözlük"):
            glossary_txt = st.text_area("Örn: AI=Yapay Zeka", height=70)

    with sb2:
        if st.session_state.history:
            for item in st.session_state.history[:5]:
                st.markdown(f"<div class='history-item'>{item['src']}</div>", unsafe_allow_html=True)
            if st.button("Temizle"): 
                st.session_state.history = []
                st.rerun()
        else:
            st.info("Geçmiş boş")

st.markdown('<div class="header-logo">LinguaFlow</div>', unsafe_allow_html=True)

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
        input_text = st.text_area("Metin", value=st.session_state.input_val, height=250, placeholder="Yazın...", label_visibility="collapsed")
        
        b1, b2, b3 = st.columns([3, 3, 3])
        with b1:
            if st.button("Çevir ➔"):
                if input_text:
                    with st.spinner("..."):
                        st.session_state.res_text = ai_engine(input_text, "translate", target_lang, "Normal", glossary_txt)
                        st.session_state.diff_html = ""
                        st.session_state.input_val = input_text
                        # Geçmiş
                        ts = datetime.datetime.now().strftime("%H:%M")
                        st.session_state.history.insert(0, {"time": ts, "src": input_text[:20]+".."})
        with b2:
            if st.button("✨ Düzelt"):
                if input_text:
                    with st.spinner("..."):
                        corrected = ai_engine(input_text, "improve")
                        st.session_state.diff_html = generate_diff(input_text, corrected)
                        st.session_state.res_text = corrected
        with b3: tone = st.selectbox("Ton", ["Normal", "Resmi", "Samimi"], label_visibility="collapsed")

    with col_out:
        if st.session_state.diff_html:
            st.markdown(f"<div class='diff-box'>{st.session_state.diff_html}</div>", unsafe_allow_html=True)
            st.caption("🔴 Silinen  🟢 Eklenen")
        else:
            res = st.session_state.res_text
            st.markdown(f"""<div class="result-box">{res if res else '...'}</div>""", unsafe_allow_html=True)
            
            # Anahtar Kelimeler
            if st.session_state.keywords:
                st.info(f"🔑 **Anahtar Kelimeler:** {st.session_state.keywords}")
            
            if res:
                st.write("")
                ca, cb, cc = st.columns([2, 2, 2])
                with ca:
                    aud = create_audio(res, target_lang, is_slow)
                    if aud: st.audio(aud, format="audio/mp3")
                with cb:
                    if st.button("🗑️ Temizle"):
                        st.session_state.input_val = ""
                        st.session_state.res_text = ""
                        st.session_state.keywords = ""
                        st.rerun()
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
                res = ai_engine(txt, "translate", target_lang, glossary=glossary_txt)
                st.markdown(f"<div class='chat-me'>{txt}<br><b>{res}</b></div>", unsafe_allow_html=True)
                aud = create_audio(res, target_lang, is_slow)
                if aud: st.audio(aud, format="audio/mp3", autoplay=True)
        with c2:
            st.warning(f"MİSAFİR ({target_lang})")
            a2 = audio_recorder(text="", icon_size="3x", key="v2", recording_color="#ec4899", neutral_color="#fce7f3")
            if a2:
                txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(a2)), model="whisper-large-v3").text
                res = ai_engine(txt, "translate", "Türkçe", glossary=glossary_txt)
                st.markdown(f"<div class='chat-you'>{txt}<br><b>{res}</b></div>", unsafe_allow_html=True)
                aud = create_audio(res, "Türkçe", is_slow)
                if aud: st.audio(aud, format="audio/mp3", autoplay=True)

    else: # Konferans
        c1, c2 = st.columns([1, 3])
        with c1:
            st.write("Sürekli Dinleme")
            ac = audio_recorder(text="BAŞLAT / DURDUR", icon_size="2x", recording_color="#dc2626", pause_threshold=20.0)
        with c2:
            if ac:
                with st.spinner("Analiz..."):
                    txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(ac)), model="whisper-large-v3").text
                    trans = ai_engine(txt, "translate", target_lang, glossary=glossary_txt)
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
                st.download_button("İndir", res, "web.txt")
            else: st.error("Hata.")

st.divider()
