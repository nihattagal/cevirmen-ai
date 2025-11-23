import streamlit as st
from groq import Groq
from audio_recorder_streamlit import audio_recorder
from gtts import gTTS
import io
import requests
from bs4 import BeautifulSoup
import PyPDF2
import datetime

# --- 1. GENEL AYARLAR ---
st.set_page_config(
    page_title="LinguaFlow Ultimate",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS TASARIM (PREMIUM) ---
st.markdown("""
    <style>
    /* Genel */
    .stApp { background-color: #f9fafb; font-family: 'Inter', sans-serif; }
    
    /* Başlık */
    .header-logo { 
        font-size: 2rem; font-weight: 800; color: #1e3a8a; 
        margin-bottom: 5px; letter-spacing: -0.5px;
    }
    .header-sub { color: #64748b; margin-bottom: 25px; font-size: 0.95rem; }
    
    /* Metin Alanı */
    .stTextArea textarea {
        border: 1px solid #e2e8f0; border-radius: 12px;
        font-size: 1.1rem; height: 280px !important; padding: 15px;
        background: white; box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        resize: none;
    }
    .stTextArea textarea:focus { border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59,130,246,0.1); }
    
    /* Sonuç Kutusu */
    .result-box {
        background-color: white; border: 1px solid #e2e8f0; border-radius: 12px;
        min-height: 280px; padding: 20px; font-size: 1.1rem; color: #1e293b;
        white-space: pre-wrap; box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    
    /* Butonlar */
    div.stButton > button {
        background-color: #1e3a8a; color: white; border: none; border-radius: 8px;
        padding: 12px; font-weight: 600; width: 100%; transition: all 0.2s;
    }
    div.stButton > button:hover { background-color: #1e40af; transform: translateY(-1px); }
    
    /* İkincil Butonlar (Temizle vs) */
    .secondary-btn div.stButton > button {
        background-color: #f1f5f9; color: #475569; border: 1px solid #cbd5e1;
    }
    .secondary-btn div.stButton > button:hover { background-color: #e2e8f0; color: #1e293b; }

    /* Geçmiş Öğeleri */
    .history-item {
        padding: 10px; margin-bottom: 8px; background: white; border-radius: 8px;
        font-size: 0.85rem; border-left: 4px solid #3b82f6; color: #475569;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    .history-time { font-size: 0.7rem; color: #94a3b8; margin-bottom: 2px; }
    </style>
""", unsafe_allow_html=True)

# --- 3. API BAĞLANTISI ---
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("⚠️ API Key Hatası! Lütfen Secrets ayarlarını kontrol edin.")
    st.stop()

# --- 4. STATE YÖNETİMİ ---
if "history" not in st.session_state: st.session_state.history = []
if "res_text" not in st.session_state: st.session_state.res_text = ""
if "input_val" not in st.session_state: st.session_state.input_val = ""

# --- 5. FONKSİYONLAR ---
def ai_engine(text, task, target_lang="English", tone="Normal"):
    if not text: return ""
    
    if task == "translate":
        sys_msg = f"""
        Sen uzman bir tercümansın.
        Hedef Dil: {target_lang}. Ton: {tone}.
        GÖREV: Metni en doğal ve akıcı şekilde çevir.
        KURAL: Asla açıklama ekleme, sadece çeviriyi ver.
        """
    elif task == "improve":
        sys_msg = "Sen kıdemli bir editörsün. Metni gramer, akıcılık ve stil açısından mükemmelleştir. Dili değiştirme."
    elif task == "summarize":
        sys_msg = f"Sen bir analistsin. Metni {target_lang} dilinde özetle. Önemli noktaları madde madde yaz."

    try:
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": text[:15000]}]
        )
        result = res.choices[0].message.content
        
        # Geçmişe Kayıt
        timestamp = datetime.datetime.now().strftime("%d/%m %H:%M")
        short_src = (text[:30] + '..') if len(text) > 30 else text
        # İşlem türüne göre etiket
        icon = "🌍" if task == "translate" else ("✨" if task == "improve" else "📝")
        
        st.session_state.history.insert(0, {
            "time": timestamp,
            "src": short_src,
            "res": result, # Tam sonucu sakla (ileride detay için)
            "type": icon
        })
            
        return result
    except Exception as e: return f"Hata: {e}"

