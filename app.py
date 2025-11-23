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

# --- 1. GENEL AYARLAR (UYGULAMA KİMLİĞİ) ---
st.set_page_config(
    page_title="LinguaFlow AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://www.google.com',
        'Report a bug': "https://www.google.com",
        'About': "LinguaFlow AI v9.0 - Yapay Zeka Destekli Çeviri Merkezi"
    }
)

# --- 2. CSS TASARIM (PROFESYONEL ARAYÜZ) ---
st.markdown("""
    <style>
    /* Genel */
    .stApp { background-color: #f8fafc; font-family: 'Inter', sans-serif; }
    
    /* Başlık Stili */
    .header-logo { 
        font-size: 2.2rem; font-weight: 800; color: #1e293b; 
        margin-bottom: 5px; letter-spacing: -0.5px;
    }
    .header-sub { color: #64748b; margin-bottom: 25px; font-size: 1rem; }
    
    /* Metin Alanları */
    .stTextArea textarea {
        border: 1px solid #e2e8f0; border-radius: 12px;
        font-size: 1.1rem; height: 280px !important; padding: 15px;
        background: white; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        resize: none;
    }
    .stTextArea textarea:focus { border-color: #3b82f6; ring: 2px solid #3b82f6; }
    
    /* Sonuç Kutusu */
    .result-box {
        background-color: white; border: 1px solid #e2e8f0; border-radius: 12px;
        min-height: 280px; padding: 20px; font-size: 1.1rem; color: #334155;
        white-space: pre-wrap; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    
    /* Ana Butonlar */
    div.stButton > button {
        background: linear-gradient(to right, #2563eb, #1d4ed8);
        color: white; border: none; border-radius: 8px;
        padding: 12px; font-weight: 600; width: 100%; transition: all 0.2s;
        box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2);
    }
    div.stButton > button:hover { 
        background: linear-gradient(to right, #1d4ed8, #1e40af);
        transform: translateY(-1px); 
        box-shadow: 0 6px 8px -1px rgba(37, 99, 235, 0.3);
    }
    
    /* Paylaşım Butonları */
    .share-btn-container {
        display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap;
    }
    .share-link {
        text-decoration: none; padding: 8px 12px; border-radius: 6px;
        font-size: 0.85rem; font-weight: 600; color: white !important;
        display: inline-flex; align-items: center; gap: 5px;
        transition: opacity 0.2s;
    }
    .share-link:hover { opacity: 0.9; text-decoration: none; }
    .whatsapp { background-color: #25D366; }
    .sms { background-color: #3b82f6; }
    .email { background-color: #64748b; }
    
    /* Geçmiş Öğeleri */
    .history-item {
        padding: 10px; margin-bottom: 8px; background: white; border-radius: 8px;
        font-size: 0.85rem; border-left: 4px solid #3b82f6; color: #475569;
        border: 1px solid #f1f5f9;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. API KONTROLÜ ---
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("⚠️ API Anahtarı Bulunamadı! Secrets ayarlarını kontrol edin.")
    st.stop()

# --- 4. STATE YÖNETİMİ ---
if "history" not in st.session_state: st.session_state.history = []
if "res_text" not in st.session_state: st.session_state.res_text = ""
if "input_val" not in st.session_state: st.session_state.input_val = ""

# --- 5. FONKSİYONLAR (MOTOR) ---
def ai_engine(text, task, target_lang="English", tone="Normal"):
    if not text: return ""
    
    if task == "translate":
        sys_msg = f"Sen uzman tercümansın. Hedef: {target_lang}. Ton: {tone}. GÖREV: Doğal ve akıcı çevir. Açıklama yapma."
    elif task == "improve":
        sys_msg = "Sen profesyonel editörsün. Metni gramer ve akıcılık yönünden düzelt. Dili koru."
    elif task == "summarize":
        sys_msg = f"Sen analistsin. Metni {target_lang} dilinde özetle. Önemli maddeleri çıkar."

    try:
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": text[:15000]}]
        )
        result = res.choices[0].message.content
        
        # Geçmişe Ekle
        if task == "translate":
            timestamp = datetime.datetime.now().strftime("%H:%M")
            short_src = (text[:30] + '..') if len(text) > 30 else text
            icon = "🌍" if task == "translate" else "✨"
            st.session_state.history.insert(0, {"time": timestamp, "src": short_src, "type": icon})
            
        return result
    except Exception as e: return f"Hata: {e}"

def create_audio(text, lang_name):
    code_map = {"Türkçe": "tr", "English": "en", "Deutsch": "de", "Français": "fr", "Español": "es", "Rusça": "ru", "Arapça": "ar", "Çince": "zh"}
    lang_code = code_map.get(lang_name, "en")
    try:
        fp = io.BytesIO()
        gTTS(text=text, lang=lang_code, slow=False).write_to_fp(fp)
        return fp.getvalue()
    except: return None

def local_read_file(file):
    try:
        if file.name.endswith('.pdf'):
            reader = PyPDF2.PdfReader(file)
            return "".join([page.extract_text() for page in reader.pages])
        else:
            return client.audio.transcriptions.create(file=("a.wav", file), model="whisper-large-v3").text
    except: return None

def render_share_buttons(text):
    if not text: return
    encoded_text = urllib.parse.quote(text)
    whatsapp_url = f"https://api.whatsapp.com/send?text={encoded_text}"
    sms_url = f"sms:?body={encoded_text}"
    email_url = f"mailto:?subject=LinguaFlow&body={encoded_text}"
    
    st.markdown(f"""
    <div class="share-btn-container">
        <a href="{whatsapp_url}" target="_blank" class="share-link whatsapp">📱 WhatsApp</a>
        <a href="{sms_url}" class="share-link sms">💬 SMS</a>
        <a href="{email_url}" class="share-link email">📧 Email</a>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# ARAYÜZ (UI)
# ==========================================

# --- YAN MENÜ ---
with st.sidebar:
    st.title("LinguaFlow")
    st.caption("v9.0 Final")
    st.markdown("---")
    
    st.markdown("### 🕒 Son İşlemler")
    if st.session_state.history:
        for item in st.session_state.history[:6]:
            st.markdown(f"""
            <div class="history-item">
                <div style="font-size:0.7rem; color:#94a3b8">{item['time']}</div>
                {item['type']} {item['src']}
            </div>
            """, unsafe_allow_html=True)
        if st.button("Temizle", type="secondary"):
            st.session_state.history = []
            st.rerun()
    else:
        st.info("Geçmiş boş.")
    
    st.markdown("---")
    with st.expander("ℹ️ Hakkında & Yardım"):
        st.markdown("""
        **LinguaFlow AI Nedir?**
        Yapay zeka destekli, çok modlu bir çeviri ve analiz asistanıdır.
        
        **Modlar:**
        - **📝 Metin:** Yazılı çeviri ve gramer düzeltme.
        - **🎙️ Ortam:** Toplantı ve konuşma dinleme.
        - **📂 Dosya:** PDF ve Ses dosyası analizi.
        - **🔗 Web:** Haber ve makale özeti.
        """)

# --- ÜST BAŞLIK ---
st.markdown('<div class="header-logo">LinguaFlow AI</div>', unsafe_allow_html=True)

# --- SEKMELER ---
tab_text, tab_conf, tab_files, tab_web = st.tabs(["📝 Metin & Yazım", "🎙️ Ortam & Toplantı", "📂 Dosya & Belge", "🔗 Web Analiz"])
LANG_OPTIONS = ["English", "Türkçe", "Deutsch", "Français", "Español", "Italiano", "Русский", "العربية", "中文"]

# --- 1. METİN ---
with tab_text:
    c1, c2, c3 = st.columns([3, 1, 3])
    with c1: st.markdown("**Giriş (Otomatik)**")
    with c3: target_lang = st.selectbox("Hedef", LANG_OPTIONS, label_visibility="collapsed")

    col_in, col_out = st.columns(2)
    with col_in:
        input_text = st.text_area("Giriş", value=st.session_state.input_val, height=280, placeholder="Metni buraya yapıştırın...", label_visibility="collapsed")
        
        b1, b2, b3, b4 = st.columns([3, 3, 2, 1])
        with b1:
            if st.button("Çevir ➔"):
                if input_text:
                    with st.spinner("Çevriliyor..."):
                        st.session_state.res_text = ai_engine(input_text, "translate", target_lang)
                        st.session_state.input_val = input_text
        with b2:
            if st.button("✨ Düzelt"):
                if input_text:
                    with st.spinner("İyileştiriliyor..."):
                        st.session_state.res_text = ai_engine(input_text, "improve")
        with b3: tone = st.selectbox("Ton", ["Normal", "Resmi", "Samimi"], label_visibility="collapsed")
        with b4:
            if st.button("🗑️"): st.session_state.input_val = ""; st.session_state.res_text = ""; st.rerun()

    with col_out:
        res = st.session_state.res_text
        st.markdown(f"""<div class="result-box">{res if res else '<span style="color:#aaa;">...</span>'}</div>""", unsafe_allow_html=True)
        if res:
            st.write("")
            ca, cb = st.columns([1, 3])
            with ca:
                aud = create_audio(res, target_lang)
                if aud: st.audio(aud, format="audio/mp3")
            with cb:
                render_share_buttons(res)
                with st.expander("Kopyala"): st.code(res, language=None)

# --- 2. KONFERANS ---
with tab_conf:
    st.info("🎙️ **Canlı Dinleme:** Toplantı veya ortam konuşmalarını dinler, bitince çevirir.")
    c1, c2 = st.columns([1, 3])
    with c1:
        conf_target = st.selectbox("Çeviri Dili", LANG_OPTIONS, key="conf_t")
        st.write("")
        audio_conf = audio_recorder(text="🔴 BAŞLAT / DURDUR", icon_size="2x", recording_color="#dc2626", pause_threshold=20.0)
    with c2:
        if audio_conf:
            with st.spinner("Analiz ediliyor..."):
                try:
                    txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(audio_conf)), model="whisper-large-v3").text
                    trans = ai_engine(txt, "translate", target_lang=conf_target)
                    st.success(f"🗣️: {txt}")
                    st.info(f"🤖: {trans}")
                    render_share_buttons(f"{txt}\n\n{trans}")
                    st.download_button("📥 İndir", f"{txt}\n{trans}", "toplanti.txt")
                except: st.error("Ses anlaşılamadı.")

