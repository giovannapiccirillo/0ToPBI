# Acceleratore Power BI — Report Agentico

Framework locale per costruire un report Power BI Desktop **end-to-end in modo
agentico** con GitHub Copilot (VS Code, Agent Mode) + MCP, senza Fabric né Azure.

Tu descrivi il report che ti serve; una catena di agenti specializzati lo
costruisce a fasi — requisiti → pulizia dati → modello semantico → layout →
build — con un **gate eseguibile** e la **tua approvazione esplicita** tra una
fase e l'altra.

```
Tu ──► orchestrator ──► fase 1 ──► fase 1.5 ──► fase 2 ──► fase 3 ──► fase 4
       (unico agente     requisiti   ETL          modello     layout      build in
        che invochi)                (se serve)   semantico    PBIR        Desktop
                         ▲ ogni fase: agente dedicato + output su file + gate + tuo OK
```

---

## Come si usa

Interagisci **sempre e solo con l'agente `orchestrator`** in Copilot Chat
(Agent Mode). Gli altri agenti sono interni: li attiva lui per delega.

**Nuovo report** — metti in `input/` il documento requisiti (`.docx`) e i dati
(`.csv`/`.xlsx`), poi ad esempio:

> Devo creare un report vendite mensile per il management.
> I dati e il documento requisiti sono in input/.
> Guidami dalla raccolta requisiti fino al report finito.

**Modifica a un report esistente** — descrivi la modifica citando il report;
l'orchestrator ricostruisce lo stato dal filesystem e riparte dalla fase giusta:

> Nel report Prova, aggiungi una misura "Margine per Ordine" al modello.

**Ripresa a metà flusso** — funziona allo stesso modo: lo stato vive su file,
non nella memoria della chat. Per vederlo in qualsiasi momento:

```bash
python scripts/status.py
```

---

## Prerequisiti

- **Power BI Desktop** (ultima versione) con la preview "Power BI Project
  (.pbip) save option" attivata: File → Options → Preview Features
- **Python 3.10+** (script di conversione e validazione in `scripts/`)
- **VS Code** con GitHub Copilot + Copilot Chat
- **Git**

---

## Il flusso a fasi

| Fase | Agente | Skill | Output | Gate (oltre al tuo OK) |
|---|---|---|---|---|
| 1. Requisiti | `requirements-analyst` | `powerbi-requirements-gathering` | `output/requirements.md` | `validate_requirements.py` = 0 |
| 1.5 Pulizia dati (solo se serve) | `etl` | `data-cleaning-etl` | `staging/<Progetto>/` + `etl-log.md` | log completo (una voce per CSV) |
| 2. Modello semantico | `semantic-modeler` | `semantic-model-authoring` | `report/<Progetto>.SemanticModel/` | `validate_model.py <Progetto>` = 0 |
| 3. Layout report | `report-builder` | `powerbi-report-design` + `powerbi-report-authoring` | PBIR in `report/<Progetto>.Report/` | `powerbi-report-author validate` + `validate_report.py <Progetto>` = 0 |
| 4. Build + verifica | orchestrator, con te | — | `report/<Progetto>.pbix` | verifica visiva in Desktop |

---

## Come funziona il processo, passo per passo

### Cosa succede quando scrivi all'orchestrator

A ogni tuo messaggio — nuovo report, modifica puntuale o ripresa — l'orchestrator:

1. **Fotografa lo stato** con `python scripts/status.py`: per ogni fase legge
   le evidenze sul filesystem e l'esito dei gate. Non si fida della memoria
   della chat né del racconto degli agenti: contano i file.
2. **Verifica che i requisiti esistenti appartengano al report che chiedi**
   (confronta nome/obiettivo): se stai chiedendo un report *diverso* da quello
   documentato, la fase 1 riparte da zero — mai riuso automatico dei requisiti.
3. **Controlla `input/`** e ti riepiloga cosa ha trovato (documento requisiti,
   file dati); con più set di file propone il match sul nome che hai citato e
   ti chiede conferma.
4. **Delega la fase giusta** all'agente competente, passandogli il contesto già
   noto (nome progetto, path, output precedenti), raccoglie il risultato, te lo
   presenta in sintesi e **chiede la tua approvazione** prima di avanzare.

### Fase 1 — Requisiti (`requirements-analyst`)

