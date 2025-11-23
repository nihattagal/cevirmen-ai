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
    page_title="LinguaFlow Ultimate",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS TASARIM ---
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; font-family: 'Inter', sans-serif; }
    
    /* Başlık */
    .header-logo { font-size: 2rem; font-weight: 800; color: #1e293b; text-align: center; letter-spacing: -0.5px; }
    .header-sub { text-align: center; color: #64748b; margin-bottom: 20px; font-size: 0.9rem; }
    
    /* Metin Alanı */
    .stTextArea textarea {
        border: 1px solid #e2e8f0; border-radius: 12px;
        font-size: 1.1rem; height: 250px !important; padding: 15px;
        background: white; resize: none; box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .stTextArea textarea:focus { border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59,130,246,0.1); }
    
    /* Sonuç Kutusu */
    .result-box {
        background-color: white; border: 1px solid #e2e8f0; border-radius: 12px;
        min-height: 250px; padding: 20px; font-size: 1.1rem; color: #334155;
        white-space: pre-wrap; box-shadow: 0 2px 4px rgba(0,0,0,0.02); position: relative;
    }
    
    /* Algılanan Dil Etiketi */
    .lang-badge {
        position: absolute; top: 10px; right: 10px;
        background: #e0f2fe; color: #0369a1; padding: 4px 8px;
        border-radius: 4px; font-size: 0.75rem; font-weight: bold;
    }
    
    /* Butonlar */
    div.stButton > button {
        background-color: #0f172a; color: white; border: none; border-radius: 8px;
        padding: 12px; font-weight: 600; width: 100%; transition: all 0.2s;
    }
    div.stButton > button:hover { background-color: #334155; transform: translateY(-1px); }
    
    /* Sohbet Balonları */
    .chat-me { background: #eff6ff; border-left: 4px solid #3b82f6; padding: 10px; border-radius: 8px; margin-bottom: 8px; color: #1e3a8a; }
    .chat-you { background: #fff1f2; border-right: 4px solid #ec4899; padding: 10px; border-radius: 8px; margin-bottom: 8px; text-align: right; color: #831843; }
    
    /* Hoca Kutusu */
    .tutor-box { background: #fff7ed; border-left: 4px solid #f97316; padding: 10px; border-radius: 6px; font-size: 0.9rem; color: #9a3412; margin-top: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- 3. API ---
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("⚠️ API Key Eksik! Secrets ayarlarını kontrol edin.")
    st.stop()

# --- 4. STATE ---
if "history" not in st.session_state: st.session_state.history = []
if "res_text" not in st.session_state: st.session_state.res_text = ""
if "detected_lang" not in st.session_state: st.session_state.detected_lang = ""
if "explanation" not in st.session_state: st.session_state.explanation = ""
if "input_val" not in st.session_state: st.session_state.input_val = ""

# --- 5. MOTOR (BAĞLAM VE DİL ALGILAMA EKLENDİ) ---
def ai_engine(text, task, target_lang="English", tone="Normal", custom_prompt=""):
    if not text: return ""
    
    # Geçmişten bağlam oluştur (Son 3 mesajı hatırlasın)
    context_memory = ""
    if st.session_state.history:
        last_items = st.session_state.history[:3]
        context_memory = "\n".join([f"Eski Çeviri: {h['src']} -> {h['res']}" for h in last_items])

    if task == "translate":
        sys_msg = f"""
        Sen uzman bir tercümansın.
        Hedef Dil: {target_lang}. Ton: {tone}.
        Özel Talimat: {custom_prompt}
        
        ÖNEMLİ GÖREVLER:
        1. Kaynak dili algıla.
        2. Çeviriyi yap.
        3. Çıktı formatı ŞU ŞEKİLDE OLMALI: [ALGILANAN_DİL] ||| ÇEVİRİ_METNİ
        
        BAĞLAM (Önceki konuşmalar):
        {context_memory}
        """
    elif task == "improve":
        sys_msg = "Editörsün. Metni düzelt. Format: [DİL] ||| DÜZELTİLMİŞ_METİN"
    elif task == "explain":
        sys_msg = f"Öğretmensin. Hataları ve nedenlerini {target_lang} dilinde açıkla. Format: [ANALİZ] ||| AÇIKLAMA"
    elif task == "summarize":
        sys_msg = f"Analistsin. Metni {target_lang} dilinde özetle. Format: [ÖZET] ||| METİN"

    try:
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": text[:15000]}]
        )
        full_res = res.choices[0].message.content
        
        # Cevabı Parçala (Dil Kodu ||| Metin)
        if "|||" in full_res:
            lang_tag, content = full_res.split("|||", 1)
            return lang_tag.strip().replace("[", "").replace("]", ""), content.strip()
        else:
            return "Otomatik", full_res

    except Exception as e: return "Hata", str(e)

def create_audio(text, lang_name):
    code_map = {"Türkçe": "tr", "İngilizce": "en", "Almanca": "de", "Fransızca": "fr", "İspanyolca": "es", "Rusça": "ru", "Arapça": "ar", "Çince": "zh"}
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
    st.markdown(f"<a href='{wa}' target='_blank' style='text-decoration:none; color:#25D366; font-weight:bold; font-size:0.9rem;'>📲 WhatsApp'ta Paylaş</a>", unsafe_allow_html=True)

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

# --- YAN MENÜ ---
with st.sidebar:
    st.markdown("### ⚙️ Ayarlar & Geçmiş")
    
    # Gelişmiş Ayar (Prompt)
    with st.expander("🛠️ Özel Talimat (Prompt)"):
        custom_p = st.text_area("AI'a özel emir ver:", placeholder="Örn: Hukuki terimler kullan...", height=70)
    
    auto_speak = st.checkbox("🔊 Oto-Okuma", value=True)
    
    st.divider()
    
    if st.session_state.history:
        for item in st.session_state.history[:6]:
            st.markdown(f"<div style='font-size:0.8rem; padding:5px; border-bottom:1px solid #eee;'>{item['src']}</div>", unsafe_allow_html=True)
        if st.button("Geçmişi Temizle"):
            st.session_state.history = []
            st.rerun()

# --- BAŞLIK ---
st.markdown('<div class="header-logo">LinguaFlow Ultimate</div><div class="header-sub">Bağlam Farkındalıklı Yapay Zeka</div>', unsafe_allow_html=True)

# --- SEKMELER ---
tab_text, tab_voice, tab_files, tab_web = st.tabs(["📝 Akıllı Çeviri", "🎙️ Hibrit Ses", "📂 Dosya Analiz", "🔗 Web"])
LANG_OPTIONS = ["English", "Türkçe", "Deutsch", "Français", "Español", "Italiano", "Русский", "العربية", "中文"]

# --- 1. METİN ---
with tab_text:
    c1, c2, c3 = st.columns([3, 1, 3])
    with c1: st.markdown(f"**Giriş**")
    with c3: target_lang = st.selectbox("Hedef", LANG_OPTIONS, label_visibility="collapsed")

    col_in, col_out = st.columns(2)
    with col_in:
        input_text = st.text_area("Giriş", value=st.session_state.input_val, height=280, placeholder="Metni buraya yapıştırın...", label_visibility="collapsed")
        
        b1, b2, b3, b4 = st.columns([3, 3, 2, 1])
        with b1:
            if st.button("Çevir ➔"):
                if input_text:
                    with st.spinner("AI Düşünüyor..."):
                        lang, txt = ai_engine(input_text, "translate", target_lang, custom_prompt=custom_p)
                        st.session_state.res_text = txt
                        st.session_state.detected_lang = lang
                        st.session_state.explanation = ""
                        st.session_state.input_val = input_text
                        # Geçmişe ekle
                        ts = datetime.datetime.now().strftime("%H:%M")
                        st.session_state.history.insert(0, {"time": ts, "src": input_text[:20]+"..", "res": txt})
        with b2:
            if st.button("✨ Düzelt & Açıkla"):
                if input_text:
                    with st.spinner("Hoca İnceliyor..."):
                        lang, txt = ai_engine(input_text, "improve")
                        _, expl = ai_engine(input_text, "explain", target_lang="Türkçe")
                        st.session_state.res_text = txt
                        st.session_state.detected_lang = lang
                        st.session_state.explanation = expl
        with b3: tone = st.selectbox("Ton", ["Normal", "Resmi", "Samimi"], label_visibility="collapsed")
        with b4: 
            if st.button("🗑️"): 
                st.session_state.input_val=""; st.session_state.res_text=""; st.session_state.detected_lang=""; st.rerun()

    with col_out:
        res = st.session_state.res_text
        d_lang = st.session_state.detected_lang
        
        # Sonuç Kutusu (HTML içinde dil etiketi ile)
        html_content = f"""
        <div class="result-box">
            {f'<span class="lang-badge">{d_lang}</span>' if d_lang else ''}
            {res if res else '...'}
        </div>
        """
        st.markdown(html_content, unsafe_allow_html=True)
        
        # Hoca Açıklaması
        if st.session_state.explanation:
            st.markdown(f"<div class='tutor-box'><b>👨‍🏫 Analiz:</b><br>{st.session_state.explanation}</div>", unsafe_allow_html=True)
        
        if res:
            st.write("")
            ca, cb = st.columns([1, 3])
            with ca:
                aud = create_audio(res, target_lang)
                if aud: 
                    st.audio(aud, format="audio/mp3")
                    if auto_speak and not st.session_state.explanation: st.audio(aud, format="audio/mp3", autoplay=True)
            with cb: render_share(res)

# --- 2. SES ---
with tab_voice:
    mode = st.radio("Mod:", ["🗣️ Karşılıklı Sohbet", "🎙️ Konferans"], horizontal=True)
    st.divider()
    
    if "Sohbet" in mode:
        c1, c2 = st.columns(2)
        with c1:
            st.info("SİZ")
            a1 = audio_recorder(text="", icon_size="3x", key="v1", recording_color="#3b82f6", neutral_color="#dbeafe")
            if a1:
                txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(a1)), model="whisper-large-v3").text
                lang, res = ai_engine(txt, "translate", target_lang, custom_prompt=custom_p)
                aud = create_audio(res, target_lang)
                st.markdown(f"<div class='chat-me'><b>Algılanan ({lang}):</b> {txt}<br><br><b>Çeviri:</b> {res}</div>", unsafe_allow_html=True)
                if aud and auto_speak: st.audio(aud, format="audio/mp3", autoplay=True)
        with c2:
            st.warning(f"MİSAFİR ({target_lang})")
            a2 = audio_recorder(text="", icon_size="3x", key="v2", recording_color="#ec4899", neutral_color="#fce7f3")
            if a2:
                txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(a2)), model="whisper-large-v3").text
                lang, res = ai_engine(txt, "translate", "Türkçe", custom_prompt=custom_p)
                aud = create_audio(res, "Türkçe")
                st.markdown(f"<div class='chat-you'><b>Algılanan ({lang}):</b> {txt}<br><br><b>Çeviri:</b> {res}</div>", unsafe_allow_html=True)
                if aud and auto_speak: st.audio(aud, format="audio/mp3", autoplay=True)

    else: # Konferans
        c1, c2 = st.columns([1, 3])
        with c1:
            st.write("Sürekli Dinleme")
            ac = audio_recorder(text="BAŞLAT / DURDUR", icon_size="2x", recording_color="#dc2626", pause_threshold=20.0)
        with c2:
            if ac:
                with st.spinner("Analiz..."):
                    try:
                        txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(ac)), model="whisper-large-v3").text
                        lang, trans = ai_engine(txt, "translate", target_lang, custom_prompt=custom_p)
                        st.success(f"Orijinal ({lang}): {txt}")
                        st.info(f"Çeviri: {trans}")
                        st.download_button("İndir", f"{txt}\n{trans}", "kayit.txt")
                    except: st.error("Ses yok.")

