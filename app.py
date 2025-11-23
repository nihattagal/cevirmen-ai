import streamlit as st
from groq import Groq
from audio_recorder_streamlit import audio_recorder
from gtts import gTTS
import io
import requests
from bs4 import BeautifulSoup
import PyPDF2

# --- 1. GENEL AYARLAR (DeepL Tarzı) ---
st.set_page_config(page_title="LinguaFlow", page_icon="🌐", layout="wide")

# --- 2. CSS (MODERN & TEMİZ) ---
st.markdown("""
    <style>
    /* Arkaplan */
    .stApp { background-color: #F3F5F7; font-family: 'Segoe UI', sans-serif; }
    
    /* Başlık */
    .header-logo { font-size: 2rem; font-weight: 800; color: #0F2B46; margin-bottom: 10px; }
    .header-sub { color: #666; margin-bottom: 30px; font-size: 1rem; }
    
    /* Metin Kutuları */
    .stTextArea textarea {
        background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px;
        font-size: 1.1rem; height: 250px !important; padding: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.02);
    }
    .stTextArea textarea:focus { border-color: #4E89E8; box-shadow: 0 0 0 1px #4E89E8; }
    
    /* Sonuç Kutusu */
    .result-box {
        background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px;
        min-height: 250px; padding: 15px; font-size: 1.1rem; color: #0F2B46;
        box-shadow: 0 2px 5px rgba(0,0,0,0.02); white-space: pre-wrap;
    }
    
    /* Konferans Modu Kutuları */
    .conf-box-src { background-color: #e8eaf6; padding: 15px; border-radius: 8px; border-left: 4px solid #3f51b5; color: #333; }
    .conf-box-trg { background-color: #e0f2f1; padding: 15px; border-radius: 8px; border-right: 4px solid #009688; color: #00695c; text-align: right; }

    /* Butonlar */
    div.stButton > button {
        background-color: #0F2B46; color: white; border: none; border-radius: 6px;
        padding: 12px; font-weight: 600; transition: 0.2s; width: 100%;
    }
    div.stButton > button:hover { background-color: #264B75; }
    
    /* Sekmeler */
    .stTabs [data-baseweb="tab-list"] { gap: 20px; border-bottom: 1px solid #ddd; }
    .stTabs [data-baseweb="tab"] { font-size: 1rem; font-weight: 600; color: #555; }
    .stTabs [aria-selected="true"] { color: #0F2B46; border-bottom: 3px solid #0F2B46; }
    </style>
""", unsafe_allow_html=True)

# --- 3. API BAĞLANTISI ---
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("Sistem Hatası: API Anahtarı bulunamadı.")
    st.stop()

# --- 4. FONKSİYONLAR ---
def ai_engine(text, task, target_lang="English", tone="Normal"):
    if not text: return ""
    
    if task == "translate":
        sys_msg = f"""
        Sen profesyonel bir simultane tercümansın.
        Hedef Dil: {target_lang}. Ton: {tone}.
        GÖREV: Metni akıcı ve doğal bir şekilde çevir. Açıklama yapma.
        """
    elif task == "improve":
        sys_msg = "Sen profesyonel bir editörsün. Metni gramer ve stil açısından düzelt. Dili değiştirme."
    
    try:
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": text[:15000]}]
        )
        return res.choices[0].message.content
    except Exception as e: return f"Hata: {e}"

def create_audio(text, lang_name):
    code_map = {"Türkçe": "tr", "İngilizce": "en", "Almanca": "de", "Fransızca": "fr", "İspanyolca": "es", "Rusça": "ru", "Arapça": "ar", "Çince": "zh"}
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
        else: # Ses
            return client.audio.transcriptions.create(file=("a.wav", file), model="whisper-large-v3").text
    except: return None

# ==========================================
# ARAYÜZ
# ==========================================

st.markdown('<div class="header-logo">LinguaFlow</div>', unsafe_allow_html=True)

# --- SEKMELER (4 ANA MOD) ---
tab_text, tab_conf, tab_files, tab_web = st.tabs(["📝 Metin & Yazım", "🎙️ Ortam Dinleme (Konferans)", "📂 Dosya & Belge", "🔗 Web Analiz"])

# --- 1. SEKME: METİN (DEEPL STİLİ) ---
with tab_text:
    c1, c2, c3 = st.columns([3, 1, 3])
    with c1: st.markdown("**Kaynak (Otomatik)**")
    with c3: target_lang = st.selectbox("Hedef Dil", ["English", "Turkish", "German", "French", "Spanish", "Russian", "Arabic"], label_visibility="collapsed")

    col_in, col_out = st.columns(2)
    with col_in:
        input_text = st.text_area("Giriş", height=250, placeholder="Metni buraya yapıştırın...", label_visibility="collapsed")
        
        b1, b2 = st.columns([1, 1])
        with b1:
            if st.button("Çevir ➔"):
                if input_text:
                    with st.spinner("Çevriliyor..."):
                        st.session_state.res_text = ai_engine(input_text, "translate", target_lang)
        with b2:
            if st.button("✨ Düzelt (Write)"):
                if input_text:
                    with st.spinner("Düzenleniyor..."):
                        st.session_state.res_text = ai_engine(input_text, "improve")

    with col_out:
        res = st.session_state.get("res_text", "")
        st.markdown(f"""<div class="result-box">{res if res else '<span style="color:#aaa;">Sonuç burada görünecek...</span>'}</div>""", unsafe_allow_html=True)
        if res:
            st.divider()
            ca, cc = st.columns([1, 3])
            with ca:
                aud = create_audio(res, target_lang)
                if aud: st.audio(aud, format="audio/mp3")
            with cc: st.code(res, language=None)

