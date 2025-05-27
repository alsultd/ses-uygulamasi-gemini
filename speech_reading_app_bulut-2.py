import docx
import re
# import speech_recognition as sr # Bu satırı kaldırın veya yoruma alın
import difflib
import random
import streamlit as st
# from streamlit.components.v1 import html # Eğer kullanmıyorsanız bu da gidebilir
import os
from deep_translator import GoogleTranslator
import pronouncing
# import winsound # Windows'a özgü, bulut ortamında çalışmaz
import time
from gtts import gTTS
import base64 # Ses dosyasını direkt HTML'e gömmek için
# Yeni eklenecek kütüphane importu
#from streamlit_speech_to_text import speech_to_text

# Sabitler
ERROR_THRESHOLD = 0.3
TOTAL_TOPICS = 152 # Konu sayınız. Eğer content.docx farklıysa bu sayıyı güncelleyin.
DOCX_FILE_NAME = "OCR_Ana_Cikti_Guncel.docx" # Dosya adını belirledik

# --- Yardımcı Fonksiyonlar ---

def get_text_from_docx(doc_path, topic_no):
    """Belirtilen dosya yolundan ve konu numarasından metni alır."""
    try:
        doc = docx.Document(doc_path)
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        topics = []
        current_topic = ""
        current_number = None
        for p in paragraphs:
            match = re.match(r'^Konu\s*:\s*(\d+)', p)
            if match:
                if current_topic and current_number is not None:
                    topics.append({"number": current_number, "text": current_topic})
                current_number = int(match.group(1))
                current_topic = ""
            else:
                if current_number is not None:
                    current_topic += p + "\n"
        if current_topic and current_number is not None:
            topics.append({"number": current_number, "text": current_topic})
        for topic in topics:
            if topic["number"] == topic_no:
                topic["text"] = topic["text"].replace("=== KONU SONU ===", "").strip()
                return topic["text"]
        return None
    except Exception as e:
        st.error(f"Dosya okuma hatası: {e}")
        return None

def split_into_paragraphs(text):
    return [p.strip() for p in text.split('\n') if p.strip()]

def preprocess_text(text):
    return re.findall(r"\b\w+\b", text.lower())

def evaluate_speech(original, spoken):
    original_words = preprocess_text(original)
    spoken_words = preprocess_text(spoken)
    diff = difflib.SequenceMatcher(None, original_words, spoken_words)
    similarity = diff.ratio()
    error_rate = 1 - similarity
    extra_words = [word for word in spoken_words if word not in original_words]
    missing_words = [word for word in original_words if word not in spoken_words]
    return error_rate, extra_words, missing_words

