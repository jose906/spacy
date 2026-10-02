# -*- coding: utf-8 -*-
"""Resolución y filtros de entidades para NetVora.

Protege las tablas normalizadas ``entities``, ``entity_aliases`` y
``tweet_entities`` sin cambiar la salida legacy de ``get_entities()``.
Compatible con Python 3.8+.
"""

import re
import unicodedata

from entity_patterns import (
    ENTITY_CATALOG,
    ENTITY_STOPLIST,
    GENERIC_ENTITY_PHRASES,
)


VALID_ENTITY_TYPES = {"PER", "ORG", "LOC", "MISC"}

# POS que jamás deben crear por sí solos una persona de una palabra cuando la
# detección proviene únicamente del NER estadístico.
_NON_PERSON_SINGLE_TOKEN_POS = {
    "VERB", "AUX", "ADJ", "ADV", "DET", "PRON", "ADP", "CCONJ",
    "SCONJ", "NUM", "PUNCT", "SYM", "INTJ",
}

_ROLE_PORTFOLIO_PREFIXES = (
    "ministro", "ministra", "viceministro", "viceministra",
    "secretario", "secretaria", "director", "directora",
    "titular", "responsable",
)


def normalize_alias(text):
    """Normaliza SOLO para comparación de alias; no altera lo almacenado."""
    if not isinstance(text, str) or not text.strip():
        return ""

    text = unicodedata.normalize("NFKC", text)
    text = (
        text.replace("’", "'")
        .replace("‘", "'")
        .replace("`", "'")
        .replace("–", "-")
        .replace("—", "-")
    )

    decomposed = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    text = text.casefold()
    text = re.sub(r"\s+", " ", text)
    text = text.strip(" \t\r\n,.;:!?\"'()[]{}<>«»")
    return text.strip()


def _row_get(row, key, index=0, default=None):
    """Soporta cursores MySQL que devuelven dict o tuple."""
    if row is None:
        return default
    if isinstance(row, dict):
        return row.get(key, default)
    try:
        return row[index]
    except (IndexError, TypeError):
        return default


