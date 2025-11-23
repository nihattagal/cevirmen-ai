import streamlit as st
from groq import Groq
from audio_recorder_streamlit import audio_recorder
from gtts import gTTS
import io
import requests
from bs4 import BeautifulSoup
import PyPDF2

# --- 1. GENEL AYARLAR (DeepL Tarzı Geniş Ekran) ---
st.set_page_config(page_title="LinguaFlow Translator", page_icon="🌐", layout="wide")

# --- 2. CSS (DeepL GÖRÜNÜMÜ) ---
st.markdown("""
    <style>
    /* Arkaplan */
    .stApp { background-color: #F3F5F7; font-family: 'Segoe UI', sans-serif; }
    
    /* Üst Başlık */
    .header-logo { font-size: 1.8rem; font-weight: 700; color: #0F2B46; margin-bottom: 20px; }
    
    /* Metin Kutuları (DeepL Tarzı) */
    .stTextArea textarea {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        font-size: 1.2rem;
        color: #333;
        height: 300px !important; /* Sabit yükseklik */
        padding: 15px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        resize: none; /* Boyutlandırmayı kapat */
    }
    .stTextArea textarea:focus {
        border-color: #4E89E8; /* Mavi odak */
        box-shadow: 0 0 0 1px #4E89E8;
    }
    
    /* Sonuç Kutusu (Sağ Taraf) */
    .result-container {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        height: 300px;
        padding: 15px;
        font-size: 1.2rem;
        color: #0F2B46;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        overflow-y: auto;
    }
    
    /* Butonlar */
    div.stButton > button {
        background-color: #0F2B46; /* Lacivert */
        color: white;
        border: none;
        border-radius: 6px;
        padding: 10px 25px;
        font-weight: 600;
        transition: 0.2s;
    }
    div.stButton > button:hover {
        background-color: #264B75;
    }
    
    /* Sekmeler */
    .stTabs [data-baseweb="tab-list"] {
        gap: 30px;
        border-bottom: 1px solid #ddd;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 1.1rem;
        font-weight: 500;
        color: #555;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        color: #0F2B46;
        border-bottom: 3px solid #0F2B46;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. API BAĞLANTISI ---
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("Sistem hatası: API Anahtarı bulunamadı.")
    st.stop()

# --- 4. FONKSİYONLAR ---
def ai_engine(text, task, target_lang="English", tone="Normal"):
    if not text: return ""
    
    if task == "translate":
        # DeepL gibi sadece çeviriye odaklı prompt
        sys_msg = f"""
        You are a professional translator like DeepL.
        Target Language: {target_lang}.
        Tone: {tone}.
        Task: Translate the text naturally and accurately. Do not add explanations.
        """
    elif task == "improve":
        # DeepL Write modu
        sys_msg = "You are an expert editor. Improve the grammar, clarity, and style of the text. Keep the same language. Output only the improved text."
    
    elif task == "summarize":
        sys_msg = f"Summarize this text in {target_lang}. Format: Bullet points."

    try:
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": text[:10000]}]
        )
        return res.choices[0].message.content
    except Exception as e: return f"Hata: {e}"

def create_audio(text, lang_name):
    code_map = {"Turkish": "tr", "English": "en", "German": "de", "French": "fr", "Spanish": "es", "Russian": "ru", "Arabic": "ar"}
    try:
        fp = io.BytesIO()
        gTTS(text=text, lang=code_map.get(lang_name, "en"), slow=False).write_to_fp(fp)
        return fp.getvalue()
    except: return None

def local_read_file(file):
    try:
        if file.name.endswith('.pdf'):
            reader = PyPDF2.PdfReader(file)
            return "".join([page.extract_text() for page in reader.pages])
        else: # Ses dosyası ise (Transkripsiyon)
            return client.audio.transcriptions.create(file=("a.wav", file), model="whisper-large-v3").text
    except: return "Dosya okunamadı."

# ==========================================
# ARAYÜZ (DEEPL LAYOUT)
# ==========================================

st.markdown('<div class="header-logo">LinguaFlow</div>', unsafe_allow_html=True)

# ANA MENÜ (SEKMELER)
tab_text, tab_files, tab_conv = st.tabs(["📝 Metin Çevirisi", "📂 Dosya Çevirisi (.pdf / .mp3)", "🗣️ Canlı Sohbet"])

# --- 1. SEKME: METİN ÇEVİRİSİ (DeepL Klonu) ---
with tab_text:
    # Dil Seçimi Satırı
    c1, c2, c3 = st.columns([3, 1, 3])
    with c1:
        st.markdown("**Kaynak Metin (Otomatik Algılanır)**")
    with c3:
        target_lang = st.selectbox("Hedef Dil", ["English", "Turkish", "German", "French", "Spanish", "Russian", "Arabic"], label_visibility="collapsed")

    # Kutular Satırı
    col_input, col_output = st.columns(2)
    
    with col_input:
        # Giriş Kutusu
        input_text = st.text_area("Giriş", height=300, placeholder="Çevirmek istediğiniz metni buraya yazın...", label_visibility="collapsed")
        
        # Alt Butonlar (Sol)
        b1, b2 = st.columns([1, 1])
        with b1:
            if st.button("✨ Düzelt / İyileştir (Write)", help="Metni dil bilgisi açısından düzeltir."):
                if input_text:
                    with st.spinner("İyileştiriliyor..."):
                        st.session_state.result = ai_engine(input_text, "improve")
        
    with col_output:
        # Sonuç Kutusu (Dinamik)
        if "result" not in st.session_state: st.session_state.result = ""
        
        # Çeviri Tetikleyici (Butonlu - DeepL'de otomatiktir ama Streamlit'te buton daha stabildir)
        if st.button("Çevir ➔", type="primary", use_container_width=True):
            if input_text:
                with st.spinner("Çevriliyor..."):
                    st.session_state.result = ai_engine(input_text, "translate", target_lang)
        
        # Sonucu Göster
        st.markdown(f"""
        <div class="result-container">
            {st.session_state.result if st.session_state.result else '<span style="color:#aaa;">Çeviri burada görünecek...</span>'}
        </div>
        """, unsafe_allow_html=True)
        
        # Araçlar (Kopyala, Dinle)
        if st.session_state.result:
            tools1, tools2 = st.columns([1, 4])
            with tools1:
                audio_bytes = create_audio(st.session_state.result, target_lang)
                if audio_bytes: st.audio(audio_bytes, format="audio/mp3")
            with tools2:
                st.code(st.session_state.result, language=None) # Kopyalama için pratik yol

# --- 2. SEKME: DOSYA ÇEVİRİSİ ---
with tab_files:
    st.markdown("#### 📂 Belge veya Ses Dosyası Yükle")
    uploaded_file = st.file_uploader("PDF veya Ses (MP3/WAV)", type=['pdf', 'mp3', 'wav', 'm4a'])
    
    if uploaded_file:
        # Dosya Türüne Göre İşlem
        file_type = "Belge" if uploaded_file.name.endswith('.pdf') else "Ses"
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            st.info(f"Yüklenen: {uploaded_file.name} ({file_type})")
            if file_type == "Ses": st.audio(uploaded_file)
            
            tgt_file = st.selectbox("Çevrilecek Dil", ["Turkish", "English", "German"], key="file_tgt")
            
            if st.button("Dosyayı Çevir"):
                with st.spinner(f"{file_type} okunuyor ve çevriliyor..."):
                    # 1. İçeriği Oku
                    raw_text = local_read_file(uploaded_file)
                    
                    # 2. Çevir
                    if len(raw_text) > 50:
                        trans_text = ai_engine(raw_text, "translate", tgt_file)
                        st.session_state.file_result = trans_text
                        st.session_state.file_raw = raw_text
                    else:
                        st.error("Dosya içeriği okunamadı veya boş.")

        with col_f2:
            if "file_result" in st.session_state:
                st.success("✅ Çeviri Tamamlandı")
                st.text_area("Sonuç", st.session_state.file_result, height=300)
                st.download_button("İndir (TXT)", st.session_state.file_result, "ceviri.txt")

# --- 3. SEKME: SESLİ SOHBET ---
with tab_voice:
    st.markdown("#### 🗣️ Karşılıklı Konuşma")
    
    c_v1, c_v2 = st.columns(2)
    
    with c_v1:
        st.markdown("**Siz (Mikrofon)**")
        audio_in = audio_recorder(text="Bas ve Konuş", icon_size="3x", recording_color="#0F2B46", neutral_color="#ddd")
        
    with c_v2:
        v_target = st.selectbox("Karşı Tarafın Dili", ["English", "German", "French", "Spanish", "Arabic"])
        
    if audio_in:
        st.divider()
        with st.spinner("Ses işleniyor..."):
            # 1. Sesi Yazıya Dök (Whisper)
            try:
                transcript = client.audio.transcriptions.create(file=("a.wav", io.BytesIO(audio_in)), model="whisper-large-v3").text
                
                # 2. Çevir (Llama)
                translation = ai_engine(transcript, "translate", v_target)
                
                col_res1, col_res2 = st.columns(2)
                with col_res1:
                    st.info(f"🗣️ Algılanan:\n{transcript}")
                with col_res2:
                    st.success(f"🤖 Çeviri:\n{translation}")
                    # 3. Oku
                    out_audio = create_audio(translation, v_target)
                    if out_audio: st.audio(out_audio, format="audio/mp3", autoplay=True)
                    
            except Exception as e:
                st.error("Ses anlaşılamadı.")

# Alt Bilgi
st.divider()
st.caption("🔒 Gizlilik: Verileriniz kaydedilmez. LinguaFlow AI.")
