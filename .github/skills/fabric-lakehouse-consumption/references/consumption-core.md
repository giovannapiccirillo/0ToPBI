# SQLDW-CONSUMPTION-CORE.md

> **Scope**: Read-only / consumption-oriented T-SQL patterns for **Lakehouse SQL analytics endpoints**, **Mirrored Database SQL analytics endpoints**, and **Fabric Data Warehouse (DW)**.
> This document is *language-agnostic* — no C#, Python, CLI, or SDK references. It covers T-SQL syntax, DDL for read-side objects, system views, security, performance, monitoring, and troubleshooting.

---

## Item-Type Capability Matrix

| Capability | Lakehouse SQLEP | Mirrored DB SQLEP | Warehouse (DW) |
|---|---|---|---|
| SELECT on auto-generated tables | ✅ | ✅ | ✅ |
| CREATE/ALTER/DROP **base tables** | ❌ (read-only) | ❌ (read-only) | ✅ |
| INSERT / UPDATE / DELETE on base tables | ❌ | ❌ | ✅ |
| CREATE VIEW | ✅ | ✅ | ✅ |
| CREATE FUNCTION (inline TVF, scalar¹) | ✅ | ✅ | ✅ |
| CREATE PROCEDURE | ✅ | ✅ | ✅ |
| CREATE SCHEMA | ✅ | ✅ | ✅ |
| Session-scoped #temp tables | ✅² | ✅² | ✅ |
| Cross-database queries (3-part names) | ✅ | ✅ | ✅ |
| GRANT / DENY / REVOKE (security) | ✅ | ✅ | ✅ |
| Row-Level Security (RLS) | ✅ | ✅ | ✅ |
| Column-Level Security (CLS) | ✅ | ✅ | ✅ |
| Dynamic Data Masking (DDM) | ✅ | ✅ | ✅ |
| Query Insights views | ✅ | ✅ | ✅ |
| DMVs (exec_requests, exec_sessions) | ✅ | ✅ | ✅ |
| TRUNCATE TABLE | ❌ | ❌ | ✅ |
| Data Clustering (CLUSTER BY) | ❌ | ❌ | ✅ (preview) |
| varchar(max) support | ❌ (8 KB truncation)³ | ✅ (post-Nov 2025) | ✅ (16 MB limit) |

¹ Scalar UDFs must be inlineable.
² Temp tables in SQL analytics endpoints follow the same syntax as in DW.
³ Lakehouse SQLEP maps Delta `string` → `varchar(8000)`. Mirrored items created after Nov 2025 get `varchar(max)`.

---

## Connection Fundamentals

### TDS Endpoint

All three item types expose a **TDS (Tabular Data Stream)** endpoint.

| Parameter | Value |
|---|---|
| **Server** | **(retrieve via API or passed by context)** |
| **Port** | 1433 (TCP, must be open outbound) |
| **Database** | Display name of the Warehouse/Lakehouse (NOT the FQDN) |
| **Authentication** | Microsoft Entra ID only (no SQL auth) |
| **Encryption** | Required (`Encrypt=Yes`) |
| **Token audience** | `https://database.windows.net/.default` |

**Critical system constraints**:

- Always specify the **database name** (warehouse or SQLEP name) as `Initial Catalog` or `Database` in the connection string. The FQDN alone is insufficient.
- **MARS (Multiple Active Result Sets) is not supported**. Remove `MultipleActiveResultSets` from connection strings or set it to `false`.
- Cross-database queries supported within the same workspace.

### System Token Size Limit

If a workspace contains many warehouses/SQLEPs, or the user belongs to many Entra groups, the system token can exceed limits, producing:

```
Couldn't complete the operation because we reached a system limit
```

**Mitigation**: Limit warehouses + SQLEPs to ≤ 40 per workspace.

---

## Supported T-SQL Surface Area (Consumption Focus)

### Querying

