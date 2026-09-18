---
name: data-analysis
description: >-
  Analisi dati (fase 1.5) tra requisiti approvati e modello semantico: schema,
  qualità dati, conteggio righe, metadati — sia da file locali in
  input/<NomeProgetto>/ sia da un Lakehouse Fabric. Produce
  output/<NomeProgetto>/data-analysis.md, la base da cui etl-resolver decide
  le correzioni e semantic-modeler decide tabelle/relazioni. Usata
  dall'agente data-analyst.
---

# data-analysis — Analisi Dati tra Requisiti e Modello

Questa skill definisce il contenuto obbligatorio e il formato di
`output/<NomeProgetto>/data-analysis.md`, l'output della fase 1.5 (Analisi
Dati). Si applica **sempre**, qualunque sia la sorgente dati (file locali o
Lakehouse Fabric): la fase di pulizia (`etl-resolver`, fase 1.6) legge questo
report per sapere cosa correggere, invece di ri-ispezionare i dati grezzi da
zero.

## Perché una fase separata dalla pulizia

L'analisi **osserva e riporta**, non corregge. Separare "cosa c'è che non va"
da "come lo sistemo" rende entrambe le fasi più semplici da validare: un report
di analisi sbagliato è facile da rileggere e correggere, un ETL che decide da
solo cosa correggere sulla base di ipotesi implicite no. `data-analyst` non
scrive mai file in `output/<NomeProgetto>/staging/`: quello è output esclusivo
di `etl-resolver`.

## Sorgente Dati: Locale vs Fabric

La sezione `## Dati Disponibili e Granularità` di
`output/<NomeProgetto>/requirements.md` (campo `Tipo di DB` /
`Modalità di connessione`) dice quale sorgente usare:

- **Locale**: file in `input/<NomeProgetto>/` (`.csv`, `.xlsx`, eventualmente
  convertiti da `.docx` non è pertinente qui — solo i file tabellari). Usa i
  tool di lettura file standard del progetto (`read`,
  `python scripts/convert_input.py <NomeProgetto>` per i binari).
- **Fabric Lakehouse**: quando i requisiti indicano una sorgente Fabric
  (Lakehouse/Warehouse/Mirrored DB), usa la skill
  `.github/skills/fabric-lakehouse-consumption/SKILL.md` (MCP
  `fabric-sqlendpoint`, tool `execute_query`) per schema discovery, conteggio
  righe e query di qualità dati. Non scaricare né duplicare i dati Fabric in
  `input/`: l'analisi lavora query per query contro l'endpoint.

Se i requisiti non chiariscono la sorgente, è un gap bloccante: fermati e
chiedi conferma prima di procedere (non indovinare tra locale e Fabric).

## Contenuto Obbligatorio del Report

`output/<NomeProgetto>/data-analysis.md` va generato **sempre** copiando con
copia binaria (`Copy-Item`/`cp`) il template
`.github/skills/data-analysis/assets/data-analysis-template.md`, poi
compilando solo il testo sotto le intestazioni — stesse regole di
`requirements.md` (nessuna sezione inventata, omessa o rinominata).

Per **ogni tabella/file rilevante** ai requisiti (non tutte le tabelle del
Lakehouse se non pertinenti):

1. **Schema**: colonne, tipi dato osservati (non solo dichiarati — es. una
   colonna "decimale" con valori scritti come testo va segnalata come
   mismatch), chiave primaria candidata.
2. **Conteggio righe**: numero esatto (locale: `len(df)`; Fabric: da
   `sys.partitions`, mai `COUNT(*)` su tabelle grandi — vedi
   `fabric-lakehouse-consumption`).
3. **Qualità dati**: valori nulli/mancanti per colonna, duplicati su chiave
   candidata, formati non uniformi (date, decimali, encoding), outlier/valori
   fuori range evidenti. Ogni anomalia va **descritta**, non corretta: è
   materiale per `etl-resolver`.
   Nota bene: differenti dal cambio di formato (es. una colonna decimale scritta come testo) le anomalie relative a incoerenza tra descrizione della colonna e valore contenuto
   (es. una colonna "Data Ordine" con valori non plausibili come date) NON sono di competenza di `etl-resolver`.
   Queste vanno segnalate come "Anomalie di dominio" e richiedono conferma esplicita dell'utente 
   prima di qualunque decisione (es. escludere le righe, correggere manualmente, chiedere al proprietario dei dati).
4. **Metadati**: origine del file/tabella, data ultima modifica (locale) o
   ultimo refresh noto (Fabric, se disponibile), eventuali note di
   provenienza utili al modello (es. "estrazione mensile", "tabella
   transazionale vs dimensionale").

## Output

Struttura obbligatoria del template — vedi
`assets/data-analysis-template.md`:

```
# Analisi Dati

## Sorgente
- Tipo: Locale | Fabric Lakehouse
- Dettaglio: <cartella input/<NomeProgetto>/ oppure workspace/Lakehouse Fabric>

## Tabelle Analizzate
### <Nome tabella/file>
- Righe: <numero>
- Colonne: <elenco con tipo osservato>
- Chiave candidata: <colonna/e o "nessuna evidente">
- Qualità dati: <elenco puntuale di anomalie o "nessuna anomalia rilevata">
- Anomalie di dominio: <elenco puntuale o "nessuna">
- Metadati: <provenienza, data/refresh, note>

## Sintesi per Fase Successiva
- Correzioni da proporre a etl-resolver: <elenco puntuale o "nessuna necessaria">
- Punti di attenzione per semantic-modeler: <elenco puntuale o "nessuno">
```

Una sottosezione `### <Nome tabella/file>` per ogni tabella/file rilevante.

## Quando Fermarsi e Chiedere

- Sorgente dati non chiara dai requisiti (locale vs Fabric).
- Fabric: risoluzione ambigua di workspace/item (vedi
  `fabric-lakehouse-consumption/references/finding-workspaces-items.md`).
- Anomalia di dominio che richiede una decisione di business per essere
  interpretata (es. valori che sembrano errati ma potrebbero essere
  legittimi in un contesto che l'agente non conosce).

## Cosa NON fare in questa fase

- Non correggere, filtrare o scartare dati: solo osservare e riportare.
- Non scrivere in `output/<NomeProgetto>/staging/`.
- Non decidere tabelle, relazioni o misure del modello semantico.
