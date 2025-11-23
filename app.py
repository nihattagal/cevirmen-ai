import streamlit as st
from groq import Groq
from audio_recorder_streamlit import audio_recorder
from gtts import gTTS
import io

# Sayfa Ayarları
st.set_page_config(page_title="AI Çevirmen", layout="centered")

st.title("🗣️ Profesyonel AI Çevirmen")

# --- 1. GÜVENLİK (API Anahtarı Kontrolü) ---
try:
    api_key = st.secrets["GROQ_API_KEY"]
except:
    st.error("API anahtarı bulunamadı! Lütfen Streamlit ayarlarından 'Secrets' kısmını kontrol edin.")
    st.stop()

client = Groq(api_key=api_key)

# --- 2. HAFIZA (Sohbet Geçmişi) ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- 3. KENAR ÇUBUĞU (Ayarlar) ---
with st.sidebar:
    st.header("⚙️ Ayarlar")
    user_mode = st.selectbox("Mod:", ("Resmi", "Samimi", "Turist", "Agresif"))
    target_lang_name = st.selectbox("Hedef Dil:", ("İngilizce", "Türkçe", "Almanca", "İspanyolca", "Fransızca"))
    
    # Dil Kodları (Google TTS için)
    lang_codes = {
        "İngilizce": "en",
        "Türkçe": "tr",
        "Almanca": "de",
        "İspanyolca": "es",
        "Fransızca": "fr"
    }
    target_lang_code = lang_codes[target_lang_name]

    # Temizle Butonu
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

# --- 5. ANA İŞLEM (Duyma -> Çevirme -> Okuma) ---
if audio_bytes:
    with st.spinner('Çevriliyor ve Seslendiriliyor...'):
        try:
            # A. Sesi İşlenebilir Hale Getir
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = "audio.wav"
            
            # B. Whisper (Duyma - Sesi Yazıya Dök)
            transcription = client.audio.transcriptions.create(
                file=("audio.wav", audio_file), 
                model="whisper-large-v3",
                response_format="text"
            )
            
            # C. Llama (Çevirme)
            system_prompt = f"Sen profesyonel bir çevirmensin. Mod: {user_mode}. Hedef Dil: {target_lang_name}. Sadece çeviriyi yaz, yorum yapma."
            
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": transcription}
                ],
            )
            
            translation = completion.choices[0].message.content

            # D. Seslendirme (Text-to-Speech)
            tts = gTTS(text=translation, lang=target_lang_code, slow=False)
            audio_fp = io.BytesIO()
            tts.write_to_fp(audio_fp)
            # Sesi dondurup kaydediyoruz (Hata çıkmasın diye)
            audio_data = audio_fp.getvalue()
            
            # E. Hafızaya Ekle
            st.session_state.chat_history.append({
                "user": transcription,
                "ai": translation,
                "audio": audio_data
            })
            
        except Exception as e:
            st.error(f"Bir hata oluştu: {str(e)}")

# --- 6. EKRANA YAZDIRMA ---
# enumerate ve reversed kullanarak en yeniyi en üstte gösteriyoruz
for i, chat in enumerate(reversed(st.session_state.chat_history)):
    with st.container(border=True):
        st.info(f"🎤 **Sen:** {chat['user']}")
        st.success(f"🤖 **Çeviri:** {chat['ai']}")
        # Ses oynatıcıya benzersiz bir 'key' veriyoruz ki karışmasın
        st.audio(chat['audio'], format="audio/mp3", key=f"audio_{i}")
