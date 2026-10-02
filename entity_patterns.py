# -*- coding: utf-8 -*-
"""Reglas y catálogo de entidades de NetVora.

Compatible con spaCy 3.x y Python 3.8+.
Las entidades conocidas reciben un ``id`` estable; los patrones
estructurales NO reciben id para evitar fusionar organizaciones distintas.
"""

import unicodedata


VALID_ENTITY_TYPES = {"PER", "ORG", "LOC", "MISC"}

# Términos que nunca deben convertirse por sí solos en entidades normalizadas.
# Se guardan normalizados porque entity_resolver.normalize_alias() trabaja así.
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
    # Falsos positivos observados repetidamente en el dataset de NetVora.
    "gobierno",
    "politica",
}


KNOWN_ENTITIES = {'TIKITA_WARA': {'name': "T'ikita Wara", 'type': 'PER', 'aliases': ["T'ikita Wara", 'T’ikita Wara']},
                  "SENASAG": {
    "name": "Servicio Nacional de Sanidad Agropecuaria e Inocuidad Alimentaria",
    "type": "ORG",
    "aliases": [
        "SENASAG",
        "Senasag",
        "Servicio Nacional de Sanidad Agropecuaria e Inocuidad Alimentaria",
    ],
},"COMITE_PRO_SANTA_CRUZ": {
    "name": "Comité pro Santa Cruz",
    "type": "ORG",
    "aliases": [
        "Comité pro Santa Cruz",
        "Comité Cívico pro Santa Cruz",
        "Comité Cívico Pro Santa Cruz",
    ],
},
"EVO_MORALES": {
    "name": "Evo Morales",
    "type": "PER",
    "aliases": [
        "Evo Morales",
        "Evo",
    ],
},

"RODRIGO_PAZ": {
    "name": "Rodrigo Paz",
    "type": "PER",
    "aliases": [
        "Rodrigo Paz",
    ],
},

"VIRGEN_DE_COTOCA": {
    "name": "Virgen de Cotoca",
    "type": "MISC",
    "aliases": [
        "Virgen de Cotoca",
    ],
},
 'COB': {'name': 'Central Obrera Boliviana', 'type': 'ORG', 'aliases': ['COB', 'Central Obrera Boliviana']},
 'CAO': {'name': 'Cámara Agropecuaria del Oriente',
         'type': 'ORG',
         'aliases': ['CAO', 'Cámara Agropecuaria del Oriente']},
 'FELCC': {'name': 'Fuerza Especial de Lucha Contra el Crimen',
           'type': 'ORG',
           'aliases': ['FELCC', 'Fuerza Especial de Lucha Contra el Crimen']},
 'ATT': {'name': 'Autoridad de Regulación y Fiscalización de Telecomunicaciones y Transportes',
         'type': 'ORG',
         'aliases': ['ATT', 'Autoridad de Regulación y Fiscalización de Telecomunicaciones y Transportes']},
 'ASFI': {'name': 'Autoridad de Supervisión del Sistema Financiero',
          'type': 'ORG',
          'aliases': ['ASFI', 'Autoridad de Supervisión del Sistema Financiero']},
 'UAGRM': {'name': 'Universidad Autónoma Gabriel René Moreno',
           'type': 'ORG',
           'aliases': ['UAGRM', 'Universidad Autónoma Gabriel René Moreno']},
 'TOYOSA': {'name': 'Toyosa', 'type': 'ORG', 'aliases': ['Toyosa']},
 'ORGANO_JUDICIAL_BOLIVIA': {'name': 'Órgano Judicial', 'type': 'ORG', 'aliases': ['Órgano Judicial']},
 'CONFEDERACION_AGROPECUARIA_NACIONAL': {'name': 'Confederación Agropecuaria Nacional',
                                         'type': 'ORG',
                                         'aliases': ['CONFEAGRO', 'Confederación Agropecuaria Nacional']},
 'AGENCIA_NOTICIAS_FIDES': {'name': 'Agencia de Noticias Fides',
                            'type': 'ORG',
                            'aliases': ['ANF', 'Agencia de Noticias Fides']},
 'GRUPO_FIDES': {'name': 'Grupo Fides', 'type': 'ORG', 'aliases': ['GrupoFides', 'Grupo Fides']},
 'CONFEDERACION_EMPRESARIOS_PRIVADOS_BOLIVIA': {'name': 'Confederación de Empresarios Privados de Bolivia',
                                                'type': 'ORG',
                                                'aliases': ['CEPB',
                                                            'Confederación de Empresarios Privados de '
                                                            'Bolivia']},
 'PARTIDO_DEMOCRATA_CRISTIANO': {'name': 'Partido Demócrata Cristiano',
                                 'type': 'ORG',
                                 'aliases': ['PDC', 'Partido Demócrata Cristiano']},
 'YPFB': {'name': 'Yacimientos Petrolíferos Fiscales Bolivianos',
          'type': 'ORG',
          'aliases': ['YPFB', 'Yacimientos Petrolíferos Fiscales Bolivianos']},
 'BANCO_CENTRAL_BOLIVIA': {'name': 'Banco Central de Bolivia',
                           'type': 'ORG',
                           'aliases': ['BCB', 'Banco Central de Bolivia']},
 'ORGANO_ELECTORAL_PLURINACIONAL': {'name': 'Órgano Electoral Plurinacional',
                                    'type': 'ORG',
                                    'aliases': ['OEP', 'Órgano Electoral Plurinacional']},
 'TRIBUNAL_SUPREMO_ELECTORAL': {'name': 'Tribunal Supremo Electoral',
                                'type': 'ORG',
                                'aliases': ['TSE', 'Tribunal Supremo Electoral']},
 'ASAMBLEA_LEGISLATIVA_PLURINACIONAL': {'name': 'Asamblea Legislativa Plurinacional',
                                        'type': 'ORG',
                                        'aliases': ['ALP', 'Asamblea Legislativa Plurinacional']},
 'CAMARA_DIPUTADOS': {'name': 'Cámara de Diputados', 'type': 'ORG', 'aliases': ['Cámara de Diputados']},
 'CAMARA_SENADORES': {'name': 'Cámara de Senadores', 'type': 'ORG', 'aliases': ['Cámara de Senadores']},
 'SENAMHI': {'name': 'Servicio Nacional de Meteorología e Hidrología',
             'type': 'ORG',
             'aliases': ['SENAMHI', 'Senamhi', 'Servicio Nacional de Meteorología e Hidrología']},
 'EMAPA': {'name': 'Empresa de Apoyo a la Producción de Alimentos',
           'type': 'ORG',
           'aliases': ['EMAPA', 'Empresa de Apoyo a la Producción de Alimentos']},
 'ADMINISTRADORA_BOLIVIANA_CARRETERAS': {'name': 'Administradora Boliviana de Carreteras',
                                         'type': 'ORG',
                                         'aliases': ['ABC', 'Administradora Boliviana de Carreteras']},
 'AGENCIA_NACIONAL_HIDROCARBUROS': {'name': 'Agencia Nacional de Hidrocarburos',
                                    'type': 'ORG',
                                    'aliases': ['ANH', 'Agencia Nacional de Hidrocarburos']},
 'INSTITUTO_NACIONAL_ESTADISTICA': {'name': 'Instituto Nacional de Estadística',
                                    'type': 'ORG',
                                    'aliases': ['INE', 'Instituto Nacional de Estadística']},
 'SEGIP': {'name': 'SEGIP', 'type': 'ORG', 'aliases': ['SEGIP']},
 'AGETIC': {'name': 'AGETIC', 'type': 'ORG', 'aliases': ['AGETIC']},
 'ADUANA_NACIONAL': {'name': 'Aduana Nacional', 'type': 'ORG', 'aliases': ['Aduana Nacional']},
 'POLICIA_BOLIVIANA': {'name': 'Policía Boliviana', 'type': 'ORG', 'aliases': ['Policía Boliviana']},
 'FUERZAS_ARMADAS_BOLIVIA': {'name': 'Fuerzas Armadas', 'type': 'ORG', 'aliases': ['Fuerzas Armadas']},
 'TRIBUNAL_CONSTITUCIONAL_PLURINACIONAL': {'name': 'Tribunal Constitucional Plurinacional',
                                           'type': 'ORG',
                                           'aliases': ['TCP', 'Tribunal Constitucional Plurinacional']},
 'TRIBUNAL_SUPREMO_JUSTICIA': {'name': 'Tribunal Supremo de Justicia',
                               'type': 'ORG',
                               'aliases': ['TSJ', 'Tribunal Supremo de Justicia']},
 'FISCALIA_GENERAL_ESTADO': {'name': 'Fiscalía General del Estado',
                             'type': 'ORG',
                             'aliases': ['Fiscalía General del Estado']},
 'CONCEJO_MUNICIPAL': {'name': 'Concejo Municipal', 'type': 'ORG', 'aliases': ['Concejo Municipal']},
 'MINISTERIO_PRESIDENCIA_BOLIVIA': {'name': 'Ministerio de la Presidencia',
                                    'type': 'ORG',
                                    'aliases': ['Ministerio de la Presidencia']},
 'FESIRMES': {'name': 'Federación de Sindicatos de Ramas Médicas de Salud Pública',
              'type': 'ORG',
              'aliases': ['FESIRMES',
                          'Fesirmes',
                          'Federación de Sindicatos de Ramas Médicas de Salud Pública',
                          'Federación de Profesionales en Salud',
                          'Federación Sindical de Ramas Médicas']},
 'VISION_360': {'name': 'Visión 360',
                'type': 'ORG',
                'aliases': ['Visión 360', 'Visión360', 'Vision 360', 'Vision360']},
 'APG_NOTICIAS': {'name': 'Agencia de Noticias APG',
                  'type': 'ORG',
                  'aliases': ['APG',
                              'APG Noticias',
                              'Agencia de Noticias APG',
                              'Agencia de Periodistas Gráficos',
                              'Agencia de Prensa Gráfica']},
 'MARIOLY_VALENCIA': {'name': 'Marioly Valencia', 'type': 'PER', 'aliases': ['Marioly Valencia']}}


