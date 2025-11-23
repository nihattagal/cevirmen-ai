import streamlit as st
from groq import Groq
from audio_recorder_streamlit import audio_recorder
from gtts import gTTS
import io
import datetime

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="AI Canlı Tercüman",
    page_icon="🎙️",
    layout="centered"
)

# --- BAŞLIK ---
st.markdown("""
    <h1 style='text-align: center; color: #FF4B4B;'>🎙️ AI Canlı Tercüman</h1>
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

# --- KENAR ÇUBUĞU ---
with st.sidebar:
    st.header("🎛️ Kontrol Paneli")
    
    st.subheader("Mikrofon Modu")
    work_mode = st.radio(
        "Nasıl çalışsın?",
        ("⚡ Telsiz Modu (Sohbet)", "🔴 Konferans Modu (Sürekli)"),
        help="Telsiz: Kısa cümleler için.\nKonferans: Sen durdurana kadar kapanmaz."
    )
    
    st.divider()
    
    st.subheader("Davranış")
    user_style = st.selectbox("Çeviri Tarzı:", ("Resmi", "Samimi", "Turist", "Özet Çıkar"))
    
    target_lang_name = st.selectbox("Hedef Dil:", ("İngilizce", "Türkçe", "Almanca", "İspanyolca", "Fransızca", "Rusça", "Arapça"))
    
    lang_codes = {
        "İngilizce": "en", "Türkçe": "tr", "Almanca": "de", 
        "İspanyolca": "es", "Fransızca": "fr", "Rusça": "ru", "Arapça": "ar"
    }
    target_lang_code = lang_codes[target_lang_name]

    # İndirme Butonu
    chat_text = ""
    for chat in st.session_state.chat_history:
        chat_text += f"🗣️ Kaynak: {chat['user']}\n🤖 Çeviri: {chat['ai']}\n-------------------\n"
    
    st.download_button(
        label="📥 Kayıtları İndir (TXT)",
        data=chat_text,
        file_name=f"konusma_gecmisi_{datetime.datetime.now().strftime('%H%M')}.txt",
        mime="text/plain"
    )

    if st.button("🗑️ Temizle", type="primary"):
        st.session_state.chat_history = []
        st.rerun()

# --- MİKROFON ALANI ---
st.divider()

if work_mode == "⚡ Telsiz Modu (Sohbet)":
    st.info("💡 **Sohbet Modu:** Kısa konuşmalar. Duraksarsan otomatik durabilir.")
    mic_text_start = "Konuş"
    icon_color = "#e8b62c" # Sarı
    pause_limit = 2.0 # 2 saniye susarsan kapat
else:
    st.warning("🔴 **Konferans Modu:** SÜREKLİ DİNLEME AKTİF. Sen butona tekrar basana kadar (veya 5 dk sessizlik olana kadar) kapanmaz.")
    mic_text_start = "Sürekli Dinlemeyi Başlat"
    icon_color = "#FF0000" # Kırmızı
    pause_limit = 300.0 # 300 saniye (5 dakika) susarsan kapat (Neredeyse sonsuz)

# Ortalanmış Mikrofon
col1, col2, col3 = st.columns([1, 10, 1])
with col2:
    audio_bytes = audio_recorder(
        text="",
        recording_color=icon_color,
        neutral_color="#333333",
        icon_name="microphone",
        icon_size="5x",
        pause_threshold=pause_limit, # <-- İŞTE SİHİRLİ DOKUNUŞ BURASI
        sample_rate=44100
    )
    
    if audio_bytes:
        st.caption("✅ Kayıt alındı, işleniyor...")
    else:
        st.caption(f"👆 {mic_text_start} için bas")

# --- İŞLEM ---
if audio_bytes:
    with st.spinner('Uzun ses kaydı işleniyor, lütfen bekleyin...'):
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
            if work_mode == "🔴 Konferans Modu (Sürekli)":
                system_prompt = f"""
                Sen profesyonel bir simultane tercümansın. 
                Kullanıcı uzun bir konuşma yaptı veya ortam sesi kaydedildi.
                Mod: {user_style}. Hedef Dil: {target_lang_name}.
                Görevin:
                1. Tüm konuşmayı anlam bütünlüğünü bozmadan akıcı bir şekilde çevir.
                2. Metin çok uzunsa ana fikri kaybetmeden özetleyerek çevir.
                """
            else:
                system_prompt = f"Çevirmen. Mod: {user_style}. Hedef: {target_lang_name}. Sadece çeviriyi ver."

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
        st.markdown(f"""
        <div style="border-left: 5px solid #FF4B4B; padding-left: 10px; margin-bottom: 5px;">
            <small style="color: gray;">Kaynak:</small><br>
            <span style="font-size: 18px;">{chat['user']}</span>
        </div>
        <div style="border-left: 5px solid #28a745; padding-left: 10px; margin-bottom: 10px; background-color: #f9f9f9;">
            <small style="color: gray;">Çeviri ({target_lang_name}):</small><br>
            <span style="font-size: 20px; font-weight: bold;">{chat['ai']}</span>
        </div>
        """, unsafe_allow_html=True)
        st.audio(chat['audio'], format="audio/mp3")
        st.divider()