# --- 2. SEKME: ORTAM DİNLEME (YENİ EKLENEN ÖZELLİK) ---
with tab_conf:
    st.info("💡 Bu modda mikrofon, ortamdaki konuşmaları sürekli dinler (Toplantı, Ders, TV).")
    
    cc1, cc2 = st.columns([1, 3])
    with cc1:
        conf_target = st.selectbox("Çevrilecek Dil", ["Türkçe", "İngilizce", "Almanca", "Fransızca"], key="conf_lang")
        st.write("")
        # Yüksek bekleme süresi (30 sn sessizlik toleransı)
        audio_conf = audio_recorder(text="🔴 DİNLEMEYİ BAŞLAT / BİTİR", icon_size="2x", recording_color="#d32f2f", pause_threshold=30.0)
    
    with cc2:
        if audio_conf:
            with st.spinner("Ses analiz ediliyor ve çevriliyor..."):
                # 1. Sesi Yazıya Dök
                try:
                    conf_text = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(audio_conf)), model="whisper-large-v3").text
                    
                    # 2. Çevir
                    conf_trans = ai_engine(conf_text, "translate", target_lang=conf_target)
                    
                    # 3. Göster (Split View)
                    row1, row2 = st.columns(2)
                    with row1:
                        st.markdown("**🗣️ Duyulan (Orijinal):**")
                        st.markdown(f"<div class='conf-box-src'>{conf_text}</div>", unsafe_allow_html=True)
                    with row2:
                        st.markdown(f"**🤖 Çeviri ({conf_target}):**")
                        st.markdown(f"<div class='conf-box-trg'>{conf_trans}</div>", unsafe_allow_html=True)
                        
                    # 4. İndirme Butonları
                    st.divider()
                    d1, d2 = st.columns(2)
                    with d1: st.download_button("📥 Orijinal Metni İndir", conf_text, "toplanti_orijinal.txt")
                    with d2: st.download_button("📥 Çeviriyi İndir", conf_trans, "toplanti_ceviri.txt")
                    
                except Exception as e:
                    st.error("Ses algılanamadı veya çok kısaydı.")
        else:
            st.markdown("""
            <div style='text-align:center; padding:50px; color:#aaa; border: 2px dashed #ddd; border-radius:10px;'>
                Mikrofon butonuna basın ve konuşmaya başlayın.<br>
                Konuşma bitince butona tekrar basarak durdurun.
            </div>
            """, unsafe_allow_html=True)

# --- 3. SEKME: DOSYA ---
with tab_files:
    st.write("📂 **PDF Belgesi** veya **Ses Dosyası (MP3)** yükleyin.")
    u_file = st.file_uploader("Dosya Seç", type=['pdf', 'mp3', 'wav', 'm4a'])
    
    if u_file:
        ftype = "Belge" if u_file.name.endswith('.pdf') else "Ses"
        col_f1, col_f2 = st.columns(2)
        
        with col_f1:
            st.info(f"Dosya: {u_file.name}")
            if ftype == "Ses": st.audio(u_file)
            f_target = st.selectbox("Hedef Dil", ["Türkçe", "İngilizce", "Almanca"], key="f_tgt")
            
            if st.button("Analiz Et ve Çevir"):
                with st.spinner("İşleniyor..."):
                    raw = local_read_file(u_file)
                    if raw and len(raw) > 10:
                        # Eğer çok uzunsa özetle, kısaysa çevir
                        mode = "translate" if len(raw) < 2000 else "summarize" # Basit mantık
                        st.session_state.f_res = ai_engine(raw, mode, f_target)
                    else: st.error("Dosya boş veya okunamadı.")

        with col_f2:
            if "f_res" in st.session_state:
                st.success("✅ Sonuç:")
                st.markdown(f"<div class='result-box'>{st.session_state.f_res}</div>", unsafe_allow_html=True)
                st.download_button("İndir", st.session_state.f_res, "dosya_sonuc.txt")

# --- 4. SEKME: WEB ---
with tab_web:
    w_url = st.text_input("Web Sitesi Linki (URL)")
    if st.button("Siteyi Oku ve Özetle") and w_url:
        with st.spinner("Site okunuyor..."):
            try:
                h = {'User-Agent': 'Mozilla/5.0'}
                page_content = requests.get(w_url, headers=h, timeout=10).content
                soup = BeautifulSoup(page_content, 'html.parser')
                raw_web = " ".join([p.get_text() for p in soup.find_all(['p', 'h1', 'h2'])])[:10000]
                
                web_res = ai_engine(raw_web, "summarize", "Türkçe")
                st.success("Site Özeti:")
                st.markdown(f"<div class='result-box'>{web_res}</div>", unsafe_allow_html=True)
            except: st.error("Site okunamadı.")

st.divider()
st.caption("LinguaFlow AI © 2024")
