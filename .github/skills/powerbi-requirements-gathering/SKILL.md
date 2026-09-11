---
name: powerbi-requirements-gathering
description: >-
  Conduce l'intervista strutturata per la raccolta requisiti di un nuovo
  report Power BI (fase 1 soltanto): audience, dati disponibili, KPI, bozza
  di architettura delle pagine e direzione di design. Produce un unico file
  `output/requirements.md` usato come input approvato per la fase 2
  (modellazione semantica) e la fase 3 (layout/authoring del report). Non
  esegue modifiche al modello, contratti di design o authoring PBIR — questi
  compiti appartengono rispettivamente a `semantic-model-authoring`,
  `powerbi-report-design` e `powerbi-report-authoring`.
  Triggers: "nuovo report", "raccolta requisiti", "cosa vuoi vedere nel
  report", "intervista requisiti".
---

# Skill di Raccolta Requisiti Power BI

Questa skill definisce l'intervista strutturata per la **sola fase 1** di un nuovo report Power BI: comprendere audience, dati, KPI e una bozza di direzione di pagina/design. Si ferma ai requisiti — non progetta un contratto di layout meccanico, non tocca il modello semantico e non esegue authoring di file PBIR.

**Confine di scope** — Questa skill decide *cosa deve realizzare il report e per chi*. Non decide tipi di grafico, griglie di layout, palette colori o DAX. Questi sono di competenza di `powerbi-report-design` (fase 3 design), `semantic-model-authoring` (fase 2 modellazione) e `powerbi-report-authoring` (fase 3 meccanica dei file). Il flusso orchestrato a 4 fasi (`orchestrator` → `requirements-analyst` → `semantic-modeler` → `report-builder`) è l'unico percorso dai requisiti a un report finito; questa skill non deve mai tentare di costruire oltre la propria fase.


## Obbligatorio/Preferire/Evitare

### OBBLIGATORIO

