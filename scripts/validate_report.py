# Valida i file PBIR del report (fase 3) contro il modello semantico e i requisiti approvati.
# Uso: python scripts/validate_report.py [NomeProgetto]   (default: unico *.Report in report/)
# Exit 0 = CONFORME; exit 1 = NON CONFORME; exit 2 = file mancanti.
# Gate obbligatorio: la fase 3 non è conclusa finché questo script non esce con 0.
#
# Complementare a `powerbi-report-author validate` (che verifica lo schema JSON):
# qui si verifica la COERENZA report ↔ modello ↔ requisiti:
#   - struttura pages/ allineata a pages.json (pageOrder, activePageName)
#   - ogni binding (Column/Measure/Hierarchy) punta a oggetti esistenti nel modello
#   - ogni pagina richiesta dai requisiti esiste nel report
#   - (avviso non bloccante) KPI dei requisiti mai usati in alcun visual
#   - nessuna sovrapposizione tra visual dati; visual dentro il canvas
#   - encoding integro (niente mojibake)
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUIREMENTS = ROOT / "output/requirements.md"

# Tipi decorativi: possono legittimamente sovrapporsi ad altri visual (annotazioni,
# sfondi, loghi) e non richiedono binding né altText obbligatorio.
DECOR_TYPES = {"textbox", "shape", "basicShape", "image", "actionButton"}


def find_dir(suffix, name=None):
    report_dir = ROOT / "report"
    if not report_dir.exists():
        return None
    if name:
        d = report_dir / f"{name}.{suffix}"
        return d if d.exists() else None
    dirs = sorted(report_dir.glob(f"*.{suffix}"))
    return dirs[0] if len(dirs) == 1 else None


def load_model_catalog(model_dir):
    """Cataloga tabelle/colonne/misure/gerarchie dal TMDL del modello validato."""
    catalog = {}
    files = [model_dir / "definition" / "model.tmdl"]
    tables_dir = model_dir / "definition" / "tables"
    if tables_dir.exists():
        files += sorted(tables_dir.glob("*.tmdl"))
    for f in files:
        if not f.exists():
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        current = None
        for line in text.splitlines():
            m = re.match(r"^table\s+(?:'([^']+)'|(\S+))", line)
            if m:
                current = m.group(1) or m.group(2)
                catalog.setdefault(current, {"columns": set(), "measures": set(), "hierarchies": set()})
                continue
            if current is None:
                continue
            m = re.match(r"^\tcolumn\s+(?:'([^']+)'|(\S+))", line)
            if m:
                catalog[current]["columns"].add(m.group(1) or m.group(2))
                continue
            m = re.match(r"^\tmeasure\s+(?:'([^']+)'|([^=\s][^=\n]*?))\s*=", line)
            if m:
                catalog[current]["measures"].add((m.group(1) or m.group(2)).strip())
                continue
            m = re.match(r"^\thierarchy\s+(?:'([^']+)'|(\S+))", line)
            if m:
                catalog[current]["hierarchies"].add(m.group(1) or m.group(2))
    return catalog


def required_measures(req_text):
    """Stessa estrazione KPI atomici di validate_model.py (fonte: requirements.md)."""
    names = []
    in_kpi = False
    for line in req_text.splitlines():
        if line.startswith("## "):
            in_kpi = line.strip() == "## KPI e Metriche Chiave"
            continue
        if in_kpi:
            m = re.match(r"^\s*- (.+?) — (?:serve nuova misura|misura esistente)", line)
            if m:
                names.append(m.group(1).strip())
    return names


def required_pages(req_text):
    """Titoli pagina dalla sezione 'Numero Pagine, Visual Desiderati e Layout'."""
    titles = []
    in_section = False
    for line in req_text.splitlines():
        if line.startswith("## "):
            in_section = line.strip() == "## Numero Pagine, Visual Desiderati e Layout"
            continue
        if in_section:
            m = re.match(r"^\d+\.\s+(.+?)\s+—", line)
            if m and not m.group(1).startswith("<"):
                titles.append(m.group(1).strip())
    return titles


def _entity_of(node):
    try:
        return node["Expression"]["SourceRef"]["Entity"]
    except (KeyError, TypeError):
        return None


