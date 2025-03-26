import streamlit as st
from deep_translator import GoogleTranslator
from gtts import gTTS
import os

def render_translator_page():
    st.title("🌍 Advanced Multilingual Translator & Voice System")

    # Instructions
    st.markdown("""
    Welcome to the Multilingual Translator & Voice System! Here's how to use it:
    1. Enter text (up to 250 words) in the input box below.
    2. Select one or more target languages for translation.
    3. Save, delete, or clear your input text as needed.
    4. Click "Translate & Speak" to see translations and hear them in the selected languages.
    """)

    # Text Input (Limit 250 words)
    text_input = st.text_area(
        "Enter Text (250 words max)", 
        max_chars=250, 
        placeholder="Type or paste your text here..."
    )

    # Language Selection
    st.subheader("Select Target Languages")
    languages = {
        "Kannada": "kn", "Malayalam": "ml", "Tamil": "ta", "Telugu": "te",
        "Hindi": "hi", "Bengali": "bn", "Gujarati": "gu", "Marathi": "mr",
        "Punjabi": "pa", "English": "en"
    }
    selected_languages = st.multiselect(
        "Choose one or more languages for translation:",
        options=list(languages.keys()),
        default=["English"],
        help="Select the languages you want the text to be translated into."
    )

    # Saved Texts
    if "saved_texts" not in st.session_state:
        st.session_state.saved_texts = []

    st.subheader("📜 Saved Translations")
    selected_saved = st.selectbox(
        "Select a saved text to reuse or delete:",
        [""] + st.session_state.saved_texts,
        index=0
    )

    # Action Buttons
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("💾 Save Current Text"):
            if text_input:
                st.session_state.saved_texts.append(text_input)
                st.success("Text saved successfully!")
            else:
                st.warning("Please enter some text to save.")
    with col2:
        if st.button("🗑️ Delete Selected Text"):
            if selected_saved:
                st.session_state.saved_texts.remove(selected_saved)
                st.success("Selected text deleted successfully!")
            else:
                st.warning("No text selected to delete.")
    with col3:
        if st.button("❌ Clear Input"):
            text_input = ""
            st.experimental_rerun()

    # Translation & Speech
    if st.button("🎤 Translate & Speak"):
        if text_input and selected_languages:
            st.subheader("Translations")
            translations = {}
            for lang in selected_languages:
                translated_text = GoogleTranslator(source="auto", target=languages[lang]).translate(text_input)
                translations[lang] = translated_text
                st.write(f"**{lang}:** {translated_text}")

                # Convert to Speech
                tts = gTTS(translated_text, lang=languages[lang])
                audio_file = f"translated_{languages[lang]}.mp3"
                tts.save(audio_file)
                st.audio(audio_file, format="audio/mp3")
                with open(audio_file, "rb") as f:
                    st.download_button(f"⬇ Download {lang} Audio", f, file_name=audio_file)
        else:
            st.warning("Please enter text and select at least one language.")

    # Clean up temporary audio files
    for file in os.listdir():
        if file.startswith("translated_") and file.endswith(".mp3"):
            os.remove(file)
