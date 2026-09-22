# Test del gate di fase 1 (scripts/validate_requirements.py).
# Esecuzione: python -m unittest discover -s tests
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import validate_requirements as vr  # noqa: E402


def conforming_text():
    """Compila il template UFFICIALE (quello vero del repo) in un file conforme."""
    lines = []
    for line in vr.TEMPLATE.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if (stripped.startswith("<") and stripped.endswith(">")) or (
            stripped.startswith("{") and stripped.endswith("}")
        ):
            lines.append("testo compilato")
            continue
        if line == "- Nome report:":
            line = "- Nome report: Report di Test"
        elif line == "- Tipo di DB:":
            line = "- Tipo di DB: CSV locale"
        elif line == "- Modalità di connessione: Import | DirectQuery | Fabric Lakehouse":
            line = "- Modalità di connessione: Import"
        lines.append(line)
        if line == "- KPI (esistenti vs. che necessitano nuove misure):":
            lines.append("  - Fatturato Totale — serve nuova misura: Quantità × Prezzo")
    return "\n".join(lines) + "\n"


class TestValidateRequirements(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        tmp = Path(self.tmp.name)
        self._saved_root = vr.ROOT
        vr.ROOT = tmp
        self.workdir = "Test"
        self.output = tmp / "output" / self.workdir / "requirements.md"
        self.output.parent.mkdir(parents=True)
        self.input_dir = tmp / "input" / self.workdir  # inesistente: nessun file tabellare

    def tearDown(self):
        vr.ROOT = self._saved_root
        self.tmp.cleanup()

    def run_main(self):
        with mock.patch.object(sys, "argv", ["validate_requirements.py", self.workdir]):
            return vr.main()

    def test_file_conforme_passa(self):
        self.output.write_text(conforming_text(), encoding="utf-8")
        self.assertEqual(self.run_main(), 0)

    def test_file_mancante_exit_2(self):
        self.assertEqual(self.run_main(), 2)

    def test_intestazione_inventata_fallisce(self):
        self.output.write_text(conforming_text() + "\n## Sezione Inventata\n- x\n", encoding="utf-8")
        self.assertEqual(self.run_main(), 1)

    def test_segnaposto_non_compilato_fallisce(self):
        text = conforming_text() + "<segnaposto dimenticato>\n"
        self.output.write_text(text, encoding="utf-8")
        self.assertEqual(self.run_main(), 1)

    def test_mojibake_fallisce(self):
        text = conforming_text().replace("Granularità", "GranularitÃ ")
        self.output.write_text(text, encoding="utf-8")
        self.assertEqual(self.run_main(), 1)

    def test_kpi_non_atomici_fallisce(self):
        text = conforming_text().replace(
            "  - Fatturato Totale — serve nuova misura: Quantità × Prezzo",
            "  - Fatturato, Margine e altri KPI vari",
        )
        self.output.write_text(text, encoding="utf-8")
        self.assertEqual(self.run_main(), 1)

    def test_mapping_non_applicabile_con_file_tabellari_fallisce(self):
        self.input_dir.mkdir(parents=True)
        (self.input_dir / "vendite.csv").write_text("a,b\n1,2\n", encoding="utf-8")
        text = conforming_text().replace(
            "| Requisito atomico | Tabella.Colonna proposta | Allineato? | Note |\n|---|---|---|---|",
            "Non applicabile",
        )
        self.output.write_text(text, encoding="utf-8")
        self.assertEqual(self.run_main(), 1)


if __name__ == "__main__":
    unittest.main()