- Fare una domanda alla volta; fermarsi quando la decisione richiesta è chiara.
- Produrre esattamente un file di output: `output/requirements.md`.
- **Ricreare `output/requirements.md` da zero a ogni raccolta requisiti**: se una versione precedente del file esiste (altro report, bozza interrotta, o versione anteriore dello stesso report), cancellarla prima di copiare il template — mai aggiornare o integrare il file esistente.
- Ottenere l'approvazione esplicita dell'utente su `output/requirements.md` prima di passare alla fase 2.
- Fermarsi a una bozza di elenco pagine e una bozza di direzione di design in prosa — non produrre un blocco YAML `Design Brief:` né alcun `layout_contract`. Quello è compito di `report-builder` nella fase 3, in consultazione con `powerbi-report-design`.
- Se manca un'informazione fondamentale per il mapping o l'import (db reale, modalità di connessione, ecc. — vedi [Mapping Requisiti → Schema Target](#mapping-requisiti--schema-target-quando-lo-schema-del-db-target-è-già-disponibile-in-input)), fermarsi e fare domande puntuali sul gap specifico, mai proseguire con ipotesi implicite.
- Il file di output deve contenere sempre le informazioni minime necessarie alla fase 2: obiettivo, audience, sorgente/schema, tabelle/colonne/chiavi, granularità, KPI e gap. Non si può considerare completata la raccolta con una descrizione generica di business.
- Ignorare come fonte una eventuale "soluzione iniziale" già presente nell'input: non va letta né usata per il mapping.

### PREFERIRE

- Deduci le risposte ovvie dal prompt o dai requisiti forniti invece di richiederle di nuovo. Presenta **tutte le deduzioni di un round in un solo riepilogo** e chiedi conferma una volta sola, riservando le domande esplicite ai soli gap genuini.
- Riepiloghi brevi dopo ogni round per validare la comprensione prima di proseguire.
- Domande concrete e chiuse piuttosto che aperte, per velocizzare l'intervista.

### EVITARE

- Non unire o saltare round per andare più veloci.
- Non eseguire modifiche al modello semantico, authoring DAX o scritture di file PBIR — questa skill si limita a intervistare e documentare.
- Non avviare una nuova raccolta su un `output/requirements.md` già approvato senza che l'utente la richieda esplicitamente; quando invece la raccolta (nuova o revisione) è in corso, non conservare né patchare il file precedente — va sempre ricreato da zero dal template.
- Non inventare requisiti che l'utente non ha dichiarato.

## Lettura di File Binari in input/ (docx, xlsx)

Il tool `read` legge solo testo semplice (`.md`, `.txt`, `.csv`, ...): non riesce ad aprire direttamente i file binari Office come `.docx` o `.xlsx`, anche se si trovano nel posto giusto (`input/`). Prima di leggere un file con una di queste estensioni, convertilo con `execute` e leggi il file convertito — mai tentare `read` direttamente sul binario, e mai chiedere all'utente di convertirlo lui: è un passaggio automatico dell'agente.

**Non è un passaggio da presentare all'utente**: è un dettaglio implementativo interno, silenzioso. Non annunciarlo come uno step a sé stante (niente "Ora converto il file...", nessuna approvazione o riepilogo intermedio su di esso). Esegui la conversione, poi passa direttamente al contenuto — la prima cosa visibile all'utente deve essere la sintesi dei requisiti letti dal documento, non la conversione stessa.

**La conversione si fa con lo script generico del progetto, mai con codice ad hoc scritto al momento:**

```bash
python scripts/convert_input.py                # converte tutti i .docx/.xlsx in input/
python scripts/convert_input.py input/Doc.docx # converte solo i file indicati
```

Lo script implementa già tutte le regole di conversione — non riscriverle inline:

- Il file convertito viene scritto **accanto all'originale in `input/`**, stesso nome ma estensione `.md` (per `.docx`, con le tabelle Word rese come tabelle markdown) o `.csv` (per `.xlsx`, un file per foglio `<nome>__<foglio>.csv` se il workbook ne ha più di uno) — visibile e riutilizzabile nelle sessioni successive senza riconvertire.
- Se il convertito esiste già ed è più recente dell'originale, lo script lo riusa (skip automatico); `--force` per riconvertire.
- L'originale non viene mai modificato né cancellato; output sempre UTF-8.
- Se lo script fallisce (exit code 1, errore stampato), fermati e chiedi all'utente un'esportazione in formato testo/CSV, invece di procedere ignorando il contenuto del file — e non ripiegare su script improvvisati one-shot: se manca una casistica, va estesa in `scripts/convert_input.py`, non aggirata.

## Struttura dei Round

Esegui i round seguenti in ordine, uno alla volta. Dopo ogni round, riassumi cosa è stato raccolto e confermalo con l'utente prima di passare al successivo.

### Round 0 — Setup

Obiettivo: assegnare un nome al report (determina il nome delle cartelle `report/<NomeProgetto>.SemanticModel/` e `.Report/` usate dalle fasi successive) e capire se l'utente ha già una lista di requisiti definita o se serve costruirla da zero con l'intervista.

**Prima di chiedere qualunque cosa, ispeziona in autonomia la cartella `input/`** (elenco file, non lettura contenuto) per verificare se contiene già:
- un file tabellare (`.xlsx` o `.csv`) da cui ricavare lo schema del db target — vale sia uno schema esplicito (tabelle/colonne elencate) sia un'**estrazione dati** (ogni file/foglio è una tabella, le intestazioni sono le colonne) — ignora eventuali file che rappresentano solo una "soluzione iniziale"/output preesistente vuoto: non è una fonte valida, trattalo come se non esistesse;
- un file Word (`.docx`) con un documento requisiti già scritto.

Il risultato di questa ispezione determina come si continua il Round 0:
- **Entrambi presenti (file tabellari + documento Word)**: comunicalo all'utente, imposta automaticamente `Modalità di raccolta: requisiti già forniti (fonte: documento Word in input/)` **senza chiederlo** (la fonte è già nota dai file trovati), poi applica direttamente la sezione [Mapping Requisiti → Schema Target](#mapping-requisiti--schema-target-quando-lo-schema-del-db-target-è-già-disponibile-in-input), **Caso A**. Questo NON è un supplemento all'intervista standard: sostituisce le domande generiche dei Round 1/3/4 ovunque il documento Word e l'Excel bastino a dedurre la risposta (vedi le condizioni "già forniti" in cima a ciascun round) — non riproporre come domande informazioni già ricavabili dai file. Le uniche domande ammesse sono quelle sui gap specifici che emergono dal confronto requisito-per-requisito (vedi [Refuso trasversale](#refuso-trasversale-in-entrambi-i-casi)).
- **Manca l'uno o l'altro (o entrambi)**: comunica all'utente cosa manca nello specifico (es. "in `input/` non trovo un file Excel con lo schema tabelle: mi servirebbe per proporre il mapping requisito → colonna") e applica la sezione Mapping, **Caso B** — fai domande mirate solo sul gap rilevato, non un'intervista generica, prima di procedere.

Se invece nessuno dei due file è rilevante per questa richiesta (es. il report non si basa su uno schema target già pronto), prosegui con le domande standard sottostanti.

Chiedi:

> Come vuoi chiamare questo report? Determinerà il nome delle cartelle del progetto (`report/<NomeProgetto>.Report/` e `.SemanticModel/`).

> Hai già una lista di requisiti definita (documento, file, appunti), oppure vuoi che ti proponga io una struttura partendo da zero?

Se l'utente ha già requisiti definiti, chiedi dove si trovano: se sono in un file, chiedigli di **metterlo lui nella cartella `input/`** e poi leggilo prima di proseguire; se preferisce, può scriverli/incollarli direttamente in chat. Questa risposta determina se i Round 1 (Audience e Scopo), 3 (KPI) e 4 (Bozza Pagine) vengono condotti come intervista o dedotti direttamente dai requisiti forniti — vedi le condizioni riportate in cima a ciascun round.

Raccogli:

```markdown
Nome report:
Modalità di raccolta: proposta da zero | requisiti già forniti (fonte: ...)
```

**Criterio di uscita**: il nome del report è fissato e la modalità di raccolta è decisa; se ci sono requisiti già forniti, sono stati acquisiti (file in `input/` o testo in chat).

### Round 1 — Audience e Scopo

**Condizione**: esegui questo round solo se l'utente ha scelto "proponimi una struttura" nel Round 0.

Obiettivo: capire per chi è il report e quale decisione/compito supporta.

Se sia l'audience sia il compito da svolgere sono già chiari dal prompt, riassumi la risposta dedotta invece di chiedere.

Chiedi se l'audience non è chiara:

> Per chi è principalmente questo report?

Scelte raccomandate:

1. Utenti  / leadership — KPI concisi, trend, rischi, decisioni
2. Analisti — esplorazione, drill-down, comparazioni, tabelle
4. Audience esterna — narrazione curata, storytelling guidato, slicer minimi

Poi chiedi solo se il compito da svolgere non è ancora chiaro:

> Cosa dovrebbe aiutarli a fare il report?

Scelte raccomandate:

1. Capire la storia complessiva
2. Monitorare le performance
3. Trovare anomalie o opportunità
4. Confrontare entità o segmenti
5. Prepararsi per una revisione periodica di business

Raccogli:

```markdown
Audience:
Scopo primario:
Tono:
Criteri di successo:
```

**Criterio di uscita**: audience, scopo primario e tono sono fissati o dedotti e confermati dall'utente.

### Round 2 — Dati Disponibili e Granularità

**Condizione**: esegui sempre questo round, indipendentemente dalla modalità scelta nel Round 0 — serve sempre sapere a quale DB agganciarsi e come i dati arriveranno, anche quando l'utente ha già una lista di requisiti pronta. **Eccezione**: se è già attivo il Caso A/B della sezione Mapping (schema target ricavabile dai file tabellari in `input/`), le tabelle sono già note — non richiederle di nuovo qui, popola direttamente `Tabelle/file attesi in input/` elencando i file/fogli tabellari già trovati. In quel caso questo round si riduce alla sola domanda sulla modalità/tipo di connessione al db reale (vedi sotto): finché non hai la risposta, tienila come voce in "Domande Aperte"; appena l'utente risponde, **spostala** in questa sezione (`Tipo di DB` / `Modalità di connessione`) di `output/requirements.md` — "Domande Aperte" è solo per i gap ancora irrisolti al momento della scrittura del file, non un contenitore permanente per l'informazione una volta raccolta.

Obiettivo: stabilire a quale database si deve agganciare il report, con quale modalità di connessione, e quali tabelle servono. Questa sezione è obbligatoria e non può rimanere vuota o generica: il brief deve specificare fonte dati, schema atteso, granularità e gap noti. Il modello semantico non esiste ancora in questa fase — viene creato nella fase 2 — quindi qui non si ispeziona nessuno schema, si raccolgono solo le informazioni che serviranno a costruirlo.

**Prima di chiedere, verifica se l'informazione è già deducibile** da ciò che hai in mano, ed evita di chiedere ciò che è già ricavabile:

- Se in `input/` sono presenti solo file Excel/CSV (nessun riferimento a una connessione live a un database reale) e il documento requisiti/BRD, se presente, descrive i dati come un'estrazione/esportazione periodica da un sistema esterno → deduci `Modalità di connessione: Import` senza chiedere, e valorizza `Tipo di DB` con la fonte descritta (es. "estrazione periodica da tool di ticketing esterno", "file Excel/CSV" se non è nominato uno strumento specifico) invece di lasciarlo vuoto o generico.
- Chiedi esplicitamente solo se **né** i file in `input/` **né** il documento requisiti chiariscono come/da dove arriveranno i dati in produzione (es. nessuna menzione di estrazione, tool sorgente, o tipo di sistema) — in quel caso la domanda resta necessaria e non va saltata.

Se l'informazione non è deducibile, chiedi:

> A quale tipo di database si deve agganciare il report (es. SQL Server, PostgreSQL, Oracle, ecc.) e con quale modalità di connessione (Import o DirectQuery)?

Chiarisci sempre esplicitamente come arriveranno i dati concreti, perché questo agente non si connette mai direttamente alla fonte dati in fase 1:

> Per costruire il modello nella fase 2 mi serve un'estrazione delle tabelle necessarie in formato Excel o CSV, da mettere nella cartella `input/` del progetto. Quali tabelle (o nomi di file) prevedi di fornire?

Non chiedere di descrivere la struttura delle tabelle in dettaglio (colonne, tipi, chiavi) — quel dettaglio si ricava direttamente dai file una volta disponibili in `input/`, in fase 2.

Raccogli le risposte come:

```markdown
Tipo di DB:
Modalità di connessione: Import | DirectQuery

Tabelle/file attesi in input/:
- nome tabella o file, contenuto atteso in una riga (es. "vendite.xlsx — vendite giornaliere per prodotto e area")

Dimensioni previste:
- data/ora, geografia, entità, categoria, responsabile, stato, segmento

Gap noti:
- dati che l'utente vuole ma non ancora disponibili in nessuna tabella/file
```

Chiedi solo per gap o ambiguità genuine, ad es.:

> Hai citato vendite giornaliere per prodotto e area, ma nessuna segmentazione cliente. Ti serve la segmentazione per questo report, o la granularità prodotto/area è sufficiente?

**Criterio di uscita**: tipo di DB, modalità di connessione e l'elenco delle tabelle/file attesi in `input/` sono definiti; i gap noti sono annotati.

### Round 3 — KPI e Metriche Chiave

**Condizione**: esegui questo round solo se l'utente ha scelto "proponimi una struttura" nel Round 0, oppure se ha requisiti già forniti ma questi non elencano già i KPI. Se i KPI sono già specificati in un file in `input/` o nel testo di requisiti incollato in chat, leggili da lì ed estraili invece di fare la domanda, poi riassumili per conferma. **Se è attivo il Caso A/B della sezione Mapping**, non fare questa domanda in nessun caso: i KPI vanno dedotti direttamente dai requisiti atomici già estratti dal documento Word (ogni requisito atomico che esprime una metrica/misura è un candidato KPI) — popola la tabella sotto da quella lista, senza chiedere all'utente "quali sono i KPI". Chiedi solo se, per uno specifico requisito atomico, non è chiaro se rappresenti effettivamente un KPI da mettere in primo piano o un filtro/dettaglio secondario — mai una domanda generica di raccolta KPI.

Obiettivo: identificare i KPI e le metriche che il report deve mostrare, e segnalare quelli che non esistono ancora nel modello.

Chiedi:

> Quali sono i 3-6 KPI che questo report deve mostrare in primo piano?

Per ogni KPI, annota se corrisponde a una misura esistente o va costruito nella fase 2:

```markdown
KPI:
- <nome KPI> — misura esistente: <nome> | serve nuova misura
- ...

Calcoli mancanti segnalati per la fase 2:
- <misura/colonna calcolata necessaria, e perché>
```

**Criterio di uscita**: sono elencati 3-6 KPI, ciascuno marcato come misura esistente o da costruire in fase 2.

### Round 4 — Numero Pagine, Visual Desiderati e Layout (bozza) + Direzione di Design

**Condizione**: esegui questo round solo se l'utente ha scelto "proponimi una struttura" nel Round 0, oppure se ha requisiti già forniti ma questi non indicano già numero di pagine, visual desiderati o layout di massima. Se queste informazioni sono già nei requisiti forniti, salta la domanda su pagine/visual e riassumi quanto dedotto; la domanda sulla direzione di design generale (tono) resta comunque utile da porre se non è già chiara.

Obiettivo: tracciare per ciascuna pagina lo scopo, l'elenco dei visual desiderati (uno per riga, non un unico riepilogo generico) e i filtri/slicer previsti, più una direzione di design generale. Questo non è ancora un layout meccanico pixel-per-pixel né un archetipo grafico (la scelta dell'archetipo visivo resta competenza di `powerbi-report-design` nella fase 3) — ma deve comunque essere specifico: elencare i singoli visual per nome/tipo (es. "line chart trend per periodo", "card KPI soddisfazione media") e i filtri concreti che si applicano a quella pagina, non solo una descrizione sommaria a parole.

Chiedi solo dopo aver applicato ciò che è già noto dai round precedenti:

> Quante pagine ti aspetti? Per ciascuna: qual è lo scopo, quali visual specifici vorresti vedere (es. card KPI, line chart trend, barre per categoria, tabella dettaglio, ecc. — elencali singolarmente) e quali filtri/slicer dovrebbero essere disponibili in quella pagina?

Bozza elenco pagine, con visual e filtri elencati singolarmente per pagina (non un layout meccanico con coordinate/griglia — quello resta compito di `report-builder` in fase 3, ma l'elenco di visual e filtri per pagina va comunque specificato qui):

```markdown
Bozza pagine:
1. <Nome pagina> — scopo: <a cosa serve questa pagina>
   - Visual: <primo visual desiderato>
   - Visual: <secondo visual desiderato>
   - Visual: <altri visual, uno per riga; marcare "(opzionale)" se non essenziale>
   - Filtri: <elenco filtri/slicer proposti per questa pagina>
2. ...
```

Chiedi la direzione di design generale, incluse preferenze concrete se l'utente le ha (tono, palette/uso del colore a livello concettuale, disposizione generale degli elementi in pagina) — senza però arrivare a coordinate, griglie pixel o specifiche di canvas:

> Che sensazione dovrebbe dare questo report? (es. pulito ed executive, denso e analitico, narrativo e story-driven) E hai preferenze di massima su come disporre gli elementi (es. KPI in alto, filtri sempre visibili) o su come usare i colori (es. un colore per canale/priorità)?

Raccogli:

```markdown
Direzione di design (bozza, in prosa ma con indicazioni concrete se disponibili):
- Tono:
- Note/preferenze: <es. disposizione generale degli elementi, uso del colore per distinguere categorie/priorità/canali, densità informativa desiderata>
```

Restano fuori scope solo il blocco YAML `Design Brief:`, coordinate/griglie precise o un `layout_contract` vero e proprio — quelli sono compito di `report-builder`/`powerbi-report-design` in fase 3. Indicazioni di stile in prosa (anche se concrete) sono invece incoraggiate qui, se l'utente le fornisce o se sono deducibili dal contesto.

**Criterio di uscita**: per ogni pagina esistono scopo, elenco di visual specifici (non un'unica descrizione generica) e filtri proposti; esiste inoltre una direzione di design in prosa (tono + note concrete su stile/colori/impaginazione generale). Non è richiesto un layout meccanico con coordinate/griglia pixel-per-pixel: quello resta compito di `report-builder` in fase 3.

## Mapping Requisiti → Schema Target (quando in input/ ci sono file tabellari)

Questa sezione si applica a un caso distinto dal normale Round 2: quando in `input/` sono già presenti uno o più **file tabellari** (`.xlsx` o `.csv`) da cui ricavare le tabelle/colonne dello schema del db target. Valgono **entrambe** le forme:

- **schema esplicito** — un workbook che elenca tabelle e colonne del db target;
- **estrazione dati** — file di dati veri e propri: ogni file (o foglio Excel) è una tabella, le **intestazioni di colonna** sono le colonne dello schema.

**Un'estrazione dati NON è un motivo per saltare il mapping**: lo schema si ricava dalle intestazioni. Scrivere "Non applicabile: solo un estratto CSV dei dati" è esattamente l'errore da non ripetere — il mapping è "Non applicabile" solo quando in `input/` non c'è **alcun** file tabellare.

In questo caso, oltre alla normale raccolta requisiti, produci anche una proposta di mapping requisito → tabella/colonna con relativa verifica di allineamento. Questa attività si aggiunge ai Round 0-4 quando lo schema è ricavabile dai file in ingresso; se invece non è disponibile alcun file tabellare, il dettaglio colonne resta compito della fase 2 (`semantic-modeler`), come già previsto dal Round 2.

### Fonte da ignorare

Se nell'input è presente anche una "soluzione iniziale" (una proposta di mapping o di modello preesistente), **non leggerla e non usarla come fonte**: è vuota/segnaposto e va ignorata. Le uniche fonti valide per il mapping sono il documento requisiti (se fornito) e i file Excel dello schema target.

### Caso A — Il documento requisiti è fornito

1. Leggi lo schema target dai file tabellari in `input/`: da uno schema esplicito, le tabelle/colonne elencate; da un'estrazione dati, ogni file/foglio è una tabella e le intestazioni di colonna sono le colonne dello schema.
2. Leggi il documento dei requisiti e **spezzalo in requisiti atomici** (un'esigenza verificabile per voce).
3. Per ciascun requisito atomico:
   - proponi quale tabella/colonna dello schema target usare;
   - verifica se la colonna proposta è effettivamente allineata al requisito (tipo dato, naming, granularità, ecc.) e segnala eventuali disallineamenti.
4. Se dal documento requisiti non emerge chiaramente come si lavorerà in fase di import (es. manca il tipo di db reale a cui ci si collegherà, o la modalità/tipo di connessione), **non assumere né inventare**: fai domande specifiche solo su quei punti mancanti, mai un'intervista generica — quelle informazioni non sono deducibili né dai requisiti né dallo schema.

### Caso B — Il documento requisiti NON è fornito

Non procedere per supposizioni. Fai domande specifiche e mirate per raccogliere i requisiti mancanti (mai domande generiche o aperte) — usa lo schema target già disponibile in `input/` per rendere le domande concrete (es. riferisciti a tabelle/colonne reali invece di chiedere in astratto "che dati ti servono?"). Solo dopo aver raccolto le risposte, procedi con la stessa logica del Caso A (spezzare in requisiti atomici → proposta tabella/colonna → verifica allineamento).

### Refuso trasversale (in entrambi i casi)

Fermati e chiedi — non proseguire mai con ipotesi implicite — in ciascuno di questi casi:

- **Manca lo schema/le colonne della sorgente dati**: non è disponibile in `input/` alcun file tabellare (`.xlsx`/`.csv`, schema esplicito o estrazione dati) da cui ricavare tabelle/colonne del db target, o è ambiguo quale file rappresenti quale tabella.
- **Manca la modalità/tipo di connessione al db reale**: non è chiaro il tipo di db a cui ci si collegherà in fase di import, o la modalità (Import/DirectQuery), quando questa informazione servirà alla fase 2.
- **Il requisito è ambiguo rispetto alle tabelle disponibili**: per un requisito atomico non è possibile proporre un match tabella/colonna affidabile (più colonne candidate senza un criterio per scegliere, oppure nessuna colonna sembra corrispondere).

In ogni caso, le domande devono essere puntuali e riferite al gap specifico individuato, mai un questionario generico. Riporta queste domande aperte (se presenti) in una sotto-sezione ben visibile dentro **Mapping Requisiti → Schema Target** di `output/requirements.md`, così l'orchestrator non delega alla fase 2 finché non sono risolte.

### Output

Aggiungi a `output/requirements.md` la sezione **Mapping Requisiti → Schema Target**, con una riga per requisito atomico:

```markdown
## Mapping Requisiti → Schema Target
| Requisito atomico | Tabella.Colonna proposta | Allineato? | Note |
|---|---|---|---|
| <requisito> | <Tabella.Colonna> | Sì / No | <motivo se No: tipo dato, naming, granularità...> |

### Domande Aperte
<presente solo se sono emersi gap bloccanti — vedi Refuso trasversale; l'orchestrator non passa alla fase 2 finché questa lista non è vuota o risolta in chat>
- <domanda puntuale sul gap specifico>
```

Questa sezione si aggiunge a quelle previste dal template quando questa modalità è applicabile — non sostituisce il Round 2, che resta la fonte di verità per i casi in cui lo schema del db target non è ancora disponibile in ingresso.

### Elaborazione incrementale per file grandi

Quando converti o leggi i file di `input/` (schema Excel o documento Word) per il mapping, tieni conto della gestione dei token: se un file convertito è grande (molti fogli/tabelle nell'Excel, molte pagine nel Word), non caricarlo tutto in un solo colpo — elaboralo a blocchi (es. un foglio Excel alla volta, o il documento Word diviso per sezioni/capitoli), riassumendo via via i requisiti atomici e le proposte di mapping già estratte prima di passare al blocco successivo. Convalida sempre il flusso partendo da file piccoli prima di applicarlo a input di grandi dimensioni.

## Vincoli, Rischi, Note (trasversale)

In qualsiasi round può emergere un vincolo, un rischio o una nota che non rientra nelle sezioni tipizzate (es. una scadenza, un limite di licenza, una dipendenza da un dato non ancora disponibile, una preferenza organizzativa). Annota tutto questo nella sezione **Vincoli, Rischi, Note** di `output/requirements.md`: è la sezione di raccolta per ciò che è rilevante ma non appartiene a un round specifico. Non serve un round dedicato — popolala man mano che le informazioni affiorano.

## Output

Produci esattamente un file: `output/requirements.md`, contenente le informazioni raccolte in tutti i round.

**Procedura vincolata (non facoltativa): parti sempre da una copia letterale del file, mai da una riscrittura a memoria.**

1. Come **primissima azione** quando è il momento di scrivere l'output (non prima, non "a mente" durante l'intervista): se `output/requirements.md` esiste già — per qualunque motivo: report precedente, bozza interrotta, versione anteriore dello stesso report — **cancellalo**, poi esegui letteralmente una copia del file `.github/skills/powerbi-requirements-gathering/assets/requirements-template.md` in `output/requirements.md` usando il tool `execute` con una **copia binaria**: `Copy-Item` in PowerShell, `cp` in bash, `shutil.copyfile` in Python. **Mai** `Get-Content`/`Set-Content`, redirezione `>` o rilettura+riscrittura del testo: su Windows corrompono gli accenti UTF-8 (es. `Granularità` → `GranularitÃ`), e un titolo corrotto non è più identico al template. Subito dopo la copia, **verifica che sia andata a buon fine** (exit code 0 e `output/requirements.md` esistente): se fallisce — path errato, template non trovato — fermati e risolvi il problema, non ripiegare mai sulla riscrittura dei titoli a mano. La copia deve partire da un file pulito: mai sovrascrivere parzialmente, integrare o "riciclare" contenuto del file esistente — non ricopiare i titoli "a memoria" scrivendo il file da zero con un editor di testo: usa un comando di copia reale, in modo che i titoli e la loro struttura esatta (incluso l'ordine, `##` vs `###`, e il segnaposto `## Mapping Requisiti → Schema Target` anche quando non applicabile) siano garantiti bit-per-bit identici al template.
2. Da quel file copiato, **modifica solo il testo sotto ciascuna intestazione** con quanto raccolto nei round corrispondenti, usando il tool di editing file (che preserva l'encoding UTF-8) — mai `Set-Content`/`Out-File` senza encoding esplicito. Non toccare mai le righe `#`/`##`/`###` stesse: non rinominarle, non riordinarle, non aggiungerne, non rimuoverne. Se una sezione non si applica (es. "Mapping Requisiti → Schema Target" solo quando in `input/` non c'è **alcun** file tabellare — un'estrazione dati CSV/Excel È uno schema valido, ricavato dalle intestazioni), lascia l'intestazione al suo posto e scrivi sotto una nota breve tipo "Non applicabile: nessun file tabellare in input/" invece di cancellare la sezione.
3. Se in qualunque momento ti accorgi di aver scritto `output/requirements.md` senza essere partito da questa copia letterale (es. lo hai generato con l'editor a partire da una bozza mentale della struttura), **fermati, cancella il file e ripeti dal passo 1** — non provare a "correggere a posteriori" i titoli di un file già scritto a mano libera: è esattamente il modo in cui in passato sono comparsi titoli numerati inventati al posto di quelli del template.
4. **Ogni sezione va scritta una volta sola, per intero, in un unico edit.** Quando compili il testo sotto un'intestazione, sostituisci tutto il segnaposto/contenuto esistente di quella sezione con la versione completa e definitiva raccolta fino a quel round — non limitarti ad "aggiungere in fondo" nuove righe lasciando quelle vecchie, e non lasciare la stessa intestazione vuota mentre il suo contenuto compare più sotto sparso tra altre sezioni. Se in un round successivo emergono nuove informazioni per una sezione già compilata (es. l'utente corregge o integra un round precedente), **riscrivi l'intera sezione da capo con il testo aggiornato**, sostituendo la versione precedente — non giustapporre un secondo blocco. Ogni frase del file deve stare fisicamente sotto la propria intestazione e non deve esistere più di un blocco di contenuto per la stessa intestazione nel file finale.
5. Non lasciare mai affermazioni contraddittorie tra loro nello stesso file (es. "Non applicabile" seguito più sotto da un elenco popolato per la stessa sezione): se una sezione è compilabile, compilala per intero e rimuovi qualunque "Non applicabile" residuo di una bozza precedente.

Questo non è una linea guida stilistica: se il file finale non ha le stesse intestazioni del template (incluso "Dati Disponibili e Granularità" con `Tipo di DB` / `Modalità di connessione`, valorizzata o messa in "Domande Aperte" se ignota), la fase 1 non è completa.

### Cosa NON scrivere mai in `output/requirements.md`

Questo output descrive **cosa serve**, non **come costruirlo**: la modellazione è compito esclusivo della fase 2 (`semantic-modeler`). Di conseguenza:

- **Non inventare né scrivere formule DAX** (misure complete con `SUM`, `CALCULATE`, `SUMX`, ecc.): per ogni KPI/metrica limitati a segnalare in linguaggio naturale se serve una nuova misura e su quale dato si baserebbe — la formula la scrive `semantic-modeler` in fase 2.
- **Non inventare nomi di tabelle o schema a stella** (es. `FactSales`, `DimDate`, `DimProduct`) se non sono i nomi reali dei fogli/tabelle trovati in `input/`. Usa sempre e solo i nomi effettivi (es. i fogli `Vendite`, `Prodotti`, `Negozi` se sono quelli presenti nell'Excel) — decidere fact/dimension, naming e relazioni del modello è competenza della fase 2, non di questo output.
- **Non scrivere una sezione "Relazioni e modello"** o equivalente: le relazioni tra tabelle le stabilisce `semantic-modeler`, non `requirements-analyst`.
- **Non "concordare" tu KPI o mapping**: per ogni requisito atomico proponi il match e verificane l'allineamento (vedi Mapping Requisiti → Schema Target), ma quando l'allineamento non è chiaro o manca un dato, fermati e chiedi — non decidere al posto dell'utente.

## Esempio Completo di Output (few-shot)

Questo è un esempio reale e approvato di `output/requirements.md`, prodotto nel Caso A (schema Excel + documento Word già entrambi disponibili in `input/`). Usalo come riferimento diretto per il livello di dettaglio atteso in ogni sezione — in particolare per "Numero Pagine, Visual Desiderati e Layout" (un `Visual:` per riga, sempre seguito da `Filtri:`) e per "Direzione di Design" (note concrete su disposizione e uso del colore, non solo aggettivi generici). Non copiare contenuti specifici di questo esempio (nomi di tabelle, KPI, pagine) in un progetto diverso: replica solo la **struttura, la granularità e lo stile di scrittura**, popolandoli con i dati reali del progetto corrente.

```markdown
# Requisiti del Report

## Setup
- Nome report: Assistenza Clienti
- Modalità di raccolta: requisiti già forniti (fonte: `input/BRD_Report_BI_Assistenza_ClickHelp.docx` + `input/Base_Dati_Assistenza_ClickHelp.xlsx`)

## Audience e Scopo
- Audience: responsabile del supporto, team leader del supporto, management aziendale
- Scopo primario: monitorare in modo continuativo il volume e l'andamento dei ticket di assistenza, il tempo di risoluzione, il carico di lavoro degli agenti e dei team, e la soddisfazione dei clienti
- Tono: operativo-analitico, chiaro e immediato, con enfasi su KPI rapidi e trend utili all'azione
- Criteri di successo: riduzione del reporting manuale, visibilità rapida su ticket aperti/chiusi e tempo di risoluzione, identificazione di agenti/team ad alto carico, capacità di individuare categorie e clienti più impattanti, gestione corretta dei valori mancanti di soddisfazione

## Dati Disponibili e Granularità
- Tipo di DB: estrazione periodica da tool di ticketing (attualmente fornito come Excel di esempio)
- Modalità di connessione: Import
- Tabelle/file attesi in input/:
  - `Base_Dati_Assistenza_ClickHelp.xlsx` con fogli:
    - `Ticket`
    - `Agenti`
- Gap noti:
  - Non è definita una connessione diretta al tool di ticketing reale; servono conferme su come verranno forniti i dati in produzione
  - Il foglio `Ticket` contiene `Soddisfazione` parziale (52 valori mancanti) e la reportistica deve gestire questi casi senza distorcere la media
  - Non è presente una tabella clienti separata; il campo `Cliente` è attualmente disponibile solo nel foglio `Ticket`
  - Non sono richieste SLA contrattuali né assegnazione automatica dei ticket in questa prima versione

## Mapping Requisiti → Schema Target
| Requisito atomico | Tabella.Colonna proposta | Allineato? | Note |
|---|---|---|---|
| Monitorare quanti ticket sono aperti e chiusi | Ticket.ID_Ticket, Ticket.Data_Apertura, Ticket.Data_Chiusura | Sì | `Data_Chiusura` null indica ticket ancora aperto; serve calcolare backlog e stato aperto/chiuso |
| Calcolare il tempo di risoluzione dei ticket | Ticket.Tempo_Risoluzione_Ore | Sì | Misura media/mediana e distribuzione per categoria/priorità/team |
| Analizzare il peso delle categorie di problemi | Ticket.Categoria | Sì | Categorie includono Bug Software, Domanda Fatturazione, Problema Accesso, ecc. |
| Misurare il carico di lavoro per agente e per team | Ticket.Agente + Agenti.Team | Sì | `Agente` è presente in Ticket; `Team` è su Agenti con relazione many-to-one |
| Monitorare la soddisfazione clienti | Ticket.Soddisfazione | Sì | Gestire i valori mancanti e calcolare media solo sui ticket valutati |
| Filtrare per canale del ticket | Ticket.Canale | Sì | Canali: Email, Portale Self-Service, Chat, Telefono |
| Analizzare la priorità dei ticket | Ticket.Priorita | Sì | Priorità: Bassa, Media, Alta, Critica |
| Identificare i clienti più attivi | Ticket.Cliente | Sì | Cliente può essere usato come attributo di dimensione cliente nel report |
| Segmentare i ticket per periodo e trend | Ticket.Data_Apertura, Ticket.Data_Chiusura | Sì | Permette trend mese su mese e confronto periodi |
| Gestire dati anagrafici agenti | Agenti.Agente, Agenti.Team, Agenti.Data_Assunzione | Sì | Utili per analisi agenti, carico e storico team |

### Domande Aperte
- Come verranno forniti i dati di produzione dal tool di ticketing: come file Excel estratto, tabella database o altra integrazione?
- Il campo `Cliente` deve essere trattato come dimensione a sé stante oppure si mantiene solo come attributo della tabella `Ticket`?
- È necessario supportare un concetto di ticket aperto con `Data_Chiusura` assente oppure si può assumere che tutti i ticket chiusi abbiano una data valorizzata?

## KPI e Metriche Chiave
- KPI (esistenti vs. che necessitano nuove misure):
  - Numero ticket aperti / numero ticket chiusi — richiede misura sui ticket e stato aperto/chiuso
  - Backlog ticket aperti — richiede calcolo su ticket senza data di chiusura
  - Tempo medio di risoluzione — nuova misura su `Tempo_Risoluzione_Ore`
  - Tempo mediano di risoluzione — nuova misura per robustezza
  - Numero ticket per agente / per team — nuove misure di conteggio
  - Soddisfazione media clienti — nuova misura su `Soddisfazione` con esclusione dei valori null
  - Ticket per categoria, canale, priorità — misure/visual basate su attributi esistenti
  - Top clienti per numero ticket — misura di ranking
- Calcoli mancanti segnalati per la fase 2:
  - Conteggio ticket distinti (`ID_Ticket`)
  - Stato ticket aperto/chiuso basato su `Data_Chiusura`
  - Media e mediana del tempo di risoluzione
  - Media di soddisfazione cliente con gestione dei valori mancanti
  - Metriche di distribuzione per agente/team/categoria/canale/priorità

## Numero Pagine, Visual Desiderati e Layout
1. Executive Summary — scopo: visione sintetica dei KPI, trend e anomalie.
   - Visual: card KPI (ticket aperti, chiusi, tempo medio di risoluzione, soddisfazione media)
   - Visual: line chart trend ticket aperti/chiusi per periodo
   - Visual: barra o donut per canale ticket
   - Visual: barra per priorità o categoria
   - Filtri: periodo, canale, priorità, agente/team
2. Analisi Agenti e Team — scopo: carico operativo e performance dei collaboratori.
   - Visual: barre per numero ticket per agente e per team
   - Visual: tabella dettagliata dei ticket recenti con stato, categoria, canale, agente
   - Visual: scatter/heatmap per tempo di risoluzione vs. priorità (opzionale)
   - Filtri: periodo, team, agente, categoria
3. Qualità e Clienti — scopo: soddisfazione e clienti più attivi.
   - Visual: KPI soddisfazione media e percentuale ticket valutati
   - Visual: top clienti per numero ticket
   - Visual: barre per soddisfazione media per categoria o agente
   - Filtri: periodo, canale, categoria

## Filtri/Slicer
- Periodo (Data_Apertura) — globale
- Canale — globale
- Priorità — globale
- Team / Agente — specifico per pagina Analisi Agenti e Team
- Categoria — specifico per pagine Analisi Agenti e Team, Qualità e Clienti

## Direzione di Design (bozza)
- Tono: operativo e professionale, con focus su numeri chiari e confronti periodici
- Note/preferenze: layout a colonne nette, KPI in alto, filtri subito visibili, uso di colori distinti per canale/priorità senza sovracaricare la pagina

## Vincoli, Rischi, Note
- Vincolo: prima versione senza RLS granulare, chi ha accesso vede tutti i dati
- Vincolo: aggiornamento dati giornaliero con import da estrazione periodica
- Rischio: i valori mancanti di `Soddisfazione` possono falsare la percezione se non vengono gestiti come `non rilevato`
- Nota: il report non deve includere SLA contrattuali né logica di assegnazione automatica dei ticket in questa release iniziale
```

## Autoverifica Obbligatoria Prima di Mostrare l'Output

Prima di presentare `output/requirements.md` all'utente o di chiedere approvazione, **scrivi per intero, come testo del tuo turno (non solo nel ragionamento interno), la checklist seguente compilata riga per riga**. Non è un controllo da fare "a mente": se la checklist non compare scritta esplicitamente prima dell'output, l'autoverifica non è stata eseguita e il file non può essere considerato pronto.

```
CHECKLIST CONFORMITÀ TEMPLATE — output/requirements.md
[ ] Ho copiato output/requirements.md a partire da .github/skills/powerbi-requirements-gathering/assets/requirements-template.md con un comando reale (execute), non riscritto i titoli a memoria: Sì/No → 
[ ] Il comando di copia è andato a buon fine (exit code 0 e output/requirements.md creato)? Sì/No → 
[ ] La copia è stata binaria (Copy-Item/cp/shutil.copyfile) e i caratteri accentati nei titoli sono integri (es. "Granularità", non "GranularitÃ")? Sì/No → 
[ ] Riga 1 template "## Setup"                                          → titolo effettivo nel file: ____________________  → identico? Sì/No
[ ] Riga 2 template "## Audience e Scopo"                                → titolo effettivo nel file: ____________________  → identico? Sì/No
[ ] Riga 3 template "## Dati Disponibili e Granularità"                  → titolo effettivo nel file: ____________________  → identico? Sì/No
[ ] Riga 4 template "## Mapping Requisiti → Schema Target"               → titolo effettivo nel file: ____________________  → identico? Sì/No
[ ] Riga 5 template "## KPI e Metriche Chiave"                           → titolo effettivo nel file: ____________________  → identico? Sì/No
[ ] Riga 6 template "## Numero Pagine, Visual Desiderati e Layout"       → titolo effettivo nel file: ____________________  → identico? Sì/No
[ ] Riga 7 template "## Filtri/Slicer"                                  → titolo effettivo nel file: ____________________  → identico? Sì/No
[ ] Riga 8 template "## Direzione di Design (bozza)"                    → titolo effettivo nel file: ____________________  → identico? Sì/No
[ ] Riga 9 template "## Vincoli, Rischi, Note"                          → titolo effettivo nel file: ____________________  → identico? Sì/No
[ ] Esistono nel file titoli ## o ### assenti da questo elenco (numerazione propria, sezioni improvvisate tipo "Ipotesi sui dati", "Esigenze di pulizia dati", "### Domande Aperte" è l'unica sotto-sezione ammessa)? Sì/No → se Sì, quali: ____________________
[ ] Per ciascuna delle 9 intestazioni sopra, esiste un SOLO blocco di contenuto nel file (nessuna intestazione appare vuota mentre il suo contenuto è scritto altrove, nessun secondo blocco che ripete/aggiorna una sezione già compilata più sopra o più sotto)? Sì/No → se No, quali intestazioni hanno contenuto duplicato o spaiato: ____________________
[ ] Nessuna riga o tabella nel file è "orfana" (es. intestazione di tabella markdown senza righe dati sopra/sotto di pertinenza, bullet isolato che non appartiene alla sezione in cui si trova fisicamente)? Sì/No
[ ] Nessuna sezione contiene affermazioni tra loro contraddittorie (es. "Non applicabile" seguito da un elenco popolato per la stessa sezione)? Sì/No
ESITO: CONFORME solo se ogni riga ha la risposta attesa: Sì ovunque, TRANNE la riga "Esistono nel file titoli ## o ### assenti da questo elenco", che deve essere No. Altrimenti: NON CONFORME.
```

Regole:
1. Compila ogni riga leggendo davvero `.github/skills/powerbi-requirements-gathering/assets/requirements-template.md` e il file appena scritto — non dare per scontato il valore, scrivi il titolo effettivo che hai trovato.
2. Se anche una sola riga risulta fuori dall'esito atteso → l'esito è NON CONFORME: **non mostrare il file né chiedere approvazione**. Cancella `output/requirements.md`, ripeti il passo 1 della sezione [Output](#output) (copia letterale via `execute` del template, poi compilazione sotto le intestazioni esistenti, una sola volta per sezione come da regola 4-5 sopra) e ripeti da capo questa checklist su file rigenerato.
3. Con ESITO: CONFORME, esegui infine il gate deterministico: `python scripts/validate_requirements.py` via `execute`. Lo script riverifica intestazioni, encoding, segnaposto residui, campi chiave e la presenza del Mapping quando in `input/` ci sono file tabellari. Solo con **exit code 0** passa al Gate di Approvazione sottostante; se fallisce, rigenera il file dal template seguendo gli errori elencati e ripeti checklist + script.

Questo controllo va reso visibile ed esplicito apposta: un confronto "mentale" o discorsivo ("segui il template", "confronta i titoli") si è già dimostrato insufficiente più volte a evitare titoli inventati o sezioni mancanti (es. `## Mapping Requisiti → Schema Target` omessa, `## Vincoli, Rischi, Note` assente, numerazione propria al posto dei titoli del template) — costringere a scrivere la checklist riga per riga, con il titolo trovato affiancato a quello atteso, rende visibile ed evidente uno scostamento che altrimenti passerebbe inosservato.

## Gate di Approvazione

Dopo aver scritto `output/requirements.md`, fai esattamente una domanda di approvazione:

> Approvi questi requisiti così possiamo passare alla fase di modello semantico?

Non passare a `semantic-modeler`/fase 2 finché l'utente non approva. Se l'utente richiede modifiche, rivedi `output/requirements.md` e chiedi di nuovo.