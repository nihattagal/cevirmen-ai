import streamlit as st
from groq import Groq
from audio_recorder_streamlit import audio_recorder
from gtts import gTTS
import io
import requests
from bs4 import BeautifulSoup

# --- 1. GENEL AYARLAR ---
st.set_page_config(page_title="AI Tercüman Pro", page_icon="🌐", layout="wide")

# CSS: Kartlar ve Tasarım
st.markdown("""
    <style>
    .main-header { font-size: 2.5rem; font-weight: 800; color: #333; text-align: center; margin-bottom: 30px; }
    /* Kart Butonlar */
    div.stButton > button {
        width: 100%; height: 120px; font-size: 1.2rem; font-weight: bold;
        border-radius: 12px; border: 1px solid #ddd; background: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); transition: 0.3s;
    }
    div.stButton > button:hover {
        transform: translateY(-5px); border-color: #4B0082; color: #4B0082; background: #f8f9fa;
    }
    /* Geri Dön Butonu (Küçük) */
    .back-area div.stButton > button { height: auto; width: auto; background: #eee; font-size: 1rem; padding: 5px 15px; }
    
    /* Mesaj Kutuları */
    .chat-row { padding: 10px; border-radius: 8px; margin-bottom: 5px; }
    .source-box { background: #e3f2fd; border-left: 4px solid #2196F3; }
    .target-box { background: #fbe9e7; border-right: 4px solid #FF5722; text-align: right; }
    </style>
""", unsafe_allow_html=True)

# --- 2. STATE YÖNETİMİ ---
if "page" not in st.session_state: st.session_state.page = "home"
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "app_lang" not in st.session_state: st.session_state.app_lang = "Türkçe"

# --- 3. API BAĞLANTISI ---
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("API Key eksik! Lütfen Secrets ayarlarını yapın.")
    st.stop()

# --- YARDIMCI FONKSİYONLAR ---
def get_translation(text, target_lang, tone, style_prompt=""):
    """
    Bu fonksiyon SADECE ÇEVİRİ yapar. Analiz yapmaz.
    """
    system_prompt = f"""
    Sen profesyonel bir tercümansın.
    GÖREVİN: Verilen metni {target_lang} diline çevirmek.
    
    KURALLAR:
    1. Ton: {tone} (Örn: Resmi, Samimi, Agresif).
    2. Ekstra Stil: {style_prompt}.
    3. ASLA metnin orijinalini tekrar etme.
    4. ASLA "Çeviri şudur" gibi giriş cümleleri kurma. Sadece çeviriyi ver.
    """
    try:
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ]
        )
        return res.choices[0].message.content
    except Exception as e:
        return f"Hata: {e}"

def get_analysis(text, target_lang):
    """
    Bu fonksiyon SADECE ANALİZ ve ÖZET yapar.
    """
    prompt = f"""
    Sen bir asistansın. Aşağıdaki metni analiz et. Rapor dili: {target_lang}.
    ÇIKTI FORMATI:
    1. 📋 Özet
    2. 💡 Ana Fikirler
    3. ✅ Varsa Aksiyonlar/Görevler
    
    Metin: {text}
    """
    res = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
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
    # Dil Seçimi
    c1, c2 = st.columns([8, 2])
    with c2:
        l = st.selectbox("Arayüz Dili", ["Türkçe", "English"], label_visibility="collapsed")
        if l != st.session_state.app_lang:
            st.session_state.app_lang = l
            st.rerun()
            
    st.markdown('<div class="main-header">🌐 AI Tercüman Pro</div>', unsafe_allow_html=True)
    
    # Kartlar
    c1, c2, c3, c4 = st.columns(4)
    
    # Metinler (Dil paketine göre)
    if st.session_state.app_lang == "Türkçe":
        titles = ["🗣️ Karşılıklı\nSohbet", "🎙️ Simültane\nKonferans", "📂 Dosya\nÇeviri", "🔗 Web\nOkuyucu"]
    else:
        titles = ["🗣️ Dual\nChat", "🎙️ Live\nConference", "📂 File\nTranslate", "🔗 Web\nReader"]

    with c1:
        if st.button(titles[0], use_container_width=True): st.session_state.page = "chat"; st.rerun()
    with c2:
        if st.button(titles[1], use_container_width=True): st.session_state.page = "conf"; st.rerun()
    with c3:
        if st.button(titles[2], use_container_width=True): st.session_state.page = "file"; st.rerun()
    with c4:
        if st.button(titles[3], use_container_width=True): st.session_state.page = "web"; st.rerun()

