import random
import streamlit as st
import json
from deep_translator import GoogleTranslator
import os
import threading
import time
from pathlib import Path
import numpy as np
import pandas as pd
from gtts import gTTS


# Try importing speech recognition and text-to-speech libraries
try:
    import speech_recognition as sr
    speech_recognition_available = True
except ImportError:
    speech_recognition_available = False

try:
    import pyttsx3
    tts_available = True
except ImportError:
    tts_available = False




# Apply custom styling
st.markdown("""
<style>
    .stButton button {
        width: 100%;
    }
    .success-text {
        color: #0f5132;
        background-color: #d1e7dd;
        padding: 10px;
        border-radius: 5px;
    }
    .info-text {
        color: #055160;
        background-color: #cff4fc;
        padding: 10px;
        border-radius: 5px;
    }
    .warning-text {
        color: #664d03;
        background-color: #fff3cd;
        padding: 10px;
        border-radius: 5px;
    }
    .error-text {
        color: #842029;
        background-color: #f8d7da;
        padding: 10px;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# Constants
DATA_FILE = "data.csv"  # Update to use CSV format
ASSISTANT_NAME = "assistant"
TTS_LOCK = threading.Lock()

# Ensure data file exists
def initialize_data_file():
    if not os.path.exists(DATA_FILE):
        df = pd.DataFrame(columns=["question", "answer"])
        df.to_csv(DATA_FILE, index=False)

# Load data from CSV file
def load_data():
    try:
        df = pd.read_csv(DATA_FILE)
        return {row["question"]: row["answer"] for _, row in df.iterrows()}
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return {}

# Save data to CSV file
def save_data(data):
    df = pd.DataFrame(list(data.items()), columns=["question", "answer"])
    df.to_csv(DATA_FILE, index=False)

# Initialize session state variables
def initialize_session_state():
    """
    Ensure all required session state variables are initialized.
    """
    if 'data' not in st.session_state:
        st.session_state.data = load_data()
    if 'listening' not in st.session_state:
        st.session_state.listening = False
    if 'listen_thread' not in st.session_state:
        st.session_state.listen_thread = None
    if 'recognized_text' not in st.session_state:
        st.session_state.recognized_text = ""
    if 'last_response' not in st.session_state:
        st.session_state.last_response = ""
    if 'status_text' not in st.session_state:
        st.session_state.status_text = "Listening stopped"
    if 'engine' not in st.session_state and tts_available:
        try:
            engine = pyttsx3.init()
            voices = engine.getProperty('voices')
            # Set female voice
            for voice in voices:
                if "female" in voice.name.lower():
                    engine.setProperty('voice', voice.id)
                    break
            # If no female voice found, try to use the second voice (often female)
            if len(voices) > 1:
                engine.setProperty('voice', voices[1].id)
            # Set speech rate
            engine.setProperty('rate', 150)
            st.session_state.engine = engine
        except Exception as e:
            st.session_state.engine = None
            st.error(f"Error initializing text-to-speech: {e}")

#......................................................................................... 
# Comprehensive rewrite of speaking and response functions

def speak(text):
    """
    Enhanced text-to-speech function with robust error handling and female voice preference.
    """
    # Ensure text is a string
    text = str(text)
    
    # First try pyttsx3 if available
    if tts_available and hasattr(st.session_state, 'engine') and st.session_state.engine:
        try:
            engine = st.session_state.engine
            # Speak the text
            engine.say(text)
            engine.runAndWait()
            return text
        except Exception as e:
            st.error(f"pyttsx3 TTS error: {e}")
    
    # Fallback to gTTS if pyttsx3 fails
    try:
        tts = gTTS(text, lang='en')
        audio_file = "temp_speech.mp3"
        tts.save(audio_file)
        st.audio(audio_file, format='audio/mp3')
        os.remove(audio_file)
        return text
    except Exception as e:
        st.error(f"gTTS TTS error: {e}")
        return text



def find_answer(query):
    """
    Find an answer from the local knowledge base.
    """
    if query in st.session_state.data:
        response = st.session_state.data[query]
        st.session_state.last_response = response
        speak(response)
        return response
    return "I don't know the answer to that question."

def continuous_listen():
    """
    Improved continuous listening function with robust error handling
    """
    while st.session_state.listening:
        try:
            # Recognize speech
            text = recognize_speech()
            st.session_state.recognized_text = text
            
            # Check for assistant activation
            if ASSISTANT_NAME in text.lower():
                # Extract query by removing assistant name
                query = text.lower().replace(ASSISTANT_NAME, "").strip()
                
                # Find and speak answer
                answer = find_answer(query)
            
            # Prevent high CPU usage
            time.sleep(0.1)
        
        except Exception as e:
            # Log and handle any unexpected errors
            st.session_state.status_text = f"Listening error: {str(e)}"
            time.sleep(1)  # Prevent rapid error cycling

# Speech recognition function
def recognize_speech():
    if not speech_recognition_available:
        return "Speech recognition not available"
    
    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            st.session_state.status_text = "Adjusting for ambient noise..."
            recognizer.adjust_for_ambient_noise(source, duration=1)
            st.session_state.status_text = "Listening..."
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
            st.session_state.status_text = "Recognizing..."
            text = recognizer.recognize_google(audio).lower()
            st.session_state.status_text = f"Recognized: {text}"
            return text
    except sr.UnknownValueError:
        return "Could not understand audio"
    except sr.RequestError:
        return "Could not request results; check network connection"
    except Exception as e:
        return f"Error: {str(e)}"

# Start listening
def start_listening():
    if not speech_recognition_available:
        st.error("Speech recognition is not available. Please install the required libraries.")
        return
    
    # Stop any existing thread
    if st.session_state.listening:
        stop_listening()
        time.sleep(0.5)  # Give it time to stop
    
    st.session_state.listening = True
    st.session_state.status_text = "Starting to listen..."
    # Create and start a new thread
    listen_thread = threading.Thread(target=continuous_listen, daemon=True)
    listen_thread.start()
    st.session_state.listen_thread = listen_thread

# Stop listening
def stop_listening():
    if st.session_state.listening:
        st.session_state.listening = False
        st.session_state.status_text = "Listening stopped"
        # No need to join the thread as it's daemonic and will terminate when the main thread exits

# Add question and answer
def add_question(question, answer):
    st.session_state.data[question.lower().strip()] = answer.strip()
    save_data(st.session_state.data)

# Delete question
def delete_question(question):
    if question in st.session_state.data:
        del st.session_state.data[question]
        save_data(st.session_state.data)
        return True
    return False

# Training data into token format
def generate_token_training_data():
    token_data = []
    for question, answer in st.session_state.data.items():
        # Simple tokenization by splitting on spaces
        q_tokens = question.lower().split()
        a_tokens = answer.split()
        
        # Create token pairs for training
        token_data.append({
            "input_tokens": q_tokens,
            "output_tokens": a_tokens,
            "original_question": question,
            "original_answer": answer
        })
    
    # Save token data for training purposes
    with open("token_data.json", "w") as f:
        json.dump(token_data, f, indent=4)
    
    return len(token_data)

# New page for multilingual translator
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

# Main app structure
def main():
    # Initialize data and session state
    initialize_data_file()
    initialize_session_state()
    
    # Create sidebar for navigation
    with st.sidebar:
        st.title("🤖 Mila AI Voice announcement ")
        
        page = st.radio("Navigation", ["Translator"])  # Removed "Assistant" and "Management"
        
        st.divider()
        
       
    
        
        # About section
        with st.expander("About"):
            st.markdown("""
            **AI Voice Assistant**
            
            A voice-activated assistant that can answer questions based on its knowledge base.
            
            Features:
            - Real-time voice recognition
            - multi language translation
            - Knowledge management
            - fredly user interface
            """)
    
    # Render the selected page
    if page == "Translator":
        render_translator_page()

    

    # Thread management for the assistant
    if 'assistant_thread' not in st.session_state:
        st.session_state.assistant_thread = None



if __name__ == "__main__":
    main()

class HumanoidVoiceAssistant:
    def __init__(self):
        # Initialize speech recognition and text-to-speech
        self.recognizer = sr.Recognizer()
        self.tts_engine = pyttsx3.init()
        
        # Configure TTS voice
        voices = self.tts_engine.getProperty('voices')
        for voice in voices:
            if 'female' in voice.name.lower():
                self.tts_engine.setProperty('voice', voice.id)
                break
        
        # Speaking rate and volume
        self.tts_engine.setProperty('rate', 160)
        
        # Conversation context
        self.context = {
            'interactions': [],
            'current_topic': None,
            'user_preferences': {}
        }
        
        # Load existing knowledge
        self.load_knowledge()
    
    def load_knowledge(self):
        """Load existing Q&A data"""
        try:
            with open('data.json', 'r') as f:
                self.knowledge_base = json.load(f)
        except FileNotFoundError:
            self.knowledge_base = {}
    
    def speak(self, text):
        """Enhanced speaking method with multiple TTS options"""
        try:
            # First try pyttsx3
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
        except Exception:
            # Fallback to gTTS
            try:
                tts = gTTS(text, lang='en')
                audio_file = "response.mp3"
                tts.save(audio_file)
                st.audio(audio_file, format="audio/mp3")
                os.remove(audio_file)
            except Exception as e:
                st.error(f"Speech synthesis failed: {e}")
    
    def recognize_speech(self):
        """Advanced speech recognition with noise reduction"""
        try:
            with sr.Microphone() as source:
                st.info("Listening...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=5)
                text = self.recognizer.recognize_google(audio).lower()
                return text
        except sr.UnknownValueError:
            st.warning("Sorry, I didn't catch that. Could you repeat?")
            return None
        except sr.RequestError:
            st.error("Speech recognition service is unavailable. Please check your internet connection.")
            return None
        except Exception as e:
            st.error(f"An error occurred during speech recognition: {e}")
            return None
    
    def process_query(self, query):
        """Advanced query processing with context awareness"""
        # Check for wake words
        # Define AssistantConfig with WAKE_WORDS if not already defined
        class AssistantConfig:
            WAKE_WORDS = ["assistant", "hey assistant", "hello assistant"]

        if not any(wake in query for wake in AssistantConfig.WAKE_WORDS):
            return None
        
        # Remove wake words
        for wake_word in AssistantConfig.WAKE_WORDS:
            query = query.replace(wake_word, '').strip()
        
        # Check for farewell
        if any(phrase in query for phrase in AssistantConfig.FAREWELL_PHRASES):
            response = random.choice(AssistantConfig.FAREWELL_RESPONSES)
            self.speak(response)
            return response
        
        # Fuzzy matching in knowledge base
        best_match = self.find_best_match(query)
        
        if best_match:
            response = self.knowledge_base[best_match]
        else:
            response = "I'm not sure about that. Could you tell me more?"
        
        # Update context
        self.context['interactions'].append({
            'query': query,
            'response': response
        })
        
        return response
    
    def find_best_match(self, query):
        """Fuzzy matching algorithm for finding closest question"""
        best_match = None
        best_score = 0
        
        for known_question in self.knowledge_base.keys():
            # Simple token-based similarity
            query_tokens = set(query.split())
            known_tokens = set(known_question.split())
            
            # Calculate overlap
            common_tokens = query_tokens.intersection(known_tokens)
            score = len(common_tokens) / max(len(query_tokens), len(known_tokens))
            
            if score > best_score:
                best_score = score
                best_match = known_question
        
        return best_match if best_score > 0.5 else None
    
    def interactive_loop(self):
        """Main interactive conversation loop"""
        # Define AssistantConfig if not already defined
        class AssistantConfig:
            GREETING_RESPONSES = [
                "Hello! How can I assist you today?",
                "Hi there! What can I do for you?",
                "Greetings! How may I help you?"
            ]

        self.speak(random.choice(AssistantConfig.GREETING_RESPONSES))
        
        while True:
            query = self.recognize_speech()
            
            if query:
                response = self.process_query(query)
                
                if response:
                    self.speak(response)
            
            time.sleep(0.5)  # Prevent high CPU usage

def main():
    st.title("🤖 Mila Voice Assistant")
    
    assistant = HumanoidVoiceAssistant()
    
    if st.button("Start Interactive Mode"):
        with st.spinner("Initializing Humanoid Assistant..."):
            assistant.interactive_loop()
