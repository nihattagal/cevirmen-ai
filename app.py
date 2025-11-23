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
    page_title="LinguaFlow Infinity",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS TASARIM (PROFESYONEL SPLIT VIEW) ---
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; font-family: 'Inter', sans-serif; }
    
    /* Başlık */
    .header-logo { 
        font-size: 2rem; font-weight: 800; color: #0f172a; 
        text-align: center; letter-spacing: -0.5px;
    }
    
    /* Metin Alanları */
    .stTextArea textarea {
        border: 1px solid #cbd5e1; border-radius: 10px;
        font-size: 1.05rem; height: 300px !important; padding: 15px;
        background: white; resize: none;
    }
    .stTextArea textarea:focus { border-color: #6366f1; box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1); }
    
    /* Sonuç Kutusu (Normal) */
    .result-box {
        background-color: white; border: 1px solid #cbd5e1; border-radius: 10px;
        min-height: 300px; padding: 20px; font-size: 1.05rem; color: #334155;
        white-space: pre-wrap; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    
    /* Yan Yana Kıyaslama Kutuları (Dosya Modu) */
    .compare-box {
        padding: 15px; border-radius: 8px; font-size: 0.95rem;
        height: 400px; overflow-y: auto; border: 1px solid #e2e8f0;
    }
    .src-view { background-color: #f1f5f9; color: #475569; }
    .trg-view { background-color: #ffffff; color: #0f172a; border-left: 4px solid #4f46e5; }

    /* Butonlar */
    div.stButton > button {
        background-color: #0f172a; color: white; border: none; border-radius: 8px;
        padding: 12px; font-weight: 600; width: 100%; transition: all 0.2s;
    }
    div.stButton > button:hover { background-color: #334155; transform: translateY(-1px); }
    
    /* İstatistik Kutucukları */
    .metric-card {
        background: white; border: 1px solid #e2e8f0; border-radius: 8px;
        padding: 10px; text-align: center; margin-bottom: 10px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    .metric-val { font-size: 1.2rem; font-weight: bold; color: #4f46e5; }
    .metric-lbl { font-size: 0.8rem; color: #64748b; }
    </style>
""", unsafe_allow_html=True)

# --- 3. API ---
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("⚠️ API Key Eksik!")
    st.stop()

# --- 4. STATE ---
if "history" not in st.session_state: st.session_state.history = []
if "res_text" not in st.session_state: st.session_state.res_text = ""
if "detected_lang" not in st.session_state: st.session_state.detected_lang = ""
# İstatistikler
if "stats_trans" not in st.session_state: st.session_state.stats_trans = 0

# --- 5. MOTOR ---
def ai_engine(text, task, target_lang="English", tone="Normal", glossary=""):
    if not text: return ""
    
    st.session_state.stats_trans += 1
    
    glossary_prompt = f"ÖZEL TERİMLER (Uygula): \n{glossary}" if glossary else ""

    if task == "translate":
        sys_msg = f"""
        Sen uzman tercümansın. Hedef: {target_lang}. Ton: {tone}.
        {glossary_prompt}
        GÖREV: 
        1. Kaynak dili algıla.
        2. Çeviriyi yap.
        3. Çıktı: [ALGILANAN_DİL] ||| METİN
        """
    elif task == "improve":
        sys_msg = "Editörsün. Metni düzelt. Format: [DİL] ||| METİN"
    elif task == "summarize":
        sys_msg = f"Analistsin. Metni {target_lang} dilinde özetle. Format: [ÖZET] ||| METİN"

    try:
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": text[:20000]}]
        )
        full_res = res.choices[0].message.content
        
        if "|||" in full_res:
            lang_tag, content = full_res.split("|||", 1)
            return lang_tag.strip().replace("[", "").replace("]", ""), content.strip()
        else:
            return "Otomatik", full_res

    except Exception as e: return "Hata", str(e)

def create_audio(text, lang_name, speed=False):
    code_map = {"Türkçe": "tr", "İngilizce": "en", "Almanca": "de", "Fransızca": "fr", "İspanyolca": "es", "Rusça": "ru", "Arapça": "ar", "Çince": "zh"}
    lang_code = code_map.get(lang_name, "en")
    try:
        fp = io.BytesIO()
        gTTS(text=text, lang=lang_code, slow=speed).write_to_fp(fp)
        return fp.getvalue()
    except: return None

def render_share(text):
    if not text: return
    encoded = urllib.parse.quote(text)
    wa = f"https://api.whatsapp.com/send?text={encoded}"
    st.markdown(f"<a href='{wa}' target='_blank' style='text-decoration:none; color:#25D366; font-weight:bold; font-size:0.85rem;'>📲 WhatsApp</a>", unsafe_allow_html=True)

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
    st.markdown("### 📊 Panel")
    st.markdown(f"<div class='metric-card'><div class='metric-val'>{st.session_state.stats_trans}</div><div class='metric-lbl'>Toplam Çeviri</div></div>", unsafe_allow_html=True)
    
    st.divider()
    st.markdown("### ⚙️ Ses Ayarı")
    # Hız Ayarı
    speech_slow = st.checkbox("🐢 Yavaş Okuma Modu", value=False)
    
    st.divider()
    st.markdown("### 📚 Sözlük (Glossary)")
    with st.expander("Terim Ekle"):
        glossary_txt = st.text_area("Örn: AI=Yapay Zeka", height=80)

    st.divider()
    st.markdown("### 🕒 Geçmiş")
    if st.session_state.history:
        for item in st.session_state.history[:5]:
            st.caption(f"• {item['src']}")
        if st.button("Temizle", type="secondary"): st.session_state.history = []; st.rerun()

# --- BAŞLIK ---
st.markdown('<div class="header-logo">LinguaFlow Infinity</div>', unsafe_allow_html=True)

# --- SEKMELER ---
tab_text, tab_files, tab_voice, tab_web = st.tabs(["📝 Metin", "📂 Dosya (Kıyaslamalı)", "🎙️ Ses", "🔗 Web"])
LANG_OPTIONS = ["English", "Türkçe", "Deutsch", "Français", "Español", "Italiano", "Русский", "العربية", "中文"]

# --- 1. METİN ---
with tab_text:
    c1, c2, c3 = st.columns([3, 1, 3])
    with c1: st.markdown("**Kaynak**")
    with c3: target_lang = st.selectbox("Hedef", LANG_OPTIONS, label_visibility="collapsed")

    col_in, col_out = st.columns(2)
    with col_in:
        input_text = st.text_area("Giriş", height=300, placeholder="Metin...", label_visibility="collapsed")
        
        b1, b2, b3 = st.columns([3, 3, 2])
        with b1:
            if st.button("Çevir ➔"):
                if input_text:
                    with st.spinner("..."):
                        lang, txt = ai_engine(input_text, "translate", target_lang, glossary=glossary_txt)
                        st.session_state.res_text = txt
                        st.session_state.detected_lang = lang
                        # Geçmiş
                        ts = datetime.datetime.now().strftime("%H:%M")
                        st.session_state.history.insert(0, {"time": ts, "src": input_text[:20]+"..", "res": txt})
        with b2:
            if st.button("✨ Düzelt"):
                if input_text:
                    with st.spinner("..."):
                        lang, txt = ai_engine(input_text, "improve")
                        st.session_state.res_text = txt
                        st.session_state.detected_lang = lang
        with b3: tone = st.selectbox("Ton", ["Normal", "Resmi", "Samimi"], label_visibility="collapsed")

    with col_out:
        res = st.session_state.res_text
        d_lang = st.session_state.detected_lang
        
        st.markdown(f"""
        <div class="result-box">
            <div style="color:#94a3b8; font-size:0.8rem; margin-bottom:5px;">{f'Algılanan: {d_lang}' if d_lang else ''}</div>
            {res if res else '...'}
        </div>
        """, unsafe_allow_html=True)
        
        if res:
            st.write("")
            ca, cb = st.columns([1, 3])
            with ca:
                aud = create_audio(res, target_lang, speech_slow) # Hız ayarı eklendi
                if aud: st.audio(aud, format="audio/mp3")
            with cb: render_share(res)

# --- 2. DOSYA (SPLIT VIEW - YENİ) ---
with tab_files:
    st.write("📂 **PDF** veya **Ses** yükleyin. Yan yana kıyaslama yapın.")
    u_file = st.file_uploader("", type=['pdf', 'mp3', 'wav', 'm4a'], label_visibility="collapsed")
    
    if u_file:
        f_target = st.selectbox("Dil", LANG_OPTIONS, key="f_tgt")
        if st.button("Analiz Et ve Çevir"):
            with st.spinner("Dosya işleniyor..."):
                raw = local_read_file(u_file)
                if raw and len(raw)>10:
                    mode = "translate" if len(raw) < 3000 else "summarize"
                    lang, res = ai_engine(raw, mode, f_target, glossary=glossary_txt)
                    
                    # SPLIT VIEW (YAN YANA)
                    st.write("---")
                    sc1, sc2 = st.columns(2)
                    with sc1:
                        st.markdown("**📄 Orijinal Metin**")
                        st.markdown(f"<div class='compare-box src-view'>{raw[:5000]}...</div>", unsafe_allow_html=True)
                    with sc2:
                        st.markdown(f"**🌍 Çeviri ({f_target})**")
                        st.markdown(f"<div class='compare-box trg-view'>{res}</div>", unsafe_allow_html=True)
                    
                    # Rapor İndirme
                    report = f"--- ORİJİNAL ---\n{raw}\n\n--- ÇEVİRİ ---\n{res}"
                    st.download_button("📥 Tam Raporu İndir", report, "dosya_rapor.txt")
                else: st.error("Hata.")

# --- 3. SES ---
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
                aud = create_audio(res, target_lang, speech_slow)
                st.markdown(f"<div class='result-box' style='min-height:100px; border-left:4px solid #3b82f6'>{txt}<br><br><b>{res}</b></div>", unsafe_allow_html=True)
                if aud: st.audio(aud, format="audio/mp3", autoplay=True)
        with c2:
            st.warning(f"MİSAFİR ({target_lang})")
            a2 = audio_recorder(text="", icon_size="3x", key="v2", recording_color="#ec4899", neutral_color="#fce7f3")
            if a2:
                txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(a2)), model="whisper-large-v3").text
                lang, res = ai_engine(txt, "translate", "Türkçe", glossary=glossary_txt)
                aud = create_audio(res, "Türkçe", speech_slow)
                st.markdown(f"<div class='result-box' style='min-height:100px; border-right:4px solid #ec4899; text-align:right'>{txt}<br><br><b>{res}</b></div>", unsafe_allow_html=True)
                if aud: st.audio(aud, format="audio/mp3", autoplay=True)

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
                        lang, trans = ai_engine(txt, "translate", target_lang, glossary=glossary_txt)
                        
                        # Split View
                        sc1, sc2 = st.columns(2)
                        with sc1: st.info(txt)
                        with sc2: st.success(trans)
                        
                        st.download_button("İndir", f"{txt}\n{trans}", "kayit.txt")
                    except: st.error("Ses yok.")

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