```sql
-- Basic SELECT
SELECT col1, col2 FROM dbo.MyTable WHERE col1 > 100;

-- CTEs (standard, sequential, nested)
WITH cte AS (
    SELECT col1, SUM(col2) AS total
    FROM dbo.FactSales
    GROUP BY col1
)
SELECT * FROM cte WHERE total > 1000;

-- Cross-database query (3-part naming)
SELECT a.*, b.CategoryName
FROM Lakehouse1.dbo.Sales AS a
INNER JOIN Warehouse1.dbo.DimCategory AS b
    ON a.CategoryID = b.CategoryID;

-- Aggregate functions, window functions, CASE, subqueries — all supported
SELECT
    ProductID,
    SaleDate,
    Amount,
    SUM(Amount) OVER (PARTITION BY ProductID ORDER BY SaleDate) AS RunningTotal
FROM dbo.Sales;
```

### Supported Query Features

- Standard and nested CTEs (nested CTEs in preview)
- Window functions (ROW_NUMBER, RANK, DENSE_RANK, NTILE, LAG, LEAD, SUM/AVG/MIN/MAX OVER)
- CASE expressions
- Subqueries (correlated and non-correlated)
- UNION / UNION ALL / INTERSECT / EXCEPT
- EXISTS / NOT EXISTS
- TOP / OFFSET-FETCH
- CROSS APPLY / OUTER APPLY
- A subset of query and join hints
- FOR JSON (only as the last operator; not allowed inside subqueries)
- PIVOT / UNPIVOT
- COALESCE, NULLIF, IIF, CHOOSE

### NOT Supported (Consumption Context)

| Feature | Status |
|---|---|
| `FOR XML` | Not supported |
| `SET ROWCOUNT` | Not supported |
| `SET TRANSACTION ISOLATION LEVEL` | Not supported |
| Recursive CTEs | Not supported |
| `PREDICT` | Not supported |
| Materialized views | Not supported |
| `BULK LOAD` / `OPENROWSET` (from SQLEP) | Not in SQLEP; DW supports OPENROWSET for external files |
| `CREATE USER` | Not supported (users are auto-created on GRANT/DENY) |
| Multi-column statistics (manual) | Not supported |
| Triggers | Not supported |
| Schema/table names with `/` or `\` | Not allowed |

### Data Types

**Supported Types**

| Category | Types |
|---|---|
| Exact numeric | `bigint`, `int`, `smallint`, `bit`, `decimal`/`numeric` |
| Approximate numeric | `float`, `real` |
| Date/Time | `date`, `time(n)`, `datetime2(n)` — precision limited to 6 fractional digits |
| Character | `char(n)`, `varchar(n)`, `varchar(max)` |
| Binary | `varbinary(n)`, `varbinary(max)` — max limit 16 MB in DW |
| Other | `uniqueidentifier` |

**NOT Supported Types — Use These Alternatives**

| Unsupported Type | Alternative | Notes |
|---|---|---|
| `nvarchar` / `nchar` | `varchar` / `char` | UTF-8 collation handles Unicode. May use more storage for multi-byte chars |
| `money` / `smallmoney` | `decimal(19,4)` | No monetary unit stored |
| `datetime` / `smalldatetime` | `datetime2(6)` | |
| `datetimeoffset` | `datetime2(6)` | Timezone offset is lost |
| `xml` | `varchar(max)` | XML structure and functions lost |
| `ntext` / `text` | `varchar(max)` | |
| `image` | `varbinary(max)` | |
| `geometry` / `geography` | `varbinary` (WKB) or `varchar` (WKT) | Cast as needed |
| `sql_variant` | No equivalent | |
| `hierarchyid` | No equivalent | |
| `tinyint` | `smallint` | |

**Delta-to-SQL Type Mapping (SQLEP Auto-Generated Tables)**

| Delta / Parquet Type | SQL Type in SQLEP |
|---|---|
| `string` | `varchar(8000)` in Lakehouse; `varchar(max)` in mirrored items (post-Nov 2025) |
| `int` / `long` | `int` / `bigint` |
| `double` / `float` | `float` / `real` |
| `boolean` | `bit` |
| `date` | `date` |
| `timestamp` | `datetime2(6)` |
| `decimal(p,s)` | `decimal(p,s)` |
| `binary` | `varbinary(8000)` |

**Collation**

- Default collation: `Latin1_General_100_BIN2_UTF8`
- Case-insensitive collation is available: `Latin1_General_100_CI_AS_KS_WS_SC_UTF8`
- Case-insensitive collation for SQL analytics endpoints is coming (announced Jul 2025)
- Row size limit: **8,060 bytes** per row (same as SQL Server). Exceeding produces error 511 or 611.

**varchar(max) Gotcha — Cross-Item Joins**

When joining tables across items where one has `varchar(max)` and the other has `varchar(8000)` on the same column, results may differ due to data truncation on the 8000-byte side. Cast explicitly to align:

```sql
SELECT *
FROM MirroredDB.dbo.Orders AS m
INNER JOIN Lakehouse1.dbo.Orders AS lh
    ON CAST(m.Description AS varchar(8000)) = lh.Description;