# --- MOD 1: KARŞILIKLI SOHBET (DETAYLI) ---
def show_chat():
    # Sidebar Ayarları (Burada olmalı!)
    with st.sidebar:
        if st.button("⬅️ Menüye Dön"): st.session_state.page = "home"; st.rerun()
        st.header("⚙️ Sohbet Ayarları")
        
        # 1. Diller
        st.subheader("Diller")
        my_lang = st.selectbox("Benim Dilim", ["Türkçe", "English", "Deutsch"])
        target_lang = st.selectbox("Karşı Taraf", ["English", "Türkçe", "Deutsch", "Français", "Español", "Russian", "Arabic", "Chinese"])
        
        # 2. Ton
        st.subheader("Çeviri Tarzı")
        tone = st.select_slider("Ton Seçimi", options=["Çok Resmi", "Resmi", "Normal", "Samimi", "Sokak Ağzı"], value="Normal")
        
        # 3. Kişilik
        st.subheader("AI Rolü")
        persona = st.selectbox("Karakter", ["Standart Tercüman", "Sabırlı Öğretmen", "Esprili Arkadaş", "Agresif"])
        
        if st.button("🗑️ Sohbeti Temizle", type="primary"):
            st.session_state.chat_history = []
            st.rerun()

    # Ana Ekran
    st.markdown(f"### 🗣️ Sohbet Modu: {my_lang} ↔️ {target_lang}")
    
    # Mikrofonlar
    c1, c2 = st.columns(2)
    
    # Dil kodları haritası
    lang_map = {"English": "en", "Türkçe": "tr", "Deutsch": "de", "Français": "fr", "Español": "es", "Russian": "ru", "Arabic": "ar", "Chinese": "zh"}
    
    # BEN
    with c1:
        st.info(f"🎤 BEN ({my_lang})")
        a1 = audio_recorder(text="", icon_size="3x", key="mic1", recording_color="#2196F3")
        if a1:
            with st.spinner("Çevriliyor..."):
                txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(a1)), model="whisper-large-v3").text
                # Çeviri: Ben -> Hedef
                trans = get_translation(txt, target_lang, tone, f"Role: {persona}")
                # Ses: Hedef dilde oku
                audio = create_voice(trans, lang_map[target_lang])
                st.session_state.chat_history.append({"src": txt, "trg": trans, "dir": "me", "audio": audio})
    
    # KARŞI TARAF
    with c2:
        st.warning(f"🎤 KARŞI TARAF ({target_lang})")
        a2 = audio_recorder(text="", icon_size="3x", key="mic2", recording_color="#FF5722")
        if a2:
            with st.spinner("Çevriliyor..."):
                txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(a2)), model="whisper-large-v3").text
                # Çeviri: Hedef -> Ben
                trans = get_translation(txt, my_lang, tone, f"Role: {persona}")
                # Ses: Benim dilimde oku
                audio = create_voice(trans, lang_map[my_lang])
                st.session_state.chat_history.append({"src": txt, "trg": trans, "dir": "you", "audio": audio})

    # Geçmiş Gösterimi
    st.divider()
    for msg in reversed(st.session_state.chat_history):
        if msg['dir'] == "me":
            # Benim mesajım (Sola yaslı)
            st.markdown(f"""
            <div class="chat-row source-box">
                <small>🗣️ {my_lang}:</small> {msg['src']}<br>
                <b style="font-size:1.2em">🤖 {target_lang}: {msg['trg']}</b>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Onun mesajı (Sağa yaslı)
            st.markdown(f"""
            <div class="chat-row target-box">
                <small>{target_lang}:</small> {msg['src']} 🗣️<br>
                <b style="font-size:1.2em">{msg['trg']} : {my_lang} 🤖</b>
            </div>
            """, unsafe_allow_html=True)
        
        if msg['audio']: st.audio(msg['audio'], format="audio/mp3")

# --- MOD 2: KONFERANS (SİMÜLTANE) ---
def show_conf():
    with st.sidebar:
        if st.button("⬅️ Menüye Dön"): st.session_state.page = "home"; st.rerun()
        st.header("🎙️ Konferans Ayarları")
        
        target_lang = st.selectbox("Hedef Dil", ["Türkçe", "English", "Deutsch", "Français", "Español"])
        tone = st.select_slider("Çeviri Tonu", ["Resmi", "Normal", "Özetleyerek"], value="Resmi")
        
        st.divider()
        st.info("Bu modda ortam dinlenir ve seçilen dile çevrilir. Sohbet edilmez, sadece çeviri yapılır.")
        
        # ANALİZ BUTONU BURADA (İsteğe bağlı)
        if st.button("📝 Toplantı Özeti Çıkar"):
            if st.session_state.chat_history:
                full_text = "\n".join([m['trg'] for m in st.session_state.chat_history])
                summary = get_analysis(full_text, target_lang)
                st.session_state.summary = summary
            else:
                st.warning("Henüz veri yok.")

    st.markdown(f"### 🎙️ Simültane Çeviri -> {target_lang}")
    
    # Mikrofon (Uzun süreli)
    audio = audio_recorder(text="Dinlemeyi Başlat / Durdur", icon_size="5x", recording_color="red", pause_threshold=300.0)
    
    if audio:
        with st.spinner("Çevriliyor..."):
            # 1. Kaynak sesi al (Dil otomatik algılanır)
            txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(audio)), model="whisper-large-v3").text
            
            # 2. Direkt Çevir (Yorum katma)
            trans = get_translation(txt, target_lang, tone)
            
            # 3. Kaydet
            st.session_state.chat_history.append({"src": txt, "trg": trans})
            
    # Özet varsa göster
    if "summary" in st.session_state:
        st.success("📝 Toplantı Raporu")
        st.write(st.session_state.summary)
        if st.button("Raporu Kapat"): del st.session_state.summary; st.rerun()
            
    # Akış
    st.divider()
    for msg in reversed(st.session_state.chat_history):
        st.markdown(f"**Kaynak:** {msg['src']}")
        st.success(f"**Çeviri:** {msg['trg']}")
        st.divider()

# --- MOD 3: DOSYA ---
def show_file():
    with st.sidebar:
        if st.button("⬅️ Menüye Dön"): st.session_state.page = "home"; st.rerun()
        st.header("📂 Dosya Ayarları")
        target_lang = st.selectbox("Hedef Dil", ["Türkçe", "English", "Deutsch"])
        mode = st.radio("İşlem", ["Sadece Çevir", "Çevir ve Özetle"])

    st.markdown("### 📂 Ses Dosyası Yükle")
    f = st.file_uploader("MP3/WAV", type=['mp3','wav'])
    
    if f and st.button("İşlemi Başlat"):
        with st.spinner("Dosya işleniyor..."):
            txt = client.audio.transcriptions.create(file=("a.wav", f), model="whisper-large-v3").text
            
            if mode == "Sadece Çevir":
                res = get_translation(txt, target_lang, "Normal")
                st.subheader("Çeviri:")
                st.write(res)
            else:
                # Çevir ve Özetle
                trans = get_translation(txt, target_lang, "Normal")
                summ = get_analysis(trans, target_lang)
                
                c1, c2 = st.columns(2)
                with c1:
                    st.subheader("Çeviri")
                    st.write(trans)
                with c2:
                    st.subheader("Analiz & Özet")
                    st.info(summ)

# --- MOD 4: WEB (Sadece gerektiğinde analiz) ---
def show_web():
    with st.sidebar:
        if st.button("⬅️ Menüye Dön"): st.session_state.page = "home"; st.rerun()
        st.header("🔗 Web Ayarları")
        target_lang = st.selectbox("Rapor Dili", ["Türkçe", "English"])

    st.markdown("### 🔗 Web Sitesi Okuyucu")
    url = st.text_input("URL Girin (http://...)")
    
    if st.button("Siteyi Oku ve Özetle"):
        if url:
            with st.spinner("Siteye bağlanılıyor..."):
                try:
                    # Web Scraping
                    page = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
                    soup = BeautifulSoup(page.content, 'html.parser')
                    raw_text = " ".join([p.get_text() for p in soup.find_all(['p', 'h1', 'h2'])])[:8000] # Limit
                    
                    # Analiz
                    summ = get_analysis(raw_text, target_lang)
                    st.success("✅ Analiz Tamamlandı")
                    st.markdown(summ)
                    
                except Exception as e:
                    st.error(f"Site okunamadı: {e}")

# --- YÖNLENDİRİCİ ---
if st.session_state.page == "home": show_home()
elif st.session_state.page == "chat": show_chat()
elif st.session_state.page == "conf": show_conf()
elif st.session_state.page == "file": show_file()
elif st.session_state.page == "web": show_web()
