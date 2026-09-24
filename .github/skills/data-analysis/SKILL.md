---
name: data-analysis
description: >-
  Analisi dati (fase 2) tra requisiti approvati e modello semantico: schema,
  qualità dati, conteggio righe, metadati — sia da file locali in
  input/<NomeProgetto>/ sia da un Lakehouse Fabric. Produce
  output/<NomeProgetto>/data-analysis.md, la base da cui etl-resolver decide
  le correzioni e semantic-modeler decide tabelle/relazioni. Usata
  dall'agente data-analyst.
---

# data-analysis — Analisi Dati tra Requisiti e Modello

Questa skill definisce il contenuto obbligatorio e il formato di
`output/<NomeProgetto>/data-analysis.md`, l'output della fase 2 (Analisi
Dati). Si applica **sempre**, qualunque sia la sorgente dati (file locali o
Lakehouse Fabric): la fase di pulizia (`etl-resolver`, fase 3) legge questo
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

- **Locale**: file tabellari in `input/<NomeProgetto>/` (`.csv`, `.xlsx`
  originali) o i loro derivati `.csv` in `input/<NomeProgetto>/temp/` se
  convertiti da `.xlsx` binari (`python scripts/common/convert_input.py
  <NomeProgetto>`); usa i tool di lettura file standard del progetto (`read`).
- **Fabric Lakehouse**: quando i requisiti indicano una sorgente Fabric
  (Lakehouse/Warehouse/Mirrored DB), usa la skill
  `.github/skills/fabric-lakehouse-consumption/SKILL.md` (MCP
  `fabric-sqlendpoint`, tool `execute_query`) per schema discovery, conteggio
  righe, query di qualità dati e i limiti di query (righe/timeout/rate
  limit, sezione "Tool Stack" della skill). Non scaricare né duplicare i
  dati Fabric in `input/`: l'analisi lavora query per query contro
  l'endpoint.

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
   mismatch).
2. **Chiave candidata e relazioni tra tabelle**: **prima leggi i metadati
   dichiarati** — constraint PK/FK/UNIQUE, se esposti (Fabric: query
   "Constraint"/"Relazioni foreign key" in
   `fabric-lakehouse-consumption/references/discovery-queries.md`). Solo se
   assenti — il caso comune su un Lakehouse, le cui tabelle sono
   auto-generate da Delta e **tipicamente non hanno PK/FK dichiarate**, Delta
   non avendo vincoli di integrità referenziale nativi — deduci dai valori:
   - *Chiave candidata*: confronta `COUNT(DISTINCT colonna)` con il
     conteggio righe della tabella; cardinalità ≈ righe indica una chiave.
   - *Relazione candidata*: per una colonna che sembra riferirsi a un'altra
     tabella per naming (es. `ProductID` in una fact), verifica che i suoi
     valori esistano tutti nella presunta tabella "parent" (query di
     inclusione insiemistica) prima di segnalarla — mai solo per
     somiglianza del nome di colonna.
3. **Cardinalità e valori per le altre colonne**: per ogni colonna
   non-chiave, `COUNT(DISTINCT colonna)`. Se la cardinalità è bassa (soglia
   indicativa, es. ≤ 20 valori distinti — valuta caso per caso) elenca i
   valori distinti effettivi; se è alta, riporta il conteggio più una Top-N
   per frequenza. Questo distingue una dimensione categorica (bassa
   cardinalità, valori noti, utile come filtro/slicer nel report) da un
   attributo libero (alta cardinalità, non utile a un modello a stella).
4. **Range temporale/numerico**: per colonne data e per le misure numeriche
   principali, MIN/MAX osservati — indica il periodo storico coperto
   (quanti mesi/anni di dati per i KPI) e aiuta a intercettare outlier
   prima del check di qualità dati.
5. **Conteggio righe**: numero esatto (locale: `len(df)`; Fabric: da
   `sys.partitions`, mai `COUNT(*)` su tabelle grandi — vedi
   `fabric-lakehouse-consumption`).
6. **Qualità dati**: valori nulli/mancanti per colonna, duplicati su chiave
   candidata, formati non uniformi (date, decimali, encoding), outlier/valori
   fuori range evidenti. Ogni anomalia va **descritta**, non corretta: è
   materiale per `etl-resolver`.
   Nota bene: differenti dal cambio di formato (es. una colonna decimale scritta come testo) le anomalie relative a incoerenza tra descrizione della colonna e valore contenuto
   (es. una colonna "Data Ordine" con valori non plausibili come date) NON sono di competenza di `etl-resolver`.
   Queste vanno segnalate come "Anomalie di dominio" e richiedono conferma esplicita dell'utente 
   prima di qualunque decisione (es. escludere le righe, correggere manualmente, chiedere al proprietario dei dati).
7. **Metadati**: origine del file/tabella, data ultima modifica (locale) o
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
- Relazioni candidate: <colonna → tabella.colonna referenziata, con fonte (constraint dichiarato o dedotta per inclusione valori) o "nessuna">
- Cardinalità e valori: <per colonna non-chiave: conteggio distinct, e valori effettivi (bassa cardinalità) o Top-N (alta cardinalità)>
- Range: <MIN/MAX per colonne data e misure numeriche principali, o "non pertinente">
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
