import streamlit as st
from groq import Groq
from audio_recorder_streamlit import audio_recorder
from gtts import gTTS
import io
import datetime

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="AI Tercüman Elite",
    page_icon="💎",
    layout="centered"
)

# --- 🎨 ÖZEL TASARIM (CSS) ---
# Burası uygulamanın "Makyaj" kısmıdır.
st.markdown("""
    <style>
    /* Ana Başlık */
    .main-title {
        text-align: center;
        background: -webkit-linear-gradient(45deg, #6a11cb, #2575fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3em;
        font-weight: bold;
        padding-bottom: 20px;
    }
    
    /* Mesaj Kutuları */
    .chat-box {
        padding: 15px;
        border-radius: 15px;
        margin-bottom: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .user-msg {
        background-color: #f0f2f6;
        border-left: 5px solid #2575fc;
    }
    .ai-msg {
        background-color: #e8f4f8;
        border-left: 5px solid #00c853;
    }
    
    /* Butonlar */
    .stButton>button {
        border-radius: 20px;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# --- BAŞLIK ---
st.markdown('<div class="main-title">💎 AI Tercüman Elite</div>', unsafe_allow_html=True)

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
    st.header("🎛️ Kontrol Merkezi")
    
    # 1. Mod
    work_mode = st.radio("Çalışma Modu:", ("⚡ Sohbet", "🔴 Konferans"), horizontal=True)
    
    # 2. Dil
    target_lang_name = st.selectbox("Hedef Dil:", ("Türkçe", "İngilizce", "Almanca", "İspanyolca", "Fransızca", "Rusça", "Arapça", "Japonca", "Çince"))
    
    lang_codes = {
        "İngilizce": "en", "Türkçe": "tr", "Almanca": "de", 
        "İspanyolca": "es", "Fransızca": "fr", "Rusça": "ru", 
        "Arapça": "ar", "Japonca": "ja", "Çince": "zh"
    }
    target_lang_code = lang_codes[target_lang_name]
    
    st.divider()

    # 3. YENİ: ÖZEL KARAKTER (PERSONA)
    st.subheader("🎭 AI Kişiliği")
    persona_choice = st.selectbox(
        "Tercüman nasıl davransın?",
        ("Standart Profesyonel", "Samimi Arkadaş", "Basit Anlatım (Çocuklar için)", "👔 Resmi/Hukuki", "✨ ÖZEL TARZ YARAT")
    )
    
    custom_system_instruction = ""
    if persona_choice == "✨ ÖZEL TARZ YARAT":
        custom_system_instruction = st.text_area("Yapay zekaya emrini yaz:", placeholder="Örn: Sen kaba bir korsansın, her cümlene 'Ahoy!' diye başla.")
    
    st.divider()
    
    # 4. Hız ve Asistan
    tts_slow = st.checkbox("🐢 Yavaş Okuma", value=False)
    
    if st.button("📝 Toplantı Özeti", type="secondary", use_container_width=True):
        if len(st.session_state.chat_history) > 0:
            with st.spinner("Analiz ediliyor..."):
                full_text = ""
                for chat in st.session_state.chat_history:
                    full_text += f"- {chat['user']} (Mod: {chat.get('mood', 'Nötr')})\n"
                
                summary_prompt = f"""
                Sen profesyonel bir asistansın. Metni analiz et. Hedef Dil: {target_lang_name}.
                ÇIKTI: 1.Özet, 2.Kararlar, 3.Görevler.
                Metin: {full_text}
                """
                summary_res = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": summary_prompt}]
                )
                st.session_state.summary_result = summary_res.choices[0].message.content
        else:
            st.warning("Kayıt yok.")

    if st.button("🗑️ Sıfırla", type="primary", use_container_width=True):
        st.session_state.chat_history = []
        if "summary_result" in st.session_state: del st.session_state.summary_result
        st.rerun()

# --- ÖZET GÖSTERİMİ ---
if "summary_result" in st.session_state:
    st.success("📝 Rapor Hazır")
    st.info(st.session_state.summary_result)
    if st.button("Kapat"):
        del st.session_state.summary_result
        st.rerun()

# --- ANA EKRAN ---
tab1, tab2 = st.tabs(["🎙️ Canlı Mikrofon", "📂 Dosya Yükle"])

# --- MOTOR ---
def process_audio(audio_file_input, source_name="Mikrofon"):
    with st.spinner(f'{source_name} işleniyor...'):
        try:
            # 1. Duy
            transcription = client.audio.transcriptions.create(
                file=("audio.wav", audio_file_input), 
                model="whisper-large-v3",
                response_format="text"
            )
            
            # 2. Karakteri Belirle
            if persona_choice == "✨ ÖZEL TARZ YARAT":
                persona_prompt = f"Senin karakterin: {custom_system_instruction}. Buna sadık kalarak çeviri yap."
            elif persona_choice == "Samimi Arkadaş":
                persona_prompt = "Sen çok samimi, 'kanka' gibi konuşan birisin. Argo kullanabilirsin."
            elif persona_choice == "Basit Anlatım (Çocuklar için)":
                persona_prompt = "Sen bir ilkokul öğretmenisin. Her şeyi 5 yaşındaki çocuğun anlayacağı kadar basitleştirerek çevir."
            elif persona_choice == "👔 Resmi/Hukuki":
                persona_prompt = "Sen bir hukuk ve diplomasi uzmanısın. Çok resmi, üst düzey bir dil kullan."
            else:
                persona_prompt = "Sen profesyonel bir tercümansın. Sadece net çeviri yap."

            # 3. Çevir + Analiz
            system_prompt = f"""
            {persona_prompt}
            Hedef Dil: {target_lang_name}.
            GÖREV:
            1. Duyguyu tek kelimeyle bul (Kızgın, Mutlu, Ciddi, Nötr).
            2. Çeviriyi yap.
            FORMAT: DUYGU ||| METİN
            """
            
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": transcription}
                ],
            )
            full_res = completion.choices[0].message.content

            if "|||" in full_res:
                parts = full_res.split("|||")
                mood = parts[0].strip()
                translation = parts[1].strip()
            else:
                mood = "Nötr"
                translation = full_res

            # 4. Seslendir
            tts = gTTS(text=translation, lang=target_lang_code, slow=tts_slow)
            audio_fp = io.BytesIO()
            tts.write_to_fp(audio_fp)
            audio_data = audio_fp.getvalue()
            
            # 5. Kaydet
            st.session_state.chat_history.append({
                "user": transcription,
                "ai": translation,
                "mood": mood,
                "audio": audio_data
            })
            
        except Exception as e:
            st.error(f"Hata: {str(e)}")

# --- SEKME 1: MİKROFON ---
with tab1:
    if work_mode == "⚡ Sohbet":
        icon_color = "#e8b62c" 
        pause_limit = 2.0 
        st.info("⚡ Bas-Konuş Modu")
    else:
        icon_color = "#FF0000" 
        pause_limit = 300.0 
        st.warning("🔴 Konferans Modu (Sürekli)")

    col1, col2, col3 = st.columns([1, 10, 1])
    with col2:
        mic_audio = audio_recorder(text="", recording_color=icon_color, neutral_color="#333333", icon_name="microphone", icon_size="5x", pause_threshold=pause_limit, sample_rate=44100)
    
    if mic_audio:
        if len(mic_audio) > 500: 
            audio_file = io.BytesIO(mic_audio)
            audio_file.name = "audio.wav"
            process_audio(audio_file, "Mikrofon")
        else:
            st.warning("⚠️ Ses çok kısa.")

# --- SEKME 2: DOSYA ---
with tab2:
    st.write("📁 **Ses dosyası yükleyin**")
    uploaded_file = st.file_uploader("Dosya Seç", type=['wav', 'mp3', 'm4a', 'ogg'])
    if uploaded_file and st.button("🚀 Çevir"):
        process_audio(uploaded_file, "Dosya")

# --- SOHBET GEÇMİŞİ (YENİ TASARIM) ---
st.divider()
mood_icons = {"Kızgın": "😡", "Mutlu": "😊", "Üzgün": "😢", "Ciddi": "😐", "Nötr": "😶"}

for chat in reversed(st.session_state.chat_history):
    current_mood = chat.get('mood', 'Nötr')
    icon = "😶"
    for key, val in mood_icons.items():
        if key in current_mood: icon = val; break
    
    # Özel Tasarımlı Kutular
    st.markdown(f"""
    <div class="chat-box user-msg">
        <small style="color:#555">🗣️ Kaynak:</small><br>
        {chat['user']}
    </div>
    <div class="chat-box ai-msg">
        <small style="color:#555">🤖 Çeviri ({icon} {current_mood}):</small><br>
        <b style="font-size:1.1em">{chat['ai']}</b>
    </div>
    """, unsafe_allow_html=True)
    
    st.audio(chat['audio'], format="audio/mp3")
