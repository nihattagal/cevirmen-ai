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
    page_title="LinguaFlow Pro",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS TASARIM (PREMIUM SAAS GÖRÜNÜMÜ) ---
st.markdown("""
    <style>
    /* Genel Yapı */
    .stApp { background-color: #f9fafb; font-family: 'Inter', sans-serif; }
    
    /* Başlık Stili */
    .header-logo { 
        font-size: 2.2rem; font-weight: 800; color: #0f172a; 
        text-align: center; letter-spacing: -0.5px; margin-bottom: 5px;
    }
    .header-sub { text-align: center; color: #64748b; margin-bottom: 30px; font-size: 0.95rem; }
    
    /* Metin Alanları */
    .stTextArea textarea {
        border: 1px solid #e2e8f0; border-radius: 12px;
        font-size: 1.1rem; height: 280px !important; padding: 15px;
        background: white; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        resize: none; transition: border 0.3s;
    }
    .stTextArea textarea:focus { border-color: #3b82f6; outline: none; box-shadow: 0 0 0 3px rgba(59,130,246,0.1); }
    
    /* Sonuç Kutusu */
    .result-box {
        background-color: white; border: 1px solid #e2e8f0; border-radius: 12px;
        min-height: 280px; padding: 20px; font-size: 1.1rem; color: #334155;
        white-space: pre-wrap; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); position: relative;
    }
    
    /* Butonlar */
    div.stButton > button {
        background-color: #0f172a; color: white; border: none; border-radius: 8px;
        padding: 12px; font-weight: 600; width: 100%; transition: all 0.2s;
        box-shadow: 0 4px 6px -1px rgba(15, 23, 42, 0.1);
    }
    div.stButton > button:hover { 
        background-color: #334155; transform: translateY(-1px); 
        box-shadow: 0 10px 15px -3px rgba(15, 23, 42, 0.1);
    }
    
    /* İkincil Butonlar */
    .secondary-btn div.stButton > button {
        background-color: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; box-shadow: none;
    }
    .secondary-btn div.stButton > button:hover { background-color: #e2e8f0; color: #1e293b; }

    /* Dil Etiketi */
    .lang-badge {
        position: absolute; top: 10px; right: 10px;
        background: #eff6ff; color: #2563eb; padding: 4px 10px;
        border-radius: 20px; font-size: 0.75rem; font-weight: 700;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. API KONTROLÜ ---
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("⚠️ API Anahtarı Bulunamadı! Secrets ayarlarını kontrol edin.")
    st.stop()

# --- 4. STATE YÖNETİMİ (HATASIZ BAŞLANGIÇ) ---
if "history" not in st.session_state: st.session_state.history = []
if "res_text" not in st.session_state: st.session_state.res_text = ""
if "input_val" not in st.session_state: st.session_state.input_val = ""
if "detected_lang" not in st.session_state: st.session_state.detected_lang = ""
if "stats_trans" not in st.session_state: st.session_state.stats_trans = 0
if "target_lang_idx" not in st.session_state: st.session_state.target_lang_idx = 0

# --- 5. MOTOR (GÜÇLENDİRİLMİŞ) ---
def ai_engine(text, task, target_lang="English", tone="Normal", glossary=""):
    if not text or len(text.strip()) == 0: return "", ""
    
    # İstatistik
    st.session_state.stats_trans += 1
    
    glossary_prompt = f"TERMİNOLOJİ (Uygula): \n{glossary}" if glossary else ""

    # Prompt Mühendisliği
    if task == "translate":
        sys_msg = f"""
        Sen uzman bir tercümansın.
        Hedef Dil: {target_lang}. Ton: {tone}.
        {glossary_prompt}
        GÖREV: Metni çevir.
        KURAL: Asla açıklama yapma.
        ÇIKTI FORMATI: [ALGILANAN_DİL] ||| ÇEVİRİ
        """
    elif task == "improve":
        sys_msg = "Sen profesyonel bir editörsün. Metni gramer, akıcılık ve stil açısından düzelt. Format: [DİL] ||| DÜZELTİLMİŞ_METİN"
    elif task == "summarize":
        sys_msg = f"Sen bir analistsin. Metni {target_lang} dilinde özetle. Önemli noktaları madde madde yaz."

    try:
        # Token Limiti Koruması (Çok uzun metinleri kırp)
        safe_text = text[:25000] 
        
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": safe_text}]
        )
        full_res = res.choices[0].message.content
        
        # Cevap Ayrıştırma
        if "|||" in full_res:
            parts = full_res.split("|||", 1)
            return parts[0].strip().replace("[", "").replace("]", ""), parts[1].strip()
        else:
            return "Otomatik", full_res

    except Exception as e: return "Hata", str(e)

def create_audio(text, lang_name, speed=False):
    if not text: return None
    code_map = {"Türkçe": "tr", "İngilizce": "en", "Almanca": "de", "Fransızca": "fr", "İspanyolca": "es", "Rusça": "ru", "Arapça": "ar", "Çince": "zh"}
    lang_code = code_map.get(lang_name, "en")
    try:
        fp = io.BytesIO()
        gTTS(text=text, lang=lang_code, slow=speed).write_to_fp(fp)
        return fp.getvalue()
    except: return None

def render_share(text):
    if not text: return
    encoded = urllib.parse.quote(text[:500]) # Paylaşım için çok uzun metinleri kırp
    wa = f"https://api.whatsapp.com/send?text={encoded}"
    st.markdown(f"<a href='{wa}' target='_blank' style='text-decoration:none; color:#25D366; font-weight:bold; font-size:0.9rem;'>📲 WhatsApp ile Paylaş</a>", unsafe_allow_html=True)

def local_read_file(file):
    try:
        if file.name.endswith('.pdf'):
            reader = PyPDF2.PdfReader(file)
            return "".join([page.extract_text() for page in reader.pages])
        else: return client.audio.transcriptions.create(file=("a.wav", file), model="whisper-large-v3").text
    except: return None

def local_read_web(url):
    try:
        # Güçlü User-Agent (Bot engellerini aşmak için)
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        # Sadece okunabilir metinleri al
        paragraphs = soup.find_all(['p', 'h1', 'h2', 'h3', 'li'])
        return " ".join([p.get_text() for p in paragraphs])
    except: return None

# ==========================================
# ARAYÜZ
# ==========================================

# --- YAN MENÜ ---
with st.sidebar:
    st.title("LinguaFlow")
    
    sb1, sb2 = st.tabs(["Ayarlar", "Geçmiş"])
    
    with sb1:
        st.subheader("Tercihler")
        speech_slow = st.checkbox("🐢 Yavaş Okuma", value=False)
        
        st.subheader("Sözlük (Terminoloji)")
        glossary_txt = st.text_area("Örn: LinguaFlow=Özel Proje", height=80, placeholder="Kelime=Çeviri")
        
        st.info(f"📊 Toplam İşlem: {st.session_state.stats_trans}")

    with sb2:
        if st.session_state.history:
            for item in st.session_state.history[:8]:
                st.markdown(f"<div style='font-size:0.8rem; padding:8px; border-bottom:1px solid #eee; color:#64748b;'>{item['src']}</div>", unsafe_allow_html=True)
            if st.button("Temizle"): st.session_state.history = []; st.rerun()
        else: st.caption("Geçmiş boş.")

# --- BAŞLIK ---
st.markdown('<div class="header-logo">LinguaFlow Pro</div><div class="header-sub">Yapay Zeka Destekli Dil Merkezi</div>', unsafe_allow_html=True)

# --- SEKMELER ---
tab_text, tab_voice, tab_files, tab_web = st.tabs(["📝 Metin", "🎙️ Canlı Ses", "📂 Dosya", "🔗 Web"])
LANG_OPTIONS = ["English", "Türkçe", "Deutsch", "Français", "Español", "Italiano", "Русский", "العربية", "中文"]

# --- 1. METİN ---
with tab_text:
    c1, c2, c3, c4 = st.columns([3, 1, 3, 1])
    with c1: st.markdown("**Giriş**")
    with c3: 
        # Session state ile dil seçimini hatırla
        target_lang = st.selectbox("Hedef", LANG_OPTIONS, index=st.session_state.target_lang_idx, key="t_lang_select", label_visibility="collapsed")
    
    with c2:
        st.markdown('<div class="secondary-btn">', unsafe_allow_html=True)
        if st.button("⇄"):
             # Basit swap: İngilizce <-> Türkçe
             st.session_state.target_lang_idx = 1 if st.session_state.target_lang_idx == 0 else 0
             st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    col_in, col_out = st.columns(2)
    
    with col_in:
        # Dikte
        mc, tc = st.columns([1, 8])
        with mc: audio_in = audio_recorder(text="", icon_size="2x", recording_color="#ef4444", neutral_color="#cbd5e1", key="dict")
        with tc: st.caption("Mikrofona basıp konuşabilirsiniz")
        
        if audio_in:
            with st.spinner("Yazılıyor..."):
                try:
                    txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(audio_in)), model="whisper-large-v3").text
                    st.session_state.input_val = txt
                    st.rerun()
                except: st.error("Ses algılanamadı.")

        with st.form(key="t_form"):
            input_text = st.text_area("Metin", value=st.session_state.input_val, height=250, label_visibility="collapsed")
            
            b1, b2 = st.columns([3, 2])
            with b1: submit = st.form_submit_button("Çevir ➔", type="primary", use_container_width=True)
            with b2: tone = st.selectbox("Ton", ["Normal", "Resmi", "Samimi"], label_visibility="collapsed")
        
        if submit and input_text:
            with st.spinner("..."):
                lang, txt = ai_engine(input_text, "translate", target_lang, tone, glossary_txt)
                st.session_state.res_text = txt
                st.session_state.detected_lang = lang
                st.session_state.input_val = input_text
                # Geçmiş
                ts = datetime.datetime.now().strftime("%H:%M")
                st.session_state.history.insert(0, {"time": ts, "src": input_text[:30]+".."})

    with col_out:
        st.write("") 
        st.write("") # Hizalama boşlukları
        
        res = st.session_state.res_text
        d_lang = st.session_state.detected_lang
        
        st.markdown(f"""
        <div class="result-box">
            {f'<span class="lang-badge">{d_lang}</span>' if d_lang else ''}
            {res if res else '...'}
        </div>
        """, unsafe_allow_html=True)
        
        if res:
            st.write("")
            ca, cb, cc = st.columns([2, 2, 2])
            with ca:
                aud = create_audio(res, target_lang, speech_slow)
                if aud: st.audio(aud, format="audio/mp3")
            with cb:
                st.markdown('<div class="secondary-btn">', unsafe_allow_html=True)
                if st.button("🗑️ Temizle"):
                    st.session_state.input_val = ""
                    st.session_state.res_text = ""
                    st.session_state.detected_lang = ""
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            with cc: render_share(res)

# --- 2. SES ---
with tab_voice:
    mode = st.radio("Mod:", ["🗣️ Sohbet", "🎙️ Konferans"], horizontal=True)
    st.divider()
    
    if "Sohbet" in mode:
        c1, c2 = st.columns(2)
        with c1:
            st.info("SİZ")
            a1 = audio_recorder(text="", icon_size="3x", key="v1", recording_color="#3b82f6", neutral_color="#dbeafe")
            if a1:
                txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(a1)), model="whisper-large-v3").text
                lang, res = ai_engine(txt, "translate", target_lang, glossary=glossary_txt)
                st.success(f"{txt}")
                st.info(f"{res}")
                aud = create_audio(res, target_lang, speech_slow)
                if aud: st.audio(aud, format="audio/mp3", autoplay=True)
        with c2:
            st.warning(f"MİSAFİR ({target_lang})")
            a2 = audio_recorder(text="", icon_size="3x", key="v2", recording_color="#ec4899", neutral_color="#fce7f3")
            if a2:
                txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(a2)), model="whisper-large-v3").text
                lang, res = ai_engine(txt, "translate", "Türkçe", glossary=glossary_txt)
                st.info(f"{txt}")
                st.success(f"{res}")
                aud = create_audio(res, "Türkçe", speech_slow)
                if aud: st.audio(aud, format="audio/mp3", autoplay=True)

    else: # Konferans
        c1, c2 = st.columns([1, 3])
        with c1:
            st.write("Sürekli Dinleme")
            ac = audio_recorder(text="BAŞLAT / DURDUR", icon_size="2x", recording_color="#dc2626", pause_threshold=20.0)
        with c2:
            if ac:
                with st.spinner("Analiz..."):
                    txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(ac)), model="whisper-large-v3").text
                    lang, trans = ai_engine(txt, "translate", target_lang, glossary=glossary_txt)
                    st.success(f"Orijinal: {txt}")
                    st.info(f"Çeviri: {trans}")
                    st.download_button("İndir", f"{txt}\n{trans}", "toplanti.txt")

# --- 3. DOSYA ---
with tab_files:
    u_file = st.file_uploader("Dosya", type=['pdf', 'mp3', 'wav', 'm4a'])
    if u_file:
        if st.button("Analiz Et"):
            with st.spinner("..."):
                raw = local_read_file(u_file)
                if raw and len(raw)>10:
                    mode = "translate" if len(raw) < 3000 else "summarize"
                    lang, res = ai_engine(raw, mode, target_lang, glossary=glossary_txt)
                    st.markdown(f"<div class='result-box'>{res}</div>", unsafe_allow_html=True)
                    st.download_button("İndir", res, "sonuc.txt")
                else: st.error("Dosya okunamadı.")

# --- 4. WEB ---
with tab_web:
    url = st.text_input("URL")
    if st.button("Analiz") and url:
        with st.spinner("..."):
            txt = local_read_web(url)
            if txt:
                lang, res = ai_engine(txt, "summarize", target_lang)
                st.markdown(f"<div class='result-box'>{res}</div>", unsafe_allow_html=True)
                st.download_button("İndir", res, "web.txt")
            else: st.error("Hata.")

st.divider()