```

---

## Read-Side Objects You Can Create

Even on read-only SQL analytics endpoints, you can create views, functions, and stored procedures to build a consumption layer.

### Views

```sql
CREATE VIEW dbo.vw_ActiveCustomers
AS
SELECT CustomerID, CustomerName, Region
FROM dbo.Customers
WHERE IsActive = 1;
GO
```

### Inline Table-Valued Functions

```sql
CREATE FUNCTION dbo.fn_SalesByRegion(@Region varchar(50))
RETURNS TABLE
AS
RETURN
(
    SELECT ProductID, SUM(Amount) AS TotalSales
    FROM dbo.FactSales
    WHERE Region = @Region
    GROUP BY ProductID
);
GO

-- Usage
SELECT * FROM dbo.fn_SalesByRegion('EMEA');
```

### Scalar UDFs (Must Be Inlineable)

```sql
CREATE FUNCTION dbo.fn_FullName(@First varchar(50), @Last varchar(50))
RETURNS varchar(101)
AS
BEGIN
    RETURN @First + ' ' + @Last;
END;
GO
```

### Stored Procedures

```sql
CREATE PROCEDURE dbo.sp_TopProducts
    @TopN int = 10
AS
BEGIN
    SELECT TOP(@TopN) ProductID, SUM(Amount) AS Revenue
    FROM dbo.FactSales
    GROUP BY ProductID
    ORDER BY Revenue DESC;
END;
GO
```

On SQL analytics endpoints (Lakehouse, Mirrored DB), procedures are read-only — they cannot INSERT/UPDATE/DELETE base tables.

---

## Temporary Tables

### Two Types

| Type | Default? | Backed By | Max Size | INSERT INTO ... SELECT | Distribution |
|---|---|---|---|---|---|
| Non-distributed `#temp` | ✅ Yes (default) | MDF | Limited | ❌ Not supported | N/A |
| Distributed `#temp` | Must request | Parquet | Unlimited | ✅ Supported | ROUND_ROBIN |

### Syntax

```sql
-- Non-distributed (default)
CREATE TABLE #staging (
    ID int,
    Name varchar(100)
);

-- Distributed (preferred for large data, DML compatibility)
CREATE TABLE #staging_dist (
    ID int,
    Name varchar(100)
)
WITH (DISTRIBUTION = ROUND_ROBIN);

-- CTAS into distributed temp table
CREATE TABLE #results
WITH (DISTRIBUTION = ROUND_ROBIN)
AS
SELECT ProductID, SUM(Quantity) AS TotalQty
FROM dbo.FactSales
GROUP BY ProductID;
```

### Temp Table Guidelines

- **Prefer distributed temp tables** for consumption queries that stage intermediate results. They fully align with warehouse user tables.
- Non-distributed temp tables exist for tool compatibility (SSMS uses them internally).
- `INSERT INTO #temp SELECT ...` is **only supported for distributed temp tables**.
- Global temp tables (`##`) are **not supported**.
- Views cannot be created on temp tables.
- Temp tables are session-scoped — auto-dropped on disconnect.
- No explicit indexes on temp tables.

---

## Cross-Database Queries

A major consumption pattern: joining data across Lakehouses, Mirrored DBs, and Warehouses within the **same workspace**.

### Three-Part Naming

```sql
-- Pattern: [DatabaseName].[SchemaName].[ObjectName]
SELECT
    s.OrderID,
    s.Amount,
    c.CustomerName
FROM SalesWarehouse.dbo.Orders AS s
INNER JOIN CRMLakehouse.dbo.Customers AS c
    ON s.CustomerID = c.CustomerID;
```

### Rules and Limitations

- All items must be in the **same workspace**.
- All items must be in the **same region**.
- The query runs in the context of the item you are connected to. Query Insights records it in that item's `queryinsights` schema.
- INSERT across databases is supported only from DW (e.g., `INSERT INTO MyWarehouse.dbo.T SELECT * FROM MyLakehouse.dbo.T`).
- Cross-database views are allowed:

