import streamlit as st
from groq import Groq
from audio_recorder_streamlit import audio_recorder
from gtts import gTTS
import io
import datetime

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="AI Tercüman Ultimate",
    page_icon="🌍",
    layout="centered"
)

# --- CSS TASARIM ---
st.markdown("""
    <style>
    .main-title {
        text-align: center;
        background: -webkit-linear-gradient(45deg, #FF416C, #FF4B2B);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3em; font-weight: bold;
    }
    .chat-box { padding: 15px; border-radius: 15px; margin-bottom: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
    .tr-msg { background-color: #e3f2fd; border-left: 5px solid #2196F3; } /* Mavi (Biz) */
    .target-msg { background-color: #fbe9e7; border-right: 5px solid #FF5722; text-align: right; } /* Turuncu (Onlar) */
    .stButton>button { border-radius: 20px; font-weight: bold; width: 100%; }
    </style>
""", unsafe_allow_html=True)

# --- BAŞLIK ---
st.markdown('<div class="main-title">🌍 AI Tercüman Ultimate</div>', unsafe_allow_html=True)

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
    st.header("🎛️ Ayarlar")
    
    # 1. Dil Seçimi (Çift Yönlü)
    st.subheader("🗣️ Diller")
    col_l1, col_l2 = st.columns(2)
    with col_l1:
        native_lang = st.selectbox("Benim Dilim:", ("Türkçe", "İngilizce"), index=0)
    with col_l2:
        target_lang_name = st.selectbox("Karşı Taraf:", ("İngilizce", "Türkçe", "Almanca", "İspanyolca", "Fransızca", "Rusça", "Arapça", "Japonca", "Çince"), index=0)
    
    # Dil Kodları
    lang_codes = {
        "İngilizce": "en", "Türkçe": "tr", "Almanca": "de", "İspanyolca": "es", 
        "Fransızca": "fr", "Rusça": "ru", "Arapça": "ar", "Japonca": "ja", "Çince": "zh"
    }
    native_code = lang_codes[native_lang]
    target_code = lang_codes[target_lang_name]

    st.divider()

    # 2. Karakter
    st.subheader("🎭 Kişilik")
    persona_choice = st.selectbox("Tarz:", ("Profesyonel", "Samimi", "Çocuksu", "Kaba/Mafya", "Şövalye", "Özel"))
    
    custom_role = ""
    if persona_choice == "Özel":
        custom_role = st.text_area("Rol yaz:", placeholder="Örn: Sen Yodasın.")

    # 3. Hız
    tts_slow = st.checkbox("🐢 Yavaş Okuma", value=False)
    
    # 4. Asistan
    st.divider()
    if st.button("📝 Özet Çıkar", type="secondary"):
        if st.session_state.chat_history:
            with st.spinner("Özetleniyor..."):
                full_text = "\n".join([f"- {c['user']} -> {c['ai']}" for c in st.session_state.chat_history])
                res = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": f"Özetle, Kararlar, Görevler:\n{full_text}"}]
                )
                st.session_state.summary = res.choices[0].message.content

    if st.button("🗑️ Temizle", type="primary"):
        st.session_state.chat_history = []
        if "summary" in st.session_state: del st.session_state.summary
        st.rerun()

# --- ÖZET ---
if "summary" in st.session_state:
    st.info(st.session_state.summary)
    if st.button("Kapat"): del st.session_state.summary; st.rerun()

# --- ANA EKRAN (SEKMELER) ---
tab1, tab2 = st.tabs(["⚡ Karşılıklı Sohbet", "📂 Dosya Analizi"])

