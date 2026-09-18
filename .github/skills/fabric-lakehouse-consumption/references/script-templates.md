<!-- Adattato da microsoft/skills-for-fabric skills/sqldw-cli/references/consumption/script-templates.md (solo template consumption pertinenti a data-analyst). -->

# Template di Workflow

Sequenze di chiamate `execute_query` per compiti ricorrenti di
`data-analyst`.

## Export Dati

### Query a CSV

Il tool `execute_query` restituisce i risultati come CSV nativo:

```text
execute_query(workspaceId, itemId, "
SET NOCOUNT ON;
SELECT ProductID, ProductName, Category, Price
FROM dbo.DimProduct
ORDER BY ProductName
")
```

### Export con Intervallo Parametrizzato

```text
# Step 1: verifica il conteggio totale nell'intervallo
execute_query(workspaceId, itemId, "
SELECT COUNT(*) AS total_rows
FROM dbo.FactSales
WHERE SaleDate BETWEEN '2025-01-01' AND '2025-06-30'
")

# Step 2: esporta (pagina se > 10.000 righe)
# Elenca le colonne esplicitamente (evita SELECT *) e ORDER BY una chiave
# univoca così la paginazione resta stabile tra chiamate.
execute_query(workspaceId, itemId, "
SET NOCOUNT ON;
SELECT SaleID, ProductID, SaleDate, Amount
FROM dbo.FactSales
WHERE SaleDate BETWEEN '2025-01-01' AND '2025-06-30'
ORDER BY SaleID
OFFSET 0 ROWS FETCH NEXT 10000 ROWS ONLY
")
```

## Workflow di Schema Discovery

```text
# Step 1: elenca schema
execute_query(workspaceId, itemId, "SELECT schema_name FROM INFORMATION_SCHEMA.SCHEMATA ORDER BY schema_name")

# Step 2: tabelle con conteggio righe
execute_query(workspaceId, itemId, "
SELECT s.name AS [schema], t.name AS [table], SUM(p.rows) AS rows
FROM sys.tables t
JOIN sys.schemas s ON t.schema_id = s.schema_id
JOIN sys.partitions p ON t.object_id = p.object_id AND p.index_id IN (0,1)
GROUP BY s.name, t.name
ORDER BY rows DESC
")

# Step 3: viste
execute_query(workspaceId, itemId, "SELECT SCHEMA_NAME(schema_id) AS [schema], name FROM sys.views ORDER BY [schema], name")
```

## Workspace/Item Discovery (via az rest)

Questi comandi `az rest` servono per trovare workspace/item ID prima di
chiamare `execute_query` — vedi
[finding-workspaces-items.md](finding-workspaces-items.md) per il dettaglio
completo.

```bash
WS_ID=$(az rest --method get \
  --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/workspaces" \
  --query "value[?displayName=='MyWorkspace'].id" --output tsv)
echo "Workspace ID: $WS_ID"
```
