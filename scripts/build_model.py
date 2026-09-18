# Genera la definizione TMDL del modello semantico da una spec dichiarativa.
# Gli agenti NON scrivono mai TMDL a mano: compilano output/<Workdir>/model.yaml e lanciano questo script.
#
# Uso: python scripts/build_model.py <Workdir> [path/spec.yaml]
#   - legge la spec (default: output/<Workdir>/model.yaml)
#   - legge le relazioni approvate da output/<Workdir>/relationships.yaml (se esiste; altrimenti spec.relationships)
#   - scrive report/<project>.SemanticModel/definition/ : database.tmdl, model.tmdl,
#     tables/*.tmdl, relationships.tmdl (+ cultures/<culture>.tmdl se mancante)
#   - esegue automaticamente scripts/validate_model.py come verifica finale
#
# Formato spec (YAML):
#   project: Prova                    # cartella report/<project>.SemanticModel deve esistere
#   culture: it-IT                    # default it-IT
#   tables:
#     - name: Vendite
#       role: fact                    # informativo
#       hidden: false                 # opzionale, tabella nascosta
#       dataCategory: Time            # opzionale (tipico per il calendario)
#       source:
#         type: csv                   # csv | calendar
#         path: output/<Workdir>/staging/vendite.csv  # per csv (relativo alla root del repo)
#         start: 2024-01-01           # per calendar
#         end: 2025-12-31             # per calendar
#       columns:                      # per calendar usare le 5 colonne standard:
#         - name: OrderID             #   Date, Anno, "Mese Numero", Mese, AnnoMese
#           dataType: string          # string | dateTime | double | int64 | boolean
#           hidden: true              # opzionale
#           isKey: true               # opzionale
#           sortBy: "Mese Numero"     # opzionale, nome colonna di ordinamento
#       measures:
#         - name: "Fatturato Totale"
#           expression: "SUMX ( Vendite, ... )"
#           formatString: "#,0.00 €"
#           displayFolder: "Revenue"  # opzionale
#       hierarchies:
#         - name: "Anno - Mese"
#           levels:
#             - { name: Anno, column: Anno }
#             - { name: Mese, column: Mese }
#   relationships:                    # usato SOLO se output/<Workdir>/relationships.yaml non esiste
#     - { from_table: Vendite, from_column: ProductID, to_table: Prodotti, to_column: ProductID }
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

M_TYPES = {
    "string": "type text",
    "dateTime": "type datetime",
    "double": "type number",
    "int64": "Int64.Type",
    "boolean": "type logical",
}


def q(name: str) -> str:
    """Quota un nome TMDL solo se necessario (spazi o caratteri speciali)."""
    return f"'{name}'" if any(c in name for c in " %.-+/()&,") else name


def render_column(col: dict) -> list[str]:
    out = [f"\tcolumn {q(col['name'])}"]
    out.append(f"\t\tdataType: {col['dataType']}")
    if col.get("hidden"):
        out.append("\t\tisHidden")
    if col.get("isKey"):
        out.append("\t\tisKey")
    out.append("\t\tsummarizeBy: none")
    out.append(f"\t\tsourceColumn: {col['name']}")
    if col.get("sortBy"):
        out.append(f"\t\tsortByColumn: {q(col['sortBy'])}")
    out.append("")
    return out


def render_measure(m: dict) -> list[str]:
    out = [f"\tmeasure {q(m['name'])} = {m['expression']}"]
    if m.get("formatString"):
        out.append(f"\t\tformatString: {m['formatString']}")
    if m.get("displayFolder"):
        out.append(f"\t\tdisplayFolder: {m['displayFolder']}")
    out.append("")
    return out


def render_hierarchy(h: dict) -> list[str]:
    out = [f"\thierarchy {q(h['name'])}", ""]
    for level in h["levels"]:
        out.append(f"\t\tlevel {q(level['name'])}")
        out.append(f"\t\t\tcolumn: {q(level['column'])}")
        out.append("")
    return out


def m_csv_source(table: dict) -> list[str]:
    path = (ROOT / table["source"]["path"]).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Sorgente CSV non trovata: {path}")
    cols = table["columns"]
    type_pairs = ", ".join(
        f'{{"{c["name"]}", {M_TYPES[c["dataType"]]}}}' for c in cols
    )
    return [
        "\t\t\t\tlet",
        f'\t\t\t\t\tSource = Csv.Document(File.Contents("{path}"),'
        f"[Delimiter=\",\", Columns={len(cols)}, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),",
        "\t\t\t\t\tPromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),",
        f"\t\t\t\t\tChangedType = Table.TransformColumnTypes(PromotedHeaders,{{{type_pairs}}})",
        "\t\t\t\tin",
        "\t\t\t\t\tChangedType",
    ]


def m_calendar_source(table: dict) -> list[str]:
    src = table["source"]
    sy, sm, sd = str(src["start"]).split("-")
    ey, em, ed = str(src["end"]).split("-")
    return [
        "\t\t\t\tlet",
        f"\t\t\t\t\tMinDate = #date({int(sy)}, {int(sm)}, {int(sd)}),",
        f"\t\t\t\t\tMaxDate = #date({int(ey)}, {int(em)}, {int(ed)}),",
        "\t\t\t\t\tDates = List.Dates(MinDate, Duration.Days(MaxDate - MinDate) + 1, #duration(1, 0, 0, 0)),",
        '\t\t\t\t\tToTable = Table.FromList(Dates, Splitter.SplitByNothing(), {"Date"}),',
        '\t\t\t\t\tTypedDate = Table.TransformColumnTypes(ToTable, {{"Date", type datetime}}),',
        '\t\t\t\t\tAddAnno = Table.AddColumn(TypedDate, "Anno", each Date.Year([Date]), Int64.Type),',
        '\t\t\t\t\tAddMeseNumero = Table.AddColumn(AddAnno, "Mese Numero", each Date.Month([Date]), Int64.Type),',
        '\t\t\t\t\tAddMese = Table.AddColumn(AddMeseNumero, "Mese", each Date.MonthName([Date]), type text),',
        '\t\t\t\t\tAddAnnoMese = Table.AddColumn(AddMese, "AnnoMese", each Text.From([Anno]) & "-" & Text.PadStart(Text.From([Mese Numero]), 2, "0"), type text)',
        "\t\t\t\tin",
        "\t\t\t\t\tAddAnnoMese",
    ]


