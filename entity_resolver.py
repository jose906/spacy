# -*- coding: utf-8 -*-

"""
Resolución, filtrado y corrección de entidades para NetVora.

Flujo:

GLiNER / Ruler
    ↓
corrección por conocimiento existente
    ↓
corrección contextual conservadora
    ↓
filtros
    ↓
resolución canonical / alias
    ↓
entities / entity_aliases
"""

import os
import re
import unicodedata

from entity_patterns import (
    ENTITY_CATALOG,
    ENTITY_STOPLIST,
    GENERIC_ENTITY_PHRASES,
)


# ============================================================
# CONFIGURACIÓN
# ============================================================

VALID_ENTITY_TYPES = {
    "PER",
    "ORG",
    "LOC",
    "MISC",
}


GLINER_MIN_CONFIDENCE = float(
    os.environ.get(
        "NETVORA_GLINER_MIN_CONFIDENCE",
        "0.60",
    )
)


# ============================================================
# POS
# ============================================================

_NON_PERSON_SINGLE_TOKEN_POS = {
    "VERB",
    "AUX",
    "ADJ",
    "ADV",
    "DET",
    "PRON",
    "ADP",
    "CCONJ",
    "SCONJ",
    "NUM",
    "PUNCT",
    "SYM",
    "INTJ",
}


_NON_ORG_SINGLE_TOKEN_POS = {
    "VERB",
    "AUX",
    "ADJ",
    "ADV",
    "DET",
    "PRON",
    "ADP",
    "CCONJ",
    "SCONJ",
    "NUM",
    "PUNCT",
    "SYM",
    "INTJ",
}


_NON_LOC_SINGLE_TOKEN_POS = {
    "VERB",
    "AUX",
    "ADJ",
    "ADV",
    "DET",
    "PRON",
    "ADP",
    "CCONJ",
    "SCONJ",
    "NUM",
    "PUNCT",
    "SYM",
    "INTJ",
}


# ============================================================
# ARTÍCULOS / DETERMINANTES
# ============================================================

_LEADING_DETERMINERS = {
    # Español
    "el",
    "la",
    "los",
    "las",
    "un",
    "una",
    "unos",
    "unas",

    # Inglés
    "the",
    "a",
    "an",
    "our",
    "their",
    "his",
    "her",
    "this",
    "that",
    "these",
    "those",
}


# ============================================================
# CARGOS / ROLES
# ============================================================

_ROLE_PORTFOLIO_PREFIXES = (
    "presidente",
    "presidenta",
    "vicepresidente",
    "vicepresidenta",

    "ministro",
    "ministra",
    "viceministro",
    "viceministra",

    "secretario",
    "secretaria",

    "director",
    "directora",

    "diputado",
    "diputada",

    "senador",
    "senadora",

    "legislador",
    "legisladora",

    "gobernador",
    "gobernadora",

    "alcalde",
    "alcaldesa",

    "fiscal",

    "notario",
    "notaria",

    "comandante",

    "titular",
    "responsable",
)


_GENERIC_PERSON_TITLES = {
    "presidente",
    "presidenta",

    "vicepresidente",
    "vicepresidenta",

    "ministro",
    "ministra",

    "viceministro",
    "viceministra",

    "secretario",
    "secretaria",

    "director",
    "directora",

    "diputado",
    "diputada",

    "senador",
    "senadora",

    "legislador",
    "legisladora",

    "gobernador",
    "gobernadora",

    "alcalde",
    "alcaldesa",

    "fiscal",

    "fiscal general",
    "fiscal general interino",

    "notario",
    "notaria",
    "notario de fe publica",

    "comandante",

    "titular",
    "responsable",
}


# ============================================================
# PERSONAS GENÉRICAS
# ============================================================

_GENERIC_PERSON_PHRASES = {

    # Español

    "persona",
    "personas",

    "grupo de personas",

    "victima",
    "victimas",

    "hombre",
    "hombres",

    "mujer",
    "mujeres",

    "menor",
    "menores",

    "nino",
    "ninos",

    "nina",
    "ninas",

    "joven",
    "jovenes",

    "adulto",
    "adultos",

    "deportista",
    "deportistas",

    "afectado",
    "afectados",

    "sospechoso",
    "sospechosos",

    "acusado",
    "acusados",

    "manifestante",
    "manifestantes",

    "trabajador",
    "trabajadores",

    "ciudadano",
    "ciudadanos",

    # Inglés

    "person",
    "people",

    "group of people",

    "victim",
    "victims",

    "man",
    "men",

    "woman",
    "women",

    "athlete",
    "athletes",

    "my friend",
    "friend",
    "friends",
}