```sql
CREATE VIEW dbo.vw_UnifiedSales
AS
SELECT 'Warehouse' AS Source, OrderID, Amount FROM SalesWarehouse.dbo.Orders
UNION ALL
SELECT 'Lakehouse' AS Source, OrderID, Amount FROM SalesLakehouse.dbo.Orders;
GO
```

---

## Query Writing Best Practices

| Practice | Why |
|---|---|
| `SELECT` only needed columns | Reduces data scanned and network transfer |
| Filter early with `WHERE` | Pushes predicates to storage; enables file/rowgroup skipping |
| Avoid `SELECT *` | Scans all columns; wastes CUs |
| Use `TOP` / `OFFSET-FETCH` for exploration | Limits data returned for ad hoc queries |
| Use query labels (`OPTION (LABEL = ...)`) | Enables tracking and performance analysis |
| Prefer `EXISTS` over `IN` for large subqueries | Generally more efficient execution |
| Avoid unnecessary `DISTINCT` | Forces deduplication pass on entire result |
| Use appropriate data types in predicates | Avoid implicit conversions (e.g., comparing varchar to int) |
| Batch complex logic into views/procedures | Encapsulation, reuse, easier security management |
| Use `UNION ALL` instead of `UNION` when duplicates are acceptable | Skips deduplication sort |

### First-Query Latency ("Cold Start")

The first execution of a query against a Fabric DW or SQLEP can be slower than subsequent runs due to:
- Metadata loading and compilation
- Cache warming (data not yet in memory)

This is expected behavior. Subsequent runs of the same or similar queries benefit from cached metadata and compiled plans.

---

## System Catalog Queries (Metadata Exploration)

### List All Tables and Schemas

```sql
SELECT s.name AS schema_name, t.name AS table_name
FROM sys.tables AS t
INNER JOIN sys.schemas AS s ON t.schema_id = s.schema_id
ORDER BY s.name, t.name;
```

### Column Metadata (with varchar(max) Detection)

```sql
SELECT
    OBJECT_SCHEMA_NAME(c.object_id) AS schema_name,
    OBJECT_NAME(c.object_id) AS table_name,
    c.name AS column_name,
    TYPE_NAME(c.user_type_id) AS data_type,
    c.max_length,
    c.precision,
    c.scale,
    c.is_nullable
FROM sys.columns AS c
INNER JOIN sys.objects AS o ON c.object_id = o.object_id
WHERE o.type = 'U'
ORDER BY schema_name, table_name, c.column_id;
```

**Detect varchar(max) columns** (`max_length = -1`):
```sql
SELECT
    OBJECT_NAME(c.object_id) AS table_name,
    c.name AS column_name,
    TYPE_NAME(c.user_type_id) AS data_type,
    c.max_length
FROM sys.columns AS c
INNER JOIN sys.objects AS o ON c.object_id = o.object_id
WHERE c.max_length = -1
  AND TYPE_NAME(c.user_type_id) IN ('varchar', 'varbinary');
```

### List Views, Functions, Procedures

```sql
SELECT s.name AS schema_name, o.name AS object_name, o.type_desc
FROM sys.objects AS o
INNER JOIN sys.schemas AS s ON o.schema_id = s.schema_id
WHERE o.type IN ('V', 'IF', 'FN', 'TF', 'P')  -- V=view, IF=inline TVF, FN=scalar, TF=TVF, P=proc
ORDER BY o.type_desc, s.name, o.name;
```

### Check Statistics

```sql
SELECT
    OBJECT_NAME(s.object_id) AS table_name,
    s.name AS stats_name,
    s.auto_created,
    s.user_created,
    sp.last_updated,
    sp.rows,
    sp.rows_sampled
FROM sys.stats AS s
CROSS APPLY sys.dm_db_stats_properties(s.object_id, s.stats_id) AS sp
WHERE OBJECTPROPERTY(s.object_id, 'IsUserTable') = 1
ORDER BY table_name, stats_name;
```

---

## Common Consumption Patterns (End-to-End Examples)

### Cross-Database Analytics Across Lakehouse and Warehouse

