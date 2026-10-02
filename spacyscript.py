# -*- coding: utf-8 -*-
"""Extracción NER de NetVora.

Conserva la interfaz legacy ``get_entities(text)`` y agrega una salida detallada
más una salida filtrada para el resolver normalizado.
Compatible con Python 3.8+ y spaCy 3.x.
"""

import os
import re
import unicodedata

import spacy
from spacy.matcher import Matcher

from entity_patterns import KNOWN_ENTITY_PATTERNS, STRUCTURAL_PATTERNS
from entity_resolver import should_resolve_entity


MODEL_NAME = os.environ.get("NETVORA_SPACY_MODEL", "es_core_news_lg")


def _known_patterns_as_token_patterns(nlp_obj):
    """Convierte frases del catálogo a token patterns case-insensitive.

    Esto evita que EntityRuler tenga que procesar cada frase por el pipeline
    completo al iniciar y elimina el warning W012 asociado al PhraseMatcher.
    La tokenización la hace el tokenizer real del modelo con ``make_doc``.
    """
    converted = []
    for item in KNOWN_ENTITY_PATTERNS:
        pattern = item.get("pattern")
        if isinstance(pattern, str):
            doc = nlp_obj.make_doc(pattern)
            if not doc:
                continue
            token_pattern = [{"LOWER": token.lower_} for token in doc]
            converted.append({
                "label": item["label"],
                "pattern": token_pattern,
                "id": item.get("id"),
            })
        else:
            converted.append(dict(item))
    return converted


def _build_nlp(model_name=MODEL_NAME):
    try:
        nlp_obj = spacy.load(model_name)
    except OSError as exc:
        # Solo para tests locales controlados. En producción NO degradamos
        # silenciosamente a un modelo vacío.
        if os.environ.get("NETVORA_ALLOW_BLANK_SPACY") == "1":
            nlp_obj = spacy.blank("es")
        else:
            raise RuntimeError(
                "No se pudo cargar %s. Instala un modelo español compatible "
                "con tu versión de spaCy (por ejemplo con: python -m spacy "
                "download es_core_news_lg)." % model_name
            ) from exc

    # 1) Reglas estructurales: corrigen errores del NER en estructuras muy
    # específicas. Se ejecutan después del NER y pueden reemplazar solapes.
    structural_kwargs = {}
    if "ner" in nlp_obj.pipe_names:
        structural_kwargs["after"] = "ner"

    structural_ruler = nlp_obj.add_pipe(
        "entity_ruler",
        name="netvora_structural_ruler",
        config={"overwrite_ents": True, "validate": True},
        **structural_kwargs
    )
    structural_ruler.add_patterns(STRUCTURAL_PATTERNS)

    # 2) Catálogo conocido al final: si una regla exacta coincide, gana sobre
    # NER y sobre reglas estructurales, y conserva ent_id_ canónico.
    # Usamos token patterns LOWER para evitar W012 y carga innecesaria.
    known_ruler = nlp_obj.add_pipe(
        "entity_ruler",
        name="netvora_known_ruler",
        after="netvora_structural_ruler",
        config={"overwrite_ents": True, "validate": True},
    )
    known_ruler.add_patterns(_known_patterns_as_token_patterns(nlp_obj))
    return nlp_obj


def _build_structural_matcher(nlp_obj):
    """Matcher paralelo usado solo para identificar la fuente de un span."""
    matcher = Matcher(nlp_obj.vocab, validate=True)
    labels = {}
    for index, item in enumerate(STRUCTURAL_PATTERNS):
        rule_name = "NETVORA_STRUCT_%s_%d" % (item["label"], index)
        matcher.add(rule_name, [item["pattern"]])
        labels[nlp_obj.vocab.strings[rule_name]] = item["label"]
    return matcher, labels


nlp = _build_nlp()
_STRUCTURAL_MATCHER, _STRUCTURAL_LABELS = _build_structural_matcher(nlp)


def split_camel_case(value):
    """Separa CamelCase/PascalCase y guiones bajos sin romper siglas."""
    if not value:
        return value

    value = re.sub(r"_+", " ", value)

    # BoliviaVerifica -> Bolivia Verifica
    value = re.sub(
        r"(?<=[a-záéíóúüñ0-9])(?=[A-ZÁÉÍÓÚÜÑ])",
        " ",
        value,
    )
    # ATBDigital -> ATB Digital; YPFB queda intacto.
    value = re.sub(
        r"(?<=[A-ZÁÉÍÓÚÜÑ])(?=[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ])",
        " ",
        value,
    )
    return re.sub(r"\s+", " ", value).strip()


