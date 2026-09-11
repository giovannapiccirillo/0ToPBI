# Relationship Proposal — `output/relationships.yaml`

Schema and rules for the relationship proposal file produced during the
"Propose Relationships from Requirements" workflow. The file is a **design
artifact** (a contract between the proposal step and the model build step),
not a TMDL file: writing it does NOT replace creating the relationships via
MCP `relationship_operations` — it drives that creation.

## When the file exists (and when it must NOT)

- Produce the file **only** when at least one required measure from
  `output/requirements.md` needs columns from more than one table.
- If every required measure can be computed from a single table, do **not**
  create the file — its absence is the signal that the model build skips the
  relationship step entirely and goes straight to measures.
- The file is written **after** the user has explicitly approved the proposed
  relationships, never before.

## Schema

```yaml
# output/relationships.yaml
project: <NomeProgetto>                 # matches report/<NomeProgetto>.pbip
source_requirements: output/requirements.md
approved: true                          # only ever written as true, post-approval

tables:                                 # every table referenced below
  - name: <TableName>                   # model table name (naming conventions apply)
    source: <path>                      # staging/<Progetto>/file.csv, or input/ fallback
    role: fact | dimension

relationships:
  - from_table: <TableName>             # MANY side (usually the fact)
    from_column: <column>
    to_table: <TableName>               # ONE side (usually the dimension)
    to_column: <column>
    cardinality: manyToOne              # manyToOne | oneToOne (manyToMany needs explicit justification)
    cross_filter: single                # single | both (both needs explicit justification)
    is_active: true                     # false only for secondary date/key paths (USERELATIONSHIP)
    required_by:                        # measures from requirements.md that need this relationship
      - "<Measure name as written in output/requirements.md>"
    notes: <optional — key type mismatches to resolve, justification for non-defaults>
```

## Validation rules (check mechanically before writing the file)

1. Every entry in `relationships` references only tables declared in `tables`.
2. Every relationship has a non-empty `required_by`: a relationship no
   measure needs must not be proposed.
3. Every multi-table measure identified in the analysis appears in at least
   one `required_by` — no orphan cross-table measures.
4. Key columns (`from_column` / `to_column`) exist in the source files and
   have compatible data types (or `notes` states how the mismatch is fixed).
5. Defaults are `manyToOne` + `single` + `is_active: true`; any deviation
   carries its justification in `notes`.
6. No duplicate table pairs with overlapping active paths (avoid ambiguity).

## How the build step consumes it

During model build, create **exactly** the relationships listed — one MCP
`relationship_operations` call per entry, mapping fields 1:1 (cardinality,
cross-filter direction, active flag). Do not add, merge, or "improve"
relationships at build time; if a new one turns out to be needed, go back to
the proposal step, get approval, update the YAML, then build it.

## Example

```yaml
project: AssistenzaClickHelp
source_requirements: output/requirements.md
approved: true

tables:
  - name: Fact_Ticket
    source: staging/AssistenzaClickHelp/Ticket.csv
    role: fact
  - name: Dim_Agente
    source: staging/AssistenzaClickHelp/Agenti.csv
    role: dimension

relationships:
  - from_table: Fact_Ticket
    from_column: id_agente
    to_table: Dim_Agente
    to_column: id_agente
    cardinality: manyToOne
    cross_filter: single
    is_active: true
    required_by:
      - "Ticket risolti per agente"
      - "Tempo medio di risoluzione per team"
```
