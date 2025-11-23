import streamlit as st
from groq import Groq
from audio_recorder_streamlit import audio_recorder # <-- YENİSİ BU OLMALI
import io

st.set_page_config(page_title="AI Çevirmen", layout="centered")

st.title("🎤 AI Canlı Çevirmen")

# Sidebar
with st.sidebar:
    st.header("Ayarlar")
    api_key = st.text_input("Groq API Anahtarı:", type="password")
    user_mode = st.selectbox("Mod:", ("Resmi", "Samimi", "Turist", "Agresif"))
    target_lang = st.selectbox("Hedef Dil:", ("İngilizce", "Türkçe", "Almanca", "İspanyolca"))

if not api_key:
    st.warning("Lütfen API anahtarını girin.")
    st.stop()

try:
    client = Groq(api_key=api_key)
except:
    st.error("API Anahtarı hatalı.")
    st.stop()

st.write("Mikrofon butonuna basarak konuşun (Kayıt başlar), tekrar basarak durdurun (Çeviri yapar):")

# --- YENİ KAYDEDİCİ ---
audio_bytes = audio_recorder(
    text="",
    recording_color="#e8b62c",
    neutral_color="#6aa36f",
    icon_name="microphone",
    icon_size="2x",
)

if audio_bytes:
    # 1. Sesi oynat
    st.audio(audio_bytes, format="audio/wav")
    
    with st.spinner('Çevriliyor...'):
        try:
            # BytesIO ile dosyayı sanal olarak oluşturuyoruz
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = "audio.wav"
            
            # Whisper (Sesi Yazıya Dök)
            transcription = client.audio.transcriptions.create(
                file=("audio.wav", audio_file), 
                model="whisper-large-v3",
                response_format="text"
            )
            
            st.success(f"Algılanan: {transcription}")
            
            # Llama 3 (Çeviri Yap)
            system_prompt = f"Sen çevirmensin. Mod: {user_mode}. Hedef: {target_lang}. Sadece çeviriyi yaz."
            
            completion = client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": transcription}
                ],
            )
            
            st.markdown(f"### 🚀 {completion.choices[0].message.content}")
            
        except Exception as e:
            st.error(f"Hata oluştu: {str(e)}")
