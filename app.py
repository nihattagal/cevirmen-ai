import streamlit as st
from groq import Groq
from audio_recorder_streamlit import audio_recorder
from gtts import gTTS
import io
import requests
from bs4 import BeautifulSoup
import PyPDF2

# --- 1. SAYFA VE GENEL AYARLAR ---
st.set_page_config(
    page_title="LinguaFlow AI",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. CSS İLE MODERN TASARIM ---
st.markdown("""
    <style>
    /* Genel Font ve Arkaplan */
    .stApp {
        background-color: #ffffff;
    }
    
    /* Hero Section (Başlık Alanı) */
    .hero-container {
        text-align: center;
        padding: 40px 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 0 0 30px 30px;
        margin-bottom: 30px;
        box-shadow: 0 10px 20px rgba(0,0,0,0.1);
    }
    .hero-title {
        font-size: 3.5rem;
        font-weight: 800;
        margin-bottom: 10px;
    }
    .hero-subtitle {
        font-size: 1.2rem;
        opacity: 0.9;
        font-weight: 300;
    }

    /* Kart Tasarımları (Butonlar) */
    div.stButton > button {
        width: 100%;
        height: 200px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        background: white;
        border: 1px solid #eee;
        border-radius: 20px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        transition: all 0.3s ease;
        color: #444;
    }
    div.stButton > button:hover {
        transform: translateY(-8px);
        box-shadow: 0 15px 30px rgba(0,0,0,0.15);
        border-color: #764ba2;
        color: #764ba2;
    }
    div.stButton > button p {
        font-size: 1.1rem;
        font-weight: 600;
    }
    
    /* Geri Dön Butonu */
    .back-btn div.stButton > button {
        height: auto;
        width: auto;
        padding: 8px 20px;
        background: #f0f2f6;
        border: none;
        color: #333;
        font-size: 0.9rem;
    }

    /* Sohbet Balonları */
    .chat-row { padding: 15px; border-radius: 15px; margin-bottom: 10px; line-height: 1.5; }
    .source-box { background: #eef2ff; border-left: 5px solid #667eea; }
    .target-box { background: #fdf2f8; border-right: 5px solid #ed64a6; text-align: right; }
    
    </style>
""", unsafe_allow_html=True)

# --- 3. SESSİZ API BAĞLANTISI ---
# Kullanıcıya asla sorma, arkada hallet.
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    # Eğer geliştirici anahtarı koymadıysa nazik bir uyarı (Sadece admin görür)
    st.error("Sistem Bakımda (API Key Hatası). Lütfen yönetici ile iletişime geçin.")
    st.stop()

# --- 4. STATE VE DİL YÖNETİMİ ---
if "page" not in st.session_state: st.session_state.page = "home"
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "app_lang" not in st.session_state: st.session_state.app_lang = "Türkçe"

# Dil Paketi (Tüm metinler burada)
TEXTS = {
    "Türkçe": {
        "hero_title": "LinguaFlow AI",
        "hero_sub": "Sınırları Kaldıran Yapay Zeka İletişim Merkezi",
        "card_1": "🗣️\n\nKARŞILIKLI SOHBET\nYabancılarla anlık konuşma",
        "card_2": "🎙️\n\nKONFERANS MODU\nToplantı ve ortam çevirisi",
        "card_3": "📂\n\nDOSYA ÇEVİRİ\nSes kayıtlarını yükle ve çevir",
        "card_4": "📄\n\nBELGE ASİSTANI\nPDF oku, özetle ve sor",
        "card_5": "🔗\n\nWEB ANALİZ\nLink ver, siteyi özetlesin",
        "back": "⬅️ Ana Ekrana Dön",
        "settings": "⚙️ Ayarlar",
        "clear": "🗑️ Temizle",
        "download": "📥 İndir",
        "processing": "İşleniyor...",
        "listening": "Dinleniyor...",
        "analyzing": "Analiz ediliyor...",
        "mic_me": "BEN (Konuş)",
        "mic_you": "KARŞI TARAF (Konuş)",
        "target_lang": "Hedef Dil",
        "tone": "Ton / Üslup",
    },
    "English": {
        "hero_title": "LinguaFlow AI",
        "hero_sub": "AI Powered Borderless Communication Hub",
        "card_1": "🗣️\n\nDUAL CHAT\nTalk with anyone instantly",
        "card_2": "🎙️\n\nCONFERENCE MODE\nMeeting & Ambient translation",
        "card_3": "📂\n\nFILE TRANSLATE\nUpload audio and translate",
        "card_4": "📄\n\nDOC ASSISTANT\nRead PDF, summarize & ask",
        "card_5": "🔗\n\nWEB ANALYZER\nPaste URL, get insights",
        "back": "⬅️ Back to Home",
        "settings": "⚙️ Settings",
        "clear": "🗑️ Clear",
        "download": "📥 Download",
        "processing": "Processing...",
        "listening": "Listening...",
        "analyzing": "Analyzing...",
        "mic_me": "ME (Speak)",
        "mic_you": "GUEST (Speak)",
        "target_lang": "Target Language",
        "tone": "Tone / Style",
    }
}

T = TEXTS[st.session_state.app_lang] # Aktif dil değişkeni

# --- 5. FONKSİYONLAR (MOTOR) ---
def local_read_pdf(file):
    reader = PyPDF2.PdfReader(file)
    return "".join([page.extract_text() for page in reader.pages])

def local_read_web(url):
    try:
        h = {'User-Agent': 'Mozilla/5.0'}
        soup = BeautifulSoup(requests.get(url, headers=h, timeout=10).content, 'html.parser')
        return " ".join([p.get_text() for p in soup.find_all(['p', 'h1', 'h2'])])
    except: return None

def get_ai_response(text, target, tone, task_type="translate"):
    if task_type == "translate":
        sys = f"Sen profesyonel tercümansın. Hedef: {target}. Ton: {tone}. Sadece çeviriyi ver."
    else:
        sys = f"Sen bir asistansın. Metni analiz et. Dil: {target}. Çıktı: Özet, Ana Fikirler, Görevler."
    
    try:
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys}, {"role": "user", "content": text}]
        )
        return res.choices[0].message.content
    except Exception as e: return f"Hata: {e}"

