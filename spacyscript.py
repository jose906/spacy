import re
import unicodedata
import spacy
from entity_patterns import ENTITY_PATTERNS

nlp = spacy.load("es_core_news_lg")

ruler = nlp.add_pipe(
    "entity_ruler",
    after="ner",
    config={
        "overwrite_ents": True,
        "phrase_matcher_attr": "LOWER"
    }
)

ruler.add_patterns(ENTITY_PATTERNS)

def preprocess_text(text: str) -> str:
    """
    Limpieza conservadora para NER.

    El objetivo NO es transformar demasiado el texto,
    sino eliminar ruido manteniendo el contexto que spaCy
    necesita para reconocer personas, organizaciones y lugares.
    """

    if not isinstance(text, str) or not text.strip():
        return ""

    # --------------------------------------------------------
    # Unicode
    # --------------------------------------------------------

    text = unicodedata.normalize("NFKC", text)

    # Caracteres invisibles frecuentes
    text = text.replace("\u200b", " ")
    text = text.replace("\ufeff", " ")
    text = text.replace("\u2060", " ")
    text = text.replace("\xa0", " ")

    # Saltos de línea / tabs
    text = text.replace("\n", " ")
    text = text.replace("\r", " ")
    text = text.replace("\t", " ")

    # --------------------------------------------------------
    # RT
    # --------------------------------------------------------

    # Elimina RT como token, pero conserva el resto del texto.
    text = re.sub(
        r'(?i)(?<!\w)RT(?!\w)\s*:?',
        ' ',
        text
    )

    # --------------------------------------------------------
    # URLs
    # --------------------------------------------------------

    text = re.sub(
        r'https?://\S+|www\.\S+',
        ' ',
        text,
        flags=re.IGNORECASE
    )

    

    text = re.sub(
        r'(?<!\w)@([A-Za-z0-9_]+)',
        r'\1',
        text
    )

    # --------------------------------------------------------
    # HASHTAGS
    # --------------------------------------------------------
    #
    # #Bolivia -> Bolivia
    # #SantaCruz -> SantaCruz
    #
    # NO intentamos todavía separar CamelCase.
    # Eso lo podemos agregar posteriormente.
    #

    text = re.sub(
        r'#([A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9_]+)',
        r'\1',
        text
    )
    text = re.sub(r'\s*[|│]\s*', '. ', text)

    # --------------------------------------------------------
    # FRASES DE DISTRIBUCIÓN / CTA
    # --------------------------------------------------------
    #
    # Mantener esta lista MUY conservadora.
    #

    patterns_remove = [
        r'(?i)\blea\s+m[aá]s\b\s*:?',
        r'(?i)\blee\s+m[aá]s\b\s*:?',
        r'(?i)\bm[aá]s\s+informaci[oó]n\b\s*:?',
    ]

    for pattern in patterns_remove:
        text = re.sub(pattern, ' ', text)

    # --------------------------------------------------------
    # SÍMBOLOS DECORATIVOS
    # --------------------------------------------------------

    text = re.sub(
    r'[★☆◆◉▪🔴🔵🟢🟡🟠🟣🟤⚫⚪'
    r'🟥🟦🟩🟨🟧🟪'
    r'✅✔✳🔹🔸▶🔻🔺📷📹🎥]+',
    ' ',
    text
)

    # --------------------------------------------------------
    # COMILLAS
    # --------------------------------------------------------

    text = text.replace('“', '"')
    text = text.replace('”', '"')
    text = text.replace("‘", "'")
    text = text.replace("’", "'")
    text = text.replace("…", "...")

    # --------------------------------------------------------
    # PUNTUACIÓN REPETIDA
    # --------------------------------------------------------

    text = re.sub(
        r'([!?.,:;])\1{2,}',
        r'\1',
        text
    )

    # --------------------------------------------------------
    # ESPACIOS
    # --------------------------------------------------------

    text = re.sub(r'\s+', ' ', text).strip()

    return text
# ============================================================
# 3. NORMALIZAR ENTIDAD
# ============================================================

def normalize_entity(ent_text: str) -> str:
    """
    Limpia únicamente los bordes de una entidad.

    IMPORTANTE:
    No convertimos a minúsculas porque queremos conservar
    el nombre tal como aparece.
    """

    if not ent_text:
        return ""

    entity = unicodedata.normalize("NFKC", ent_text)

    entity = entity.strip()

    # Eliminar puntuación problemática solamente de los extremos.
    entity = re.sub(
        r'^[\s,;:!?."\'()\[\]{}\-–—]+',
        '',
        entity
    )

    entity = re.sub(
        r'[\s,;:!?."\'()\[\]{}\-–—]+$',
        '',
        entity
    )

    # Espacios repetidos
    entity = re.sub(r'\s+', ' ', entity)

    return entity.strip()


