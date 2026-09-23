<!-- Adattato da microsoft/skills-for-fabric skills/sqldw-cli/references/consumption/script-templates.md
     e consumption-cli-quickref.md (fusi: stesso scope, pattern di query per
     data-analyst — vedi SKILL.md per le regole obbligatorie/limiti). -->

# Pattern di Query per Compiti Ricorrenti

Pattern concisi per `execute_query`, per i compiti che `data-analyst` ripete
più spesso dopo la discovery iniziale (vedi
[consumption.md](consumption.md) per la sequenza di schema discovery — non
ripetuta qui). Per la superficie T-SQL completa vedi
[consumption-core.md](consumption-core.md); per limiti e regole vedi
[SKILL.md](../SKILL.md).

## Query Singola

```text
execute_query(workspaceId, itemId, "SET NOCOUNT ON; SELECT * FROM dbo.FactSales WHERE SaleDate >= '2025-01-01'")
```

## Multi-Statement (Batch Singolo)

Più statement combinabili in un solo batch (niente `GO`):

```text
execute_query(workspaceId, itemId, "
SET NOCOUNT ON;
SELECT COUNT(*) AS TotalRows FROM dbo.FactSales;
")
```

> Per più result set, usa chiamate `execute_query` separate: il tool
> restituisce solo l'ultimo result set di un batch multi-statement.

## Intervalli Parametrizzati

```text
execute_query(workspaceId, itemId, "
SET NOCOUNT ON;
SELECT * FROM dbo.FactSales
WHERE SaleDate BETWEEN '2025-01-01' AND '2025-06-30'
ORDER BY SaleDate
")
```

## Export e Paginazione su Risultati Grandi

Il tool `execute_query` restituisce i risultati come CSV nativo, ma tronca a
~10.000 righe (vedi [SKILL.md](../SKILL.md) per il limite osservato):

```text
# Step 1: verifica il conteggio totale nell'intervallo
execute_query(workspaceId, itemId, "
SELECT COUNT(*) AS total_rows
FROM dbo.FactSales
WHERE SaleDate BETWEEN '2025-01-01' AND '2025-06-30'
")

# Step 2: pagina se serve (OFFSET/FETCH). Elenca solo le colonne
# necessarie e ordina per una chiave univoca, così la paginazione resta
# stabile tra chiamate.
execute_query(workspaceId, itemId, "
SET NOCOUNT ON;
SELECT SaleID, ProductID, SaleDate, Amount
FROM dbo.FactSales
WHERE SaleDate BETWEEN '2025-01-01' AND '2025-06-30'
ORDER BY SaleID
OFFSET 0 ROWS FETCH NEXT 10000 ROWS ONLY
")
```

## Note per Agenti

- Usa direttamente il tool MCP `execute_query`. Nessun comando shell
  necessario per l'esecuzione SQL.
- Spazia le chiamate durante investigazioni multi-step (max 20 req/min per
  identità — vedi [SKILL.md](../SKILL.md)).
- Per la risoluzione di workspace/item ID usa `az rest` — vedi
  [finding-workspaces-items.md](finding-workspaces-items.md), non ripetuto
  qui.