# ============================================================
# ORGANIZACIONES GENÉRICAS
# ============================================================

_GENERIC_ORG_PHRASES = {

    "justicia",

    "gobierno",
    "gobiernos",

    "government",
    "governments",

    "bomberos",
    "firefighters",

    "hospital",
    "hospitals",
    "hospitales",

    "autoridad",
    "autoridades",

    "authority",
    "authorities",

    "mafia",
    "mafias",

    "sociedad",
    "society",

    "nacional",

    "christian",
    "christians",

    "zionist",
    "zionists",

    "zionism",

    "magic-mushrooms",
    "magic mushrooms",

    "psilocybin mushrooms",
}


# ============================================================
# REFERENCIAS ORGANIZACIONALES AMBIGUAS
# ============================================================

# Sí pueden representar una ORG,
# pero no son suficientemente específicas para
# crear una entidad nueva.
#
# Ejemplo:
#
# Comité pro Santa Cruz ...
# luego:
# "el comité cívico dijo..."
#
_AMBIGUOUS_ORG_REFERENCES = {
    "comite civico",
}


# ============================================================
# MEDIA GENÉRICOS
# ============================================================

_GENERIC_MEDIA_PATTERNS = (
    r"^irish media$",
    r"^western media$",
    r"^national media$",
    r"^local media$",
    r"^mainstream media$",
    r"^social media$",
)


# ============================================================
# LUGARES GENÉRICOS
# ============================================================

_GENERIC_LOCATION_PHRASES = {

    "plaza",
    "parque",

    "ciudad",
    "ciudades",

    "zona",
    "region",

    "nacional",

    "informate",
    "increible",

    "juqueo",

    # Inglés

    "world",
    "city",
    "cities",

    "park",
    "square",

    "sadly",

    # Fragmento truncado observado
    "parliam",
}


# ============================================================
# EVENTOS
# ============================================================

_EVENT_PREFIXES = {
    "festival",
    "feria",
    "congreso",
    "encuentro",
    "evento",
    "certamen",
}


# ============================================================
# ORGANIZACIONES CONOCIDAS - GUARD DE TIPO
# ============================================================

# Esto evita:
#
# ELDEBER -> PER
# ELDEBER -> LOC
#
# incluso si GLiNER falla.
#
_KNOWN_ORG_TYPE_GUARDS = {
    "el deber",
    "eldeber",
}


# ============================================================
# NORMALIZACIÓN
# ============================================================

def normalize_alias(text):

    if (
        not isinstance(text, str)
        or not text.strip()
    ):
        return ""

    text = unicodedata.normalize(
        "NFKC",
        text,
    )

    text = (
        text
        .replace("’", "'")
        .replace("‘", "'")
        .replace("`", "'")
        .replace("–", "-")
        .replace("—", "-")
    )

    decomposed = unicodedata.normalize(
        "NFKD",
        text,
    )

    text = "".join(
        ch
        for ch in decomposed
        if not unicodedata.combining(ch)
    )

    text = text.casefold()

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    text = text.strip(
        " \t\r\n,.;:!?\\\"'()[]{}<>«»"
    )

    return text.strip()


# ============================================================
# QUITAR ARTÍCULOS
# ============================================================

def _strip_leading_determiners(
    normalized,
):

    if not normalized:
        return ""

    words = normalized.split()

    while (
        words
        and words[0]
        in _LEADING_DETERMINERS
    ):
        words.pop(0)

    return " ".join(words)


# ============================================================
# UTILIDADES DB
# ============================================================

def _row_get(
    row,
    key,
    index=0,
    default=None,
):

    if row is None:
        return default

    if isinstance(row, dict):

        return row.get(
            key,
            default,
        )

    try:

        return row[index]

    except (
        IndexError,
        TypeError,
    ):

        return default


def _safe_float(
    value,
    default,
):

    try:

        return float(value)

    except (
        TypeError,
        ValueError,
    ):

        return default


# ============================================================
# CONFIANZA
# ============================================================

