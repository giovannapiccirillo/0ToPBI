# Test del gate di fase 1.5 (scripts/validate_data_analysis.py).
# Esecuzione: python -m unittest discover -s tests
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import validate_data_analysis as vda  # noqa: E402


def conforming_text():
    """Compila il template UFFICIALE (quello vero del repo) in un file conforme,
    con una singola tabella '### Vendite' completamente popolata."""
    lines = []
    for line in vda.TEMPLATE.read_text(encoding="utf-8").splitlines():
        if line == "- Tipo: Locale | Fabric Lakehouse":
            line = "- Tipo: Locale"
        elif line == "- Dettaglio:":
            line = "- Dettaglio: input/Test/"
        elif line == "### <Nome tabella/file>":
            line = "### Vendite"
        elif line == "- Righe:":
            line = "- Righe: 100"
        elif line == "- Colonne:":
            line = "- Colonne: Data (date), Importo (decimal)"
        elif line == "- Chiave candidata:":
            line = "- Chiave candidata: nessuna evidente"
        elif line == "- Qualità dati:":
            line = "- Qualità dati: nessuna anomalia rilevata"
        elif line == "- Anomalie di dominio:":
            line = "- Anomalie di dominio: nessuna"
        elif line == "- Metadati:":
            line = "- Metadati: estrazione mensile"
        elif line == "- Correzioni da proporre a etl-resolver:":
            line = "- Correzioni da proporre a etl-resolver: nessuna necessaria"
        elif line == "- Punti di attenzione per semantic-modeler:":
            line = "- Punti di attenzione per semantic-modeler: nessuno"
        lines.append(line)
    return "\n".join(lines) + "\n"


class TestValidateDataAnalysis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        tmp = Path(self.tmp.name)
        self._saved_root = vda.ROOT
        vda.ROOT = tmp
        self.workdir = "Test"
        self.output = tmp / "output" / self.workdir / "data-analysis.md"
        self.output.parent.mkdir(parents=True)

    def tearDown(self):
        vda.ROOT = self._saved_root
        self.tmp.cleanup()

    def run_main(self):
        with mock.patch.object(sys, "argv", ["validate_data_analysis.py", self.workdir]):
            return vda.main()

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
        text = conforming_text().replace("Vendite", "VenditÃ ")
        self.output.write_text(text, encoding="utf-8")
        self.assertEqual(self.run_main(), 1)

    def test_tipo_sorgente_non_ammesso_fallisce(self):
        text = conforming_text().replace("- Tipo: Locale", "- Tipo: Cloud generico")
        self.output.write_text(text, encoding="utf-8")
        self.assertEqual(self.run_main(), 1)

    def test_nessuna_tabella_fallisce(self):
        text = conforming_text()
        text = "\n".join(
            l for l in text.splitlines()
            if not l.startswith("### ") and l not in (
                "- Righe: 100", "- Colonne: Data (date), Importo (decimal)",
                "- Chiave candidata: nessuna evidente", "- Qualità dati: nessuna anomalia rilevata",
                "- Anomalie di dominio: nessuna", "- Metadati: estrazione mensile",
            )
        ) + "\n"
        self.output.write_text(text, encoding="utf-8")
        self.assertEqual(self.run_main(), 1)

    def test_campo_tabella_vuoto_fallisce(self):
        text = conforming_text().replace(
            "- Chiave candidata: nessuna evidente", "- Chiave candidata:"
        )
        self.output.write_text(text, encoding="utf-8")
        self.assertEqual(self.run_main(), 1)

    def test_sintesi_vuota_fallisce(self):
        text = conforming_text().replace(
            "- Correzioni da proporre a etl-resolver: nessuna necessaria",
            "- Correzioni da proporre a etl-resolver:",
        )
        self.output.write_text(text, encoding="utf-8")
        self.assertEqual(self.run_main(), 1)


if __name__ == "__main__":
    unittest.main()
