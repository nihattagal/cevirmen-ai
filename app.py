import streamlit as st
from groq import Groq
from audio_recorder_streamlit import audio_recorder
from gtts import gTTS
import io
import datetime

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="AI Tercüman Pro",
    page_icon="🧠",
    layout="centered"
)

# --- BAŞLIK ---
st.markdown("<h1 style='text-align: center; color: #4B0082;'>🧠 AI Tercüman Pro</h1>", unsafe_allow_html=True)

# --- GÜVENLİK ---
try:
    api_key = st.secrets["GROQ_API_KEY"]
except:
    st.error("API anahtarı bulunamadı! Secrets ayarlarını kontrol et.")
    st.stop()

client = Groq(api_key=api_key)

# --- HAFIZA ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- KENAR ÇUBUĞU ---
with st.sidebar:
    st.header("🎛️ Ayarlar")
    
    # 1. Mod
    work_mode = st.radio("Çalışma Modu:", ("⚡ Sohbet", "🔴 Konferans"), horizontal=True)
    
    # 2. Dil
    target_lang_name = st.selectbox("Hedef Dil:", ("Türkçe", "İngilizce", "Almanca", "İspanyolca", "Fransızca", "Rusça", "Arapça", "Japonca", "Çince"))
    
    lang_codes = {
        "İngilizce": "en", "Türkçe": "tr", "Almanca": "de", 
        "İspanyolca": "es", "Fransızca": "fr", "Rusça": "ru", 
        "Arapça": "ar", "Japonca": "ja", "Çince": "zh"
    }
    target_lang_code = lang_codes[target_lang_name]

    # 3. YENİ ÖZELLİK: HIZ AYARI
    st.divider()
    tts_slow = st.checkbox("🐢 Yavaş Okuma Modu", value=False)
    st.divider()

    # 4. Sekreter
    st.subheader("📝 AI Asistan")
    if st.button("Toplantı Özeti Çıkar", type="secondary", use_container_width=True):
        if len(st.session_state.chat_history) > 0:
            with st.spinner("Analiz ediliyor..."):
                full_text = ""
                for chat in st.session_state.chat_history:
                    full_text += f"- {chat['user']} (Mod: {chat.get('mood', 'Nötr')})\n"
                
                summary_prompt = f"""
                Sen profesyonel bir asistansın. Aşağıdaki metni analiz et. Hedef Dil: {target_lang_name}.
                ÇIKTI:
                1. 📋 Genel Özet
                2. ✅ Kararlar
                3. 📌 Görevler
                Metin: {full_text}
                """
                summary_res = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": summary_prompt}]
                )
                st.session_state.summary_result = summary_res.choices[0].message.content
        else:
            st.warning("Kayıt yok.")

    # Temizle
    if st.button("🗑️ Her Şeyi Sil", type="primary", use_container_width=True):
        st.session_state.chat_history = []
        if "summary_result" in st.session_state: del st.session_state.summary_result
        st.rerun()

# --- ÖZET GÖSTERİMİ ---
if "summary_result" in st.session_state:
    st.success("📝 Rapor Hazır")
    st.info(st.session_state.summary_result)
    if st.button("Kapat"):
        del st.session_state.summary_result
        st.rerun()

# --- ANA EKRAN (SEKMELER) ---
tab1, tab2 = st.tabs(["🎙️ Canlı Mikrofon", "📂 Dosya Yükle"])

# --- FONKSİYON: SES İŞLEME MOTORU (Kod tekrarını önlemek için) ---
def process_audio(audio_file_input, source_name="Mikrofon"):
    with st.spinner(f'{source_name} işleniyor...'):
        try:
            # 1. Duy (Whisper)
            transcription = client.audio.transcriptions.create(
                file=("audio.wav", audio_file_input), 
                model="whisper-large-v3",
                response_format="text"
            )
            
            # 2. Çevir + Analiz
            system_prompt = f"""
            Sen uzman tercümansın. Hedef Dil: {target_lang_name}.
            GÖREV:
            1. Duyguyu tek kelimeyle bul (Kızgın, Mutlu, Ciddi, Nötr).
            2. Çeviriyi yap.
            FORMAT: DUYGU ||| METİN
            """
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": transcription}
                ],
            )
            full_res = completion.choices[0].message.content

            if "|||" in full_res:
                parts = full_res.split("|||")
                mood = parts[0].strip()
                translation = parts[1].strip()
            else:
                mood = "Nötr"
                translation = full_res

            # 3. Seslendir (Hız ayarlı)
            tts = gTTS(text=translation, lang=target_lang_code, slow=tts_slow)
            audio_fp = io.BytesIO()
            tts.write_to_fp(audio_fp)
            audio_data = audio_fp.getvalue()
            
            # 4. Kaydet
            st.session_state.chat_history.append({
                "user": transcription,
                "ai": translation,
                "mood": mood,
                "audio": audio_data
            })
            st.rerun() # Ekranı yenile ki mesaj görünsün
            
        except Exception as e:
            st.error(f"Hata: {str(e)}")

# --- SEKME 1: MİKROFON ---
with tab1:
    if work_mode == "⚡ Sohbet":
        icon_color = "#e8b62c" 
        pause_limit = 2.0 
        st.info("Bas-Konuş Modu")
    else:
        icon_color = "#FF0000" 
        pause_limit = 300.0 
        st.warning("Konferans Modu (Sürekli)")

    col1, col2, col3 = st.columns([1, 10, 1])
    with col2:
        mic_audio = audio_recorder(text="", recording_color=icon_color, neutral_color="#333333", icon_name="microphone", icon_size="5x", pause_threshold=pause_limit, sample_rate=44100)
    
    if mic_audio:
        audio_file = io.BytesIO(mic_audio)
        audio_file.name = "audio.wav"
        process_audio(audio_file, "Mikrofon")

# --- SEKME 2: DOSYA YÜKLEME ---
with tab2:
    st.write("📁 **Ses dosyası yükleyin (MP3, WAV, M4A)**")
    uploaded_file = st.file_uploader("Dosya Seç", type=['wav', 'mp3', 'm4a', 'ogg'])
    
    if uploaded_file is not None:
        if st.button("🚀 Dosyayı Çevir ve Analiz Et"):
            # Dosyayı direkt işleyebiliriz
            process_audio(uploaded_file, "Dosya")

# --- SOHBET GEÇMİŞİ ---
st.divider()
mood_icons = {"Kızgın": "😡", "Mutlu": "😊", "Üzgün": "😢", "Ciddi": "😐", "Nötr": "😶"}

for chat in reversed(st.session_state.chat_history):
    with st.container():
        current_mood = chat.get('mood', 'Nötr')
        icon = "😶"
        for key, val in mood_icons.items():
            if key in current_mood: icon = val; break
        
        st.markdown(f"**🗣️ Kaynak:** {chat['user']}")
        st.info(f"{icon} **Duygu:** {current_mood}")
        st.code(chat['ai'], language=None)
        st.audio(chat['audio'], format="audio/mp3")
        st.divider()
