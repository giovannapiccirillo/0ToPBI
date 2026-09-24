---
name: powerbi-requirements-gathering
description: >-
  Conduce l'intervista strutturata per la raccolta requisiti di un nuovo
  report Power BI (fase 1 soltanto): audience, dati disponibili, KPI, bozza
  di architettura delle pagine e direzione di design. Produce un unico file
  `output/<NomeProgetto>/requirements.md` usato come input approvato per la fase 4
  (modellazione semantica) e la fase 5 (layout/authoring del report). Non
  esegue modifiche al modello, contratti di design o authoring PBIR 
  Triggers: "nuovo report", "raccolta requisiti", "cosa vuoi vedere nel
  report", "intervista requisiti".
---

# Skill di Raccolta Requisiti Power BI

Questa skill definisce l'intervista strutturata per la **sola fase 1** di un nuovo report Power BI: comprendere audience, dati, KPI e una bozza di direzione di pagina/design — cioè decide *cosa deve realizzare il report e per chi*. Non decide tipi di grafico, griglie di layout, palette colori o DAX, non progetta un contratto di layout meccanico, non tocca il modello semantico e non esegue authoring di file PBIR: quelle sono competenza di `powerbi-report-design` (fase 5 design), `semantic-model-authoring` (fase 4 modellazione) e `powerbi-report-authoring` (fase 5 meccanica dei file). Il flusso orchestrato a 6 fasi (`orchestrator` → `requirements-analyst` → `data-analyst` → `etl-resolver` → `semantic-modeler` → `report-builder`) è l'unico percorso dai requisiti a un report finito; questa skill non deve mai tentare di costruire oltre la propria fase.


## Obbligatorio/Preferire/Evitare

### OBBLIGATORIO

