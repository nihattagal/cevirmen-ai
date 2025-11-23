import streamlit as st
from groq import Groq
from audio_recorder_streamlit import audio_recorder
from gtts import gTTS
import io
import datetime

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="AI Tercüman & Asistan",
    page_icon="🧠",
    layout="centered"
)

# --- BAŞLIK ---
st.markdown("<h1 style='text-align: center; color: #4B0082;'>🧠 AI Tercüman & Asistan</h1>", unsafe_allow_html=True)

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
    
    # 1. Mod Seçimi
    st.subheader("1. Çalışma Modu")
    work_mode = st.radio(
        "Seçiniz:",
        ("⚡ Sohbet (Telsiz)", "🔴 Konferans (Sürekli)"),
        label_visibility="collapsed"
    )
    
    st.divider()
    
    # 2. Dil Seçimi
    st.subheader("2. Hedef Dil")
    target_lang_name = st.selectbox("Seçiniz:", ("Türkçe", "İngilizce", "Almanca", "İspanyolca", "Fransızca", "Rusça", "Arapça", "Japonca", "Çince"), label_visibility="collapsed")
    
    lang_codes = {
        "İngilizce": "en", "Türkçe": "tr", "Almanca": "de", 
        "İspanyolca": "es", "Fransızca": "fr", "Rusça": "ru", 
        "Arapça": "ar", "Japonca": "ja", "Çince": "zh"
    }
    target_lang_code = lang_codes[target_lang_name]

    st.divider()

    # 3. AI SEKRETER (YENİ ÖZELLİK)
    st.subheader("3. 📝 AI Sekreter")
    if st.button("Toplantı Özeti Çıkar", type="secondary", use_container_width=True):
        if len(st.session_state.chat_history) > 0:
            with st.spinner("Tüm konuşmalar analiz ediliyor..."):
                # Tüm geçmişi tek metin yap
                full_text = ""
                for chat in st.session_state.chat_history:
                    full_text += f"- {chat['user']} (Analiz: {chat.get('mood', 'Nötr')})\n"
                
                # Özetleme İstemi
                summary_prompt = f"""
                Sen profesyonel bir toplantı asistanısın. Aşağıdaki konuşma metnini analiz et.
                Hedef Dil: {target_lang_name}.
                
                ÇIKTI FORMATI:
                1. 📋 **Genel Özet** (2-3 cümle)
                2. ✅ **Alınan Kararlar** (Madde madde)
                3. 📌 **Aksiyon/Görev Listesi** (Kim ne yapacak?)
                4. 🌡️ **Genel Ortam Havası** (Konuşmaların duygusuna göre)

                Konuşma Metni:
                {full_text}
                """
                
                summary_res = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": summary_prompt}]
                )
                
                # Sonucu ekrana şık bir kutuda basacağız (Aşağıda session_state'e atıyoruz)
                st.session_state.summary_result = summary_res.choices[0].message.content
        else:
            st.warning("Henüz konuşma kaydı yok.")

    # İndirme ve Temizleme
    st.divider()
    chat_text = ""
    for chat in st.session_state.chat_history:
        mood_info = chat.get('mood', 'Nötr')
        chat_text += f"Kaynak: {chat['user']}\nAnaliz: {mood_info}\nÇeviri: {chat['ai']}\n-------------------\n"
    
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.download_button(
            label="📥 İndir",
            data=chat_text,
            file_name=f"kayit_{datetime.datetime.now().strftime('%H%M')}.txt",
            mime="text/plain",
            use_container_width=True
        )
    with col_d2:
        if st.button("🗑️ Sil", type="primary", use_container_width=True):
            st.session_state.chat_history = []
            if "summary_result" in st.session_state:
                del st.session_state.summary_result
            st.rerun()

# --- ÖZET ALANI (Varsa Göster) ---
if "summary_result" in st.session_state:
    st.success("📝 **Toplantı Raporu Hazır!**")
    st.markdown(f"<div style='background-color:#e8f4f8; padding:15px; border-radius:10px; color:black;'>{st.session_state.summary_result}</div>", unsafe_allow_html=True)
    if st.button("Raporu Kapat"):
        del st.session_state.summary_result
        st.rerun()
    st.divider()

# --- MİKROFON ALANI ---
if work_mode == "⚡ Sohbet (Telsiz)":
    st.info("💡 **Sohbet:** Bas-Konuş. Kısa diyaloglar.")
    icon_color = "#e8b62c" 
    pause_limit = 2.0 
else:
    st.warning("🔴 **Konferans:** SÜREKLİ DİNLEME. 'Bitir' diyene kadar kapanmaz.")
    icon_color = "#FF0000" 
    pause_limit = 300.0 

col1, col2, col3 = st.columns([1, 10, 1])
with col2:
    audio_bytes = audio_recorder(
        text="",
        recording_color=icon_color,
        neutral_color="#333333",
        icon_name="microphone",
        icon_size="5x",
        pause_threshold=pause_limit,
        sample_rate=44100
    )

# --- İŞLEM ---
if audio_bytes:
    with st.spinner('⏳ Ses işleniyor...'):
        try:
            # A. Sesi Hazırla
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = "audio.wav"
            
            # B. Duy
            transcription = client.audio.transcriptions.create(
                file=("audio.wav", audio_file), 
                model="whisper-large-v3",
                response_format="text"
            )
            
            # C. Çevir + Analiz
            system_prompt = f"""
            Sen uzman bir tercüman ve psikologsun. Hedef Dil: {target_lang_name}.
            GÖREVİN:
            1. Duygu durumunu tek kelimeyle analiz et (Örn: Kızgın, Mutlu, Ciddi, Nötr).
            2. Metni çevir.
            
            KURALLAR: "Test", "Ses" gibi kelimelerde Duygu=Nötr.
            FORMAT: DUYGU ||| METİN
            """

            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": transcription}
                ],
            )
            full_response = completion.choices[0].message.content

            # Parçala
            if "|||" in full_response:
                parts = full_response.split("|||")
                mood = parts[0].strip()
                translation = parts[1].strip()
            else:
                mood = "Nötr"
                translation = full_response

            # D. Seslendir
            tts = gTTS(text=translation, lang=target_lang_code, slow=False)
            audio_fp = io.BytesIO()
            tts.write_to_fp(audio_fp)
            audio_data = audio_fp.getvalue()
            
            # E. Kaydet
            st.session_state.chat_history.append({
                "user": transcription,
                "ai": translation,
                "mood": mood,
                "audio": audio_data
            })
            
        except Exception as e:
            st.error(f"Hata: {str(e)}")

# --- SOHBET GÖRÜNÜMÜ ---
st.divider()

mood_icons = {
    "Kızgın": "😡", "Öfkeli": "😡", "Mutlu": "😊", "Sevinçli": "😁", 
    "Üzgün": "😢", "Endişeli": "😟", "Ciddi": "😐", "Nötr": "😶"
}

for chat in reversed(st.session_state.chat_history):
    with st.container():
        current_mood = chat.get('mood', 'Nötr')
        icon = "😶"
        for key, val in mood_icons.items():
            if key in current_mood: 
                icon = val
                break
        
        st.markdown(f"**🗣️ Kaynak:** {chat['user']}")
        st.info(f"{icon} **Duygu:** {current_mood}")
        st.code(chat['ai'], language=None)
        st.audio(chat['audio'], format="audio/mp3")
        st.divider()
