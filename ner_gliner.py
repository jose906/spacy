# -*- coding: utf-8 -*-

import os
import threading

from gliner import GLiNER


MODEL_NAME = os.environ.get(
    "NETVORA_GLINER_MODEL",
    "urchade/gliner_multi-v2.1",
)


GLINER_LABELS = [
    "person",
    "organization",
    "location",
]


LABEL_MAP = {
    "person": "PER",
    "organization": "ORG",
    "location": "LOC",
}


# ============================================================
# MODELO SINGLETON
# ============================================================

_model = None
_model_lock = threading.Lock()


def get_gliner_model():
    """
    Carga GLiNER una sola vez por instancia.

    No se carga durante el import del módulo.

    Esto evita que endpoints como /test carguen
    innecesariamente el modelo.
    """

    global _model

    if _model is not None:
        return _model

    with _model_lock:

        if _model is not None:
            return _model

        print(
            f"🧠 Cargando GLiNER: {MODEL_NAME}",
            flush=True,
        )

        model = GLiNER.from_pretrained(
            MODEL_NAME
        )

        # Inferencia solamente.
        try:
            model.eval()
        except Exception:
            pass

        _model = model

        print(
            "✅ GLiNER cargado correctamente.",
            flush=True,
        )

        return _model


# ============================================================
# EXTRACCIÓN
# ============================================================

def extract_gliner_entities(
    text,
    threshold=0.5,
):
    """
    Extrae entidades con GLiNER.

    Retorna el formato usado internamente por NetVora.
    """

    if not isinstance(text, str):
        return []

    if not text.strip():
        return []

    model = get_gliner_model()

    predictions = model.predict_entities(
        text,
        GLINER_LABELS,
        threshold=threshold,
    )

    entities = []

    for prediction in predictions:

        gliner_label = prediction.get(
            "label"
        )

        netvora_label = LABEL_MAP.get(
            gliner_label
        )

        if not netvora_label:
            continue

        entities.append({
            "text": prediction["text"],
            "label": netvora_label,

            "start_char": prediction[
                "start"
            ],

            "end_char": prediction[
                "end"
            ],

            "detection_source": "ner",

            "ner_model": "gliner",

            "model_confidence": float(
                prediction["score"]
            ),
        })

    return entities