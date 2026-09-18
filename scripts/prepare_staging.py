"""Script generico e parametrico per la fase 1.5 (ETL) del progetto.

Non contiene logica specifica di alcun report: le colonne, i formati attesi
e i mapping categorici vanno passati come configurazione al momento della
chiamata (vedi funzione `prepare_staging` e gli esempi in `__main__`).
"""
import re
from datetime import date

import pandas as pd
from pathlib import Path


def normalize_text(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().replace({"nan": "", "None": ""})


def normalize_date(series: pd.Series) -> pd.Series:
    s = normalize_text(series)
    return pd.to_datetime(s, errors="coerce", dayfirst=False, format="mixed")


def normalize_decimal(series: pd.Series) -> pd.Series:
    s = normalize_text(series)
    s = s.str.replace(r"[€$]|EUR|USD", "", regex=True).str.strip()
    def to_float(v: str):
        if v == "":
            return None
        if "," in v and "." in v:
            v = v.replace(".", "").replace(",", ".")
        elif "," in v:
            v = v.replace(",", ".")
        try:
            return float(v)
        except ValueError:
            return None
    return s.apply(to_float)


def normalize_boolean(series: pd.Series, true_values: set, false_values: set):
    s = normalize_text(series).str.lower()
    tv = {v.lower() for v in true_values}
    fv = {v.lower() for v in false_values}
    def to_bool(v: str):
        if v in tv:
            return True
        if v in fv:
            return False
        return None
    return s.apply(to_bool)


def normalize_categorical(series: pd.Series, mapping: dict) -> pd.Series:
    """mapping: {valore_originale_lowercase_trim: valore_canonico}.
    I valori non presenti nel mapping restano invariati (per non correggere
    silenziosamente casi non previsti/ambigui)."""
    s = normalize_text(series)
    lower_map = {k.lower(): v for k, v in mapping.items()}
    return s.apply(lambda v: lower_map.get(v.lower(), v))


TRANSFORMS = {
    "date": normalize_date,
    "decimal": normalize_decimal,
    "text": normalize_text,
}


def apply_column_config(df: pd.DataFrame, column_config: dict) -> tuple[pd.DataFrame, list[str]]:
    """column_config: {colonna: spec}, dove spec è una delle:
      - "date" | "decimal" | "text"
      - {"type": "boolean", "true": [...], "false": [...]}
      - {"type": "categorical", "mapping": {...}}
    Ritorna (df_trasformato, elenco_descrizioni_trasformazioni_applicate).
    """
    log = []
    for col, spec in column_config.items():
        if col not in df.columns:
            continue
        if isinstance(spec, str):
            df[col] = TRANSFORMS[spec](df[col])
            log.append(f"{col}: normalizzazione {spec}")
        elif spec.get("type") == "boolean":
            df[col] = normalize_boolean(df[col], set(spec["true"]), set(spec["false"]))
            log.append(f"{col}: valori misti -> booleano")
        elif spec.get("type") == "categorical":
            df[col] = normalize_categorical(df[col], spec["mapping"])
            log.append(f"{col}: case/typo -> valore canonico")
    return df, log


def read_source(source_path: str, sheet_name: str | None = None) -> pd.DataFrame:
    p = Path(source_path)
    if p.suffix.lower() in (".xlsx", ".xls"):
        return pd.read_excel(p, sheet_name=sheet_name, dtype=str, keep_default_na=False)
    return pd.read_csv(p, dtype=str, keep_default_na=False)


def write_etl_log_entry(
    out_dir: Path,
    entry_name: str,
    source_path: str,
    rows_in: int,
    rows_out: int,
    transform_log: list[str],
    requirement_refs: dict | None = None,
    anomalies: list[str] | None = None,
    log_filename: str = "etl-log.md",
) -> Path:
    """Scrive (o sostituisce) la sezione `## <entry_name>` in etl-log.md.

    requirement_refs: {colonna: requisito atomico dal "Mapping Requisiti →
    Schema Target"} — obbligatorio per ogni colonna trasformata, così il log
    traccia il *perché* oltre alla modifica tecnica.
    """
    requirement_refs = requirement_refs or {}
    lines = [
        f"## {entry_name}",
        f"- Data: {date.today().isoformat()}",
        f"- Sorgente: {source_path}",
        f"- Righe in ingresso / in uscita: {rows_in} / {rows_out}",
        "- Trasformazioni applicate:",
    ]
    if transform_log:
        for item in transform_log:
            col = item.split(":", 1)[0].strip()
            ref = requirement_refs.get(col, "non indicato — integrare a mano")
            lines.append(f"  - {item} (requisito di riferimento: {ref})")
    else:
        lines.append("  - Nessuna: dati già conformi allo schema atteso")
    lines.append("- Anomalie segnalate (non corrette automaticamente):")
    if anomalies:
        lines.extend(f"  - {a}" for a in anomalies)
    else:
        lines.append("  - Nessuna")
    section = "\n".join(lines) + "\n"

    log_path = out_dir / log_filename
    existing = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    if existing:
        # Sostituisce la sezione con lo stesso titolo, se presente (ri-esecuzioni)
        pattern = re.compile(
            rf"^## {re.escape(entry_name)}\n.*?(?=^## |\Z)", re.M | re.S
        )
        if pattern.search(existing):
            # sostituzione LETTERALE: il testo può contenere backslash (path Windows)
            # che re.sub interpreterebbe come escape del template
            existing = pattern.sub(lambda _: section, existing)
            log_path.write_text(existing, encoding="utf-8")
            return log_path
        if not existing.endswith("\n"):
            existing += "\n"
        existing += "\n"
    else:
        existing = "# Log Trasformazioni ETL\n\n"
    log_path.write_text(existing + section, encoding="utf-8")
    return log_path


def prepare_staging(
    source_path: str,
    project_name: str,
    column_config: dict,
    out_filename: str | None = None,
    sheet_name: str | None = None,
    staging_root: str | None = None,
    requirement_refs: dict | None = None,
    anomalies: list[str] | None = None,
) -> dict:
    """staging_root: default 'output/<project_name>/staging' (nome cartella
    condivisa con input/<project_name>/ e output/<project_name>/)."""
    p = Path(source_path)
    out_dir = Path(staging_root) if staging_root else Path("output") / project_name / "staging"
    out_dir.mkdir(parents=True, exist_ok=True)

    df = read_source(source_path, sheet_name=sheet_name)
    rows_in = len(df)

    df, transform_log = apply_column_config(df, column_config)

    rows_out = len(df)
    out_name = out_filename or (p.stem + ".csv")
    out_path = out_dir / out_name
    df.to_csv(out_path, index=False, encoding="utf-8")

    # Il log è parte dell'output obbligatorio della fase 1.5: viene scritto
    # insieme al CSV, non lasciato come passo separato dell'agente.
    log_path = write_etl_log_entry(
        out_dir,
        entry_name=out_name,
        source_path=source_path,
        rows_in=rows_in,
        rows_out=rows_out,
        transform_log=transform_log,
        requirement_refs=requirement_refs,
        anomalies=anomalies,
    )

    return {
        "path": str(out_path),
        "log_path": str(log_path),
        "rows_in": rows_in,
        "rows_out": rows_out,
        "transform_log": transform_log,
    }


USAGE = """\
Uso: python scripts/prepare_staging.py --config <file.json>

Il file JSON descrive il progetto (= nome cartella condivisa da input/<project>/
e output/<project>/) e i file da processare (la config la costruisce l'agente
`etl-resolver` a partire da output/<project>/requirements.md - questo messaggio
NON e' un errore ne' un motivo per saltare la fase 1.5):

{
  "project": "<Workdir>",
  "jobs": [
    {
      "source": "input/<Workdir>/<file>.csv|.xlsx",
      "column_config": {"<colonna>": "date|decimal|text",
                         "<colonna>": {"type": "categorical", "mapping": {...}}},
      "requirement_refs": {"<colonna>": "<requisito atomico dal Mapping>"},
      "anomalies": ["<anomalia segnalata>", "..."],
      "out_filename": null,
      "sheet_name": null
    }
  ]
}

Un file gia' conforme va comunque incluso come job (con "column_config": {}):
produce il CSV UTF-8 in output/<Workdir>/staging/ e la voce "Nessuna" in etl-log.md.
In alternativa, importa prepare_staging() da Python e passa gli stessi parametri.
"""


def run_config(config_path: str) -> list[dict]:
    import json

    cfg = json.loads(Path(config_path).read_text(encoding="utf-8"))
    results = []
    for job in cfg["jobs"]:
        results.append(
            prepare_staging(
                source_path=job["source"],
                project_name=cfg["project"],
                column_config=job.get("column_config", {}),
                out_filename=job.get("out_filename"),
                sheet_name=job.get("sheet_name"),
                staging_root=cfg.get("staging_root"),
                requirement_refs=job.get("requirement_refs"),
                anomalies=job.get("anomalies"),
            )
        )
    return results


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 3 and sys.argv[1] == "--config":
        for r in run_config(sys.argv[2]):
            print(r)
    else:
        print(USAGE)
        sys.exit(2)
