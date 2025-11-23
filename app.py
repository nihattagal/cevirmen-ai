import streamlit as st
from groq import Groq
from audio_recorder_streamlit import audio_recorder
from gtts import gTTS
import io
import datetime

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="AI Canlı Tercüman",
    page_icon="🧠",
    layout="centered"
)

# --- BAŞLIK ---
st.markdown("<h1 style='text-align: center; color: #4B0082;'>🧠 Empatik AI Tercüman</h1>", unsafe_allow_html=True)

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
    st.header("🎛️ Kontrol Paneli")
    
    st.subheader("Mikrofon Modu")
    work_mode = st.radio(
        "Nasıl çalışsın?",
        ("⚡ Telsiz Modu (Sohbet)", "🔴 Konferans Modu (Sürekli)"),
        help="Telsiz: Kısa cümleler.\nKonferans: 5 dk boyunca dinler."
    )
    
    st.divider()
    
    target_lang_name = st.selectbox("Hedef Dil:", ("İngilizce", "Türkçe", "Almanca", "İspanyolca", "Fransızca", "Rusça", "Arapça", "Japonca", "Çince"))
    
    lang_codes = {
        "İngilizce": "en", "Türkçe": "tr", "Almanca": "de", 
        "İspanyolca": "es", "Fransızca": "fr", "Rusça": "ru", 
        "Arapça": "ar", "Japonca": "ja", "Çince": "zh"
    }
    target_lang_code = lang_codes[target_lang_name]

    # İndirme Butonu
    chat_text = ""
    for chat in st.session_state.chat_history:
        mood_info = chat.get('mood', 'Nötr')
        chat_text += f"Kaynak: {chat['user']}\nAnaliz: {mood_info}\nÇeviri: {chat['ai']}\n-------------------\n"
    
    st.download_button(
        label="📥 Dökümü İndir (TXT)",
        data=chat_text,
        file_name=f"konusma_{datetime.datetime.now().strftime('%H%M')}.txt",
        mime="text/plain"
    )

    if st.button("🗑️ Temizle", type="primary"):
        st.session_state.chat_history = []
        st.rerun()

# --- MİKROFON ALANI ---
st.divider()

if work_mode == "⚡ Telsiz Modu (Sohbet)":
    st.info("💡 **Sohbet Modu:** Bas-Konuş. Kısa diyaloglar için.")
    icon_color = "#e8b62c" 
    pause_limit = 2.0 
else:
    st.warning("🔴 **Konferans Modu:** SÜREKLİ DİNLEME. 'Bitir' diyene kadar kapanmaz.")
    icon_color = "#FF0000" 
    pause_limit = 300.0 

col1, col2, col3 = st.columns([1, 10, 1])
with col2:
    audio_bytes = audio_recorder(
        text="",
        recording_color=icon_color,
        neutral_color="#333333",
        icon_name="microphone",
        icon_size="5x",
        pause_threshold=pause_limit,
        sample_rate=44100
    )

# --- İŞLEM ---
if audio_bytes:
    with st.spinner('Ses analizi ve duygu tespiti yapılıyor...'):
        try:
            # A. Sesi Hazırla
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = "audio.wav"
            
            # B. Duy (Whisper)
            transcription = client.audio.transcriptions.create(
                file=("audio.wav", audio_file), 
                model="whisper-large-v3",
                response_format="text"
            )
            
            # C. Çevir + Analiz Et
            system_prompt = f"""
            Sen uzman bir tercüman ve psikologsun.
            Hedef Dil: {target_lang_name}.
            
            GÖREVİN:
            1. Metindeki duygu durumunu tek kelimeyle analiz et.
            2. Metni hedef dile çevir.
            
            KURALLAR:
            - Eğer kullanıcı "Alo", "Ses", "Test" diyorsa DUYGU yerine "Nötr" yaz.
            - Emin değilsen "Nötr" yaz.
            - Duygular: Kızgın, Mutlu, Ciddi, Heyecanlı, Üzgün, Nötr, Şaşkın.
            
            CEVAP FORMATI:
            DUYGU_DURUMU ||| ÇEVRİLMİŞ_METİN
            """

            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": transcription}
                ],
            )
            full_response = completion.choices[0].message.content

            # Cevabı Parçala
            if "|||" in full_response:
                parts = full_response.split("|||")
                mood = parts[0].strip()
                translation = parts[1].strip()
            else:
                mood = "Nötr"
                translation = full_response

            # D. Seslendir
            tts = gTTS(text=translation, lang=target_lang_code, slow=False)
            audio_fp = io.BytesIO()
            tts.write_to_fp(audio_fp)
            audio_data = audio_fp.getvalue()
            
            # E. Kaydet
            st.session_state.chat_history.append({
                "user": transcription,
                "ai": translation,
                "mood": mood,
                "audio": audio_data
            })
            
        except Exception as e:
            st.error(f"Hata: {str(e)}")

# --- SOHBET GÖRÜNÜMÜ ---
st.divider()

mood_icons = {
    "Kızgın": "😡", "Öfkeli": "😡", "Sinirli": "😠",
    "Mutlu": "😊", "Sevinçli": "😁", "Heyecanlı": "🤩",
    "Üzgün": "😢", "Endişeli": "😟", "Kırgın": "💔",
    "Ciddi": "😐", "Resmi": "👔",
    "Şaşkın": "😲",
    "Nötr": "😶", "Normal": "😶"
}

for chat in reversed(st.session_state.chat_history):
    with st.container():
        current_mood = chat.get('mood', 'Nötr')
        
        # İkon Bulma
        icon = "😶"
        for key, val in mood_icons.items():
            if key in current_mood:
                icon = val
                break
        
        # GÜVENLİ GÖRÜNÜM KODU (Hata çıkaran kısım düzeltildi)
        st.markdown(f"**🗣️ Kaynak:** {chat['user']}")
        st.info(f"{icon} **Duygu:** {current_mood}")
        st.code(chat['ai'], language=None)
        st.audio(chat['audio'], format="audio/mp3")
        st.divider()