def create_audio(text, lang_name):
    code_map = {
        "Türkçe": "tr", "English": "en", "Deutsch": "de", "Français": "fr", 
        "Español": "es", "Italiano": "it", "Português": "pt", "Polski": "pl",
        "Русский": "ru", "العربية": "ar", "中文": "zh", "日本語": "ja"
    }
    lang_code = code_map.get(lang_name, "en")
    try:
        fp = io.BytesIO()
        gTTS(text=text, lang=lang_code, slow=False).write_to_fp(fp)
        return fp.getvalue()
    except: return None

def local_read_file(file):
    try:
        if file.name.endswith('.pdf'):
            reader = PyPDF2.PdfReader(file)
            return "".join([page.extract_text() for page in reader.pages])
        else: 
            return client.audio.transcriptions.create(file=("a.wav", file), model="whisper-large-v3").text
    except: return None

# ==========================================
# ARAYÜZ
# ==========================================

# --- YAN MENÜ (AKILLI GEÇMİŞ) ---
with st.sidebar:
    st.markdown("### 🕒 İşlem Geçmişi")
    
    if st.session_state.history:
        # Geçmişi listele (En son en üstte)
        for item in st.session_state.history[:10]:
            st.markdown(f"""
            <div class="history-item">
                <div class="history-time">{item['time']}</div>
                {item['type']} {item['src']}
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown('<div class="secondary-btn">', unsafe_allow_html=True)
        if st.button("🗑️ Geçmişi Temizle"):
            st.session_state.history = []
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.caption("Henüz bir işlem yapılmadı.")
    
    st.divider()
    st.info("💡 **Bilgi:** Sohbet modunda mikrofon uzun süreli (20sn) dinleme yapabilir.")

# --- ÜST BAŞLIK ---
st.markdown('<div class="header-logo">LinguaFlow Ultimate</div><div class="header-sub">Yapay Zeka Destekli Dil Merkezi</div>', unsafe_allow_html=True)

# --- SEKMELER ---
tab_text, tab_conf, tab_files, tab_web = st.tabs(["📝 Metin & Yazım", "🎙️ Ortam & Toplantı", "📂 Dosya & Belge", "🔗 Web Analiz"])

# --- GLOBAL DİL LİSTESİ ---
LANG_OPTIONS = ["English", "Türkçe", "Deutsch", "Français", "Español", "Italiano", "Português", "Polski", "Русский", "العربية", "中文", "日本語"]

# --- 1. METİN SEKMESİ ---
with tab_text:
    c1, c2, c3 = st.columns([3, 1, 3])
    with c1: st.markdown("**Giriş (Otomatik Algılanır)**")
    with c3: target_lang = st.selectbox("Hedef Dil", LANG_OPTIONS, label_visibility="collapsed")

    col_in, col_out = st.columns(2)
    with col_in:
        # Metin girişini state'e bağladık (Temizleme için)
        input_text = st.text_area("Giriş", value=st.session_state.input_val, height=280, placeholder="Metni buraya yapıştırın...", label_visibility="collapsed")
        
        b1, b2, b3, b4 = st.columns([3, 3, 2, 1])
        with b1:
            if st.button("Çevir ➔"):
                if input_text:
                    with st.spinner("Çevriliyor..."):
                        st.session_state.res_text = ai_engine(input_text, "translate", target_lang)
                        st.session_state.input_val = input_text # State'i koru
        with b2:
            if st.button("✨ Düzelt (Write)"):
                if input_text:
                    with st.spinner("İyileştiriliyor..."):
                        st.session_state.res_text = ai_engine(input_text, "improve")
        with b3:
            tone = st.selectbox("Ton", ["Normal", "Resmi", "Samimi"], label_visibility="collapsed")
        with b4:
            st.markdown('<div class="secondary-btn">', unsafe_allow_html=True)
            if st.button("🗑️"): # Temizle Butonu
                st.session_state.input_val = ""
                st.session_state.res_text = ""
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    with col_out:
        res = st.session_state.res_text
        st.markdown(f"""<div class="result-box">{res if res else '<span style="color:#aaa;">Sonuç burada görünecek...</span>'}</div>""", unsafe_allow_html=True)
        
        if res:
            st.write("")
            ca, cc = st.columns([1, 4])
            with ca:
                aud = create_audio(res, target_lang)
                if aud: st.audio(aud, format="audio/mp3")
            with cc:
                st.code(res, language=None)

# --- 2. KONFERANS SEKMESİ ---
with tab_conf:
    st.info("🎙️ **Canlı Dinleme:** Toplantı veya ortam konuşmalarını dinler, bitince çevirir.")
    
    c_conf1, c_conf2 = st.columns([1, 3])
    with c_conf1:
        conf_target = st.selectbox("Çeviri Dili", LANG_OPTIONS, key="conf_t")
        st.write("")
        audio_conf = audio_recorder(text="🔴 BAŞLAT / BİTİR", icon_size="2x", recording_color="#d32f2f", pause_threshold=20.0)
    
    with c_conf2:
        if audio_conf:
            with st.spinner("Analiz ediliyor..."):
                try:
                    conf_text = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(audio_conf)), model="whisper-large-v3").text
                    conf_trans = ai_engine(conf_text, "translate", target_lang=conf_target)
                    
                    # Split View (Yan Yana)
                    c_src, c_trg = st.columns(2)
                    with c_src:
                        st.markdown(f"**🗣️ Duyulan:**")
                        st.info(conf_text)
                    with c_trg:
                        st.markdown(f"**🤖 Çeviri ({conf_target}):**")
                        st.success(conf_trans)
                    
                    # Dinamik Dosya Adı
                    t_stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
                    st.download_button("📥 Raporu İndir", f"Kaynak: {conf_text}\n\nÇeviri: {conf_trans}", f"Toplanti_{t_stamp}.txt")
                except: st.error("Ses anlaşılamadı.")

# --- 3. DOSYA SEKMESİ ---
with tab_files:
    st.write("📂 **PDF** veya **Ses Dosyası** yükleyin.")
    u_file = st.file_uploader("", type=['pdf', 'mp3', 'wav', 'm4a'], label_visibility="collapsed")
    
    if u_file:
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            st.info(f"Dosya: {u_file.name}")
            f_target = st.selectbox("Hedef Dil", LANG_OPTIONS, key="f_tgt")
            
            if st.button("Analiz Et ve Çevir"):
                with st.spinner("İşleniyor..."):
                    raw = local_read_file(u_file)
                    if raw and len(raw) > 10:
                        mode = "translate" if len(raw) < 3000 else "summarize"
                        st.session_state.f_res = ai_engine(raw, mode, f_target)
                        st.toast("İşlem Başarılı!", icon="✅")
                    else: st.error("Dosya okunamadı.")

        with col_f2:
            if "f_res" in st.session_state:
                st.success("Sonuç:")
                st.markdown(f"<div class='result-box'>{st.session_state.f_res}</div>", unsafe_allow_html=True)
                
                t_stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
                st.download_button("📥 İndir", st.session_state.f_res, f"Dosya_Analiz_{t_stamp}.txt")

# --- 4. WEB SEKMESİ ---
with tab_web:
    w_url = st.text_input("Web Sitesi Adresi (URL)")
    w_target = st.selectbox("Rapor Dili", LANG_OPTIONS, key="w_tgt")
    
    if st.button("Siteyi Oku ve Özetle") and w_url:
        with st.spinner("Site okunuyor..."):
            try:
                h = {'User-Agent': 'Mozilla/5.0'}
                soup = BeautifulSoup(requests.get(w_url, headers=h, timeout=10).content, 'html.parser')
                raw = " ".join([p.get_text() for p in soup.find_all(['p', 'h1', 'h2'])])[:10000]
                
                web_res = ai_engine(raw, "summarize", w_target)
                st.success("Site Özeti:")
                st.markdown(f"<div class='result-box'>{web_res}</div>", unsafe_allow_html=True)
                
                t_stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
                st.download_button("📥 İndir", web_res, f"Web_Ozet_{t_stamp}.txt")
            except: st.error("Siteye erişilemedi.")

st.divider()
st.caption("LinguaFlow AI v7.0 © 2024")
