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
from fpdf import FPDF

# --- 1. GENEL AYARLAR ---
st.set_page_config(
    page_title="LinguaFlow Suite",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS TASARIM (PROFESYONEL) ---
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; font-family: 'Inter', sans-serif; }
    
    /* Başlık */
    .header-logo { 
        font-size: 2rem; font-weight: 800; color: #0f172a; 
        text-align: center; margin-top: -20px; letter-spacing: -0.5px;
    }
    
    /* Metin Alanı */
    .stTextArea textarea {
        border: 1px solid #cbd5e1; border-radius: 10px;
        font-size: 1.1rem; height: 250px !important; padding: 15px;
        background: white; resize: none;
    }
    .stTextArea textarea:focus { border-color: #4f46e5; box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.2); }
    
    /* Sonuç Kutusu */
    .result-box {
        background-color: white; border: 1px solid #cbd5e1; border-radius: 10px;
        min-height: 250px; padding: 20px; font-size: 1.1rem; color: #334155;
        white-space: pre-wrap; box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    
    /* Sohbet Balonları (Dual Chat) */
    .chat-me { background: #dbeafe; border-left: 4px solid #3b82f6; padding: 10px; border-radius: 10px; margin-bottom: 8px; text-align: right; margin-left: 20%; }
    .chat-you { background: #fce7f3; border-right: 4px solid #ec4899; padding: 10px; border-radius: 10px; margin-bottom: 8px; text-align: left; margin-right: 20%; }
    
    /* Roleplay Balonları */
    .rp-ai { background: #f1f5f9; padding: 15px; border-radius: 15px; margin-bottom: 10px; border-left: 4px solid #475569; }
    .rp-user { background: #e0e7ff; padding: 15px; border-radius: 15px; margin-bottom: 10px; text-align: right; border-right: 4px solid #4f46e5; }

    /* Butonlar */
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
if "chat_messages" not in st.session_state: st.session_state.chat_messages = [] # Sohbet için
if "rp_history" not in st.session_state: st.session_state.rp_history = [] # Roleplay için
if "rp_scenario" not in st.session_state: st.session_state.rp_scenario = ""
if "res_text" not in st.session_state: st.session_state.res_text = ""
if "input_val" not in st.session_state: st.session_state.input_val = ""
if "keywords" not in st.session_state: st.session_state.keywords = ""

# --- 5. MOTOR ---
def ai_engine(text, task, target_lang="English", tone="Normal", glossary="", extra_ctx=""):
    if not text: return ""
    
    glossary_prompt = f"TERMİNOLOJİ: \n{glossary}" if glossary else ""

    if task == "translate":
        sys_msg = f"""
        Sen uzman tercümansın. Hedef: {target_lang}. Ton: {tone}. {glossary_prompt}.
        GÖREV: 
        1. Çeviriyi yap.
        2. Metindeki en önemli 3 anahtar kelimeyi bul.
        FORMAT: [ÇEVİRİ] ||| [ANAHTAR_KELİMELER]
        """
    elif task == "improve":
        sys_msg = "Editörsün. Metni düzelt. Sadece düzeltilmiş metni ver."
    elif task == "summarize":
        sys_msg = f"Analistsin. Metni {target_lang} dilinde özetle."
    elif task == "roleplay":
        sys_msg = f"Sen bir dil eğitmenisin. Senaryo: {extra_ctx}. Rol yap, cevap ver ve parantez içinde hataları düzelt. Dil: {target_lang}."

    try:
        msgs = [{"role": "system", "content": sys_msg}]
        if task == "roleplay":
            for msg in st.session_state.rp_history[-6:]: msgs.append(msg)
        
        msgs.append({"role": "user", "content": text[:15000]})

        res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=msgs)
        full_res = res.choices[0].message.content
        
        # Metin modunda anahtar kelimeleri ayır
        if task == "translate" and "|||" in full_res:
            parts = full_res.split("|||")
            st.session_state.keywords = parts[1].strip()
            return parts[0].strip()
        else:
            return full_res

    except Exception as e: return f"Hata: {e}"

def create_pdf(title, content):
    """Güvenli PDF Oluşturucu"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    # Başlık temizle
    safe_title = title.encode('latin-1', 'ignore').decode('latin-1')
    pdf.cell(0, 10, safe_title, ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", '', 12)
    
    # İçerik temizle (Unicode karakterleri latin-1'e uyarla veya at)
    # Not: Gerçek prodüksiyonda Unicode font (DejaVuSans) kullanılır, bu basit çözümdür.
    replacements = {'ğ':'g', 'Ğ':'G', 'ü':'u', 'Ü':'U', 'ş':'s', 'Ş':'S', 'ı':'i', 'İ':'I', 'ö':'o', 'Ö':'O', 'ç':'c', 'Ç':'C'}
    safe_content = content
    for k, v in replacements.items(): safe_content = safe_content.replace(k, v)
    
    # Desteklenmeyen diğer karakterleri temizle
    safe_content = safe_content.encode('latin-1', 'replace').decode('latin-1')
    
    pdf.multi_cell(0, 10, safe_content)
    return pdf.output(dest='S').encode('latin-1')

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
    st.caption("Ultimate Suite v28.0")
    
    st.markdown("### ⚙️ Ayarlar")
    speed_opt = st.select_slider("Hız", options=["Yavaş", "Normal"], value="Normal")
    is_slow = True if speed_opt == "Yavaş" else False
    
    with st.expander("📚 Sözlük"):
        glossary_txt = st.text_area("Örn: AI=Yapay Zeka", height=70)

    st.divider()
    if st.button("Geçmişi Temizle"):
        st.session_state.history = []
        st.session_state.chat_messages = []
        st.rerun()

st.markdown('<div class="header-logo">LinguaFlow Suite</div>', unsafe_allow_html=True)

# 5 SEKME: Tüm Özellikler
tab_text, tab_voice, tab_roleplay, tab_files, tab_web = st.tabs(["📝 Metin", "🎙️ Ses Merkezi", "🎭 Rol Yapma", "📂 Dosya", "🔗 Web"])
LANG_OPTIONS = ["English", "Türkçe", "Deutsch", "Français", "Español", "Italiano", "Русский", "العربية", "中文"]

# --- 1. METİN ---
with tab_text:
    c1, c2, c3 = st.columns([3, 1, 3])
    with c1: st.markdown("**Giriş**")
    with c3: target_lang = st.selectbox("Hedef", LANG_OPTIONS, label_visibility="collapsed")

    col_in, col_out = st.columns(2)
    with col_in:
        input_text = st.text_area("Metin", value=st.session_state.input_val, height=250, placeholder="Yazın...", label_visibility="collapsed")
        if st.button("Çevir ➔"):
            if input_text:
                with st.spinner("..."):
                    st.session_state.res_text = ai_engine(input_text, "translate", target_lang, "Normal", glossary_txt)
                    st.session_state.input_val = input_text
                    ts = datetime.datetime.now().strftime("%H:%M")
                    st.session_state.history.insert(0, {"src": input_text, "trg": st.session_state.res_text})

    with col_out:
        res = st.session_state.res_text
        st.markdown(f"""<div class="result-box">{res if res else '...'}</div>""", unsafe_allow_html=True)
        
        # Anahtar Kelimeler (Varsa)
        if st.session_state.keywords:
            st.info(f"🔑 **Anahtar Kelimeler:** {st.session_state.keywords}")
        
        if res:
            st.write("")
            ca, cb = st.columns([1, 4])
            with ca:
                aud = create_audio(res, target_lang, is_slow)
                if aud: st.audio(aud, format="audio/mp3")
            with cb: st.code(res, language=None)

# --- 2. SES MERKEZİ (HİBRİT) ---
with tab_voice:
    v_mode = st.radio("Mod Seçin:", ["🗣️ Karşılıklı Sohbet (Turist)", "🎙️ Konferans (Toplantı)"], horizontal=True)
    st.divider()
    
    if "Sohbet" in v_mode:
        c1, c2 = st.columns(2)
        with c1:
            st.info("SİZ (Sol)")
            a1 = audio_recorder(text="", icon_size="3x", key="v1", recording_color="#3b82f6", neutral_color="#dbeafe")
            if a1:
                txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(a1)), model="whisper-large-v3").text
                res = ai_engine(txt, "translate", target_lang, glossary=glossary_txt)
                st.session_state.chat_messages.append({"role": "me", "src": txt, "trg": res})
                aud = create_audio(res, target_lang, is_slow)
                if aud: st.audio(aud, format="audio/mp3", autoplay=True)
        
        with c2:
            st.warning(f"MİSAFİR ({target_lang})")
            a2 = audio_recorder(text="", icon_size="3x", key="v2", recording_color="#ec4899", neutral_color="#fce7f3")
            if a2:
                txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(a2)), model="whisper-large-v3").text
                res = ai_engine(txt, "translate", "Türkçe", glossary=glossary_txt)
                st.session_state.chat_messages.append({"role": "you", "src": txt, "trg": res})
                aud = create_audio(res, "Türkçe", is_slow)
                if aud: st.audio(aud, format="audio/mp3", autoplay=True)
        
        # Sohbet Geçmişi
        st.write("---")
        for msg in reversed(st.session_state.chat_messages):
            cls = "chat-me" if msg['role'] == "me" else "chat-you"
            st.markdown(f"<div class='{cls}'>{msg['src']}<br><b>{msg['trg']}</b></div>", unsafe_allow_html=True)

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
                    
                    pdf = create_pdf("Toplanti Kaydi", f"{txt}\n\n---\n\n{trans}")
                    st.download_button("📄 PDF Rapor", pdf, "toplanti.pdf", "application/pdf")

# --- 3. ROL YAPMA ---
with tab_roleplay:
    c_sc, c_lang = st.columns([3, 1])
    with c_sc: scenario = st.selectbox("Senaryo:", ["Restoran", "Otel", "İş", "Doktor", "Serbest"])
    with c_lang: rp_lang = st.selectbox("Pratik Dili", LANG_OPTIONS, index=0)

    if scenario != st.session_state.rp_scenario:
        st.session_state.rp_scenario = scenario
        st.session_state.rp_history = []
        st.session_state.rp_history.append({"role": "assistant", "content": ai_engine("Başla", "roleplay", rp_lang, extra_ctx=scenario)})
        st.rerun()

    for msg in st.session_state.rp_history:
        cls = "rp-ai" if msg['role'] == "assistant" else "rp-user"
        icon = "🤖" if msg['role'] == "assistant" else "👤"
        st.markdown(f"<div class='{cls}'><b>{icon}</b> {msg['content']}</div>", unsafe_allow_html=True)

    rp_input = st.text_input("Cevabınız...", key="rp_in")
    if st.button("Gönder") and rp_input:
        st.session_state.rp_history.append({"role": "user", "content": rp_input})
        with st.spinner("..."):
            reply = ai_engine(rp_input, "roleplay", rp_lang, extra_ctx=scenario)
            st.session_state.rp_history.append({"role": "assistant", "content": reply})
        st.rerun()

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
                    
                    pdf = create_pdf("Dosya Analizi", res)
                    st.download_button("📄 PDF İndir", pdf, "analiz.pdf", "application/pdf")
                else: st.error("Hata.")

# --- 5. WEB ---
with tab_web:
    url = st.text_input("URL")
    if st.button("Analiz") and url:
        with st.spinner("..."):
            txt = local_read_web(url)
            if txt:
                res = ai_engine(txt, "summarize", target_lang)
                st.markdown(f"<div class='result-box'>{res}</div>", unsafe_allow_html=True)
                pdf = create_pdf(f"Web: {url}", res)
                st.download_button("📄 PDF İndir", pdf, "web.pdf", "application/pdf")
            else: st.error("Hata.")

st.divider()
