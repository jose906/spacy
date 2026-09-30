import re
import unicodedata


def normalize_alias(text):
    """
    Normalización utilizada EXCLUSIVAMENTE para comparar alias.

    No modifica el texto original almacenado.
    """

    if not text:
        return ""

    text = unicodedata.normalize("NFKD", text)

    # quitar acentos
    text = "".join(
        c for c in text
        if not unicodedata.combining(c)
    )

    text = text.casefold()

    # espacios
    text = re.sub(r"\s+", " ", text)

    # puntuación en bordes
    text = text.strip(" ,.;:!?\"'()[]{}")

    return text.strip()


def resolve_entity(cursor, entity):
    """
    Resuelve una entidad detectada por spaCy.

    Retorna:

    {
        "entity_id": ...,
        "resolution_source": ...,
        "confidence": ...
    }
    """

    mention = entity["text"]
    entity_type = entity["label"]
    canonical_id = entity.get("canonical_id")

    normalized = normalize_alias(mention)

    # =========================================================
    # 1. ENTITY RULER
    # =========================================================

    if canonical_id:

        cursor.execute(
            """
            SELECT id
            FROM entities
            WHERE external_key = %s
              AND status = 'active'
            LIMIT 1
            """,
            (canonical_id,)
        )

        row = cursor.fetchone()

        if row:

            entity_id = row["id"]

            _ensure_alias(
                cursor,
                entity_id,
                mention,
                normalized,
                "ruler",
                1.0
            )

            return {
                "entity_id": entity_id,
                "resolution_source": "ruler",
                "confidence": 1.0
            }

        # -----------------------------------------------------
        # Primera vez que vemos esta entidad del EntityRuler
        # -----------------------------------------------------

        canonical_name = mention

        cursor.execute(
            """
            INSERT INTO entities (
                canonical_name,
                entity_type,
                external_key
            )
            VALUES (%s, %s, %s)
            """,
            (
                canonical_name,
                entity_type,
                canonical_id
            )
        )

        entity_id = cursor.lastrowid

        _ensure_alias(
            cursor,
            entity_id,
            mention,
            normalized,
            "ruler",
            1.0
        )

        return {
            "entity_id": entity_id,
            "resolution_source": "ruler",
            "confidence": 1.0
        }

    # =========================================================
    # 2. ALIAS EXACTO
    # =========================================================

    cursor.execute(
        """
        SELECT
            e.id
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
            entity_type
        )
    )

    rows = cursor.fetchall()

    # Una sola coincidencia -> seguro.
    if len(rows) == 1:

        return {
            "entity_id": rows[0]["id"],
            "resolution_source": "exact_alias",
            "confidence": 1.0
        }

    # =========================================================
    # 3. ENTIDAD NUEVA
    # =========================================================

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
            entity_type
        )
    )

    entity_id = cursor.lastrowid

    _ensure_alias(
        cursor,
        entity_id,
        mention,
        normalized,
        "ner",
        1.0
    )

    return {
        "entity_id": entity_id,
        "resolution_source": "new",
        "confidence": 1.0
    }


def _ensure_alias(
    cursor,
    entity_id,
    alias,
    normalized_alias,
    source,
    confidence
):

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
            confidence
        )
    )