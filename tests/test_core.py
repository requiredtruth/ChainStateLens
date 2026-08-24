import copy
import json
import unittest
from pathlib import Path

from chainstatelens.core import LensError, parse_spec, project

DATA = Path(__file__).parents[1] / "chainstatelens" / "data"


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.spec_raw = json.loads((DATA / "demo_spec.json").read_text())
        self.evidence = json.loads((DATA / "demo_evidence.json").read_text())

    def test_projects_known_values(self):
        report = project(parse_spec(self.spec_raw), self.evidence)
        self.assertEqual(report["chain_id"], 1)
        self.assertEqual(len(report["rows"]), 2)
        self.assertEqual(report["rows"][0]["balance_wei"], 100)
        self.assertEqual(report["rows"][1]["nonce"], 2)
        self.assertEqual(report["rows"][0]["gas_utilization"], 0.5)
        self.assertEqual(len(report["report_sha256"]), 64)

    def test_is_deterministic(self):
        spec = parse_spec(self.spec_raw)
        self.assertEqual(project(spec, self.evidence), project(spec, copy.deepcopy(self.evidence)))

    def test_rejects_reorg_during_capture(self):
        self.evidence["captures"][0]["confirm_hash"] = "0x" + "0" * 64
        with self.assertRaisesRegex(LensError, "changed during capture"):
            project(parse_spec(self.spec_raw), self.evidence)

    def test_rejects_wrong_block(self):
        self.evidence["captures"][0]["block"]["number"] = "0x65"
        with self.assertRaisesRegex(LensError, "expected block"):
            project(parse_spec(self.spec_raw), self.evidence)

    def test_rejects_noncanonical_quantity(self):
        self.evidence["captures"][0]["accounts"]["demo_contract"]["balance"] = "0x064"
        with self.assertRaisesRegex(LensError, "canonical"):
            project(parse_spec(self.spec_raw), self.evidence)

    def test_rejects_missing_storage(self):
        self.evidence["captures"][0]["accounts"]["demo_contract"]["storage"] = {}
        with self.assertRaisesRegex(LensError, "storage evidence"):
            project(parse_spec(self.spec_raw), self.evidence)

    def test_rejects_duplicate_blocks(self):
        self.spec_raw["blocks"] = [100, 100]
        with self.assertRaisesRegex(LensError, "unique and increasing"):
            parse_spec(self.spec_raw)

    def test_rejects_unknown_spec_fields(self):
        self.spec_raw["private_key"] = "never"
        with self.assertRaisesRegex(LensError, "only blocks and targets"):
            parse_spec(self.spec_raw)
