# Test dello script generico di fase 1.5 (scripts/prepare_staging.py).
# Esecuzione: python -m unittest discover -s tests
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import prepare_staging as ps  # noqa: E402


class TestNormalizzazioni(unittest.TestCase):
    def test_decimal_formato_italiano(self):
        s = pd.Series(["1.234,56", "10,5", "€ 99,90", "1234.56", "", "abc"])
        out = ps.normalize_decimal(s)
        self.assertEqual(out[0], 1234.56)
        self.assertEqual(out[1], 10.5)
        self.assertEqual(out[2], 99.90)
        self.assertEqual(out[3], 1234.56)
        self.assertTrue(pd.isna(out[4]))
        self.assertTrue(pd.isna(out[5]))

    def test_date_iso_e_invalide(self):
        s = pd.Series(["2024-01-15", "non-una-data", ""])
        out = ps.normalize_date(s)
        self.assertEqual(out[0], pd.Timestamp("2024-01-15"))
        self.assertTrue(pd.isna(out[1]))
        self.assertTrue(pd.isna(out[2]))

    def test_boolean_valori_misti(self):
        s = pd.Series(["SI", "no", "Sì?", ""])
        out = ps.normalize_boolean(s, true_values={"si", "sì"}, false_values={"no"})
        self.assertEqual(out[0], True)
        self.assertEqual(out[1], False)
        self.assertIsNone(out[2])  # valore non mappato: non si indovina
        self.assertIsNone(out[3])

    def test_categorical_non_mappato_resta_invariato(self):
        s = pd.Series(["nord", "NORD ", "Sud-Ovest"])
        out = ps.normalize_categorical(s, {"nord": "Nord"})
        self.assertEqual(list(out), ["Nord", "Nord", "Sud-Ovest"])


class TestPrepareStaging(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.source = self.dir / "vendite.csv"
        self.source.write_text(
            "OrderID,Amount\nA1,\"1.234,56\"\nA2,\"10,5\"\n", encoding="utf-8"
        )
        self.staging_root = self.dir / "staging"

    def tearDown(self):
        self.tmp.cleanup()

    def run_job(self, column_config, **kwargs):
        return ps.prepare_staging(
            source_path=str(self.source),
            project_name="Test",
            column_config=column_config,
            staging_root=str(self.staging_root),
            **kwargs,
        )

    def test_csv_e_log_scritti_insieme(self):
        result = self.run_job(
            {"Amount": "decimal"},
            requirement_refs={"Amount": "Fatturato Totale"},
        )
        out_csv = self.staging_root / "Test" / "vendite.csv"
        log = self.staging_root / "Test" / "etl-log.md"
        self.assertTrue(out_csv.exists())
        self.assertTrue(log.exists(), "etl-log.md è output obbligatorio quanto il CSV")
        log_text = log.read_text(encoding="utf-8")
        self.assertIn("## vendite.csv", log_text)
        self.assertIn("Fatturato Totale", log_text)  # requisito di riferimento tracciato
        self.assertEqual(result["rows_in"], 2)
        df = pd.read_csv(out_csv)
        self.assertAlmostEqual(df["Amount"][0], 1234.56)

    def test_file_gia_conforme_logga_nessuna_trasformazione(self):
        self.run_job({})
        log_text = (self.staging_root / "Test" / "etl-log.md").read_text(encoding="utf-8")
        self.assertIn("Nessuna: dati già conformi", log_text)

    def test_riesecuzione_sostituisce_la_sezione_senza_duplicarla(self):
        self.run_job({"Amount": "decimal"})
        self.run_job({"Amount": "decimal"})
        log_text = (self.staging_root / "Test" / "etl-log.md").read_text(encoding="utf-8")
        self.assertEqual(log_text.count("## vendite.csv"), 1)

    def test_anomalie_riportate_nel_log(self):
        self.run_job({}, anomalies=["3 righe con OrderID duplicato: conferma richiesta"])
        log_text = (self.staging_root / "Test" / "etl-log.md").read_text(encoding="utf-8")
        self.assertIn("OrderID duplicato", log_text)

    def test_run_config_da_json(self):
        import json

        cfg = self.dir / "etl-config.json"
        cfg.write_text(json.dumps({
            "project": "Test",
            "staging_root": str(self.staging_root),
            "jobs": [{"source": str(self.source), "column_config": {"Amount": "decimal"}}],
        }), encoding="utf-8")
        results = ps.run_config(str(cfg))
        self.assertEqual(len(results), 1)
        self.assertTrue(Path(results[0]["path"]).exists())


if __name__ == "__main__":
    unittest.main()