def create_voice(text, lang_code):
    try:
        fp = io.BytesIO()
        gTTS(text=text, lang=lang_code, slow=False).write_to_fp(fp)
        return fp.getvalue()
    except: return None

# ==========================================
# EKRANLAR (VIEWS)
# ==========================================

# --- 1. GİRİŞ EKRANI (LANDING PAGE) ---
def show_home():
    # Dil Seçici (Sağ Üst)
    c1, c2 = st.columns([9, 1])
    with c2:
        sel_lang = st.selectbox("Language", ["Türkçe", "English"], label_visibility="collapsed")
        if sel_lang != st.session_state.app_lang:
            st.session_state.app_lang = sel_lang
            st.rerun()

    # Hero Section
    st.markdown(f"""
    <div class="hero-container">
        <div class="hero-title">{T['hero_title']}</div>
        <div class="hero-subtitle">{T['hero_sub']}</div>
    </div>
    """, unsafe_allow_html=True)

    # Menü Kartları (Grid)
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button(T["card_1"], use_container_width=True): st.session_state.page = "chat"; st.rerun()
    with col2:
        if st.button(T["card_2"], use_container_width=True): st.session_state.page = "conf"; st.rerun()
    with col3:
        if st.button(T["card_3"], use_container_width=True): st.session_state.page = "file"; st.rerun()
    
    c_spacer, c4, c5, c_spacer2 = st.columns([0.5, 1, 1, 0.5])
    with c4:
        if st.button(T["card_4"], use_container_width=True): st.session_state.page = "doc"; st.rerun()
    with c5:
        if st.button(T["card_5"], use_container_width=True): st.session_state.page = "web"; st.rerun()

# --- 2. SOHBET MODU ---
def show_chat():
    # Geri Dön & Sidebar
    st.markdown('<div class="back-btn">', unsafe_allow_html=True)
    if st.button(T["back"]): st.session_state.page = "home"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    with st.sidebar:
        st.header(T["settings"])
        # Dil Listesi
        langs = ["English", "Türkçe", "Deutsch", "Français", "Español", "Russian", "Arabic", "Chinese"]
        my_lang = st.selectbox("Ben / Me", langs, index=1 if st.session_state.app_lang=="Türkçe" else 0)
        target_lang = st.selectbox("Misafir / Guest", langs, index=0 if st.session_state.app_lang=="Türkçe" else 1)
        tone = st.select_slider(T["tone"], ["Resmi", "Normal", "Samimi"], value="Normal")
        
        if st.button(T["clear"], type="primary"): st.session_state.chat_history = []; st.rerun()
        
        if st.session_state.chat_history:
            log = "\n".join([f"{m['src']} -> {m['trg']}" for m in st.session_state.chat_history])
            st.download_button(T["download"], log, "chat.txt")

    # Dil Kodları
    lang_map = {"English": "en", "Türkçe": "tr", "Deutsch": "de", "Français": "fr", "Español": "es", "Russian": "ru", "Arabic": "ar", "Chinese": "zh"}

    # Arayüz
    c1, c2 = st.columns(2)
    with c1:
        st.info(f"👤 {my_lang}")
        a1 = audio_recorder(text="", icon_size="3x", key="m1", recording_color="#667eea", neutral_color="#dfe4ea")
        if a1:
            with st.spinner(T["processing"]):
                txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(a1)), model="whisper-large-v3").text
                res = get_ai_response(txt, target_lang, tone)
                aud = create_voice(res, lang_map[target_lang])
                st.session_state.chat_history.append({"src": txt, "trg": res, "dir": "me", "audio": aud})

    with c2:
        st.warning(f"👤 {target_lang}")
        a2 = audio_recorder(text="", icon_size="3x", key="m2", recording_color="#ed64a6", neutral_color="#dfe4ea")
        if a2:
            with st.spinner(T["processing"]):
                txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(a2)), model="whisper-large-v3").text
                res = get_ai_response(txt, my_lang, tone)
                aud = create_voice(res, lang_map[my_lang])
                st.session_state.chat_history.append({"src": txt, "trg": res, "dir": "you", "audio": aud})

    # Akış
    st.divider()
    for i, m in enumerate(reversed(st.session_state.chat_history)):
        align = "source-box" if m["dir"] == "me" else "target-box"
        icon = "🗣️" if m["dir"] == "me" else "🤖"
        
        st.markdown(f"""
        <div class="chat-row {align}">
            <small>{icon} {m['src']}</small><br>
            <strong style="font-size:1.1em">{m['trg']}</strong>
        </div>
        """, unsafe_allow_html=True)
        
        if m["audio"]:
            c_aud, c_dl = st.columns([4,1])
            with c_aud: st.audio(m["audio"], format="audio/mp3")
            with c_dl: st.download_button("⬇", m["audio"], f"audio_{i}.mp3", "audio/mp3", key=f"dl_{i}")

