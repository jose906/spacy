# ============================================================
# ENTITY PATTERNS - NETVORA
# ============================================================
# Reglas complementarias para es_core_news_lg.
#
# Objetivos:
# 1. Corregir errores conocidos del NER.
# 2. Reconocer instituciones bolivianas frecuentes.
# 3. Reconocer familias institucionales mediante estructura.
# 4. Unificar alias mediante ent_id.
#
# IMPORTANTE:
# No pretendemos reemplazar spaCy.
# Estas reglas complementan el modelo estadístico.
# ============================================================


# ============================================================
# FILTROS DE CALIDAD
# ============================================================

ENTITY_STOPLIST = {
    "el", "la", "los", "las",
    "un", "una", "unos", "unas",
    "este", "esta", "esto",
    "ese", "esa", "aquel", "aquella",
    "buenos dias", "buenas tardes", "buenas noches",
}

GENERIC_ENTITY_PHRASES = {
    "el jefe de estado",
    "jefe de estado",
    "la informacion",
    "informacion",
}


# ============================================================
# ENTIDADES CONOCIDAS
# ============================================================
# Cada entidad se define UNA SOLA VEZ.
#
# key     -> external_key / canonical_id estable
# name    -> nombre canónico para mostrar y guardar
# type    -> PER / ORG / LOC / MISC
# aliases -> formas que EntityRuler debe reconocer
# ============================================================

KNOWN_ENTITIES = {
    # --------------------------------------------------------
    # EMPRESAS / ORGANIZACIONES DETECTADAS EN DATOS REALES
    # --------------------------------------------------------
    "TOYOSA": {
        "name": "Toyosa",
        "type": "ORG",
        "aliases": ["Toyosa"],
    },
    "ORGANO_JUDICIAL_BOLIVIA": {
        "name": "Órgano Judicial",
        "type": "ORG",
        "aliases": ["Órgano Judicial"],
    },
    "CONFEDERACION_AGROPECUARIA_NACIONAL": {
        "name": "Confederación Agropecuaria Nacional",
        "type": "ORG",
        "aliases": [
            "CONFEAGRO",
            "Confederación Agropecuaria Nacional",
        ],
    },

    # --------------------------------------------------------
    # MEDIOS
    # --------------------------------------------------------
    "AGENCIA_NOTICIAS_FIDES": {
        "name": "Agencia de Noticias Fides",
        "type": "ORG",
        "aliases": [
            "ANF",
            "Agencia de Noticias Fides",
        ],
    },
    "GRUPO_FIDES": {
        "name": "Grupo Fides",
        "type": "ORG",
        "aliases": [
            "GrupoFides",
            "Grupo Fides",
        ],
    },

    # --------------------------------------------------------
    # ORGANIZACIONES EMPRESARIALES
    # --------------------------------------------------------
    "CONFEDERACION_EMPRESARIOS_PRIVADOS_BOLIVIA": {
        "name": "Confederación de Empresarios Privados de Bolivia",
        "type": "ORG",
        "aliases": [
            "CEPB",
            "Confederación de Empresarios Privados de Bolivia",
        ],
    },

    # --------------------------------------------------------
    # PARTIDOS
    # --------------------------------------------------------
    "PARTIDO_DEMOCRATA_CRISTIANO": {
        "name": "Partido Demócrata Cristiano",
        "type": "ORG",
        "aliases": [
            "PDC",
            "Partido Demócrata Cristiano",
        ],
    },

    # --------------------------------------------------------
    # EMPRESAS / ENTIDADES ESTATALES
    # --------------------------------------------------------
    "YPFB": {
        "name": "Yacimientos Petrolíferos Fiscales Bolivianos",
        "type": "ORG",
        "aliases": [
            "YPFB",
            "Yacimientos Petrolíferos Fiscales Bolivianos",
        ],
    },
    "BANCO_CENTRAL_BOLIVIA": {
        "name": "Banco Central de Bolivia",
        "type": "ORG",
        "aliases": [
            "BCB",
            "Banco Central de Bolivia",
        ],
    },

    # --------------------------------------------------------
    # ÓRGANO ELECTORAL
    # --------------------------------------------------------
    "ORGANO_ELECTORAL_PLURINACIONAL": {
        "name": "Órgano Electoral Plurinacional",
        "type": "ORG",
        "aliases": [
            "OEP",
            "Órgano Electoral Plurinacional",
        ],
    },
    "TRIBUNAL_SUPREMO_ELECTORAL": {
        "name": "Tribunal Supremo Electoral",
        "type": "ORG",
        "aliases": [
            "TSE",
            "Tribunal Supremo Electoral",
        ],
    },

    # --------------------------------------------------------
    # PODER LEGISLATIVO
    # --------------------------------------------------------
    "ASAMBLEA_LEGISLATIVA_PLURINACIONAL": {
        "name": "Asamblea Legislativa Plurinacional",
        "type": "ORG",
        "aliases": [
            "ALP",
            "Asamblea Legislativa Plurinacional",
        ],
    },
    "CAMARA_DIPUTADOS": {
        "name": "Cámara de Diputados",
        "type": "ORG",
        "aliases": ["Cámara de Diputados"],
    },
    "CAMARA_SENADORES": {
        "name": "Cámara de Senadores",
        "type": "ORG",
        "aliases": ["Cámara de Senadores"],
    },

    # --------------------------------------------------------
    # OTRAS ENTIDADES PÚBLICAS
    # --------------------------------------------------------
    "ADMINISTRADORA_BOLIVIANA_CARRETERAS": {
        "name": "Administradora Boliviana de Carreteras",
        "type": "ORG",
        "aliases": [
            "ABC",
            "Administradora Boliviana de Carreteras",
        ],
    },
    "AGENCIA_NACIONAL_HIDROCARBUROS": {
        "name": "Agencia Nacional de Hidrocarburos",
        "type": "ORG",
        "aliases": [
            "ANH",
            "Agencia Nacional de Hidrocarburos",
        ],
    },
    "INSTITUTO_NACIONAL_ESTADISTICA": {
        "name": "Instituto Nacional de Estadística",
        "type": "ORG",
        "aliases": [
            "INE",
            "Instituto Nacional de Estadística",
        ],
    },
    "SEGIP": {
        "name": "SEGIP",
        "type": "ORG",
        "aliases": ["SEGIP"],
    },
    "AGETIC": {
        "name": "AGETIC",
        "type": "ORG",
        "aliases": ["AGETIC"],
    },
    "ADUANA_NACIONAL": {
        "name": "Aduana Nacional",
        "type": "ORG",
        "aliases": ["Aduana Nacional"],
    },
    "POLICIA_BOLIVIANA": {
        "name": "Policía Boliviana",
        "type": "ORG",
        "aliases": ["Policía Boliviana"],
    },
    "FUERZAS_ARMADAS_BOLIVIA": {
        "name": "Fuerzas Armadas",
        "type": "ORG",
        "aliases": ["Fuerzas Armadas"],
    },

    # --------------------------------------------------------
    # JUSTICIA
    # --------------------------------------------------------
    "TRIBUNAL_CONSTITUCIONAL_PLURINACIONAL": {
        "name": "Tribunal Constitucional Plurinacional",
        "type": "ORG",
        "aliases": [
            "TCP",
            "Tribunal Constitucional Plurinacional",
        ],
    },
    "TRIBUNAL_SUPREMO_JUSTICIA": {
        "name": "Tribunal Supremo de Justicia",
        "type": "ORG",
        "aliases": [
            "TSJ",
            "Tribunal Supremo de Justicia",
        ],
    },
    "FISCALIA_GENERAL_ESTADO": {
        "name": "Fiscalía General del Estado",
        "type": "ORG",
        "aliases": ["Fiscalía General del Estado"],
    },

    # --------------------------------------------------------
    # CONCEJOS
    # --------------------------------------------------------
    "CONCEJO_MUNICIPAL": {
        "name": "Concejo Municipal",
        "type": "ORG",
        "aliases": ["Concejo Municipal"],
    },
}


