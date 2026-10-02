# -*- coding: utf-8 -*-
"""Prueba rápida para ejecutar en el mismo entorno real de NetVora."""

from pprint import pprint

from entity_resolver import should_resolve_entity
from spacyscript import debug_entities, get_entities_detailed, get_resolvable_entities


SAMPLES = [
    "Luis Arce se reunió con YPFB en La Paz.",
    "El Gobierno Autónomo Municipal de La Paz anunció nuevas medidas.",
    "Gobierno analiza nuevas medidas económicas.",
    "El Ministerio de Gobierno informó sobre el operativo.",
    "La Camara de Diputados tratará el proyecto.",
    "El Tribunal Supremo Electoral publicó el calendario.",
    "#TheStrongest jugará este domingo en La Paz.",
]


for text in SAMPLES:
    print("=" * 100)
    print(text)
    pprint(debug_entities(text), sort_dicts=False)

# Regresión específica que originó el problema.
gobierno = {
    "text": "Gobierno",
    "label": "LOC",
    "canonical_id": None,
    "detection_source": "ner",
}
assert should_resolve_entity(gobierno) is False

# La forma institucional completa sí debe sobrevivir.
municipal = {
    "text": "Gobierno Autónomo Municipal de La Paz",
    "label": "ORG",
    "canonical_id": None,
    "detection_source": "ruler_structural",
}
assert should_resolve_entity(municipal) is True

print("\nSMOKE TEST OK")
