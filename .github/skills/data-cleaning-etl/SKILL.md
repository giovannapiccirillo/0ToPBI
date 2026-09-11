---
name: data-cleaning-etl
description: >-
  Pulisce e normalizza i file dati grezzi in `input/` prima che entrino nel
  modello semantico (fase 1.5, tra requisiti e modellazione): formati data,
  separatori decimali, encoding, duplicati, valori nulli, tipi di colonna,
  in base allo schema atteso da `output/requirements.md`. Produce i file
  puliti in `staging/`, senza mai modificare gli originali in `input/`. Non
  crea tabelle, relazioni o misure — quello è compito di
  `semantic-model-authoring`.
  Triggers: "pulizia dati", "normalizza le date", "formato decimali",
  "encoding file", "dati sporchi", "prepara i dati per il modello".
---

# Skill di Pulizia Dati (ETL)

Questa skill definisce come normalizzare i file grezzi trovati in `input/`
prima che diventino sorgente del modello semantico. Si occupa solo di
**qualità e formato dei dati** (date, decimali, encoding, duplicati, tipi,
valori mancanti) — non decide tabelle, relazioni o misure: quello è compito
di `semantic-model-authoring` nella fase 2.

**Confine di scope** — questa skill non tocca `report/<Nome>.SemanticModel/`
né `report/<Nome>.Report/`, non scrive DAX e non decide fact/dimension. Legge
`input/` e `output/requirements.md`, scrive solo in `staging/`.

## Obbligatorio/Preferire/Evitare

### OBBLIGATORIO

- Non modificare mai i file originali in `input/`: sono la fonte di verità,
  vanno trattati come sola lettura.
- Scrivere ogni file pulito in `staging/<NomeProgetto>/`, con lo stesso nome
  base del file di `input/` (stessa cartella per foglio se un workbook Excel
  ha più fogli), in formato CSV con encoding UTF-8.
- Basare le correzioni sullo schema atteso descritto in
  `output/requirements.md` (sezione "Dati Disponibili e Granularità" e
  "Mapping Requisiti → Schema Target", se presente): tipo di dato e
  granularità attesi per ciascuna colonna determinano quale normalizzazione
  applicare, non un'euristica generica.