# --- 3. DOSYA ---
with tab_files:
    u_file = st.file_uploader("Dosya", type=['pdf', 'mp3', 'wav', 'm4a'])
    if u_file:
        if st.button("İşle"):
            with st.spinner("..."):
                raw = local_read_file(u_file)
                if raw:
                    mode = "translate" if len(raw) < 3000 else "summarize"
                    lang, res = ai_engine(raw, mode, target_lang)
                    st.markdown(f"<div class='result-box'>{res}</div>", unsafe_allow_html=True)
                    st.download_button("İndir", res, "sonuc.txt")
                else: st.error("Hata.")

# --- 4. WEB ---
with tab_web:
    url = st.text_input("URL")
    if st.button("Analiz") and url:
        with st.spinner("..."):
            try:
                h = {'User-Agent': 'Mozilla/5.0'}
                soup = BeautifulSoup(requests.get(url, headers=h, timeout=10).content, 'html.parser')
                raw = " ".join([p.get_text() for p in soup.find_all(['p', 'h1'])])[:10000]
                lang, res = ai_engine(raw, "summarize", target_lang)
                st.markdown(f"<div class='result-box'>{res}</div>", unsafe_allow_html=True)
                st.download_button("İndir", res, "web.txt")
            except: st.error("Hata.")

st.divider()
