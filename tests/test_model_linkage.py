"""Model-to-product linkage check against the exported Innoslate model.

Reads the UC.1.x action numbers from the XML export in docs/model/ and verifies that
(1) each has at least one @realizes-tagged implementation and (2) no other UC.1.x
action ID is tagged in code. It does not check performers or satisfies links.
"""

import glob
import os
import re
import unittest
import xml.etree.ElementTree as ET

import src.x1_commuter_sim  # noqa: F401  (importing pulls in every participant)
from src.model_trace import REGISTRY

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "docs", "model")
UC1_ACTION = re.compile(r"^UC\.1\.\d+$")


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


class TestModelLinkage(unittest.TestCase):
    def test_model_has_the_twelve_uc1_actions(self):
        self.assertEqual(model_uc1_actions(), {f"UC.1.{i}" for i in range(1, 13)})

    def test_every_modeled_uc1_action_has_code(self):
        self.assertEqual(model_uc1_actions() - set(REGISTRY), set())

    def test_no_code_claims_an_unmodeled_uc1_action(self):
        tagged = {a for a in REGISTRY if UC1_ACTION.match(a)}
        self.assertEqual(tagged - model_uc1_actions(), set())


if __name__ == "__main__":
    unittest.main()
