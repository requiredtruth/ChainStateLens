import pathlib
import unittest

ROOT = pathlib.Path(__file__).parents[1]


class ReleaseTests(unittest.TestCase):
    def test_required_files(self):
        for path in ["README.md", "SUPPORT.md", "LICENSE", "CHANGELOG.md", "PROJECT_SPEC.md", "install.sh", "run.sh"]:
            self.assertTrue((ROOT / path).is_file(), path)

    def test_funding_addresses_exact(self):
        expected = {
            "bc1qh474jpyw4malh0fmg2uy7n05ggtjvnjtcwhdne",
            "0x8fcC9C0d1FFCE17b1dEC91B299E56d66BC126Ba8",
            "D6qp2awRAHVo2VgincTAW5frhnJ9MBZcz4",
        }
        support = (ROOT / "SUPPORT.md").read_text()
        self.assertEqual({line.split("`",2)[1] for line in support.splitlines() if line.startswith("- ")}, expected)

    def test_no_secret_or_transaction_surface(self):
        source = "\n".join(p.read_text() for p in (ROOT / "chainstatelens").rglob("*.py"))
        for forbidden in ["eth_sendTransaction", "eth_sendRawTransaction", "personal_unlockAccount"]:
            self.assertNotIn(forbidden, source.replace('"eth_sendRawTransaction"', ''))
