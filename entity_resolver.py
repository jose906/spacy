# -*- coding: utf-8 -*-
"""Resolución y filtros de entidades para NetVora.

Este módulo protege las tablas normalizadas ``entities``, ``entity_aliases``
y ``tweet_entities`` sin cambiar la salida legacy de ``get_entities()``.
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
        # No se aplica a LOC porque existen ubicaciones reales con "y/e".
        if entity_type == "PER" and re.fullmatch(
            r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ'-]+\s+(?:y|e)\s+"
            r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ'-]+",
            mention,
            flags=re.IGNORECASE,
        ):
            return False

    if isinstance(text, str) and text:
        normalized_text = normalize_alias(text)
        if entity_type == "LOC" and normalized in {"buenos", "buenas"}:
            if re.search(r"\bbuenos dias\b|\bbuenas tardes\b|\bbuenas noches\b", normalized_text):
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

    Es retrocompatible con ``resolve_entity(cursor, entity)``; el argumento
    opcional ``text`` mejora los filtros contextuales.

    Retorna ``None`` cuando la detección no debe persistirse o cuando existe
    ambigüedad, o un dict con ``entity_id``, ``resolution_source`` y
    ``confidence``.
    """
    if cursor is None or not should_resolve_entity(entity, text=text):
        return None

    mention = entity["text"].strip()
    entity_type = entity["label"]
    canonical_id = entity.get("canonical_id")
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

        # external_key debe ser UNIQUE. LAST_INSERT_ID(id) hace el alta idempotente
        # si dos workers intentan crear la misma entidad conocida a la vez.
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

    # 2) Alias exacto, pero solo dentro del mismo tipo para no fusionar
    # homónimos como persona/lugar/organización.
    cursor.execute(
        """
        SELECT e.id
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
        return {
            "entity_id": _row_get(rows[0], "id", 0),
            "resolution_source": "exact_alias",
            "confidence": 1.0,
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

    _ensure_alias(cursor, entity_id, mention, normalized, "ner", 1.0)
    return {
        "entity_id": entity_id,
        "resolution_source": "new",
        "confidence": 1.0,
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