- Ispeziona `input/` come prima azione. I file binari (`.docx`, `.xlsx`)
  vengono convertiti in testo con `convert_input.py`, in modo trasparente.
- **Se ci sono sia documento requisiti sia file dati**: niente intervista
  generica. Il documento viene scomposto in **requisiti atomici** e ognuno
  viene mappato sulle colonne reali dei file (sezione "Mapping Requisiti →
  Schema Target"); i KPI si deducono dal documento. Ti vengono fatte solo le
  domande sui **gap reali** (es. modalità di connessione, requisito senza
  colonna corrispondente).
- **Se manca uno dei due**: domande mirate solo su ciò che manca; senza nulla
  in mano, intervista strutturata a round (audience, dati, KPI, pagine, stile),
  un round alla volta con riepilogo e conferma.
- Il file `output/requirements.md` è **sempre ricreato copiando il template
  ufficiale** e compilando solo il testo sotto le intestazioni — mai patchato,
  mai con sezioni inventate.
- Chiusura: autoverifica titolo-per-titolo contro il template, poi
  `validate_requirements.py` fino a exit 0, poi la tua approvazione.

### Fase 1.5 — Pulizia dati (`etl`, solo se serve)

- Parte **solo dopo** l'approvazione dei requisiti, e solo se questi indicano
  file in `input/` da normalizzare. Se i dati sono già pronti (o la connessione
  è diretta), l'orchestrator **dichiara lo skip in una riga** e passa oltre.
- L'agente ispeziona ogni file rispetto allo schema atteso (formato date,
  separatore decimale, encoding, duplicati, valori mancanti) e costruisce la
  configurazione del progetto in `staging/<Progetto>/etl-config.json`.
- Le correzioni le applica **solo** lo script generico `prepare_staging.py`
  (`--config`): deterministiche e tracciabili, mai euristiche riga per riga.
  Lo script scrive **insieme** il CSV pulito e la voce in `etl-log.md`, con il
  requisito che ha motivato ogni trasformazione — anche per i file già
  conformi ("Nessuna trasformazione").
- Ogni ambiguità che richiede una decisione di business (duplicati su chiave,
  valori fuori range, date ambigue) **si ferma e ti chiede**: niente valori
  inventati, niente righe scartate in silenzio.
- Chiusura: autoverifica log completo (una sezione per ogni CSV), poi la tua
  approvazione. `input/` non viene mai modificato.

### Fase 2 — Modello semantico (`semantic-modeler`)

- **Prima le relazioni, poi le misure**: dai KPI dei requisiti deriva quali
  tabelle servono a ciascuna misura. Se una misura attraversa più tabelle, ti
  **propone** le relazioni necessarie (chiavi, cardinalità, direzione filtro),
  motivate dalle misure che le richiedono; dopo il tuo ok le formalizza in
  `output/relationships.yaml` — l'**unica** fonte da cui le relazioni vengono
  poi create. Se basta una tabella sola, lo dichiara e salta lo step.
- Il modello si costruisce via **MCP `powerbi-modeling-mcp`** collegandosi
  direttamente alla cartella PBIP (Desktop non serve aperto): tabelle, colonne,
  relazioni (solo quelle nel YAML), misure DAX per tutti i KPI. Se l'MCP non è
  disponibile, il fallback è la spec `output/model.yaml` + `build_model.py` —
  **mai TMDL scritto a mano**.
- Le partition delle tabelle puntano a `staging/<Progetto>/` (dati puliti) se
  la fase 1.5 è stata eseguita, altrimenti a `input/`.
- Chiusura: validazione a ogni batch, poi `validate_model.py <Progetto>` fino a
  exit 0 (tabelle, partition, copertura di **tutte** le misure dei requisiti,
  encoding), poi la tua approvazione.

### Fase 3 — Layout report (`report-builder`)

Due passaggi ben distinti:

- **Design (co-design con te)** — l'agente ispeziona il modello, sceglie
  un'identità visiva (tono + firma), classifica ogni pagina in un archetipo
  (executive, operational, analytical, narrative, comparative) con la variante
  di layout adatta ai dati, seleziona i grafici e compone il **design brief**:
  per ogni pagina archetipo, disposizione su griglia, visual con i binding,
  slicer, palette. Il brief ti viene presentato come **proposta** con i punti
  aperti e le alternative: si itera finché non lo approvi. **Nessun file PBIR
  viene scritto prima del tuo ok.**