def _strip_diacritics(text):
    """Devuelve una variante sin tildes para texto social informal."""
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _alias_variants(alias):
    """Genera variantes seguras de un alias sin inventar abreviaturas."""
    variants = [alias]
    accentless = _strip_diacritics(alias)
    if accentless != alias:
        variants.append(accentless)

    straight = alias.replace("’", "'").replace("‘", "'").replace("`", "'")
    if straight not in variants:
        variants.append(straight)

    return variants


def _normalized_pattern_key(text):
    return " ".join(_strip_diacritics(text).casefold().split())


def _validate_known_entities():
    """Falla temprano si el catálogo tiene tipos o alias ambiguos."""
    aliases = {}
    for external_key, data in KNOWN_ENTITIES.items():
        if data.get("type") not in VALID_ENTITY_TYPES:
            raise ValueError("Tipo inválido para %s: %r" % (external_key, data.get("type")))
        if not data.get("name"):
            raise ValueError("Entidad sin nombre canónico: %s" % external_key)
        if not data.get("aliases"):
            raise ValueError("Entidad sin aliases: %s" % external_key)

        for alias in data["aliases"]:
            for variant in _alias_variants(alias):
                key = _normalized_pattern_key(variant)
                previous = aliases.get(key)
                if previous and previous != external_key:
                    raise ValueError(
                        "Alias ambiguo %r entre %s y %s" % (alias, previous, external_key)
                    )
                aliases[key] = external_key


