# Test del convertitore generico di input/ (scripts/convert_input.py).
# Esecuzione: python -m unittest discover -s tests
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import convert_input as ci  # noqa: E402

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

DOC_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="{W_NS}"><w:body>
<w:p><w:r><w:t>Requisiti del report vendite</w:t></w:r></w:p>
<w:tbl>
<w:tr><w:tc><w:p><w:r><w:t>KPI</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>Formula</w:t></w:r></w:p></w:tc></w:tr>
<w:tr><w:tc><w:p><w:r><w:t>Fatturato</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>Q x P</w:t></w:r></w:p></w:tc></w:tr>
</w:tbl>
</w:body></w:document>"""


def make_docx(path: Path):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("word/document.xml", DOC_XML)


class TestConvertInput(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_docx_to_markdown_paragrafi_e_tabelle(self):
        src = self.dir / "requisiti.docx"
        make_docx(src)
        md = ci.docx_to_markdown(src)
        self.assertIn("Requisiti del report vendite", md)
        self.assertIn("| KPI | Formula |", md)
        self.assertIn("| Fatturato | Q x P |", md)

    def test_convert_one_scrive_md_accanto_e_riusa(self):
        src = self.dir / "requisiti.docx"
        make_docx(src)
        [(dest, status)] = ci.convert_one(src, force=False)
        self.assertEqual(dest, src.with_suffix(".md"))
        self.assertEqual(status, "convertito")
        self.assertTrue(dest.exists())
        [(_, status2)] = ci.convert_one(src, force=False)  # seconda chiamata: riuso
        self.assertIn("riusato", status2)

    def test_estensione_non_gestita_ignorata(self):
        src = self.dir / "dati.txt"
        src.write_text("x", encoding="utf-8")
        [(_, status)] = ci.convert_one(src, force=False)
        self.assertIn("ignorato", status)

    def test_xlsx_to_csv(self):
        try:
            import openpyxl
        except ImportError:
            self.skipTest("openpyxl non installato")
        src = self.dir / "vendite.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Vendite"
        ws.append(["OrderID", "Amount"])
        ws.append(["A1", "10,5"])
        wb.save(src)
        results = ci.xlsx_to_csv(src, force=False)
        self.assertEqual(len(results), 1)
        dest, status = results[0]
        self.assertEqual(status, "convertito")
        text = dest.read_text(encoding="utf-8")
        self.assertIn("OrderID,Amount", text)
        self.assertIn('A1,"10,5"', text)


if __name__ == "__main__":
    unittest.main()
