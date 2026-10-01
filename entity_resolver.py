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
    if len(rows) > 1:
        return None

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
    
def should_resolve_entity(entity, text=None):
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

    detection_source = entity.get("detection_source", "ner")

    if text is not None and not isinstance(text, str):
        text = None

    # -----------------------------------------------------
    # 3. Normalización
    # -----------------------------------------------------

    normalized = normalize_alias(mention)

    if not normalized:
        return False

    # -----------------------------------------------------
    # 4. Siglas técnicas / infraestructura
    # -----------------------------------------------------
    #
    # spaCy puede confundir ciertas siglas técnicas con
    # ubicaciones u organizaciones.
    #
    # Ejemplo:
    #   PTAR -> LOC
    #
    # PTAR se utiliza en nuestro dataset para referirse a
    # Planta de Tratamiento de Aguas Residuales / proyectos
    # de infraestructura, no a una organización o ubicación.
    #
    # Solo bloqueamos detecciones provenientes del NER.
    # Una entidad explícitamente conocida por EntityRuler
    # ya habría sido aceptada mediante canonical_id.
    # -----------------------------------------------------

    if detection_source == "ner":
        technical_acronyms = {
            "ptar",
        }

        if normalized in technical_acronyms:
            return False

    # -----------------------------------------------------
    # 5. MISC detectado solamente por el NER
    # -----------------------------------------------------
    #
    # MISC es una categoría demasiado abierta en spaCy.
    # No la guardamos automáticamente salvo que haya sido
    # reconocida explícitamente por EntityRuler.
    #
    # Las entidades conocidas con canonical_id ya fueron
    # aceptadas anteriormente.
    #
    # PER / ORG / LOC continúan funcionando normalmente.
    # -----------------------------------------------------

    if entity_type == "MISC":
        return False

    # -----------------------------------------------------
    # 6. Contexto: saludos confundidos con ubicaciones
    # -----------------------------------------------------
    #
    # spaCy puede interpretar:
    #
    #   "Buenos días" -> "Buenos" | LOC
    #
    # No bloqueamos "Buenos" globalmente porque queremos
    # evitar reglas ciegas basadas únicamente en la entidad.
    # Solo se descarta cuando el contexto confirma un saludo.
    # -----------------------------------------------------

    if entity_type == "LOC" and text:

        normalized_text = normalize_alias(text)

        greeting_patterns = [
            r"\bbuenos dias\b",
            r"\bbuenas tardes\b",
            r"\bbuenas noches\b",
        ]

        for pattern in greeting_patterns:
            if re.search(pattern, normalized_text):
                if normalized in {"buenos", "buenas"}:
                    return False

    # -----------------------------------------------------
    # 7. Contexto: alertas confundidas con organizaciones
    # -----------------------------------------------------
    #
    # Ejemplos:
    #
    #   Alerta Naranja Hidrológica
    #   Alerta Roja Meteorológica
    #
    # Son avisos/estados de alerta, no organizaciones.
    #
    # Solo bloqueamos detecciones del NER.
    # Las entidades conocidas del EntityRuler ya fueron
    # aceptadas anteriormente mediante canonical_id.
    # -----------------------------------------------------

    if entity_type == "ORG" and detection_source == "ner":

        if re.search(r"^alerta\b", normalized):
            return False

    # -----------------------------------------------------
    # 8. Ubicaciones coordinadas sospechosas
    # -----------------------------------------------------
    #
    # spaCy ocasionalmente fusiona dos nombres propios:
    #
    #   "Ramos y Arce" -> LOC
    #
    # Una ubicación real puede contener "y", por lo que
    # NO bloqueamos cualquier LOC con conjunción.
    #
    # Solo rechazamos el patrón especialmente sospechoso:
    # dos bloques cortos con apariencia de nombres propios
    # unidos por "y/e".
    # -----------------------------------------------------

    if entity_type in {"PER", "LOC"} and detection_source == "ner":

        coordinated_name = re.fullmatch(
            r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ'-]+\s+(?:y|e)\s+"
            r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ'-]+",
            mention,
            flags=re.IGNORECASE
        )

        if coordinated_name:
            return False

    # -----------------------------------------------------
    # 9. Stoplist exacta
    # -----------------------------------------------------

    if normalized in ENTITY_STOPLIST:
        return False

    # -----------------------------------------------------
    # 10. Frases genéricas
    # -----------------------------------------------------

    if normalized in GENERIC_ENTITY_PHRASES:
        return False

    # -----------------------------------------------------
    # 11. Muy corto
    # -----------------------------------------------------
    #
    # Evita cosas como:
    #
    #   EL
    #   DE
    #   A
    #
    # PERO no bloqueamos siglas conocidas porque las
    # entidades con canonical_id ya pasaron arriba.
    # -----------------------------------------------------

    compact = re.sub(r"[^a-z0-9]", "", normalized)

    if len(compact) < 3:
        return False

    # -----------------------------------------------------
    # 12. Debe contener al menos una letra
    # -----------------------------------------------------

    if not re.search(r"[a-z]", normalized):
        return False

    # -----------------------------------------------------
    # 13. Frases excesivamente largas
    # -----------------------------------------------------
    #
    # Normalmente indican que spaCy capturó parte de una
    # oración o encabezado completo.
    # -----------------------------------------------------

    words = normalized.split()

    if len(words) > 10:
        return False

    # -----------------------------------------------------
    # 14. Basura editorial frecuente
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

    # -----------------------------------------------------
    # 15. Entidad aceptada
    # -----------------------------------------------------

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