# --- MOTOR ---
def process_audio(audio_data, mode="native"):
    # mode: 'native' (Ben konuşuyorum -> Hedefe çevir) 
    # mode: 'target' (O konuşuyor -> Bana çevir)
    
    lang_label = native_lang if mode == "native" else target_lang_name
    target_label = target_lang_name if mode == "native" else native_lang
    output_lang_code = target_code if mode == "native" else native_code
    
    with st.spinner(f'{lang_label} dinleniyor ve çevriliyor...'):
        try:
            # 1. Duy
            transcription = client.audio.transcriptions.create(
                file=("audio.wav", audio_data), 
                model="whisper-large-v3",
                response_format="text"
            )
            
            # 2. Prompt Ayarla
            role_desc = "Profesyonel tercüman."
            if persona_choice == "Samimi": role_desc = "Kanka gibi konuş."
            elif persona_choice == "Kaba/Mafya": role_desc = "Mafya babası gibi konuş."
            elif persona_choice == "Şövalye": role_desc = "Orta çağ şövalyesi gibi konuş."
            elif persona_choice == "Özel": role_desc = custom_role

            system_prompt = f"""
            Sen {role_desc}.
            Kaynak Dil: {lang_label}. Hedef Dil: {target_label}.
            
            GÖREV:
            1. Metnin duygusunu bul (Tek kelime).
            2. Metni hedef dile, karakterine uygun çevir.
            
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
                mood, translation = full_res.split("|||", 1)
            else:
                mood, translation = "Nötr", full_res

            # 3. Seslendir (Hedef dilde konuş)
            tts = gTTS(text=translation, lang=output_lang_code, slow=tts_slow)
            audio_fp = io.BytesIO()
            tts.write_to_fp(audio_fp)
            
            # 4. Kaydet
            st.session_state.chat_history.append({
                "direction": mode, # Yönü kaydet (Ben mi O mu?)
                "user": transcription,
                "ai": translation,
                "mood": mood.strip(),
                "audio": audio_fp.getvalue()
            })
            # st.rerun() # Otomatik yenileme kapalı (Döngü hatası olmasın)
            
        except Exception as e:
            st.error(f"Hata: {e}")

# --- SEKME 1: ÇİFT MİKROFON ---
with tab1:
    st.write("Aşağıdaki butonları kullanarak karşılıklı konuşun:")
    
    col_me, col_you = st.columns(2)
    
    with col_me:
        st.info(f"🎤 **BEN ({native_lang})**")
        audio_me = audio_recorder(text="", recording_color="#2196F3", neutral_color="#d6eaf8", icon_name="microphone", icon_size="4x", key="mic_me")
        if audio_me and len(audio_me) > 500:
            process_audio(io.BytesIO(audio_me), mode="native")
            
    with col_you:
        st.warning(f"🎤 **MİSAFİR ({target_lang_name})**")
        audio_you = audio_recorder(text="", recording_color="#FF5722", neutral_color="#fadbd8", icon_name="microphone", icon_size="4x", key="mic_you")
        if audio_you and len(audio_you) > 500:
            process_audio(io.BytesIO(audio_you), mode="target")

# --- SEKME 2: DOSYA ---
with tab2:
    f = st.file_uploader("Ses Dosyası", type=['wav', 'mp3'])
    if f and st.button("Çevir"):
        process_audio(f, mode="native")

# --- SOHBET AKIŞI ---
st.divider()
for chat in reversed(st.session_state.chat_history):
    # Mesajın yönüne göre tasarımı değiştir
    if chat['direction'] == 'native':
        # Ben konuştuysam (Sola yaslı, Mavi)
        align_class = "tr-msg"
        speaker_label = f"🗣️ SEN ({native_lang})"
        trans_label = f"🤖 ÇEVİRİ ({target_lang_name})"
    else:
        # O konuştuysa (Sağa yaslı, Turuncu)
        align_class = "target-msg"
        speaker_label = f"🗣️ MİSAFİR ({target_lang_name})"
        trans_label = f"🤖 ÇEVİRİ ({native_lang})"
    
    st.markdown(f"""
    <div class="chat-box {align_class}">
        <small style="color:#555">{speaker_label}:</small><br>
        <i>"{chat['user']}"</i><br><br>
        <small style="color:#555">{trans_label} [Mod: {chat['mood']}]:</small><br>
        <b style="font-size:1.2em">{chat['ai']}</b>
    </div>
    """, unsafe_allow_html=True)
    
    col_audio, _ = st.columns([1, 3])
    with col_audio:
        st.audio(chat['audio'], format="audio/mp3")
