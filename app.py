import streamlit as st
from groq import Groq
from audio_recorder_streamlit import audio_recorder
from gtts import gTTS
import io
import datetime

# --- 1. SAYFA YAPILANDIRMASI ---
st.set_page_config(
    page_title="AI Super Translator",
    page_icon="🌐",
    layout="wide", # Geniş ekran modu
    initial_sidebar_state="collapsed"
)

# --- 2. CSS TASARIM (MODERN & KARTLAR) ---
st.markdown("""
    <style>
    /* Ana Başlık */
    .main-title {
        font-size: 3.5rem;
        font-weight: 800;
        background: -webkit-linear-gradient(45deg, #FF0080, #7928CA);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0px;
    }
    .subtitle {
        text-align: center; font-size: 1.2rem; color: #666; margin-bottom: 30px;
    }
    
    /* Kart Tasarımı (Menü Butonları) */
    .card-container {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #ddd;
        text-align: center;
        transition: transform 0.2s;
        height: 200px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }
    .card-container:hover {
        transform: scale(1.03);
        box-shadow: 0 10px 20px rgba(0,0,0,0.1);
        border-color: #7928CA;
    }
    .card-icon { font-size: 3rem; margin-bottom: 10px; }
    .card-title { font-size: 1.5rem; font-weight: bold; color: #333; }
    .card-desc { color: #666; font-size: 0.9rem; }
    
    /* Mesaj Balonları */
    .msg-box { padding: 15px; border-radius: 15px; margin-bottom: 10px; }
    .msg-user { background-color: #e3f2fd; border-left: 5px solid #2196F3; }
    .msg-ai { background-color: #f3e5f5; border-right: 5px solid #9c27b0; text-align: right; }
    
    </style>
""", unsafe_allow_html=True)

# --- 3. DİL PAKETİ (LOCALIZATION) ---
# Uygulama diline göre metinler burada tutulur
TEXTS = {
    "Türkçe": {
        "title": "AI Super Translator",
        "subtitle": "Yapay Zeka Destekli Evrensel İletişim Aracı",
        "mode_1_title": "Karşılıklı Sohbet",
        "mode_1_desc": "Yabancı biriyle masa tenisi oynar gibi karşılıklı konuşun.",
        "mode_2_title": "Simültane Konferans",
        "mode_2_desc": "Toplantıları veya ortamı kesintisiz dinleyin ve çevirin.",
        "mode_3_title": "Dosya Analizi",
        "mode_3_desc": "Ses dosyalarını yükleyin, çevirin ve özetini çıkarın.",
        "back": "⬅️ Ana Menüye Dön",
        "mic_me": "BEN (Konuş)",
        "mic_you": "MİSAFİR (Konuş)",
        "translating": "Çevriliyor...",
        "analyzing": "Analiz ediliyor...",
        "summary_btn": "Toplantı Özeti Çıkar",
        "clear_btn": "Temizle",
        "download_btn": "İndir",
        "settings": "Ayarlar",
        "target_lang": "Hedef Dil",
        "persona": "AI Karakteri",
    },
    "English": {
        "title": "AI Super Translator",
        "subtitle": "AI Powered Universal Communication Tool",
        "mode_1_title": "Dual Chat",
        "mode_1_desc": "Talk back-and-forth like playing ping-pong.",
        "mode_2_title": "Live Conference",
        "mode_2_desc": "Listen and translate meetings continuously.",
        "mode_3_title": "File Analysis",
        "mode_3_desc": "Upload audio files, translate and summarize.",
        "back": "⬅️ Back to Menu",
        "mic_me": "ME (Speak)",
        "mic_you": "GUEST (Speak)",
        "translating": "Translating...",
        "analyzing": "Analyzing...",
        "summary_btn": "Generate Summary",
        "clear_btn": "Clear",
        "download_btn": "Download",
        "settings": "Settings",
        "target_lang": "Target Language",
        "persona": "AI Persona",
    }
}

# --- 4. SESSION STATE YÖNETİMİ ---
if "app_lang" not in st.session_state: st.session_state.app_lang = "Türkçe"
if "current_page" not in st.session_state: st.session_state.current_page = "home"
if "chat_history" not in st.session_state: st.session_state.chat_history = []

# --- 5. GROQ BAĞLANTISI ---
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("API Key Eksik! Lütfen secrets.toml dosyasını kontrol et.")
    st.stop()