def replace_hashtag(match):
    hashtag = match.group(1)
    hashtag = split_camel_case(hashtag)

    # Aislamos el hashtag por ambos lados.
    #
    # "Senasag #Economía"
    # -> "Senasag. Economía."
    #
    # "#GrupoFides #ANF #Sucre"
    # -> ". Grupo Fides. . ANF. . Sucre."
    #
    # Evita que spaCy fusione la palabra anterior
    # con el contenido del hashtag.
    return ". " + hashtag + ". "


def replace_mention(match):
    # Los handles NO se convierten en texto para NER.
    # @correodelsurcom no debe transformarse en una falsa LOC/ORG/PER.
    return " "


def _remove_editorial_credits(text):
    """Elimina créditos fotográficos/editoriales que no son contenido NER."""
    # 📸APG / 📷 APG / 📸 Juan Perez
    # Crédito fotográfico compacto:
    # 📸APG -> eliminado
    # 📷 ABI -> eliminado
    # pero NO consume el texto que viene después.

    text = re.sub(
        r'(?:📸|📷)\s*'
        r'[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9_.-]{2,30}'
        r'(?=\s|$)',
        ' ',
        text
    )

    # Foto: APG / Crédito: Juan Pérez / Fotografía - APG Noticias
    text = re.sub(
        r"(?i)\b(?:foto|fotograf[ií]a|cr[eé]dito)\s*[:\-]\s*"
        r"[A-ZÁÉÍÓÚÜÑ0-9][A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9_.\-']{1,30}"
        r"(?:\s+[A-ZÁÉÍÓÚÜÑ0-9][A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9_.\-']{1,30}){0,3}",
        " ",
        text,
    )
    return text


