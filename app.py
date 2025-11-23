import streamlit as st
from groq import Groq
import os

# Sayfa Ayarları
st.set_page_config(page_title="AI Çevirmen", layout="centered")

st.title("🎤 AI Canlı Çevirmen")

# Kenar Çubuğu
with st.sidebar:
    st.header("⚙️ Ayarlar")
    api_key = st.text_input("Groq API Anahtarı:", type="password")
    st.divider()
    user_mode = st.selectbox("Mod:", ("Resmi", "Samimi", "Turist", "Agresif"))
    target_lang = st.selectbox("Hedef Dil:", ("İngilizce", "Türkçe", "Almanca", "İspanyolca", "Fransızca"))

if not api_key:
    st.warning("Lütfen API anahtarını girin.")
    st.stop()

try:
    client = Groq(api_key=api_key)
except Exception as e:
    st.error(f"API Hatası: {e}")
    st.stop()

# --- YENİ YÖNTEM: Dahili Ses Kaydedici ---
audio_value = st.audio_input("Ses kaydı için mikrofona tıklayın")

if audio_value:
    st.audio(audio_value)
    
    with st.spinner('Çevriliyor...'):
        try:
            # 1. Ses Dosyasını Hazırla
            # Whisper için dosyayı byte formatına çeviriyoruz
            transcription = client.audio.transcriptions.create(
                file=("input.wav", audio_value), 
                model="whisper-large-v3",
                response_format="text"
            )
            
            detected_text = transcription
            st.success("Algılanan:")
            st.write(f"🗣️ {detected_text}")
            
            # 2. Çeviri Yap
            system_prompt = f"Sen çevirmensin. Mod: {user_mode}. Hedef Dil: {target_lang}. Sadece çeviriyi yaz."
            
            completion = client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": detected_text}
                ],
                temperature=0.7
            )
            
            translation = completion.choices[0].message.content
            st.subheader("Çeviri:")
            st.markdown(f"### 🚀 {translation}")
            
        except Exception as e:
            st.error(f"Hata: {e}")