def _confidence_for_source(
    source,
):

    if source in {
        "ruler",
        "manual",
        "catalog",
    }:

        return 1.0

    if source == "ruler_structural":

        return 0.95

    if source == "ner":

        return 0.80

    return 0.75


def _confidence_for_existing_alias(
    alias_source,
    stored_confidence,
):

    base = _confidence_for_source(
        alias_source
    )

    stored = _safe_float(
        stored_confidence,
        base,
    )

    if alias_source in {
        "ruler",
        "manual",
        "catalog",
    }:

        return 1.0

    if alias_source == "ruler_structural":

        return min(
            max(
                stored,
                0.0,
            ),
            0.95,
        )

    if alias_source == "ner":

        return min(
            max(
                stored,
                0.0,
            ),
            0.80,
        )

    return min(
        max(
            stored,
            0.0,
        ),
        1.0,
    )


# ============================================================
# GLINER CONFIDENCE
# ============================================================

def _passes_gliner_confidence(
    entity,
):

    if not isinstance(
        entity,
        dict,
    ):
        return False

    if (
        entity.get(
            "detection_source"
        )
        != "ner"
    ):

        return True

    if (
        entity.get(
            "ner_model"
        )
        != "gliner"
    ):

        return True

    confidence = entity.get(
        "model_confidence"
    )

    if confidence is None:

        return True

    try:

        confidence = float(
            confidence
        )

    except (
        TypeError,
        ValueError,
    ):

        return True

    return (
        confidence
        >= GLINER_MIN_CONFIDENCE
    )


# ============================================================
# CARGO + CARTERA
# ============================================================

def _looks_like_role_portfolio(
    normalized_mention,
    normalized_text,
):

    if (
        not normalized_mention
        or not normalized_text
    ):

        return False

    role_group = (
        "(?:%s)"
        % "|".join(
            map(
                re.escape,
                _ROLE_PORTFOLIO_PREFIXES,
            )
        )
    )

    connector = (
        r"(?:de|del|de la|de los|de las)"
    )

    pattern = (
        r"\b"
        + role_group
        + r"\s+"
        + connector
        + r"\s+"
        + re.escape(
            normalized_mention
        )
        + r"\b"
    )

    return (
        re.search(
            pattern,
            normalized_text,
        )
        is not None
    )


# ============================================================
# SPAN COMPLETO CARGO + CARTERA
# ============================================================

def _is_role_portfolio_span(
    normalized,
):

    if not normalized:

        return False

    role_group = (
        "(?:%s)"
        % "|".join(
            map(
                re.escape,
                _ROLE_PORTFOLIO_PREFIXES,
            )
        )
    )

    pattern = (
        r"^"
        + role_group
        + r"\s+"
        + r"(?:de|del|de la|de los|de las)"
        + r"\s+.+$"
    )

    return (
        re.match(
            pattern,
            normalized,
        )
        is not None
    )


# ============================================================
# PERSONA GENÉRICA
# ============================================================

def _is_generic_person(
    entity,
    normalized,
):

    if (
        normalized
        in _GENERIC_PERSON_PHRASES
    ):

        return True

    if (
        normalized
        in _GENERIC_PERSON_TITLES
    ):

        return True

    if _is_role_portfolio_span(
        normalized
    ):

        return True

    if re.fullmatch(
        (
            r"grupo de "
            r"(?:"
            r"personas"
            r"|hombres"
            r"|mujeres"
            r"|jovenes"
            r"|trabajadores"
            r"|manifestantes"
            r")"
        ),
        normalized,
    ):

        return True

    if re.fullmatch(
        (
            r"group of "
            r"(?:"
            r"people"
            r"|men"
            r"|women"
            r"|workers"
            r"|protesters"
            r")"
        ),
        normalized,
    ):

        return True

    return False


# ============================================================
# ORGANIZACIÓN GENÉRICA
# ============================================================

def _is_generic_org(
    normalized,
):

    if (
        normalized
        in _GENERIC_ORG_PHRASES
    ):

        return True

    for pattern in (
        _GENERIC_MEDIA_PATTERNS
    ):

        if re.fullmatch(
            pattern,
            normalized,
        ):

            return True

    # Economía como concepto.
    if re.fullmatch(
        (
            r"economia"
            r"(?:\s+(?:"
            r"boliviana"
            r"|nacional"
            r"|mundial"
            r"|global"
            r"|local"
            r"))?"
        ),
        normalized,
    ):

        return True

    return False


