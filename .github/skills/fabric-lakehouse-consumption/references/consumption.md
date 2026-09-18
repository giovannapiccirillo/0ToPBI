<!-- Adattato da microsoft/skills-for-fabric skills/sqldw-cli/references/consumption.md (solo modalità consumption). -->

> **Regole critiche**
> 1. Read-only: solo `SELECT` e query di catalogo — mai `CREATE`, `ALTER`,
>    `DROP`, `INSERT`, `UPDATE`, `DELETE`, `MERGE`, `TRUNCATE`, `COPY INTO`.
> 2. Il deliverable è la risposta con i dati reali, non un riassunto della
>    query: esegui sempre la query contro l'endpoint live.

# Esplorazione di un Lakehouse Fabric via SQL Analytics Endpoint

## Connessione

### Risolvere workspaceId e itemId

Vedi [finding-workspaces-items.md](finding-workspaces-items.md) per come
risolvere questi due GUID da nome via `az rest`. Per un **Lakehouse**, usa
l'id del suo **SQL analytics endpoint**
(`properties.sqlEndpointProperties.id`) — **non** l'id del Lakehouse.

### Eseguire una query

```text
execute_query(
  workspaceId: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
  itemId: "11111111-2222-3333-4444-555555555555",
  query: "SELECT TOP 10 * FROM dbo.FactSales"
)
```

Nessuna configurazione di connessione aggiuntiva: l'autenticazione è gestita
dal protocollo MCP (basata sulla sessione `az login` già attiva).

## Sequenza di Schema Discovery

Esegui in ordine per capire cosa c'è nell'endpoint. Vedi
[discovery-queries.md](discovery-queries.md) per query estese.

```text
# 1. Elenca gli schema
execute_query(workspaceId, itemId, "SELECT schema_name FROM INFORMATION_SCHEMA.SCHEMATA ORDER BY schema_name")

# 2. Elenca tabelle e viste
execute_query(workspaceId, itemId, "SELECT table_schema, table_name, table_type FROM INFORMATION_SCHEMA.TABLES ORDER BY table_schema, table_name")

# 3. Colonne di una tabella
execute_query(workspaceId, itemId, "SELECT column_name, data_type, character_maximum_length, is_nullable FROM INFORMATION_SCHEMA.COLUMNS WHERE table_schema='dbo' AND table_name='FactSales' ORDER BY ordinal_position")

# 4. Anteprima righe
execute_query(workspaceId, itemId, "SELECT TOP 5 * FROM dbo.FactSales")

# 5. Conteggio righe (da sys.partitions, non COUNT(*): non richiede scan)
execute_query(workspaceId, itemId, "SELECT s.name AS [schema], t.name AS [table], SUM(p.rows) AS row_count FROM sys.tables t JOIN sys.schemas s ON t.schema_id=s.schema_id JOIN sys.partitions p ON t.object_id=p.object_id AND p.index_id IN (0,1) GROUP BY s.name, t.name ORDER BY row_count DESC")

# 6. Oggetti di programmabilità (viste, funzioni, procedure)
execute_query(workspaceId, itemId, "SELECT name, type_desc FROM sys.objects WHERE type IN ('V','FN','IF','P','TF') ORDER BY type_desc, name")
```

## Workflow

1. **Scopri** → esegui gli step 1-3 per capire tabelle/colonne disponibili.
2. **Campiona** → `SELECT TOP 5` sulle tabelle rilevanti.
3. **Formula** → scrivi T-SQL usando
   [consumption-core.md](consumption-core.md) (superficie T-SQL supportata,
   tipi dato, gotcha).
4. **Esegui** → chiama `execute_query(workspaceId, itemId, query)`.
5. **Itera** → affina in base ai risultati.
6. **Presenta** → riporta i risultati nell'artefatto di analisi
   (`output/<NomeProgetto>/data-analysis.md`).

## Limiti osservati (non un contratto documentato)

| Limite | Valore | Note |
|---|---|---|
| Righe massime | ~10.000 | Risultati troncati oltre. Usa `TOP`, filtri o aggregazioni. |
| Timeout query | 300s | Query lunghe falliscono per timeout. |
| Rate limit | 20 richieste/min per identità | HTTP 429 se superato. Ritenta con backoff. |

Verifica il comportamento reale da risposte live (troncamento, 429, timeout)
piuttosto che affidarti a questi numeri come garanzia.

## Regole

### OBBLIGATORIO

- Verificare che il tool MCP `execute_query` sia disponibile prima della
  prima operazione — se assente, chiedere all'utente di registrare l'MCP
  `fabric-sqlendpoint` (vedi `.mcp.json` del progetto).
- Usare sempre `TOP`/`WHERE` — il tool tronca a ~10.000 righe: se ne
  restituisce esattamente 10.000, i risultati sono probabilmente troncati.
- Usare `COUNT(*)` (o meglio `sys.partitions`) prima di un `SELECT` senza
  filtri su una tabella grande.
- `SET NOCOUNT ON;` a inizio di query multi-statement.
- Inviare un solo batch T-SQL per chiamata: niente `GO`, niente comandi
  sqlcmd. Per operazioni multi-batch, usa chiamate `execute_query` separate.

### EVITARE

- `SELECT *` non filtrato: rischia il cap di 10.000 righe.
- Query ravvicinate oltre il rate limit (20/min): spazia le chiamate o
  consolida con JOIN/UNION ALL.
- MARS (Multiple Active Result Sets): non supportato, ogni query è
  indipendente.
- GUID hardcoded: risolvi sempre workspace/item da nome.

### PREFERIRE

- `TOP N` sulle query esplorative.
- Consolidare query correlate in un'unica `SELECT` con JOIN.
- Query aggregate (`COUNT`, `SUM`, `AVG`, `GROUP BY`) rispetto a scan
  completi.
- `ORDER BY` con `TOP` per risultati deterministici.

## Troubleshooting

| Sintomo | Causa | Soluzione |
|---|---|---|
| Tool MCP non disponibile | MCP `fabric-sqlendpoint` non registrato | Verificare `.mcp.json`; l'utente deve aver eseguito `az login` |
| HTTP 401 | Token scaduto o non valido | Ri-autenticare (`az login` di nuovo) |
| HTTP 403 | Permessi insufficienti sul workspace/item | Verificare ruolo Viewer+ sul workspace/item |
| HTTP 404 | workspaceId/itemId errato | Verificare i GUID via `finding-workspaces-items.md` |
| HTTP 429 | Rate limit superato (20/min) | Attendere e ritentare con backoff; consolidare query |
| Timeout query (300s) | Query troppo complessa o dati troppo estesi | Semplificare, aggiungere filtri, usare `TOP` |
| Esattamente 10.000 righe | Troncamento risultati | Aggiungere `TOP N`/`WHERE`; usare `COUNT(*)` per il totale |
| Errore SQL nella risposta | Sintassi T-SQL errata o oggetto inesistente | Correggere; verificare nomi tabella/colonna via schema discovery |
