# Valida output/requirements.md contro il template ufficiale della fase 1.
# Uso: python scripts/validate_requirements.py
# Exit 0 = CONFORME; exit 1 = NON CONFORME (errori elencati); exit 2 = file mancanti.
# Gate obbligatorio: la fase 1 non è conclusa finché questo script non esce con 0.
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / ".github/skills/powerbi-requirements-gathering/assets/requirements-template.md"
OUTPUT = ROOT / "output/requirements.md"
INPUT_DIR = ROOT / "input"

MAPPING_HEADING = "## Mapping Requisiti → Schema Target"


def headings(text):
    return [l.rstrip() for l in text.splitlines() if re.match(r"^#{1,3} ", l)]


def section_body(text, heading):
    lines = text.splitlines()
    try:
        start = next(i for i, l in enumerate(lines) if l.rstrip() == heading)
    except StopIteration:
        return None
    body = []
    for l in lines[start + 1:]:
        if re.match(r"^## ", l):
            break
        body.append(l)
    return "\n".join(body)


def main():
    if not TEMPLATE.exists():
        print(f"ERRORE: template non trovato: {TEMPLATE}")
        return 2
    if not OUTPUT.exists():
        print(f"NON CONFORME: {OUTPUT} non esiste")
        return 2

    template = TEMPLATE.read_text(encoding="utf-8")
    output = OUTPUT.read_text(encoding="utf-8", errors="replace")
    errors = []

    # 1. Encoding integro (niente mojibake da Set-Content/ANSI)
    if "Ã" in output or "�" in output:
        errors.append(
            "Encoding corrotto: trovati caratteri mojibake (es. 'GranularitÃ'). "
            "Rigenerare con copia binaria (Copy-Item) e edit UTF-8."
        )

    # 2. Intestazioni identiche al template (stesso testo, stesso ordine, nessuna in più o in meno)
    t_heads, o_heads = headings(template), headings(output)
    if o_heads != t_heads:
        missing = [h for h in t_heads if h not in o_heads]
        extra = [h for h in o_heads if h not in t_heads]
        if missing:
            errors.append("Intestazioni del template ASSENTI nel file: " + "; ".join(missing))
        if extra:
            errors.append(
                "Intestazioni INVENTATE non previste dal template (es. numerazioni proprie): "
                + "; ".join(extra)
            )
        if not missing and not extra:
            errors.append("Intestazioni presenti ma in ORDINE diverso dal template.")

    # 3. Nessun segnaposto del template sopravvissuto (sezioni non compilate)
    placeholders = [l for l in output.splitlines() if re.match(r"^\s*<.+>\s*$", l)]
    if placeholders:
        errors.append(
            "Segnaposto del template non compilati: " + "; ".join(p.strip() for p in placeholders)
        )

    # 4. Campi chiave valorizzati
    for field in ("Nome report:", "Tipo di DB:"):
        m = re.search(rf"^- {re.escape(field)}(.*)$", output, re.MULTILINE)
        if m is not None and not m.group(1).strip():
            errors.append(f"Campo '{field}' vuoto.")
    if re.search(r"^- Modalità di connessione: Import \| DirectQuery\s*$", output, re.MULTILINE):
        errors.append("Campo 'Modalità di connessione:' lasciato al valore segnaposto 'Import | DirectQuery'.")

    # 4-bis. Formato atomico dei KPI: una riga per KPI, con marcatura esistente/nuova misura
    kpi_body = section_body(output, "## KPI e Metriche Chiave")
    if kpi_body is not None and not re.search(
        r"^\s*- .+? — (?:serve nuova misura|misura esistente)", kpi_body, re.MULTILINE
    ):
        errors.append(
            "Sezione 'KPI e Metriche Chiave' senza righe KPI atomiche: ogni KPI va su una riga propria "
            "nel formato '- <Nome KPI> — serve nuova misura: <base di calcolo>' oppure "
            "'- <Nome KPI> — misura esistente: <nome>' (niente elenchi schiacciati su una riga sola)."
        )

    # 5. Mapping obbligatorio se in input/ ci sono file tabellari
    tabular = []
    if INPUT_DIR.exists():
        tabular = sorted(
            p.name for p in INPUT_DIR.iterdir() if p.suffix.lower() in (".csv", ".xlsx")
        )
    body = section_body(output, MAPPING_HEADING)
    if body is not None and tabular:
        if re.search(r"non applicabile", body, re.IGNORECASE):
            errors.append(
                f"Sezione Mapping dichiarata 'Non applicabile' ma in input/ ci sono file tabellari "
                f"({', '.join(tabular)}): lo schema si ricava dalle intestazioni, il mapping va compilato."
            )
        data_rows = [
            l for l in body.splitlines()
            if l.startswith("|") and not re.match(r"^\|[\s\-|]+\|$", l)
            and "Requisito atomico" not in l
        ]
        if not data_rows:
            errors.append(
                f"Sezione Mapping senza righe di requisiti atomici, ma in input/ ci sono file tabellari "
                f"({', '.join(tabular)}): serve una riga per requisito con Tabella.Colonna reale e verifica di allineamento."
            )

    if errors:
        print("NON CONFORME — output/requirements.md non rispetta il template:")
        for e in errors:
            print(f"  - {e}")
        print("\nAzione richiesta: cancellare il file, ricopiare il template "
              "(.github/skills/powerbi-requirements-gathering/assets/requirements-template.md) "
              "con copia binaria e compilare solo il testo sotto le intestazioni.")
        return 1

    print("CONFORME: output/requirements.md rispetta il template"
          + (f" (mapping verificato su: {', '.join(tabular)})" if tabular else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
