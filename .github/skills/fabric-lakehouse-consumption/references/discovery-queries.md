# Query di Schema Discovery Estese

Query per l'esplorazione approfondita dello schema, oltre alla sequenza base
in [consumption.md](consumption.md). Funzionano su Lakehouse SQL endpoint,
Warehouse e Mirrored DB.

> **Esecuzione**: tutte le query sotto vanno passate come parametro `query`
> a `execute_query(workspaceId, itemId, "<query>")` — vedi
> [consumption.md](consumption.md) per la firma del tool.
>
> **Una query per chiamata.** Dove una sezione elenca più `SELECT`
> indipendenti, ognuno è una chiamata `execute_query` separata — il tool
> restituisce solo l'**ultimo** result set di un batch multi-statement.

## Schema e Metadati Oggetti

### Metadati Tabelle e Colonne

```sql
-- Tutte le colonne di tutte le tabelle con i tipi
SELECT t.table_schema, t.table_name, c.column_name,
       c.data_type, c.character_maximum_length,
       c.numeric_precision, c.numeric_scale, c.is_nullable
FROM INFORMATION_SCHEMA.TABLES t
JOIN INFORMATION_SCHEMA.COLUMNS c
  ON t.table_schema = c.table_schema AND t.table_name = c.table_name
WHERE t.table_type = 'BASE TABLE'
ORDER BY t.table_schema, t.table_name, c.ordinal_position;

-- Tabelle con conteggio righe e colonne
SELECT s.name AS [schema], t.name AS [table],
       COUNT(DISTINCT c.column_id) AS col_count,
       SUM(p.rows) AS row_count
FROM sys.tables t
JOIN sys.schemas s ON t.schema_id = s.schema_id
JOIN sys.columns c ON t.object_id = c.object_id
JOIN sys.partitions p ON t.object_id = p.object_id AND p.index_id IN (0,1)
GROUP BY s.name, t.name
ORDER BY row_count DESC;

-- Constraint (PK, FK, UNIQUE)
SELECT tc.constraint_type, tc.table_schema, tc.table_name,
       tc.constraint_name, kcu.column_name
FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
  ON tc.constraint_name = kcu.constraint_name
ORDER BY tc.table_schema, tc.table_name, tc.constraint_type;

-- Relazioni foreign key (utili per suggerire JOIN)
SELECT
    fk.name AS fk_name,
    OBJECT_SCHEMA_NAME(fk.parent_object_id) + '.' + OBJECT_NAME(fk.parent_object_id) AS child_table,
    COL_NAME(fkc.parent_object_id, fkc.parent_column_id) AS child_column,
    OBJECT_SCHEMA_NAME(fk.referenced_object_id) + '.' + OBJECT_NAME(fk.referenced_object_id) AS parent_table,
    COL_NAME(fkc.referenced_object_id, fkc.referenced_column_id) AS parent_column
FROM sys.foreign_keys fk
JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
ORDER BY child_table, fk_name;
```

### Definizioni Viste e Funzioni

```sql
-- Definizioni viste (SQL sorgente)
SELECT s.name AS [schema], v.name AS [view],
       m.definition
FROM sys.views v
JOIN sys.schemas s ON v.schema_id = s.schema_id
JOIN sys.sql_modules m ON v.object_id = m.object_id
ORDER BY s.name, v.name;

-- Definizioni funzioni
SELECT s.name AS [schema], o.name AS [function], o.type_desc,
       m.definition
FROM sys.objects o
JOIN sys.schemas s ON o.schema_id = s.schema_id
JOIN sys.sql_modules m ON o.object_id = m.object_id
WHERE o.type IN ('FN','IF','TF')
ORDER BY s.name, o.name;
```

### Discovery Cross-Database

```sql
-- Elenca tutti i database accessibili nel workspace
SELECT name, create_date FROM sys.databases ORDER BY name;

-- Tabelle in un altro database (nome a 3 parti)
SELECT table_schema, table_name FROM OtherDatabase.INFORMATION_SCHEMA.TABLES ORDER BY table_schema, table_name;
```

## Statistiche e Metadati Performance

```sql
-- Statistiche sulle tabelle
SELECT OBJECT_SCHEMA_NAME(s.object_id) AS [schema],
       OBJECT_NAME(s.object_id) AS [table],
       s.name AS stat_name,
       COL_NAME(sc.object_id, sc.column_id) AS column_name,
       STATS_DATE(s.object_id, s.stats_id) AS last_updated
FROM sys.stats s
JOIN sys.stats_columns sc ON s.object_id = sc.object_id AND s.stats_id = sc.stats_id
ORDER BY [schema], [table], stat_name;
```
