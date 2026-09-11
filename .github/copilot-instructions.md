# Istruzioni Progetto: Report Power BI Agentico

Questo progetto genera un **report Power BI Desktop end-to-end in modo agentico**, orchestrato attraverso più fasi specializzate con validazione tra ogni step.

---

## Decisione Iniziale: Quale Agente Usare?

**Hai un nuovo report da zero?**  
→ Usa **`orchestrator`**  
*Lui coordina tutto: requisiti → modello → layout → build*

**Hai già requisiti approvati e sei a metà progetto?**  
→ Usa comunque **`orchestrator`** e digli da quale fase ripartire  
*Gli agenti di fase non sono invocabili direttamente: l'orchestrator ricostruisce lo stato dal filesystem e delega alla fase giusta*

---

## Flusso Operativo

L'utente interagisce **sempre e solo con l'orchestrator**. Le fasi qui sotto sono
condotte da agenti interni a cui l'orchestrator delega: non vanno invocati
direttamente.

1. **Fase 1 – Requisiti** (delega a `requirements-analyst`)  
   Output: `output/requirements.md`

2. **Fase 1.5 – Pulizia Dati (ETL)** (delega a `etl`, solo se in `input/` ci sono file grezzi da normalizzare)  
   Output: `staging/<NomeProgetto>/` (dati normalizzati + log trasformazioni)

3. **Fase 2 – Modello Semantico** (delega a `semantic-modeler`)  
   Output: `report/<NomeProgetto>.SemanticModel/` (validato)

4. **Fase 3 – Layout Report** (delega a `report-builder`)  
   Output: file PBIR in `report/<NomeProgetto>.Report/` (validati)