- **Authoring** — il brief approvato viene tradotto in file PBIR reali in
  `report/<Progetto>.Report/definition/` (un `page.json` per pagina, un
  `visual.json` per visual con binding esatti ai campi del modello), a piccoli
  batch, ognuno validato subito con `powerbi-report-author validate`.
- Chiusura: `validate_report.py <Progetto>` fino a exit 0 (binding esistenti
  nel modello, pagine dei requisiti presenti, visual nel canvas e non
  sovrapposti), poi la tua approvazione.

### Fase 4 — Build e verifica (orchestrator, con te)

Il `.pbix` lo genera **solo Power BI Desktop**, non esiste una "compilazione"
via script:

1. Doppio click su `report/<Progetto>.pbip`
2. In Desktop: **Home → Aggiorna** (importa i dati da `staging/` o `input/`)
3. Verifica con l'orchestrator che pagine e valori corrispondano a
   `output/requirements.md`
4. **File → Salva con nome** → `report/<Progetto>.pbix`

Se Desktop segnala errori all'apertura, la fase competente (2 o 3) non era
davvero conclusa: l'orchestrator la rimanda all'agente giusto.

### Modifiche a un report esistente

Descrivi la modifica all'orchestrator citando il report: lui individua la fase
competente (layout → fase 3, misura/DAX → fase 2, nuovo requisito → fase 1,
dati cambiati → fase 1.5) e riparte da lì, senza rifare le fasi già valide. La
fase modificata riesegue il proprio gate e ti richiede l'approvazione; alla
fine si ripassa sempre dalla fase 4 per rigenerare il `.pbix` (quello vecchio
non si aggiorna da solo).

---

## Struttura del repository

| Cartella/File | Contenuto |
|---|---|
| `.github/agents/` | 5 agenti: `orchestrator` (unico invocabile), `requirements-analyst`, `etl`, `semantic-modeler`, `report-builder` |
| `.github/skills/` | Skill di fase (vedi tabella del flusso) |
| `.github/copilot-instructions.md` | Regole globali sempre caricate: flusso, gate obbligatori, catalogo agenti |
| `.mcp.json` | Config MCP: `powerbi-modeling-mcp` locale (Tier 1 per il modello) |
| `input/` | File forniti da te: requisiti (`.docx`) e dati (`.csv`/`.xlsx`). **Sola lettura** per gli agenti |
| `output/` | Artefatti di fase: `requirements.md`, `model.yaml`, `relationships.yaml`, `design-brief.md` |
| `staging/<Progetto>/` | Dati normalizzati dalla fase 1.5 + `etl-log.md` |
| `report/` | Progetto PBIP: `<Progetto>.pbip`, `<Progetto>.SemanticModel/`, `<Progetto>.Report/` |
| `scripts/` | Script generici del progetto (vedi sotto) — **mai script ad hoc per singolo report** |
| `tests/` | Suite di test degli script (`unittest`, nessuna dipendenza extra) |

---

## Script generici (`scripts/`)

Tutti escono con **exit code 0 = OK**; un codice diverso blocca il passaggio di fase.

| Script | Scopo |
|---|---|
| `convert_input.py` | Converte `.docx` → `.md` e `.xlsx` → `.csv` accanto all'originale in `input/`. Riusa il convertito se aggiornato; `--force` per riconvertire |
| `validate_requirements.py` | **Gate fase 1**: conformità di `output/requirements.md` al template (intestazioni, encoding, KPI atomici, Mapping compilato se ci sono file tabellari) |
| `prepare_staging.py` | Normalizzazioni parametriche di fase 1.5 (date, decimali, booleani, categorici). Config per progetto via `--config`; scrive CSV **e** voce di `etl-log.md` insieme |
| `build_model.py` | Fallback di fase 2 senza MCP: genera l'intera `definition/` TMDL da `output/model.yaml` + `relationships.yaml`, poi lancia da solo `validate_model.py` |
| `validate_model.py` | **Gate fase 2**: indentazione TMDL, tabelle duplicate, partition presenti, copertura di tutte le misure dei requisiti, encoding |
| `validate_report.py` | **Gate fase 3**: coerenza report ↔ modello ↔ requisiti — struttura `pages/`, binding a tabelle/colonne/misure esistenti, pagine dei requisiti presenti, visual nel canvas e non sovrapposti, encoding. Complementare a `powerbi-report-author validate` (schema JSON) |
| `status.py` | Fotografia dello stato: per ogni progetto, evidenze ed esito dei gate fase per fase. Sola lettura, exit sempre 0 |

