import streamlit as st
from groq import Groq
from audio_recorder_streamlit import audio_recorder
import io

st.set_page_config(page_title="AI Çevirmen", layout="centered")

st.title("🎤 AI Canlı Çevirmen")

# --- GÜVENLİK ---
# Anahtarı kullanıcıdan değil, sunucunun gizli kasasından çekiyoruz
try:
    api_key = st.secrets["GROQ_API_KEY"]
except:
    st.error("Sunucu ayarlarında API anahtarı bulunamadı! Lütfen Secrets kısmını kontrol edin.")
    st.stop()

# Groq Bağlantısı
client = Groq(api_key=api_key)

# Sidebar (Sadece gerekli ayarlar kaldı)
with st.sidebar:
    st.header("Ayarlar")
    # API Anahtarı girişi ARTIK YOK
    user_mode = st.selectbox("Mod:", ("Resmi", "Samimi", "Turist", "Agresif"))
    target_lang = st.selectbox("Hedef Dil:", ("İngilizce", "Türkçe", "Almanca", "İspanyolca", "Fransızca"))

st.write("Mikrofona bas, konuş ve tekrar bas (Otomatik Çevirir):")

# Ses Kaydedici
audio_bytes = audio_recorder(
    text="",
    recording_color="#e8b62c",
    neutral_color="#6aa36f",
    icon_name="microphone",
    icon_size="3x", # Butonu biraz büyüttüm telefonda kolay basılsın diye
)

if audio_bytes:
    # 1. Kaydı Oynatma (İstersen burayı silebilirsin, sesini duymak istemezsen)
    st.audio(audio_bytes, format="audio/wav")
    
    with st.spinner('Yapay Zeka düşünüyor...'):
        try:
            # Dosya Hazırlığı
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = "audio.wav"
            
            # 1. Aşama: Sesi Anla (Whisper)
            transcription = client.audio.transcriptions.create(
                file=("audio.wav", audio_file), 
                model="whisper-large-v3",
                response_format="text"
            )
            
            # Ekrana ne anladığını yaz
            st.info(f"🗣️ Algılanan: {transcription}")
            
            # 2. Aşama: Çevir (Llama 3.3)
            system_prompt = f"Sen çevirmensin. Mod: {user_mode}. Hedef: {target_lang}. Sadece çeviriyi yaz."
            
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": transcription}
                ],
            )
            
            # Sonucu Ekrana Bas
            st.success("Çeviri:")
            st.markdown(f"## 🚀 {completion.choices[0].message.content}")
            
        except Exception as e:
            st.error(f"Bir hata oluştu: {str(e)}")
