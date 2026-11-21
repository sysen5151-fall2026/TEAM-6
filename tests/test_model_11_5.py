"""Structure checks on the Innoslate export 11.5 (11.4 plus the criteria, alternatives and decision of Chapter 11
and the risks of Chapter 12).

These check the file, not Innoslate: the export has not been imported yet, so Innoslate's own Intelligence report is
still needed. Run:  python -m unittest discover -s tests -t .
"""

import os
import unittest
import xml.etree.ElementTree as ET

from tests.test_model_10_9 import Model

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "docs", "model")
OLD = os.path.join(MODEL_DIR, "EcoCommute_11.4_C10_simulation.xml")
NEW = os.path.join(MODEL_DIR, "EcoCommute_11.5_C11-C12_analysis_risk.xml")

CRITERIA = {f"EC.{i}" for i in range(1, 7)}
ALTERNATIVES = {f"AL.{c}" for c in "ABCDE"}
NEW_RISKS = {f"TR.{i}" for i in range(16, 23)}
ADDED = CRITERIA | ALTERNATIVES | {"DEC.1"} | NEW_RISKS


class TestModel115(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old, cls.new = Model(OLD), Model(NEW)
        root = ET.parse(NEW).getroot()
        cls.prop = {p.get("id"): p.findtext("name") for c in root.find("schema") if c.tag == "schemaClass" for p in c.findall("schemaProperty")}

    def added(self):
        return {gid: e for gid, e in self.new.by_gid.items() if gid not in self.old.by_gid}

    def attr(self, entity, name):
        for a in entity:
            if a.tag.endswith("Attribute") and self.prop.get(a.get("schemaPropertyId")) == name:
                child = a.find("doubleValue") if a.find("doubleValue") is not None else a.find("value")
                return child.text
        raise AssertionError(f"{name} not found")

    def test_nothing_was_removed_and_no_name_number_or_description_changed(self):
        for gid, entity in self.old.by_gid.items():
            self.assertIn(gid, self.new.by_gid)
            for tag in ("name", "number", "description", "schemaClassId"):
                self.assertEqual(entity.findtext(tag), self.new.by_gid[gid].findtext(tag), (gid, tag))
        self.assertLessEqual(set(self.old.relationships), set(self.new.relationships))

    def test_exactly_the_planned_entities_were_added(self):
        numbers = {(e.findtext("number") or "").strip() for e in self.added().values()}
        self.assertEqual(numbers, ADDED)

    def test_ids_and_global_ids_are_unique_and_every_relationship_points_at_an_entity(self):
        ids = [e.get("id") for e in self.new.entities]
        gids = [e.findtext("globalId") for e in self.new.entities]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(gids), len(set(gids)))
        for s, name, t in self.new.relationships:
            self.assertIn(s, self.new.by_gid)
            self.assertIn(t, self.new.by_gid)

    def test_every_relationship_added_has_its_inverse(self):
        pairs = {(s, t) for s, _, t in self.new.relationships}
        new_pairs = {(s, t) for s, _, t in set(self.new.relationships) - set(self.old.relationships)}
        for s, t in new_pairs:
            self.assertIn((t, s), pairs)

    def test_each_criterion_is_traced_to_a_requirement_and_states_its_value_function(self):
        for number in CRITERIA:
            e = self.new.one(number, "Statement")
            self.assertIn("Value function", e.findtext("description"))
            self.assertIn("Swing weight", e.findtext("description"))
            self.assertTrue(self.new.targets(number, "traced to", "Statement"), number)

    def test_the_alternatives_are_assets_related_to_the_subsystems_and_one_is_selected(self):
        selected = []
        for number in ALTERNATIVES:
            self.assertEqual(self.new.one(number, "Asset").findtext("name")[:24], "Plan-path alternative " + number[-1] + ":")
            related = self.new.targets(number, "relates", "Asset")
            self.assertTrue({"C.0.2", "C.0.6"} <= related, number)
            if "3.4.2.1" in self.new.targets(number, "satisfies", "Asset"):
                selected.append(number)
        self.assertEqual(len(selected), 1)
        self.assertIn("SELECTED", self.new.one(selected[0], "Asset").findtext("description"))

    def test_the_decision_is_related_to_every_alternative_and_criterion(self):
        self.assertEqual(self.new.targets("DEC.1", "relates", "Statement"), ALTERNATIVES | CRITERIA)

    def test_every_risk_has_a_probability_and_consequence_inside_the_matrix(self):
        for e in self.new.entities:
            if self.new.cls[e.findtext("schemaClassId")] == "Risk":
                for name in ("Probability", "Consequence"):
                    value = float(self.attr(e, name))
                    self.assertTrue(0.0 < value < 1.0, (e.findtext("number"), name, value))

    def test_the_new_risks_are_related_to_requirements_and_the_top_risk_to_its_functions(self):
        for number in NEW_RISKS:
            risk = self.new.one(number, "Risk")
            self.assertTrue(self.new.targets(number, "related to", "Risk"), number)
            self.assertTrue(risk.findtext("description"))
        top = self.new.targets("TR.16", "relates", "Risk")
        self.assertTrue({"F.2.2.3", "F.2.2.4", "IO.5"} <= top)
        self.assertTrue({"3.4.2.1", "5.4.4", "5.5.3"} <= self.new.targets("TR.16", "related to", "Risk"))


if __name__ == "__main__":
    unittest.main()
