import streamlit as st
from groq import Groq
from audio_recorder_streamlit import audio_recorder
from gtts import gTTS
import io
import requests
from bs4 import BeautifulSoup
import PyPDF2

# --- 1. GENEL AYARLAR ---
st.set_page_config(page_title="LinguaFlow (DeepL Edition)", page_icon="🌐", layout="wide")

# --- CSS TASARIM (DeepL Benzeri Temiz Arayüz) ---
st.markdown("""
    <style>
    /* Arkaplan ve Fontlar */
    .stApp { background-color: #F7F9FB; }
    
    /* Başlık Alanı */
    .header-container {
        text-align: center; padding: 20px; margin-bottom: 20px;
    }
    .header-title {
        font-size: 2.5rem; font-weight: 800; color: #0F2B46; /* DeepL Laciverti */
    }
    
    /* Metin Kutuları (TextArea) */
    .stTextArea textarea {
        border-radius: 8px;
        border: 1px solid #ddd;
        font-size: 1.1rem;
        height: 200px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .stTextArea textarea:focus {
        border-color: #0F2B46;
        box-shadow: 0 0 0 1px #0F2B46;
    }
    
    /* Sonuç Kutusu */
    .result-box {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 8px;
        border: 1px solid #ddd;
        min-height: 200px;
        font-size: 1.1rem;
        color: #333;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    
    /* Butonlar */
    div.stButton > button {
        background-color: #0F2B46;
        color: white;
        border-radius: 5px;
        font-weight: bold;
        border: none;
        padding: 10px 20px;
        width: 100%;
        transition: 0.3s;
    }
    div.stButton > button:hover {
        background-color: #1A4D7A;
        color: white;
    }
    
    /* Sekme (Tab) Tasarımı */
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: white;
        border-radius: 5px 5px 0 0;
        color: #0F2B46;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #fff;
        border-bottom: 3px solid #0F2B46;
    }
    </style>
""", unsafe_allow_html=True)

# --- API & AYARLAR ---
if "chat_history" not in st.session_state: st.session_state.chat_history = []
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("Sistem Bağlantı Hatası (API Key)")
    st.stop()

# --- FONKSİYONLAR ---
def ai_process(text, task, target_lang="Turkish", tone="Normal"):
    """
    Tüm zeka işlemleri tek fonksiyonda.
    task: 'translate', 'improve', 'summarize'
    """
    if task == "translate":
        prompt = f"""
        Sen dünyanın en iyi tercümanısın (DeepL kalitesinde).
        GÖREV: Aşağıdaki metni {target_lang} diline çevir.
        KURALLAR:
        1. Kaynak dili OTOMATİK algıla.
        2. Ton: {tone}.
        3. Asla açıklama yapma, sadece çeviriyi ver.
        """
    elif task == "improve":
        prompt = f"""
        Sen profesyonel bir editörsün (DeepL Write gibi).
        GÖREV: Aşağıdaki metni dil bilgisi, akıcılık ve stil açısından DÜZELT ve İYİLEŞTİR.
        KURALLAR:
        1. Dili değiştirme (Hangi dildeyse o dilde kalsın).
        2. Sadece düzeltilmiş metni ver.
        """
    elif task == "summarize":
        prompt = f"Sen bir asistansın. Metni {target_lang} dilinde özetle. Maddeler halinde ver."

    try:
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": prompt}, {"role": "user", "content": text}]
        )
        return res.choices[0].message.content
    except Exception as e: return f"Hata: {e}"

def create_audio(text, lang_name):
    # Dil isimlerini kodlara çevir
    code_map = {"Türkçe": "tr", "İngilizce": "en", "Almanca": "de", "Fransızca": "fr", "İspanyolca": "es", "Rusça": "ru", "Arapça": "ar", "Çince": "zh"}
    lang_code = code_map.get(target_lang, "en")
    try:
        fp = io.BytesIO()
        gTTS(text=text, lang=lang_code, slow=False).write_to_fp(fp)
        return fp.getvalue()
    except: return None

def local_read_pdf(file):
    reader = PyPDF2.PdfReader(file)
    return "".join([page.extract_text() for page in reader.pages])

def local_read_web(url):
    try:
        h = {'User-Agent': 'Mozilla/5.0'}
        soup = BeautifulSoup(requests.get(url, headers=h, timeout=10).content, 'html.parser')
        return " ".join([p.get_text() for p in soup.find_all(['p', 'h1'])])[:10000]
    except: return None

# ==========================================
# ARAYÜZ (UI) - DEEPL TARZI
# ==========================================

# Başlık
st.markdown('<div class="header-container"><div class="header-title">LinguaFlow</div><small>AI Powered Translation & Writing Assistant</small></div>', unsafe_allow_html=True)

