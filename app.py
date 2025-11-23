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
    
    # --- YENİ: ÇALIŞMA MODU SEÇİMİ ---
    st.subheader("Mikrofon Modu")
    work_mode = st.radio(
        "Nasıl çalışsın?",
        ("⚡ Telsiz Modu (Sohbet)", "🔴 Konferans Modu (Sürekli)"),
        help="Telsiz: Kısa cümleler için.\nKonferans: Sen durdurana kadar saatlerce dinler."
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

# Mod'a göre bilgilendirme yazısı
if work_mode == "⚡ Telsiz Modu (Sohbet)":
    st.info("💡 **Sohbet Modu:** Kısa ve hızlı konuşmalar için idealdir. Durdurunca hemen çevirir.")
    mic_text_start = "Konuş"
    mic_text_stop = "Durdur"
    icon_color = "#e8b62c" # Sarı
else:
    st.warning("🔴 **Konferans Modu:** Ortamı kesintisiz dinler. Sen 'Bitir' diyene kadar kapanmaz. Uzun konuşmaları tek seferde çevirir.")
    mic_text_start = "Sürekli Dinlemeyi Başlat"
    mic_text_stop = "Dinlemeyi Bitir ve Çevir"
    icon_color = "#FF0000" # Kırmızı

# Ortalanmış Mikrofon
col1, col2, col3 = st.columns([1, 10, 1])
with col2:
    audio_bytes = audio_recorder(
        text="",
        recording_color=icon_color,
        neutral_color="#333333",
        icon_name="microphone",
        icon_size="5x", # Dev buton
    )
    # Butonun altına açıklama
    if audio_bytes:
        st.caption("✅ Kayıt alındı, işleniyor...")
    else:
        st.caption(f"👆 {mic_text_start} butonuna basın")

# --- İŞLEM ---
if audio_bytes:
    with st.spinner('Ses analizi yapılıyor... (Uzun konuşmalarda bu işlem 2-3 saniye sürebilir)'):
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
            
            # C. Çevir (Llama - Moda Göre Prompt)
            if work_mode == "🔴 Konferans Modu (Sürekli)":
                # Konferans modunda yapay zekaya "Akıcı ol" diyoruz
                system_prompt = f"""
                Sen profesyonel bir simultane tercümansın. 
                Kullanıcı uzun bir konuşma yaptı veya ortam sesi kaydedildi.
                Mod: {user_style}. Hedef Dil: {target_lang_name}.
                Görevin:
                1. Tüm konuşmayı anlam bütünlüğünü bozmadan akıcı bir şekilde çevir.
                2. Eğer konuşma çok dağınıksa toparla ve özetle.
                """
            else:
                # Telsiz modunda hızlı cevap
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
# En yeni mesaj en üstte
for chat in reversed(st.session_state.chat_history):
    with st.container():
        st.markdown(f"""
        <div style="border-left: 5px solid #FF4B4B; padding-left: 10px; margin-bottom: 5px;">
            <small style="color: gray;">Kaynak Ses:</small><br>
            <span style="font-size: 18px;">{chat['user']}</span>
        </div>
        <div style="border-left: 5px solid #28a745; padding-left: 10px; margin-bottom: 10px; background-color: #f9f9f9;">
            <small style="color: gray;">Çeviri ({target_lang_name}):</small><br>
            <span style="font-size: 20px; font-weight: bold;">{chat['ai']}</span>
        </div>
        """, unsafe_allow_html=True)
        
        st.audio(chat['audio'], format="audio/mp3")
        st.divider()