def read_paragraph(paragraph):
    clean_text = " ".join(paragraph.splitlines())
    clean_text = (clean_text.replace('"', '')
                  .replace("'", "")
                  .replace('{', '')
                  .replace('}', '')
                  .replace('\n', ' ')
                  .replace('\r', ' ')
                  .replace('\t', ' '))
    try:
        tts = gTTS(text=clean_text, lang='en', slow=False)
        audio_file = "temp_audio.mp3"
        tts.save(audio_file)
        audio_base64 = ""
        with open(audio_file, "rb") as audio_file_obj:
            audio_base64 = base64.b64encode(audio_file_obj.read()).decode('utf-8')
        os.remove(audio_file)
        audio_html = f"""
        <audio id="audio" controls autoplay>
            <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
            Tarayıcınız ses oynatmayı desteklemiyor.
        </audio>
        """
        st.markdown(audio_html, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Paragraf oynatılamadı: {e}")

def play_word(word):
    try:
        tts = gTTS(text=word, lang='en', slow=True)
        audio_file = "temp_word_audio.mp3"
        tts.save(audio_file)
        audio_base64 = ""
        with open(audio_file, "rb") as audio_file_obj:
            audio_base64 = base64.b64encode(audio_file_obj.read()).decode('utf-8')
        os.remove(audio_file)
        audio_html = f"""
        <audio id="word_audio_{word}" controls autoplay>
            <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
            Tarayıcınız ses oynatmayı desteklemiyor.
        </audio>
        """
        st.markdown(audio_html, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Telaffuz oynatılamadı: {e}")

def translate_word(word):
    try:
        return GoogleTranslator(source='en', target='tr').translate(word)
    except Exception:
        return "Çeviri yapılamadı"

def translate_paragraph(paragraph):
    try:
        return GoogleTranslator(source='en', target='tr').translate(paragraph)
    except Exception as e:
        return f"Paragraf çevirisi yapılamadı: {e}"

def report_errors(error_rate, extra_words, missing_words):
    error_rate_percent = round(error_rate * 100)
    st.write(f"**Hata Oranı:** {error_rate_percent}%")

    if extra_words:
        st.write("**Fazladan söylenen kelimeler:**")
        st.write(", ".join(extra_words))
    else:
        st.write("**Harika!** Fazladan kelime yok.")

    if missing_words:
        st.write("**Eksik kelimeler:**")
        missing_data = []
        for word in missing_words:
            phonetics = pronouncing.phones_for_word(word)
            phonetic = phonetics[0] if phonetics else "Telaffuz bulunamadı"
            translation = translate_word(word)
            missing_data.append({"Kelime": word, "Telaffuz": phonetic, "Türkçe": translation})
        st.table(missing_data)

#def listen_and_convert():
#    recognizer = sr.Recognizer()
#    with sr.Microphone() as source:
#        st.info("Lütfen konuşmaya başlayın... (45 saniye)")
#        recognizer.adjust_for_ambient_noise(source, duration=1)
#        recognizer.energy_threshold = 300
#        recognizer.pause_threshold = 1.0
#        try:
#            audio = recognizer.listen(source, timeout=45, phrase_time_limit=40)
#            spoken_text = recognizer.recognize_google(audio, language="en-US")
#            return spoken_text
#        except sr.UnknownValueError:
#            return "Konuşma tanınamadı. Daha net konuşmayı deneyin."
#        except sr.RequestError as e:
#            return f"API hatası: {e}. İnternet bağlantınızı veya Google Speech API limitlerini kontrol edin."
#        except Exception as e:
#            return f"Ses kaydı sırasında beklenmeyen bir hata oluştu: {e}"

# --- Ana Streamlit Uygulaması ---
def listen_and_convert(audio_file):
    """Yüklenen ses dosyasını metne çevirir."""
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(audio_file) as source:
            audio = recognizer.record(source)
            spoken_text = recognizer.recognize_google(audio, language="en-US")
            return spoken_text
    except sr.UnknownValueError:
        return "Konuşma tanınamadı. Daha net bir ses dosyası yüklemeyi deneyin."
    except sr.RequestError as e:
        return f"API hatası: {e}. İnternet bağlantınızı veya Google Speech API limitlerini kontrol edin."
    except Exception as e:
        return f"Ses dosyası işlenirken bir hata oluştu: {e}"

def main():
    st.title("Sesle Okuma Çalışması")
    st.write("DEBUG: Uygulama Başlatıldı") # Bu debug satırını isterseniz kaldırabilirsiniz.
    st.write(f"**Toplam Konu Sayısı:** {TOTAL_TOPICS}")

    # Session state değişkenlerini başlatıyoruz
    if "paragraphs" not in st.session_state:
        st.session_state["paragraphs"] = []
        st.session_state["current_index"] = 0
        st.session_state["selected_word"] = None
        st.session_state["translation"] = ""
        st.session_state["doc_text"] = {} # Yüklenen metinleri önbellekte tutmak için
        st.session_state["translated_paragraph"] = ""
        st.session_state["spoken_text"] = ""

    # DOCX dosyasını otomatik olarak yükleyen kısım
    current_script_dir = os.path.dirname(__file__) # app.py'nin bulunduğu dizin
    doc_path_for_processing = os.path.join(current_script_dir,DOCX_FILE_NAME)

    if not os.path.exists(doc_path_for_processing):
        st.error(f"Hata: '{DOCX_FILE_NAME}' dosyası bulunamadı. Lütfen dosyanın uygulamanın (app.py) ile aynı dizinde olduğundan emin olun.")
        return # Dosya yoksa uygulamayı sonlandır

    st.success(f"'{DOCX_FILE_NAME}' dosyası başarıyla yüklendi.")
    # Dosya yüklendiğinde, session state'e yolu kaydetmeye gerek yok, her zaman aynı path'i kullanacak.

    #topic_no = st.number_input("Konu No giriniz:", min_value=1, max_value=TOTAL_TOPICS, step=1,
    #                            help=f"Toplam {TOTAL_TOPICS} konu mevcut. Lütfen 1 ile {TOTAL_TOPICS} arasında bir sayı seçin.")
    topic_no = st.number_input("Konu No giriniz:", min_value=1, max_value=TOTAL_TOPICS, step=1,
                               value=random.randint(1, TOTAL_TOPICS),
                               help=f"Toplam {TOTAL_TOPICS} konu mevcut. Lütfen 1 ile {TOTAL_TOPICS} arasında bir sayı seçin.")

    # Metni Yükle butonu, dosya bulunduğunda her zaman etkin olacak
    if st.button("Metni Yükle"):
        cache_key = f"{DOCX_FILE_NAME}_{topic_no}" # Önbellek anahtarı dosya adı ve konu numarası
        if cache_key not in st.session_state["doc_text"]:
            text = get_text_from_docx(doc_path_for_processing, topic_no)
            if text:
                st.session_state["doc_text"][cache_key] = text
                paragraphs = split_into_paragraphs(text)
                st.session_state["paragraphs"] = paragraphs
                st.session_state["current_index"] = 0
                st.session_state["selected_word"] = None
                st.session_state["translation"] = ""
                st.session_state["translated_paragraph"] = ""
                st.session_state["spoken_text"] = ""
                st.success("Metin yüklendi!")
            else:
                st.error("Konu bulunamadı veya dosya okunamadı! Lütfen doğru konu numarasını girin.")
        else:
            text = st.session_state["doc_text"][cache_key]
            paragraphs = split_into_paragraphs(text)
            st.session_state["paragraphs"] = paragraphs
            st.session_state["current_index"] = 0
            st.session_state["selected_word"] = None
            st.session_state["translation"] = ""
            st.session_state["translated_paragraph"] = ""
            st.session_state["spoken_text"] = ""
            st.info("Metin önbellekten yüklendi!") # Mesajı bilgilendirme olarak değiştirdim

    if st.session_state["paragraphs"]:
        paragraphs = st.session_state["paragraphs"]
        current_index = st.session_state["current_index"]

        st.subheader(f"Paragraf {current_index + 1}/{len(paragraphs)}")
        st.write(paragraphs[current_index])

        if st.button("Paragrafı Çevir", key="translate_paragraph"):
            translated = translate_paragraph(paragraphs[current_index])
            st.session_state["translated_paragraph"] = translated

        if st.session_state["translated_paragraph"]:
            st.write("**Çevrilmiş Paragraf (Türkçe):**")
            st.info(st.session_state["translated_paragraph"])

        st.write("**Kelime çevirisi için kelimelere tıklayın:**")
        cols = st.columns(5)
        for i, word in enumerate(paragraphs[current_index].split()):
            with cols[i % 5]:
                if st.button(word, key=f"word_{i}_{current_index}"):
                    st.session_state["selected_word"] = word
                    st.session_state["translation"] = translate_word(word)
                    play_word(word)

        if st.session_state["selected_word"]:
            st.info(f"'{st.session_state['selected_word']}' çevirisi: {st.session_state['translation']}")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("Paragrafı Oku", key="read_paragraph"):
                read_paragraph(paragraphs[current_index])
        #with col2:
        #    if st.button("Sesimi Kaydet", key="record_speech"):
        #        spoken_text = listen_and_convert()
        #        st.session_state["spoken_text"] = spoken_text
        #        if st.session_state["spoken_text"]:
        #            st.write("**Tanınan Metniniz (Sizin Okumanız):**")
        #            st.success(st.session_state["spoken_text"]) # Tanınan metni başarı olarak göster

        #    if st.session_state["spoken_text"] and not st.session_state["spoken_text"].startswith("Konuşma tanınamadı") \
        #                                     and not st.session_state["spoken_text"].startswith("API hatası") \
        #                                     and not st.session_state["spoken_text"].startswith("Ses kaydı sırasında"):
        #        if st.button("Analizi Yap", key="analyze_speech"):
        #            error_rate, extra_words, missing_words = evaluate_speech(paragraphs[current_index], st.session_state["spoken_text"])
        #            if error_rate < ERROR_THRESHOLD:
        #                st.balloons() # Başarılı okumalarda balonlar uçsun
        #                st.success("Harika! Okumanız oldukça iyi.")
        #            else:
        #                st.warning("Bazı hatalar var. Aşağıdaki raporu inceleyin.")
        #            report_errors(error_rate, extra_words, missing_words)
        #            st.write("**Karşılaştırma:**")
        #            st.markdown(f"**Orijinal Paragraf:** `{paragraphs[current_index]}`")
        #            st.markdown(f"**Sizin Okumanız:** `{st.session_state['spoken_text']}`")
        with col2:
            if st.button("Sesle Oku", key="record_speech"):
                st.write("3 saniye bekleyin...")
                time.sleep(3)
                # FontAwesome mikrofon ikonu ve "Konuş" yazısı
                #---------27.05.2025
                print("🔊 Okumaya başla! (Bip sesiyle beraber)")
                #--------------------------------
                st.markdown(
                    """
                    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
                    <i class="fas fa-microphone-alt" style="font-size: 24px; color: green;"></i>
                    <span style="font-size: 20px; font-weight: bold; margin-left: 10px;">Konuş</span>
                    """,
                    unsafe_allow_html=True
                )
                st.session_state["show_upload"] = True

            if "show_upload" in st.session_state and st.session_state["show_upload"]:
                st.warning("Not: Streamlit Cloud mikrofon erişimine izin vermiyor. Lütfen paragrafı okuduğunuz bir ses dosyasını yükleyin (WAV formatında, en az 45 saniye).")
                audio_file = st.file_uploader("Ses dosyası seçin", type=["wav"], key="speech_upload")
                if audio_file is not None:
                    st.audio(audio_file, format="audio/wav")  # Yüklenen sesi çal
                    spoken_text = listen_and_convert(audio_file)
                    st.session_state["spoken_text"] = spoken_text
                    if st.session_state["spoken_text"]:
                        st.write("**Tanınan Metniniz (Sizin Okumanız):**")
                        st.success(st.session_state["spoken_text"])

                        # Orijinal ve tanınan metni alt alta göster
                        st.write("**Karşılaştırma:**")
                        st.markdown(f"**Orijinal Paragraf:** `{paragraphs[current_index]}`")
                        st.markdown(f"**Sizin Okumanız:** `{st.session_state['spoken_text']}`")

                        # Hataları analiz et ve göster
                        if not st.session_state["spoken_text"].startswith("Konuşma tanınamadı") \
                            and not st.session_state["spoken_text"].startswith("API hatası") \
                            and not st.session_state["spoken_text"].startswith("Ses dosyası işlenirken"):
                            error_rate, extra_words, missing_words = evaluate_speech(paragraphs[current_index], st.session_state["spoken_text"])
                            st.write("**Hata Analizi:**")
                            st.write(f"- **Hata Oranı:** {error_rate:.2%}")
                            st.write(f"- **Fazladan Kelimeler:** {extra_words if extra_words else 'Yok'}")
                            st.write(f"- **Eksik Kelimeler:** {missing_words if missing_words else 'Yok'}")
                            if error_rate < ERROR_THRESHOLD:
                                st.balloons()
                                st.success("Harika! Okumanız oldukça iyi.")
                            else:
                                st.warning("Bazı hatalar var. Yukarıdaki raporu inceleyin.")
# def listen_and_convert():
#     recognizer = sr.Recognizer()
#     with sr.Microphone() as source:
#         st.info("Lütfen konuşmaya başlayın... (45 saniye)")
#         ...

def listen_and_convert(audio_file):
    """Yüklenen ses dosyasını metne çevirir."""
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(audio_file) as source:
            audio = recognizer.record(source)
            spoken_text = recognizer.recognize_google(audio, language="en-US")
            return spoken_text
    except sr.UnknownValueError:
        return "Konuşma tanınamadı. Daha net bir ses dosyası yüklemeyi deneyin."
    except sr.RequestError as e:
        return f"API hatası: {e}. İnternet bağlantınızı veya Google Speech API limitlerini kontrol edin."
    except Exception as e:
        return f"Ses dosyası işlenirken bir hata oluştu: {e}"


        with col3:
            if st.button("Önceki"):
                if current_index > 0:
                    st.session_state["current_index"] -= 1
                    st.session_state["translated_paragraph"] = ""
                    st.session_state["spoken_text"] = ""
                    st.session_state["selected_word"] = None
                    st.session_state["translation"] = ""
                    st.rerun()
                else:
                    st.warning("Bu ilk paragraf, daha geriye gidemezsiniz!")
        with col4:
            if st.button("Sonraki"):
                if current_index < len(paragraphs) - 1:
                    st.session_state["current_index"] += 1
                    st.session_state["translated_paragraph"] = ""
                    st.session_state["spoken_text"] = ""
                    st.session_state["selected_word"] = None
                    st.session_state["translation"] = ""
                    st.rerun()
                else:
                    st.warning("Bu son paragraf, daha ileri gidemezsiniz!")

if __name__ == "__main__":
    main()
