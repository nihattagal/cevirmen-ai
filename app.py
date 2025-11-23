import streamlit as st
from groq import Groq

# Sayfa Ayarları
st.set_page_config(page_title="AI Çevirmen", layout="centered")

st.title("🎤 AI Canlı Çevirmen")

# Sidebar
with st.sidebar:
    st.header("Ayarlar")
    api_key = st.text_input("Groq API Anahtarı:", type="password")
    user_mode = st.selectbox("Mod:", ("Resmi", "Samimi", "Turist", "Agresif"))
    target_lang = st.selectbox("Hedef Dil:", ("İngilizce", "Türkçe", "Almanca", "İspanyolca"))

if not api_key:
    st.info("Lütfen soldan API anahtarını girin.")
    st.stop()

client = Groq(api_key=api_key)

# --- YENİ SES KAYDEDİCİ ---
audio_value = st.audio_input("Mikrofona tıklayıp konuşun")

if audio_value:
    # 1. Sesi ekranda oynat
    st.audio(audio_value)
    
    # KİLİT NOKTA: Dosyayı okuduktan sonra başa sarıyoruz!
    audio_value.seek(0)
    
    with st.spinner('Çevriliyor...'):
        try:
            # Whisper'a gönder
            transcription = client.audio.transcriptions.create(
                file=("input.wav", audio_value), 
                model="whisper-large-v3",
                response_format="text"
            )
            
            detected_text = transcription
            st.success(f"Algılanan: {detected_text}")
            
            # Çeviri yap
            system_prompt = f"Sen çevirmensin. Mod: {user_mode}. Hedef: {target_lang}. Sadece çeviriyi yaz."
            
            completion = client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": detected_text}
                ],
                temperature=0.7
            )
            
            st.markdown(f"### 🚀 {completion.choices[0].message.content}")
            
        except Exception as e:
            st.error(f"Hata detayı: {e}")
