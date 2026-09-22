---
name: fabric-lakehouse-consumption
description: >-
  Esplorazione read-only di un Lakehouse Fabric (o Warehouse/Mirrored DB)
  via il suo SQL analytics endpoint: schema discovery, conteggio righe,
  metadati, qualità dei dati. Usata dall'agente data-analyst (fase 1.5) come
  alternativa a input/<NomeProgetto>/ quando i requisiti indicano una
  sorgente Fabric Lakehouse. Nessuna scrittura: solo query T-SQL SELECT e
  catalogo. Triggers: "dati su Fabric", "Lakehouse", "schema tabelle Fabric",
  "quante righe ha la tabella", "esplora il Lakehouse".
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

## Tool Stack

| Tool | Ruolo |
|---|---|
| MCP `fabric-sqlendpoint` (`execute_query`) | **Primario**: esegue T-SQL contro l'endpoint SQL Fabric. Configurato in `.mcp.json` di questo repo. Autenticazione trasparente via `az login` (nessun token/secret da gestire a mano). |
| `az rest` | Solo per risolvere `workspaceId`/`itemId` da nome (discovery control-plane), non per eseguire query dati |
| `scripts/ensure_fabric_login.py` | Verifica/stabilisce la sessione `az login` (vedi sezione "Autenticazione" sotto) prima di usare gli altri due |

> **Se il tool MCP `execute_query` non è disponibile** nella tua sessione:
> fermati e segnala all'utente di verificare che l'MCP `fabric-sqlendpoint`
> sia configurato in `.mcp.json`. Se invece il problema è di autenticazione
> (query che falliscono con errore 401/403), esegui prima
> `scripts/ensure_fabric_login.py` invece di segnalare subito: potrebbe
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
live): max ~10.000 righe per risposta, timeout 300s, 20 richieste/min per
identità. Usa sempre `TOP`/`WHERE`/`COUNT(*)` prima di un `SELECT` non
filtrato — vedi [references/consumption-core.md](references/consumption-core.md).

## Autenticazione — Verifica Sessione az

Prima di qualunque chiamata `az rest` o `execute_query`, esegui via `execute`:

```text
python scripts/ensure_fabric_login.py
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
sequenza completa (schema discovery → sample righe → conteggi → query
mirate). In sintesi:

1. **Schema discovery**: schemi, tabelle, colonne e tipi (vedi
   [references/discovery-queries.md](references/discovery-queries.md) per
   query estese: constraint, foreign key, viste, statistiche).
2. **Conteggio righe** per tabella (`sys.partitions`, non `COUNT(*)` su
   tabelle grandi — più veloce e non richiede scan).
3. **Sample righe** (`SELECT TOP N`) per capire formati e valori reali.
4. **Query di qualità dati mirate** (valori nulli, duplicati su chiave
   candidata, range/outlier) costruite ad hoc sullo schema appena scoperto —
   vedi [references/consumption-core.md](references/consumption-core.md)
   per la superficie T-SQL supportata e i tipi dato mappati da Delta.

Per template di workflow pronti (export CSV, discovery completa, paginazione
su tabelle grandi) vedi
[references/script-templates.md](references/script-templates.md) e
[references/consumption-cli-quickref.md](references/consumption-cli-quickref.md).

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
