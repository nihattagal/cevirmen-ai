import streamlit as st
from groq import Groq
from audio_recorder_streamlit import audio_recorder
from gtts import gTTS
import io
import requests
from bs4 import BeautifulSoup # Web sitelerini okumak için

# --- 1. SAYFA YAPILANDIRMASI ---
st.set_page_config(
    page_title="AI Super Hub",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. CSS TASARIM (TIKLANABİLİR KARTLAR) ---
st.markdown("""
    <style>
    /* Ana Başlık */
    .main-title {
        font-size: 3rem;
        font-weight: 800;
        background: -webkit-linear-gradient(45deg, #FF0080, #7928CA);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 10px;
    }
    .subtitle { text-align: center; color: #666; margin-bottom: 40px; }

    /* KART GÖRÜNÜMLÜ BUTONLAR */
    /* Streamlit butonlarını tamamen değiştiriyoruz */
    div.stButton > button {
        width: 100%;
        height: 180px;
        white-space: pre-wrap; /* Alt satıra geçmeye izin ver */
        background-color: #ffffff;
        color: #333333;
        border: 1px solid #e0e0e0;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        transition: all 0.3s ease;
        font-size: 1.2rem;
    }
    
    /* Mouse üzerine gelince (Hover) */
    div.stButton > button:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 20px rgba(0,0,0,0.15);
        border-color: #7928CA;
        color: #7928CA;
        background-color: #fcfcfc;
    }
    
    /* Geri Dön Butonu için özel stil (Küçük olsun) */
    div.back-btn > button {
        height: auto;
        width: auto;
        padding: 5px 15px;
        font-size: 1rem;
        background-color: #f0f0f0;
    }

    /* Mesaj Kutuları */
    .msg-box { padding: 15px; border-radius: 15px; margin-bottom: 10px; }
    .msg-user { background-color: #e3f2fd; border-left: 5px solid #2196F3; }
    .msg-ai { background-color: #f3e5f5; border-right: 5px solid #9c27b0; text-align: right; }
    </style>
""", unsafe_allow_html=True)

# --- 3. DİL VE METİNLER ---
TEXTS = {
    "Türkçe": {
        "title": "AI Super Hub",
        "sub": "Ses, Metin ve Web Analiz Merkezi",
        "m1": "🗣️\n\nKarşılıklı\nSohbet",
        "m2": "🎙️\n\nSimültane\nKonferans",
        "m3": "📂\n\nSes Dosyası\nAnalizi",
        "m4": "🔗\n\nWeb Sitesi\nÇeviri & Analiz", # YENİ
        "back": "⬅️ Ana Menü",
        "analyze": "Analiz Et",
        "translating": "Çevriliyor...",
        "analyzing": "İçerik çekiliyor ve analiz ediliyor...",
        "url_ph": "https://www.ornek.com",
        "web_title": "Web Sitesi Analizcisi",
        "web_desc": "Bir URL girin, yapay zeka içeriği okusun, özetlesin ve çevirsin.",
        "mic_me": "BEN", "mic_you": "MİSAFİR",
        "err_url": "Lütfen geçerli bir URL girin.",
        "summary_h": "📋 Özet", "trans_h": "🌍 Çeviri",
        "chat_ph": "Sohbet geçmişi...",
    },
    "English": {
        "title": "AI Super Hub",
        "sub": "Voice, Text & Web Analysis Center",
        "m1": "🗣️\n\nDual\nChat",
        "m2": "🎙️\n\nLive\nConference",
        "m3": "📂\n\nAudio File\nAnalysis",
        "m4": "🔗\n\nWeb Page\nTranslate & Analyze", # YENİ
        "back": "⬅️ Main Menu",
        "analyze": "Analyze",
        "translating": "Translating...",
        "analyzing": "Fetching and analyzing content...",
        "url_ph": "https://www.example.com",
        "web_title": "Web Page Analyzer",
        "web_desc": "Enter a URL, AI will read, summarize and translate it.",
        "mic_me": "ME", "mic_you": "GUEST",
        "err_url": "Please enter a valid URL.",
        "summary_h": "📋 Summary", "trans_h": "🌍 Translation",
        "chat_ph": "Chat history...",
    }
}

# --- STATE ---
if "app_lang" not in st.session_state: st.session_state.app_lang = "Türkçe"
if "current_page" not in st.session_state: st.session_state.current_page = "home"
if "chat_history" not in st.session_state: st.session_state.chat_history = []

# --- GROQ ---
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("API Key Eksik!")
    st.stop()

# --- YARDIMCI FONKSİYONLAR ---
def scrape_website(url):
    """Verilen URL'deki metinleri çeker"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Sadece paragrafları ve başlıkları al
        paragraphs = soup.find_all(['p', 'h1', 'h2', 'h3'])
        text = " ".join([p.get_text() for p in paragraphs])
        
        # Çok uzunsa kırp (Token limiti için)
        return text[:6000] 
    except Exception as e:
        return None

def get_ai_response(text, system_p, target_lang):
    prompt = f"{system_p}\nHedef Dil: {target_lang}\nMetin: {text}"
    try:
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}]
        )
        return res.choices[0].message.content
    except: return "Hata."

def create_audio(text, lang="tr"):
    try:
        tts = gTTS(text=text, lang=lang, slow=False)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        return fp.getvalue()
    except: return None

# =========================================================
# SAYFALAR
# =========================================================

def show_home():
    # Dil Seçimi
    c1, c2, c3 = st.columns([1, 6, 1])
    with c3:
        sl = st.selectbox("", ["Türkçe", "English"], label_visibility="collapsed")
        if sl != st.session_state.app_lang:
            st.session_state.app_lang = sl
            st.rerun()

    t = TEXTS[st.session_state.app_lang]
    st.markdown(f'<div class="main-title">{t["title"]}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="subtitle">{t["sub"]}</div>', unsafe_allow_html=True)

    # 4 KARTLI IZGARA MENÜ
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        # Butonun kendisi KART oldu artık
        if st.button(t["m1"], use_container_width=True):
            st.session_state.current_page = "chat"
            st.rerun()
    
    with col2:
        if st.button(t["m2"], use_container_width=True):
            st.session_state.current_page = "conf"
            st.rerun()
            
    with col3:
        if st.button(t["m3"], use_container_width=True):
            st.session_state.current_page = "file"
            st.rerun()

    with col4:
        if st.button(t["m4"], use_container_width=True):
            st.session_state.current_page = "web"
            st.rerun()

# --- MOD 1: SOHBET ---
def show_chat():
    t = TEXTS[st.session_state.app_lang]
    st.markdown('<div class="back-btn">', unsafe_allow_html=True)
    if st.button(t["back"]): st.session_state.current_page = "home"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.header(t["m1"].replace("\n", " "))
    
    # Mikrofonlar
    c1, c2 = st.columns(2)
    with c1:
        st.info(t["mic_me"])
        a1 = audio_recorder(text="", icon_size="3x", key="a1", recording_color="#2196F3")
        if a1: 
            with st.spinner(t["translating"]):
                txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(a1)), model="whisper-large-v3").text
                trans = get_ai_response(txt, "Translate this text.", "English") # Basitleştirildi
                st.session_state.chat_history.append({"u": txt, "a": trans, "dir": "me"})

    with c2:
        st.warning(t["mic_you"])
        a2 = audio_recorder(text="", icon_size="3x", key="a2", recording_color="#9c27b0")
        if a2:
             with st.spinner(t["translating"]):
                txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(a2)), model="whisper-large-v3").text
                trans = get_ai_response(txt, "Translate this text.", "Turkish")
                st.session_state.chat_history.append({"u": txt, "a": trans, "dir": "you"})
    
    # Geçmiş
    for c in reversed(st.session_state.chat_history):
        align = "msg-user" if c["dir"] == "me" else "msg-ai"
        st.markdown(f'<div class="msg-box {align}"><b>{c["u"]}</b><br><i>{c["a"]}</i></div>', unsafe_allow_html=True)

# --- MOD 2: KONFERANS ---
def show_conf():
    t = TEXTS[st.session_state.app_lang]
    st.markdown('<div class="back-btn">', unsafe_allow_html=True)
    if st.button(t["back"]): st.session_state.current_page = "home"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.header(t["m2"].replace("\n", " "))
    st.info("5 dk sessizliğe kadar dinler.")
    
    audio = audio_recorder(text="", icon_size="5x", recording_color="red", pause_threshold=300.0)
    if audio:
        with st.spinner(t["translating"]):
            txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(audio)), model="whisper-large-v3").text
            trans = get_ai_response(txt, "Summarize and translate.", "Turkish")
            st.success(trans)

# --- MOD 3: DOSYA ---
def show_file():
    t = TEXTS[st.session_state.app_lang]
    st.markdown('<div class="back-btn">', unsafe_allow_html=True)
    if st.button(t["back"]): st.session_state.current_page = "home"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.header(t["m3"].replace("\n", " "))
    f = st.file_uploader("MP3/WAV", type=['mp3','wav'])
    if f and st.button(t["analyze"]):
        with st.spinner(t["analyzing"]):
            txt = client.audio.transcriptions.create(file=("a.wav", f), model="whisper-large-v3").text
            res = get_ai_response(txt, "Analyze this audio text.", "Turkish")
            st.info(res)

# --- MOD 4: WEB ANALİZ (YENİ) ---
def show_web():
    t = TEXTS[st.session_state.app_lang]
    
    # Geri Dön
    st.markdown('<div class="back-btn">', unsafe_allow_html=True)
    if st.button(t["back"]): st.session_state.current_page = "home"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.header(f"🔗 {t['web_title']}")
    st.write(t["web_desc"])
    
    # URL Girişi
    url_input = st.text_input("URL:", placeholder=t["url_ph"])
    
    if st.button(t["analyze"], type="primary", use_container_width=True):
        if url_input and "http" in url_input:
            with st.spinner(t["analyzing"]):
                # 1. Siteyi Oku
                web_text = scrape_website(url_input)
                
                if web_text and len(web_text) > 50:
                    # 2. AI'a Gönder
                    system_msg = """
                    Sen bir web analistisin. Verilen metni analiz et.
                    GÖREVLER:
                    1. İçeriğin Özetini Çıkar (3-4 madde).
                    2. Ana fikirleri ve önemli noktaları listele.
                    3. İçeriği Hedef Dile Çevir (Özet olarak).
                    """
                    target = "Turkish" if st.session_state.app_lang == "Türkçe" else "English"
                    
                    analysis = get_ai_response(web_text, system_msg, target)
                    
                    # 3. Sonucu Göster
                    st.success("✅ Analiz Tamamlandı!")
                    st.markdown(f"""
                    <div style="background-color:#f9f9f9; padding:20px; border-radius:10px; border:1px solid #ddd;">
                        {analysis}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 4. Sesli Oku (Opsiyonel)
                    audio_data = create_audio(analysis[:200], "tr") # Sadece başını oku
                    if audio_data: st.audio(audio_data, format="audio/mp3")
                    
                else:
                    st.error("Site içeriği okunamadı veya çok kısa. (Bazı siteler bot korumalı olabilir).")
        else:
            st.warning(t["err_url"])

# --- ROUTER ---
if st.session_state.current_page == "home": show_home()
elif st.session_state.current_page == "chat": show_chat()
elif st.session_state.current_page == "conf": show_conf()
elif st.session_state.current_page == "file": show_file()
elif st.session_state.current_page == "web": show_web()
