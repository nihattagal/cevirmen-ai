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
st.set_page_config(
    page_title="LinguaFlow AI",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS TASARIM (Premium His) ---
st.markdown("""
    <style>
    /* Arkaplan ve Font */
    .stApp { background-color: #f8f9fa; font-family: 'Inter', sans-serif; }
    
    /* Başlık */
    .header-logo { 
        font-size: 2.2rem; font-weight: 800; color: #0F2B46; 
        text-align: center; margin-bottom: 5px; letter-spacing: -1px;
    }
    .header-sub { text-align: center; color: #666; margin-bottom: 30px; font-size: 0.9rem; }
    
    /* Metin Alanları */
    .stTextArea textarea {
        border: 1px solid #e2e8f0; border-radius: 12px;
        font-size: 1.05rem; height: 250px !important; padding: 15px;
        background: white; box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .stTextArea textarea:focus { border-color: #3182ce; box-shadow: 0 0 0 2px rgba(49,130,206,0.2); }
    
    /* Sonuç Kutusu */
    .result-box {
        background-color: white; border: 1px solid #e2e8f0; border-radius: 12px;
        min-height: 250px; padding: 20px; font-size: 1.05rem; color: #2d3748;
        white-space: pre-wrap; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    
    /* Butonlar */
    div.stButton > button {
        background-color: #0F2B46; color: white; border: none; border-radius: 8px;
        padding: 12px; font-weight: 600; width: 100%; transition: all 0.2s;
    }
    div.stButton > button:hover { background-color: #2c5282; transform: translateY(-1px); }
    
    /* Konferans Kutuları */
    .conf-src { background: #ebf8ff; padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 4px solid #4299e1; color: #2b6cb0; }
    .conf-trg { background: #f0fff4; padding: 15px; border-radius: 10px; border-left: 4px solid #48bb78; color: #2f855a; }

    /* Geçmiş Öğeleri */
    .history-item {
        font-size: 0.85rem; color: #4a5568; padding: 8px; 
        border-bottom: 1px solid #edf2f7; background: white; margin-bottom: 2px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. API BAĞLANTISI ---
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("Lütfen API anahtarınızı Secrets ayarlarından girin.")
    st.stop()

# --- 4. STATE YÖNETİMİ ---
if "history" not in st.session_state: st.session_state.history = []
if "res_text" not in st.session_state: st.session_state.res_text = ""

# --- 5. FONKSİYONLAR ---
def ai_engine(text, task, target_lang="English", tone="Normal"):
    if not text: return ""
    
    if task == "translate":
        sys_msg = f"""
        Sen profesyonel bir tercümansın.
        Hedef Dil: {target_lang}. Ton: {tone}.
        GÖREV: Metni kültürel nüanslara dikkat ederek çevir.
        KURAL: Sadece çeviriyi ver, asla açıklama yapma.
        """
    elif task == "improve":
        sys_msg = "Sen kıdemli bir editörsün. Metni gramer, akıcılık ve stil açısından mükemmelleştir. Dili değiştirme."
    elif task == "summarize":
        sys_msg = f"Sen bir analistsin. Metni {target_lang} dilinde özetle. Önemli noktaları madde madde yaz."

    try:
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": text[:12000]}]
        )
        result = res.choices[0].message.content
        
        # Geçmişe Kayıt
        if task == "translate":
            timestamp = datetime.datetime.now().strftime("%H:%M")
            short = (text[:15] + '..') if len(text) > 15 else text
            st.session_state.history.insert(0, f"[{timestamp}] {short}")
            
        return result
    except Exception as e: return f"Hata: {e}"

def create_audio(text, lang_name):
    # Genişletilmiş Dil Haritası
    code_map = {
        "Türkçe": "tr", "English": "en", "Deutsch": "de", "Français": "fr", 
        "Español": "es", "Italiano": "it", "Português": "pt", "Polski": "pl",
        "Русский": "ru", "العربية": "ar", "中文": "zh", "日本語": "ja"
    }
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
# ARAYÜZ
# ==========================================

# --- YAN MENÜ (AYARLAR & GEÇMİŞ) ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/language.png", width=50)
    st.title("Geçmiş")
    
    if st.session_state.history:
        for item in st.session_state.history[:8]:
            st.markdown(f"<div class='history-item'>{item}</div>", unsafe_allow_html=True)
        
        if st.button("🗑️ Temizle", type="secondary"):
            st.session_state.history = []
            st.rerun()
    else:
        st.caption("İşlem geçmişi boş.")
    
    st.divider()
    st.info("💡 **İpucu:** Konferans modunda mikrofon 30 saniyeye kadar sessizliği bekler.")

# --- ÜST BAŞLIK ---
st.markdown('<div class="header-logo">LinguaFlow AI</div><div class="header-sub">Global Çeviri ve Analiz Platformu</div>', unsafe_allow_html=True)

# --- SEKMELER ---
tab_text, tab_conf, tab_files, tab_web = st.tabs(["📝 Metin Çeviri", "🎙️ Konferans (Canlı)", "📂 Dosya & PDF", "🔗 Web Analiz"])

# --- GLOBAL DİL LİSTESİ ---
LANG_OPTIONS = ["English", "Türkçe", "Deutsch", "Français", "Español", "Italiano", "Português", "Polski", "Русский", "العربية", "中文", "日本語"]

# --- 1. METİN SEKMESİ ---
with tab_text:
    c1, c2, c3 = st.columns([3, 1, 3])
    with c1: st.markdown("**:blue[Kaynak] (Otomatik Algılanır)**")
    with c3: target_lang = st.selectbox("Hedef Dil", LANG_OPTIONS, label_visibility="collapsed")

    col_in, col_out = st.columns(2)
    with col_in:
        input_text = st.text_area("Giriş", height=250, placeholder="Metni buraya yazın...", label_visibility="collapsed")
        
        b1, b2, b3 = st.columns([2, 2, 1])
        with b1:
            if st.button("Çevir ➔"):
                if input_text:
                    with st.spinner("Çevriliyor..."):
                        st.session_state.res_text = ai_engine(input_text, "translate", target_lang)
                        st.toast("Çeviri Tamamlandı!", icon="✅")
        with b2:
            if st.button("✨ Düzelt (Write)"):
                if input_text:
                    with st.spinner("İyileştiriliyor..."):
                        st.session_state.res_text = ai_engine(input_text, "improve")
                        st.toast("Metin İyileştirildi!", icon="✨")
        with b3:
            tone = st.selectbox("Ton", ["Normal", "Resmi", "Samimi"], label_visibility="collapsed")

    with col_out:
        res = st.session_state.res_text
        st.markdown(f"""<div class="result-box">{res if res else '<span style="color:#aaa;">Sonuç burada görünecek...</span>'}</div>""", unsafe_allow_html=True)
        
        if res:
            st.write("")
            ca, cc = st.columns([1, 4])
            with ca:
                aud = create_audio(res, target_lang)
                if aud: st.audio(aud, format="audio/mp3")
            with cc:
                st.code(res, language=None)

# --- 2. KONFERANS SEKMESİ ---
with tab_conf:
    st.success("🎙️ **Canlı Dinleme Modu:** Toplantıları veya ortam konuşmalarını anlık olarak çevirir.")
    
    c_conf1, c_conf2 = st.columns([1, 3])
    with c_conf1:
        conf_target = st.selectbox("Çeviri Dili", LANG_OPTIONS, key="conf_t")
        st.write("")
        # Büyük Buton
        audio_conf = audio_recorder(text="🔴 BAŞLAT / DURDUR", icon_size="2x", recording_color="#e53e3e", pause_threshold=30.0)
    
    with c_conf2:
        if audio_conf:
            with st.spinner("Ses analiz ediliyor..."):
                try:
                    conf_text = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(audio_conf)), model="whisper-large-v3").text
                    conf_trans = ai_engine(conf_text, "translate", target_lang=conf_target)
                    
                    st.markdown(f"**🗣️ Duyulan:**\n<div class='conf-src'>{conf_text}</div>", unsafe_allow_html=True)
                    st.markdown(f"**🤖 Çeviri:**\n<div class='conf-trg'>{conf_trans}</div>", unsafe_allow_html=True)
                    
                    st.toast("Ses Çevrildi!", icon="🎙️")
                    
                    d1, d2 = st.columns(2)
                    with d1: st.download_button("📥 Orijinal", conf_text, "orijinal.txt")
                    with d2: st.download_button("📥 Çeviri", conf_trans, "ceviri.txt")
                except: st.error("Ses anlaşılamadı.")
        else:
            st.info("Mikrofona basıp konuşmaya başlayın. Sustuğunuzda veya durdurduğunuzda çeviri başlar.")

# --- 3. DOSYA SEKMESİ ---
with tab_files:
    st.markdown("#### 📂 Dosya Yükle (PDF, MP3, WAV)")
    u_file = st.file_uploader("", type=['pdf', 'mp3', 'wav', 'm4a'], label_visibility="collapsed")
    
    if u_file:
        ftype = "Belge" if u_file.name.endswith('.pdf') else "Ses"
        col_f1, col_f2 = st.columns(2)
        
        with col_f1:
            st.info(f"Dosya: {u_file.name}")
            if ftype == "Ses": st.audio(u_file)
            f_target = st.selectbox("Hedef Dil", LANG_OPTIONS, key="f_tgt")
            
            if st.button(f"{ftype} Analiz Et"):
                with st.spinner("İşleniyor..."):
                    raw = local_read_file(u_file)
                    if raw and len(raw) > 10:
                        mode = "translate" if len(raw) < 3000 else "summarize"
                        st.session_state.f_res = ai_engine(raw, mode, f_target)
                        st.toast("Dosya İşlendi!", icon="📂")
                    else: st.error("Dosya okunamadı.")

        with col_f2:
            if "f_res" in st.session_state:
                st.success("Sonuç:")
                st.markdown(f"<div class='result-box'>{st.session_state.f_res}</div>", unsafe_allow_html=True)
                st.download_button("İndir (TXT)", st.session_state.f_res, "dosya_sonuc.txt")

# --- 4. WEB SEKMESİ ---
with tab_web:
    w_url = st.text_input("Web Sitesi Adresi (URL)", placeholder="https://...")
    w_target = st.selectbox("Rapor Dili", LANG_OPTIONS, key="w_tgt")
    
    if st.button("Siteyi Oku ve Özetle") and w_url:
        with st.spinner("Site okunuyor..."):
            try:
                h = {'User-Agent': 'Mozilla/5.0'}
                soup = BeautifulSoup(requests.get(w_url, headers=h, timeout=10).content, 'html.parser')
                raw = " ".join([p.get_text() for p in soup.find_all(['p', 'h1', 'h2'])])[:10000]
                
                web_res = ai_engine(raw, "summarize", w_target)
                st.success("Site Analizi:")
                st.markdown(f"<div class='result-box'>{web_res}</div>", unsafe_allow_html=True)
                st.toast("Site Analiz Edildi!", icon="🌐")
            except: st.error("Siteye erişilemedi.")

# --- ALT BİLGİ (KULLANIM KILAVUZU) ---
st.divider()
with st.expander("ℹ️ Nasıl Kullanılır? (Yardım)"):
    st.markdown("""
    - **📝 Metin:** Sol kutuya yazın, 'Çevir'e basın. Gramer düzeltmek için 'Düzelt'i kullanın.
    - **🎙️ Konferans:** Toplantılarda mikrofonu açın. Siz durdurana kadar dinler ve sonra çevirir.
    - **📂 Dosya:** PDF belgelerini özetlemek veya ses kayıtlarını çevirmek için yükleyin.
    - **🔗 Web:** Bir haber sitesinin linkini yapıştırın, AI size özetini çıkarsın.
    """)