# --- YARDIMCI FONKSİYONLAR ---
def get_ai_response(text, role_prompt, target_lang):
    """Llama 3 ile çeviri ve analiz yapar"""
    system_prompt = f"""
    {role_prompt}
    Target Language: {target_lang}.
    TASK: Translate the text and detect sentiment (One word: Happy, Angry, Neutral etc.).
    FORMAT: SENTIMENT ||| TRANSLATION
    """
    try:
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": text}]
        )
        content = res.choices[0].message.content
        if "|||" in content:
            return content.split("|||")
        return "Nötr", content
    except:
        return "Error", "Hata oluştu"

def create_audio(text, lang_code):
    """Metni sese çevirir"""
    try:
        tts = gTTS(text=text, lang=lang_code, slow=False)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        return fp.getvalue()
    except:
        return None

# =========================================================
# SAYFA 1: GİRİŞ VE MENÜ (DASHBOARD)
# =========================================================
def show_home():
    # Dil Seçimi (En Üstte)
    col_lang1, col_lang2, _ = st.columns([1, 1, 4])
    with col_lang1:
        st.write("🌐 Interface Language:")
    with col_lang2:
        selected_lang = st.selectbox("", ["Türkçe", "English"], label_visibility="collapsed")
        if selected_lang != st.session_state.app_lang:
            st.session_state.app_lang = selected_lang
            st.rerun()

    t = TEXTS[st.session_state.app_lang] # Seçili dil paketini al

    st.markdown(f'<div class="main-title">{t["title"]}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="subtitle">{t["subtitle"]}</div>', unsafe_allow_html=True)

    st.divider()

    # KART MENÜSÜ
    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown(f"""
        <div class="card-container">
            <div class="card-icon">🗣️</div>
            <div class="card-title">{t['mode_1_title']}</div>
            <div class="card-desc">{t['mode_1_desc']}</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button(f"Giriş: {t['mode_1_title']}", key="btn1", use_container_width=True):
            st.session_state.current_page = "chat_mode"
            st.rerun()

    with c2:
        st.markdown(f"""
        <div class="card-container">
            <div class="card-icon">🎙️</div>
            <div class="card-title">{t['mode_2_title']}</div>
            <div class="card-desc">{t['mode_2_desc']}</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button(f"Giriş: {t['mode_2_title']}", key="btn2", use_container_width=True):
            st.session_state.current_page = "conf_mode"
            st.rerun()

    with c3:
        st.markdown(f"""
        <div class="card-container">
            <div class="card-icon">📂</div>
            <div class="card-title">{t['mode_3_title']}</div>
            <div class="card-desc">{t['mode_3_desc']}</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button(f"Giriş: {t['mode_3_title']}", key="btn3", use_container_width=True):
            st.session_state.current_page = "file_mode"
            st.rerun()

# =========================================================
# MOD 1: KARŞILIKLI SOHBET (DUAL CHAT)
# =========================================================
def show_chat_mode():
    t = TEXTS[st.session_state.app_lang]
    
    # Üst Bar
    c1, c2 = st.columns([1, 5])
    with c1:
        if st.button(t["back"]):
            st.session_state.current_page = "home"
            st.rerun()
    with c2:
        st.header(f"🗣️ {t['mode_1_title']}")

    # Sidebar Ayarları
    with st.sidebar:
        st.subheader(t["settings"])
        target_lang = st.selectbox(t["target_lang"], ["English", "Turkish", "German", "Spanish", "French", "Russian", "Arabic", "Chinese"])
        persona = st.selectbox(t["persona"], ["Professional", "Friendly", "Kids Mode", "Rude/Mafia", "Knight"])
        
        # Temizle Butonu
        if st.button(t["clear_btn"], type="primary"):
            st.session_state.chat_history = []
            st.rerun()

    # Dil Kodları
    lang_map = {"English": "en", "Turkish": "tr", "German": "de", "Spanish": "es", "French": "fr", "Russian": "ru", "Arabic": "ar", "Chinese": "zh"}
    target_code = lang_map[target_lang]
    
    # Karakter Promptu
    prompts = {
        "Professional": "You are a professional translator.",
        "Friendly": "You are a best friend, use slang.",
        "Kids Mode": "Explain like I am 5 years old.",
        "Rude/Mafia": "You are a mafia boss, be rude.",
        "Knight": "You are a medieval knight, use noble language."
    }
    role_prompt = prompts[persona]

    # Mikrofonlar
    col_me, col_you = st.columns(2)
    with col_me:
        st.info(f"🎤 {t['mic_me']}")
        audio_me = audio_recorder(text="", icon_size="3x", key="rec_me", recording_color="#2196F3", neutral_color="#bbdefb")
        if audio_me:
            with st.spinner(t["translating"]):
                mood, trans = get_ai_response(client.audio.transcriptions.create(file=("a.wav", io.BytesIO(audio_me)), model="whisper-large-v3").text, role_prompt, target_lang)
                audio_data = create_audio(trans, target_code)
                st.session_state.chat_history.append({"dir": "me", "text": trans, "mood": mood, "audio": audio_data})

    with col_you:
        st.warning(f"🎤 {t['mic_you']}")
        audio_you = audio_recorder(text="", icon_size="3x", key="rec_you", recording_color="#9c27b0", neutral_color="#e1bee7")
        if audio_you:
            with st.spinner(t["translating"]):
                # Buraya normalde kaynak dil tespiti gelir ama basitleştirmek için İngilizce varsayalım
                mood, trans = get_ai_response(client.audio.transcriptions.create(file=("a.wav", io.BytesIO(audio_you)), model="whisper-large-v3").text, role_prompt, "Turkish" if target_lang != "Turkish" else "English")
                audio_data = create_audio(trans, "tr") # Varsayılan dönüş Türkçe
                st.session_state.chat_history.append({"dir": "you", "text": trans, "mood": mood, "audio": audio_data})

    # Geçmişi Göster
    st.divider()
    for chat in reversed(st.session_state.chat_history):
        cls = "msg-user" if chat["dir"] == "me" else "msg-ai"
        align = "left" if chat["dir"] == "me" else "right"
        st.markdown(f"""
        <div class="msg-box {cls}">
            <div style="text-align: {align}; font-size: 0.8em; color: #555;">{chat['mood']}</div>
            <div style="text-align: {align}; font-weight: bold; font-size: 1.2em;">{chat['text']}</div>
        </div>
        """, unsafe_allow_html=True)
        if chat["audio"]: st.audio(chat["audio"], format="audio/mp3")

# =========================================================
# MOD 2: KONFERANS (SÜREKLİ DİNLEME)
# =========================================================
def show_conf_mode():
    t = TEXTS[st.session_state.app_lang]
    
    if st.button(t["back"]):
        st.session_state.current_page = "home"
        st.rerun()
    
    st.header(f"🎙️ {t['mode_2_title']}")
    st.info("Bu modda mikrofon siz 'Durdur' diyene kadar kapanmaz (Max 5 dk sessizlik).")

    with st.sidebar:
        target_lang = st.selectbox(t["target_lang"], ["Turkish", "English", "German"])
        if st.button(t["summary_btn"]):
            st.success("Özet çıkarılıyor...")
            # Özet mantığı buraya

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # Pause threshold yüksek (300sn)
        audio = audio_recorder(text="Sürekli Dinle / Bitir", icon_size="5x", recording_color="#FF0000", pause_threshold=300.0)
    
    if audio:
        with st.spinner(t["analyzing"]):
            text = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(audio)), model="whisper-large-v3").text
            _, trans = get_ai_response(text, "You are a simultane translator. Summarize if too long.", target_lang)
            st.markdown(f"### 📝 Çeviri:\n{trans}")
            st.audio(create_audio(trans, "tr"), format="audio/mp3")

# =========================================================
# MOD 3: DOSYA YÜKLEME
# =========================================================
def show_file_mode():
    t = TEXTS[st.session_state.app_lang]
    
    if st.button(t["back"]):
        st.session_state.current_page = "home"
        st.rerun()

    st.header(f"📂 {t['mode_3_title']}")
    
    uploaded_file = st.file_uploader("Ses Dosyası (MP3/WAV)", type=['mp3', 'wav', 'm4a'])
    
    if uploaded_file and st.button("Analiz Et"):
        with st.spinner(t["analyzing"]):
            text = client.audio.transcriptions.create(file=("a.wav", uploaded_file), model="whisper-large-v3").text
            st.subheader("Orijinal Metin:")
            st.write(text)
            
            st.divider()
            
            st.subheader("AI Analizi & Çeviri:")
            _, trans = get_ai_response(text, "Analyze this text, translate it and give a summary.", "Turkish")
            st.info(trans)


# =========================================================
# ANA YÖNLENDİRİCİ (ROUTER)
# =========================================================
if st.session_state.current_page == "home":
    show_home()
elif st.session_state.current_page == "chat_mode":
    show_chat_mode()
elif st.session_state.current_page == "conf_mode":
    show_conf_mode()
elif st.session_state.current_page == "file_mode":
    show_file_mode()
