import streamlit as st
from groq import Groq
from audio_recorder_streamlit import audio_recorder
from gtts import gTTS
import io
import uuid # DÜNYADA TEK (Benzersiz) kod üretmek için
import urllib.parse

st.set_page_config(page_title="AI Çevirmen", layout="centered")

st.title("🎨 Görsel & Sesli AI Çevirmen")

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
    
    show_images = st.toggle("🖼️ Görsel Oluşturmayı Aç", value=True)

    lang_codes = {"İngilizce": "en", "Türkçe": "tr", "Almanca": "de", "İspanyolca": "es", "Fransızca": "fr"}
    target_lang_code = lang_codes[target_lang_name]

    if st.button("🗑️ Temizle"):
        st.session_state.chat_history = []
        st.cache_data.clear()
        st.rerun()

# --- MİKROFON ---
st.write("Mikrofona basıp konuşun (Örn: 'Kadıköy çarşıda geziyorum'):")
audio_bytes = audio_recorder(
    text="",
    recording_color="#e8b62c",
    neutral_color="#6aa36f",
    icon_name="microphone",
    icon_size="3x",
)

# --- İŞLEM ---
if audio_bytes:
    with st.spinner('Yapay Zeka düşünüyor, çiziyor ve seslendiriyor...'):
        try:
            # 1. Ses Dosyası
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = "audio.wav"
            
            # 2. Whisper (Duyma)
            transcription = client.audio.transcriptions.create(
                file=("audio.wav", audio_file), 
                model="whisper-large-v3",
                response_format="text"
            )
            
            # 3. Llama (Çevirme + Görsel Tespiti)
            system_prompt = f"""
            Sen bir çevirmensin. 
            Mod: {user_mode}. 
            Hedef Dil: {target_lang_name}.
            
            GÖREVİN:
            1. Metni hedef dile çevir.
            2. Metin içinde SOMUT bir nesne veya ortam varsa onu detaylı İngilizce kelimelerle tanımla.
            
            ÖNEMLİ: 
            - 'Kadıköy' veya 'Çarşı' geçerse -> 'crowded city street market istanbul shopping' gibi betimle.
            - 'Mavi gömlek' geçerse -> 'blue shirt fabric fashion' gibi betimle.
            
            CEVAP FORMATI (Buna uy):
            Çevrilmiş Metin ||| Görsel_Tanımı_Ingilizce
            """
            
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": transcription}
                ],
            )
            
            full_response = completion.choices[0].message.content
            
            # Cevabı parçala
            if "|||" in full_response:
                parts = full_response.split("|||")
                translation = parts[0].strip()
                image_keyword = parts[1].strip()
                
                # --- URL OLUŞTURMA (BENZERSİZ ID İLE) ---
                safe_keyword = urllib.parse.quote(image_keyword)
                
                # Rastgelelik yerine UUID kullanıyoruz (Kesin çözüm)
                unique_id = str(uuid.uuid4())
                
                image_url = f"https://image.pollinations.ai/prompt/{safe_keyword}?nologo=true&seed={unique_id}"
            else:
                translation = full_response
                image_url = None
                image_keyword = None

            # 4. Seslendirme (TTS)
            tts = gTTS(text=translation, lang=target_lang_code, slow=False)
            audio_io = io.BytesIO()
            tts.write_to_fp(audio_io)
            audio_io.seek(0)
            
            # 5. Hafızaya Kaydet
            st.session_state.chat_history.append({
                "user": transcription,
                "ai": translation,
                "audio": audio_io,
                "image": image_url,
                "keyword": image_keyword,
                "id": str(uuid.uuid4()) # Her mesajın kendi kimliği olsun
            })
            
        except Exception as e:
            st.error(f"Hata: {str(e)}")

# --- EKRAN GÖRÜNÜMÜ ---
# enumerate kullanarak karışıklığı önlüyoruz
for i, chat in enumerate(reversed(st.session_state.chat_history)):
    with st.container(border=True):
        col1, col2 = st.columns([2, 1]) 
        
        with col1:
            st.info(f"🎤 **Sen:** {chat['user']}")
            st.success(f"🤖 **Çeviri:** {chat['ai']}")
            st.audio(chat['audio'], format="audio/mp3", key=f"audio_{i}") # Key ekledik
        
        with col2:
            if chat['image'] and show_images:
                # Key ekledik ki resimler karışmasın
                st.image(chat['image'], caption=f"AI: {chat['keyword']}", use_container_width=True)
