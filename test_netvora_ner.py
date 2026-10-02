# -*- coding: utf-8 -*-
import os
import unittest

os.environ.setdefault("NETVORA_ALLOW_BLANK_SPACY", "1")

from entity_patterns import ENTITY_CATALOG, KNOWN_ENTITY_PATTERNS, STRUCTURAL_PATTERNS
from entity_resolver import normalize_alias, resolve_entity, should_resolve_entity
import spacyscript as ner


class FakeCursor(object):
    def __init__(self):
        self.calls = []
        self.lastrowid = 0
        self._one = None
        self._all = []

    def execute(self, sql, params=()):
        compact = " ".join(sql.split())
        self.calls.append((compact, params))
        if "FROM entities WHERE external_key" in compact and compact.startswith("SELECT"):
            self._one = None
        elif "INSERT INTO entities" in compact and "external_key" in compact:
            self.lastrowid = 42
        elif "FROM entity_aliases" in compact:
            self._all = []
        elif compact.startswith("INSERT INTO entities"):
            self.lastrowid = 99

    def fetchone(self):
        return self._one

    def fetchall(self):
        return self._all


class NetVoraNerTests(unittest.TestCase):
    def test_preprocess(self):
        clean = ner.preprocess_text(
            "RT @BoliviaVerifica: Lea más: https://ejemplo.com #LuisArce | www.foo.bo"
        )
        self.assertIn("Bolivia Verifica", clean)
        self.assertIn("Luis Arce", clean)
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
        self.assertTrue(any("ON DUPLICATE KEY UPDATE" in sql for sql, _ in cursor.calls))

    def test_normalize_alias(self):
        self.assertEqual(normalize_alias(" GÓBIERNO "), "gobierno")
        self.assertEqual(normalize_alias("T’ikita Wara"), "t'ikita wara")

    def test_known_patterns_all_match(self):
        for pattern in KNOWN_ENTITY_PATTERNS:
            doc = ner.nlp(pattern["pattern"])
            self.assertTrue(
                any(
                    ent.ent_id_ == pattern["id"] and ent.label_ == pattern["label"]
                    for ent in doc.ents
                ),
                pattern,
            )

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

    def test_catalog_and_pattern_counts(self):
        self.assertEqual(len(ENTITY_CATALOG), 36)
        self.assertGreaterEqual(len(KNOWN_ENTITY_PATTERNS), 36)
        self.assertEqual(len(STRUCTURAL_PATTERNS), 11)


if __name__ == "__main__":
    unittest.main(verbosity=2)