_validate_known_entities()


ENTITY_CATALOG = {
    external_key: {"name": data["name"], "type": data["type"]}
    for external_key, data in KNOWN_ENTITIES.items()
}


# Frases conocidas: el mismo id une sigla, nombre largo y variantes sin tildes.
# spacyscript.py las convierte a token patterns con LOWER usando nlp.make_doc().
# Así evitamos pasar las frases por todo el pipeline al iniciar EntityRuler.
KNOWN_ENTITY_PATTERNS = []
_seen_known_patterns = set()
for external_key, data in KNOWN_ENTITIES.items():
    for alias in data.get("aliases", []):
        for variant in _alias_variants(alias):
            key = (data["type"], " ".join(variant.casefold().split()), external_key)
            if key in _seen_known_patterns:
                continue
            _seen_known_patterns.add(key)
            KNOWN_ENTITY_PATTERNS.append({
                "label": data["type"],
                "pattern": variant,
                "id": external_key,
            })


# Los cuantificadores están acotados para impedir que una regla estructural
# absorba media oración. spaCy Matcher admite {n,m} en OP.
_NAME_TOKENS = {
    "POS": {"IN": ["PROPN", "NOUN", "ADJ", "ADP", "DET", "CCONJ"]},
    "IS_PUNCT": False,
    "OP": "{1,8}",
}
_PLACE_TOKENS = {
    "POS": {"IN": ["PROPN", "NOUN", "ADJ", "ADP", "DET"]},
    "IS_PUNCT": False,
    "OP": "{1,6}",
}