def preprocess_text(text):
    """Limpieza conservadora que mantiene el contexto útil para NER."""
    if not isinstance(text, str) or not text.strip():
        return ""

    text = unicodedata.normalize("NFKC", text)
    for invisible in ("\ufe0f", "\ufe0e", "\u200b", "\ufeff", "\u2060"):
        text = text.replace(invisible, " ")
    text = text.replace("\xa0", " ")
    text = text.replace("\n", " ").replace("\r", " ").replace("\t", " ")

    # RT aislado, con dos puntos opcionales.
    text = re.sub(r"(?i)(?<!\w)RT(?!\w)\s*:?\s*", " ", text)

    # URLs completas o www.*
    text = re.sub(r"https?://\S+|www\.\S+", " ", text, flags=re.IGNORECASE)

    # Créditos editoriales antes de limpiar emojis.
    text = _remove_editorial_credits(text)
    text = re.sub(r'(?:\.\s*){2,}', '. ', text)


    # Mentions se eliminan; hashtags conservan contenido semántico.
    text = re.sub(
        r"@([A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9_]+)",
        replace_mention,
        text,
    )
    text = re.sub(
        r"#([A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9_]+)",
        replace_hashtag,
        text,
    )

    # Separadores editoriales.
    text = re.sub(r"\s*[|│]\s*", ". ", text)

    patterns_remove = (
        r"(?i)\blea\s+m[aá]s\b\s*:?\s*",
        r"(?i)\blee\s+m[aá]s\b\s*:?\s*",
        r"(?i)\bm[aá]s\s+informaci[oó]n\b\s*:?\s*",
        r"(?i)\bmant[eé]ngase\s+informado\b\s*:?\s*",
    )
    for pattern in patterns_remove:
        text = re.sub(pattern, " ", text)

    text = re.sub(
        r"[★☆◆◉▪🔴🔵🟢🟡🟠🟣🟤⚫⚪🟥🟦🟩🟨🟧🟪✅✔✳🔹🔸▶🔻🔺📌📷📸📹🎥]+",
        " ",
        text,
    )

    text = (
        text.replace("“", '"')
        .replace("”", '"')
        .replace("‘", "'")
        .replace("’", "'")
        .replace("…", "...")
    )
    text = re.sub(r"([!?.,:;])\1{2,}", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_entity(ent_text):
    """Limpia bordes sin destruir la grafía original de la entidad."""
    if not isinstance(ent_text, str) or not ent_text:
        return ""

    entity = unicodedata.normalize("NFKC", ent_text).strip()
    entity = entity.strip(" \t\r\n,;:!? .\"'()[]{}<>-–—")
    entity = re.sub(r"\s+", " ", entity)
    return entity.strip()


def is_valid_entity(ent_text, label=None):
    if not isinstance(ent_text, str) or not ent_text:
        return False

    value = ent_text.strip()
    if len(value) < 2:
        return False
    if not re.search(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]", value):
        return False
    if re.fullmatch(r"[\W_]+", value, flags=re.UNICODE):
        return False
    if re.fullmatch(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]", value):
        return False
    if re.search(r"https?://|www\.", value, flags=re.IGNORECASE):
        return False
    if value.startswith("@"):
        return False

    noise = {
        "rt", "lea", "lee", "más", "mas", "video", "vídeo", "foto",
        "fotos", "ahora", "aquí", "aqui", "acá", "aca", "vía", "via",
        "link", "enlace",
    }
    return value.casefold() not in noise


def entity_key(text):
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip().casefold()


def _get_structural_spans(doc):
    spans = set()
    for match_id, start, end in _STRUCTURAL_MATCHER(doc):
        label = _STRUCTURAL_LABELS.get(match_id)
        spans.add((start, end, label))
    return spans


def _token_feature(token, attr, default=""):
    if token is None:
        return default
    value = getattr(token, attr, default)
    return value if value is not None else default


def get_entities_detailed(text):
    clean_text = preprocess_text(text)
    if not clean_text:
        return {"PER": [], "ORG": [], "LOC": [], "MISC": []}

    doc = nlp(clean_text)
    structural_spans = _get_structural_spans(doc)

    entities = {"PER": [], "ORG": [], "LOC": [], "MISC": []}
    seen = {"PER": set(), "ORG": set(), "LOC": set(), "MISC": set()}

    for ent in doc.ents:
        label = ent.label_ if ent.label_ in entities else "MISC"
        entity_text = normalize_entity(ent.text)
        if not is_valid_entity(entity_text, label):
            continue

        key = entity_key(entity_text)
        if key in seen[label]:
            continue
        seen[label].add(key)

        canonical_id = ent.ent_id_ or None
        if canonical_id:
            detection_source = "ruler"
        elif (ent.start, ent.end, label) in structural_spans:
            detection_source = "ruler_structural"
        else:
            detection_source = "ner"

        prev_token = doc[ent.start - 1] if ent.start > 0 else None
        next_token = doc[ent.end] if ent.end < len(doc) else None
        root = ent.root
        head = root.head if root is not None else None

        entities[label].append({
            "text": entity_text,
            "label": label,
            "canonical_id": canonical_id,
            # Estos offsets corresponden al texto PREPROCESADO.
            "start_char": ent.start_char,
            "end_char": ent.end_char,
            "detection_source": detection_source,
            # Features lingüísticos usados solo por la capa de calidad.
            "root_pos": _token_feature(root, "pos_"),
            "root_lemma": _token_feature(root, "lemma_"),
            "root_dep": _token_feature(root, "dep_"),
            "head_pos": _token_feature(head, "pos_"),
            "head_lemma": _token_feature(head, "lemma_"),
            "prev_lower": _token_feature(prev_token, "lower_"),
            "next_lower": _token_feature(next_token, "lower_"),
            "next_lemma": _token_feature(next_token, "lemma_"),
            "next_pos": _token_feature(next_token, "pos_"),
            "span_pos": [token.pos_ for token in ent],
        })

    return entities


def get_entities(text):
    """Interfaz legacy: retorna listas de strings por tipo."""
    detailed = get_entities_detailed(text)
    return {
        label: [entity["text"] for entity in label_entities]
        for label, label_entities in detailed.items()
    }


def get_resolvable_entities(text):
    """Salida recomendada para alimentar resolve_entity()/tweet_entities."""
    detailed = get_entities_detailed(text)
    return {
        label: [
            entity
            for entity in label_entities
            if should_resolve_entity(entity, text=text)
        ]
        for label, label_entities in detailed.items()
    }


def debug_entities(text):
    clean_text = preprocess_text(text)
    doc = nlp(clean_text) if clean_text else None
    raw_entities = []
    if doc is not None:
        structural_spans = _get_structural_spans(doc)
        for ent in doc.ents:
            if ent.ent_id_:
                source = "ruler"
            elif (ent.start, ent.end, ent.label_) in structural_spans:
                source = "ruler_structural"
            else:
                source = "ner"
            raw_entities.append({
                "text": ent.text,
                "label": ent.label_,
                "canonical_id": ent.ent_id_ or None,
                "detection_source": source,
                "start": ent.start_char,
                "end": ent.end_char,
                "root_pos": ent.root.pos_,
                "root_lemma": ent.root.lemma_,
            })

    return {
        "original": text,
        "clean": clean_text,
        "spacy_raw": raw_entities,
        "final": get_entities(text),
        "resolvable": get_resolvable_entities(text),
    }


__all__ = [
    "nlp",
    "preprocess_text",
    "normalize_entity",
    "is_valid_entity",
    "get_entities_detailed",
    "get_entities",
    "get_resolvable_entities",
    "debug_entities",
]
