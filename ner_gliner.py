# -*- coding: utf-8 -*-

from gliner import GLiNER


MODEL_NAME = "urchade/gliner_multi-v2.1"


# ---------------------------------------------------------
# Modelo
# ---------------------------------------------------------

print("Cargando GLiNER...")

model = GLiNER.from_pretrained(MODEL_NAME)

print("GLiNER cargado correctamente.")


# ---------------------------------------------------------
# Etiquetas que le pedimos detectar
# ---------------------------------------------------------

GLINER_LABELS = [
    "person",
    "organization",
    "location",
]


# ---------------------------------------------------------
# Conversión GLiNER -> NetVora
# ---------------------------------------------------------

LABEL_MAP = {
    "person": "PER",
    "organization": "ORG",
    "location": "LOC",
}


# ---------------------------------------------------------
# Extracción
# ---------------------------------------------------------

def extract_gliner_entities(text, threshold=0.5):

    if not isinstance(text, str):
        return []

    

    if not text.strip():
        return []

    predictions = model.predict_entities(
        text,
        GLINER_LABELS,
        threshold=threshold,
    )

    entities = []

    for prediction in predictions:

        gliner_label = prediction["label"]

        netvora_label = LABEL_MAP.get(
            gliner_label
        )

        # Si GLiNER entrega algo que todavía
        # no sabemos mapear, no lo aceptamos.
        if not netvora_label:
            continue

        entities.append({
            "text": prediction["text"],

            "label": netvora_label,

            "start_char": prediction["start"],

            "end_char": prediction["end"],

            "detection_source": "ner",

            "ner_model": "gliner",

            "model_confidence": float(
                prediction["score"]
            ),
        })

    return entities