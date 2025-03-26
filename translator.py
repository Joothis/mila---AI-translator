import requests
import config

def translate_text(text, target_lang):
    """Translates text using Google AI API."""
    url = "https://translation.googleapis.com/language/translate/v2"
    params = {
        "q": text,
        "target": target_lang,
        "format": "text",
        "key": config.GOOGLE_API_KEY
    }
    
    response = requests.post(url, params=params)
    if response.status_code == 200:
        return response.json()["data"]["translations"][0]["translatedText"]
    else:
        return "Translation Error"
