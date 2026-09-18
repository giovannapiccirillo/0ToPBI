# Test del gate di fase 2 (scripts/validate_model.py).
# Esecuzione: python -m unittest discover -s tests
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import validate_model as vm  # noqa: E402

TABLE_TMDL = """table Vendite
\tcolumn Quantity
\t\tdataType: int64
\t\tsummarizeBy: none
\t\tsourceColumn: Quantity

\tmeasure 'Fatturato Totale' = SUM ( Vendite[Quantity] )
\t\tformatString: #,0

\tpartition Vendite = m
\t\tmode: import
\t\tsource = let x = Csv.Document(File.Contents("staging/Test/vendite.csv")) in x
"""

REQ_TEXT = """# Requisiti del Report

## KPI e Metriche Chiave
- Fatturato Totale — serve nuova misura: somma quantità per prezzo
"""


class TestValidateModel(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        tmp = Path(self.tmp.name)
        self._saved_root = vm.ROOT
        vm.ROOT = tmp
        self.workdir = "Test"
        self.requirements = tmp / "output" / self.workdir / "requirements.md"
        self.requirements.parent.mkdir(parents=True)
        self.requirements.write_text(REQ_TEXT, encoding="utf-8")
        self.def_dir = tmp / "report" / "Test.SemanticModel" / "definition"
        (self.def_dir / "tables").mkdir(parents=True)
        (self.def_dir / "model.tmdl").write_text("model Model\n\tculture: it-IT\n", encoding="utf-8")
        (self.def_dir / "tables" / "Vendite.tmdl").write_text(TABLE_TMDL, encoding="utf-8")

    def tearDown(self):
        vm.ROOT = self._saved_root
        self.tmp.cleanup()

    def run_main(self):
        with mock.patch.object(sys, "argv", ["validate_model.py", self.workdir, "Test"]):
            return vm.main()

    def test_modello_conforme_passa(self):
        self.assertEqual(self.run_main(), 0)

    def test_cartella_mancante_exit_2(self):
        with mock.patch.object(sys, "argv", ["validate_model.py", self.workdir, "Inesistente"]):
            self.assertEqual(vm.main(), 2)

    def test_misura_richiesta_assente_fallisce(self):
        self.requirements.write_text(
            REQ_TEXT + "- Margine — serve nuova misura: fatturato meno costi\n",
            encoding="utf-8",
        )
        self.assertEqual(self.run_main(), 1)

    def test_tmdl_senza_indentazione_fallisce(self):
        flat = TABLE_TMDL.replace("\t\tdataType: int64", "dataType: int64")
        (self.def_dir / "tables" / "Vendite.tmdl").write_text(flat, encoding="utf-8")
        self.assertEqual(self.run_main(), 1)

    def test_tabella_duplicata_fallisce(self):
        (self.def_dir / "tables" / "Vendite2.tmdl").write_text(TABLE_TMDL, encoding="utf-8")
        self.assertEqual(self.run_main(), 1)

    def test_partition_mancante_fallisce(self):
        no_partition = TABLE_TMDL.split("\tpartition")[0]
        (self.def_dir / "tables" / "Vendite.tmdl").write_text(no_partition, encoding="utf-8")
        self.assertEqual(self.run_main(), 1)


if __name__ == "__main__":
    unittest.main()
