import re

def clean_text(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-záéíóúñ0-9 ]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text
