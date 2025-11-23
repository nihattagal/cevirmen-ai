import streamlit as st
from groq import Groq
from audio_recorder_streamlit import audio_recorder
from gtts import gTTS
import io
import datetime

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="AI Tercüman",
    page_icon="🌍",
    layout="centered"
)

# --- BAŞLIK VE TASARIM ---
st.markdown("""
    <h1 style='text-align: center; color: #FF4B4B;'>🌍 AI Cep Tercümanı</h1>
    <p style='text-align: center;'>Bas • Konuş • Dinle</p>
""", unsafe_allow_html=True)

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

# --- KENAR ÇUBUĞU (AYARLAR) ---
with st.sidebar:
    st.header("⚙️ Kontrol Paneli")
    
    st.subheader("Davranış")
    user_mode = st.selectbox("Mod:", ("Resmi", "Samimi", "Turist", "Agresif"))
    
    st.subheader("Çeviri Hedefi")
    target_lang_name = st.selectbox("Hangi Dile Çevilsin?", ("İngilizce", "Türkçe", "Almanca", "İspanyolca", "Fransızca", "Rusça", "Arapça"))
    
    # Dil Kodları (Genişletildi)
    lang_codes = {
        "İngilizce": "en", "Türkçe": "tr", "Almanca": "de", 
        "İspanyolca": "es", "Fransızca": "fr", "Rusça": "ru", "Arapça": "ar"
    }
    target_lang_code = lang_codes[target_lang_name]

    st.divider()

    # --- YENİ ÖZELLİK: İNDİRME BUTONU ---
    # Sohbet geçmişini metne dönüştür
    chat_text = ""
    for chat in st.session_state.chat_history:
        chat_text += f"🗣️ Sen: {chat['user']}\n🤖 AI: {chat['ai']}\n-------------------\n"
    
    # İndirme butonu
    st.download_button(
        label="📥 Sohbeti İndir (TXT)",
        data=chat_text,
        file_name=f"ceviri_gecmisi_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.txt",
        mime="text/plain"
    )

    if st.button("🗑️ Sohbeti Temizle", type="primary"):
        st.session_state.chat_history = []
        st.rerun()

# --- MİKROFON ALANI ---
# Ortalamak için sütun kullanıyoruz
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.write("🎙️ **Kaydı Başlat / Bitir:**")
    audio_bytes = audio_recorder(
        text="",
        recording_color="#ff4b4b",
        neutral_color="#333333",
        icon_name="microphone",
        icon_size="4x", # Buton daha büyük
    )

# --- İŞLEM ---
if audio_bytes:
    with st.spinner('Ses analizi yapılıyor...'):
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
            system_prompt = f"Sen profesyonel bir tercümansın. Mod: {user_mode}. Hedef Dil: {target_lang_name}. Sadece çeviriyi ver."
            
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

# --- SOHBET GÖRÜNÜMÜ ---
st.divider()
for chat in reversed(st.session_state.chat_history):
    with st.container():
        # Mesaj balonları tasarımı
        st.markdown(f"""
        <div style="background-color: #f0f2f6; padding: 10px; border-radius: 10px; margin-bottom: 5px;">
            <p style="margin:0;"><b>🗣️ Sen:</b> {chat['user']}</p>
        </div>
        <div style="background-color: #d1e7dd; padding: 10px; border-radius: 10px; margin-bottom: 10px;">
            <p style="margin:0;"><b>🤖 Çeviri ({target_lang_name}):</b> {chat['ai']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Ses oynatıcı
        st.audio(chat['audio'], format="audio/mp3")
        st.divider()
