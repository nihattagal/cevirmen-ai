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
    page_title="LinguaFlow AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS TASARIM (PREMIUM) ---
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; font-family: 'Inter', sans-serif; }
    
    /* Başlık */
    .header-logo { 
        font-size: 2.2rem; font-weight: 800; color: #0F172A; 
        text-align: center; letter-spacing: -1px; margin-top: -20px;
    }
    .header-sub { text-align: center; color: #64748b; margin-bottom: 20px; font-size: 0.9rem; }
    
    /* Metin Alanı */
    .stTextArea textarea {
        border: 1px solid #cbd5e1; border-radius: 12px;
        font-size: 1.1rem; height: 250px !important; padding: 15px;
        background: white; box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .stTextArea textarea:focus { border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59,130,246,0.1); }
    
    /* Sonuç Kutusu */
    .result-box {
        background-color: white; border: 1px solid #cbd5e1; border-radius: 12px;
        min-height: 250px; padding: 20px; font-size: 1.1rem; color: #334155;
        white-space: pre-wrap; box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    
    /* Sözlük Modu Kutusu */
    .dict-box {
        background-color: #fffbeb; border: 1px solid #fcd34d; border-radius: 12px;
        padding: 15px; color: #92400e; font-size: 0.95rem; margin-top: 10px;
    }
    
    /* Butonlar */
    div.stButton > button {
        background: #0F172A; color: white; border: none; border-radius: 8px;
        padding: 12px; font-weight: 600; width: 100%; transition: all 0.2s;
    }
    div.stButton > button:hover { background: #1e293b; transform: translateY(-1px); }
    
    /* Paylaşım Butonları */
    .share-btn-container { display: flex; gap: 8px; margin-top: 10px; }
    .share-link {
        text-decoration: none; padding: 6px 12px; border-radius: 6px;
        font-size: 0.8rem; font-weight: 600; color: white !important;
        display: inline-flex; align-items: center; gap: 5px;
    }
    .whatsapp { background-color: #25D366; }
    .email { background-color: #64748b; }
    
    /* Sohbet Balonları */
    .chat-me { background: #eff6ff; border-left: 4px solid #3b82f6; padding: 10px; border-radius: 8px; margin-bottom: 5px;}
    .chat-you { background: #fff1f2; border-right: 4px solid #ec4899; padding: 10px; border-radius: 8px; margin-bottom: 5px; text-align: right;}
    </style>
""", unsafe_allow_html=True)

# --- 3. API ---
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("⚠️ API Key Hatası! Secrets ayarlarını kontrol edin.")
    st.stop()

# --- 4. STATE ---
if "history" not in st.session_state: st.session_state.history = []
if "res_text" not in st.session_state: st.session_state.res_text = ""
if "input_val" not in st.session_state: st.session_state.input_val = ""
if "dict_res" not in st.session_state: st.session_state.dict_res = ""

# --- 5. MOTOR (SÖZLÜK YETENEĞİ EKLENDİ) ---
def ai_engine(text, task, target_lang="English", tone="Normal"):
    if not text: return ""
    
    if task == "translate":
        # Eğer metin çok kısaysa (1-3 kelime), Sözlük Modunu devreye sok
        word_count = len(text.split())
        if word_count <= 3:
            return ai_engine(text, "dictionary", target_lang)
            
        sys_msg = f"Sen uzman tercümansın. Hedef: {target_lang}. Ton: {tone}. Sadece çeviriyi ver. Açıklama yapma."
    
    elif task == "dictionary":
        sys_msg = f"""
        Sen bir sözlüksün. Girilen kelimeyi/ifadeyi {target_lang} diline çevir.
        FORMAT:
        1. [Ana Çeviri]
        2. (Kelime Türü: İsim/Fiil vb.)
        3. Alternatif Anlamlar: ...
        4. Örnek Cümle: ...
        """
        
    elif task == "improve":
        sys_msg = "Sen editörsün. Metni gramer ve stil açısından düzelt. Dili koru."
    elif task == "summarize":
        sys_msg = f"Sen analistsin. Metni {target_lang} dilinde özetle. Önemli maddeleri çıkar."

    try:
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": text[:15000]}]
        )
        result = res.choices[0].message.content
        
        # Geçmişe Ekle (Sözlük hariç, çok kalabalık olmasın)
        if task == "translate":
            timestamp = datetime.datetime.now().strftime("%H:%M")
            short_src = (text[:20] + '..') if len(text) > 20 else text
            st.session_state.history.insert(0, f"[{timestamp}] {short_src}")
            
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

def render_share(text):
    if not text: return
    encoded = urllib.parse.quote(text)
    wa = f"https://api.whatsapp.com/send?text={encoded}"
    em = f"mailto:?body={encoded}"
    st.markdown(f"""
    <div class="share-btn-container">
        <a href="{wa}" target="_blank" class="share-link whatsapp">📱 WhatsApp</a>
        <a href="{em}" class="share-link email">📧 Email</a>
    </div>
    """, unsafe_allow_html=True)

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

with st.sidebar:
    st.title("Geçmiş")
    if st.session_state.history:
        for item in st.session_state.history[:8]: st.caption(item)
        if st.button("Temizle", type="secondary"): st.session_state.history = []; st.rerun()
    else: st.info("Boş")

st.markdown('<div class="header-logo">LinguaFlow AI</div><div class="header-sub">V10.0 Platinum</div>', unsafe_allow_html=True)

tab_text, tab_voice, tab_files, tab_web = st.tabs(["📝 Metin & Sözlük", "🎙️ Ses (Sohbet/Konferans)", "📂 Dosya", "🔗 Web"])

LANG_OPTIONS = ["English", "Türkçe", "Deutsch", "Français", "Español", "Italiano", "Русский", "العربية", "中文"]

# --- 1. METİN & SÖZLÜK ---
with tab_text:
    c1, c2, c3 = st.columns([3, 1, 3])
    with c1: st.markdown("**Giriş (Otomatik)**")
    with c3: target_lang = st.selectbox("Hedef", LANG_OPTIONS, label_visibility="collapsed")

    col_in, col_out = st.columns(2)
    with col_in:
        input_text = st.text_area("Metin", value=st.session_state.input_val, height=280, placeholder="Metin veya tek kelime yazın...", label_visibility="collapsed")
        
        b1, b2, b3, b4 = st.columns([3, 3, 2, 1])
        with b1:
            if st.button("Çevir ➔"):
                if input_text:
                    with st.spinner("İşleniyor..."):
                        st.session_state.res_text = ai_engine(input_text, "translate", target_lang)
                        st.session_state.input_val = input_text
        with b2:
            if st.button("✨ Düzelt"):
                if input_text:
                    with st.spinner("..."):
                        st.session_state.res_text = ai_engine(input_text, "improve")
        with b3: tone = st.selectbox("Ton", ["Normal", "Resmi", "Samimi"], label_visibility="collapsed")
        with b4:
            if st.button("🗑️"): st.session_state.input_val = ""; st.session_state.res_text = ""; st.rerun()

    with col_out:
        res = st.session_state.res_text
        # Eğer sonuç sözlük formatındaysa (liste içeriyorsa) farklı göster
        if "1." in res and "Örnek" in res:
            st.markdown(f"<div class='result-box' style='border-left:5px solid #f59e0b;'>{res}</div>", unsafe_allow_html=True)
            st.caption("💡 Akıllı Sözlük Modu Aktif")
        else:
            st.markdown(f"""<div class="result-box">{res if res else '...'}</div>""", unsafe_allow_html=True)
        
        if res:
            st.write("")
            ca, cb = st.columns([1, 3])
            with ca:
                aud = create_audio(res, target_lang)
                if aud: st.audio(aud, format="audio/mp3")
            with cb: render_share(res)

# --- 2. SES (HİBRİT MOD) ---
with tab_voice:
    voice_mode = st.radio("Mod Seçiniz:", ["🗣️ Karşılıklı Sohbet (Turist)", "🎙️ Konferans (Sürekli Dinleme)"], horizontal=True)
    st.divider()
    
    if "Sohbet" in voice_mode:
        c1, c2 = st.columns(2)
        with c1:
            st.info("SİZ (Mikrofon 1)")
            a1 = audio_recorder(text="", icon_size="3x", key="v1", recording_color="#3b82f6", neutral_color="#dbeafe")
            if a1:
                txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(a1)), model="whisper-large-v3").text
                res = ai_engine(txt, "translate", target_lang) # Üstte seçili dile çevir
                aud = create_audio(res, target_lang)
                st.markdown(f"<div class='chat-me'>🗣️ {txt}<br><b>{res}</b></div>", unsafe_allow_html=True)
                if aud: st.audio(aud, format="audio/mp3", autoplay=True)
        
        with c2:
            st.warning(f"MİSAFİR ({target_lang})")
            a2 = audio_recorder(text="", icon_size="3x", key="v2", recording_color="#ec4899", neutral_color="#fce7f3")
            if a2:
                txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(a2)), model="whisper-large-v3").text
                res = ai_engine(txt, "translate", "Türkçe") # Bize çevir
                aud = create_audio(res, "Türkçe")
                st.markdown(f"<div class='chat-you'>🗣️ {txt}<br><b>{res}</b></div>", unsafe_allow_html=True)
                if aud: st.audio(aud, format="audio/mp3", autoplay=True)

    else: # Konferans Modu
        c_conf1, c_conf2 = st.columns([1, 3])
        with c_conf1:
            st.write("Uzun süreli dinleme.")
            audio_conf = audio_recorder(text="BAŞLAT / DURDUR", icon_size="2x", recording_color="#dc2626", pause_threshold=20.0)
        with c_conf2:
            if audio_conf:
                with st.spinner("Analiz..."):
                    try:
                        txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(audio_conf)), model="whisper-large-v3").text
                        trans = ai_engine(txt, "translate", target_lang)
                        st.success(f"Orijinal: {txt}")
                        st.info(f"Çeviri: {trans}")
                        st.download_button("İndir", f"{txt}\n{trans}", "kayit.txt")
                    except: st.error("Ses yok.")

# --- 3. DOSYA ---
with tab_files:
    u_file = st.file_uploader("Dosya Seç", type=['pdf', 'mp3', 'wav', 'm4a'])
    if u_file:
        if st.button("Analiz Et"):
            with st.spinner("..."):
                raw = local_read_file(u_file)
                if raw:
                    mode = "translate" if len(raw) < 3000 else "summarize"
                    res = ai_engine(raw, mode, target_lang)
                    st.markdown(f"<div class='result-box'>{res}</div>", unsafe_allow_html=True)
                    st.download_button("İndir", res, "sonuc.txt")
                else: st.error("Okunamadı.")

# --- 4. WEB ---
with tab_web:
    url = st.text_input("URL")
    if st.button("Analiz") and url:
        with st.spinner("..."):
            try:
                h = {'User-Agent': 'Mozilla/5.0'}
                soup = BeautifulSoup(requests.get(url, headers=h, timeout=10).content, 'html.parser')
                raw = " ".join([p.get_text() for p in soup.find_all(['p', 'h1'])])[:10000]
                res = ai_engine(raw, "summarize", target_lang)
                st.markdown(f"<div class='result-box'>{res}</div>", unsafe_allow_html=True)
                st.download_button("İndir", res, "web.txt")
            except: st.error("Hata.")

st.divider()
