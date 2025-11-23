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
from fpdf import FPDF

# --- 1. GENEL AYARLAR ---
st.set_page_config(
    page_title="LinguaFlow Pro",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS TASARIM ---
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; font-family: 'Inter', sans-serif; }
    
    .header-logo { 
        font-size: 2.2rem; font-weight: 800; color: #1e293b; 
        text-align: center; margin-top: -20px; letter-spacing: -0.5px;
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
    
    /* Roleplay Balonları */
    .rp-ai { background: #f1f5f9; padding: 15px; border-radius: 15px 15px 15px 0; margin-bottom: 10px; border-left: 4px solid #475569; }
    .rp-user { background: #e0e7ff; padding: 15px; border-radius: 15px 15px 0 15px; margin-bottom: 10px; text-align: right; border-right: 4px solid #4f46e5; }

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
if "rp_history" not in st.session_state: st.session_state.rp_history = [] # Roleplay geçmişi
if "rp_scenario" not in st.session_state: st.session_state.rp_scenario = ""

# --- 5. MOTOR ---
def ai_engine(text, task, target_lang="English", tone="Normal", glossary="", extra_ctx=""):
    if not text: return ""
    
    glossary_prompt = f"TERMİNOLOJİ: \n{glossary}" if glossary else ""

    if task == "translate":
        sys_msg = f"Sen tercümansın. Hedef: {target_lang}. Ton: {tone}. {glossary_prompt}. Sadece çeviriyi ver."
    elif task == "improve":
        sys_msg = "Editörsün. Metni düzelt. Sadece düzeltilmiş metni ver."
    elif task == "summarize":
        sys_msg = f"Analistsin. Metni {target_lang} dilinde özetle."
    elif task == "roleplay":
        sys_msg = f"""
        Sen bir dil eğitmenisin ve şu senaryoyu oynuyorsun: {extra_ctx}.
        Kullanıcıya cevap ver ve konuşmayı sürdür.
        Cevabın sonuna parantez içinde (Kullanıcının hatası varsa düzelt) notunu ekle.
        Dil: {target_lang}.
        """

    try:
        msgs = [{"role": "system", "content": sys_msg}]
        # Roleplay için geçmişi ekle
        if task == "roleplay":
            for msg in st.session_state.rp_history[-6:]: # Son 6 mesajı hatırla
                msgs.append(msg)
        
        msgs.append({"role": "user", "content": text[:15000]})

        res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=msgs)
        return res.choices[0].message.content
    except Exception as e: return f"Hata: {e}"

def create_pdf(title, content):
    """Basit PDF Raporlayıcı"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, title.encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", '', 12)
    
    # Türkçe karakter sorunu için basit replace (FPDF unicode desteği sınırlı)
    content = content.replace('ğ','g').replace('Ğ','G').replace('ş','s').replace('Ş','S').replace('İ','I').replace('ı','i')
    
    pdf.multi_cell(0, 10, content.encode('latin-1', 'replace').decode('latin-1'))
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
    st.caption("Business Edition v27.0")
    
    st.markdown("### ⚙️ Ayarlar")
    speed_opt = st.select_slider("Hız", options=["Yavaş", "Normal"], value="Normal")
    is_slow = True if speed_opt == "Yavaş" else False
    
    with st.expander("📚 Sözlük"):
        glossary_txt = st.text_area("Örn: AI=Yapay Zeka", height=70)

    st.divider()
    st.markdown("### 🕒 Geçmiş")
    if st.session_state.history:
        for item in st.session_state.history[:5]:
            st.caption(f"• {item['src'][:30]}..")
        if st.button("Temizle"): st.session_state.history = []; st.rerun()

st.markdown('<div class="header-logo">LinguaFlow Pro</div>', unsafe_allow_html=True)

tab_text, tab_roleplay, tab_voice, tab_files, tab_web = st.tabs(["📝 Metin", "🎭 Rol Yapma", "🎙️ Ses", "📂 Dosya", "🔗 Web"])
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
                    
                    # Geçmişe ekle
                    ts = datetime.datetime.now().strftime("%H:%M")
                    st.session_state.history.insert(0, {"src": input_text, "trg": st.session_state.res_text})

    with col_out:
        res = st.session_state.res_text
        st.markdown(f"""<div class="result-box">{res if res else '...'}</div>""", unsafe_allow_html=True)
        if res:
            st.write("")
            ca, cb = st.columns([1, 4])
            with ca:
                aud = create_audio(res, target_lang, is_slow)
                if aud: st.audio(aud, format="audio/mp3")
            with cb: st.code(res, language=None)

# --- 2. ROL YAPMA (ROLEPLAY) ---
with tab_roleplay:
    c_sc, c_lang = st.columns([3, 1])
    with c_sc:
        scenario = st.selectbox("Senaryo Seçin:", ["Restoranda Sipariş", "Otel Check-in", "İş Görüşmesi", "Adres Sorma", "Doktorda", "Serbest Sohbet"])
    with c_lang:
        rp_lang = st.selectbox("Pratik Dili", LANG_OPTIONS, index=0) # Default English

    # Senaryo değişirse geçmişi temizle
    if scenario != st.session_state.rp_scenario:
        st.session_state.rp_scenario = scenario
        st.session_state.rp_history = []
        # İlk mesajı AI başlatsın
        start_msg = ai_engine("Başlangıç cümlesi kur.", "roleplay", rp_lang, extra_ctx=scenario)
        st.session_state.rp_history.append({"role": "assistant", "content": start_msg})
        st.rerun()

    # Sohbet Alanı
    for msg in st.session_state.rp_history:
        cls = "rp-ai" if msg['role'] == "assistant" else "rp-user"
        icon = "🤖" if msg['role'] == "assistant" else "👤"
        st.markdown(f"<div class='{cls}'><b>{icon}</b> {msg['content']}</div>", unsafe_allow_html=True)

    # Giriş
    rp_input = st.text_input("Cevabınız...", key="rp_in")
    if st.button("Gönder") and rp_input:
        st.session_state.rp_history.append({"role": "user", "content": rp_input})
        with st.spinner("AI yazıyor..."):
            reply = ai_engine(rp_input, "roleplay", rp_lang, extra_ctx=scenario)
            st.session_state.rp_history.append({"role": "assistant", "content": reply})
        st.rerun()
        
    if st.button("Senaryoyu Sıfırla", type="secondary"):
        st.session_state.rp_history = []
        st.session_state.rp_scenario = "" # Trigger reset
        st.rerun()

# --- 3. SES ---
with tab_voice:
    c1, c2 = st.columns([1, 3])
    with c1: st.write("Sürekli Dinleme")
    with c2:
        ac = audio_recorder(text="BAŞLAT / DURDUR", icon_size="2x", recording_color="#dc2626", pause_threshold=20.0)
        if ac:
            with st.spinner("Analiz..."):
                txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(ac)), model="whisper-large-v3").text
                trans = ai_engine(txt, "translate", target_lang, glossary=glossary_txt)
                st.success(f"Orijinal: {txt}")
                st.info(f"Çeviri: {trans}")
                
                # PDF Rapor
                pdf = create_pdf("Toplanti Raporu", f"KAYNAK:\n{txt}\n\nCEVIRI:\n{trans}")
                st.download_button("📄 PDF Raporu İndir", pdf, "toplanti.pdf", "application/pdf")

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
                res = ai_engine(txt, "summarize", target_lang=target_lang) # Hedef dili kullan
                st.markdown(f"<div class='result-box'>{res}</div>", unsafe_allow_html=True)
                
                pdf = create_pdf(f"Web Analizi: {url[:30]}...", res)
                st.download_button("📄 PDF İndir", pdf, "web_analiz.pdf", "application/pdf")
            else: st.error("Hata.")

st.divider()
