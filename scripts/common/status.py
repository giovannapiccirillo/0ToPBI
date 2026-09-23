# Fotografia deterministica dello stato del progetto, fase per fase (sola lettura).
# Uso: python scripts/status.py [Workdir]   (default: tutte le cartelle in output/)
# Exit sempre 0: è uno strumento informativo, non un gate.
#
# Ogni progetto vive su due nomi distinti, potenzialmente diversi:
#   - Workdir: cartella condivisa da input/<Workdir>/ e output/<Workdir>/ (nome libero)
#   - NomeProgetto PBIP: report/<NomeProgetto>.pbip / .SemanticModel / .Report,
#     letto dal campo "Nome report:" di output/<Workdir>/requirements.md
#
# Per ogni fase stampa l'evidenza sul filesystem e l'esito del gate eseguibile
# (validate_requirements / validate_data_analysis / validate_model / validate_report).
# Fasi: 1 Requisiti, 2 Analisi Dati, 3 Pulizia Dati (ETL), 4 Modello Semantico,
# 5 Layout Report, 6 Build + Verifica.
# È la fonte da cui l'orchestrator ricostruisce il punto di ripartenza, al posto di dedurlo a mano.
# NOTA: le approvazioni esplicite dell'utente non sono tracciate su file — un gate
# a exit 0 rende la fase COMPLETABILE, non approvata: l'approvazione resta in chat.
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = ROOT / "output"
SCRIPTS = ROOT / "scripts"

sys.path.insert(0, str(SCRIPTS / "common"))
from env_preset import load_env  # noqa: E402

# Ogni gate vive nella sottocartella scripts/ della propria fase.
GATE_PATHS = {
    "validate_requirements.py": SCRIPTS / "01_requisiti" / "validate_requirements.py",
    "validate_data_analysis.py": SCRIPTS / "02_analisi_dati" / "validate_data_analysis.py",
    "validate_model.py": SCRIPTS / "04_modello" / "validate_model.py",
    "validate_report.py": SCRIPTS / "05_report" / "validate_report.py",
}


