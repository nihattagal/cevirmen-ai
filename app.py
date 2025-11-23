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
from fpdf import FPDF # PDF oluşturucu

# --- 1. GENEL AYARLAR ---
st.set_page_config(
    page_title="LinguaFlow Platinum",
    page_icon="🏆",
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
    
    /* Metin Alanı */
    .stTextArea textarea {
        border: 1px solid #cbd5e1; border-radius: 10px;
        font-size: 1.1rem; padding: 15px;
        background: white; resize: none; box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .stTextArea textarea:focus { border-color: #4f46e5; box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.2); }
    
    /* Sonuç Kutusu */
    .result-box {
        background-color: white; border: 1px solid #cbd5e1; border-radius: 10px;
        padding: 20px; font-size: 1.1rem; color: #334155;
        white-space: pre-wrap; box-shadow: 0 2px 4px rgba(0,0,0,0.02); position: relative;
    }
    
    /* Butonlar */
    div.stButton > button {
        background-color: #0f172a; color: white; border: none; border-radius: 8px;
        padding: 12px; font-weight: 600; width: 100%; transition: all 0.2s;
    }
    div.stButton > button:hover { background-color: #334155; transform: translateY(-1px); }
    
    /* İkincil Butonlar */
    .secondary-btn div.stButton > button { background-color: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; }
    .secondary-btn div.stButton > button:hover { background-color: #e2e8f0; color: #1e293b; }

    /* WhatsApp Balonları */
    .chat-me { background: #dbeafe; border-radius: 12px 12px 0 12px; padding: 12px; margin: 5px 0; text-align: right; margin-left: auto; max-width: 80%; color:#1e3a8a; }
    .chat-you { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px 12px 12px 0; padding: 12px; margin: 5px 0; max-width: 80%; color:#334155; }
    
    /* PDF Butonu */
    .pdf-btn div.stButton > button { background-color: #dc2626; color: white; }
    .pdf-btn div.stButton > button:hover { background-color: #b91c1c; }
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
if "chat_messages" not in st.session_state: st.session_state.chat_messages = []
if "res_text" not in st.session_state: st.session_state.res_text = ""
if "input_val" not in st.session_state: st.session_state.input_val = ""
if "detected_lang" not in st.session_state: st.session_state.detected_lang = ""
if "sentiment_score" not in st.session_state: st.session_state.sentiment_score = 50

# --- 5. MOTOR ---
def ai_engine(text, task, target_lang="English", tone="Normal", glossary="", extra_prompt=""):
    if not text: return ""
    
    glossary_prompt = f"TERMİNOLOJİ: \n{glossary}" if glossary else ""

    if task == "translate":
        sys_msg = f"""
        Sen uzman tercümansın. Hedef: {target_lang}. Ton: {tone}.
        {glossary_prompt}
        GÖREVLER:
        1. Metni çevir.
        2. Metnin duygu tonunu 0 ile 100 arasında puanla (0=Çok Negatif, 50=Nötr, 100=Çok Pozitif).
        3. Format: [PUAN] ||| [DİL] ||| ÇEVİRİ
        """
    elif task == "improve":
        sys_msg = "Editörsün. Metni düzelt. Format: [50] ||| [Dil] ||| METİN"
    elif task == "summarize":
        sys_msg = f"Analistsin. Metni {target_lang} dilinde özetle. Format: [50] ||| [Dil] ||| METİN"

    try:
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": text[:15000]}]
        )
        full_res = res.choices[0].message.content
        
        # Parser
        if "|||" in full_res:
            parts = full_res.split("|||")
            if len(parts) >= 3:
                score = int(parts[0].strip().replace("[", "").replace("]", ""))
                lang = parts[1].strip().replace("[", "").replace("]", "")
                content = parts[2].strip()
                
                st.session_state.sentiment_score = score
                st.session_state.detected_lang = lang
                return content
            else:
                return full_res
        else:
            return full_res

    except Exception as e: return f"Hata: {str(e)}"

def create_pdf(original, translated, title="LinguaFlow Raporu"):
    """Profesyonel PDF Oluşturucu"""
    pdf = FPDF()
    pdf.add_page()
    
    # Türkçe karakter desteği için font ayarı (Arial varsayılan, basit çözüm unicode replace)
    # FPDF'in standart fontları Türkçe karakterleri desteklemez, bu yüzden basit mapping yapıyoruz
    # Gerçek prodüksiyonda .ttf font dosyası yüklenir.
    def clean(text):
        replacements = {'ğ':'g', 'Ğ':'G', 'ü':'u', 'Ü':'U', 'ş':'s', 'Ş':'S', 'ı':'i', 'İ':'I', 'ö':'o', 'Ö':'O', 'ç':'c', 'Ç':'C'}
        for k, v in replacements.items(): text = text.replace(k, v)
        return text.encode('latin-1', 'replace').decode('latin-1')

    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, clean(title), ln=True, align="C")
    pdf.ln(10)
    
    pdf.set_font("Arial", "B", 12)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 10, clean(f"Tarih: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"), ln=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, "KAYNAK METIN:", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, clean(original[:2000])) # Sığması için limit
    
    pdf.ln(10)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "CEVIRI / ANALIZ:", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, clean(translated[:2000]))
    
    return pdf.output(dest='S').encode('latin-1')

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
    st.markdown(f"<a href='{wa}' target='_blank' style='text-decoration:none; color:#25D366; font-weight:bold; font-size:0.85rem;'>📲 WhatsApp Paylaş</a>", unsafe_allow_html=True)

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
    st.markdown("### ⚙️ Ayarlar")
    
    # MOBİL MOD
    is_mobile_mode = st.toggle("📱 Mobil Uygulama Modu", value=False)
    
    # GÖRÜNÜM AYARI
    layout_mode = st.radio("Görünüm:", ["Yan Yana (PC)", "Alt Alta (Mobil)"], horizontal=True)
    is_split = True if layout_mode == "Yan Yana (PC)" else False
    
    st.divider()
    speech_slow = st.checkbox("🐢 Yavaş Okuma", value=False)
    with st.expander("📚 Sözlük"):
        glossary_txt = st.text_area("Örn: AI=Yapay Zeka", height=70)

# --- BAŞLIK ---
st.markdown('<div class="header-logo">LinguaFlow Platinum</div>', unsafe_allow_html=True)

# --- SEKMELER ---
if is_mobile_mode:
    tabs = st.tabs(["📝 Metin", "💬 Sohbet", "📂 Dosya", "🔗 Web"])
    t_text, t_chat, t_file, t_web = tabs[0], tabs[1], tabs[2], tabs[3]
else:
    tabs = st.tabs(["📝 Metin", "📂 Dosya", "🔗 Web"])
    t_text, t_file, t_web = tabs[0], tabs[1], tabs[2]
    t_chat = None

LANG_OPTIONS = ["English", "Türkçe", "Deutsch", "Français", "Español", "Italiano", "Русский", "العربية", "中文"]

# --- 1. METİN ---
with t_text:
    c1, c2, c3, c4 = st.columns([3, 1, 3, 1])
    with c1: st.markdown("**Kaynak (Otomatik)**")
    with c3: target_lang = st.selectbox("Hedef", LANG_OPTIONS, label_visibility="collapsed")
    
    with c2:
        st.markdown('<div class="secondary-btn">', unsafe_allow_html=True)
        if st.button("⇄"): pass # Swap logic eklenebilir
        st.markdown('</div>', unsafe_allow_html=True)

    # DİNAMİK LAYOUT (YAN YANA veya ALT ALTA)
    if is_split:
        col_in, col_out = st.columns(2)
    else:
        col_in = st.container()
        col_out = st.container()
    
    with col_in:
        # Dikte
        mc, tc = st.columns([1, 8])
        with mc: audio_in = audio_recorder(text="", icon_size="2x", recording_color="#ef4444", neutral_color="#e2e8f0", key="dict")
        with tc: st.caption("Sesle Yaz")
        
        if audio_in:
            with st.spinner("..."):
                txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(audio_in)), model="whisper-large-v3").text
                st.session_state.input_val = txt
                st.rerun()

        with st.form(key="t_form"):
            input_text = st.text_area("Metin", value=st.session_state.input_val, height=280, label_visibility="collapsed")
            b1, b2 = st.columns([3, 2])
            with b1: submit = st.form_submit_button("Çevir ➔", type="primary", use_container_width=True)
            with b2: tone = st.selectbox("Ton", ["Normal", "Resmi", "Samimi"], label_visibility="collapsed")
        
        if submit and input_text:
            with st.spinner("AI Çalışıyor..."):
                st.session_state.res_text = ai_engine(input_text, "translate", target_lang, tone, glossary_txt)
                st.session_state.input_val = input_text

    with col_out:
        if is_split: 
            st.write("") # Hizalama
            st.write("")
        
        res = st.session_state.res_text
        
        # DUYGU METRESİ (Yeni Özellik)
        if res:
            score = st.session_state.get("sentiment_score", 50)
            st.progress(score, text=f"Duygu Tonu: {'Pozitif' if score > 60 else 'Negatif' if score < 40 else 'Nötr'}")
        
        st.markdown(f"""<div class="result-box">{res if res else '...'}</div>""", unsafe_allow_html=True)
        
        if res:
            st.write("")
            ca, cb, cc = st.columns([2, 2, 2])
            with ca:
                aud = create_audio(res, target_lang, speech_slow)
                if aud: st.audio(aud, format="audio/mp3")
            with cb:
                st.markdown('<div class="pdf-btn">', unsafe_allow_html=True)
                pdf_data = create_pdf(input_text, res)
                st.download_button("📄 PDF İndir", pdf_data, file_name="Ceviri_Raporu.pdf", mime="application/pdf", use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
            with cc: render_share(res)

# --- 2. SOHBET (Mobil) ---
if is_mobile_mode and t_chat:
    with t_chat:
        st.info("🗣️ **Canlı Sohbet**")
        c1, c2 = st.columns(2)
        with c1:
            st.write("🎤 SİZ")
            a1 = audio_recorder(text="", icon_size="3x", key="v1", recording_color="#3b82f6")
            if a1:
                txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(a1)), model="whisper-large-v3").text
                res = ai_engine(txt, "translate", target_lang, glossary=glossary_txt)
                st.session_state.chat_messages.append({"role": "me", "src": txt, "trg": res})
        with c2:
            st.write(f"🎤 MİSAFİR")
            a2 = audio_recorder(text="", icon_size="3x", key="v2", recording_color="#ec4899")
            if a2:
                txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(a2)), model="whisper-large-v3").text
                res = ai_engine(txt, "translate", "Türkçe", glossary=glossary_txt)
                st.session_state.chat_messages.append({"role": "you", "src": txt, "trg": res})

        st.divider()
        if st.session_state.chat_messages:
            for msg in reversed(st.session_state.chat_messages):
                role_cls = "chat-me" if msg['role'] == 'me' else "chat-you"
                st.markdown(f"""<div class="{role_cls}">{msg['src']}<br><b>{msg['trg']}</b></div>""", unsafe_allow_html=True)
            if st.button("Temizle"): st.session_state.chat_messages = []; st.rerun()