Uso tipico:

```bash
python scripts/convert_input.py
python scripts/validate_requirements.py
python scripts/validate_model.py <NomeProgetto>
python scripts/validate_report.py <NomeProgetto>
python scripts/status.py
```

### Test degli script (`tests/`)

Gli script in `scripts/` sono i **gate del flusso**: se uno di loro si rompe o
diventa troppo permissivo, le fasi avanzano su artefatti sbagliati senza che
nessuno se ne accorga. La suite in `tests/` (standard `unittest`, nessuna
dipendenza extra) protegge proprio questo: ogni file testa lo script omonimo,
sia sul caso conforme (exit 0) sia sui casi di errore che il gate **deve**
bloccare.

| File di test | Script coperto | Cosa verifica |
|---|---|---|
| `test_convert_input.py` | `convert_input.py` | conversione `.docx` → `.md` (paragrafi e tabelle) e `.xlsx` → `.csv`, riuso del file già convertito |
| `test_validate_requirements.py` | `validate_requirements.py` | il gate di fase 1 accetta un `requirements.md` compilato dal template ufficiale e rifiuta segnaposto non compilati, intestazioni mancanti, KPI non atomici |
| `test_prepare_staging.py` | `prepare_staging.py` | le normalizzazioni di fase 1.5 (decimali italiani `1.234,56`, date, booleani SI/NO): i valori non riconosciuti diventano vuoti, mai indovinati; scrittura CSV + voce di `etl-log.md` |
| `test_validate_model.py` | `validate_model.py` | il gate di fase 2 accetta un TMDL corretto e rifiuta misure dei requisiti mancanti, partition assenti, indentazione errata |
| `test_validate_report.py` | `validate_report.py` | il gate di fase 3 accetta un PBIR coerente col modello e rifiuta binding a campi inesistenti, pagine dei requisiti mancanti, visual fuori canvas o sovrapposti |

I test girano su file temporanei: non toccano `input/`, `output/`, `staging/`
né `report/`. Vanno eseguiti (tutti verdi) dopo **ogni** modifica a `scripts/`:

```bash
python -m unittest discover -s tests
```

---

## Regole fondamentali

1. **Un solo punto d'ingresso**: parli con `orchestrator`; gli agenti di fase
   non si invocano mai direttamente.
2. **Gate + approvazione**: nessuna fase avanza senza il proprio gate a exit 0
   **e** la tua approvazione esplicita in chat. Il gate rende la fase
   completabile; l'approvazione la chiude (le approvazioni non sono tracciate
   su file).
3. **Lo stato vive sul filesystem**: puoi chiudere la chat e riprendere quando
   vuoi; `status.py` ricostruisce il punto esatto.
4. **`input/` è sola lettura**; i dati puliti vanno in `staging/`, gli
   artefatti di fase in `output/`.
5. **Mai TMDL a mano, mai `.pbix` via script**: il modello si costruisce via
   MCP (o `build_model.py`), il `.pbix` lo genera solo Power BI Desktop.
6. **Script generici, non ad hoc**: se manca una casistica si estende lo
   script in `scripts/` (e i suoi test), non si scrive codice usa-e-getta.
7. **Un nuovo report = nuova raccolta requisiti**: `output/requirements.md`
   vale per un solo report; per un report diverso la fase 1 si rifà da capo.
8. **Ambiente solo locale**: Power BI Desktop + VS Code. No Fabric, Azure o
   workspace remoti.

---

## Aggiornare le skill Microsoft in futuro

Le skill `semantic-model-authoring`, `powerbi-report-design` e
`powerbi-report-authoring` derivano da `microsoft/skills-for-fabric`
(plugin `powerbi-authoring`); `powerbi-requirements-gathering` e
`data-cleaning-etl` sono custom di questo progetto e **non vanno sovrascritte**.

```bash
git clone https://github.com/microsoft/skills-for-fabric _tmp/skills-for-fabric
# confronta prima con diff: le skill locali contengono personalizzazioni
diff -r _tmp/skills-for-fabric/plugins/powerbi-authoring/skills/semantic-model-authoring .github/skills/semantic-model-authoring
rm -rf _tmp
```
