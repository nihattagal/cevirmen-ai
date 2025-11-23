import streamlit as st
from groq import Groq
from audio_recorder_streamlit import audio_recorder
from gtts import gTTS
import io
import requests
from bs4 import BeautifulSoup
import PyPDF2

# --- 1. GENEL AYARLAR ---
st.set_page_config(page_title="AI Tercüman Pro", page_icon="🌐", layout="wide")

# CSS TASARIM (KARTLAR VE RENKLER)
st.markdown("""
    <style>
    .main-header { font-size: 2.5rem; font-weight: 800; color: #333; text-align: center; margin-bottom: 30px; }
    
    /* Kart Butonlar */
    div.stButton > button {
        width: 100%; height: 130px; font-size: 1.1rem; font-weight: bold;
        border-radius: 15px; border: 1px solid #ddd; background: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); transition: 0.3s;
    }
    div.stButton > button:hover {
        transform: translateY(-5px); border-color: #4B0082; color: #4B0082; background: #f8f9fa;
        box-shadow: 0 8px 15px rgba(0,0,0,0.1);
    }
    /* Geri Dön Butonu */
    .back-area div.stButton > button { height: auto; width: auto; background: #eee; font-size: 1rem; padding: 5px 15px; }
    
    /* Mesaj Balonları */
    .chat-row { padding: 15px; border-radius: 10px; margin-bottom: 8px; }
    .source-box { background: #e3f2fd; border-left: 5px solid #2196F3; }
    .target-box { background: #fbe9e7; border-right: 5px solid #FF5722; text-align: right; }
    </style>
""", unsafe_allow_html=True)

# --- 2. STATE ---
if "page" not in st.session_state: st.session_state.page = "home"
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "app_lang" not in st.session_state: st.session_state.app_lang = "Türkçe"

# --- 3. API ---
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("API Key eksik! Lütfen Secrets ayarlarını yapın.")
    st.stop()

# --- YEREL FONKSİYONLAR (SENİN KAYNAKLARIN) ---
def local_read_pdf(file):
    """PDF dosyasını yerel işlemciyle okur"""
    reader = PyPDF2.PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