# ============================================================
# LUGAR GENÉRICO
# ============================================================

def _is_generic_location(
    normalized,
):

    return (
        normalized
        in _GENERIC_LOCATION_PHRASES
    )


# ============================================================
# CORRECCIÓN 1:
# TIPO SEGÚN ENTIDADES / ALIASES EXISTENTES
# ============================================================

def _correct_type_from_existing_alias(
    cursor,
    entity,
):
    """
    Corrige el tipo usando SOLO conocimiento histórico
    considerado confiable.

    NO utilizamos aliases creados simplemente por NER,
    porque la BD histórica puede contener errores.

    Fuentes confiables:
        - ruler
        - manual
        - catalog
        - entidades con external_key
    """

    if cursor is None:
        return entity

    if not isinstance(entity, dict):
        return entity

    # Las entidades provenientes directamente del catálogo/ruler
    # ya tienen prioridad y no necesitan corrección.
    if entity.get("canonical_id"):
        return entity

    mention = entity.get("text")

    if (
        not isinstance(mention, str)
        or not mention.strip()
    ):
        return entity

    normalized = normalize_alias(
        mention
    )

    if not normalized:
        return entity

    cursor.execute(
        """
        SELECT DISTINCT
            e.entity_type,
            e.external_key,
            ea.source,
            ea.confidence

        FROM entity_aliases ea

        INNER JOIN entities e
            ON e.id = ea.entity_id

        WHERE ea.normalized_alias = %s
          AND e.status = 'active'
        """,
        (
            normalized,
        ),
    )

    rows = (
        cursor.fetchall()
        or []
    )

    trusted_types = set()

    trusted_sources = {
        "ruler",
        "manual",
        "catalog",
    }

    for row in rows:

        entity_type = _row_get(
            row,
            "entity_type",
            0,
        )

        external_key = _row_get(
            row,
            "external_key",
            1,
        )

        alias_source = _row_get(
            row,
            "source",
            2,
        )

        if (
            entity_type
            not in VALID_ENTITY_TYPES
        ):
            continue

        # ----------------------------------------------------
        # SOLO CONOCIMIENTO CONFIABLE
        # ----------------------------------------------------

        is_trusted = (
            bool(external_key)
            or alias_source
            in trusted_sources
        )

        if not is_trusted:
            continue

        trusted_types.add(
            entity_type
        )

    # --------------------------------------------------------
    # Sin evidencia confiable
    # --------------------------------------------------------

    if not trusted_types:
        return entity

    # --------------------------------------------------------
    # Evidencia contradictoria
    # --------------------------------------------------------

    if len(trusted_types) != 1:
        return entity

    known_type = next(
        iter(trusted_types)
    )

    current_type = entity.get(
        "label"
    )

    if (
        known_type
        == current_type
    ):
        return entity

    corrected = dict(
        entity
    )

    corrected[
        "original_label"
    ] = current_type

    corrected[
        "label"
    ] = known_type

    corrected[
        "type_correction_source"
    ] = "trusted_existing_alias"

    return corrected

# ============================================================
# CORRECCIÓN 2:
# CONTEXTO DEL TEXTO
# ============================================================

def _correct_type_from_context(
    entity,
    text=None,
):
    """
    Correcciones contextuales conservadoras.

    IMPORTANTE:

    Solo corregimos patrones con evidencia razonablemente
    fuerte.

    Si no estamos seguros, se mantiene el tipo de GLiNER.
    """

    if not isinstance(
        entity,
        dict,
    ):

        return entity

    if (
        not isinstance(
            text,
            str,
        )
        or not text.strip()
    ):

        return entity

    if entity.get(
        "canonical_id"
    ):

        return entity

    mention = (
        entity.get(
            "text",
            "",
        )
        .strip()
    )

    current_type = (
        entity.get(
            "label"
        )
    )

    if not mention:

        return entity

    normalized_mention = (
        normalize_alias(
            mention
        )
    )

    normalized_text = (
        normalize_alias(
            text
        )
    )

    root_pos = (
        entity.get(
            "root_pos"
        )
        or ""
    ).upper()

    # ========================================================
    # CASO:
    #
    # Dockweiler: La Fiscalía...
    #
    # GLiNER:
    # Dockweiler -> LOC
    #
    # Características:
    # - una palabra
    # - PROPN
    # - abre un titular
    # - seguida por ":"
    #
    # La interpretación más probable es una persona.
    # ========================================================

    if (
        current_type == "LOC"
        and len(
            normalized_mention.split()
        ) == 1
        and root_pos == "PROPN"
    ):

        pattern = (
            r"^"
            + re.escape(
                normalized_mention
            )
            + r"\s*:"
        )

        if re.search(
            pattern,
            normalized_text,
        ):

            corrected = dict(
                entity
            )

            corrected[
                "original_label"
            ] = current_type

            corrected[
                "label"
            ] = "PER"

            corrected[
                "type_correction_source"
            ] = "headline_person"

            return corrected

    return entity


