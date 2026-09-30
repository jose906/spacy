import re
import unicodedata
from entity_patterns import ENTITY_CATALOG, ENTITY_STOPLIST,GENERIC_ENTITY_PHRASES


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

        # =====================================================
        # YA EXISTE
        # =====================================================

        if row:

            entity_id = row["id"]

            # Obtener nombre canónico desde el catálogo
            catalog_entry = ENTITY_CATALOG.get(canonical_id)

            if catalog_entry:
                cursor.execute(
                    """
                    UPDATE entities
                    SET canonical_name = %s,
                        entity_type = %s
                    WHERE id = %s
                    """,
                    (
                        catalog_entry["name"],
                        catalog_entry["type"],
                        entity_id
                    )
                )

            # Registrar el alias si todavía no existe
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

        # =====================================================
        # NO EXISTE -> CREAR ENTIDAD
        # =====================================================

        catalog_entry = ENTITY_CATALOG.get(canonical_id)

        if catalog_entry:
            canonical_name = catalog_entry["name"]
            canonical_type = catalog_entry["type"]
        else:
            canonical_name = mention
            canonical_type = entity_type

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
                canonical_type,
                canonical_id
            )
        )

        entity_id = cursor.lastrowid

        # Registrar el alias encontrado
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
    
def should_resolve_entity(entity):
    """
    Decide si una entidad detectada por spaCy merece entrar
    al sistema normalizado de entidades.

    IMPORTANTE:
    Esto NO modifica get_entities() ni el sistema legacy.
    Solo protege entities/entity_aliases/tweet_entities.
    """

    if not entity:
        return False

    mention = entity.get("text")
    entity_type = entity.get("label")
    canonical_id = entity.get("canonical_id")

    # -----------------------------------------------------
    # 1. Validaciones básicas
    # -----------------------------------------------------

    if not mention or not isinstance(mention, str):
        return False

    mention = mention.strip()

    if not mention:
        return False

    # -----------------------------------------------------
    # 2. Las entidades conocidas del EntityRuler
    #    tienen prioridad.
    # -----------------------------------------------------

    if canonical_id:
        return True

    # -----------------------------------------------------
    # 3. Normalización
    # -----------------------------------------------------

    normalized = normalize_alias(mention)

    if not normalized:
        return False

    # -----------------------------------------------------
    # 4. Stoplist exacta
    # -----------------------------------------------------

    if normalized in ENTITY_STOPLIST:
        return False

    # -----------------------------------------------------
    # 5. Frases genéricas
    # -----------------------------------------------------

    if normalized in GENERIC_ENTITY_PHRASES:
        return False

    # -----------------------------------------------------
    # 6. Muy corto
    #
    # Evita cosas como:
    # EL
    # DE
    # A
    #
    # PERO no bloqueamos siglas conocidas porque las
    # entidades con canonical_id ya pasaron arriba.
    # -----------------------------------------------------

    compact = re.sub(r"[^a-z0-9]", "", normalized)

    if len(compact) < 3:
        return False

    # -----------------------------------------------------
    # 7. Debe contener al menos una letra
    # -----------------------------------------------------

    if not re.search(r"[a-z]", normalized):
        return False

    # -----------------------------------------------------
    # 8. Frases excesivamente largas
    #
    # Normalmente indican que spaCy capturó parte de una
    # oración o encabezado completo.
    # -----------------------------------------------------

    words = normalized.split()

    if len(words) > 10:
        return False

    # -----------------------------------------------------
    # 9. Basura editorial frecuente
    # -----------------------------------------------------

    editorial_patterns = [
        r"^a primera hora\b",
        r"^la informacion al instante\b",
        r"^ultima hora\b",
        r"^ultimo momento\b",
    ]

    for pattern in editorial_patterns:
        if re.search(pattern, normalized):
            return False

    return True


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