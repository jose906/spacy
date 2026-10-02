# -*- coding: utf-8 -*-
"""Prueba de humo para ejecutar en el mismo entorno real de NetVora."""

from pprint import pprint

from entity_resolver import should_resolve_entity
from spacyscript import debug_entities, get_entities_detailed, preprocess_text


SAMPLES = [
    "Luis Arce se reunió con YPFB en La Paz.",
    "El Gobierno Autónomo Municipal de La Paz anunció nuevas medidas.",
    "Gobierno analiza nuevas medidas económicas.",
    "El presidente de la Cámara Nacional de Industria, Gonzalo Morales, habló con el Gobierno.",
    "El secretario de la Federación de Profesionales en Salud (FESIRMES) habló del conflicto.",
    "El ministro de Desarrollo Productivo, Óscar Mario Justiniano, se reunió con productores.",
    "📸APG El ministro dio una conferencia.",
    "Ataque ruso a Kiev deja heridos a través de @correodelsurcom",
    "Empresarios dicen: ‘Afectaron la economía’.",
    "Marioly Valencia explica cómo interpretar la energía de los animales.",
    "#Visión360 presenta las noticias más leídas de la jornada.",
    "#GrupoFides #ANF #Sucre informó sobre el TSJ y el Órgano Judicial en Potosí.",
]

for text in SAMPLES:
    print("=" * 100)
    print(text)
    pprint(debug_entities(text), sort_dicts=False)

# Regresiones críticas observadas en producción.
gobierno = {
    "text": "Gobierno",
    "label": "LOC",
    "canonical_id": None,
    "detection_source": "ner",
}
assert should_resolve_entity(gobierno) is False

false_verb_person = {
    "text": "Afectaron",
    "label": "PER",
    "canonical_id": None,
    "detection_source": "ner",
    "root_pos": "VERB",
}
assert should_resolve_entity(false_verb_person) is False

portfolio = {
    "text": "Desarrollo Productivo",
    "label": "PER",
    "canonical_id": None,
    "detection_source": "ner",
    "root_pos": "PROPN",
}
assert should_resolve_entity(
    portfolio,
    text="El ministro de Desarrollo Productivo, Óscar Mario Justiniano, informó.",
) is False

assert "correodelsurcom" not in preprocess_text(
    "Ataque ruso a Kiev a través de @correodelsurcom"
)
assert "APG" not in preprocess_text("📸APG El ministro dio una conferencia")

# Entidades observadas que deben quedar canónicas.
detailed = get_entities_detailed("FESIRMES, Visión360, APG y Marioly Valencia")
flat = [entity for values in detailed.values() for entity in values]
ids = {entity.get("canonical_id") for entity in flat}
assert "FESIRMES" in ids
assert "VISION_360" in ids
assert "APG_NOTICIAS" in ids
assert "MARIOLY_VALENCIA" in ids

print("\nSMOKE TEST OK")