# Sekmeler (Menü yerine üst sekmeler - Daha modern)
tab_text, tab_files, tab_voice, tab_web = st.tabs(["✏️ Metin Çeviri & Yazım", "📂 Dosya & Belge", "🎙️ Sesli Sohbet", "🔗 Web Analiz"])

# --- 1. SEKME: METİN (DEEPL KLONU) ---
with tab_text:
    col1, col2 = st.columns([1, 1])
    
    # SOL TARA (GİRİŞ)
    with col1:
        st.subheader("Giriş")
        input_text = st.text_area("Buraya yazın veya yapıştırın...", height=250, label_visibility="collapsed")
        
        # Alt Butonlar
        c_btn1, c_btn2 = st.columns(2)
        with c_btn1:
            target_lang = st.selectbox("Hedef Dil", ["İngilizce", "Türkçe", "Almanca", "Fransızca", "İspanyolca", "Rusça", "Arapça", "Çince"])
        with c_btn2:
            tone = st.selectbox("Ton", ["Normal", "Resmi", "Samimi", "Akademik"])

        btn_translate = st.button("Çevir ➔", type="primary")
        btn_improve = st.button("✨ Metni Güzelleştir (DeepL Write)", help="Dil bilgisini düzeltir ve daha profesyonel yazar.")

    # SAĞ TARAF (SONUÇ)
    with col2:
        st.subheader("Sonuç")
        result_placeholder = st.empty()
        
        # İşlem Mantığı
        if btn_translate and input_text:
            with st.spinner("Çevriliyor..."):
                result = ai_process(input_text, "translate", target_lang, tone)
                # Sonucu şık bir kutuda göster
                result_placeholder.markdown(f"<div class='result-box'>{result}</div>", unsafe_allow_html=True)
                
                # Araçlar
                st.divider()
                c_copy, c_audio = st.columns([1, 1])
                with c_copy: st.code(result, language=None) # Kopyalama için
                with c_audio: 
                    audio = create_audio(result, target_lang)
                    if audio: st.audio(audio, format="audio/mp3")

        elif btn_improve and input_text:
            with st.spinner("Metin iyileştiriliyor..."):
                result = ai_process(input_text, "improve")
                result_placeholder.markdown(f"<div class='result-box' style='border-left: 5px solid #F9A825;'>{result}</div>", unsafe_allow_html=True)
                st.code(result, language=None)
        
        else:
            result_placeholder.markdown("<div class='result-box' style='color:#aaa;'>Çeviri veya düzeltme sonucu burada görünecek...</div>", unsafe_allow_html=True)

# --- 2. SEKME: DOSYA & BELGE ---
with tab_files:
    st.info("PDF belgelerini veya Ses dosyalarını yükleyin. AI formatı tanıyıp işlem yapacaktır.")
    
    uploaded_file = st.file_uploader("Dosya Seç (PDF, MP3, WAV)", type=['pdf', 'mp3', 'wav', 'm4a'])
    
    if uploaded_file:
        file_type = uploaded_file.name.split('.')[-1].lower()
        
        # Eğer SES dosyasıysa
        if file_type in ['mp3', 'wav', 'm4a']:
            st.audio(uploaded_file)
            if st.button("Sesi Deşifre Et ve Çevir"):
                with st.spinner("Ses dinleniyor..."):
                    txt = client.audio.transcriptions.create(file=("a.wav", uploaded_file), model="whisper-large-v3").text
                    st.subheader("Orijinal:")
                    st.write(txt)
                    st.divider()
                    trans = ai_process(txt, "translate", target_lang="Türkçe") # Varsayılan Türkçe
                    st.subheader("Çeviri:")
                    st.success(trans)
        
        # Eğer PDF ise
        elif file_type == 'pdf':
            if st.button("Belgeyi Analiz Et"):
                with st.spinner("PDF okunuyor..."):
                    text = local_read_pdf(uploaded_file)
                    summary = ai_process(text, "summarize", target_lang="Türkçe")
                    st.markdown(f"### 📄 Belge Özeti\n{summary}")
                    st.download_button("Özeti İndir", summary, "ozet.txt")

# --- 3. SEKME: SESLİ SOHBET (ESKİ KONFERANS MODU) ---
with tab_voice:
    c_conf, c_set = st.columns([3, 1])
    with c_set:
        v_lang = st.selectbox("Konuşulan Çıktı Dili", ["Türkçe", "İngilizce", "Almanca"])
        
    with c_conf:
        st.write("Mikrofona konuşun, seçili dile çevirip sesli okusun.")
        audio_bytes = audio_recorder(text="Bas-Konuş", icon_size="3x", recording_color="#ef4444", neutral_color="#333")
        
        if audio_bytes:
