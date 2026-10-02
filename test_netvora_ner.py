# -*- coding: utf-8 -*-
import os
import unittest

os.environ.setdefault("NETVORA_ALLOW_BLANK_SPACY", "1")

from entity_patterns import ENTITY_CATALOG, KNOWN_ENTITY_PATTERNS, STRUCTURAL_PATTERNS
from entity_resolver import normalize_alias, resolve_entity, should_resolve_entity
import spacyscript as ner


class FakeCursor(object):
    def __init__(self, alias_rows=None):
        self.calls = []
        self.lastrowid = 0
        self._one = None
        self._all = []
        self.alias_rows = alias_rows or []

    def execute(self, sql, params=()):
        compact = " ".join(sql.split())
        self.calls.append((compact, params))

        if "FROM entities WHERE external_key" in compact and compact.startswith("SELECT"):
            self._one = None
        elif compact.startswith("SELECT id, status, merged_into_id FROM entities"):
            self._one = None
        elif "INSERT INTO entities" in compact and "external_key" in compact:
            self.lastrowid = 42
        elif "FROM entity_aliases" in compact:
            self._all = list(self.alias_rows)
        elif compact.startswith("INSERT INTO entities"):
            self.lastrowid = 99

    def fetchone(self):
        return self._one

    def fetchall(self):
        return self._all


