"""Model-to-product linkage check against the exported Innoslate model.

Reads the UC.1.x action numbers from the XML export in docs/model/ and verifies that
(1) each has at least one @realizes-tagged implementation and (2) no other UC.1.x
action ID is tagged in code. For the web flow (UC.3.x, model 10.9) it also reads who
performs each action: every action performed by a component (C.1-C.4) must have code,
and no other UC.3.x ID may be tagged. It does not check satisfies links.
"""

import glob
import os
import re
import unittest
import xml.etree.ElementTree as ET

import src.x1_commuter_sim  # noqa: F401  (importing pulls in every participant)
from src.model_trace import REGISTRY

try:
    import src.c1_web_front_end.web_app  # noqa: F401  (tags the C.1 pages; needs Flask)

    WEB_PAGES_LOADED = True
except ImportError:
    WEB_PAGES_LOADED = False

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "docs", "model")
UC1_ACTION = re.compile(r"^UC\.1\.\d+$")
UC3_ACTION = re.compile(r"^UC\.3\.\d+$")


def model_uc1_actions():
    files = sorted(glob.glob(os.path.join(MODEL_DIR, "EcoCommute_*.xml")))
    assert files, "no Innoslate export found in docs/model/"
    root = ET.parse(files[-1]).getroot()
    numbers = set()
    for entity in root.find("database").iter("entity"):
        number = (entity.findtext("number") or "").strip()
        if UC1_ACTION.match(number):
            numbers.add(number)
    return numbers


def model_uc3_performers():
    """{UC.3.x action: set of performer numbers} from the latest export."""
    root = ET.parse(sorted(glob.glob(os.path.join(MODEL_DIR, "EcoCommute_*.xml")))[-1]).getroot()
    schema, db = root.find("schema"), root.find("database")
    relation = {c.get("id"): c.findtext("name") for c in schema if c.tag == "schemaRelation"}
    number = {e.findtext("globalId"): (e.findtext("number") or "").strip() for e in db.iter("entity")}
    performers = {n: set() for n in number.values() if UC3_ACTION.match(n)}
    for r in db.iter("relationship"):
        if relation[r.findtext("schemaRelationId")] == "performed by":
            action = number[r.findtext("sourceId")]
            if action in performers:
                performers[action].add(number[r.findtext("targetId")])
    return performers


class TestModelLinkage(unittest.TestCase):
    def test_model_has_the_twelve_uc1_actions(self):
        self.assertEqual(model_uc1_actions(), {f"UC.1.{i}" for i in range(1, 13)})

    def test_every_modeled_uc1_action_has_code(self):
        self.assertEqual(model_uc1_actions() - set(REGISTRY), set())

    def test_no_code_claims_an_unmodeled_uc1_action(self):
        tagged = {a for a in REGISTRY if UC1_ACTION.match(a)}
        self.assertEqual(tagged - model_uc1_actions(), set())


class TestWebFlowLinkage(unittest.TestCase):
    def test_model_has_the_eleven_uc3_actions(self):
        self.assertEqual(set(model_uc3_performers()), {f"UC.3.{i}" for i in range(1, 12)})

    def test_every_uc3_action_performed_by_a_component_has_code(self):
        by_component = {a for a, who in model_uc3_performers().items() if any(w.startswith("C.") for w in who)}
        self.assertTrue(by_component)
        if not WEB_PAGES_LOADED:  # the C.1 pages need Flask; the other components can still be checked
            by_component = {a for a in by_component if not model_uc3_performers()[a] & {"C.1"}}
        self.assertEqual(by_component - set(REGISTRY), set())

    def test_no_code_claims_an_unmodeled_uc3_action(self):
        tagged = {a for a in REGISTRY if UC3_ACTION.match(a)}
        self.assertEqual(tagged - set(model_uc3_performers()), set())


if __name__ == "__main__":
    unittest.main()