- Produrre per ogni file un log delle trasformazioni applicate (vedi
  [Output](#output)): ogni scostamento dal dato originale deve essere
  tracciabile. Scrivi una voce di log per ogni file anche quando non è
  necessaria alcuna correzione (es. "Nessuna: dati già conformi allo schema
  atteso") — l'assenza di trasformazioni non è un motivo per omettere la
  voce.
- Per ogni trasformazione loggata, indicare anche il **requisito atomico di
  riferimento** (dalla sezione "Mapping Requisiti → Schema Target" di
  `output/requirements.md`) che l'ha resa necessaria — non basta la
  descrizione tecnica della trasformazione, va tracciato anche il *perché*.
- Non considerare `staging/` pronto per la fase 2, né chiedere approvazione
  (vedi [Gate di Approvazione](#gate-di-approvazione)), finché
  `staging/<NomeProgetto>/etl-log.md` non contiene una voce per ciascun file
  processato: è un output obbligatorio quanto i CSV puliti, non un passo
  facoltativo o rimandabile.
- Segnalare (non correggere silenziosamente) le anomalie che richiedono una
  decisione di business: valori fuori range plausibile, chiavi duplicate che
  non sembrano errori di formattazione, righe con troppi campi mancanti per
  essere recuperabili. Va sempre chiesta conferma prima di scartare righe.
- Se un file non è in un formato leggibile come testo (`.xlsx`, `.docx`,
  formati binari), convertilo prima con `python scripts/convert_input.py`
  (script generico del progetto, mai codice di conversione ad hoc; regole in
  [powerbi-requirements-gathering](../powerbi-requirements-gathering/SKILL.md#lettura-di-file-binari-in-input-docx-xlsx)):
  non presentarla come uno step separato.

### PREFERIRE

- Correzioni deterministiche e reversibili (parsing esplicito di un formato
  data noto, sostituzione di un separatore decimale coerente in tutta la
  colonna) rispetto a euristiche indovinate riga per riga.
- Validare la normalizzazione su un campione prima di applicarla a tutto il
  file, specialmente per file grandi.
- Riusare `staging/` già prodotto in una sessione precedente se l'originale
  in `input/` non è cambiato (confronta data di modifica), invece di
  ripulire da zero.

### EVITARE

- Non inventare valori per celle vuote: un valore mancante resta mancante
  (o `NULL` esplicito) a meno che i requisiti non definiscano una regola di
  default esplicita e approvata dall'utente.
- Non scartare righe o colonne senza segnalarlo e ottenere conferma.
- Non normalizzare una colonna che i requisiti non useranno: la pulizia si
  applica solo alle colonne effettivamente rilevanti per il mapping
  requisiti → schema, non all'intero file "per sicurezza".
- Non decidere tipi di tabella (fact/dimension), relazioni o nomi di colonna
  del modello: questa skill non rinomina colonne per convenzioni di
  modellazione, si limita a normalizzarne il contenuto/formato.

## Categorie di Correzione

Applica solo le categorie effettivamente necessarie per i file in `input/` e
lo schema atteso — non tutte si applicano sempre.

### Date e orari

- Rileva il formato sorgente (es. `gg/mm/aaaa`, `mm/gg/aaaa`, seriale Excel,
  testo libero) e normalizza a ISO 8601 (`YYYY-MM-DD`, o
  `YYYY-MM-DDTHH:MM:SS` se presente un orario).
- Attenzione all'ambiguità giorno/mese (es. `03/04/2025`): se il file ha
  colonne con giorno > 12 in altre righe, usa quello per dedurre l'ordine;
  se resta ambiguo, segnalalo come domanda invece di assumere.
- Uniforma il fuso orario solo se i requisiti lo richiedono esplicitamente;
  altrimenti lascia l'orario locale così com'è, senza conversioni implicite.

### Numeri e decimali

- Rileva il separatore decimale e delle migliaia in uso (`1.234,56` vs
  `1,234.56`) e normalizza al formato con punto come separatore decimale e
  nessun separatore delle migliaia (`1234.56`), pronto per l'import.
- Rimuovi simboli di valuta, percentuale o unità di misura incorporati nel
  valore (`€ 1.234,56`, `12%`) spostandoli, se richiesto dai requisiti, in
  una colonna/nota separata invece di lasciarli nel valore numerico.
- Mantieni coerenza del numero di decimali all'interno della stessa colonna
  solo se richiesto esplicitamente; non arrotondare silenziosamente dati che
  serviranno per KPI di precisione.

### Testo ed encoding

- Normalizza l'encoding a UTF-8 se il file sorgente usa un altro charset
  (es. `Windows-1252`, `ISO-8859-1`) e ci sono caratteri corrotti/mojibake.
- Rimuovi spazi bianchi superflui a inizio/fine cella (`trim`); non alterare
  spazi interni al valore.
- Uniforma maiuscole/minuscole solo se i requisiti lo richiedono per un
  match con un'altra tabella (es. join case-insensitive diventato
  case-sensitive nel modello); altrimenti preserva il valore originale.

### Chiavi, duplicati e integrità referenziale

- Segnala (non deduplica automaticamente) le righe duplicate su chiave
  primaria attesa: la deduplica automatica rischia di scartare dati validi
  se la chiave attesa è sbagliata.
- Verifica che le colonne usate come chiave di relazione (da
  "Mapping Requisiti → Schema Target") abbiano valori coerenti tra le
  tabelle correlate (stesso tipo, stesso formato) — es. un ID prodotto
  numerico in una tabella e testuale in un'altra va segnalato.

### Valori mancanti e outlier

- Marca esplicitamente le celle vuote/`NULL` senza inventare un default,
  a meno che i requisiti non specifichino una regola (es. "quantità mancante
  → 0").
- Segnala valori chiaramente fuori scala plausibile (es. importi negativi
  dove i requisiti non li prevedono, date fuori dal periodo di
  granularità atteso) come domanda aperta, non come correzione automatica.

## Workflow

1. Leggi `output/requirements.md` per lo schema atteso (tabelle, colonne,
   tipi, granularità) e l'elenco "Tabelle/file attesi in `input/`".
2. Ispeziona ogni file in `input/` corrispondente: identifica formato
   sorgente di date, decimali, encoding; individua duplicati, valori
   mancanti e disallineamenti di tipo rispetto allo schema atteso.
3. Applica le correzioni deterministiche (vedi
   [Categorie di Correzione](#categorie-di-correzione)) chiamando
   `prepare_staging()` di `scripts/prepare_staging.py` con la
   `column_config` del progetto, i `requirement_refs` (colonna → requisito
   atomico) e le `anomalies` rilevate: la funzione scrive
   `staging/<NomeProgetto>/<nome-file>.csv` E la relativa voce di
   `etl-log.md` in un colpo solo. Passa dalla funzione anche i file che non
   richiedono correzioni (config vuota o minimale), così la loro voce
   "Nessuna: dati già conformi" viene comunque scritta.
4. Autoverifica meccanica di chiusura: elenca i CSV in
   `staging/<NomeProgetto>/` e controlla che `etl-log.md` contenga una
   sezione `## <nome-file>` per ciascuno, con requisito di riferimento per
   ogni trasformazione. Se una voce manca, completala prima di proseguire.
5. Se emergono anomalie che richiedono una decisione (ambiguità di formato,
   righe duplicate su chiave, valori fuori range, dati mancanti senza regola
   nota), fermati e chiedi conferma puntuale invece di procedere per
   ipotesi.
6. Riepiloga all'utente cosa è stato normalizzato per ciascun file e chiedi
   **approvazione esplicita** prima di considerare `staging/` pronto per la
   fase 2.

## Output

Per ogni file sorgente pulito, produci:

- `staging/<NomeProgetto>/<nome-file>.csv` — dati normalizzati, UTF-8.
- Un log delle trasformazioni applicate, in coda a
  `staging/<NomeProgetto>/etl-log.md` (un file unico per progetto, sezione
  per file). La voce è scritta automaticamente da `prepare_staging()`
  insieme al CSV quando le passi `requirement_refs` e `anomalies` — non
  scrivere CSV in `staging/` con codice che aggira questo meccanismo. Il
  formato della sezione:

```markdown
## <nome-file originale>
- Data: <YYYY-MM-DD>
- Sorgente: input/<nome-file>
- Righe in ingresso / in uscita: <N> / <M>
- Trasformazioni applicate:
  - <colonna>: <descrizione trasformazione, es. "data gg/mm/aaaa -> ISO 8601">
    (requisito di riferimento: <requisito atomico dal Mapping Requisiti → Schema Target che ha motivato la trasformazione>)
  - <colonna>: <descrizione, es. "separatore decimale , -> .">
    (requisito di riferimento: <...>)
- Anomalie segnalate (non corrette automaticamente):
  - <descrizione, con riferimento a righe/valori>
```

## Gate di Approvazione

Dopo aver scritto `staging/` e il log, fai esattamente una domanda di
approvazione:

> Approvi i dati puliti in `staging/` così possiamo passare alla fase di
> modello semantico?

Non passare alla fase 2 (`semantic-modeler`) finché l'utente non approva. Se
richiede modifiche, rivedi i file in `staging/` e chiedi di nuovo.
