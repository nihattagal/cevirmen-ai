import streamlit as st
from groq import Groq
from streamlit_audiorecorder import audiorecorder

st.set_page_config(page_title="AI Çevirmen")

st.title("🎤 AI Canlı Çevirmen")

# Sol Menü
with st.sidebar:
    st.header("Ayarlar")
    api_key = st.text_input("Groq API Anahtarı:", type="password")
    user_mode = st.selectbox("Mod:", ("Resmi", "Samimi", "Turist"))
    target_lang = st.selectbox("Hedef Dil:", ("İngilizce", "Türkçe", "Almanca"))

if not api_key:
    st.warning("Lütfen API anahtarını girin.")
    st.stop()

client = Groq(api_key=api_key)

# Ses Kaydedici
st.write("Mikrofon butonuna basın, konuşun ve tekrar basıp durdurun:")
audio = audiorecorder("Başlat", "Durdur")

if len(audio) > 0:
    # 1. Kaydı Oynat
    st.audio(audio.export().read())

    # 2. Kaydı Dosyaya Yaz
    audio.export("temp.wav", format="wav")

    with st.spinner('Çevriliyor...'):
        try:
            # Whisper (Sesi Yazıya Dök)
            with open("temp.wav", "rb") as file:
                transcription = client.audio.transcriptions.create(
                    file=("temp.wav", file.read()),
                    model="whisper-large-v3",
                    response_format="text"
                )
            
            st.success(f"Algılanan: {transcription}")

            # Llama 3 (Çeviri Yap)
            completion = client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    {"role": "system", "content": f"Sen çevirmensin. Mod: {user_mode}. Hedef Dil: {target_lang}. Sadece çeviriyi yaz."},
                    {"role": "user", "content": transcription}
                ],
            )
            
            st.markdown(f"### 🚀 {completion.choices[0].message.content}")

        except Exception as e:
            st.error(f"Hata: {e}")