STRUCTURAL_PATTERNS = [
    {
        "label": "ORG",
        "pattern": [
            {"LOWER": "ministerio"},
            {"LOWER": "de"},
            dict(_NAME_TOKENS),
        ],
    },
    {
        "label": "ORG",
        "pattern": [
            {"LOWER": "viceministerio"},
            {"LOWER": "de"},
            dict(_NAME_TOKENS),
        ],
    },
    {
        "label": "ORG",
        "pattern": [
            {"LOWER": "universidad"},
            dict(_NAME_TOKENS),
        ],
    },
    {
        "label": "ORG",
        "pattern": [
            {"LOWER": "gobierno"},
            {"LOWER": {"IN": ["autónomo", "autonomo"]}},
            {"LOWER": "municipal"},
            {"LOWER": "de"},
            dict(_PLACE_TOKENS),
        ],
    },
    {
        "label": "ORG",
        "pattern": [
            {"LOWER": "gobierno"},
            {"LOWER": {"IN": ["autónomo", "autonomo"]}},
            {"LOWER": "departamental"},
            {"LOWER": "de"},
            dict(_PLACE_TOKENS),
        ],
    },
    {
        "label": "ORG",
        "pattern": [
            {"LOWER": "asamblea"},
            {"LOWER": "legislativa"},
            {"LOWER": "departamental"},
            {"LOWER": "de"},
            dict(_PLACE_TOKENS),
        ],
    },
    {
        "label": "ORG",
        "pattern": [
            {"LOWER": "tribunal"},
            {"LOWER": "electoral"},
            {"LOWER": "departamental"},
            {"LOWER": "de"},
            dict(_PLACE_TOKENS),
        ],
    },
    {
        "label": "ORG",
        "pattern": [
            {"LOWER": {"IN": ["federación", "federacion"]}},
            dict(_NAME_TOKENS),
        ],
    },
    {
        "label": "ORG",
        "pattern": [
            {"LOWER": {"IN": ["confederación", "confederacion"]}},
            dict(_NAME_TOKENS),
        ],
    },
    {
        "label": "ORG",
        "pattern": [
            {"LOWER": {"IN": ["cámara", "camara"]}},
            dict(_NAME_TOKENS),
        ],
    },
    {
        "label": "ORG",
        "pattern": [
            {"LOWER": "instituto"},
            {"LOWER": "nacional"},
            dict(_NAME_TOKENS),
        ],
    },
]


# Compatibilidad con código anterior. Para el EntityRuler de NetVora se usa
# KNOWN_ENTITY_PATTERNS por separado para que el catálogo exacto tenga prioridad.
ENTITY_PATTERNS = STRUCTURAL_PATTERNS + KNOWN_ENTITY_PATTERNS

__all__ = [
    "ENTITY_STOPLIST",
    "GENERIC_ENTITY_PHRASES",
    "KNOWN_ENTITIES",
    "ENTITY_CATALOG",
    "KNOWN_ENTITY_PATTERNS",
    "STRUCTURAL_PATTERNS",
    "ENTITY_PATTERNS",
]
