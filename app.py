import streamlit as st
from groq import Groq
from audio_recorder_streamlit import audio_recorder
from gtts import gTTS
import io

st.set_page_config(page_title="AI Çevirmen", layout="centered")

st.title("🗣️ Sesli AI Çevirmen")

# --- GÜVENLİK ---
try:
    api_key = st.secrets["GROQ_API_KEY"]
except:
    st.error("API anahtarı bulunamadı! Secrets ayarlarını kontrol et.")
    st.stop()

client = Groq(api_key=api_key)

# --- HAFIZA (SESSION STATE) ---
# Eğer hafıza yoksa oluştur, varsa eskisini kullan
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Sidebar
with st.sidebar:
    st.header("⚙️ Ayarlar")
    user_mode = st.selectbox("Mod:", ("Resmi", "Samimi", "Turist", "Agresif"))
    target_lang_name = st.selectbox("Hedef Dil:", ("İngilizce", "Türkçe", "Almanca", "İspanyolca", "Fransızca"))
    
    # Seslendirme için dil kodları
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

# --- MİKROFON ---
st.write("Mikrofona basıp konuşun:")
audio_bytes = audio_recorder(
    text="",
    recording_color="#e8b62c",
    neutral_color="#6aa36f",
    icon_name="microphone",
    icon_size="3x",
)

# --- İŞLEM ---
if audio_bytes:
    # Sadece yeni bir kayıt varsa işlem yap
    with st.spinner('Çevriliyor...'):
        try:
            # 1. Ses Dosyasını Hazırla
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = "audio.wav"
            
            # 2. Whisper (Duyma)
            transcription = client.audio.transcriptions.create(
                file=("audio.wav", audio_file), 
                model="whisper-large-v3",
                response_format="text"
            )
            
            # 3. Llama (Çevirme)
            system_prompt = f"Sen çevirmensin. Mod: {user_mode}. Hedef: {target_lang_name}. Sadece çeviriyi yaz."
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": transcription}
                ],
            )
            translation = completion.choices[0].message.content

            # 4. Seslendirme (TTS)
            tts = gTTS(text=translation, lang=target_lang_code, slow=False)
            audio_io = io.BytesIO()
            tts.write_to_fp(audio_io)
            audio_io.seek(0)
            
            # 5. Hafızaya Kaydet
            st.session_state.chat_history.append({
                "user": transcription,
                "ai": translation,
                "audio": audio_io
            })
            
        except Exception as e:
            st.error(f"Hata: {str(e)}")

# --- EKRANA YAZDIRMA (Sohbet Görünümü) ---
# En yeniden eskiye doğru göstermek için ters çevirip döngüye sokuyoruz
for chat in reversed(st.session_state.chat_history):
    with st.container(border=True):
        st.info(f"🎤 **Sen:** {chat['user']}")
        st.success(f"🤖 **Çeviri:** {chat['ai']}")
        # Ses oynatıcı
        st.audio(chat['audio'], format="audio/mp3")
