---
name: fabric-lakehouse-consumption
description: >-
  Probe read-only di un Lakehouse Fabric (o Warehouse/Mirrored DB) via il
  suo SQL analytics endpoint per la costruzione di un modello semantico
  Power BI e dei relativi KPI: schema, conteggio righe, chiave candidata,
  relazioni tra tabelle, cardinalità/valori distinti, range
  temporale/numerico, qualità dei dati. Usata dall'agente data-analyst
  (fase 2) come alternativa a input/<NomeProgetto>/ quando i requisiti
  indicano una sorgente Fabric Lakehouse. Solo esplorazione — non estrazione
  di dataset per uso applicativo: nessuna scrittura, solo query T-SQL SELECT
  e catalogo. Triggers: "dati su Fabric", "Lakehouse", "schema tabelle
  Fabric", "quante righe ha la tabella", "esplora il Lakehouse".
---

# fabric-lakehouse-consumption — Esplorazione Read-Only di un Lakehouse Fabric

Questa skill copre **solo la modalità consumption** (query read-only) contro
il SQL analytics endpoint di un Lakehouse Fabric (funziona identicamente su
Warehouse e Mirrored Database). È un sottoinsieme, ridotto e adattato per
questo progetto, della skill ufficiale `sqldw-cli` di
[microsoft/skills-for-fabric](https://github.com/microsoft/skills-for-fabric)
— qui non sono incluse le modalità `authoring` (DDL/DML) e `operations`
(diagnostica performance): questo progetto non le usa, perché `data-analyst`
si limita a leggere schema, righe e qualità dei dati, mai a modificare nulla
su Fabric.

**Confine di scope** — solo `SELECT` e query di catalogo (`INFORMATION_SCHEMA`,
`sys.*`). Nessun `CREATE`/`ALTER`/`DROP`/`INSERT`/`UPDATE`/`DELETE`/`MERGE`.
Se serve scrivere su Fabric, è fuori scope di questo progetto: fermati e
segnalalo all'utente invece di improvvisare con altri strumenti.

**Finalità del probe** — l'obiettivo finale è la reportistica Power BI:
ogni query serve a raccogliere ciò che `semantic-modeler` (fase 4) userà per
decidere tabelle/relazioni/misure e costruire i KPI dei requisiti (schema,
chiave candidata, relazioni tra tabelle, cardinalità/valori, range,
qualità dati) — non a estrarre un dataset per un uso applicativo a valle.
Query con filtri di business su un intervallo specifico o l'estrazione
riga per riga di un dataset intero sono fuori scope qui.

## Tool Stack

| Tool | Ruolo |
|---|---|
| MCP `fabric-sqlendpoint` (`execute_query`) | **Primario**: esegue T-SQL contro l'endpoint SQL Fabric. Configurato in `.mcp.json` di questo repo. Autenticazione trasparente via `az login` (nessun token/secret da gestire a mano). |
| `az rest` | Solo per risolvere `workspaceId`/`itemId` da nome (discovery control-plane), non per eseguire query dati |
| `scripts/common/ensure_fabric_login.py` | Verifica/stabilisce la sessione `az login` (vedi sezione "Autenticazione" sotto) prima di usare gli altri due |

> **Se il tool MCP `execute_query` non è disponibile** nella tua sessione:
> fermati e segnala all'utente di verificare che l'MCP `fabric-sqlendpoint`
> sia configurato in `.mcp.json`. Se invece il problema è di autenticazione
> (query che falliscono con errore 401/403), esegui prima
> `scripts/common/ensure_fabric_login.py` invece di segnalare subito: potrebbe
> bastare un nuovo login. Non ripiegare comunque su `sqlcmd` o altri
> strumenti ad hoc.

### Firma del tool

```text
execute_query(workspaceId, itemId, query)
```

- `workspaceId`: GUID del workspace Fabric.
- `itemId`: GUID dell'item. **Per un Lakehouse, usa l'id del suo SQL analytics
  endpoint** (`properties.sqlEndpointProperties.id`), **non** l'id del
  Lakehouse stesso — sono due GUID diversi.
- `query`: singolo batch T-SQL (niente separatori `GO`, niente comandi
  `sqlcmd`).

**Limiti osservati** (default non garantiti, verifica sul comportamento
live):

| Limite | Valore | Note |
|---|---|---|
| Righe massime | ~10.000 | Risultati troncati oltre. Usa `TOP`, filtri o aggregazioni — vedi [references/query-patterns.md](references/query-patterns.md) per la paginazione. |
| Timeout query | 300s | Query lunghe falliscono per timeout. |
| Rate limit | 20 richieste/min per identità | HTTP 429 se superato. Consolida o spazia le chiamate. |

Questa è l'unica tabella dei limiti in questa skill: le references sotto la
citano per link, non la ripetono.

## Autenticazione — Verifica Sessione az

Prima di qualunque chiamata `az rest` o `execute_query`, esegui via `execute`:

```text
python scripts/common/ensure_fabric_login.py
```

Controlla se esiste già una sessione `az login` valida (`az account show`).
Se manca o è scaduta, **lancia automaticamente `az login`**, che apre il
browser per l'autenticazione Microsoft interattiva (popup di login) — non
serve chiedere all'utente di lanciarlo a mano da terminale. Procedi con la
risoluzione workspace/item solo con exit code 0. Se lo script esce con
codice diverso da 0 (login fallito o annullato), fermati e segnalalo
all'utente invece di ripetere il login in loop.

## Risoluzione workspace/item

Prima di poter chiamare `execute_query` servono `workspaceId` e l'`itemId`
del SQL analytics endpoint. Segui
[references/finding-workspaces-items.md](references/finding-workspaces-items.md)
per risolverli da nome via `az rest` — non indovinare mai un GUID, e non
chiedere all'utente di fornirteli se puoi risolverli dal nome workspace/
Lakehouse che ha già indicato.

## Workflow di Esplorazione

Segui [references/consumption.md](references/consumption.md) per la
sequenza completa e autorevole (connessione → schema discovery → sample →
conteggi → constraint → probe di modellazione). Quel file è l'unico punto
in cui questa sequenza è scritta per esteso — non ripeterla altrove.

Per approfondire, in ordine di quando servono:

- Query estese di schema (constraint PK/FK/UNIQUE, viste, statistiche) —
  **controllare sempre prima di dedurre relazioni dai valori**:
  [references/discovery-queries.md](references/discovery-queries.md).
- Superficie T-SQL supportata, tipi dato mappati da Delta e gotcha:
  [references/consumption-core.md](references/consumption-core.md).
- Pattern pronti per il probe di modellazione (cardinalità, valori
  distinti/Top-N, range, relazioni candidate per inclusione insiemistica) e
  per compiti ricorrenti (multi-statement batch):
  [references/query-patterns.md](references/query-patterns.md).
- Risoluzione `workspaceId`/`itemId` da nome:
  [references/finding-workspaces-items.md](references/finding-workspaces-items.md).

## Obbligatorio/Preferire/Evitare

### OBBLIGATORIO

- Solo query read-only: `SELECT` e catalogo. Mai DDL/DML.
- Usare `TOP N` o filtri `WHERE` su ogni query esplorativa — mai `SELECT *`
  senza limite su una tabella di cui non conosci ancora la cardinalità.
- Verificare la cardinalità (`sys.partitions`, non `COUNT(*)` a tabella
  intera) prima di un sample o di un'aggregazione su tabelle grandi.
- Risolvere `workspaceId`/`itemId` da nome, mai inventare o assumere GUID.
- Se il tool MCP non è disponibile o la query fallisce con errore di
  autenticazione, fermarsi e segnalarlo — non tentare fallback con altri
  strumenti (`sqlcmd`, connessioni dirette) non previsti da questo progetto.

### PREFERIRE

- Query aggregate (`COUNT`, `GROUP BY`) rispetto a scan completi.
- Consolidare query correlate in un'unica chiamata (JOIN/UNION ALL) per
  restare sotto il rate limit.
- `INFORMATION_SCHEMA`/`sys.*` per lo schema, prima di campionare righe.

### EVITARE

- Non modificare mai lo schema o i dati su Fabric da questa skill.
- Non usare `SELECT *` non filtrato su tabelle di cardinalità sconosciuta.
- Non eseguire query multiple ravvicinate oltre il rate limit osservato
  (20/min): consolidare o spaziare le chiamate.

## Riferimento

Questa skill è un estratto mirato — non un mirror completo — di
`skills/sqldw-cli` (modalità `consumption`) in
[microsoft/skills-for-fabric](https://github.com/microsoft/skills-for-fabric).
Se in futuro serve anche `authoring`/`operations` su Fabric per questo
progetto, importa quelle modalità come skill/estensione separata invece di
espandere questa, che deve restare dichiaratamente read-only.
