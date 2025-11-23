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
    page_title="LinguaFlow Elite",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS TASARIM ---
st.markdown("""
    <style>
    .stApp { background-color: #f0f2f5; font-family: 'Helvetica Neue', sans-serif; }
    
    .header-logo { 
        font-size: 2rem; font-weight: 800; color: #111b21; 
        text-align: center; margin-top: -20px; letter-spacing: -0.5px;
    }
    
    .stTextArea textarea {
        border: 1px solid #dadce0; border-radius: 8px;
        font-size: 1.1rem; height: 250px !important; padding: 15px;
        background: white; resize: none;
    }
    .stTextArea textarea:focus { border-color: #00a884; box-shadow: 0 0 0 2px rgba(0, 168, 132, 0.2); }
    
    .result-box {
        background-color: white; border: 1px solid #dadce0; border-radius: 8px;
        min-height: 250px; padding: 20px; font-size: 1.1rem; color: #111b21;
        white-space: pre-wrap; position: relative;
    }
    
    div.stButton > button {
        background-color: #008069; color: white; border: none; border-radius: 20px;
        padding: 10px 20px; font-weight: 600; width: 100%; transition: all 0.2s;
    }
    div.stButton > button:hover { background-color: #00a884; transform: translateY(-1px); }
    
    .secondary-btn div.stButton > button { background-color: #e9edef; color: #54656f; }
    .secondary-btn div.stButton > button:hover { background-color: #d1d7db; color: #111b21; }

    /* WhatsApp Tarzı Balonlar */
    .chat-bubble-me {
        align-self: flex-end; background-color: #d9fdd3; 
        padding: 10px 15px; border-radius: 10px 0 10px 10px;
        max-width: 80%; margin-left: auto; text-align: right; color: #111b21; margin-bottom: 5px;
    }
    .chat-bubble-you {
        align-self: flex-start; background-color: #ffffff; 
        padding: 10px 15px; border-radius: 0 10px 10px 10px;
        max-width: 80%; margin-right: auto; text-align: left; color: #111b21; margin-bottom: 5px;
    }
    
    .lang-badge {
        position: absolute; top: 10px; right: 10px;
        background: #e7fce3; color: #135c2c; padding: 4px 10px;
        border-radius: 12px; font-size: 0.75rem; font-weight: 700;
    }
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
if "chat_messages" not in st.session_state: st.session_state.chat_messages = []
if "res_text" not in st.session_state: st.session_state.res_text = ""
if "input_val" not in st.session_state: st.session_state.input_val = ""
if "detected_lang" not in st.session_state: st.session_state.detected_lang = ""
if "total_words" not in st.session_state: st.session_state.total_words = 0

# --- 5. MOTOR ---
def ai_engine(text, task, target_lang="English", tone="Normal", glossary="", extra_prompt=""):
    if not text: return "", ""
    
    st.session_state.total_words += len(text.split())
    glossary_prompt = f"TERMİNOLOJİ: \n{glossary}" if glossary else ""

    if task == "translate":
        sys_msg = f"""
        Sen uzman tercümansın. Hedef: {target_lang}. Ton: {tone}.
        {glossary_prompt}
        GÖREV: Kaynak dili algıla ve çevir.
        ÇIKTI: [ALGILANAN_DİL] ||| METİN
        """
    elif task == "improve":
        sys_msg = "Editörsün. Metni düzelt. Format: [DİL] ||| METİN"
    elif task == "summarize":
        sys_msg = f"Analistsin. Metni {target_lang} dilinde özetle. Format: [ÖZET] ||| METİN"
    elif task == "custom":
        sys_msg = f"Görev: {extra_prompt}. Hedef Dil: {target_lang}. Format: [ANALİZ] ||| METİN"

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
            return "AI", full_res

    except Exception as e: return "Hata", str(e)

def create_audio(text, lang_name, speed=False):
    code_map = {"Türkçe": "tr", "İngilizce": "en", "Almanca": "de", "Fransızca": "fr", "Español": "es", "Rusça": "ru", "Arapça": "ar", "Çince": "zh"}
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
    st.markdown(f"<a href='{wa}' target='_blank' style='text-decoration:none; color:#00a884; font-weight:bold; font-size:0.85rem;'>📲 WhatsApp'ta Paylaş</a>", unsafe_allow_html=True)

def local_read_file(file):
    try:
        if file.name.endswith('.pdf'):
            reader = PyPDF2.PdfReader(file)
            return "".join([page.extract_text() for page in reader.pages])
        else: return client.audio.transcriptions.create(file=("a.wav", file), model="whisper-large-v3").text
    except: return None

def local_read_web(url):
    try:
        h = {'User-Agent': 'Mozilla/5.0'}
        soup = BeautifulSoup(requests.get(url, headers=h, timeout=10).content, 'html.parser')
        return " ".join([p.get_text() for p in soup.find_all(['p', 'h1', 'h2'])])[:15000]
    except: return None

# ==========================================
# ARAYÜZ
# ==========================================

# --- YAN MENÜ (AYARLAR) ---
with st.sidebar:
    st.markdown("### ⚙️ Platform Ayarı")
    
    # PLATFORM ANAHTARI (Web'de gizle, Mobilde aç)
    is_mobile_mode = st.toggle("📱 Mobil Uygulama Modu", value=False, help="Canlı sohbet özelliğini açmak için aktif edin.")
    
    st.divider()
    st.info(f"**İşlenen Kelime:** {st.session_state.total_words}")
    
    speech_slow = st.checkbox("🐢 Yavaş Okuma", value=False)
    with st.expander("📚 Sözlük"):
        glossary_txt = st.text_area("Örn: Lingua=Dil", height=70)

    st.divider()
    if st.session_state.history:
        st.markdown("### 🕒 Geçmiş")
        for item in st.session_state.history[:5]:
            st.caption(f"• {item['src']}")
        if st.button("Temizle", key="cl_hist"):
            st.session_state.history = []
            st.rerun()

# --- BAŞLIK ---
st.markdown('<div class="header-logo">LinguaFlow Elite</div>', unsafe_allow_html=True)

# --- DİNAMİK SEKMELER ---
# Eğer Mobil Mod açıksa Sohbet sekmesini ekle, değilse gizle.
if is_mobile_mode:
    tab_list = ["📝 Metin Çeviri", "💬 Canlı Sohbet (App)", "📂 Dosya & PDF", "🔗 Web"]
    tabs = st.tabs(tab_list)
    t_text, t_chat, t_file, t_web = tabs[0], tabs[1], tabs[2], tabs[3]
else:
    tab_list = ["📝 Metin Çeviri", "📂 Dosya & PDF", "🔗 Web"]
    tabs = st.tabs(tab_list)
    t_text, t_file, t_web = tabs[0], tabs[1], tabs[2]
    t_chat = None # Web modunda bu sekme yok

LANG_OPTIONS = ["English", "Türkçe", "Deutsch", "Français", "Español", "Italiano", "Русский", "العربية", "中文"]

# --- 1. METİN ---
with t_text:
    c1, c2, c3, c4 = st.columns([3, 1, 3, 1])
    with c1: st.markdown("**Kaynak (Otomatik)**")
    with c3: 
        if "target_idx" not in st.session_state: st.session_state.target_idx = 0
        target_lang = st.selectbox("Hedef", LANG_OPTIONS, index=st.session_state.target_idx, label_visibility="collapsed")
    
    with c2:
        st.markdown('<div class="secondary-btn">', unsafe_allow_html=True)
        if st.button("⇄"):
             st.session_state.target_idx = 1 if st.session_state.target_idx == 0 else 0
             st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    col_in, col_out = st.columns(2)
    
    with col_in:
        # Dikte sadece mobil modda mı çıksın? Hayır, web'de de kullanışlı olabilir.
        # Ama istenirse buraya da `if is_mobile_mode:` eklenebilir.
        mc, tc = st.columns([1, 8])
        with mc: audio_in = audio_recorder(text="", icon_size="2x", recording_color="#25D366", neutral_color="#cbd5e1", key="dict")
        with tc: st.caption("Sesle Yaz")
        
        if audio_in:
            with st.spinner("..."):
                txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(audio_in)), model="whisper-large-v3").text
                st.session_state.input_val = txt
                st.rerun()

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
                ts = datetime.datetime.now().strftime("%H:%M")
                st.session_state.history.insert(0, {"time": ts, "src": input_text[:20]+".."})

    with col_out:
        st.write("") 
        st.write("")
        
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
                    st.session_state.input_val = ""; st.session_state.res_text = ""; st.session_state.detected_lang = ""; st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            with cc: render_share(res)

# --- 2. SOHBET (SADECE MOBİL MODDA GÖRÜNÜR) ---
if is_mobile_mode and t_chat:
    with t_chat:
        st.info("🗣️ **Uygulama Modu Aktif:** Bu özellik telefon mikrofonu ile karşılıklı konuşma içindir.")
        
        c1, c2 = st.columns(2)
        with c1:
            st.write(f"🎤 **BEN (Konuş)**")
            a1 = audio_recorder(text="", icon_size="3x", key="v1", recording_color="#25D366", neutral_color="#e9edef")
            if a1:
                txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(a1)), model="whisper-large-v3").text
                lang, res = ai_engine(txt, "translate", target_lang, glossary=glossary_txt).split("|||")[-1], ai_engine(txt, "translate", target_lang, glossary=glossary_txt)
                st.session_state.chat_messages.append({"role": "me", "src": txt, "trg": res, "lang": lang})
        
        with c2:
            st.write(f"🎤 **MİSAFİR ({target_lang})**")
            a2 = audio_recorder(text="", icon_size="3x", key="v2", recording_color="#34b7f1", neutral_color="#e9edef")
            if a2:
                txt = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(a2)), model="whisper-large-v3").text
                res = ai_engine(txt, "translate", "Türkçe", glossary=glossary_txt).split("|||")[-1]
                st.session_state.chat_messages.append({"role": "you", "src": txt, "trg": res, "lang": target_lang})

        st.divider()
        
        if st.session_state.chat_messages:
            for msg in reversed(st.session_state.chat_messages):
                if msg['role'] == 'me':
                    st.markdown(f"""<div class="chat-bubble-me"><div>{msg['src']}</div><div style="font-weight:bold; margin-top:5px;">{msg['trg']}</div></div>""", unsafe_allow_html=True)
                else:
                    st.markdown(f"""<div class="chat-bubble-you"><div>{msg['src']}</div><div style="font-weight:bold; margin-top:5px;">{msg['trg']}</div></div>""", unsafe_allow_html=True)
                    
            if st.button("Sohbeti Temizle"):
                st.session_state.chat_messages = []; st.rerun()

# --- 3. DOSYA ---
with t_file:
    st.write("📂 **PDF** veya **Ses** yükleyin.")
    u_file = st.file_uploader("", type=['pdf', 'mp3', 'wav', 'm4a'], label_visibility="collapsed")
    
    if u_file:
        c_act, c_lang = st.columns(2)
        with c_act: action = st.selectbox("İşlem", ["Çevir", "Özetle", "Gramer Kontrolü"])
        with c_lang: f_target = st.selectbox("Dil", LANG_OPTIONS, key="f_tgt")
            
        if st.button("Başlat"):
            with st.spinner("..."):
                raw = local_read_file(u_file)
                if raw:
                    prompt_map = {
                        "Çevir": f"Metni {f_target} diline çevir.",
                        "Özetle": f"Metni {f_target} dilinde özetle.",
                        "Gramer Kontrolü": "Metindeki hataları bul ve düzelt."
                    }
                    lang, res = ai_engine(raw, "custom", f_target, extra_prompt=prompt_map[action])
                    st.markdown(f"<div class='result-box'>{res}</div>", unsafe_allow_html=True)
                    st.download_button("İndir", res, "sonuc.txt")
                else: st.error("Hata.")

# --- 4. WEB ---
with t_web:
    url = st.text_input("Web Sitesi Adresi (URL)")
    w_target = st.selectbox("Rapor Dili", LANG_OPTIONS, key="w_tgt")
    if st.button("Analiz Et") and url:
        with st.spinner("..."):
            txt = local_read_web(url)
            if txt:
                lang, res = ai_engine(txt, "summarize", w_target)
                st.markdown(f"<div class='result-box'>{res}</div>", unsafe_allow_html=True)
                st.download_button("İndir", res, "web.txt")
            else: st.error("Hata.")

st.divider()