# --- MOD 2: KONFERANS ---
def show_conf():
    st.markdown('<div class="back-btn">', unsafe_allow_html=True)
    if st.button(T["back"]): st.session_state.page = "home"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    with st.sidebar:
        target = st.selectbox(T["target_lang"], ["Türkçe", "English", "Deutsch", "Français"])
        tone = st.selectbox(T["tone"], ["Normal", "Özetleyerek", "Resmi"])
        if st.button("Rapor Oluştur"):
            full = "\n".join([m['trg'] for m in st.session_state.chat_history])
            st.session_state.summary = get_analysis(full, target)

    st.subheader(f"🎙️ {T['card_2'].splitlines()[2]}")
    
    audio = audio_recorder(text="🔴 REC / STOP", icon_size="4x", recording_color="red", pause_threshold=300.0)
    if audio:
        with st.spinner(T["processing"]):
            txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(audio)), model="whisper-large-v3").text
            res = get_ai_response(txt, target, tone)
            st.session_state.chat_history.append({"src": txt, "trg": res})
    
    if "summary" in st.session_state:
        st.info(st.session_state.summary)
        st.download_button(T["download"], st.session_state.summary, "report.txt")
        if st.button("Kapat"): del st.session_state.summary; st.rerun()

    st.divider()
    for m in reversed(st.session_state.chat_history):
        st.success(f"**{m['trg']}**")
        st.caption(f"Kaynak: {m['src']}")

# --- MOD 3, 4, 5 (ORTAK YAPI) ---
def show_files_web_doc(mode):
    st.markdown('<div class="back-btn">', unsafe_allow_html=True)
    if st.button(T["back"]): st.session_state.page = "home"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    with st.sidebar:
        target = st.selectbox(T["target_lang"], ["Türkçe", "English", "Deutsch"])
    
    if mode == "file":
        st.subheader("📂 Dosya Çeviri")
        f = st.file_uploader("MP3/WAV", type=['mp3','wav'])
        if f and st.button("Başlat"):
            with st.spinner(T["processing"]):
                txt = client.audio.transcriptions.create(file=("a.wav", f), model="whisper-large-v3").text
                res = get_ai_response(txt, target, "Normal")
                st.success(res)
                st.download_button(T["download"], res, "transcription.txt")

    elif mode == "doc":
        st.subheader("📄 Belge Asistanı")
        f = st.file_uploader("PDF", type=['pdf'])
        if f and st.button("Analiz Et"):
            with st.spinner(T["analyzing"]):
                txt = local_read_pdf(f)
                res = get_analysis(txt, target)
                st.markdown(res)
                st.download_button(T["download"], res, "summary.txt")

    elif mode == "web":
        st.subheader("🔗 Web Analiz")
        url = st.text_input("URL")
        if url and st.button("Analiz"):
            with st.spinner(T["analyzing"]):
                txt = local_read_web(url)
                if txt:
                    res = get_analysis(txt, target)
                    st.markdown(res)
                    st.download_button(T["download"], res, "analysis.txt")
                else: st.error("Site okunamadı.")

# --- YÖNLENDİRME ---
if st.session_state.page == "home": show_home()
elif st.session_state.page == "chat": show_chat()
elif st.session_state.page == "conf": show_conf()
elif st.session_state.page == "file": show_files_web_doc("file")
elif st.session_state.page == "doc": show_files_web_doc("doc")
elif st.session_state.page == "web": show_files_web_doc("web")
