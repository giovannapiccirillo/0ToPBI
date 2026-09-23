# Convertitore generico dei file binari in input/<Workdir>/ — nessuno script ad hoc per report.
# Uso:
#   python scripts/convert_input.py <Workdir>                # converte tutti i .docx/.xlsx in input/<Workdir>/
#   python scripts/convert_input.py <Workdir> doc.docx        # converte solo i file indicati (nomi relativi a input/<Workdir>/)
#   python scripts/convert_input.py <Workdir> --force         # riconverte anche se il convertito è aggiornato
#
# <Workdir> è il nome libero della sottocartella di progetto in input/ (es. "demo"),
# scelto dall'utente indipendentemente dal nome del progetto PBIP.
#
# Regole (dalla skill powerbi-requirements-gathering):
# - il convertito va accanto all'originale: <nome>.md per i .docx, <nome>.csv per gli .xlsx
#   (un CSV per foglio, <nome>__<foglio>.csv, se il workbook ha più fogli)
# - se il convertito esiste ed è più recente dell'originale, si riusa (skip) salvo --force
# - l'originale non viene mai modificato; output sempre UTF-8
# Exit 0 = ok (anche se tutto era già convertito); exit 1 = almeno una conversione fallita; exit 2 = uso errato.
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def docx_to_markdown(src: Path) -> str:
    with zipfile.ZipFile(src) as z:
        xml = z.read("word/document.xml")
    body = ET.fromstring(xml).find(f"{W}body")
    out = []

    def para_text(p):
        return "".join(t.text or "" for t in p.iter(f"{W}t"))

    for el in body:
        if el.tag == f"{W}p":
            text = para_text(el).strip()
            out.append(text)
        elif el.tag == f"{W}tbl":
            rows = []
            for tr in el.iter(f"{W}tr"):
                cells = [" ".join(para_text(p).strip() for p in tc.iter(f"{W}p")).strip()
                         for tc in tr.findall(f"{W}tc")]
                rows.append("| " + " | ".join(cells) + " |")
            if rows:
                header_sep = "|" + "---|" * (rows[0].count("|") - 1)
                out.append(rows[0])
                out.append(header_sep)
                out.extend(rows[1:])
                out.append("")
    text = "\n".join(out)
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"


def xlsx_to_csv(src: Path, force: bool):
    """Ritorna lista di (percorso_csv, stato)."""
    import csv
    try:
        import openpyxl
        wb = openpyxl.load_workbook(src, data_only=True, read_only=True)
        # righe materializzate subito: il workbook read_only tiene il file
        # aperto (lock su Windows) finché non viene chiuso
        sheets = {ws.title: [tuple(r) for r in ws.iter_rows(values_only=True)]
                  for ws in wb.worksheets}
        wb.close()
    except ImportError:
        import pandas as pd
        frames = pd.read_excel(src, sheet_name=None, dtype=str)
        sheets = {name: ([tuple(df.columns)] + [tuple(r) for r in df.itertuples(index=False)])
                  for name, df in frames.items()}
    results = []
    multi = len(sheets) > 1
    for name, rows in sheets.items():
        dest = src.with_name(f"{src.stem}__{name}.csv" if multi else f"{src.stem}.csv")
        if not force and dest.exists() and dest.stat().st_mtime >= src.stat().st_mtime:
            results.append((dest, "riusato (già aggiornato)"))
            continue
        with open(dest, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for row in rows:
                writer.writerow(["" if v is None else v for v in row])
        results.append((dest, "convertito"))
    return results


def convert_one(src: Path, force: bool):
    suffix = src.suffix.lower()
    if suffix == ".docx":
        dest = src.with_suffix(".md")
        if not force and dest.exists() and dest.stat().st_mtime >= src.stat().st_mtime:
            return [(dest, "riusato (già aggiornato)")]
        dest.write_text(docx_to_markdown(src), encoding="utf-8")
        return [(dest, "convertito")]
    if suffix in (".xlsx", ".xls"):
        return xlsx_to_csv(src, force)
    return [(src, "ignorato (estensione non gestita)")]


def main():
    argv = sys.argv[1:]
    force = "--force" in argv
    positional = [a for a in argv if a != "--force"]
    if not positional:
        print("Uso: python scripts/convert_input.py <Workdir> [file...] [--force]")
        return 2
    workdir, *names = positional
    input_dir = ROOT / "input" / workdir

    targets = [input_dir / n for n in names] if names else sorted(
        p for p in input_dir.iterdir() if p.suffix.lower() in (".docx", ".xlsx", ".xls")
    ) if input_dir.exists() else []

    if not targets:
        print(f"Nessun file .docx/.xlsx da convertire in input/{workdir}/.")
        return 0

    failed = False
    for src in targets:
        if not src.exists():
            print(f"ERRORE: {src} non esiste")
            failed = True
            continue
        try:
            for dest, status in convert_one(src, force):
                print(f"{src.name} -> {dest.name}: {status}")
        except Exception as e:
            print(f"ERRORE su {src.name}: {e}")
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
