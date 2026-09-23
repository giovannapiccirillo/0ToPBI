# Valida output/<Workdir>/data-analysis.md contro il template ufficiale della fase 2 (Analisi Dati).
# Uso: python scripts/validate_data_analysis.py <Workdir>
# Exit 0 = CONFORME; exit 1 = NON CONFORME (errori elencati); exit 2 = file mancanti/uso errato.
# Gate obbligatorio: la fase 2 (Analisi Dati) non è conclusa finché questo script non esce con 0.
#
# <Workdir> è il nome libero della sottocartella di progetto condivisa da
# input/<Workdir>/ e output/<Workdir>/.
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
TEMPLATE = ROOT / ".github/skills/data-analysis/assets/data-analysis-template.md"

TABLE_HEADING_RE = re.compile(r"^### (.+)$", re.MULTILINE)
REQUIRED_TABLE_FIELDS = [
    "Righe:", "Colonne:", "Chiave candidata:", "Qualità dati:",
    "Anomalie di dominio:", "Metadati:",
]


def top_headings(text):
    """Solo # e ## (non ### delle singole tabelle, che sono ripetibili)."""
    return [l.rstrip() for l in text.splitlines() if re.match(r"^#{1,2} ", l)]


def section_body(text, heading, level=2):
    lines = text.splitlines()
    marker = "#" * level + " "
    try:
        start = next(i for i, l in enumerate(lines) if l.rstrip() == heading)
    except StopIteration:
        return None
    body = []
    for l in lines[start + 1:]:
        if l.startswith(marker):
            break
        body.append(l)
    return "\n".join(body)


def main():
    if len(sys.argv) != 2:
        print("Uso: python scripts/validate_data_analysis.py <Workdir>")
        return 2
    workdir = sys.argv[1]
    output = ROOT / "output" / workdir / "data-analysis.md"

    if not TEMPLATE.exists():
        print(f"ERRORE: template non trovato: {TEMPLATE}")
        return 2
    if not output.exists():
        print(f"NON CONFORME: {output} non esiste")
        return 2

    template = TEMPLATE.read_text(encoding="utf-8")
    output_text = output.read_text(encoding="utf-8", errors="replace")
    errors = []

    # 1. Encoding integro
    if "Ã" in output_text or "�" in output_text:
        errors.append(
            "Encoding corrotto: trovati caratteri mojibake. "
            "Rigenerare con copia binaria (Copy-Item) e edit UTF-8."
        )

    # 2. Intestazioni di primo/secondo livello identiche al template (le ### tabella sono ripetibili, escluse)
    t_heads, o_heads = top_headings(template), top_headings(output_text)
    if o_heads != t_heads:
        missing = [h for h in t_heads if h not in o_heads]
        extra = [h for h in o_heads if h not in t_heads]
        if missing:
            errors.append("Intestazioni del template ASSENTI nel file: " + "; ".join(missing))
        if extra:
            errors.append(
                "Intestazioni INVENTATE non previste dal template: " + "; ".join(extra)
            )
        if not missing and not extra:
            errors.append("Intestazioni presenti ma in ORDINE diverso dal template.")

    # 3. Nessun segnaposto del template sopravvissuto
    placeholders = [l for l in output_text.splitlines() if re.match(r"^\s*<.+>\s*$", l)]
    if placeholders:
        errors.append(
            "Segnaposto del template non compilati: " + "; ".join(p.strip() for p in placeholders)
        )

    # 4. Sorgente dichiarata
    m = re.search(r"^- Tipo:\s*(.+)$", output_text, re.MULTILINE)
    if m is None or not m.group(1).strip():
        errors.append("Campo '- Tipo:' (Sorgente) vuoto o assente.")
    elif m.group(1).strip() not in ("Locale", "Fabric Lakehouse"):
        errors.append(
            f"Campo '- Tipo:' con valore non ammesso ('{m.group(1).strip()}'): "
            "atteso 'Locale' o 'Fabric Lakehouse'."
        )

    # 5. Almeno una tabella analizzata, con tutti i campi richiesti popolati
    table_titles = TABLE_HEADING_RE.findall(output_text)
    if not table_titles:
        errors.append(
            "Nessuna sottosezione '### <Nome tabella/file>' trovata sotto "
            "'## Tabelle Analizzate': l'analisi deve coprire almeno una tabella."
        )
    for title in table_titles:
        body = section_body(output_text, f"### {title}", level=3)
        if body is None:
            continue
        for field in REQUIRED_TABLE_FIELDS:
            fm = re.search(rf"^- {re.escape(field)}(.*)$", body, re.MULTILINE)
            if fm is None:
                errors.append(f"Tabella '{title}': campo '{field}' assente.")
            elif not fm.group(1).strip():
                errors.append(f"Tabella '{title}': campo '{field}' vuoto.")

    # 6. Sintesi per fase successiva compilata
    sintesi = section_body(output_text, "## Sintesi per Fase Successiva")
    if sintesi is not None:
        for field in ("Correzioni da proporre a etl-resolver:", "Punti di attenzione per semantic-modeler:"):
            fm = re.search(rf"^- {re.escape(field)}(.*)$", sintesi, re.MULTILINE)
            if fm is None:
                errors.append(f"Sezione 'Sintesi per Fase Successiva': campo '{field}' assente.")
            elif not fm.group(1).strip():
                errors.append(f"Sezione 'Sintesi per Fase Successiva': campo '{field}' vuoto.")

    if errors:
        print(f"NON CONFORME — {output.relative_to(ROOT)} non rispetta il template:")
        for e in errors:
            print(f"  - {e}")
        print("\nAzione richiesta: cancellare il file, ricopiare il template "
              "(.github/skills/data-analysis/assets/data-analysis-template.md) "
              "con copia binaria e compilare solo il testo sotto le intestazioni.")
        return 1

    print(f"CONFORME: {output.relative_to(ROOT)} rispetta il template "
          f"({len(table_titles)} tabella/e analizzata/e)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
