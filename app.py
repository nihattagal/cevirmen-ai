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

# --- TASARIM (CSS) ---
st.markdown("""
    <style>
    .main-title {
        text-align: center;
        background: -webkit-linear-gradient(45deg, #6a11cb, #2575fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3em;
        font-weight: bold;
        padding-bottom: 20px;
    }
    .chat-box {
        padding: 15px; border-radius: 15px; margin-bottom: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .user-msg { background-color: #f0f2f6; border-left: 5px solid #2575fc; }
    .ai-msg { background-color: #e8f4f8; border-left: 5px solid #00c853; }
    .stButton>button { border-radius: 20px; font-weight: bold; }
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
    
    # Mod ve Dil
    work_mode = st.radio("Çalışma Modu:", ("⚡ Sohbet", "🔴 Konferans"), horizontal=True)
    target_lang_name = st.selectbox("Hedef Dil:", ("Türkçe", "İngilizce", "Almanca", "İspanyolca", "Fransızca", "Rusça", "Arapça", "Japonca", "Çince"))
    
    lang_codes = {
        "İngilizce": "en", "Türkçe": "tr", "Almanca": "de", 
        "İspanyolca": "es", "Fransızca": "fr", "Rusça": "ru", 
        "Arapça": "ar", "Japonca": "ja", "Çince": "zh"
    }
    target_lang_code = lang_codes[target_lang_name]
    
    st.divider()

    # --- GELİŞMİŞ KARAKTER SEÇİMİ ---
    st.subheader("🎭 AI Kişiliği")
    persona_choice = st.selectbox(
        "Tercüman Rolü:",
        ("Standart Profesyonel", "Samimi Kanka", "Masal Anlatıcısı (Çocuklar için)", "Mafya Babası", "Orta Çağ Şövalyesi", "✨ ÖZEL TARZ YARAT")
    )
    
    custom_system_instruction = ""
    if persona_choice == "✨ ÖZEL TARZ YARAT":
        custom_system_instruction = st.text_area("Rol tanımı yaz:", placeholder="Örn: Sen Yoda'sın. Cümleleri devrik kur.")
    
    st.divider()
    
    # Ekstra Araçlar
    tts_slow = st.checkbox("🐢 Yavaş Okuma", value=False)
    
    if st.button("📝 Toplantı Özeti", type="secondary", use_container_width=True):
        if len(st.session_state.chat_history) > 0:
            with st.spinner("Analiz ediliyor..."):
                full_text = ""
                for chat in st.session_state.chat_history:
                    full_text += f"- {chat['user']} (Mod: {chat.get('mood', 'Nötr')})\n"
                
                summary_prompt = f"Sen bir asistansın. Metni analiz et. Hedef: {target_lang_name}. Çıktı: Özet, Kararlar, Görevler.\nMetin: {full_text}"
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

# --- ÖZET ---
if "summary_result" in st.session_state:
    st.success("📝 Rapor Hazır")
    st.info(st.session_state.summary_result)
    if st.button("Kapat"): del st.session_state.summary_result; st.rerun()

# --- ANA EKRAN ---
tab1, tab2 = st.tabs(["🎙️ Canlı Mikrofon", "📂 Dosya Yükle"])

# --- İŞLEME MOTORU ---
def process_audio(audio_file_input, source_name="Mikrofon"):
    with st.spinner(f'{source_name} işleniyor...'):
        try:
            # 1. Duy
            transcription = client.audio.transcriptions.create(
                file=("audio.wav", audio_file_input), 
                model="whisper-large-v3",
                response_format="text"
            )
            
            # 2. Karakter Ayarları (Prompt Mühendisliği)
            if persona_choice == "✨ ÖZEL TARZ YARAT":
                persona_prompt = f"ROLÜN: {custom_system_instruction}. Çeviriyi tam olarak bu role bürünerek yap."
            elif persona_choice == "Samimi Kanka":
                persona_prompt = "ROLÜN: Çok samimi, sokak ağzıyla konuşan, 'kanka', 'bro' gibi kelimeler kullanan birisin."
            elif persona_choice == "Masal Anlatıcısı (Çocuklar için)":
                persona_prompt = "ROLÜN: Bir masalcı teyzesin. Çok tatlı, basit ve sevimli bir dille, çocuklara anlatır gibi çevir."
            elif persona_choice == "Mafya Babası":
                persona_prompt = "ROLÜN: Ağır bir mafya babasısın (Godfather). Racon keserek, ağır ve tehditkar konuş."
            elif persona_choice == "Orta Çağ Şövalyesi":
                persona_prompt = "ROLÜN: Orta çağdan gelen asil bir şövalyesin. Eski Türkçe (veya İngilizce) kullan. 'Azizim', 'Zat-ı aliniz', 'Hürmetler' gibi ifadelerle çok süslü konuş."
            else:
                persona_prompt = "ROLÜN: Profesyonel tercüman. Net ve doğru çevir."

            # 3. Çeviri + Analiz (GÜÇLENDİRİLMİŞ PROMPT)
            system_prompt = f"""
            Sen hem bir tercüman hem de ödüllü bir oyuncusun.
            Hedef Dil: {target_lang_name}.
            
            {persona_prompt}
            
            GÖREVİN:
            1. Metindeki duyguyu analiz et.
            2. Metni hedef dile çevir AMA çeviriyi ROLÜNE UYGUN ŞEKİLDE YENİDEN YAZ.
            
            ÖNEMLİ:
            - Sadece kelime çevirme, karakterin ruhunu kat!
            - Eğer şövalyeysen "Nasılsın?" deme, "Sıhhatiniz yerinde midir ey yolcu?" de.
            - Eğer mafyaysan "Para nerede?" deme, "Mangırları sökül bakalım" de.
            
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
            # st.rerun() # Döngü sorununa karşı kapalı
            
        except Exception as e:
            st.error(f"Hata: {str(e)}")

# --- SEKME 1 ---
with tab1:
    if work_mode == "⚡ Sohbet":
        icon_color = "#e8b62c"; pause_limit = 2.0; st.info("Bas-Konuş")
    else:
        icon_color = "#FF0000"; pause_limit = 300.0; st.warning("Sürekli Dinleme")

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

# --- SEKME 2 ---
with tab2:
    uploaded_file = st.file_uploader("Dosya Yükle", type=['wav', 'mp3', 'm4a', 'ogg'])
    if uploaded_file and st.button("🚀 Çevir"):
        process_audio(uploaded_file, "Dosya")

# --- GEÇMİŞ ---
st.divider()
mood_icons = {"Kızgın": "😡", "Mutlu": "😊", "Üzgün": "😢", "Ciddi": "😐", "Nötr": "😶"}

for chat in reversed(st.session_state.chat_history):
    current_mood = chat.get('mood', 'Nötr')
    icon = "😶"
    for key, val in mood_icons.items():
        if key in current_mood: icon = val; break
    
    st.markdown(f"""
    <div class="chat-box user-msg">
        <small style="color:#555">🗣️ Kaynak:</small><br>{chat['user']}
    </div>
    <div class="chat-box ai-msg">
        <small style="color:#555">🤖 Çeviri ({icon} {current_mood}):</small><br>
        <b style="font-size:1.1em">{chat['ai']}</b>
    </div>
    """, unsafe_allow_html=True)
    st.audio(chat['audio'], format="audio/mp3")
