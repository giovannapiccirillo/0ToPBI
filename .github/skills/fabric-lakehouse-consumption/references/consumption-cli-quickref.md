<!-- Adattato da microsoft/skills-for-fabric skills/sqldw-cli/references/consumption/consumption-cli-quickref.md (solo pattern query pertinenti a data-analyst). -->

# Quick Reference — Pattern di Query

Pattern concisi per `execute_query`. Per la superficie T-SQL completa vedi
[consumption-core.md](consumption-core.md).

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

## Gestione Risultati Grandi

Il tool tronca a ~10.000 righe (default osservato, non garantito):

```text
-- Step 1: verifica il conteggio totale
execute_query(workspaceId, itemId, "SELECT COUNT(*) AS total FROM dbo.FactSales WHERE SaleDate >= '2025-01-01'")

-- Step 2: pagina se serve (OFFSET/FETCH). Elenca solo le colonne
-- necessarie -- riduce il rischio di toccare il cap di ~10.000 righe/payload.
execute_query(workspaceId, itemId, "
SELECT SaleID, SaleDate, ProductKey, CustomerKey, Quantity, Amount FROM dbo.FactSales
WHERE SaleDate >= '2025-01-01'
ORDER BY SaleID
OFFSET 0 ROWS FETCH NEXT 10000 ROWS ONLY
")
```

## Note per Agenti

- Usa direttamente il tool MCP `execute_query`. Nessun comando shell
  necessario per l'esecuzione SQL.
- **GitHub Copilot**: il tool MCP compare in automatico nella tool list
  quando il server `fabric-sqlendpoint` è registrato in `.mcp.json`.
- Spazia le chiamate durante investigazioni multi-step (max 20 req/min per
  identità).
- Per la risoluzione di workspace/item ID usa `az rest` — vedi
  [finding-workspaces-items.md](finding-workspaces-items.md).
