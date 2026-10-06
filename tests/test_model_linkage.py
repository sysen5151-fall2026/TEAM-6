"""Model-to-product linkage check: every UC.1 action in the Innoslate model has code,
and no code claims an action ID that is not in the model."""

import unittest

import src.x1_commuter_sim  # noqa: F401  (importing pulls in every participant)
from src.model_trace import REGISTRY

# From the Innoslate export EcoCommute 10.4.xml (UC.1.1 - UC.1.12).
MODEL_UC1_ACTIONS = {f"UC.1.{i}" for i in range(1, 13)}


class TestModelLinkage(unittest.TestCase):
    def test_every_uc1_action_has_code(self):
        self.assertEqual(MODEL_UC1_ACTIONS - set(REGISTRY), set())

    def test_no_code_claims_an_unmodeled_action(self):
        self.assertEqual(set(REGISTRY) - MODEL_UC1_ACTIONS, set())


if __name__ == "__main__":
    unittest.main()
