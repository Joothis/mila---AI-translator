import speech_recognition as sr
from gtts import gTTS
import os
import config
import pygame

def speech_to_text():
    """Converts spoken audio to text using SpeechRecognition."""
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("🎙️ Listening...")
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)

    try:
        text = recognizer.recognize_google(audio)
        print(f"Recognized Text: {text}")
        return text
    except sr.UnknownValueError:
        return "Could not understand audio"
    except sr.RequestError:
        return "Speech Recognition API is not available"

def text_to_speech(text, lang="en"):
    """Converts text to speech using gTTS."""
    tts = gTTS(text=text, lang=lang, slow=False)
    tts.save("output.mp3")

    pygame.init()
    pygame.mixer.init()
    pygame.mixer.music.load("output.mp3")
    pygame.mixer.music.play()
    
    while pygame.mixer.music.get_busy():
        continue
    
    os.remove("output.mp3")