# ============================================================
# SHOULD RESOLVE
# ============================================================

def should_resolve_entity(
    entity,
    text=None,
):
    """
    Decide si una detección es suficientemente
    específica y confiable para entrar al sistema
    normalizado de NetVora.
    """

    if not isinstance(
        entity,
        dict,
    ):

        return False

    mention = entity.get(
        "text"
    )

    entity_type = entity.get(
        "label"
    )

    canonical_id = entity.get(
        "canonical_id"
    )

    detection_source = entity.get(
        "detection_source",
        "ner",
    )

    # ========================================================
    # VALIDACIÓN
    # ========================================================

    if (
        not isinstance(
            mention,
            str,
        )
        or not mention.strip()
    ):

        return False

    mention = mention.strip()

    # ========================================================
    # CATÁLOGO GANA
    # ========================================================

    if canonical_id:

        return True

    if (
        entity_type
        not in VALID_ENTITY_TYPES
    ):

        return False

    # ========================================================
    # MISC
    # ========================================================

    if entity_type == "MISC":

        return False

    # ========================================================
    # NORMALIZACIÓN
    # ========================================================

    normalized = normalize_alias(
        mention
    )

    if not normalized:

        return False

    normalized_base = (
        _strip_leading_determiners(
            normalized
        )
    )

    if not normalized_base:

        return False

    # ========================================================
    # GLINER CONFIDENCE
    # ========================================================

    if not _passes_gliner_confidence(
        entity
    ):

        return False

    # ========================================================
    # STOPLIST
    # ========================================================

    if (
        normalized
        in ENTITY_STOPLIST

        or normalized
        in GENERIC_ENTITY_PHRASES

        or normalized_base
        in ENTITY_STOPLIST

        or normalized_base
        in GENERIC_ENTITY_PHRASES
    ):

        return False

    # ========================================================
    # LONGITUD
    # ========================================================

    compact = re.sub(
        r"[^a-z0-9]",
        "",
        normalized,
    )

    if len(compact) < 3:

        return False

    if not re.search(
        r"[a-z]",
        normalized,
    ):

        return False

    if (
        len(
            normalized.split()
        )
        > 10
    ):

        return False

    # ========================================================
    # NER / GLINER
    # ========================================================

    if detection_source == "ner":

        # ----------------------------------------------------
        # SIGLAS TÉCNICAS
        # ----------------------------------------------------

        if normalized_base in {
            "ptar",
        }:

            return False

        # ====================================================
        # PERSON
        # ====================================================

        if entity_type == "PER":

            # -----------------------------------------------
            # Organización conocida etiquetada como persona
            # -----------------------------------------------

            if (
                normalized_base
                in _KNOWN_ORG_TYPE_GUARDS
            ):

                return False

            compact_person = re.sub(
                r"[^a-z0-9]",
                "",
                normalized_base,
            )

            for known_org in (
                _KNOWN_ORG_TYPE_GUARDS
            ):

                known_compact = re.sub(
                    r"[^a-z0-9]",
                    "",
                    known_org,
                )

                if (
                    compact_person
                    == known_compact
                ):

                    return False

            # -----------------------------------------------
            # Paz aislado
            # -----------------------------------------------

            if (
                normalized_base
                == "paz"
            ):

                return False

            # -----------------------------------------------
            # Personas genéricas
            # -----------------------------------------------

            if _is_generic_person(
                entity,
                normalized_base,
            ):

                return False

            # -----------------------------------------------
            # Personas coordinadas
            # -----------------------------------------------

            if re.fullmatch(
                (
                    r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ'-]+"
                    r"\s+(?:y|e)\s+"
                    r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ'-]+"
                ),
                mention,
                flags=re.IGNORECASE,
            ):

                return False

            # -----------------------------------------------
            # POS
            # -----------------------------------------------

            words = (
                normalized_base
                .split()
            )

            root_pos = (
                entity.get(
                    "root_pos"
                )
                or ""
            ).upper()

            if (
                len(words) == 1
                and root_pos
                in _NON_PERSON_SINGLE_TOKEN_POS
            ):

                return False

            # -----------------------------------------------
            # Desarrollo Productivo
            #
            # dentro de:
            # ministro de Desarrollo Productivo
            # -----------------------------------------------

            if (
                isinstance(
                    text,
                    str,
                )
                and text
            ):

                normalized_text = (
                    normalize_alias(
                        text
                    )
                )

                if _looks_like_role_portfolio(
                    normalized_base,
                    normalized_text,
                ):

                    return False

        # ====================================================
        # ORGANIZATION
        # ====================================================

        elif entity_type == "ORG":

            # -----------------------------------------------
            # Organizaciones genéricas
            # -----------------------------------------------

            if _is_generic_org(
                normalized_base
            ):

                return False

            # -----------------------------------------------
            # Referencias ambiguas
            # -----------------------------------------------

            if (
                normalized_base
                in _AMBIGUOUS_ORG_REFERENCES
            ):

                return False

            # -----------------------------------------------
            # Alertas
            # -----------------------------------------------

            if re.search(
                r"^alerta\b",
                normalized_base,
            ):

                return False

            # -----------------------------------------------
            # POS
            # -----------------------------------------------

            words = (
                normalized_base
                .split()
            )

            root_pos = (
                entity.get(
                    "root_pos"
                )
                or ""
            ).upper()

            if (
                len(words) == 1
                and root_pos
                in _NON_ORG_SINGLE_TOKEN_POS
            ):

                return False

        # ====================================================
        # LOCATION
        # ====================================================

        elif entity_type == "LOC":

            # -----------------------------------------------
            # Organización conocida etiquetada LOC
            # -----------------------------------------------

            if (
                normalized_base
                in _KNOWN_ORG_TYPE_GUARDS
            ):

                return False

            compact_loc = re.sub(
                r"[^a-z0-9]",
                "",
                normalized_base,
            )

            for known_org in (
                _KNOWN_ORG_TYPE_GUARDS
            ):

                known_compact = re.sub(
                    r"[^a-z0-9]",
                    "",
                    known_org,
                )

                if (
                    compact_loc
                    == known_compact
                ):

                    return False

            # -----------------------------------------------
            # Lugares genéricos
            # -----------------------------------------------

            if _is_generic_location(
                normalized_base
            ):

                return False

            # -----------------------------------------------
            # Eventos
            # -----------------------------------------------

            first_word = (
                normalized_base
                .split()[0]
            )

            if (
                first_word
                in _EVENT_PREFIXES
            ):

                return False

            # -----------------------------------------------
            # POS
            # -----------------------------------------------

            words = (
                normalized_base
                .split()
            )

            root_pos = (
                entity.get(
                    "root_pos"
                )
                or ""
            ).upper()

            if (
                len(words) == 1
                and root_pos
                in _NON_LOC_SINGLE_TOKEN_POS
            ):

                return False

    # ========================================================
    # CONTEXTO GENERAL
    # ========================================================

    if (
        isinstance(
            text,
            str,
        )
        and text
    ):

        normalized_text = (
            normalize_alias(
                text
            )
        )

        if (
            entity_type == "LOC"
            and normalized_base
            in {
                "buenos",
                "buenas",
            }
        ):

            if re.search(
                (
                    r"\bbuenos dias\b"
                    r"|\bbuenas tardes\b"
                    r"|\bbuenas noches\b"
                ),
                normalized_text,
            ):

                return False

    # ========================================================
    # FRASES EDITORIALES
    # ========================================================

    editorial_patterns = (
        r"^a primera hora\b",
        r"^la informacion al instante\b",
        r"^ultima hora\b",
        r"^ultimo momento\b",
        r"^lee la nota\b",
        r"^lea la nota\b",
        r"^mas informacion\b",
        r"^informate\b",
    )

    if any(
        re.search(
            pattern,
            normalized_base,
        )
        for pattern
        in editorial_patterns
    ):

        return False

    return True


