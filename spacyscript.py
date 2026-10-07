# -*- coding: utf-8 -*-


import os
import re
import unicodedata

import spacy
from spacy.matcher import Matcher

from entity_patterns import KNOWN_ENTITY_PATTERNS, STRUCTURAL_PATTERNS
from entity_resolver import should_resolve_entity
from ner_gliner import extract_gliner_entities


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
            # Si el catálogo ya trae un token pattern explícito, se conserva.
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
    """Conserva el contenido del hashtag, pero lo aísla del texto vecino.

    Ejemplos:
      Senasag #Economía -> Senasag. Economía.
      #GrupoFides #ANF  -> Grupo Fides. ANF.

    La frontera evita falsos spans como ``Senasag Economía``.
    """
    hashtag = split_camel_case(match.group(1))

    if not hashtag:
        return " "

    return ". " + hashtag + ". "


def replace_mention(match):
    """Elimina handles: no deben convertirse en candidatos NER."""

    # @correodelsurcom no debe transformarse en una falsa LOC/ORG/PER.
    return " "


def _remove_editorial_credits(text):
    """Elimina créditos fotográficos/editoriales sin tragarse el contenido."""

    # Crédito compacto asociado al emoji:
    #
    # 📸APG El ministro...
    # -> El ministro...
    #
    # 📷 ABI Conferencia...
    # -> Conferencia...
    #
    # Se elimina SOLO el primer token inmediatamente asociado al emoji.
    text = re.sub(
        r"(?:📸|📷)\s*"
        r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9_.\-]{2,30}"
        r"(?=\s|$)",
        " ",
        text,
    )

    # Formatos explícitos de crédito permiten nombres de hasta 4 tokens:
    #
    # Foto: APG
    # Crédito: Juan Pérez
    # Fotografía - APG Noticias
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

    for invisible in (
        "\ufe0f",
        "\ufe0e",
        "\u200b",
        "\ufeff",
        "\u2060",
    ):
        text = text.replace(invisible, " ")

    text = text.replace("\xa0", " ")

    text = (
        text
        .replace("\n", " ")
        .replace("\r", " ")
        .replace("\t", " ")
    )

    # RT aislado, con dos puntos opcionales.
    text = re.sub(
        r"(?i)(?<!\w)RT(?!\w)\s*:?\s*",
        " ",
        text,
    )

    # URLs completas o www.*
    text = re.sub(
        r"https?://\S+|www\.\S+",
        " ",
        text,
        flags=re.IGNORECASE,
    )

    # Créditos editoriales antes de limpiar emojis.
    text = _remove_editorial_credits(text)

    # Mentions se eliminan.
    text = re.sub(
        r"@([A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9_]+)",
        replace_mention,
        text,
    )

    # Hashtags conservan el contenido semántico,
    # pero quedan separados del texto vecino.
    text = re.sub(
        r"#([A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9_]+)",
        replace_hashtag,
        text,
    )

    # Separadores editoriales.
    text = re.sub(
        r"\s*[|│]\s*",
        ". ",
        text,
    )

    patterns_remove = (
        r"(?i)\blea\s+m[aá]s\b\s*:?\s*",
        r"(?i)\blee\s+m[aá]s\b\s*:?\s*",
        r"(?i)\bm[aá]s\s+informaci[oó]n\b\s*:?\s*",
        r"(?i)\bmant[eé]ngase\s+informado\b\s*:?\s*",
    )

    for pattern in patterns_remove:
        text = re.sub(
            pattern,
            " ",
            text,
        )

    # Emojis/editoriales residuales.
    text = re.sub(
        r"[★☆◆◉▪🔴🔵🟢🟡🟠🟣🟤⚫⚪"
        r"🟥🟦🟩🟨🟧🟪✅✔✳🔹🔸▶🔻🔺"
        r"📌📷📸📹🎥]+",
        " ",
        text,
    )

    # Comillas/puntuación Unicode a representación estable.
    text = (
        text
        .replace("“", '"')
        .replace("”", '"')
        .replace("‘", "'")
        .replace("’", "'")
        .replace("…", "...")
    )

    # Normaliza puntuación introducida por hashtags/separadores.
    text = re.sub(
        r"\s+([.,;:!?])",
        r"\1",
        text,
    )

    text = re.sub(
        r"(?:\.\s*){2,}",
        ". ",
        text,
    )

    text = re.sub(
        r"([!?.,:;])\1{2,}",
        r"\1",
        text,
    )

    text = re.sub(
        r"^\s*\.\s*",
        "",
        text,
    )

    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


