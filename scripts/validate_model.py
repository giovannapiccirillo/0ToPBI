# Valida il modello semantico PBIP (fase 2) contro i requisiti approvati.
# Uso: python scripts/validate_model.py [NomeProgetto]   (default: unico *.SemanticModel in report/)
# Exit 0 = CONFORME; exit 1 = NON CONFORME; exit 2 = file mancanti.
# Gate obbligatorio: la fase 2 non è conclusa finché questo script non esce con 0.
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUIREMENTS = ROOT / "output/requirements.md"


def find_model_dir(name=None):
    report_dir = ROOT / "report"
    if not report_dir.exists():
        return None
    if name:
        d = report_dir / f"{name}.SemanticModel"
        return d if d.exists() else None
    dirs = sorted(report_dir.glob("*.SemanticModel"))
    return dirs[0] if len(dirs) == 1 else None


def collect_tmdl(model_dir):
    files = [model_dir / "definition" / "model.tmdl"]
    files += sorted((model_dir / "definition" / "tables").glob("*.tmdl")) \
        if (model_dir / "definition" / "tables").exists() else []
    return "\n".join(f.read_text(encoding="utf-8", errors="replace") for f in files if f.exists())


# Proprietà TMDL che non possono MAI stare a colonna 0: se ci sono, il file è
# stato scritto a mano senza indentazione e Desktop fallirà con "Indentation".
FLAT_PROPS = re.compile(
    r"^(?:(?:compatibilityLevel|dataType|formatString|sourceColumn|summarizeBy|mode|"
    r"fromColumn|toColumn|cardinality|crossFilteringBehavior|isActive|culture):"
    r"|(?:isHidden|isKey)\s*$)",
    re.MULTILINE,
)


def check_indentation(model_dir):
    bad = []
    for f in sorted((model_dir / "definition").rglob("*.tmdl")):
        text = f.read_text(encoding="utf-8", errors="replace")
        if FLAT_PROPS.search(text):
            bad.append(f.name)
    return bad


def required_measures(req_text):
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


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else None
    model_dir = find_model_dir(name)
    if model_dir is None:
        print("ERRORE: cartella *.SemanticModel non trovata (o ambigua: passare il NomeProgetto).")
        return 2
    if not REQUIREMENTS.exists():
        print(f"ERRORE: {REQUIREMENTS} non esiste — la fase 2 richiede requisiti approvati.")
        return 2

    tmdl = collect_tmdl(model_dir)
    if not tmdl.strip():
        print(f"NON CONFORME: nessun TMDL trovato in {model_dir}/definition")
        return 1
    errors = []

    # 0. Indentazione TMDL: proprietà a colonna 0 = file scritto a mano senza struttura
    flat_files = check_indentation(model_dir)
    if flat_files:
        errors.append(
            "TMDL senza indentazione (proprietà a colonna 0) in: " + ", ".join(flat_files)
            + " — Desktop fallisce con 'Errore di formato TMDL: Indentation'. "
            "Le proprietà vanno indentate con tab sotto il proprio oggetto."
        )

    # 1. Encoding integro (à/€ corrotti da scritture ANSI)
    if "Ã" in tmdl or "�" in tmdl:
        errors.append("Encoding corrotto nel TMDL (mojibake tipo 'Ã'): riscrivere via MCP/UTF-8.")

    # 2. Tabelle duplicate (blocco 'table X' ripetuto)
    tables = re.findall(r"^table\s+(?:'([^']+)'|(\S+))", tmdl, re.MULTILINE)
    tables = [a or b for a, b in tables]
    dupes = sorted({t for t in tables if tables.count(t) > 1})
    if dupes:
        errors.append(f"Tabelle definite più volte nel TMDL: {', '.join(dupes)} — il PBIP non si aprirà in Desktop.")

    # 3. Ogni tabella deve avere una partition (sorgente dati)
    partitions = len(re.findall(r"^\s*partition\s+", tmdl, re.MULTILINE))
    if tables and partitions == 0:
        errors.append("Nessuna 'partition' definita: il modello non ha sorgenti dati e le tabelle resterebbero vuote.")
    elif partitions < len(set(tables)):
        errors.append(f"Partition mancanti: {len(set(tables))} tabelle ma solo {partitions} partition.")

    # 4. Copertura misure: ogni KPI 'serve nuova misura' dei requisiti deve esistere nel modello
    req_text = REQUIREMENTS.read_text(encoding="utf-8", errors="replace")
    model_measures = [a or b for a, b in re.findall(
        r"^\s*measure\s+(?:'([^']+)'|([^\s=]+))\s*=", tmdl, re.MULTILINE)]
    # Fallback per TMDL vecchio stile senza keyword 'measure' (nomi nudi prima di '=')
    if not model_measures:
        model_measures = [a or b for a, b in re.findall(
            r"^\s*(?:'([^']+)'|([^\s=][^=\n]*?))\s*=", tmdl, re.MULTILINE)]
    model_measures = [m.strip() for m in model_measures]
    required = required_measures(req_text)
    if not required:
        errors.append("Sezione 'KPI e Metriche Chiave' di output/requirements.md non nel formato atomico "
                      "richiesto ('- <Nome> — serve nuova misura ...' / '- <Nome> — misura esistente ...'): "
                      "impossibile verificare la copertura misure. Correggere prima requirements.md "
                      "(python scripts/validate_requirements.py).")
    missing = [r for r in required if r not in model_measures]
    if missing:
        errors.append("Misure richieste dai requisiti ASSENTI nel modello (o con nome diverso/corrotto): "
                      + "; ".join(missing))

    # 5. Nomi misura o formatString con '?' (tipico residuo di à/€ persi in scrittura ANSI)
    suspicious = sorted({m for m in model_measures if "?" in m})
    if suspicious:
        errors.append("Nomi misura con '?' (probabile corruzione di caratteri accentati): " + "; ".join(suspicious))
    if re.search(r'formatString:.*\?', tmdl):
        errors.append("formatString contenente '?' (probabile simbolo € corrotto): correggere i formati valuta.")

    if errors:
        print(f"NON CONFORME — {model_dir.name} non supera la validazione di fase 2:")
        for e in errors:
            print(f"  - {e}")
        print("\nAzione richiesta: correggere il modello via powerbi-modeling-mcp (mai editando i TMDL a mano) "
              "e rieseguire questo script fino a exit 0.")
        return 1

    print(f"CONFORME: {model_dir.name} — {len(set(tables))} tabelle, {partitions} partition, "
          f"{len(model_measures)} misure; copertura KPI dei requisiti completa.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
