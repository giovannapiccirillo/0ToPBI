# Pattern di Query per Compiti Ricorrenti

Pattern concisi per `execute_query`, per i compiti che `data-analyst` ripete
più spesso dopo la discovery iniziale (vedi
[consumption.md](consumption.md) per la sequenza di schema discovery — non
ripetuta qui). Per la superficie T-SQL completa vedi
[consumption-core.md](consumption-core.md); per limiti e regole vedi
[SKILL.md](../SKILL.md).

## Query Singola

```text
execute_query(workspaceId, itemId, "SET NOCOUNT ON; SELECT TOP 20 * FROM dbo.FactSales")
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

## Pattern per Probe di Modellazione

Pattern per il contenuto obbligatorio di `data-analysis.md` (chiave
candidata, relazioni, cardinalità/valori, range — vedi
[data-analysis/SKILL.md](../../data-analysis/SKILL.md)). **Usa questi
pattern solo se i constraint dichiarati (query "Constraint"/"Relazioni
foreign key" in [discovery-queries.md](discovery-queries.md)) non bastano o
non esistono** — il caso comune su un Lakehouse, le cui tabelle
auto-generate da Delta tipicamente non hanno PK/FK dichiarate.

### Cardinalità (chiave candidata)

Confronta con il conteggio righe della tabella (step 5 di
[consumption.md](consumption.md)): cardinalità ≈ righe indica una chiave.

```text
execute_query(workspaceId, itemId, "SELECT COUNT(DISTINCT ProductID) AS distinct_count FROM dbo.FactSales")
```

### Valori Distinti o Top-N per Frequenza

Per colonne a bassa cardinalità, elenca i valori effettivi. Per colonne ad
alta cardinalità, limita a una Top-N per frequenza invece di elencare tutto:

```text
# Bassa cardinalità: valori distinti
execute_query(workspaceId, itemId, "SELECT DISTINCT Region FROM dbo.DimCustomer ORDER BY Region")

# Alta cardinalità: Top-N per frequenza
execute_query(workspaceId, itemId, "SELECT TOP 20 CustomerName, COUNT(*) AS freq FROM dbo.FactSales GROUP BY CustomerName ORDER BY freq DESC")
```

### Range Temporale/Numerico

```text
execute_query(workspaceId, itemId, "SELECT MIN(SaleDate) AS min_date, MAX(SaleDate) AS max_date, MIN(Amount) AS min_amount, MAX(Amount) AS max_amount FROM dbo.FactSales")
```

### Relazione Candidata (Inclusione Insiemistica)

Conferma una relazione dedotta per naming — non basarsi solo sulla
somiglianza dei nomi di colonna: verifica che i valori della colonna
"child" esistano tutti nella colonna candidata "parent" (nessuna riga in
risposta = inclusione confermata).

```text
execute_query(workspaceId, itemId, "
SELECT DISTINCT f.ProductID
FROM dbo.FactSales AS f
LEFT JOIN dbo.DimProduct AS p ON f.ProductID = p.ProductID
WHERE p.ProductID IS NULL
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