# --- 3. DOSYA ---
with tab_files:
    st.write("📂 **PDF** veya **Ses** yükleyin.")
    u_file = st.file_uploader("", type=['pdf', 'mp3', 'wav', 'm4a'], label_visibility="collapsed")
    if u_file:
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"Dosya: {u_file.name}")
            f_target = st.selectbox("Dil", LANG_OPTIONS, key="f_tgt")
            if st.button("Analiz Et"):
                with st.spinner("İşleniyor..."):
                    raw = local_read_file(u_file)
                    if raw and len(raw)>10:
                        mode = "translate" if len(raw) < 3000 else "summarize"
                        st.session_state.f_res = ai_engine(raw, mode, f_target)
                    else: st.error("Hata.")
        with col2:
            if "f_res" in st.session_state:
                st.markdown(f"<div class='result-box'>{st.session_state.f_res}</div>", unsafe_allow_html=True)
                render_share_buttons(st.session_state.f_res)
                st.download_button("📥 İndir", st.session_state.f_res, "dosya.txt")

# --- 4. WEB ---
with tab_web:
    url = st.text_input("Web URL")
    w_target = st.selectbox("Rapor Dili", LANG_OPTIONS, key="w_tgt")
    if st.button("Analiz Et") and url:
        with st.spinner("Okunuyor..."):
            try:
                h = {'User-Agent': 'Mozilla/5.0'}
                soup = BeautifulSoup(requests.get(url, headers=h, timeout=10).content, 'html.parser')
                raw = " ".join([p.get_text() for p in soup.find_all(['p', 'h1'])])[:10000]
                res = ai_engine(raw, "summarize", w_target)
                st.markdown(f"<div class='result-box'>{res}</div>", unsafe_allow_html=True)
                render_share_buttons(f"Link: {url}\n\n{res}")
                st.download_button("📥 İndir", res, "web_ozet.txt")
            except: st.error("Siteye erişilemedi.")

st.divider()