class NetVoraNerTests(unittest.TestCase):
    def test_preprocess_removes_mentions_urls_and_photo_credit(self):
        clean = ner.preprocess_text(
            "RT @BoliviaVerifica: Lea más: https://ejemplo.com "
            "#LuisArce | 📸APG www.foo.bo"
        )
        self.assertNotIn("BoliviaVerifica", clean)
        self.assertNotIn("Bolivia Verifica", clean)
        self.assertIn("Luis Arce", clean)
        self.assertNotIn("APG", clean)
        self.assertNotIn("http", clean)
        self.assertNotIn("www.", clean)

    def test_generic_false_positive_is_blocked(self):
        entity = {
            "text": "Gobierno",
            "label": "LOC",
            "canonical_id": None,
            "detection_source": "ner",
        }
        self.assertFalse(should_resolve_entity(entity))
        cursor = FakeCursor()
        self.assertIsNone(resolve_entity(cursor, entity))
        self.assertEqual(cursor.calls, [])

    def test_false_single_word_person_verb_is_blocked(self):
        entity = {
            "text": "Afectaron",
            "label": "PER",
            "canonical_id": None,
            "detection_source": "ner",
            "root_pos": "VERB",
        }
        self.assertFalse(should_resolve_entity(entity))

    def test_single_word_person_propn_survives(self):
        entity = {
            "text": "Evo",
            "label": "PER",
            "canonical_id": None,
            "detection_source": "ner",
            "root_pos": "PROPN",
        }
        self.assertTrue(should_resolve_entity(entity))

    def test_role_portfolio_false_person_is_blocked(self):
        entity = {
            "text": "Desarrollo Productivo",
            "label": "PER",
            "canonical_id": None,
            "detection_source": "ner",
            "root_pos": "PROPN",
        }
        text = "El ministro de Desarrollo Productivo, Óscar Mario Justiniano, informó."
        self.assertFalse(should_resolve_entity(entity, text=text))

    def test_known_entity_is_idempotent_path(self):
        cursor = FakeCursor()
        entity = {
            "text": "YPFB",
            "label": "ORG",
            "canonical_id": "YPFB",
            "detection_source": "ruler",
        }
        result = resolve_entity(cursor, entity)
        self.assertEqual(result["entity_id"], 42)
        self.assertEqual(result["resolution_source"], "ruler")
        self.assertEqual(result["confidence"], 1.0)
        self.assertTrue(any("ON DUPLICATE KEY UPDATE" in sql for sql, _ in cursor.calls))


    def test_known_entity_promotes_legacy_exact_alias(self):
        cursor = FakeCursor(alias_rows=[{
            "id": 443,
            "external_key": None,
        }])
        entity = {
            "text": "Federación de Profesionales en Salud",
            "label": "ORG",
            "canonical_id": "FESIRMES",
            "detection_source": "ruler",
        }
        result = resolve_entity(cursor, entity)
        self.assertEqual(result["entity_id"], 443)
        self.assertEqual(result["resolution_source"], "ruler_promoted")
        self.assertEqual(result["confidence"], 1.0)
        self.assertTrue(
            any(
                "SET canonical_name = %s, entity_type = %s, external_key = %s" in sql
                for sql, _ in cursor.calls
            )
        )

    def test_ner_new_entity_confidence_is_not_one(self):
        cursor = FakeCursor()
        entity = {
            "text": "Persona Correcta",
            "label": "PER",
            "canonical_id": None,
            "detection_source": "ner",
            "root_pos": "PROPN",
        }
        result = resolve_entity(cursor, entity)
        self.assertEqual(result["entity_id"], 99)
        self.assertEqual(result["confidence"], 0.80)
        self.assertTrue(any(params[-2:] == ("ner", 0.80) for _, params in cursor.calls if params))

    def test_structural_new_entity_confidence(self):
        cursor = FakeCursor()
        entity = {
            "text": "Cámara Nacional de Industria",
            "label": "ORG",
            "canonical_id": None,
            "detection_source": "ruler_structural",
        }
        result = resolve_entity(cursor, entity)
        self.assertEqual(result["confidence"], 0.95)
        self.assertTrue(
            any(params[-2:] == ("ruler_structural", 0.95) for _, params in cursor.calls if params)
        )

    def test_exact_alias_keeps_ner_confidence_cap(self):
        cursor = FakeCursor(alias_rows=[{
            "id": 7,
            "alias_source": "ner",
            "alias_confidence": 1.0,  # legado: antes se guardaba 1.0
        }])
        entity = {
            "text": "Nombre Correcto",
            "label": "PER",
            "canonical_id": None,
            "detection_source": "ner",
            "root_pos": "PROPN",
        }
        result = resolve_entity(cursor, entity)
        self.assertEqual(result["entity_id"], 7)
        self.assertEqual(result["resolution_source"], "exact_alias")
        self.assertEqual(result["confidence"], 0.80)

    def test_normalize_alias(self):
        self.assertEqual(normalize_alias(" GÓBIERNO "), "gobierno")
        self.assertEqual(normalize_alias("T’ikita Wara"), "t'ikita wara")

    def test_known_patterns_all_match(self):
        # El catálogo se convierte en token patterns dentro de spacyscript.
        for pattern in KNOWN_ENTITY_PATTERNS:
            doc = ner.nlp(pattern["pattern"])
            self.assertTrue(
                any(
                    ent.ent_id_ == pattern["id"] and ent.label_ == pattern["label"]
                    for ent in doc.ents
                ),
                pattern,
            )

    def test_known_ruler_uses_token_patterns_not_phrase_matcher(self):
        ruler = ner.nlp.get_pipe("netvora_known_ruler")
        self.assertEqual(len(ruler.phrase_patterns), 0)
        self.assertGreater(len(ruler.token_patterns), 0)

    def test_structural_government(self):
        doc = ner.nlp.make_doc("Gobierno Autónomo Municipal de La Paz")
        poses = ["NOUN", "ADJ", "ADJ", "ADP", "DET", "PROPN"]
        for token, pos in zip(doc, poses):
            token.pos = ner.nlp.vocab.strings[pos]
        doc = ner.nlp.get_pipe("netvora_structural_ruler")(doc)
        doc = ner.nlp.get_pipe("netvora_known_ruler")(doc)
        self.assertEqual(
            [(ent.text, ent.label_) for ent in doc.ents],
            [("Gobierno Autónomo Municipal de La Paz", "ORG")],
        )

    def test_observed_entities_are_canonicalized(self):
        cases = {
            "FESIRMES": ("ORG", "FESIRMES"),
            "Visión360": ("ORG", "VISION_360"),
            "APG": ("ORG", "APG_NOTICIAS"),
            "Marioly Valencia": ("PER", "MARIOLY_VALENCIA"),
        }
        for text, expected in cases.items():
            doc = ner.nlp(text)
            found = [(ent.label_, ent.ent_id_) for ent in doc.ents]
            self.assertIn(expected, found, (text, found))

    def test_catalog_and_pattern_counts(self):
        self.assertEqual(len(ENTITY_CATALOG), 40)
        self.assertGreaterEqual(len(KNOWN_ENTITY_PATTERNS), 40)
        self.assertEqual(len(STRUCTURAL_PATTERNS), 11)


if __name__ == "__main__":
    unittest.main(verbosity=2)
