import streamlit as st
from groq import Groq
from audio_recorder_streamlit import audio_recorder
from gtts import gTTS
import io

# Sayfa Ayarları
st.set_page_config(page_title="AI Çevirmen", layout="centered")

st.title("🗣️ Profesyonel AI Çevirmen")

# --- 1. GÜVENLİK ---
try:
    api_key = st.secrets["GROQ_API_KEY"]
except:
    st.error("API anahtarı bulunamadı! Secrets ayarlarını kontrol et.")
    st.stop()

client = Groq(api_key=api_key)

# --- 2. HAFIZA ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- 3. AYARLAR ---
with st.sidebar:
    st.header("⚙️ Ayarlar")
    user_mode = st.selectbox("Mod:", ("Resmi", "Samimi", "Turist", "Agresif"))
    target_lang_name = st.selectbox("Hedef Dil:", ("İngilizce", "Türkçe", "Almanca", "İspanyolca", "Fransızca"))
    
    lang_codes = {
        "İngilizce": "en",
        "Türkçe": "tr",
        "Almanca": "de",
        "İspanyolca": "es",
        "Fransızca": "fr"
    }
    target_lang_code = lang_codes[target_lang_name]

    if st.button("🗑️ Sohbeti Temizle"):
        st.session_state.chat_history = []
        st.rerun()

# --- 4. MİKROFON ---
st.write("Mikrofona basıp konuşun (Kayıt başlar), tekrar basıp durdurun (Çeviri yapar):")
audio_bytes = audio_recorder(
    text="",
    recording_color="#e8b62c",
    neutral_color="#6aa36f",
    icon_name="microphone",
    icon_size="3x",
)

# --- 5. İŞLEM ---
if audio_bytes:
    with st.spinner('Çevriliyor ve Seslendiriliyor...'):
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
            
            # C. Çevir (Llama)
            system_prompt = f"Sen profesyonel bir çevirmensin. Mod: {user_mode}. Hedef Dil: {target_lang_name}. Sadece çeviriyi yaz."
            
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": transcription}
                ],
            )
            
            translation = completion.choices[0].message.content

            # D. Seslendir (TTS)
            tts = gTTS(text=translation, lang=target_lang_code, slow=False)
            audio_fp = io.BytesIO()
            tts.write_to_fp(audio_fp)
            audio_data = audio_fp.getvalue()
            
            # E. Kaydet
            st.session_state.chat_history.append({
                "user": transcription,
                "ai": translation,
                "audio": audio_data
            })
            
        except Exception as e:
            st.error(f"Hata: {str(e)}")

# --- 6. EKRANA YAZDIRMA ---
for chat in reversed(st.session_state.chat_history):
    with st.container(border=True):
        st.info(f"🎤 **Sen:** {chat['user']}")
        st.success(f"🤖 **Çeviri:** {chat['ai']}")
        # DÜZELTME BURADA: key parametresini kaldırdık
        st.audio(chat['audio'], format="audio/mp3")