5. **Verifica e Build** (orchestrator, con l'utente)  
   Output: screenshot Power BI Desktop, `.pbix` se necessario

---

## Regole Operative

### Approvazione tra Fasi
- ✅ **Non procedere alla fase successiva senza approvazione esplicita tua**
- Ogni fase produce output in `output/` o nella cartella PBIP
- Se l'output non è approvato, chiedi correzioni all'agente prima di proseguire

### Nomi e Convenzioni
- Progetti PBIP: `report/<NomeProgetto>.pbip`
- Output temporanei: `output/`
- Dati grezzi: `input/` (sola lettura, mai modificato)
- Dati puliti (post-ETL): `staging/<NomeProgetto>/`
- Modello semantico: `report/<NomeProgetto>.SemanticModel/`
- Report visuals: `report/<NomeProgetto>.Report/`

### Struttura OBBLIGATORIA di `output/requirements.md` (vale per qualunque agente la scriva)
- Il file va **sempre** generato copiando con copia binaria (`Copy-Item`/`cp`, mai `Set-Content` o riscrittura a mano) il template `.github/skills/powerbi-requirements-gathering/assets/requirements-template.md`, poi compilando **solo il testo sotto le intestazioni**. Le intestazioni del file devono coincidere esattamente con quelle del template: niente numerazioni proprie (es. "## 1. Obiettivo"), niente sezioni inventate, niente sezioni omesse.
- La sezione `## Mapping Requisiti → Schema Target` è **obbligatoria**: contiene la scomposizione del documento requisiti in **requisiti atomici** e la **verifica di allineamento**, una riga per requisito (`Requisito atomico | Tabella.Colonna proposta | Allineato? | Note`), usando i nomi di colonna reali letti dalle intestazioni dei file in `input/`. Va popolata ogni volta che in `input/` c'è almeno un file tabellare (`.xlsx`/`.csv`) — **anche se è un'estrazione dati**: ogni file/foglio è una tabella, le intestazioni sono le colonne. "Non applicabile" è ammesso solo se in `input/` non c'è alcun file tabellare.
- Un `output/requirements.md` con struttura diversa dal template è **non valido**: va cancellato e rigenerato dal template, e nessuna fase successiva (1.5/2/3) può partire da esso.
- **Gate eseguibile, non opzionale**: dopo aver scritto (o trovato) `output/requirements.md`, eseguire `python scripts/validate_requirements.py`. La fase 1 è conclusa e l'approvazione può essere chiesta **solo con exit code 0**; se fallisce, lo script elenca gli errori esatti da correggere (rigenerando dal template, mai patchando). Questo comando va eseguito da chi scrive il file (fine fase 1) e ri-eseguito dall'orchestrator prima di delegare qualsiasi fase successiva.

### TMDL: mai scritti a mano
- Il modello semantico si costruisce **solo** in due modi: (a) `powerbi-modeling-mcp` (Tier 1, preferito), oppure (b) spec dichiarativa `output/model.yaml` + `python scripts/build_model.py`, che genera tutta la `definition/` con indentazione/struttura/encoding corretti e lancia da solo il gate di validazione. Scrivere o modificare file `.tmdl` a mano riga per riga è vietato: produce file senza indentazione che Power BI Desktop rifiuta con "Errore di formato TMDL: Indentation".

### Validazione
- Il modello semantico deve essere validato prima di procedere alla fase report
- **Gate fase 2 eseguibile**: `python scripts/validate_model.py <NomeProgetto>` deve uscire con exit code 0 prima di chiedere l'approvazione del modello e prima di delegare la fase 3 (verifica tabelle duplicate, partition/sorgenti dati, copertura misure dei requisiti, encoding)
- **Gate fase 3 eseguibile**: `python scripts/validate_report.py <NomeProgetto>` deve uscire con exit code 0 prima di chiedere l'approvazione del layout e prima della fase 4 (verifica struttura pages/, binding a tabelle/colonne/misure esistenti nel modello, pagine dei requisiti presenti, visual nel canvas e non sovrapposti, encoding) — complementare a `powerbi-report-author validate`, che controlla lo schema JSON
- **Stato del progetto**: `python scripts/status.py [NomeProgetto]` stampa lo stato di ogni fase con evidenze ed esito dei gate (sola lettura): è la prima azione dell'orchestrator per ricostruire il punto di ripartenza. Le approvazioni utente non sono tracciate su file: un gate a exit 0 rende la fase completabile, l'approvazione va sempre confermata in chat
- I file PBIR devono renderizzare correttamente in Power BI Desktop
- Requisiti approvati guidano il design e il modello — niente improvvisazioni
- **Il `.pbix` lo genera solo Power BI Desktop** (aprire `report/<NomeProgetto>.pbip` → Aggiorna → Salva con nome `.pbix`): nessun agente deve mai creare/zippare un `.pbix` a mano o via script

---

## Catalogo Agenti

Solo l'`orchestrator` è invocabile dall'utente (`user-invocable: true`). Gli
altri quattro sono agenti di fase **interni** (`user-invocable: false`): non
vanno chiamati direttamente, li attiva l'orchestrator delegando. I file
completi sono in `.github/agents/`.

### orchestrator — punto d'ingresso unico
- **Scopo:** unico agente invocabile; ingresso per qualsiasi richiesta su un report Power BI (nuova o su progetto esistente, intera o puntuale). Ricostruisce lo stato del progetto dal filesystem, riparte dalla fase giusta e delega agli agenti di fase.
- **Trigger:** qualsiasi richiesta su un report Power BI — "crea un report", "guidami nella creazione", "aggiungi una misura", "modifica una pagina", "riparti dalla fase modello".

### requirements-analyst — Fase 1 (interno)
- **Cosa fa:** conduce l'intervista strutturata di raccolta requisiti.
- **Output:** `output/requirements.md`
- **Delegato dall'orchestrator quando:** servono requisiti (audience, dati, KPI, bozza pagine) o non esistono ancora.

### etl — Fase 1.5 (interno)
- **Cosa fa:** pulisce e normalizza i file grezzi in `input/` (date, decimali, encoding, duplicati, valori mancanti) rispetto allo schema atteso, senza mai modificare gli originali.
- **Output:** `staging/<NomeProgetto>/` (dati normalizzati + log trasformazioni)
- **Prerequisiti:** requisiti approvati in `output/requirements.md`; delegato solo se in `input/` ci sono file grezzi da normalizzare

### semantic-modeler — Fase 2 (interno)
- **Cosa fa:** costruisce il modello semantico (tabelle, relazioni, misure DAX) via `powerbi-modeling-mcp`, senza richiedere Power BI Desktop aperto.
- **Output:** `report/<NomeProgetto>.SemanticModel/` validato
- **Prerequisiti:** requisiti approvati in `output/requirements.md`; dati normalizzati in `staging/<NomeProgetto>/` se la fase 1.5 si è applicata

### report-builder — Fase 3 (interno)
- **Cosa fa:** progetta il layout e scrive/valida i file PBIR.
- **Output:** file PBIR validati in `report/<NomeProgetto>.Report/`
- **Prerequisiti:** modello semantico validato; requisiti approvati
