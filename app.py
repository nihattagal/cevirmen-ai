import streamlit as st
from groq import Groq
from streamlit_audiorecorder import audiorecorder
import os

# Sayfa Ayarları
st.set_page_config(page_title="AI Çevirmen", layout="centered")

# Başlık
st.title("🎤 AI Canlı Çevirmen")

# Kenar Çubuğu (Ayarlar)
with st.sidebar:
    st.header("⚙️ Ayarlar")
    
    # API Anahtarı Girişi (Güvenlik için şifreli giriş)
    api_key = st.text_input("Groq API Anahtarınızı Girin:", type="password")
    
    st.divider()
    
    # Kullanıcı Modu Seçimi
    user_mode = st.selectbox(
        "Çeviri Modu Seçin:",
        ("Resmi (İş Görüşmesi)", "Samimi (Arkadaş Ortamı)", "Turist (Basit ve Net)", "Agresif (Tartışma)")
    )
    
    # Hedef Dil Seçimi
    target_lang = st.selectbox(
        "Hangi Dile Çevrilecek?",
        ("İngilizce", "Türkçe", "Almanca", "İspanyolca", "Fransızca", "Japonca")
    )

    st.info("Not: Mikrofon butonuna basarak konuşun, durdurduğunuzda çeviri otomatik başlar.")

# Ana Ekran Akışı
if not api_key:
    st.warning("Lütfen sol menüden Groq API anahtarınızı girin.")
    st.stop()

try:
    client = Groq(api_key=api_key)
except Exception as e:
    st.error(f"API Anahtarı hatası: {e}")
    st.stop()

# Ses Kaydedici
audio = audiorecorder("Mikrofonu Başlat", "Kaydı Durdur")

if len(audio) > 0:
    # Sesi geçici olarak kaydet
    st.audio(audio.export().read())
    audio.export("temp_audio.wav", format="wav")
    
    with st.spinner('Ses analizi yapılıyor ve çevriliyor...'):
        try:
            # 1. Adım: Sesi Yazıya Dökme (Whisper)
            with open("temp_audio.wav", "rb") as file:
                transcription = client.audio.transcriptions.create(
                file=(filename, file.read()),
                model="whisper-large-v3",
                response_format="text"
            )
            
            detected_text = transcription
            st.success("Algılanan Konuşma:")
            st.write(f"🗣️ {detected_text}")
            
            # 2. Adım: Çeviri ve Kişilik (Llama 3)
            system_prompt = f"""
            Sen profesyonel bir çevirmensin. 
            Kullanıcının seçtiği mod: {user_mode}.
            Hedef Dil: {target_lang}.
            
            Görevlerin:
            1. Gelen metni hedef dile çevir.
            2. Bunu yaparken seçilen moda uygun bir ton kullan.
            3. Sadece çeviriyi ver, başka açıklama yapma.
            """
            
            completion = client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": detected_text}
                ],
                temperature=0.7,
                max_tokens=1024,
            )
            
            translation = completion.choices[0].message.content
            
            st.subheader(f"Çeviri ({target_lang}):")
            st.markdown(f"### 🚀 {translation}")
            
        except Exception as e:
            st.error(f"Bir hata oluştu: {e}")