def normalize_entity(ent_text):
    """Limpia bordes sin destruir la grafía original de la entidad."""

    if not isinstance(ent_text, str) or not ent_text:
        return ""

    entity = unicodedata.normalize(
        "NFKC",
        ent_text,
    ).strip()

    entity = entity.strip(
        " \t\r\n,;:!? .\"'()[]{}<>-–—"
    )

    entity = re.sub(
        r"\s+",
        " ",
        entity,
    )

    return entity.strip()


def is_valid_entity(ent_text, label=None):
    if not isinstance(ent_text, str) or not ent_text:
        return False

    value = ent_text.strip()

    if len(value) < 2:
        return False

    if not re.search(
        r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]",
        value,
    ):
        return False

    if re.fullmatch(
        r"[\W_]+",
        value,
        flags=re.UNICODE,
    ):
        return False

    if re.fullmatch(
        r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]",
        value,
    ):
        return False

    if re.search(
        r"https?://|www\.",
        value,
        flags=re.IGNORECASE,
    ):
        return False

    if value.startswith("@"):
        return False

    noise = {
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

    return value.casefold() not in noise


def entity_key(text):
    """Clave ligera para deduplicación/contexto dentro del mismo documento."""

    if not isinstance(text, str):
        return ""

    text = unicodedata.normalize(
        "NFKC",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip().casefold()


def _apply_contextual_canonicalization(
    entity_text,
    label,
    canonical_id,
    detection_source,
    clean_text,
):
    """Corrige entidades altamente ambiguas usando el contexto completo.

    Esta capa NO sustituye al NER ni al EntityRuler.

    Solo interviene cuando una forma superficial es ambigua
    y necesita contexto para obtener tipo y canonical_id correctos.

    Caso actual:
        EVO / Evo -> Evo Morales únicamente en contexto político suficiente.

    IMPORTANTE:
        - No usa ``Evo`` como alias global case-insensitive.
        - Permite titulares completamente en mayúsculas.
        - Si EntityRuler ya entregó canonical_id, se respeta y no se toca.
    """

    # Si ya viene resuelto por el catálogo, no lo modificamos.
    if canonical_id:
        return (
            label,
            canonical_id,
            detection_source,
        )

    normalized_entity = entity_key(entity_text)
    normalized_text = entity_key(clean_text)

    # ==========================================================
    # EVO / Evo -> Evo Morales
    # ==========================================================
    #
    # No usamos "Evo" como alias global porque "EVO"
    # también podría ser una sigla en otro contexto.
    #
    # Sin embargo, en un contexto claramente asociado a:
    #
    # - Trópico
    # - Chapare
    # - cocaleros
    # - dirigentes
    # - expresidente
    #
    # se trata como Evo Morales.
    # ==========================================================

    if normalized_entity == "evo":

        evo_context_patterns = (
            r"\bevo\s+morales\b",

            r"\b(?:ex\s*presidente|expresidente)"
            r"\s+evo\b",

            r"\bevo\b.{0,100}\btr[oó]pico\b",

            r"\btr[oó]pico\b.{0,100}\bevo\b",

            r"\bevo\b.{0,100}\bchapare\b",

            r"\bchapare\b.{0,100}\bevo\b",

            r"\bevo\b.{0,100}"
            r"\bcocaler(?:o|os|a|as)?\b",

            r"\bcocaler(?:o|os|a|as)?\b"
            r".{0,100}\bevo\b",

            r"\bevo\s+y\s+(?:los\s+)?dirigentes\b",

            r"\bdirigentes\b.{0,100}\bevo\b",
        )

        if any(
            re.search(
                pattern,
                normalized_text,
                flags=re.IGNORECASE,
            )
            for pattern in evo_context_patterns
        ):
            return (
                "PER",
                "EVO_MORALES",
                "contextual",
            )

    return (
        label,
        canonical_id,
        detection_source,
    )


def _get_structural_spans(doc):
    spans = set()

    for match_id, start, end in _STRUCTURAL_MATCHER(doc):

        label = _STRUCTURAL_LABELS.get(
            match_id
        )

        spans.add(
            (
                start,
                end,
                label,
            )
        )

    return spans


def _token_feature(
    token,
    attr,
    default="",
):
    if token is None:
        return default

    value = getattr(
        token,
        attr,
        default,
    )

    return (
        value
        if value is not None
        else default
    )


def _gliner_to_spacy_span(doc, entity):
    """Convierte una entidad GLiNER en un Span de spaCy."""

    span = doc.char_span(
        entity["start_char"],
        entity["end_char"],
        alignment_mode="expand",
    )

    return span
def _get_gliner_entities_detailed(doc, clean_text):

    predictions = extract_gliner_entities(clean_text)

    entities = []

    for prediction in predictions:

        span = _gliner_to_spacy_span(
            doc,
            prediction,
        )

        if span is None:
            continue

        root = span.root

        head = root.head if root is not None else None

        prev_token = (
            doc[span.start - 1]
            if span.start > 0
            else None
        )

        next_token = (
            doc[span.end]
            if span.end < len(doc)
            else None
        )

        entities.append({
            "text": normalize_entity(
                prediction["text"]
            ),

            "label": prediction["label"],

            "canonical_id": None,

            "start_char": prediction["start_char"],

            "end_char": prediction["end_char"],

            "detection_source": "ner",

            "ner_model": "gliner",

            "model_confidence": prediction["model_confidence"],

            "root_pos": _token_feature(
                root,
                "pos_",
            ),

            "root_lemma": _token_feature(
                root,
                "lemma_",
            ),

            "root_dep": _token_feature(
                root,
                "dep_",
            ),

            "head_pos": _token_feature(
                head,
                "pos_",
            ),

            "head_lemma": _token_feature(
                head,
                "lemma_",
            ),

            "prev_lower": _token_feature(
                prev_token,
                "lower_",
            ),

            "next_lower": _token_feature(
                next_token,
                "lower_",
            ),

            "next_lemma": _token_feature(
                next_token,
                "lemma_",
            ),

            "next_pos": _token_feature(
                next_token,
                "pos_",
            ),

            "span_pos": [
                token.pos_
                for token in span
            ],
        })

    return entities


def _merge_gliner_with_rules(gliner_entities, rule_doc):
    """
    Fusiona GLiNER con EntityRuler.
    Si una regla se solapa con GLiNER, gana la regla.
    """

    rule_entities = []

    for ent in rule_doc.ents:
        rule_entities.append({
            "text": ent.text,
            "label": ent.label_,
            "start_char": ent.start_char,
            "end_char": ent.end_char,
            "canonical_id": ent.ent_id_ or None,
            "detection_source": (
                "ruler"
                if ent.ent_id_
                else "ruler_structural"
            ),
        })

    merged = list(rule_entities)

    for entity in gliner_entities:

        overlaps_rule = any(
            entity["start_char"] < rule["end_char"]
            and entity["end_char"] > rule["start_char"]
            for rule in rule_entities
        )

        if not overlaps_rule:
            merged.append(entity)

    return merged

def _enrich_merged_entities(doc, entities):

    result = []

    for entity in entities:

        span = doc.char_span(
            entity["start_char"],
            entity["end_char"],
            alignment_mode="expand",
        )

        if span is None:
            continue

        root = span.root
        head = root.head if root is not None else None

        prev_token = (
            doc[span.start - 1]
            if span.start > 0
            else None
        )

        next_token = (
            doc[span.end]
            if span.end < len(doc)
            else None
        )

        enriched = dict(entity)

        enriched.update({
            "root_pos": _token_feature(root, "pos_"),
            "root_lemma": _token_feature(root, "lemma_"),
            "root_dep": _token_feature(root, "dep_"),
            "head_pos": _token_feature(head, "pos_"),
            "head_lemma": _token_feature(head, "lemma_"),
            "prev_lower": _token_feature(prev_token, "lower_"),
            "next_lower": _token_feature(next_token, "lower_"),
            "next_lemma": _token_feature(next_token, "lemma_"),
            "next_pos": _token_feature(next_token, "pos_"),
            "span_pos": [
                token.pos_
                for token in span
            ],
        })

        result.append(enriched)

    return result

def get_entities_detailed_gliner(text):

    clean_text = preprocess_text(text)

    if not clean_text:
        return {
            "PER": [],
            "ORG": [],
            "LOC": [],
            "MISC": [],
        }

    # spaCy sigue haciendo:
    # POS, dependencias, lemas y EntityRuler,
    # pero desactivamos su NER estadístico.
    with nlp.select_pipes(disable=["ner"]):
        doc = nlp(clean_text)

    # NER principal
    gliner_entities = extract_gliner_entities(
        clean_text
    )

    # GLiNER + reglas conocidas/estructurales
    merged = _merge_gliner_with_rules(
        gliner_entities,
        doc,
    )

    # Agregamos features lingüísticos de spaCy
    merged = _enrich_merged_entities(
        doc,
        merged,
    )

    entities = {
        "PER": [],
        "ORG": [],
        "LOC": [],
        "MISC": [],
    }

    seen = {
        "PER": set(),
        "ORG": set(),
        "LOC": set(),
        "MISC": set(),
    }

    for entity in merged:

        entity_text = normalize_entity(
            entity["text"]
        )

        original_label = entity.get(
            "label",
            "MISC",
        )

        if original_label not in entities:
            original_label = "MISC"

        if not is_valid_entity(
            entity_text,
            original_label,
        ):
            continue

        canonical_id = entity.get(
            "canonical_id"
        )

        detection_source = entity.get(
            "detection_source",
            "ner",
        )

        # Conservamos tu lógica contextual,
        # por ejemplo EVO -> Evo Morales.
        (
            label,
            canonical_id,
            detection_source,
        ) = _apply_contextual_canonicalization(
            entity_text=entity_text,
            label=original_label,
            canonical_id=canonical_id,
            detection_source=detection_source,
            clean_text=clean_text,
        )

        if label not in entities:
            label = "MISC"

        key = entity_key(
            entity_text
        )

        if key in seen[label]:
            continue

        seen[label].add(key)

        final_entity = dict(entity)

        final_entity.update({
            "text": entity_text,
            "label": label,
            "canonical_id": canonical_id,
            "detection_source": detection_source,
        })

        entities[label].append(
            final_entity
        )

    return entities

def get_resolvable_entities_gliner(text):

    detailed = get_entities_detailed_gliner(text)

    return {
        label: [
            entity
            for entity in label_entities
            if should_resolve_entity(
                entity,
                text=text,
            )
        ]
        for label, label_entities
        in detailed.items()
    }
    
def get_entities_gliner(text):

    detailed = get_entities_detailed_gliner(text)

    return {
        label: [
            entity["text"]
            for entity in label_entities
        ]
        for label, label_entities
        in detailed.items()
    }

def get_entities_detailed(text):
    clean_text = preprocess_text(text)

    if not clean_text:
        return {
            "PER": [],
            "ORG": [],
            "LOC": [],
            "MISC": [],
        }

    doc = nlp(clean_text)

    structural_spans = _get_structural_spans(
        doc
    )

    entities = {
        "PER": [],
        "ORG": [],
        "LOC": [],
        "MISC": [],
    }

    seen = {
        "PER": set(),
        "ORG": set(),
        "LOC": set(),
        "MISC": set(),
    }

    for ent in doc.ents:

        # ------------------------------------------------------
        # Tipo ORIGINAL entregado por spaCy / EntityRuler
        # ------------------------------------------------------

        original_label = (
            ent.label_
            if ent.label_ in entities
            else "MISC"
        )

        entity_text = normalize_entity(
            ent.text
        )

        if not is_valid_entity(
            entity_text,
            original_label,
        ):
            continue

        # ------------------------------------------------------
        # Fuente original
        # ------------------------------------------------------

        canonical_id = (
            ent.ent_id_
            or None
        )

        if canonical_id:

            detection_source = "ruler"

        elif (
            ent.start,
            ent.end,
            original_label,
        ) in structural_spans:

            detection_source = (
                "ruler_structural"
            )

        else:

            detection_source = "ner"

        # ------------------------------------------------------
        # Corrección contextual
        #
        # IMPORTANTE:
        # esto ocurre ANTES de deduplicar.
        #
        # Puede cambiar:
        #
        # EVO ORG
        #
        # a:
        #
        # EVO PER / EVO_MORALES
        # ------------------------------------------------------

        (
            label,
            canonical_id,
            detection_source,
        ) = _apply_contextual_canonicalization(
            entity_text=entity_text,
            label=original_label,
            canonical_id=canonical_id,
            detection_source=detection_source,
            clean_text=clean_text,
        )

        if label not in entities:
            label = "MISC"

        # ------------------------------------------------------
        # Deduplicación DESPUÉS de reclasificación
        # ------------------------------------------------------

        key = entity_key(
            entity_text
        )

        if key in seen[label]:
            continue

        seen[label].add(
            key
        )

        # ------------------------------------------------------
        # Features lingüísticos
        # ------------------------------------------------------

        prev_token = (
            doc[ent.start - 1]
            if ent.start > 0
            else None
        )

        next_token = (
            doc[ent.end]
            if ent.end < len(doc)
            else None
        )

        root = ent.root

        head = (
            root.head
            if root is not None
            else None
        )

        # ------------------------------------------------------
        # Resultado
        # ------------------------------------------------------

        entities[label].append(
            {
                "text": entity_text,

                "label": label,

                "canonical_id": canonical_id,

                # Estos offsets corresponden
                # al texto PREPROCESADO.
                "start_char": ent.start_char,

                "end_char": ent.end_char,

                "detection_source": (
                    detection_source
                ),

                # Features lingüísticos usados
                # por la capa de calidad.
                "root_pos": _token_feature(
                    root,
                    "pos_",
                ),

                "root_lemma": _token_feature(
                    root,
                    "lemma_",
                ),

                "root_dep": _token_feature(
                    root,
                    "dep_",
                ),

                "head_pos": _token_feature(
                    head,
                    "pos_",
                ),

                "head_lemma": _token_feature(
                    head,
                    "lemma_",
                ),

                "prev_lower": _token_feature(
                    prev_token,
                    "lower_",
                ),

                "next_lower": _token_feature(
                    next_token,
                    "lower_",
                ),

                "next_lemma": _token_feature(
                    next_token,
                    "lemma_",
                ),

                "next_pos": _token_feature(
                    next_token,
                    "pos_",
                ),

                "span_pos": [
                    token.pos_
                    for token in ent
                ],
            }
        )

    return entities


def get_entities(text):
    """Interfaz legacy: retorna listas de strings por tipo."""

    detailed = get_entities_detailed(
        text
    )

    return {
        label: [
            entity["text"]
            for entity in label_entities
        ]
        for label, label_entities
        in detailed.items()
    }


def get_resolvable_entities(text):
    """Salida recomendada para resolve_entity()/tweet_entities."""

    detailed = get_entities_detailed(
        text
    )

    return {
        label: [
            entity
            for entity in label_entities
            if should_resolve_entity(
                entity,
                text=text,
            )
        ]
        for label, label_entities
        in detailed.items()
    }


def debug_entities(text):
    """Debug: salida cruda de spaCy y salida final de NetVora."""

    clean_text = preprocess_text(
        text
    )

    doc = (
        nlp(clean_text)
        if clean_text
        else None
    )

    raw_entities = []

    if doc is not None:

        structural_spans = (
            _get_structural_spans(
                doc
            )
        )

        for ent in doc.ents:

            raw_label = (
                ent.label_
                if ent.label_ in {
                    "PER",
                    "ORG",
                    "LOC",
                    "MISC",
                }
                else "MISC"
            )

            if ent.ent_id_:

                source = "ruler"

            elif (
                ent.start,
                ent.end,
                raw_label,
            ) in structural_spans:

                source = (
                    "ruler_structural"
                )

            else:

                source = "ner"

            raw_entities.append(
                {
                    "text": ent.text,

                    "label": ent.label_,

                    "canonical_id": (
                        ent.ent_id_
                        or None
                    ),

                    "detection_source": (
                        source
                    ),

                    "start": ent.start_char,

                    "end": ent.end_char,

                    "root_pos": (
                        ent.root.pos_
                    ),

                    "root_lemma": (
                        ent.root.lemma_
                    ),
                }
            )

    # spacy_raw conserva deliberadamente
    # la salida cruda.
    #
    # final/resolvable incluyen las
    # correcciones contextuales.

    return {
        "original": text,

        "clean": clean_text,

        "spacy_raw": (
            raw_entities
        ),

        "final": (
            get_entities(
                text
            )
        ),

        "resolvable": (
            get_resolvable_entities(
                text
            )
        ),
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