# Test del gate di fase 3 (scripts/validate_report.py).
# Esecuzione: python -m unittest discover -s tests
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import validate_report as vp  # noqa: E402

TABLE_TMDL = """table Vendite
\tcolumn Quantity
\t\tdataType: int64
\t\tsummarizeBy: none
\t\tsourceColumn: Quantity

\tmeasure 'Fatturato Totale' = SUM ( Vendite[Quantity] )
\t\tformatString: #,0

\tpartition Vendite = m
\t\tmode: import
\t\tsource = let x = 1 in x
"""

REQ_TEXT = """# Requisiti del Report

## KPI e Metriche Chiave
- Fatturato Totale — serve nuova misura: somma quantità

## Numero Pagine, Visual Desiderati e Layout
1. Executive Summary — scopo: panoramica di test
"""


def make_visual(vid, x, y, w, h, vtype="card", entity="Vendite",
                measure="Fatturato Totale", column=None):
    if column:
        field = {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": column}}
    else:
        field = {"Measure": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": measure}}
    return {
        "name": vid,
        "position": {"x": x, "y": y, "z": 0, "height": h, "width": w},
        "visual": {
            "visualType": vtype,
            "query": {"queryState": {"Values": {"projections": [{"field": field, "queryRef": "q"}]}}},
            "visualContainerObjects": {
                "general": [{"properties": {"altText": {"expr": {"Literal": {"Value": "'test'"}}}}}]
            },
        },
    }


class TestValidateReport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        tmp = Path(self.tmp.name)
        self._saved = (vp.ROOT, vp.REQUIREMENTS)
        vp.ROOT = tmp
        vp.REQUIREMENTS = tmp / "requirements.md"
        vp.REQUIREMENTS.write_text(REQ_TEXT, encoding="utf-8")

        model_def = tmp / "report" / "Test.SemanticModel" / "definition"
        (model_def / "tables").mkdir(parents=True)
        (model_def / "model.tmdl").write_text("model Model\n", encoding="utf-8")
        (model_def / "tables" / "Vendite.tmdl").write_text(TABLE_TMDL, encoding="utf-8")

        self.definition = tmp / "report" / "Test.Report" / "definition"
        (self.definition / "pages").mkdir(parents=True)
        (self.definition / "report.json").write_text("{}", encoding="utf-8")
        self.write_pages_meta(["page1"])
        self.add_page("page1", "Executive Summary")
        self.add_visual("page1", make_visual("v1", 0, 0, 300, 200))

    def tearDown(self):
        vp.ROOT, vp.REQUIREMENTS = self._saved
        self.tmp.cleanup()

    def write_pages_meta(self, page_order):
        (self.definition / "pages" / "pages.json").write_text(
            json.dumps({"pageOrder": page_order, "activePageName": page_order[0]}),
            encoding="utf-8",
        )

    def add_page(self, page_id, display_name, width=1280, height=720):
        d = self.definition / "pages" / page_id
        d.mkdir(exist_ok=True)
        (d / "page.json").write_text(json.dumps({
            "name": page_id, "displayName": display_name, "width": width, "height": height,
        }), encoding="utf-8")

    def add_visual(self, page_id, visual):
        d = self.definition / "pages" / page_id / "visuals" / visual["name"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "visual.json").write_text(json.dumps(visual), encoding="utf-8")

    def run_main(self):
        with mock.patch.object(sys, "argv", ["validate_report.py", "Test"]):
            return vp.main()

    def test_report_conforme_passa(self):
        self.assertEqual(self.run_main(), 0)

    def test_binding_a_misura_inesistente_fallisce(self):
        self.add_visual("page1", make_visual("v2", 400, 0, 300, 200, measure="Margine Fantasma"))
        self.assertEqual(self.run_main(), 1)

    def test_binding_a_tabella_inesistente_fallisce(self):
        self.add_visual("page1", make_visual("v2", 400, 0, 300, 200, entity="TabellaFantasma"))
        self.assertEqual(self.run_main(), 1)

    def test_visual_dati_sovrapposti_fallisce(self):
        self.add_visual("page1", make_visual("v2", 100, 50, 300, 200, vtype="barChart"))
        self.assertEqual(self.run_main(), 1)

    def test_textbox_sovrapposta_ammessa(self):
        overlay = make_visual("v2", 100, 50, 300, 200, vtype="textbox")
        del overlay["visual"]["query"]  # le textbox non hanno binding
        self.add_visual("page1", overlay)
        self.assertEqual(self.run_main(), 0)

    def test_visual_fuori_canvas_fallisce(self):
        self.add_visual("page1", make_visual("v2", 1200, 600, 300, 200))  # sborda 1280x720
        self.assertEqual(self.run_main(), 1)

    def test_cartella_pagina_orfana_fallisce(self):
        self.add_page("page2", "Orfana")  # esiste su disco ma non in pageOrder
        self.assertEqual(self.run_main(), 1)

    def test_pagina_richiesta_dai_requisiti_assente_fallisce(self):
        vp.REQUIREMENTS.write_text(
            REQ_TEXT + "2. Analisi di Dettaglio — scopo: approfondimento\n", encoding="utf-8"
        )
        self.assertEqual(self.run_main(), 1)

    def test_report_mancante_exit_2(self):
        with mock.patch.object(sys, "argv", ["validate_report.py", "Inesistente"]):
            self.assertEqual(vp.main(), 2)


if __name__ == "__main__":
    unittest.main()