# ============================================================
# 4. VALIDAR ENTIDAD
# ============================================================

def is_valid_entity(ent_text: str, label: str = None) -> bool:

    if not ent_text:
        return False

    t = ent_text.strip()

    if len(t) < 2:
        return False

    # --------------------------------------------------------
    # Debe contener por lo menos una letra
    # --------------------------------------------------------

    if not re.search(
        r'[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]',
        t
    ):
        return False

    # --------------------------------------------------------
    # Solo símbolos
    # --------------------------------------------------------

    if re.fullmatch(r'[\W_]+', t):
        return False

    # --------------------------------------------------------
    # Una sola letra
    # --------------------------------------------------------

    if re.fullmatch(
        r'[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]',
        t
    ):
        return False

    # --------------------------------------------------------
    # URLs que pudieran haber sobrevivido
    # --------------------------------------------------------

    if re.search(
        r'https?://|www\.',
        t,
        flags=re.IGNORECASE
    ):
        return False

    # --------------------------------------------------------
    # Username aislado extraño
    # --------------------------------------------------------

    if t.startswith("@"):
        return False

    # --------------------------------------------------------
    # Basura genérica
    # --------------------------------------------------------

    basura = {
        "rt",
        "lea",
        "lee",
        "más",
        "mas",
        "video",
        "vídeo",
        "foto",
        "fotos",
        "ahora",
        "aquí",
        "aqui",
        "acá",
        "aca",
        "vía",
        "via",
        "link",
        "enlace",
    }

    if t.casefold() in basura:
        return False

    return True



def entity_key(text: str) -> str:
    """
    Genera una representación comparable.

    Ejemplo:

    "La Paz" -> "la paz"
    "LA PAZ" -> "la paz"

    Esto solamente se utiliza para deduplicar.
    NO modifica el valor final almacenado.
    """

    text = unicodedata.normalize("NFKC", text)

    text = re.sub(r'\s+', ' ', text)

    return text.strip().casefold()
def get_entities_detailed(text):

    text = preprocess_text(text)

    if not text or not isinstance(text, str):
        return {
            "PER": [],
            "ORG": [],
            "LOC": [],
            "MISC": []
        }

    doc = nlp(text)

    entidades = {
        "PER": [],
        "ORG": [],
        "LOC": [],
        "MISC": []
    }

    seen = {
        "PER": set(),
        "ORG": set(),
        "LOC": set(),
        "MISC": set()
    }

    for ent in doc.ents:

        label = ent.label_

        if label not in entidades:
            label = "MISC"

        entity_text = normalize_entity(ent.text)

        if not is_valid_entity(entity_text, label):
            continue

        key = entity_key(entity_text)

        if key in seen[label]:
            continue

        seen[label].add(key)

        entidades[label].append({
        "text": entity_text,
        "label": label,
        "canonical_id": ent.ent_id_ if ent.ent_id_ else None,
        "start_char": ent.start_char,
        "end_char": ent.end_char,
        "detection_source": (
            "ruler"
            if ent.ent_id_
            else "ner"
        )
})

    return entidades


def get_entities(text):
    """
    Mantiene EXACTAMENTE la interfaz anterior utilizada
    por el proceso actual de NetVora.

    Ejemplo:

    {
        "PER": ["Luis Arce"],
        "ORG": ["YPFB"],
        "LOC": ["La Paz"],
        "MISC": []
    }
    """

    detailed = get_entities_detailed(text)

    return {
        label: [
            entity["text"]
            for entity in entities
        ]
        for label, entities in detailed.items()
    }

# ============================================================
# 7. FUNCIÓN DE DEBUG
# ============================================================

def debug_entities(text):
    """
    Función solamente para pruebas.

    Permite comparar:
    texto original
    texto limpio
    entidades crudas de spaCy
    entidades finales
    """

    clean_text = preprocess_text(text)

    doc = nlp(clean_text)

    raw_entities = []

    for ent in doc.ents:
        raw_entities.append({
            "text": ent.text,
            "label": ent.label_,
            "start": ent.start_char,
            "end": ent.end_char
        })

    return {
        "original": text,
        "clean": clean_text,
        "spacy_raw": raw_entities,
        "final": get_entities(text)
    }
    
texto = "La Confederación Agropecuaria Nacional anunció nuevas medidas."

doc = nlp(texto)

for ent in doc.ents:
        print(
            "TEXT:", ent.text,
            "| LABEL:", ent.label_,
            "| ENT_ID:", ent.ent_id_, flush=True)
    
