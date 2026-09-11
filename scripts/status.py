# Fotografia deterministica dello stato del progetto, fase per fase (sola lettura).
# Uso: python scripts/status.py [NomeProgetto]   (default: tutti i progetti in report/)
# Exit sempre 0: è uno strumento informativo, non un gate.
#
# Per ogni fase stampa l'evidenza sul filesystem e l'esito del gate eseguibile
# (validate_requirements / validate_model / validate_report). È la fonte da cui
# l'orchestrator ricostruisce il punto di ripartenza, al posto di dedurlo a mano.
# NOTA: le approvazioni esplicite dell'utente non sono tracciate su file — un gate
# a exit 0 rende la fase COMPLETABILE, non approvata: l'approvazione resta in chat.
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUIREMENTS = ROOT / "output/requirements.md"
SCRIPTS = ROOT / "scripts"


def run_gate(script, *args):
    """Esegue uno script di validazione e ritorna (exit_code, prime_righe_output)."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        capture_output=True, text=True, cwd=ROOT, encoding="utf-8", errors="replace",
    )
    lines = [l for l in (proc.stdout + proc.stderr).splitlines() if l.strip()]
    return proc.returncode, lines


def print_gate(label, code, lines, detail_lines=4):
    verdict = "OK (exit 0)" if code == 0 else f"FALLITO (exit {code})"
    print(f"  Gate {label}: {verdict}")
    if code != 0:
        for l in lines[:detail_lines]:
            print(f"    | {l}")
        if len(lines) > detail_lines:
            print(f"    | ... ({len(lines) - detail_lines} righe omesse)")


def requirements_report_name():
    if not REQUIREMENTS.exists():
        return None
    m = re.search(r"^- Nome report:\s*(.+)$",
                  REQUIREMENTS.read_text(encoding="utf-8", errors="replace"), re.MULTILINE)
    return m.group(1).strip() if m else None


def staging_dir_for(project, report_name):
    """La cartella staging può usare il nome PBIP o il 'Nome report' dei requisiti."""
    for candidate in (project, report_name):
        if candidate and (ROOT / "staging" / candidate).exists():
            return ROOT / "staging" / candidate
    return None


def phase_15_status(staging_dir):
    csvs = sorted(p.name for p in staging_dir.glob("*.csv"))
    log = staging_dir / "etl-log.md"
    if not csvs:
        return ["Cartella staging presente ma senza CSV: fase 1.5 NON conclusa."]
    out = [f"CSV in staging: {', '.join(csvs)}"]
    if not log.exists():
        out.append("etl-log.md ASSENTE: fase 1.5 NON conclusa (il log è output obbligatorio).")
        return out
    log_text = log.read_text(encoding="utf-8", errors="replace")
    sections = set(re.findall(r"^## (.+)$", log_text, re.MULTILINE))
    missing = [c for c in csvs if c not in sections]
    if missing:
        out.append("etl-log.md presente ma SENZA voce per: " + ", ".join(missing)
                   + " — fase 1.5 NON conclusa.")
    else:
        out.append("etl-log.md completo: una voce per ogni CSV — fase 1.5 conclusa (evidenza).")
    input_dir = ROOT / "input"
    if input_dir.exists():
        newest_input = max((p.stat().st_mtime for p in input_dir.iterdir() if p.is_file()), default=0)
        oldest_staging = min((p.stat().st_mtime for p in staging_dir.iterdir() if p.is_file()), default=0)
        if newest_input > oldest_staging:
            out.append("ATTENZIONE: file in input/ più recenti dello staging — valutare ri-esecuzione ETL.")
    return out


def project_status(project):
    print(f"=== Progetto: {project} ===")

    # Fase 1 — Requisiti
    print("Fase 1 — Requisiti (output/requirements.md)")
    if not REQUIREMENTS.exists():
        print("  output/requirements.md ASSENTE: fase 1 da avviare (requirements-analyst).")
        return
    report_name = requirements_report_name()
    print(f"  Nome report nei requisiti: {report_name or '(non trovato)'}")
    if report_name and report_name.casefold() != project.casefold():
        print(f"  NOTA: nome PBIP '{project}' diverso dal nome nei requisiti — verificare che "
              "requirements.md si riferisca a QUESTO report (regola 'nuovo report vs prosecuzione').")
    code, lines = run_gate("validate_requirements.py")
    print_gate("fase 1 (validate_requirements.py)", code, lines)

    # Fase 1.5 — ETL
    print("Fase 1.5 — Pulizia dati (staging/)")
    staging = staging_dir_for(project, report_name)
    if staging is None:
        print("  Nessuna cartella staging trovata: fase 1.5 non eseguita "
              "(da valutare se necessaria o skip dichiarato — vedi orchestrator).")
    else:
        print(f"  Cartella: {staging.relative_to(ROOT)}")
        for line in phase_15_status(staging):
            print(f"  {line}")

    # Fase 2 — Modello semantico
    print("Fase 2 — Modello semantico (report/<Progetto>.SemanticModel/)")
    model_dir = ROOT / "report" / f"{project}.SemanticModel"
    if not model_dir.exists():
        print("  Cartella modello ASSENTE: fase 2 da avviare (semantic-modeler).")
    else:
        code, lines = run_gate("validate_model.py", project)
        print_gate("fase 2 (validate_model.py)", code, lines)

    # Fase 3 — Layout report
    print("Fase 3 — Layout report (report/<Progetto>.Report/)")
    report_dir = ROOT / "report" / f"{project}.Report"
    if not (report_dir / "definition").exists():
        print("  Definizione PBIR ASSENTE: fase 3 da avviare (report-builder).")
    else:
        code, lines = run_gate("validate_report.py", project)
        print_gate("fase 3 (validate_report.py)", code, lines)

    # Fase 4 — Build
    print("Fase 4 — Build (.pbix da Power BI Desktop)")
    pbix = ROOT / "report" / f"{project}.pbix"
    print(f"  {pbix.relative_to(ROOT)}: {'presente' if pbix.exists() else 'assente (build in Desktop non ancora fatta)'}")


def main():
    requested = sys.argv[1] if len(sys.argv) > 1 else None
    projects = [requested] if requested else sorted(
        p.stem for p in (ROOT / "report").glob("*.pbip")
    ) if (ROOT / "report").exists() else []
    if not projects:
        print("Nessun progetto PBIP in report/ (il nome progetto viene deciso in fase 1)."
              if not requested else f"Progetto '{requested}' non trovato in report/.")
        if REQUIREMENTS.exists():
            print(f"output/requirements.md esiste (Nome report: {requirements_report_name() or '?'}) "
                  "— fase 1 in corso o conclusa, fasi successive non avviate.")
        return 0
    print("Le approvazioni esplicite dell'utente NON sono tracciate su file: "
          "un gate OK rende la fase completabile, l'approvazione va confermata in chat.\n")
    for project in projects:
        project_status(project)
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