def local_read_web(url):
    """Web sitesini yerel işlemciyle okur"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        page = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(page.content, 'html.parser')
        # Sadece metinleri al
        return " ".join([p.get_text() for p in soup.find_all(['p', 'h1', 'h2'])])
    except Exception as e:
        return None

# --- AI FONKSİYONLARI (SADECE BEYİN) ---
def get_translation(text, target_lang, tone, style_prompt=""):
    system_prompt = f"""
    Sen profesyonel bir tercümansın.
    GÖREVİN: Verilen metni {target_lang} diline çevirmek.
    KURALLAR:
    1. Ton: {tone}.
    2. {style_prompt}
    3. Sadece çeviriyi ver. Yorum yapma.
    """
    try:
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": text}]
        )
        return res.choices[0].message.content
    except Exception as e: return f"Hata: {e}"

def get_analysis(text, target_lang):
    prompt = f"Sen bir asistansın. Metni analiz et. Rapor Dili: {target_lang}. ÇIKTI: 1.Özet 2.Ana Fikirler 3.Görevler\nMetin: {text[:15000]}" # Token limiti için kırpma
    res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}])
    return res.choices[0].message.content

def create_voice(text, lang_code):
    try:
        tts = gTTS(text=text, lang=lang_code, slow=False)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        return fp.getvalue()
    except: return None

# ==========================================
# SAYFALAR
# ==========================================

# --- ANA MENÜ ---
def show_home():
    c1, c2 = st.columns([8, 2])
    with c2:
        l = st.selectbox("Arayüz Dili", ["Türkçe", "English"], label_visibility="collapsed")
        if l != st.session_state.app_lang: st.session_state.app_lang = l; st.rerun()
            
    st.markdown('<div class="main-header">🌐 AI Tercüman Pro</div>', unsafe_allow_html=True)
    
    # 5 KARTLI MENÜ
    # İlk satır 3 kart
    c1, c2, c3 = st.columns(3)
    
    if st.session_state.app_lang == "Türkçe":
        titles = ["🗣️ Karşılıklı Sohbet", "🎙️ Simültane Konferans", "📂 Ses Dosyası", "🔗 Web Analiz", "📄 Belge Asistanı"]
    else:
        titles = ["🗣️ Dual Chat", "🎙️ Live Conference", "📂 Audio File", "🔗 Web Reader", "📄 Doc Assistant"]

    with c1: 
        if st.button(titles[0], use_container_width=True): st.session_state.page = "chat"; st.rerun()
    with c2: 
        if st.button(titles[1], use_container_width=True): st.session_state.page = "conf"; st.rerun()
    with c3: 
        if st.button(titles[2], use_container_width=True): st.session_state.page = "file"; st.rerun()
    
    # İkinci satır 2 kart (Ortalanmış)
    c_empty, c4, c5, c_empty2 = st.columns([0.5, 1, 1, 0.5])
    with c4: 
        if st.button(titles[3], use_container_width=True): st.session_state.page = "web"; st.rerun()
    with c5: 
        if st.button(titles[4], use_container_width=True): st.session_state.page = "doc"; st.rerun()

# --- MOD 1: SOHBET ---
def show_chat():
    with st.sidebar:
        if st.button("⬅️ Menüye Dön"): st.session_state.page = "home"; st.rerun()
        st.header("⚙️ Sohbet")
        my_lang = st.selectbox("Benim Dilim", ["Türkçe", "English", "Deutsch"])
        target_lang = st.selectbox("Karşı Taraf", ["English", "Türkçe", "Deutsch", "Français", "Español", "Russian", "Arabic", "Chinese"], index=0)
        tone = st.select_slider("Ton", ["Resmi", "Normal", "Samimi"], value="Normal")
        if st.button("🗑️ Temizle", type="primary"): st.session_state.chat_history = []; st.rerun()

    st.markdown(f"### 🗣️ Sohbet: {my_lang} ↔️ {target_lang}")
    lang_map = {"English": "en", "Türkçe": "tr", "Deutsch": "de", "Français": "fr", "Español": "es", "Russian": "ru", "Arabic": "ar", "Chinese": "zh"}
    
    c1, c2 = st.columns(2)
    with c1:
        st.info(f"🎤 BEN ({my_lang})")
        a1 = audio_recorder(text="", icon_size="3x", key="mic1", recording_color="#2196F3")
        if a1:
            with st.spinner("..."):
                txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(a1)), model="whisper-large-v3").text
                trans = get_translation(txt, target_lang, tone)
                audio = create_voice(trans, lang_map[target_lang])
                st.session_state.chat_history.append({"src": txt, "trg": trans, "dir": "me", "audio": audio})
    with c2:
        st.warning(f"🎤 KARŞI TARAF ({target_lang})")
        a2 = audio_recorder(text="", icon_size="3x", key="mic2", recording_color="#FF5722")
        if a2:
            with st.spinner("..."):
                txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(a2)), model="whisper-large-v3").text
                trans = get_translation(txt, my_lang, tone)
                audio = create_voice(trans, lang_map[my_lang])
                st.session_state.chat_history.append({"src": txt, "trg": trans, "dir": "you", "audio": audio})

    st.divider()
    for msg in reversed(st.session_state.chat_history):
        if msg['dir'] == "me":
            st.markdown(f'<div class="chat-row source-box"><small>🗣️ {my_lang}:</small> {msg["src"]}<br><b style="font-size:1.2em">🤖 {target_lang}: {msg["trg"]}</b></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-row target-box"><small>{target_lang}:</small> {msg["src"]} 🗣️<br><b style="font-size:1.2em">{msg["trg"]} : {my_lang} 🤖</b></div>', unsafe_allow_html=True)
        if msg['audio']: st.audio(msg['audio'], format="audio/mp3")

# --- MOD 2: KONFERANS ---
def show_conf():
    with st.sidebar:
        if st.button("⬅️ Menüye Dön"): st.session_state.page = "home"; st.rerun()
        st.header("🎙️ Konferans")
        target_lang = st.selectbox("Hedef Dil", ["Türkçe", "English", "Deutsch", "Français", "Español"], index=1)
        if st.button("📝 Özet Çıkar"):
            if st.session_state.chat_history:
                full = "\n".join([m['trg'] for m in st.session_state.chat_history])
                st.session_state.summary = get_analysis(full, target_lang)
            else: st.warning("Veri yok.")

    st.markdown(f"### 🎙️ Simültane Çeviri -> {target_lang}")
    audio = audio_recorder(text="Başlat / Bitir", icon_size="5x", recording_color="red", pause_threshold=300.0)
    
    if audio:
        with st.spinner("Çevriliyor..."):
            txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(audio)), model="whisper-large-v3").text
            trans = get_translation(txt, target_lang, "Normal")
            st.session_state.chat_history.append({"src": txt, "trg": trans})
            
    if "summary" in st.session_state:
        st.success("📝 Rapor"); st.write(st.session_state.summary)
        if st.button("Raporu Kapat"): del st.session_state.summary; st.rerun()
            
    st.divider()
    for msg in reversed(st.session_state.chat_history):
        st.markdown(f"**Kaynak:** {msg['src']}")
        st.success(f"**Çeviri:** {msg['trg']}")
        st.divider()

# --- MOD 3: DOSYA ---
def show_file():
    with st.sidebar:
        if st.button("⬅️ Menüye Dön"): st.session_state.page = "home"; st.rerun()
        st.header("📂 Dosya")
        target_lang = st.selectbox("Hedef Dil", ["Türkçe", "English", "Deutsch"])

    st.markdown("### 📂 Ses Dosyası Yükle")
    f = st.file_uploader("MP3/WAV", type=['mp3','wav'])
    if f and st.button("Başlat"):
        with st.spinner("İşleniyor..."):
            txt = client.audio.transcriptions.create(file=("a.wav", f), model="whisper-large-v3").text
            trans = get_translation(txt, target_lang, "Normal")
            st.subheader("Çeviri:"); st.write(trans)

# --- MOD 4: WEB ---
def show_web():
    with st.sidebar:
        if st.button("⬅️ Menüye Dön"): st.session_state.page = "home"; st.rerun()
        st.header("🔗 Web")
        target_lang = st.selectbox("Rapor Dili", ["Türkçe", "English"])

    st.markdown("### 🔗 Web Okuyucu")
    url = st.text_input("URL")
    if st.button("Analiz Et") and url:
        with st.spinner("Site yerel olarak okunuyor..."):
            # 1. YEREL İŞLEM (Web Scraping)
            raw_text = local_read_web(url)
            
            if raw_text and len(raw_text) > 50:
                # 2. AI İŞLEM (Sadece analiz)
                summ = get_analysis(raw_text, target_lang)
                st.success("✅ Analiz Tamamlandı")
                st.markdown(summ)
            else:
                st.error("Site içeriği okunamadı (Bot koruması olabilir).")

# --- MOD 5: BELGE ---
def show_doc():
    with st.sidebar:
        if st.button("⬅️ Menüye Dön"): st.session_state.page = "home"; st.rerun()
        st.header("📄 Belge")
        target_lang = st.selectbox("Dil", ["Türkçe", "English"])

    st.markdown("### 📄 PDF Asistanı")
    doc_file = st.file_uploader("PDF Yükle", type=['pdf'])
    
    if doc_file:
        with st.spinner("PDF okunuyor..."):
            # 1. YEREL İŞLEM (PDF Parsing)
            doc_text = local_read_pdf(doc_file)
            st.info(f"Belge okundu: {len(doc_text)} karakter.")
            
        if st.button("Özetle"):
            with st.spinner("AI Analiz Ediyor..."):
                # 2. AI İŞLEM
                st.markdown(get_analysis(doc_text, target_lang))

# --- ROUTER ---
if st.session_state.page == "home": show_home()
elif st.session_state.page == "chat": show_chat()
elif st.session_state.page == "conf": show_conf()
elif st.session_state.page == "file": show_file()
elif st.session_state.page == "web": show_web()
elif st.session_state.page == "doc": show_doc()
