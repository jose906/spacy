# ============================================================
# ENTITY PATTERNS - NETVORA
# ============================================================
#
# Reglas complementarias para es_core_news_lg.
#
# Objetivos:
#
# 1. Corregir errores conocidos del NER.
# 2. Reconocer instituciones bolivianas frecuentes.
# 3. Reconocer familias institucionales mediante estructura.
# 4. Unificar alias mediante ent_id.
#
# IMPORTANTE:
# No pretendemos reemplazar spaCy.
# Estas reglas complementan el modelo estadístico.
#
# ============================================================


ENTITY_CATALOG = {

    # ========================================================
    # MEDIOS
    # ========================================================

    "AGENCIA_NOTICIAS_FIDES": {
        "name": "Agencia de Noticias Fides",
        "type": "ORG"
    },

    "GRUPO_FIDES": {
        "name": "Grupo Fides",
        "type": "ORG"
    },

    # ========================================================
    # ORGANIZACIONES EMPRESARIALES
    # ========================================================

    "CONFEDERACION_EMPRESARIOS_PRIVADOS_BOLIVIA": {
        "name": "Confederación de Empresarios Privados de Bolivia",
        "type": "ORG"
    },

    # ========================================================
    # PARTIDOS
    # ========================================================

    "PARTIDO_DEMOCRATA_CRISTIANO": {
        "name": "Partido Demócrata Cristiano",
        "type": "ORG"
    },

    # ========================================================
    # EMPRESAS / ENTIDADES ESTATALES
    # ========================================================

    "YPFB": {
        "name": "Yacimientos Petrolíferos Fiscales Bolivianos",
        "type": "ORG"
    },

    "BANCO_CENTRAL_BOLIVIA": {
        "name": "Banco Central de Bolivia",
        "type": "ORG"
    },

    # ========================================================
    # ÓRGANO ELECTORAL
    # ========================================================

    "ORGANO_ELECTORAL_PLURINACIONAL": {
        "name": "Órgano Electoral Plurinacional",
        "type": "ORG"
    },

    "TRIBUNAL_SUPREMO_ELECTORAL": {
        "name": "Tribunal Supremo Electoral",
        "type": "ORG"
    },

    # ========================================================
    # PODER LEGISLATIVO
    # ========================================================

    "ASAMBLEA_LEGISLATIVA_PLURINACIONAL": {
        "name": "Asamblea Legislativa Plurinacional",
        "type": "ORG"
    },

    "CAMARA_DIPUTADOS": {
        "name": "Cámara de Diputados",
        "type": "ORG"
    },

    "CAMARA_SENADORES": {
        "name": "Cámara de Senadores",
        "type": "ORG"
    },

    # ========================================================
    # OTRAS ENTIDADES PÚBLICAS
    # ========================================================

    "ADMINISTRADORA_BOLIVIANA_CARRETERAS": {
        "name": "Administradora Boliviana de Carreteras",
        "type": "ORG"
    },

    "AGENCIA_NACIONAL_HIDROCARBUROS": {
        "name": "Agencia Nacional de Hidrocarburos",
        "type": "ORG"
    },

    "INSTITUTO_NACIONAL_ESTADISTICA": {
        "name": "Instituto Nacional de Estadística",
        "type": "ORG"
    },

    "SEGIP": {
        "name": "SEGIP",
        "type": "ORG"
    },

    "AGETIC": {
        "name": "AGETIC",
        "type": "ORG"
    },

    "ADUANA_NACIONAL": {
        "name": "Aduana Nacional",
        "type": "ORG"
    },

    "POLICIA_BOLIVIANA": {
        "name": "Policía Boliviana",
        "type": "ORG"
    },

    "FUERZAS_ARMADAS_BOLIVIA": {
        "name": "Fuerzas Armadas",
        "type": "ORG"
    },

    # ========================================================
    # JUSTICIA
    # ========================================================

    "TRIBUNAL_CONSTITUCIONAL_PLURINACIONAL": {
        "name": "Tribunal Constitucional Plurinacional",
        "type": "ORG"
    },

    "TRIBUNAL_SUPREMO_JUSTICIA": {
        "name": "Tribunal Supremo de Justicia",
        "type": "ORG"
    },

    "FISCALIA_GENERAL_ESTADO": {
        "name": "Fiscalía General del Estado",
        "type": "ORG"
    },

    # ========================================================
    # CONCEJOS
    # ========================================================

    "CONCEJO_MUNICIPAL": {
        "name": "Concejo Municipal",
        "type": "ORG"
    }
}
ENTITY_PATTERNS = [

    # ========================================================
    # MEDIOS / ORGANIZACIONES CONOCIDAS
    # ========================================================

    {
        "label": "ORG",
        "pattern": "ANF",
        "id": "AGENCIA_NOTICIAS_FIDES"
    },

    {
        "label": "ORG",
        "pattern": "Agencia de Noticias Fides",
        "id": "AGENCIA_NOTICIAS_FIDES"
    },

    {
        "label": "ORG",
        "pattern": "GrupoFides",
        "id": "GRUPO_FIDES"
    },

    {
        "label": "ORG",
        "pattern": "Grupo Fides",
        "id": "GRUPO_FIDES"
    },


    # ========================================================
    # ORGANIZACIONES EMPRESARIALES
    # ========================================================

    {
        "label": "ORG",
        "pattern": "CEPB",
        "id": "CONFEDERACION_EMPRESARIOS_PRIVADOS_BOLIVIA"
    },

    {
        "label": "ORG",
        "pattern": "Confederación de Empresarios Privados de Bolivia",
        "id": "CONFEDERACION_EMPRESARIOS_PRIVADOS_BOLIVIA"
    },


    # ========================================================
    # PARTIDOS
    # ========================================================

    {
        "label": "ORG",
        "pattern": "PDC",
        "id": "PARTIDO_DEMOCRATA_CRISTIANO"
    },

    {
        "label": "ORG",
        "pattern": "Partido Demócrata Cristiano",
        "id": "PARTIDO_DEMOCRATA_CRISTIANO"
    },


    # ========================================================
    # EMPRESAS / ENTIDADES ESTATALES
    # ========================================================

    # YPFB

    {
        "label": "ORG",
        "pattern": "YPFB",
        "id": "YPFB"
    },

    {
        "label": "ORG",
        "pattern": "Yacimientos Petrolíferos Fiscales Bolivianos",
        "id": "YPFB"
    },


    # ========================================================
    # BANCO CENTRAL
    # ========================================================

    {
        "label": "ORG",
        "pattern": "BCB",
        "id": "BANCO_CENTRAL_BOLIVIA"
    },

    {
        "label": "ORG",
        "pattern": "Banco Central de Bolivia",
        "id": "BANCO_CENTRAL_BOLIVIA"
    },


    # ========================================================
    # ÓRGANO ELECTORAL
    # ========================================================

    {
        "label": "ORG",
        "pattern": "OEP",
        "id": "ORGANO_ELECTORAL_PLURINACIONAL"
    },

    {
        "label": "ORG",
        "pattern": "Órgano Electoral Plurinacional",
        "id": "ORGANO_ELECTORAL_PLURINACIONAL"
    },

    {
        "label": "ORG",
        "pattern": "TSE",
        "id": "TRIBUNAL_SUPREMO_ELECTORAL"
    },

    {
        "label": "ORG",
        "pattern": "Tribunal Supremo Electoral",
        "id": "TRIBUNAL_SUPREMO_ELECTORAL"
    },


    # ========================================================
    # PODER LEGISLATIVO
    # ========================================================

    {
        "label": "ORG",
        "pattern": "ALP",
        "id": "ASAMBLEA_LEGISLATIVA_PLURINACIONAL"
    },

    {
        "label": "ORG",
        "pattern": "Asamblea Legislativa Plurinacional",
        "id": "ASAMBLEA_LEGISLATIVA_PLURINACIONAL"
    },

    {
        "label": "ORG",
        "pattern": "Cámara de Diputados",
        "id": "CAMARA_DIPUTADOS"
    },

    {
        "label": "ORG",
        "pattern": "Cámara de Senadores",
        "id": "CAMARA_SENADORES"
    },


    # ========================================================
    # OTRAS ENTIDADES PÚBLICAS MUY FRECUENTES
    # ========================================================

    {
        "label": "ORG",
        "pattern": "ABC",
        "id": "ADMINISTRADORA_BOLIVIANA_CARRETERAS"
    },

    {
        "label": "ORG",
        "pattern": "Administradora Boliviana de Carreteras",
        "id": "ADMINISTRADORA_BOLIVIANA_CARRETERAS"
    },

    {
        "label": "ORG",
        "pattern": "ANH",
        "id": "AGENCIA_NACIONAL_HIDROCARBUROS"
    },

    {
        "label": "ORG",
        "pattern": "Agencia Nacional de Hidrocarburos",
        "id": "AGENCIA_NACIONAL_HIDROCARBUROS"
    },

    {
        "label": "ORG",
        "pattern": "INE",
        "id": "INSTITUTO_NACIONAL_ESTADISTICA"
    },

    {
        "label": "ORG",
        "pattern": "Instituto Nacional de Estadística",
        "id": "INSTITUTO_NACIONAL_ESTADISTICA"
    },

    {
        "label": "ORG",
        "pattern": "SEGIP",
        "id": "SEGIP"
    },

    {
        "label": "ORG",
        "pattern": "AGETIC",
        "id": "AGETIC"
    },

    {
        "label": "ORG",
        "pattern": "Aduana Nacional",
        "id": "ADUANA_NACIONAL"
    },

    {
        "label": "ORG",
        "pattern": "Policía Boliviana",
        "id": "POLICIA_BOLIVIANA"
    },

    {
        "label": "ORG",
        "pattern": "Fuerzas Armadas",
        "id": "FUERZAS_ARMADAS_BOLIVIA"
    },


    # ========================================================
    # JUSTICIA
    # ========================================================

    {
        "label": "ORG",
        "pattern": "TCP",
        "id": "TRIBUNAL_CONSTITUCIONAL_PLURINACIONAL"
    },

    {
        "label": "ORG",
        "pattern": "Tribunal Constitucional Plurinacional",
        "id": "TRIBUNAL_CONSTITUCIONAL_PLURINACIONAL"
    },

    {
        "label": "ORG",
        "pattern": "TSJ",
        "id": "TRIBUNAL_SUPREMO_JUSTICIA"
    },

    {
        "label": "ORG",
        "pattern": "Tribunal Supremo de Justicia",
        "id": "TRIBUNAL_SUPREMO_JUSTICIA"
    },

    {
        "label": "ORG",
        "pattern": "Fiscalía General del Estado",
        "id": "FISCALIA_GENERAL_ESTADO"
    },


    # ========================================================
    # CONCEJOS
    # ========================================================

    {
        "label": "ORG",
        "pattern": "Concejo Municipal",
        "id": "CONCEJO_MUNICIPAL"
    },


    # ========================================================
    # PATRONES ESTRUCTURALES
    # ========================================================
    #
    # A partir de aquí no estamos diciendo:
    #
    # "esta organización concreta existe en nuestro catálogo"
    #
    # sino:
    #
    # "esta estructura lingüística suele representar ORG".
    #
    # ========================================================


    # ========================================================
    # MINISTERIOS
    # ========================================================

    {
        "label": "ORG",
        "pattern": [
            {"LOWER": "ministerio"},
            {"LOWER": "de"},
            {
                "POS": {
                    "IN": [
                        "NOUN",
                        "PROPN",
                        "ADJ",
                        "ADP",
                        "CCONJ"
                    ]
                },
                "OP": "+"
            }
        ]
    },


    # ========================================================
    # VICEMINISTERIOS
    # ========================================================

    {
        "label": "ORG",
        "pattern": [
            {"LOWER": "viceministerio"},
            {"LOWER": "de"},
            {
                "POS": {
                    "IN": [
                        "NOUN",
                        "PROPN",
                        "ADJ",
                        "ADP",
                        "CCONJ"
                    ]
                },
                "OP": "+"
            }
        ]
    },


    # ========================================================
    # UNIVERSIDADES
    # ========================================================

    {
        "label": "ORG",
        "pattern": [
            {"LOWER": "universidad"},
            {
                "POS": {
                    "IN": [
                        "PROPN",
                        "ADJ",
                        "NOUN",
                        "ADP",
                        "DET",
                        "CCONJ"
                    ]
                },
                "OP": "+"
            }
        ]
    },


    # ========================================================
    # GOBIERNOS AUTÓNOMOS MUNICIPALES
    # ========================================================

    {
        "label": "ORG",
        "pattern": [
            {"LOWER": "gobierno"},
            {"LOWER": "autónomo"},
            {"LOWER": "municipal"},
            {"LOWER": "de"},
            {
                "POS": {
                    "IN": [
                        "PROPN",
                        "ADP",
                        "DET"
                    ]
                },
                "OP": "+"
            }
        ]
    },


    # ========================================================
    # GOBIERNOS AUTÓNOMOS DEPARTAMENTALES
    # ========================================================

    {
        "label": "ORG",
        "pattern": [
            {"LOWER": "gobierno"},
            {"LOWER": "autónomo"},
            {"LOWER": "departamental"},
            {"LOWER": "de"},
            {
                "POS": {
                    "IN": [
                        "PROPN",
                        "ADP",
                        "DET"
                    ]
                },
                "OP": "+"
            }
        ]
    },


    # ========================================================
    # ASAMBLEAS LEGISLATIVAS DEPARTAMENTALES
    # ========================================================

    {
        "label": "ORG",
        "pattern": [
            {"LOWER": "asamblea"},
            {"LOWER": "legislativa"},
            {"LOWER": "departamental"},
            {"LOWER": "de"},
            {
                "POS": {
                    "IN": [
                        "PROPN",
                        "ADP",
                        "DET"
                    ]
                },
                "OP": "+"
            }
        ]
    },


    # ========================================================
    # TRIBUNALES ELECTORALES DEPARTAMENTALES
    # ========================================================

    {
        "label": "ORG",
        "pattern": [
            {"LOWER": "tribunal"},
            {"LOWER": "electoral"},
            {"LOWER": "departamental"},
            {"LOWER": "de"},
            {
                "POS": {
                    "IN": [
                        "PROPN",
                        "ADP",
                        "DET"
                    ]
                },
                "OP": "+"
            }
        ]
    },


    # ========================================================
    # FEDERACIONES
    # ========================================================
    #
    # Conservador: exigimos que empiece por Federación y
    # dejamos que spaCy determine componentes nominales.
    #
    # ========================================================

    {
        "label": "ORG",
        "pattern": [
            {"LOWER": "federación"},
            {
                "POS": {
                    "IN": [
                        "PROPN",
                        "NOUN",
                        "ADJ",
                        "ADP",
                        "DET",
                        "CCONJ"
                    ]
                },
                "OP": "+"
            }
        ]
    },


    # ========================================================
    # CONFEDERACIONES
    # ========================================================

    {
        "label": "ORG",
        "pattern": [
            {"LOWER": "confederación"},
            {
                "POS": {
                    "IN": [
                        "PROPN",
                        "NOUN",
                        "ADJ",
                        "ADP",
                        "DET",
                        "CCONJ"
                    ]
                },
                "OP": "+"
            }
        ]
    },


    # ========================================================
    # CÁMARAS EMPRESARIALES / INSTITUCIONALES
    # ========================================================

    {
        "label": "ORG",
        "pattern": [
            {"LOWER": "cámara"},
            {
                "POS": {
                    "IN": [
                        "PROPN",
                        "NOUN",
                        "ADJ",
                        "ADP",
                        "DET",
                        "CCONJ"
                    ]
                },
                "OP": "+"
            }
        ]
    },


    # ========================================================
    # INSTITUTOS NACIONALES
    # ========================================================

    {
        "label": "ORG",
        "pattern": [
            {"LOWER": "instituto"},
            {"LOWER": "nacional"},
            {
                "POS": {
                    "IN": [
                        "PROPN",
                        "NOUN",
                        "ADJ",
                        "ADP",
                        "DET",
                        "CCONJ"
                    ]
                },
                "OP": "+"
            }
        ]
    },

]