```sql
-- Connected to Warehouse in same workspace
SELECT
    lh.EventDate,
    lh.EventType,
    lh.UserID,
    wh.UserName,
    wh.Department
FROM EventsLakehouse.dbo.UserEvents AS lh
INNER JOIN UsersWarehouse.dbo.DimUser AS wh
    ON lh.UserID = wh.UserID
WHERE lh.EventDate >= '2025-01-01'
OPTION (LABEL = 'XQUERY_EventsWithUsers');
```

### Exploratory Query with Temp Table Staging

```sql
-- Stage filtered data into distributed temp table
CREATE TABLE #recent_orders
WITH (DISTRIBUTION = ROUND_ROBIN)
AS
SELECT OrderID, CustomerID, Amount, OrderDate
FROM dbo.FactSales
WHERE OrderDate >= DATEADD(DAY, -30, GETUTCDATE());

-- Analyze staged data (multiple queries without rescanning)
SELECT CustomerID, COUNT(*) AS OrderCount, SUM(Amount) AS TotalSpend
FROM #recent_orders
GROUP BY CustomerID
ORDER BY TotalSpend DESC;

SELECT
    CAST(OrderDate AS date) AS Day,
    SUM(Amount) AS DailyRevenue
FROM #recent_orders
GROUP BY CAST(OrderDate AS date)
ORDER BY Day;

-- Cleanup (optional — auto-dropped on disconnect)
DROP TABLE #recent_orders;
```

---

## Gotchas and Troubleshooting Reference

| # | Issue | Cause | Resolution |
|---|---|---|---|
| 1 | `FOR XML` in subquery | Only allowed as last operator | Restructure query; use FOR JSON instead or move to outer query |
| 2 | Table not visible in SQLEP | Delta table outside `/tables` folder, or metadata sync lag | Move data to `/tables`; force Refresh (portal or REST API) |
| 3 | `uniqueidentifier` cross-join mismatch | Stored as binary in Delta; doesn't round-trip through Spark | Avoid cross-joining on uniqueidentifier between DW and Lakehouse |
| 4 | `INSERT INTO #temp SELECT` fails | Using non-distributed temp table | Add `WITH (DISTRIBUTION = ROUND_ROBIN)` to CREATE TABLE |
| 5 | Foreign key on SQLEP blocks schema updates | FK constraint prevents auto-schema changes | Drop the FK constraint to allow new Delta columns to sync |
| 6 | `NVARCHAR` type not found | Not supported in Fabric | Use `varchar` with UTF-8 collation |
| 7 | Error 511 / 611 on INSERT | Row exceeds 8,060 byte limit | Reduce column sizes; split wide tables |
| 8 | `SET TRANSACTION ISOLATION LEVEL` fails | Not supported | Remove from scripts; Fabric uses snapshot isolation internally |
| 9 | Query killed after failover | Session-scoped #temp tables lost on front-end failover | Re-create temp tables; design for session transience |
| 10 | Slow queries on Lakehouse SQLEP | Small-file problem; unoptimized Delta tables | Run `OPTIMIZE` and `VACUUM` on lakehouse tables via Spark (fuori scope di questo progetto: solo segnalare) |
| 11 | BIN2 collation causes unexpected string comparisons | Default collation is `Latin1_General_100_BIN2_UTF8` (case-sensitive, binary) | Use explicit `COLLATE` in comparisons if needed; or use CI collation on DW |
| 12 | OPENROWSET on SQLEP | Not available on SQL analytics endpoints | Use Spark for file-level access; or use DW with OPENROWSET for external files |
| 13 | Cross-region connection fails | Source and target items in different regions | Ensure all items share the same region |
| 14 | Queries on Delta timestamp columns slow | Missing rowgroup-level stats (Spark runtime < 3.5.0) | Upgrade to Spark 3.5.0+; recreate and re-ingest table |

---

## Quick Reference: Consumption Capabilities by Scenario

| Scenario | Recommended Approach |
|---|---|
| Power BI report on lakehouse data | Connect to SQLEP; build views in `reporting` schema; use DirectQuery or Import |
| Ad hoc SQL exploration | Connect via SSMS 19+ or VS Code mssql extension; use TOP/OFFSET for pagination |
| Cross-source analytics | Use 3-part naming across items in same workspace |
| Stage intermediate results | Use distributed `#temp` tables with `ROUND_ROBIN` |
