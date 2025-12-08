import spacy



nlp = spacy.load("es_core_news_lg")

# Configura tu conexión MySQL
# --- 2. Función para extraer entidades ---
def get_entities(text):
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



