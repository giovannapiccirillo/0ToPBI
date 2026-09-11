# Log Trasformazioni ETL

## vendite.csv
- Data: 2026-09-01
- Sorgente: input/vendite.csv
- Righe in ingresso / in uscita: 1285 / 1285
- Trasformazioni applicate:
  - Quantity: normalizzazione decimal (requisito di riferimento: Quantità Totale Venduta (somma di Quantity) e Fatturato Totale = Quantità × Prezzo × (1 − Sconto))
  - UnitPrice: normalizzazione decimal (requisito di riferimento: Fatturato Totale = Quantità × Prezzo × (1 − Sconto))
  - Discount: normalizzazione decimal (requisito di riferimento: Sconto Medio % pesato sul fatturato e impatto degli sconti sul margine)
- Dettaglio: rappresentazione numerica uniformata a float con punto decimale
  (es. `Quantity` 4 → 4.0 su 1285 righe, `Discount` 0 → 0.0 su 529 righe;
  `UnitPrice` già conforme, valori invariati)
- Verifiche effettuate (nessuna correzione necessaria):
  - `OrderDate`: già ISO 8601 (`YYYY-MM-DD`) su tutte le 1285 righe, periodo 2024-01-03 → 2025-12-31 coerente con la granularità attesa (24 mesi per confronto YoY)
  - `OrderID`: nessun duplicato su chiave
  - Nessun valore mancante in alcuna colonna
  - Integrità referenziale: tutti i `ProductID` presenti in `prodotti.csv`, stesso tipo/formato (requisito: collegamento vendite↔prodotti su `ProductID` per costo e margine)
- Anomalie segnalate (non corrette automaticamente):
  - Nessuna

## prodotti.csv
- Data: 2026-09-01
- Sorgente: input/prodotti.csv
- Righe in ingresso / in uscita: 10 / 10
- Trasformazioni applicate:
  - Nessuna: dati già conformi allo schema atteso
- Verifiche effettuate (nessuna correzione necessaria):
  - `ProductID`: nessun duplicato su chiave (10 prodotti P001–P010)
  - `UnitCost`: già numerico con punto decimale, nessun separatore di migliaia o simbolo valuta
  - Nessun valore mancante in alcuna colonna; encoding UTF-8 conforme
- Anomalie segnalate (non corrette automaticamente):
  - Nessuna
