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
   Output: `output/<NomeProgetto>/requirements.md`

2. **Fase 2 – Analisi Dati** (delega a `data-analyst`, **sempre**, sia sorgente locale che Fabric)  
   Output: `output/<NomeProgetto>/data-analysis.md` (schema, qualità dati, righe, metadati)

3. **Fase 3 – Pulizia Dati (ETL)** (delega a `etl-resolver`, solo se `data-analysis.md` segnala correzioni da applicare)  
   Output: `output/<NomeProgetto>/staging/` (dati normalizzati + log trasformazioni)

4. **Fase 4 – Modello Semantico** (delega a `semantic-modeler`)  
   Output: `report/<NomeProgetto>.SemanticModel/` (validato)

5. **Fase 5 – Layout Report** (delega a `report-builder`)  
   Output: file PBIR in `report/<NomeProgetto>.Report/` (validati)

6. **Fase 6 – Verifica e Build** (orchestrator, con l'utente)  
   Output: screenshot Power BI Desktop, `.pbix` se necessario

---

## Regole Operative

### Approvazione tra Fasi
- ✅ **Non procedere alla fase successiva senza approvazione esplicita tua**
- Ogni fase produce output in `output/<NomeProgetto>/` o nella cartella PBIP
- Se l'output non è approvato, chiedi correzioni all'agente prima di proseguire

### Nomi e Convenzioni
- Ogni progetto vive su due nomi, potenzialmente diversi:
  - `<NomeProgetto>`: nome libero della cartella condivisa da `input/` e `output/` (es. `input/vendite-mensili/`, `output/vendite-mensili/`), scelto dall'utente prima ancora che il progetto PBIP esista
  - `<Progetto>`: nome del PBIP in `report/<Progetto>.pbip`, deciso in fase 1
- Dati grezzi: `input/<NomeProgetto>/` (sola lettura, mai modificato)
- Derivati di conversione (`.docx` → `.md`, `.xlsx` → `.csv`, via `scripts/common/convert_input.py`): `input/<NomeProgetto>/temp/`, mai accanto all'originale
- Output temporanei/artefatti di fase: `output/<NomeProgetto>/`
- Dati puliti (post-ETL): `output/<NomeProgetto>/staging/`
- Modello semantico: `report/<Progetto>.SemanticModel/`
- Report visuals: `report/<Progetto>.Report/`

### Template PBIP di partenza (`report/_Template.*`)
- `report/_Template.pbip`, `_Template.Report/`, `_Template.SemanticModel/` sono lo scheletro PBIP minimo del repository: pagine/tabelle segnaposto, tema custom, struttura di cartelle già valida per Power BI Desktop. Non è un progetto reale e non va mai usato così com'è per un report da consegnare.
- A ogni nuovo `<Progetto>`, `semantic-modeler` (fase 4) copia questa cartella (mai spostarla o rinominarla in-place) in `report/<Progetto>.pbip` / `.SemanticModel/` / `.Report/` e aggiorna al suo interno i riferimenti al nome (`.pbip`, i `.platform`, `definition.pbir`) prima di iniziare a costruire tabelle/relazioni/misure sul progetto copiato.
- Il prefisso `_` è intenzionale: mantiene il template in cima all'elenco della cartella `report/` e lo distingue a colpo d'occhio da un progetto reale.

### Preset locale (`.env`, opzionale)
- Un file `.env` alla radice (non versionato, `.env.example` documenta il formato) può fissare `NOME_PROGETTO`, `NOME_PBIP`, `CULTURA` come valori noti a priori
- L'orchestrator li usa come **default silenzioso**: se non specificato altrimenti in chat, li applica senza chiedere conferma; qualunque valore diverso indicato dall'utente o già presente sul filesystem prevale sempre
- `python scripts/common/status.py` lo segnala quando non esiste ancora alcun progetto in `output/`

### Struttura OBBLIGATORIA di `output/<NomeProgetto>/requirements.md` (vale per qualunque agente la scriva)
- Il file va **sempre** generato copiando con copia binaria (`Copy-Item`/`cp`, mai `Set-Content` o riscrittura a mano) il template `.github/skills/powerbi-requirements-gathering/templates/requirements-template.md` come primo passo della fase 1 (non a fine sessione) — `requirements-analyst` non ha il tool `execute`: è l'orchestrator a eseguire questa copia, prima di delegare, come parte del proprio Core Workflow. `requirements-analyst` compila **solo il testo sotto le intestazioni**, sezione per sezione man mano che ogni round viene confermato dall'utente. Le intestazioni del file devono coincidere esattamente con quelle del template: niente numerazioni proprie (es. "## 1. Obiettivo"), niente sezioni inventate, niente sezioni omesse.
- La sezione `## Mapping Requisiti → Schema Target` è **obbligatoria**: contiene la scomposizione del documento requisiti in **requisiti atomici** e la **verifica di allineamento**, una riga per requisito (`Requisito atomico | Tabella.Colonna proposta | Allineato? | Note`), usando i nomi di colonna reali letti dalle intestazioni dei file in `input/<NomeProgetto>/`. Va popolata ogni volta che in `input/<NomeProgetto>/` c'è almeno un file tabellare (`.xlsx`/`.csv`) — **anche se è un'estrazione dati**: ogni file/foglio è una tabella, le intestazioni sono le colonne. "Non applicabile" è ammesso solo se in `input/<NomeProgetto>/` non c'è alcun file tabellare.
- Un `output/<NomeProgetto>/requirements.md` con struttura diversa dal template è **non valido**: va cancellato e rigenerato dal template, e nessuna fase successiva (2/3/4/5) può partire da esso.
- **Gate eseguibile, non opzionale**: dopo che `output/<NomeProgetto>/requirements.md` è stato scritto (o trovato), eseguire `python scripts/01_requisiti/validate_requirements.py <NomeProgetto>`. La fase 1 è conclusa e l'approvazione può essere chiesta **solo con exit code 0**; se fallisce, lo script elenca gli errori esatti da correggere (rigenerando dal template, mai patchando). L'orchestrator è l'unico esecutore di questo comando: lo lancia quando `requirements-analyst` dichiara pronto il file (fine fase 1) e lo ri-esegue prima di delegare qualsiasi fase successiva.

### TMDL: mai scritti a mano
- Il modello semantico si costruisce **solo** in due modi: (a) `powerbi-modeling-mcp` (Tier 1, preferito), oppure (b) spec dichiarativa `output/<NomeProgetto>/model.yaml` + `python scripts/04_modello/build_model.py <NomeProgetto>`, che genera tutta la `definition/` con indentazione/struttura/encoding corretti e lancia da solo il gate di validazione. Scrivere o modificare file `.tmdl` a mano riga per riga è vietato: produce file senza indentazione che Power BI Desktop rifiuta con "Errore di formato TMDL: Indentation".

### Validazione
- **Gate fase 2 eseguibile**: `python scripts/02_analisi_dati/validate_data_analysis.py <NomeProgetto>` deve uscire con exit code 0 prima di chiedere l'approvazione dell'analisi dati e prima di valutare la fase 3 o delegare la fase 4
- Il modello semantico deve essere validato prima di procedere alla fase report
- **Gate fase 4 eseguibile**: `python scripts/04_modello/validate_model.py <NomeProgetto> <Progetto>` deve uscire con exit code 0 prima di chiedere l'approvazione del modello e prima di delegare la fase 5 (verifica tabelle duplicate, partition/sorgenti dati, copertura misure dei requisiti, encoding)
- **Gate fase 5 eseguibile**: `python scripts/05_report/validate_report.py <NomeProgetto> <Progetto>` deve uscire con exit code 0 prima di chiedere l'approvazione del layout e prima della fase 6 (verifica struttura pages/, binding a tabelle/colonne/misure esistenti nel modello, pagine dei requisiti presenti, visual nel canvas e non sovrapposti, encoding) — complementare a `powerbi-report-author validate`, che controlla lo schema JSON
- **Stato del progetto**: `python scripts/common/status.py [NomeProgetto]` stampa lo stato di ogni fase con evidenze ed esito dei gate (sola lettura): è la prima azione dell'orchestrator per ricostruire il punto di ripartenza. Le approvazioni utente non sono tracciate su file: un gate a exit 0 rende la fase completabile, l'approvazione va sempre confermata in chat
- I file PBIR devono renderizzare correttamente in Power BI Desktop
- Requisiti approvati guidano il design e il modello — niente improvvisazioni
- **Il `.pbix` lo genera solo Power BI Desktop** (aprire `report/<Progetto>.pbip` → Aggiorna → Salva con nome `.pbix`): nessun agente deve mai creare/zippare un `.pbix` a mano o via script

---

## Catalogo Agenti

Solo l'`orchestrator` è invocabile dall'utente (`user-invocable: true`). Gli
altri cinque sono agenti di fase **interni** (`user-invocable: false`): non
vanno chiamati direttamente, li attiva l'orchestrator delegando. I file
completi sono in `.github/agents/`.

### orchestrator — punto d'ingresso unico
- **Scopo:** unico agente invocabile; ingresso per qualsiasi richiesta su un report Power BI (nuova o su progetto esistente, intera o puntuale). Ricostruisce lo stato del progetto dal filesystem, riparte dalla fase giusta e delega agli agenti di fase.
- **Trigger:** qualsiasi richiesta su un report Power BI — "crea un report", "guidami nella creazione", "aggiungi una misura", "modifica una pagina", "riparti dalla fase modello".

### requirements-analyst — Fase 1 (interno)
- **Cosa fa:** conduce l'intervista strutturata di raccolta requisiti.
- **Output:** `output/<NomeProgetto>/requirements.md`
- **Delegato dall'orchestrator quando:** servono requisiti (audience, dati, KPI, bozza pagine) o non esistono ancora.

### data-analyst — Fase 2 (interno)
- **Cosa fa:** analizza i dati (schema, qualità, conteggio righe, metadati) da `input/<NomeProgetto>/` o da un Lakehouse Fabric (via skill `fabric-lakehouse-consumption`), senza correggere nulla.
- **Output:** `output/<NomeProgetto>/data-analysis.md`
- **Prerequisiti:** requisiti approvati in `output/<NomeProgetto>/requirements.md`; si applica **sempre**, qualunque sia la sorgente

### etl-resolver — Fase 3 (interno)
- **Cosa fa:** pulisce e normalizza i file grezzi in `input/<NomeProgetto>/` (date, decimali, encoding, duplicati, valori mancanti) sulla base delle anomalie riportate in `output/<NomeProgetto>/data-analysis.md`, senza mai modificare gli originali.
- **Output:** `output/<NomeProgetto>/staging/` (dati normalizzati + log trasformazioni)
- **Prerequisiti:** analisi dati approvata in `output/<NomeProgetto>/data-analysis.md`; delegato solo se la sua sezione "Sintesi per Fase Successiva" segnala correzioni da applicare

### semantic-modeler — Fase 4 (interno)
- **Cosa fa:** costruisce il modello semantico (tabelle, relazioni, misure DAX) via `powerbi-modeling-mcp`, senza richiedere Power BI Desktop aperto.
- **Output:** `report/<Progetto>.SemanticModel/` validato
- **Prerequisiti:** requisiti approvati in `output/<NomeProgetto>/requirements.md`; analisi dati in `output/<NomeProgetto>/data-analysis.md`; dati normalizzati in `output/<NomeProgetto>/staging/` se la fase 3 si è applicata

### report-builder — Fase 5 (interno)
- **Cosa fa:** progetta il layout e scrive/valida i file PBIR.
- **Output:** file PBIR validati in `report/<Progetto>.Report/`
- **Prerequisiti:** modello semantico validato; requisiti approvati
