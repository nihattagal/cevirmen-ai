import streamlit as st
from groq import Groq
from audio_recorder_streamlit import audio_recorder
from gtts import gTTS
import io
import requests
from bs4 import BeautifulSoup
import PyPDF2
import datetime

# --- 1. GENEL AYARLAR ---
st.set_page_config(page_title="LinguaFlow AI", page_icon="🌐", layout="wide")

# --- 2. CSS TASARIM (MOBİL UYUMLU & DEEPL TARZI) ---
st.markdown("""
    <style>
    /* Arkaplan */
    .stApp { background-color: #F3F5F7; font-family: 'Segoe UI', sans-serif; }
    
    /* Başlık */
    .header-logo { 
        font-size: 1.8rem; font-weight: 800; color: #0F2B46; 
        margin-bottom: 10px; border-bottom: 2px solid #e0e0e0; padding-bottom: 10px;
    }
    
    /* Metin Alanları */
    .stTextArea textarea {
        background-color: #ffffff; border: 1px solid #ccc; border-radius: 8px;
        font-size: 1rem; height: 200px !important; padding: 10px;
    }
    .stTextArea textarea:focus { border-color: #4E89E8; box-shadow: 0 0 0 1px #4E89E8; }
    
    /* Sonuç Kutusu */
    .result-box {
        background-color: #ffffff; border: 1px solid #ccc; border-radius: 8px;
        min-height: 200px; padding: 15px; font-size: 1rem; color: #0F2B46;
        white-space: pre-wrap; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    /* Butonlar (Mobil Dostu) */
    div.stButton > button {
        background-color: #0F2B46; color: white; border: none; border-radius: 8px;
        padding: 12px; font-weight: 600; transition: 0.2s; width: 100%;
        min-height: 50px; /* Mobilde parmakla basmak için */
    }
    div.stButton > button:hover { background-color: #264B75; }
    
    /* Konferans Modu Kutuları */
    .conf-row { display: flex; gap: 10px; margin-bottom: 10px; }
    .conf-src { background: #e3f2fd; padding: 10px; border-radius: 8px; flex: 1; color: #0d47a1; font-size: 0.9rem; }
    .conf-trg { background: #f3e5f5; padding: 10px; border-radius: 8px; flex: 1; color: #4a148c; font-size: 0.9rem; font-weight: bold; }

    /* Geçmiş Listesi (Sidebar) */
    .history-item {
        padding: 8px; margin-bottom: 5px; background: white; border-radius: 5px;
        font-size: 0.85rem; border-left: 3px solid #0F2B46; color: #555;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. API BAĞLANTISI ---
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("Sistem Hatası: API Anahtarı bulunamadı.")
    st.stop()

# --- 4. STATE VE HAFIZA ---
if "history" not in st.session_state: st.session_state.history = []
if "res_text" not in st.session_state: st.session_state.res_text = ""

# --- 5. FONKSİYONLAR ---
def ai_engine(text, task, target_lang="English", tone="Normal"):
    if not text: return ""
    
    if task == "translate":
        sys_msg = f"""
        Sen profesyonel bir tercümansın.
        Hedef: {target_lang}. Ton: {tone}.
        GÖREV: Metni çevir. Sadece çeviriyi ver.
        """
    elif task == "improve":
        sys_msg = "Sen bir editörsün. Metni gramer ve stil açısından düzelt. Dili değiştirme."
    
    try:
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": text[:10000]}]
        )
        result = res.choices[0].message.content
        
        # Geçmişe Ekle (Sadece çeviri işlemlerini)
        if task == "translate":
            timestamp = datetime.datetime.now().strftime("%H:%M")
            short_src = (text[:20] + '..') if len(text) > 20 else text
            short_res = (result[:20] + '..') if len(result) > 20 else result
            st.session_state.history.insert(0, f"[{timestamp}] {short_src} ➔ {short_res}")
            
        return result
    except Exception as e: return f"Hata: {e}"

def create_audio(text, lang_name):
    code_map = {"Türkçe": "tr", "İngilizce": "en", "Almanca": "de", "Fransızca": "fr", "İspanyolca": "es", "Rusça": "ru", "Arapça": "ar", "Çince": "zh"}
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

# ==========================================
# ARAYÜZ (UI)
# ==========================================

# --- KENAR ÇUBUĞU (GEÇMİŞ) ---
with st.sidebar:
    st.markdown("### 🕒 Geçmiş İşlemler")
    if st.session_state.history:
        for item in st.session_state.history[:10]: # Son 10 işlem
            st.markdown(f"<div class='history-item'>{item}</div>", unsafe_allow_html=True)
        
        if st.button("🗑️ Geçmişi Temizle"):
            st.session_state.history = []
            st.rerun()
    else:
        st.info("Henüz çeviri yapılmadı.")
    
    st.divider()
    st.caption("LinguaFlow AI v5.0")

# --- ANA EKRAN ---
st.markdown('<div class="header-logo">LinguaFlow AI</div>', unsafe_allow_html=True)

# Sekmeler
tab_text, tab_conf, tab_files, tab_web = st.tabs(["📝 Metin", "🎙️ Ortam (Konferans)", "📂 Dosya", "🔗 Web"])

# --- 1. SEKME: METİN ÇEVİRİ ---
with tab_text:
    c1, c2, c3 = st.columns([3, 1, 3])
    with c1: st.markdown("**Kaynak (Otomatik)**")
    with c3: target_lang = st.selectbox("Hedef Dil", ["English", "Turkish", "German", "French", "Spanish", "Russian", "Arabic"], label_visibility="collapsed")

    col_in, col_out = st.columns(2)
    with col_in:
        input_text = st.text_area("Giriş", height=200, placeholder="Yazın veya yapıştırın...", label_visibility="collapsed")
        
        b1, b2 = st.columns([1, 1])
        with b1:
            if st.button("Çevir ➔", type="primary"):
                if input_text:
                    with st.spinner("Çevriliyor..."):
                        st.session_state.res_text = ai_engine(input_text, "translate", target_lang)
        with b2:
            if st.button("✨ Düzelt"):
                if input_text:
                    with st.spinner("Düzenleniyor..."):
                        st.session_state.res_text = ai_engine(input_text, "improve")

    with col_out:
        res = st.session_state.res_text
        st.markdown(f"""<div class="result-box">{res if res else '<span style="color:#aaa;">...</span>'}</div>""", unsafe_allow_html=True)
        
        if res:
            st.write("") # Boşluk
            ca, cc = st.columns([1, 4])
            with ca:
                aud = create_audio(res, target_lang)
                if aud: st.audio(aud, format="audio/mp3")
            with cc:
                st.code(res, language=None)

# --- 2. SEKME: ORTAM DİNLEME ---
with tab_conf:
    st.info("🎙️ Toplantı veya ortam dinleme modu. Konuşmalar bittiğinde çevirir.")
    
    c_conf1, c_conf2 = st.columns([1, 3])
    with c_conf1:
        conf_target = st.selectbox("Çeviri Dili", ["Türkçe", "İngilizce", "Almanca"], key="conf_t")
        # Uzun süreli dinleme
        audio_conf = audio_recorder(text="🔴 BAŞLAT / DURDUR", icon_size="2x", recording_color="#d32f2f", pause_threshold=20.0)
    
    with c_conf2:
        if audio_conf:
            with st.spinner("Analiz ediliyor..."):
                try:
                    # 1. STT
                    conf_text = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(audio_conf)), model="whisper-large-v3").text
                    # 2. Translate
                    conf_trans = ai_engine(conf_text, "translate", target_lang=conf_target)
                    
                    # 3. Gösterim
                    st.markdown(f"""
                    <div class="conf-row">
                        <div class="conf-src">🗣️ {conf_text}</div>
                        <div class="conf-trg">🤖 {conf_trans}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.download_button("📥 İndir (TXT)", f"Kaynak: {conf_text}\nÇeviri: {conf_trans}", "toplanti.txt")
                except: st.error("Ses alınamadı.")

# --- 3. SEKME: DOSYA ---
with tab_files:
    u_file = st.file_uploader("Dosya (PDF, MP3)", type=['pdf', 'mp3', 'wav', 'm4a'])
    if u_file:
        ftype = "Belge" if u_file.name.endswith('.pdf') else "Ses"
        
        c_f1, c_f2 = st.columns(2)
        with c_f1:
            st.info(f"Dosya: {u_file.name}")
            f_target = st.selectbox("Dil", ["Türkçe", "İngilizce", "Almanca"], key="f_tgt")
            
            if st.button("Analiz Et"):
                with st.spinner("İşleniyor..."):
                    raw = local_read_file(u_file)
                    if raw:
                        st.session_state.f_res = ai_engine(raw, "translate" if len(raw)<3000 else "summarize", f_target)
                    else: st.error("Dosya okunamadı.")

        with c_f2:
            if "f_res" in st.session_state:
                st.success("Sonuç:")
                st.markdown(f"<div class='result-box'>{st.session_state.f_res}</div>", unsafe_allow_html=True)
                st.download_button("İndir", st.session_state.f_res, "dosya.txt")

# --- 4. SEKME: WEB ---
with tab_web:
    w_url = st.text_input("Web Sitesi URL")
    if st.button("Siteyi Oku") and w_url:
        with st.spinner("Siteye bağlanılıyor..."):
            try:
                h = {'User-Agent': 'Mozilla/5.0'}
                soup = BeautifulSoup(requests.get(w_url, headers=h, timeout=10).content, 'html.parser')
                raw = " ".join([p.get_text() for p in soup.find_all(['p', 'h1', 'h2'])])[:10000]
                
                res = ai_engine(raw, "summarize", "Türkçe")
                st.markdown(f"<div class='result-box'>{res}</div>", unsafe_allow_html=True)
            except: st.error("Site okunamadı.")