# ============================================================
# CATÁLOGO CANÓNICO
# ============================================================
# Mantiene compatibilidad con entity_resolver.py:
#
# from entity_patterns import ENTITY_CATALOG
# ============================================================

ENTITY_CATALOG = {
    external_key: {
        "name": data["name"],
        "type": data["type"],
    }
    for external_key, data in KNOWN_ENTITIES.items()
}


# ============================================================
# PATTERNS DE ENTIDADES CONOCIDAS
# ============================================================
# Se generan automáticamente desde KNOWN_ENTITIES.
# Cada alias recibe el mismo external_key mediante "id".
# ============================================================

KNOWN_ENTITY_PATTERNS = []

for external_key, data in KNOWN_ENTITIES.items():
    for alias in data.get("aliases", []):
        KNOWN_ENTITY_PATTERNS.append({
            "label": data["type"],
            "pattern": alias,
            "id": external_key,
        })


# ============================================================
# PATRONES ESTRUCTURALES
# ============================================================
# Estos NO reciben "id".
#
# No representan una organización concreta del catálogo.
# Solamente indican que una estructura lingüística suele
# representar una organización.
#
# IMPORTANTE:
# Nunca poner un id genérico como MINISTERIO o UNIVERSIDAD,
# porque eso fusionaría organizaciones diferentes.
# ============================================================