def render_table(table: dict) -> str:
    out = [f"table {q(table['name'])}"]
    if table.get("hidden"):
        out.append("\tisHidden")
    if table.get("dataCategory"):
        out.append(f"\tdataCategory: {table['dataCategory']}")
    out.append("")
    for col in table.get("columns", []):
        out.extend(render_column(col))
    for m in table.get("measures", []):
        out.extend(render_measure(m))
    for h in table.get("hierarchies", []):
        out.extend(render_hierarchy(h))
    src_type = table["source"]["type"]
    out.append(f"\tpartition {q(table['name'])} = m")
    out.append("\t\tmode: import")
    out.append("\t\tsource =")
    out.extend(m_csv_source(table) if src_type == "csv" else m_calendar_source(table))
    out.append("")
    return "\n".join(out)


def load_relationships(spec: dict, relationships_yaml: Path) -> list[dict]:
    if relationships_yaml.exists():
        data = yaml.safe_load(relationships_yaml.read_text(encoding="utf-8"))
        return data.get("relationships", [])
    return spec.get("relationships", [])


def render_relationships(rels: list[dict]) -> str:
    out = []
    for r in rels:
        name = f"{r['from_table']}{r['to_table']}"
        out.append(f"relationship {name}")
        out.append(f"\tfromColumn: {r['from_table']}.{r['from_column']}")
        out.append(f"\ttoColumn: {r['to_table']}.{r['to_column']}")
        if r.get("cardinality") and r["cardinality"] != "manyToOne":
            out.append(f"\tcardinality: {r['cardinality']}")
        if r.get("cross_filter") == "both":
            out.append("\tcrossFilteringBehavior: bothDirections")
        if r.get("is_active") is False:
            out.append("\tisActive: false")
        out.append("")
    return "\n".join(out)


def main():
    args = sys.argv[1:]
    if not args:
        print("Uso: python scripts/build_model.py <Workdir> [path/spec.yaml]")
        return 2
    workdir = args[0]
    spec_path = Path(args[1]) if len(args) > 1 else ROOT / "output" / workdir / "model.yaml"
    relationships_yaml = ROOT / "output" / workdir / "relationships.yaml"
    if not spec_path.exists():
        print(f"ERRORE: spec non trovata: {spec_path}")
        return 2
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))

    project = spec["project"]
    culture = spec.get("culture", "it-IT")
    model_dir = ROOT / "report" / f"{project}.SemanticModel"
    if not model_dir.exists():
        print(f"ERRORE: {model_dir} non esiste — creare prima lo scaffold PBIP (o correggere 'project').")
        return 2
    definition = model_dir / "definition"
    (definition / "tables").mkdir(parents=True, exist_ok=True)
    (definition / "cultures").mkdir(parents=True, exist_ok=True)

    # database.tmdl
    (definition / "database.tmdl").write_text("database\n\tcompatibilityLevel: 1702\n", encoding="utf-8")

    # model.tmdl
    table_names = [t["name"] for t in spec["tables"]]
    query_order = ",".join(f'"{n}"' for n in table_names)
    model_lines = [
        "model Model",
        f"\tculture: {culture}",
        "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
        f"\tsourceQueryCulture: {culture}",
        "\tdataAccessOptions",
        "\t\tlegacyRedirects",
        "\t\treturnErrorValuesAsNull",
        "",
        f"\tannotation PBI_QueryOrder = [{query_order}]",
        "",
    ]
    model_lines += [f"ref table {q(n)}" for n in table_names]
    model_lines += ["", f"ref cultureInfo {culture}", ""]
    (definition / "model.tmdl").write_text("\n".join(model_lines), encoding="utf-8")

    # cultures/<culture>.tmdl (solo se mancante: non sovrascrivere metadati linguistici esistenti)
    culture_file = definition / "cultures" / f"{culture}.tmdl"
    if not culture_file.exists():
        culture_file.write_text(f"cultureInfo {culture}\n", encoding="utf-8")

    # tables/*.tmdl (rimuove i file di tabelle non più presenti nella spec)
    for old in (definition / "tables").glob("*.tmdl"):
        old.unlink()
    for table in spec["tables"]:
        (definition / "tables" / f"{table['name']}.tmdl").write_text(
            render_table(table), encoding="utf-8"
        )

    # relationships.tmdl
    rels = load_relationships(spec, relationships_yaml)
    rel_file = definition / "relationships.tmdl"
    if rels:
        rel_file.write_text(render_relationships(rels), encoding="utf-8")
    elif rel_file.exists():
        rel_file.unlink()

    src = str(relationships_yaml.relative_to(ROOT)) if relationships_yaml.exists() else "spec"
    print(f"Generato {definition} — {len(table_names)} tabelle, {len(rels)} relazioni (da {src}).")

    # Verifica finale con il gate di fase 2
    import subprocess
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_model.py"), workdir, project],
        cwd=ROOT,
    )
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