# --- 3. DOSYA ---
with t_file:
    u_file = st.file_uploader("Dosya Yükle", type=['pdf', 'mp3', 'wav', 'm4a'])
    if u_file:
        if st.button("Analiz Et"):
            with st.spinner("..."):
                raw = local_read_file(u_file)
                if raw:
                    res = ai_engine(raw, "summarize" if len(raw)>3000 else "translate", target_lang, glossary=glossary_txt)
                    st.markdown(f"<div class='result-box'>{res}</div>", unsafe_allow_html=True)
                    
                    # PDF İndirme
                    pdf_data = create_pdf(raw[:2000], res, "Dosya Analizi")
                    st.download_button("📄 PDF Raporu İndir", pdf_data, "Analiz.pdf", mime="application/pdf")
                else: st.error("Hata.")

# --- 4. WEB ---
with t_web:
    url = st.text_input("URL")
    if st.button("Analiz") and url:
        with st.spinner("..."):
            txt = local_read_web(url)
            if txt:
                res = ai_engine(txt, "summarize", target_lang)
                st.markdown(f"<div class='result-box'>{res}</div>", unsafe_allow_html=True)
                pdf_data = create_pdf(url, res, "Web Özeti")
                st.download_button("📄 PDF Raporu İndir", pdf_data, "Web_Ozet.pdf", mime="application/pdf")
            else: st.error("Hata.")

st.divider()