def _safe_float(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _confidence_for_source(source):
    """Confianza semántica del origen, no probabilidad del modelo spaCy."""
    if source in {"ruler", "manual", "catalog"}:
        return 1.0
    if source == "ruler_structural":
        return 0.95
    if source == "ner":
        return 0.80
    return 0.75


def _confidence_for_existing_alias(alias_source, stored_confidence):
    """No convierte un alias NER antiguo en 1.0 solo por repetirse."""
    base = _confidence_for_source(alias_source)
    stored = _safe_float(stored_confidence, base)

    if alias_source in {"ruler", "manual", "catalog"}:
        return 1.0
    if alias_source == "ruler_structural":
        return min(max(stored, 0.0), 0.95)
    if alias_source == "ner":
        return min(max(stored, 0.0), 0.80)
    return min(max(stored, 0.0), 1.0)


def _looks_like_role_portfolio(normalized_mention, normalized_text):
    """Detecta falsos PER como 'Desarrollo Productivo' en 'ministro de ...'."""
    if not normalized_mention or not normalized_text:
        return False

    role_group = "(?:%s)" % "|".join(map(re.escape, _ROLE_PORTFOLIO_PREFIXES))
    connector = r"(?:de|del|de la|de los|de las)"
    pattern = (
        r"\b" + role_group + r"\s+" + connector + r"\s+" +
        re.escape(normalized_mention) + r"\b"
    )
    return re.search(pattern, normalized_text) is not None


def should_resolve_entity(entity, text=None):
    """Decide si una detección merece entrar al sistema normalizado."""
    if not isinstance(entity, dict):
        return False

    mention = entity.get("text")
    entity_type = entity.get("label")
    canonical_id = entity.get("canonical_id")
    detection_source = entity.get("detection_source", "ner")

    if not isinstance(mention, str) or not mention.strip():
        return False
    mention = mention.strip()

    # Una entidad conocida por catálogo es explícita y tiene prioridad.
    if canonical_id:
        return True

    if entity_type not in VALID_ENTITY_TYPES:
        return False

    # MISC del modelo es demasiado abierto para crear entidades automáticamente.
    if entity_type == "MISC":
        return False

    normalized = normalize_alias(mention)
    if not normalized:
        return False
    if (
    detection_source == "ner"
    and entity_type == "PER"
    and normalized == "paz"
    and canonical_id is None
):
        return False

    # Stoplists exactas. Aquí queda resuelto el falso positivo "Gobierno".
    if normalized in ENTITY_STOPLIST or normalized in GENERIC_ENTITY_PHRASES:
        return False

    compact = re.sub(r"[^a-z0-9]", "", normalized)
    if len(compact) < 3 or not re.search(r"[a-z]", normalized):
        return False

    if len(normalized.split()) > 10:
        return False

    if detection_source == "ner":
        # Siglas técnicas que el modelo puede etiquetar como entidad.
        if normalized in {"ptar"}:
            return False

        # Alertas/estados, no organizaciones.
        if entity_type == "ORG" and re.search(r"^alerta\b", normalized):
            return False

        # Nombres de eventos etiquetados erróneamente como ubicación.
        if entity_type == "LOC":
            first_word = normalized.split()[0]
            if first_word in {"festival", "feria", "congreso", "encuentro"}:
                return False

        # Dos personas coordinadas no deben convertirse en una sola persona.
        if entity_type == "PER" and re.fullmatch(
            r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ'-]+\s+(?:y|e)\s+"
            r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ'-]+",
            mention,
            flags=re.IGNORECASE,
        ):
            return False

        if entity_type == "PER":
            words = normalized.split()
            root_pos = (entity.get("root_pos") or "").upper()

            # Evita Afectaron -> PER, Señala -> PER, etc. sin bloquear Evo,
            # Morales u otros nombres de una palabra marcados como PROPN.
            if len(words) == 1 and root_pos in _NON_PERSON_SINGLE_TOKEN_POS:
                return False

            # Evita 'Desarrollo Productivo' -> PER cuando forma parte de una
            # cartera/cargo: 'ministro de Desarrollo Productivo'.
            if isinstance(text, str) and text:
                normalized_text = normalize_alias(text)
                if _looks_like_role_portfolio(normalized, normalized_text):
                    return False

    if isinstance(text, str) and text:
        normalized_text = normalize_alias(text)
        if entity_type == "LOC" and normalized in {"buenos", "buenas"}:
            if re.search(
                r"\bbuenos dias\b|\bbuenas tardes\b|\bbuenas noches\b",
                normalized_text,
            ):
                return False

    editorial_patterns = (
        r"^a primera hora\b",
        r"^la informacion al instante\b",
        r"^ultima hora\b",
        r"^ultimo momento\b",
    )
    if any(re.search(pattern, normalized) for pattern in editorial_patterns):
        return False

    return True


def resolve_entity(cursor, entity, text=None):
    """Resuelve una detección a ``entities.id``.

    Retorna ``None`` cuando la detección no debe persistirse o cuando existe
    ambigüedad, o un dict con ``entity_id``, ``resolution_source`` y
    ``confidence``.
    """
    if cursor is None or not should_resolve_entity(entity, text=text):
        return None

    mention = entity["text"].strip()
    entity_type = entity["label"]
    canonical_id = entity.get("canonical_id")
    detection_source = entity.get("detection_source", "ner")
    normalized = normalize_alias(mention)

    # 1) Entidades explícitas del EntityRuler / catálogo.
    if canonical_id:
        cursor.execute(
            """
            SELECT id, status, merged_into_id
            FROM entities
            WHERE external_key = %s
            LIMIT 1
            """,
            (canonical_id,),
        )
        row = cursor.fetchone()

        if row:
            row_id = _row_get(row, "id", 0)
            status = _row_get(row, "status", 1, "active")
            merged_into_id = _row_get(row, "merged_into_id", 2)

            if status == "merged":
                if not merged_into_id:
                    return None
                entity_id = merged_into_id
            elif status != "active":
                # Respeta una decisión humana de review/inactividad.
                return None
            else:
                entity_id = row_id

            catalog_entry = ENTITY_CATALOG.get(canonical_id)
            if catalog_entry and status == "active":
                cursor.execute(
                    """
                    UPDATE entities
                    SET canonical_name = %s,
                        entity_type = %s
                    WHERE id = %s
                    """,
                    (catalog_entry["name"], catalog_entry["type"], entity_id),
                )

            _ensure_alias(cursor, entity_id, mention, normalized, "ruler", 1.0)
            return {
                "entity_id": entity_id,
                "resolution_source": "ruler",
                "confidence": 1.0,
            }

        catalog_entry = ENTITY_CATALOG.get(canonical_id)
        canonical_name = catalog_entry["name"] if catalog_entry else mention
        canonical_type = catalog_entry["type"] if catalog_entry else entity_type

        # Antes de crear otra fila, intentamos PROMOVER una entidad legacy que
        # ya tenga exactamente este alias y tipo pero todavía no external_key.
        # Esto evita duplicados al incorporar al catálogo una entidad que antes
        # fue descubierta por NER/ruler_structural (ej. FESIRMES).
        cursor.execute(
            """
            SELECT e.id, e.external_key
            FROM entity_aliases ea
            INNER JOIN entities e ON e.id = ea.entity_id
            WHERE ea.normalized_alias = %s
              AND e.entity_type = %s
              AND e.status = 'active'
            LIMIT 2
            """,
            (normalized, canonical_type),
        )
        legacy_rows = cursor.fetchall() or []

        if len(legacy_rows) == 1:
            legacy_id = _row_get(legacy_rows[0], "id", 0)
            legacy_key = _row_get(legacy_rows[0], "external_key", 1, None)
            if legacy_id and not legacy_key:
                cursor.execute(
                    """
                    UPDATE entities
                    SET canonical_name = %s,
                        entity_type = %s,
                        external_key = %s
                    WHERE id = %s
                      AND external_key IS NULL
                    """,
                    (canonical_name, canonical_type, canonical_id, legacy_id),
                )
                _ensure_alias(cursor, legacy_id, mention, normalized, "ruler", 1.0)
                return {
                    "entity_id": legacy_id,
                    "resolution_source": "ruler_promoted",
                    "confidence": 1.0,
                }

        # external_key debe ser UNIQUE. LAST_INSERT_ID(id) hace el alta
        # idempotente si dos workers crean la misma entidad conocida a la vez.
        cursor.execute(
            """
            INSERT INTO entities (canonical_name, entity_type, external_key)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
                id = LAST_INSERT_ID(id)
            """,
            (canonical_name, canonical_type, canonical_id),
        )
        entity_id = cursor.lastrowid

        if not entity_id:
            cursor.execute(
                "SELECT id FROM entities WHERE external_key = %s LIMIT 1",
                (canonical_id,),
            )
            entity_id = _row_get(cursor.fetchone(), "id", 0)

        if not entity_id:
            raise RuntimeError("No se pudo resolver external_key %r" % canonical_id)

        _ensure_alias(cursor, entity_id, mention, normalized, "ruler", 1.0)
        return {
            "entity_id": entity_id,
            "resolution_source": "ruler",
            "confidence": 1.0,
        }

    # 2) Alias exacto dentro del mismo tipo para no fusionar homónimos entre
    # persona/lugar/organización. Conservamos el origen/confianza del alias.
    cursor.execute(
        """
        SELECT
            e.id,
            ea.source AS alias_source,
            ea.confidence AS alias_confidence
        FROM entity_aliases ea
        INNER JOIN entities e ON e.id = ea.entity_id
        WHERE ea.normalized_alias = %s
          AND e.entity_type = %s
          AND e.status = 'active'
        LIMIT 2
        """,
        (normalized, entity_type),
    )
    rows = cursor.fetchall() or []

    if len(rows) == 1:
        row = rows[0]
        alias_source = _row_get(row, "alias_source", 1, "ner")
        alias_confidence = _row_get(row, "alias_confidence", 2, None)
        return {
            "entity_id": _row_get(row, "id", 0),
            "resolution_source": "exact_alias",
            "confidence": _confidence_for_existing_alias(
                alias_source,
                alias_confidence,
            ),
        }
    if len(rows) > 1:
        return None

    # 3) Entidad nueva. Solo llega aquí si pasó todos los filtros anteriores.
    cursor.execute(
        """
        INSERT INTO entities (canonical_name, entity_type)
        VALUES (%s, %s)
        """,
        (mention, entity_type),
    )
    entity_id = cursor.lastrowid
    if not entity_id:
        raise RuntimeError("INSERT de entidad nueva no devolvió lastrowid")

    confidence = _confidence_for_source(detection_source)
    alias_source = (
        detection_source
        if detection_source in {"ner", "ruler_structural", "ruler"}
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


def _ensure_alias(cursor, entity_id, alias, normalized_alias, source, confidence):
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
        (entity_id, alias, normalized_alias, source, confidence),
    )


__all__ = ["normalize_alias", "should_resolve_entity", "resolve_entity"]