STRUCTURAL_PATTERNS = [
    # --------------------------------------------------------
    # MINISTERIOS
    # --------------------------------------------------------
    {
        "label": "ORG",
        "pattern": [
            {"LOWER": "ministerio"},
            {"LOWER": "de"},
            {
                "POS": {
                    "IN": ["NOUN", "PROPN", "ADJ", "ADP", "CCONJ"]
                },
                "OP": "+",
            },
        ],
    },

    # --------------------------------------------------------
    # VICEMINISTERIOS
    # --------------------------------------------------------
    {
        "label": "ORG",
        "pattern": [
            {"LOWER": "viceministerio"},
            {"LOWER": "de"},
            {
                "POS": {
                    "IN": ["NOUN", "PROPN", "ADJ", "ADP", "CCONJ"]
                },
                "OP": "+",
            },
        ],
    },

    # --------------------------------------------------------
    # UNIVERSIDADES
    # --------------------------------------------------------
    {
        "label": "ORG",
        "pattern": [
            {"LOWER": "universidad"},
            {
                "POS": {
                    "IN": ["PROPN", "ADJ", "NOUN", "ADP", "DET", "CCONJ"]
                },
                "OP": "+",
            },
        ],
    },

    # --------------------------------------------------------
    # GOBIERNOS AUTÓNOMOS MUNICIPALES
    # --------------------------------------------------------
    {
        "label": "ORG",
        "pattern": [
            {"LOWER": "gobierno"},
            {"LOWER": "autónomo"},
            {"LOWER": "municipal"},
            {"LOWER": "de"},
            {
                "POS": {
                    "IN": ["PROPN", "ADP", "DET"]
                },
                "OP": "+",
            },
        ],
    },

    # --------------------------------------------------------
    # GOBIERNOS AUTÓNOMOS DEPARTAMENTALES
    # --------------------------------------------------------
    {
        "label": "ORG",
        "pattern": [
            {"LOWER": "gobierno"},
            {"LOWER": "autónomo"},
            {"LOWER": "departamental"},
            {"LOWER": "de"},
            {
                "POS": {
                    "IN": ["PROPN", "ADP", "DET"]
                },
                "OP": "+",
            },
        ],
    },

    # --------------------------------------------------------
    # ASAMBLEAS LEGISLATIVAS DEPARTAMENTALES
    # --------------------------------------------------------
    {
        "label": "ORG",
        "pattern": [
            {"LOWER": "asamblea"},
            {"LOWER": "legislativa"},
            {"LOWER": "departamental"},
            {"LOWER": "de"},
            {
                "POS": {
                    "IN": ["PROPN", "ADP", "DET"]
                },
                "OP": "+",
            },
        ],
    },

    # --------------------------------------------------------
    # TRIBUNALES ELECTORALES DEPARTAMENTALES
    # --------------------------------------------------------
    {
        "label": "ORG",
        "pattern": [
            {"LOWER": "tribunal"},
            {"LOWER": "electoral"},
            {"LOWER": "departamental"},
            {"LOWER": "de"},
            {
                "POS": {
                    "IN": ["PROPN", "ADP", "DET"]
                },
                "OP": "+",
            },
        ],
    },

    # --------------------------------------------------------
    # FEDERACIONES
    # --------------------------------------------------------
    {
        "label": "ORG",
        "pattern": [
            {"LOWER": "federación"},
            {
                "POS": {
                    "IN": ["PROPN", "NOUN", "ADJ", "ADP", "DET", "CCONJ"]
                },
                "OP": "+",
            },
        ],
    },

    # --------------------------------------------------------
    # CONFEDERACIONES
    # --------------------------------------------------------
    {
        "label": "ORG",
        "pattern": [
            {"LOWER": "confederación"},
            {
                "POS": {
                    "IN": ["PROPN", "NOUN", "ADJ", "ADP", "DET", "CCONJ"]
                },
                "OP": "+",
            },
        ],
    },

    # --------------------------------------------------------
    # CÁMARAS EMPRESARIALES / INSTITUCIONALES
    # --------------------------------------------------------
    {
        "label": "ORG",
        "pattern": [
            {"LOWER": "cámara"},
            {
                "POS": {
                    "IN": ["PROPN", "NOUN", "ADJ", "ADP", "DET", "CCONJ"]
                },
                "OP": "+",
            },
        ],
    },

    # --------------------------------------------------------
    # INSTITUTOS NACIONALES
    # --------------------------------------------------------
    {
        "label": "ORG",
        "pattern": [
            {"LOWER": "instituto"},
            {"LOWER": "nacional"},
            {
                "POS": {
                    "IN": ["PROPN", "NOUN", "ADJ", "ADP", "DET", "CCONJ"]
                },
                "OP": "+",
            },
        ],
    },
]


# ============================================================
# EXPORT FINAL PARA SPACY
# ============================================================
# spacyscript.py puede seguir usando exactamente:
#
# from entity_patterns import ENTITY_PATTERNS
#
# ruler.add_patterns(ENTITY_PATTERNS)
# ============================================================

ENTITY_PATTERNS = KNOWN_ENTITY_PATTERNS + STRUCTURAL_PATTERNS

