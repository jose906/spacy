import spacy
from nltk.stem import WordNetLemmatizer
from nltk.corpus import stopwords
import re

nlp = spacy.load("es_core_news_lg")

# Configura tu conexión MySQL
# --- 2. Función para extraer entidades ---
def get_entities(text):
    text = preprocess_text(text)
    if not text or not isinstance(text, str):
        return {"PER": [], "ORG": [], "LOC": [], "MISC": []}

    doc = nlp(text)
    entidades = {"PER": [], "ORG": [], "LOC": [], "MISC": []}

    for ent in doc.ents:
        if ent.label_ in entidades:
            entidades[ent.label_].append(ent.text)
        else:
            entidades["MISC"].append(ent.text)
    return entidades


def preprocess_text(text: str) -> str:

     # Eliminar URLs (http, https, www)
    texto = re.sub(r'http\S+|www\S+', '', texto)
    
    # Eliminar hashtags (#palabra)
    texto = re.sub(r'#\w+', '', texto)

    # Quitar espacios extra
    texto = re.sub(r'\s+', ' ', texto).strip()

    return texto
    

    
    