- Fare una domanda alla volta; fermarsi quando la decisione richiesta è chiara.
- Produrre esattamente un file di output: `output/<NomeProgetto>/requirements.md`.
- **Ricreare `output/<NomeProgetto>/requirements.md` da zero a ogni raccolta requisiti**: se una versione precedente del file esiste (altro report, bozza interrotta, o versione anteriore dello stesso report), cancellarla prima di copiare il template — mai aggiornare o integrare il file esistente **di una raccolta precedente**.
- **Compilare il file progressivamente durante l'intervista, non solo alla fine**: copiare il template al Round 0 (non a fine sessione) e scrivere ogni sezione non appena il round corrispondente viene confermato dall'utente — vedi [Output](#output). Le risposte non restano solo in conversazione: il file sul disco è lo stato di avanzamento reale.
- Ottenere l'approvazione esplicita dell'utente su `output/<NomeProgetto>/requirements.md` prima di passare alla fase 2 (analisi dati).
- Fermarsi a una bozza di elenco pagine e una bozza di direzione di design in prosa — non produrre un blocco YAML `Design Brief:` né alcun `layout_contract`. Quello è compito di `report-builder` nella fase 5, in consultazione con `powerbi-report-design`.
- Se manca un'informazione fondamentale per l'import (db reale, modalità di connessione, ecc. — vedi [Mapping Requisiti → Schema Target](#mapping-requisiti--schema-target)), fermarsi e fare domande puntuali sul gap specifico, mai proseguire con ipotesi implicite.
- **Non ispezionare mai lo schema reale** (intestazioni di file `.xlsx`/`.csv` in `input/<NomeProgetto>/`, o un Lakehouse Fabric) per dedurre un match `Tabella.Colonna`: leggere lo schema è compito esclusivo di `data-analyst` in fase 2. Un match va riportato solo se è dichiarato esplicitamente nei requisiti stessi (documento o utente).
- Il file di output deve contenere sempre le informazioni minime necessarie alle fasi successive: obiettivo, audience, sorgente/schema, tabelle/colonne/chiavi, granularità, KPI e gap. Non si può considerare completata la raccolta con una descrizione generica di business.
- **Considera tutto ciò che è presente in `input/<NomeProgetto>/`** come fonte utile per la raccolta requisiti, inclusa un'eventuale bozza di soluzione/modello preesistente: qualunque contenuto proposto va comunque riverificato da `data-analyst` in fase 2, quindi non c'è motivo di escluderlo a priori. La lettura del contenuto avviene nei round che la richiedono (mai all'ispezione iniziale di `input/`, che resta solo elenco file — vedi `requirements-analyst.agent.md`). Resta fermo il divieto di dedurre autonomamente un match `Tabella.Colonna` ispezionando schemi (vedi sopra): un mapping già proposto in un file di input va riportato come "Da confermare in fase 2", non come dichiarazione dell'utente.
- **Nessuna sezione resta con un valore implicito quando il round è chiuso**:
  - Campi che vanno **sempre chiesti/dedotti** (Audience e Scopo, Dati Disponibili, KPI): se l'utente non risponde o non lo sa, scrivi `Non specificato` — non saltare la domanda solo perché prevedi questa via d'uscita, provaci prima.
  - Sezioni **genuinamente condizionali** (Mapping Requisiti, Domande Aperte, Gap noti, Vincoli/Rischi/Note): se al termine del round non emerge nulla di rilevante, scrivi `Non applicabile` seguito dal motivo in breve (es. `Non applicabile: nessuna fonte-schema disponibile`).

  Le regole meccaniche su come si scrive materialmente ogni sezione (placeholder vuoti, intestazioni intoccabili, una sola riscrittura per sezione) sono responsabilità dell'agente — vedi "Come Scrivo il File" in `requirements-analyst.agent.md`.

### PREFERIRE

- Deduci le risposte ovvie dal prompt o dai requisiti forniti invece di richiederle di nuovo. Presenta **tutte le deduzioni di un round in un solo riepilogo** e chiedi conferma una volta sola, riservando le domande esplicite ai soli gap genuini. **Nessuna deduzione va scritta nel file senza questa conferma esplicita**: dedurre serve solo a evitare di riproporre come domanda un'informazione già ricavabile, mai a saltare la conferma dell'utente.
- Riepiloghi brevi dopo ogni round per validare la comprensione prima di proseguire.
- Domande concrete e chiuse piuttosto che aperte, per velocizzare l'intervista.

### EVITARE

- Non unire o saltare round per andare più veloci.
- Non eseguire modifiche al modello semantico, authoring DAX o scritture di file PBIR — questa skill si limita a intervistare e documentare.
- Non avviare una nuova raccolta su un `output/<NomeProgetto>/requirements.md` già approvato senza che l'utente la richieda esplicitamente; quando invece la raccolta (nuova o revisione) è in corso, non conservare né patchare il file precedente — va sempre ricreato da zero dal template.
- Non inventare requisiti che l'utente non ha dichiarato.

## Struttura dei Round

Esegui i round seguenti in ordine, uno alla volta. Dopo ogni round, riassumi cosa è stato raccolto e confermalo con l'utente prima di passare al successivo.

**Principio comune di condizione (Round 1, 3, 4)**: esegui la domanda del round solo se l'utente ha scelto "proponimi una struttura" nel Round 0, oppure se ha requisiti già forniti ma questi non coprono già l'informazione specifica del round (audience/scopo, KPI, pagine/visual — vedi la condizione di ciascun round per il dettaglio). Se l'informazione è già nei requisiti forniti, salta la domanda e riassumi quanto dedotto invece di richiederla.

### Round 0 — Setup

Obiettivo: assegnare un nome al report (determina il nome delle cartelle `report/<NomeProgetto>.SemanticModel/` e `.Report/` usate dalle fasi successive) e capire se l'utente ha già una lista di requisiti definita o se serve costruirla da zero con l'intervista.

**La Domanda di Apertura** (definita nell'agente `requirements-analyst`, non in questa skill) precede questo round: l'agente ispeziona già `input/<NomeProgetto>/` e chiede all'utente se ci sono **altre fonti da aggiungere** — requisiti in chat, altri file, e/o tabelle su Fabric. Le fonti **non sono esclusive**: possono coesistere più fonti insieme (es. un documento Word in `input/`, requisiti aggiuntivi dettati in chat, e alcune tabelle su un Lakehouse Fabric). Non richiedere qui informazioni già emerse da quella domanda.

**Fonti da tracciare, ciascuna indipendentemente presente o assente:**
- **Requisiti**: documento (`.docx` in `input/<NomeProgetto>/`), testo in chat/prompt, o entrambi (si combinano: leggi il documento e integra con quanto detto in chat, senza contraddizioni — se la chat corregge o aggiunge rispetto al documento, vince la chat perché più recente)
- **Schema/dati**: file tabellari locali (`.xlsx`/`.csv`, schema esplicito o estrazione dati) in `input/<NomeProgetto>/`, tabelle su un Lakehouse Fabric, o entrambi insieme (alcune tabelle da un lato, altre dall'altro — è un caso legittimo, non un'ambiguità da risolvere scegliendo una sola fonte)

Un'eventuale bozza di soluzione/modello preesistente trovata in `input/<NomeProgetto>/` è anch'essa fonte utile (vedi [OBBLIGATORIO](#obbligatorio)): quando il round la legge, trattala per requisiti/contesto come qualunque altro file, ma un mapping Tabella.Colonna che propone va comunque riportato come "Da confermare in fase 2", non come dichiarazione dell'utente.

**Determina la combinazione attiva e procedi di conseguenza:**
- **Documento requisiti presente (in `input/` o in chat)** → spezzalo in requisiti atomici e applica [Mapping Requisiti → Schema Target](#mapping-requisiti--schema-target); le uniche domande ammesse sono quelle sui gap reali (vedi [Refuso trasversale](references/requirements-mapping.md#refuso-trasversale) nel reference). La presenza di file/tabelle di schema (locali o Fabric) non cambia questo criterio: non vanno ispezionati qui per dedurre risposte, solo registrati come fonte-schema per la fase 2 (vedi Round 2).
- **Nessun documento requisiti** → fai domande mirate sui requisiti mancanti (Round 1/3/4 standard); l'eventuale presenza di file/tabelle di schema non sostituisce la domanda, perché il match tabella/colonna resta comunque compito di `data-analyst` in fase 2.

Come si registra la modalità di connessione per ciascuna fonte-schema attiva è materia del Round 2 — qui basta rilevare quali fonti sono attive.

Chiedi solo se non già noto dalla Domanda di Apertura o dal prompt:

> Come vuoi chiamare questo report? Determinerà il nome delle cartelle del progetto (`report/<NomeProgetto>.Report/` e `.SemanticModel/`).

Raccogli nel campo `Modalità di raccolta:` di `## Setup` (unico campo del template per questo, non aggiungerne altri):

```markdown
Nome report:
Modalità di raccolta: proposta da zero | requisiti già forniti (fonte: documento in input/... | testo in chat | documento + chat)
```

**Criterio di uscita**: il nome del report è fissato, la modalità di raccolta è decisa; ogni fonte di requisiti già fornita è stata acquisita (file, chat, o entrambi); per ogni fonte Fabric attiva è noto almeno il nome del workspace/Lakehouse (se l'utente lo conosce già).

### Round 1 — Audience e Scopo

**Condizione**: vedi il principio comune sopra — qui l'informazione specifica è audience e scopo.

Obiettivo: capire per chi è il report (es. leadership vs analisti vs audience esterna — profili con esigenze molto diverse in termini di concisione, drill-down e storytelling) e quale decisione/compito supporta (es. monitorare performance, individuare anomalie, confrontare segmenti).

Se sia l'audience sia il compito da svolgere sono già chiari dal prompt, riassumi la risposta dedotta invece di chiedere; altrimenti chiedili con una domanda concreta e chiusa per volta (vedi [PREFERIRE](#preferire)), una per audience e una per compito/scopo.

Scrivi il risultato in `## Audience e Scopo` del template (Audience, Scopo primario, Tono, Criteri di successo).

**Criterio di uscita**: audience, scopo primario e tono sono fissati o dedotti e confermati dall'utente.

### Round 2 — Dati Disponibili e Granularità

**Condizione**: esegui sempre questo round, indipendentemente dalla modalità scelta nel Round 0 — serve sempre sapere a quale DB agganciarsi e come i dati arriveranno, anche quando l'utente ha già una lista di requisiti pronta. Se in `input/<NomeProgetto>/` sono già presenti file tabellari (`.xlsx`/`.csv`), elenca direttamente i loro nomi in `Tabelle/file attesi in input/<NomeProgetto>/` (solo il nome del file/foglio, senza aprirlo per leggerne le colonne). In quel caso questo round si riduce alla sola domanda sulla modalità/tipo di connessione al db reale (vedi sotto): finché non hai la risposta, tienila come voce in "Domande Aperte"; appena l'utente risponde, **spostala** in questa sezione (`Tipo di DB` / `Modalità di connessione`) di `output/<NomeProgetto>/requirements.md` — "Domande Aperte" è solo per i gap ancora irrisolti al momento della scrittura del file, non un contenitore permanente per l'informazione una volta raccolta.

Obiettivo: stabilire a quale database si deve agganciare il report, con quale modalità di connessione, e quali tabelle servono. Questa sezione è obbligatoria e non può rimanere vuota o generica: il brief deve specificare fonte dati, schema atteso, granularità e gap noti — il modello semantico non esiste ancora in questa fase, viene creato nella fase 4.

Tratta ciascuna fonte-schema attiva (vedi Round 0) indipendentemente, senza forzare una scelta esclusiva tra locale e Fabric.

**Componente Fabric** (se almeno una fonte-schema è un Lakehouse Fabric): registra `Tipo di DB` e `Modalità di connessione` includendo `Fabric Lakehouse` tra le fonti attive, e il nome del workspace/Lakehouse se l'utente lo conosce già, in `Tabelle/file attesi in input/<NomeProgetto>/ (oppure workspace/Lakehouse Fabric)`. Non chiedere un'estrazione Excel/CSV né i nomi delle tabelle per questa componente: lo schema reale lo esplora `data-analyst` in fase 2 via `fabric-lakehouse-consumption`. Se il nome del workspace/Lakehouse non è ancora noto, chiedilo una volta sola:

> Conosci già il nome del workspace e del Lakehouse Fabric da cui leggere i dati? Se non ancora, va bene: lo risolveremo nella fase di analisi dati.

Se **tutte** le fonti-schema attive sono Fabric (nessuna componente locale), salta il resto di questo round (le domande sottostanti si applicano alla componente locale) e vai al Criterio di uscita. Se invece è attiva anche una componente locale, continua con quanto segue per quella componente, e mantieni entrambe nell'output finale (`Modalità di connessione: Import + Fabric Lakehouse`, non una sola delle due).

**Componente locale — prima di chiedere, verifica se l'informazione è già deducibile** da ciò che hai in mano, per non riproporre come domanda aperta ciò che è già ricavabile — ma nessuna deduzione va scritta nel file senza conferma esplicita dell'utente (vedi [PREFERIRE](#preferire)):

- Se in `input/<NomeProgetto>/` sono presenti solo file Excel/CSV (nessun riferimento a una connessione live a un database reale) e il documento requisiti/BRD, se presente, descrive i dati come un'estrazione/esportazione periodica da un sistema esterno → presenta la deduzione (`Modalità di connessione: Import`, `Tipo di DB` valorizzato con la fonte descritta, es. "estrazione periodica da tool di ticketing esterno", "file Excel/CSV" se non è nominato uno strumento specifico) e chiedi conferma in una riga, invece di riproporre la domanda aperta o di scriverla senza conferma.
- Se **né** i file in `input/<NomeProgetto>/` **né** il documento requisiti chiariscono come/da dove arriveranno i dati in produzione (es. nessuna menzione di estrazione, tool sorgente, o tipo di sistema), non c'è nulla da dedurre: poni la domanda esplicita sotto, non va saltata.

Se l'informazione non è deducibile, chiedi:

> A quale tipo di database si deve agganciare il report (es. SQL Server, PostgreSQL, Oracle, ecc.) e con quale modalità di connessione (Import o DirectQuery)?

Chiarisci sempre esplicitamente come arriveranno i dati concreti, perché questo agente non si connette mai direttamente alla fonte dati in fase 1:

> Per costruire il modello nella fase 4 mi serve un'estrazione delle tabelle necessarie in formato Excel o CSV, da mettere nella cartella `input/<NomeProgetto>/` del progetto. Quali tabelle (o nomi di file) prevedi di fornire?

Non chiedere di descrivere la struttura delle tabelle in dettaglio (colonne, tipi, chiavi) — quel dettaglio si ricava direttamente dai file una volta disponibili in `input/<NomeProgetto>/`, in fase 4.

Scrivi il risultato in `## Dati Disponibili e Granularità` del template (Tipo di DB, Modalità di connessione, Tabelle/file attesi, Gap noti); usa più righe in `Modalità di connessione`/`Tabelle/file attesi` solo se sono davvero attive più fonti.

Chiedi solo per gap o ambiguità genuine, ad es.:

> Hai citato vendite giornaliere per prodotto e area, ma nessuna segmentazione cliente. Ti serve la segmentazione per questo report, o la granularità prodotto/area è sufficiente?

**Criterio di uscita**: tipo di DB, modalità di connessione e l'elenco delle tabelle/file attesi in `input/<NomeProgetto>/` sono definiti; i gap noti sono annotati.

### Round 3 — KPI e Metriche Chiave

**Condizione**: vedi il principio comune sopra — qui l'informazione specifica sono i KPI. Se i KPI sono già specificati in un file in `input/<NomeProgetto>/` o nel testo di requisiti incollato in chat, leggili da lì ed estraili invece di fare la domanda, poi riassumili per conferma — se un documento requisiti è stato spezzato in requisiti atomici (vedi [Mapping Requisiti → Schema Target](#mapping-requisiti--schema-target)), ogni requisito atomico che esprime una metrica/misura è un candidato KPI: popola la tabella da quella lista, senza chiedere all'utente "quali sono i KPI". Chiedi solo se, per uno specifico requisito atomico, non è chiaro se rappresenti effettivamente un KPI da mettere in primo piano o un filtro/dettaglio secondario — mai una domanda generica di raccolta KPI.

Obiettivo: identificare 3-6 KPI e metriche che il report deve mostrare in primo piano, e segnalare quelli che non esistono ancora nel modello.

Chiedi con una domanda diretta se non già deducibile dal contesto. Per ogni KPI raccolto, annota se corrisponde a una misura esistente o va costruito nella fase 4, scrivendo il risultato in `## KPI e Metriche Chiave` del template: **una riga per KPI**, mai un elenco schiacciato su una riga sola, nel formato esatto `- <Nome KPI> — misura esistente: <nome misura>` oppure `- <Nome KPI> — serve nuova misura: <base di calcolo>` (es. `- Fatturato Totale — serve nuova misura: Quantità × Prezzo Unitario`).

Non assumere un valore di dominio non dichiarato nei requisiti (es. quale stringa di `STATO_ORDINE` indica un reso): scrivi la base di calcolo restando ai concetti nominati e segnala il valore mancante come "Da confermare in fase 2 con data-analyst".

**Criterio di uscita**: sono elencati 3-6 KPI, ciascuno marcato come misura esistente o da costruire in fase 4.

### Round 4 — Numero Pagine, Visual Desiderati e Layout (bozza) + Direzione di Design

**Condizione**: vedi il principio comune sopra — qui l'informazione specifica sono numero di pagine, visual desiderati e layout di massima. La domanda sulla direzione di design generale (tono) resta comunque utile da porre anche quando pagine/visual sono già noti, se non è già chiara.

Obiettivo: tracciare per ciascuna pagina lo scopo, l'elenco dei visual desiderati (uno per riga, non un unico riepilogo generico) e i filtri/slicer previsti, più una direzione di design generale in prosa (tono, uso del colore a livello concettuale, disposizione generale). Questo non è ancora un layout meccanico pixel-per-pixel né un archetipo grafico (competenza di `powerbi-report-design` in fase 5) — ma deve comunque essere specifico: visual singoli per nome/tipo (es. "line chart trend per periodo"), filtri concreti per pagina, non descrizioni sommarie.

Chiedi solo dopo aver applicato ciò che è già noto dai round precedenti: numero di pagine attese, per ciascuna scopo/visual/filtri, e la direzione di design generale (tono, eventuali preferenze di disposizione/colore).

Scrivi il risultato in `## Numero Pagine, Visual Desiderati e Layout` e `## Direzione di Design (bozza)` del template.

Restano fuori scope solo il blocco YAML `Design Brief:`, coordinate/griglie precise o un `layout_contract` vero e proprio — quelli sono compito di `report-builder`/`powerbi-report-design` in fase 5. Indicazioni di stile in prosa (anche se concrete) sono invece incoraggiate qui, se l'utente le fornisce o se sono deducibili dal contesto.

Popola anche `## Filtri/Slicer` nel template: è un riepilogo aggregato dei filtri già raccolti per pagina qui sopra (un bullet per dimensione filtrabile, con ambito globale o per pagina) — non richiede domande proprie, non lasciarlo vuoto se filtri/pagina sono stati raccolti.

**Criterio di uscita**: per ogni pagina esistono scopo, elenco di visual specifici (non un'unica descrizione generica) e filtri proposti; esiste inoltre una direzione di design in prosa (tono + note concrete su stile/colori/impaginazione generale) e il riepilogo in `## Filtri/Slicer`. Non è richiesto un layout meccanico con coordinate/griglia pixel-per-pixel: quello resta compito di `report-builder` in fase 5.

## Mapping Requisiti → Schema Target

Si applica quando è disponibile un documento/testo di requisiti (`input/<NomeProgetto>/` o chat) da cui estrarre requisiti atomici. In questo caso, oltre alla normale raccolta requisiti, spezza il documento in requisiti atomici e popola la sezione `## Mapping Requisiti → Schema Target` del template: un match `Tabella.Colonna` solo se dichiarato esplicitamente nei requisiti, altrimenti `Da confermare in fase 2` — **mai ispezionare file locali o Fabric per dedurre il match**, è compito esclusivo di `data-analyst`. È "Non applicabile" solo quando non c'è alcun documento/testo di requisiti da cui estrarre requisiti atomici.

Procedura completa (requisiti atomici, gestione dei match non dichiarati, casi in cui fermarsi e chiedere): vedi [references/requirements-mapping.md](references/requirements-mapping.md).

Questa attività si aggiunge ai Round 0-4 quando è disponibile un documento requisiti; il dettaglio colonne reale (locale o Fabric) resta sempre compito della fase 2 (`data-analyst`), come già previsto dal Round 2.

## Vincoli, Rischi, Note (trasversale)

In qualsiasi round può emergere un vincolo, un rischio o una nota che non rientra nelle sezioni tipizzate (es. una scadenza, un limite di licenza, una dipendenza da un dato non ancora disponibile, una preferenza organizzativa). Annota tutto questo nella sezione **Vincoli, Rischi, Note** di `output/<NomeProgetto>/requirements.md`: è la sezione di raccolta per ciò che è rilevante ma non appartiene a un round specifico. Non serve un round dedicato — popolala man mano che le informazioni affiorano.

## Output

Produci esattamente un file: `output/<NomeProgetto>/requirements.md`. Il file va creato dal template **subito**, al Round 0 (l'orchestrator lo copia dal template prima della delega — vedi `requirements-analyst.agent.md`), e **compilato progressivamente**, sezione per sezione, appena ciascun round viene confermato dall'utente — non tenere le risposte solo in conversazione fino alla fine: il file sul disco è lo stato di avanzamento reale della raccolta, aggiornato passo dopo passo, non solo il riepilogo finale.

Le regole meccaniche di scrittura (come si scrive ogni sezione, quando riscriverne una già compilata, come reagire a un file non conforme al template) sono responsabilità dell'agente — vedi "Come scrivo il file" in `requirements-analyst.agent.md`. Qui in skill conta solo *quando* una sezione si applica o resta "Non applicabile" (vedi [OBBLIGATORIO](#obbligatorio)) — non c'è mai un'intestazione senza il suo contenuto.

Se il file finale non ha le stesse intestazioni del template, la fase 1 non è completa: non è una linea guida stilistica.

### Cosa NON scrivere mai in `output/<NomeProgetto>/requirements.md`

Questo output descrive **cosa serve**, non **come costruirlo**: la modellazione è compito esclusivo della fase 4 (`semantic-modeler`). Di conseguenza:

- **Non inventare né scrivere formule DAX** (misure complete con `SUM`, `CALCULATE`, `SUMX`, ecc.): per ogni KPI/metrica limitati a segnalare in linguaggio naturale se serve una nuova misura e su quale dato si baserebbe — la formula la scrive `semantic-modeler` in fase 4.
- **Non inventare nomi di tabelle o schema a stella** (es. `FactSales`, `DimDate`, `DimProduct`): un nome di tabella/colonna compare nell'output solo se dichiarato esplicitamente nei requisiti — mai un nome dedotto o inventato ispezionando i file, quello è compito di `data-analyst` in fase 2. Decidere fact/dimension, naming e relazioni del modello resta competenza della fase 4.
- **Non scrivere una sezione "Relazioni e modello"** o equivalente: le relazioni tra tabelle le stabilisce `semantic-modeler`, non `requirements-analyst`.
- **Non "concordare" tu KPI o mapping**: per ogni requisito atomico riporta il match solo se dichiarato esplicitamente, altrimenti marca "Da confermare in fase 2" (vedi Mapping Requisiti → Schema Target) — non decidere né verificare l'allineamento al posto di `data-analyst`.
- **Non inventare valori di dominio di una colonna** (es. quale valore rappresenta "reso", "attivo", ecc.): resta ai concetti dichiarati nei requisiti, segnala il resto come "Da confermare in fase 2 con data-analyst" — ispezionare i valori reali è compito esclusivo di `data-analyst`.

**Gate di approvazione**: criteri di completezza prima di dichiarare il file pronto — tutte le sezioni compilate, intestazioni identiche al template, nessun placeholder vuoto, nessuna sezione duplicata o orfana (vedi [OBBLIGATORIO](#obbligatorio)). La procedura di validazione (chi esegue `validate_requirements.py`, quando richiedere l'approvazione all'utente) è definita in `requirements-analyst.agent.md`, sezione "Fine Intervista" — non va ripetuta qui. Non passare alla fase 2 (`data-analyst`) finché l'utente non approva esplicitamente; se richiede modifiche, rivedi il file e ripeti il gate.