import streamlit as st
from groq import Groq
from audio_recorder_streamlit import audio_recorder
from gtts import gTTS
import io

st.set_page_config(page_title="AI Çevirmen", layout="centered")

st.title("🗣️ Profesyonel AI Çevirmen")

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

# Sidebar
with st.sidebar:
    st.header("⚙️ Ayarlar")
    user_mode = st.selectbox("Mod:", ("Resmi", "Samimi", "Turist", "Agresif"))
    target_lang_name = st.selectbox("Hedef Dil:", ("İngilizce", "Türkçe", "Almanca", "İspanyolca", "Fransızca"))
    
    lang_codes = {"İngilizce": "en", "Türkçe": "tr", "Almanca": "de", "İspanyolca": "es", "Fransızca": "fr"}
    target_lang_code = lang_codes[target_lang_name]

    if st.button("🗑️ Sohbeti Temizle"):
        st.session_state.chat_history = []
        st.rerun()

# --- MİKROFON ---
st.write("Mikrofona basıp konuşun (Kayıt başlar), tekrar basıp durdurun (Çeviri yapar):")
audio_bytes = audio_recorder(
    text="",
    recording_color="#e8b62c",
    neutral_color="#6aa36f",
    icon_name="microphone",
    icon_size="3x",
)

# --- İŞLEM ---
if audio_bytes:
    with st.spinner('Çevriliyor ve Seslendiriliyor...'):
        try:
            # 1. Ses Dosyasını Okunabilir Hale Getir
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = "audio.wav"
            
            # 2. Whisper (Duyma)
            transcription = client.audio.transcriptions.create(
                file=("audio.wav", audio_file), 
                model="whisper-large-v3",
                response_format="text"
            )
            
            # 3. Llama (Çevirme - Sade Prompt)
            system_prompt = f"Sen profesyonel bir çevirmensin. Mod: {user_mode}. Hedef Dil: {target_lang_name}. Sadece çeviriyi yaz, başka yorum yapma."
            
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": transcription}
                ],
            )
