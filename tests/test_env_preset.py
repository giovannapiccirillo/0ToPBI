# Test del lettore del preset locale (scripts/env_preset.py).
# Esecuzione: python -m unittest discover -s tests
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import env_preset as ep  # noqa: E402


class TestEnvPreset(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_file_assente_ritorna_dict_vuoto(self):
        self.assertEqual(ep.load_env(self.dir / "non-esiste.env"), {})

    def test_legge_chiavi_valorizzate(self):
        env = self.dir / ".env"
        env.write_text("NOME_PROGETTO=demo\nNOME_PBIP=Vendite\nCULTURA=it-IT\n", encoding="utf-8")
        self.assertEqual(
            ep.load_env(env),
            {"NOME_PROGETTO": "demo", "NOME_PBIP": "Vendite", "CULTURA": "it-IT"},
        )

    def test_ignora_commenti_e_righe_vuote(self):
        env = self.dir / ".env"
        env.write_text("# commento\n\nNOME_PROGETTO=demo\n", encoding="utf-8")
        self.assertEqual(ep.load_env(env), {"NOME_PROGETTO": "demo"})

    def test_chiave_vuota_non_inclusa(self):
        env = self.dir / ".env"
        env.write_text("NOME_PROGETTO=\nCULTURA=it-IT\n", encoding="utf-8")
        self.assertEqual(ep.load_env(env), {"CULTURA": "it-IT"})


if __name__ == "__main__":
    unittest.main()
