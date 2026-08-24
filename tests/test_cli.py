import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from chainstatelens.cli import main

DATA = Path(__file__).parents[1] / "chainstatelens" / "data"


class CliTests(unittest.TestCase):
    def test_replay_then_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = str(Path(tmp) / "report.json")
            self.assertEqual(main(["replay", str(DATA/"demo_spec.json"), str(DATA/"demo_evidence.json"), "--output", report]), 0)
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(["verify", str(DATA/"demo_spec.json"), str(DATA/"demo_evidence.json"), report]), 0)
            self.assertIn("verified report_sha256=", output.getvalue())

    def test_tampered_report_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.json"
            main(["replay", str(DATA/"demo_spec.json"), str(DATA/"demo_evidence.json"), "--output", str(report)])
            value = json.loads(report.read_text())
            value["rows"][0]["balance_wei"] = 999
            report.write_text(json.dumps(value))
            errors = StringIO()
            with redirect_stderr(errors):
                self.assertEqual(main(["verify", str(DATA/"demo_spec.json"), str(DATA/"demo_evidence.json"), str(report)]), 2)
            self.assertIn("does not match", errors.getvalue())