def walk_bindings(node, out):
    """Raccoglie ricorsivamente i riferimenti a campi del modello nel JSON PBIR."""
    if isinstance(node, dict):
        for kind, prop_key in (("Column", "Property"), ("Measure", "Property"), ("Hierarchy", "Hierarchy")):
            sub = node.get(kind)
            if isinstance(sub, dict) and prop_key in sub:
                entity = _entity_of(sub)
                if entity:
                    out.append((kind, entity, sub[prop_key]))
        for v in node.values():
            walk_bindings(v, out)
    elif isinstance(node, list):
        for v in node:
            walk_bindings(v, out)


def rects_overlap(a, b, eps=1.0):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax + eps < bx + bw and bx + eps < ax + aw and ay + eps < by + bh and by + eps < ay + ah


def read_json(path, errors, mojibake_files):
    raw = path.read_text(encoding="utf-8", errors="replace")
    rel = path.relative_to(ROOT)
    if "Ã" in raw or "�" in raw:
        mojibake_files.append(str(rel))
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        errors.append(f"JSON non valido in {rel}: {e}")
        return None


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else None
    report_dir = find_dir("Report", name)
    if report_dir is None:
        print("ERRORE: cartella *.Report non trovata (o ambigua: passare il NomeProgetto).")
        return 2
    stem = report_dir.name[: -len(".Report")]
    model_dir = find_dir("SemanticModel", stem)
    if model_dir is None:
        print(f"ERRORE: report/{stem}.SemanticModel non trovato — la fase 3 richiede il modello della fase 2.")
        return 2
    if not REQUIREMENTS.exists():
        print(f"ERRORE: {REQUIREMENTS} non esiste — la fase 3 richiede requisiti approvati.")
        return 2
    definition = report_dir / "definition"
    pages_json = definition / "pages" / "pages.json"
    if not definition.exists() or not pages_json.exists():
        print(f"NON CONFORME: {definition / 'pages' / 'pages.json'} non esiste — struttura PBIR assente.")
        return 2

    errors = []
    warnings = []
    mojibake_files = []

    read_json(definition / "report.json", errors, mojibake_files) if (definition / "report.json").exists() \
        else errors.append("definition/report.json mancante.")
    pages_meta = read_json(pages_json, errors, mojibake_files) or {}

    page_order = pages_meta.get("pageOrder", [])
    page_dirs = sorted(d.name for d in (definition / "pages").iterdir() if d.is_dir())
    missing_dirs = [p for p in page_order if p not in page_dirs]
    orphan_dirs = [d for d in page_dirs if d not in page_order]
    if missing_dirs:
        errors.append("Pagine in pageOrder SENZA cartella corrispondente: " + ", ".join(missing_dirs))
    if orphan_dirs:
        errors.append("Cartelle pagina NON elencate in pageOrder: " + ", ".join(orphan_dirs))
    active = pages_meta.get("activePageName")
    if active and active not in page_order:
        errors.append(f"activePageName '{active}' non presente in pageOrder.")

    catalog = load_model_catalog(model_dir)
    if not catalog:
        errors.append(f"Nessuna tabella trovata nel TMDL di {model_dir.name}: impossibile verificare i binding.")

    display_names = []
    bound_measures = set()
    n_visuals = 0
    n_bindings = 0

    for page_id in page_dirs:
        page_dir = definition / "pages" / page_id
        page = read_json(page_dir / "page.json", errors, mojibake_files) if (page_dir / "page.json").exists() else None
        if page is None:
            errors.append(f"pages/{page_id}/page.json mancante o illeggibile.")
            continue
        if page.get("name") != page_id:
            errors.append(f"pages/{page_id}: 'name' ('{page.get('name')}') diverso dal nome cartella.")
        display = (page.get("displayName") or "").strip()
        if not display:
            errors.append(f"pages/{page_id}: displayName vuoto.")
        display_names.append(display)
        pw, ph = page.get("width", 0), page.get("height", 0)
        if not pw or not ph:
            errors.append(f"pages/{page_id}: width/height del canvas mancanti.")

        data_rects = []  # (visual_id, visualType, rect)
        visuals_dir = page_dir / "visuals"
        for vdir in sorted(visuals_dir.iterdir()) if visuals_dir.exists() else []:
            vfile = vdir / "visual.json"
            if not vfile.exists():
                errors.append(f"pages/{page_id}/visuals/{vdir.name}: visual.json mancante.")
                continue
            visual = read_json(vfile, errors, mojibake_files)
            if visual is None:
                continue
            n_visuals += 1
            vid = vdir.name
            where = f"pagina '{display or page_id}', visual {vid}"
            if visual.get("name") != vid:
                errors.append(f"{where}: 'name' diverso dal nome cartella.")
            pos = visual.get("position") or {}
            rect = (pos.get("x"), pos.get("y"), pos.get("width"), pos.get("height"))
            if any(v is None for v in rect):
                errors.append(f"{where}: position incompleta (x/y/width/height).")
                rect = None
            body = visual.get("visual")
            vtype = (body or {}).get("visualType", "")
            if body is not None and not vtype:
                errors.append(f"{where}: visualType mancante.")
            if rect and pw and ph and (rect[0] + rect[2] > pw + 1 or rect[1] + rect[3] > ph + 1
                                       or rect[0] < 0 or rect[1] < 0):
                errors.append(f"{where}: fuori dal canvas {pw}x{ph} "
                              f"(x={rect[0]}, y={rect[1]}, w={rect[2]}, h={rect[3]}).")

            refs = []
            walk_bindings(visual, refs)
            n_bindings += len(refs)
            for kind, entity, prop in refs:
                table = catalog.get(entity)
                if table is None:
                    errors.append(f"{where}: binding a tabella inesistente nel modello: '{entity}'.")
                    continue
                if kind == "Column" and prop not in table["columns"]:
                    errors.append(f"{where}: colonna '{entity}'[{prop}] inesistente nel modello.")
                elif kind == "Measure":
                    if prop not in table["measures"]:
                        errors.append(f"{where}: misura '{entity}'[{prop}] inesistente nel modello.")
                    else:
                        bound_measures.add(prop)
                elif kind == "Hierarchy" and prop not in table["hierarchies"]:
                    errors.append(f"{where}: gerarchia '{entity}'[{prop}] inesistente nel modello.")

            if body is not None and vtype not in DECOR_TYPES:
                if rect:
                    data_rects.append((vid, vtype, rect))
                # altText atteso sui visual informativi; gli slicer sono controlli interattivi
                if vtype != "slicer":
                    vco = body.get("visualContainerObjects") or {}
                    general = (vco.get("general") or [{}])[0].get("properties", {})
                    if "altText" not in general:
                        warnings.append(f"{where} ({vtype}): altText assente (accessibilità).")

        for i in range(len(data_rects)):
            for j in range(i + 1, len(data_rects)):
                (id1, t1, r1), (id2, t2, r2) = data_rects[i], data_rects[j]
                if rects_overlap(r1, r2):
                    errors.append(f"pagina '{display or page_id}': visual dati sovrapposti "
                                  f"{id1} ({t1}) e {id2} ({t2}).")

    if mojibake_files:
        errors.append("Encoding corrotto (mojibake tipo 'Ã') in: " + ", ".join(sorted(set(mojibake_files)))
                      + " — riscrivere i file in UTF-8.")

    # I requisiti impongono la copertura KPI nel MODELLO (gate fase 2) e la copertura
    # PAGINE nel report: un KPI mai mostrato in un visual è un avviso, non un errore.
    req_text = REQUIREMENTS.read_text(encoding="utf-8", errors="replace")
    missing_kpi = [k for k in required_measures(req_text) if k not in bound_measures]
    if missing_kpi:
        warnings.append("KPI dei requisiti non usati in alcun visual del report: " + "; ".join(missing_kpi))
    have = {d.casefold() for d in display_names}
    missing_pages = [t for t in required_pages(req_text) if t.casefold() not in have]
    if missing_pages:
        errors.append("Pagine richieste dai requisiti ASSENTI nel report (o con displayName diverso): "
                      + "; ".join(missing_pages))

    if warnings:
        print("AVVISI (non bloccanti):")
        for w in warnings:
            print(f"  - {w}")

    if errors:
        print(f"NON CONFORME — {report_dir.name} non supera la validazione di fase 3:")
        for e in errors:
            print(f"  - {e}")
        print("\nAzione richiesta: correggere i file PBIR (report-builder), rieseguire "
              "`powerbi-report-author validate` e questo script fino a exit 0.")
        return 1

    print(f"CONFORME: {report_dir.name} — {len(page_dirs)} pagine, {n_visuals} visual, "
          f"{n_bindings} binding verificati sul modello; tutte le pagine dei requisiti presenti.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