def run_gate(script, *args):
    """Esegue uno script di validazione e ritorna (exit_code, prime_righe_output)."""
    proc = subprocess.run(
        [sys.executable, str(GATE_PATHS[script]), *args],
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


def requirements_report_name(requirements_path):
    if not requirements_path.exists():
        return None
    m = re.search(r"^- Nome report:\s*(.+)$",
                  requirements_path.read_text(encoding="utf-8", errors="replace"), re.MULTILINE)
    return m.group(1).strip() if m else None


def phase_3_status(staging_dir):
    csvs = sorted(p.name for p in staging_dir.glob("*.csv"))
    log = staging_dir / "etl-log.md"
    if not csvs:
        return ["Cartella staging presente ma senza CSV: fase 3 NON conclusa."]
    out = [f"CSV in staging: {', '.join(csvs)}"]
    if not log.exists():
        out.append("etl-log.md ASSENTE: fase 3 NON conclusa (il log è output obbligatorio).")
        return out
    log_text = log.read_text(encoding="utf-8", errors="replace")
    sections = set(re.findall(r"^## (.+)$", log_text, re.MULTILINE))
    missing = [c for c in csvs if c not in sections]
    if missing:
        out.append("etl-log.md presente ma SENZA voce per: " + ", ".join(missing)
                   + " — fase 3 NON conclusa.")
    else:
        out.append("etl-log.md completo: una voce per ogni CSV — fase 3 conclusa (evidenza).")
    return out


def project_status(workdir):
    print(f"=== Progetto (workdir): {workdir} ===")
    output_dir = OUTPUT_DIR / workdir
    requirements = output_dir / "requirements.md"

    # Fase 1 — Requisiti
    print(f"Fase 1 — Requisiti (output/{workdir}/requirements.md)")
    if not requirements.exists():
        print(f"  output/{workdir}/requirements.md ASSENTE: fase 1 da avviare (requirements-analyst).")
        return
    report_name = requirements_report_name(requirements)
    print(f"  Nome report (PBIP) nei requisiti: {report_name or '(non trovato)'}")
    code, lines = run_gate("validate_requirements.py", workdir)
    print_gate("fase 1 (validate_requirements.py)", code, lines)

    project = report_name  # nome progetto PBIP: report/<project>.pbip / .SemanticModel / .Report

    # Fase 2 — Analisi Dati
    print(f"Fase 2 — Analisi dati (output/{workdir}/data-analysis.md)")
    data_analysis = output_dir / "data-analysis.md"
    if not data_analysis.exists():
        print(f"  output/{workdir}/data-analysis.md ASSENTE: fase 2 da avviare (data-analyst).")
    else:
        code, lines = run_gate("validate_data_analysis.py", workdir)
        print_gate("fase 2 (validate_data_analysis.py)", code, lines)

    # Fase 3 — ETL
    print(f"Fase 3 — Pulizia dati (output/{workdir}/staging/)")
    staging = output_dir / "staging"
    if not staging.exists():
        print("  Nessuna cartella staging trovata: fase 3 non eseguita "
              "(da valutare se necessaria, secondo la sintesi di data-analysis.md, o skip dichiarato — vedi orchestrator).")
    else:
        print(f"  Cartella: {staging.relative_to(ROOT)}")
        for line in phase_3_status(staging):
            print(f"  {line}")
        input_dir = ROOT / "input" / workdir
        if input_dir.exists():
            newest_input = max((p.stat().st_mtime for p in input_dir.iterdir() if p.is_file()), default=0)
            oldest_staging = min((p.stat().st_mtime for p in staging.iterdir() if p.is_file()), default=0)
            if newest_input > oldest_staging:
                print(f"  ATTENZIONE: file in input/{workdir}/ più recenti dello staging — valutare ri-esecuzione ETL.")

    if not project:
        print("Fase 4/5/6: nome progetto PBIP non trovato in requirements.md — impossibile proseguire.")
        return

    # Fase 4 — Modello semantico
    print(f"Fase 4 — Modello semantico (report/{project}.SemanticModel/)")
    model_dir = ROOT / "report" / f"{project}.SemanticModel"
    if not model_dir.exists():
        print("  Cartella modello ASSENTE: fase 4 da avviare (semantic-modeler).")
    else:
        code, lines = run_gate("validate_model.py", workdir, project)
        print_gate("fase 4 (validate_model.py)", code, lines)

    # Fase 5 — Layout report
    print(f"Fase 5 — Layout report (report/{project}.Report/)")
    report_dir = ROOT / "report" / f"{project}.Report"
    if not (report_dir / "definition").exists():
        print("  Definizione PBIR ASSENTE: fase 5 da avviare (report-builder).")
    else:
        code, lines = run_gate("validate_report.py", workdir, project)
        print_gate("fase 5 (validate_report.py)", code, lines)

    # Fase 6 — Build
    print("Fase 6 — Build (.pbix da Power BI Desktop)")
    pbix = ROOT / "report" / f"{project}.pbix"
    print(f"  {pbix.relative_to(ROOT)}: {'presente' if pbix.exists() else 'assente (build in Desktop non ancora fatta)'}")


def main():
    requested = sys.argv[1] if len(sys.argv) > 1 else None
    workdirs = [requested] if requested else sorted(
        p.name for p in OUTPUT_DIR.iterdir() if p.is_dir()
    ) if OUTPUT_DIR.exists() else []
    if not workdirs:
        print("Nessuna cartella progetto in output/ (il nome cartella si crea in fase 1)."
              if not requested else f"Cartella 'output/{requested}/' non trovata.")
        preset = load_env()
        if preset:
            print("Preset trovato in .env (default silenzioso, sovrascrivibile in chat): "
                  + ", ".join(f"{k}={v}" for k, v in preset.items()))
        return 0
    print("Le approvazioni esplicite dell'utente NON sono tracciate su file: "
          "un gate OK rende la fase completabile, l'approvazione va confermata in chat.\n")
    for workdir in workdirs:
        project_status(workdir)
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