# ============================================================
# RESOLVE ENTITY
# ============================================================

def resolve_entity(
    cursor,
    entity,
    text=None,
):
    """
    Resuelve una detección a entities.id.
    """

    if cursor is None:

        return None

    # ========================================================
    # 1. CORRECCIÓN SEGÚN CONOCIMIENTO EXISTENTE
    # ========================================================

    entity = (
        _correct_type_from_existing_alias(
            cursor,
            entity,
        )
    )

    # ========================================================
    # 2. CORRECCIÓN SEGÚN CONTEXTO
    # ========================================================

    entity = (
        _correct_type_from_context(
            entity,
            text=text,
        )
    )

    # ========================================================
    # 3. FILTROS
    # ========================================================

    if not should_resolve_entity(
        entity,
        text=text,
    ):

        return None

    mention = (
        entity["text"]
        .strip()
    )

    entity_type = (
        entity["label"]
    )

    canonical_id = (
        entity.get(
            "canonical_id"
        )
    )

    detection_source = (
        entity.get(
            "detection_source",
            "ner",
        )
    )

    normalized = normalize_alias(
        mention
    )

    # ========================================================
    # 4. CATÁLOGO / RULER
    # ========================================================

    if canonical_id:

        cursor.execute(
            """
            SELECT
                id,
                status,
                merged_into_id

            FROM entities

            WHERE external_key = %s

            LIMIT 1
            """,
            (
                canonical_id,
            ),
        )

        row = cursor.fetchone()

        if row:

            row_id = _row_get(
                row,
                "id",
                0,
            )

            status = _row_get(
                row,
                "status",
                1,
                "active",
            )

            merged_into_id = (
                _row_get(
                    row,
                    "merged_into_id",
                    2,
                )
            )

            if status == "merged":

                if not merged_into_id:

                    return None

                entity_id = (
                    merged_into_id
                )

            elif status != "active":

                return None

            else:

                entity_id = (
                    row_id
                )

            catalog_entry = (
                ENTITY_CATALOG.get(
                    canonical_id
                )
            )

            if (
                catalog_entry
                and status == "active"
            ):

                cursor.execute(
                    """
                    UPDATE entities

                    SET
                        canonical_name = %s,
                        entity_type = %s

                    WHERE id = %s
                    """,
                    (
                        catalog_entry[
                            "name"
                        ],
                        catalog_entry[
                            "type"
                        ],
                        entity_id,
                    ),
                )

            _ensure_alias(
                cursor,
                entity_id,
                mention,
                normalized,
                "ruler",
                1.0,
            )

            return {
                "entity_id": entity_id,
                "resolution_source": (
                    "ruler"
                ),
                "confidence": 1.0,
            }

        # ----------------------------------------------------
        # CATÁLOGO AÚN NO EXISTE
        # ----------------------------------------------------

        catalog_entry = (
            ENTITY_CATALOG.get(
                canonical_id
            )
        )

        canonical_name = (
            catalog_entry["name"]
            if catalog_entry
            else mention
        )

        canonical_type = (
            catalog_entry["type"]
            if catalog_entry
            else entity_type
        )

        # ----------------------------------------------------
        # PROMOVER LEGACY
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                e.id,
                e.external_key

            FROM entity_aliases ea

            INNER JOIN entities e
                ON e.id = ea.entity_id

            WHERE ea.normalized_alias = %s
              AND e.entity_type = %s
              AND e.status = 'active'

            LIMIT 2
            """,
            (
                normalized,
                canonical_type,
            ),
        )

        legacy_rows = (
            cursor.fetchall()
            or []
        )

        if (
            len(
                legacy_rows
            )
            == 1
        ):

            legacy_id = (
                _row_get(
                    legacy_rows[0],
                    "id",
                    0,
                )
            )

            legacy_key = (
                _row_get(
                    legacy_rows[0],
                    "external_key",
                    1,
                    None,
                )
            )

            if (
                legacy_id
                and not legacy_key
            ):

                cursor.execute(
                    """
                    UPDATE entities

                    SET
                        canonical_name = %s,
                        entity_type = %s,
                        external_key = %s

                    WHERE id = %s
                      AND external_key IS NULL
                    """,
                    (
                        canonical_name,
                        canonical_type,
                        canonical_id,
                        legacy_id,
                    ),
                )

                _ensure_alias(
                    cursor,
                    legacy_id,
                    mention,
                    normalized,
                    "ruler",
                    1.0,
                )

                return {
                    "entity_id": (
                        legacy_id
                    ),
                    "resolution_source": (
                        "ruler_promoted"
                    ),
                    "confidence": 1.0,
                }

        # ----------------------------------------------------
        # CREAR ENTIDAD CONOCIDA
        # ----------------------------------------------------

        cursor.execute(
            """
            INSERT INTO entities (
                canonical_name,
                entity_type,
                external_key
            )

            VALUES (%s, %s, %s)

            ON DUPLICATE KEY UPDATE
                id = LAST_INSERT_ID(id)
            """,
            (
                canonical_name,
                canonical_type,
                canonical_id,
            ),
        )

        entity_id = (
            cursor.lastrowid
        )

        if not entity_id:

            cursor.execute(
                """
                SELECT id

                FROM entities

                WHERE external_key = %s

                LIMIT 1
                """,
                (
                    canonical_id,
                ),
            )

            entity_id = (
                _row_get(
                    cursor.fetchone(),
                    "id",
                    0,
                )
            )

        if not entity_id:

            raise RuntimeError(
                (
                    "No se pudo resolver "
                    "external_key %r"
                )
                % canonical_id
            )

        _ensure_alias(
            cursor,
            entity_id,
            mention,
            normalized,
            "ruler",
            1.0,
        )

        return {
            "entity_id": entity_id,
            "resolution_source": "ruler",
            "confidence": 1.0,
        }

    # ========================================================
    # 5. ALIAS EXACTO DEL TIPO FINAL
    # ========================================================

    cursor.execute(
        """
        SELECT
            e.id,
            ea.source AS alias_source,
            ea.confidence AS alias_confidence

        FROM entity_aliases ea

        INNER JOIN entities e
            ON e.id = ea.entity_id

        WHERE ea.normalized_alias = %s
          AND e.entity_type = %s
          AND e.status = 'active'

        LIMIT 2
        """,
        (
            normalized,
            entity_type,
        ),
    )

    rows = (
        cursor.fetchall()
        or []
    )

    if len(rows) == 1:

        row = rows[0]

        alias_source = (
            _row_get(
                row,
                "alias_source",
                1,
                "ner",
            )
        )

        alias_confidence = (
            _row_get(
                row,
                "alias_confidence",
                2,
                None,
            )
        )

        return {
            "entity_id": (
                _row_get(
                    row,
                    "id",
                    0,
                )
            ),

            "resolution_source": (
                "exact_alias"
            ),

            "confidence": (
                _confidence_for_existing_alias(
                    alias_source,
                    alias_confidence,
                )
            ),
        }

    # Alias ambiguo.
    if len(rows) > 1:

        return None

    # ========================================================
    # 6. ENTIDAD NUEVA
    # ========================================================

    cursor.execute(
        """
        INSERT INTO entities (
            canonical_name,
            entity_type
        )

        VALUES (%s, %s)
        """,
        (
            mention,
            entity_type,
        ),
    )

    entity_id = (
        cursor.lastrowid
    )

    if not entity_id:

        raise RuntimeError(
            (
                "INSERT de entidad nueva "
                "no devolvió lastrowid"
            )
        )

    confidence = (
        _confidence_for_source(
            detection_source
        )
    )

    alias_source = (
        detection_source

        if detection_source
        in {
            "ner",
            "ruler_structural",
            "ruler",
        }

        else "ner"
    )

    _ensure_alias(
        cursor,
        entity_id,
        mention,
        normalized,
        alias_source,
        confidence,
    )

    return {
        "entity_id": entity_id,
        "resolution_source": "new",
        "confidence": confidence,
    }


# ============================================================
# ALIAS
# ============================================================

def _ensure_alias(
    cursor,
    entity_id,
    alias,
    normalized_alias,
    source,
    confidence,
):

    if not normalized_alias:

        return

    cursor.execute(
        """
        INSERT IGNORE INTO entity_aliases (
            entity_id,
            alias,
            normalized_alias,
            source,
            confidence
        )

        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            entity_id,
            alias,
            normalized_alias,
            source,
            confidence,
        ),
    )


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "normalize_alias",
    "should_resolve_entity",
    "resolve_entity",
    "_correct_type_from_existing_alias",
    "_correct_type_from_context",
]
entity = {
    "text": "Dockweiler",
    "label": "LOC",
    "detection_source": "ner",
    "root_pos": "PROPN",
}


