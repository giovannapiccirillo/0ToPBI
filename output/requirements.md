# Requisiti del Report

## Setup
- Nome report: Report Vendite Mensile per il Management
- Modalità di raccolta: requisiti già forniti (fonte: `input/requisiti_report_vendite.docx` + `input/vendite.csv` + `input/prodotti.csv`)

## Audience e Scopo
- Audience: Direzione Commerciale (utente primario, consumo desktop/tablet), Sales Manager di area (monitoraggio della propria regione e prodotti), Controllo di Gestione (coerenza tra fatturato, margine e sconti)
- Scopo primario: fornire una vista sintetica e navigabile delle performance di vendita mensili, a supporto delle decisioni su allocazione budget e focus commerciale/prodotto
- Tono: executive, sintetico e orientato alle decisioni; leggibile su desktop e tablet
- Criteri di successo: KPI principali immediatamente visibili; confronto temporale MoM e YoY; analisi di fatturato, margine, sconti e top prodotti per area e categoria; supporto alle decisioni su budget e focus commerciale/prodotto

## Dati Disponibili e Granularità
- Tipo di DB: estrazione in file tabellari locali (CSV); nessuna connessione live a un database (ambiente solo Power BI Desktop locale, no Fabric/servizio)
- Modalità di connessione: Import
- Tabelle/file attesi in input/:
  - `vendite.csv` — tabella fatti, una riga per linea d'ordine; colonne: `OrderID`, `OrderDate`, `ProductID`, `CustomerName`, `Region`, `Quantity`, `UnitPrice`, `Discount`
  - `prodotti.csv` — anagrafica prodotti; colonne: `ProductID`, `ProductName`, `Category`, `SubCategory`, `UnitCost`
- Granularità: una riga sorgente = una linea d'ordine (un prodotto per ordine, con quantità e sconto applicato); periodo dati 2024–2025 (24 mesi) per consentire il confronto YoY
- Gap noti:
  - Non esiste una tabella Calendario nei file sorgente: la gerarchia Anno → Mese richiesta va costruita in fase 2 a partire da `OrderDate`
  - `Region` e `CustomerName` sono denormalizzati nella tabella fatti: l'eventuale normalizzazione in dimensioni separate è una decisione di modellazione di fase 2
  - Refresh dati manuale (import), nessun refresh incrementale richiesto

## Mapping Requisiti → Schema Target
| Requisito atomico | Tabella.Colonna proposta | Allineato? | Note |
|---|---|---|---|
| Andamento del fatturato mese su mese e anno su anno | vendite.OrderDate, vendite.Quantity, vendite.UnitPrice, vendite.Discount | Sì | Richiede tabella Calendario (assente nei sorgenti, da creare in fase 2 da `OrderDate`) e misure di time intelligence |
| Fatturato e margine per categoria/prodotto | vendite.ProductID + prodotti.Category, prodotti.SubCategory, prodotti.ProductName | Sì | Richiede collegamento vendite↔prodotti su `ProductID` (stesso tipo/formato nei due file) |
| Distribuzione delle vendite per area geografica | vendite.Region | Sì | Denormalizzata nella tabella fatti; nessuna gerarchia geografica richiesta |
| Impatto degli sconti applicati sul margine | vendite.Discount, vendite.Quantity, vendite.UnitPrice + prodotti.UnitCost | Sì | Margine calcolabile solo agganciando il costo unitario da `prodotti.csv` via `ProductID` |
| Top 10 prodotti per fatturato nel periodo selezionato | vendite.ProductID + prodotti.ProductName | Sì | Ranking su misura di fatturato (fase 2) |
| Valore medio ordine e sua variazione nel tempo | vendite.OrderID, vendite.OrderDate | Sì | Conteggio distinto di `OrderID`; serve nuova misura in fase 2 |
| Fatturato Totale = Quantità × Prezzo × (1 − Sconto) | vendite.Quantity, vendite.UnitPrice, vendite.Discount | Sì | Serve nuova misura in fase 2 |
| Quantità Totale Venduta | vendite.Quantity | Sì | Serve nuova misura in fase 2 |
| Sconto Medio % pesato sul fatturato | vendite.Discount, vendite.Quantity, vendite.UnitPrice | Sì | Media pesata, non media semplice della colonna |
| Costo Totale, Margine e Margine % | vendite.Quantity + prodotti.UnitCost | Sì | Richiede il collegamento vendite↔prodotti su `ProductID` |
| Fatturato YTD, Var. % MoM, Var. % YoY | vendite.OrderDate + misure di fatturato | Sì | Time intelligence in fase 2, dipende dalla tabella Calendario |
| Analisi/filtro per cliente | vendite.CustomerName | Sì | Solo elenco/filtro, nessuna gerarchia cliente richiesta |
| Gerarchia temporale Anno → Mese | (nessuna colonna esistente) | No | Nei sorgenti esiste solo `OrderDate`: la tabella Calendario con gerarchia va creata in fase 2 |

### Domande Aperte
- Nessuna domanda bloccante: il documento requisiti copre fonte, granularità, misure e output attesi. Le decisioni segnalate (tabella Calendario, eventuale normalizzazione di Regione/Cliente in dimensioni) sono scelte di modellazione demandate alla fase 2.

## KPI e Metriche Chiave
- KPI (esistenti vs. che necessitano nuove misure):
  - Fatturato Totale — serve nuova misura: Quantità × Prezzo Unitario × (1 − Sconto)
  - Quantità Totale Venduta — serve nuova misura: somma di `Quantity`
  - Sconto Medio % — serve nuova misura: media dello sconto pesata sul fatturato
  - Costo Totale — serve nuova misura: Quantità × `UnitCost` di prodotto
  - Margine — serve nuova misura: Fatturato Totale − Costo Totale
  - Margine % — serve nuova misura: Margine / Fatturato Totale
  - Fatturato YTD — serve nuova misura: fatturato cumulato da inizio anno
  - Var. % Fatturato MoM — serve nuova misura: variazione vs mese precedente
  - Var. % Fatturato YoY — serve nuova misura: variazione vs stesso mese anno precedente
  - Numero Ordini — serve nuova misura: conteggio distinto di `OrderID`
  - Valore Medio Ordine — serve nuova misura: Fatturato Totale / Numero Ordini
- Calcoli mancanti segnalati per la fase 2:
  - Tabella Calendario dedicata con gerarchia Anno → Mese (da `OrderDate`)
  - Misure di time intelligence: YTD, variazione MoM, variazione YoY
  - Collegamento vendite↔prodotti su `ProductID` per le misure di costo e margine

## Numero Pagine, Visual Desiderati e Layout
1. Executive Summary — scopo: panoramica sintetica delle performance complessive di vendita
   - Visual: card KPI Fatturato Totale
   - Visual: card KPI Margine %
   - Visual: card KPI Numero Ordini
   - Visual: card KPI Var. % YoY
   - Visual: line chart trend mensile del Fatturato Totale con confronto anno precedente
   - Visual: barre top 5 categorie per fatturato
   - Filtri: periodo, regione, categoria, cliente
2. Analisi Prodotto & Area — scopo: analisi di dettaglio per prodotto e area geografica
   - Visual: matrice Prodotto × Regione con Fatturato Totale
   - Visual: barre top 10 prodotti per Fatturato Totale
   - Visual: barre Sconto Medio % per categoria
   - Filtri: periodo, regione, categoria, sottocategoria, cliente

## Filtri/Slicer
- Periodo (Anno/Mese) — globale
- Regione — globale
- Categoria — globale
- Cliente — globale
- Sottocategoria — specifico per pagina Analisi Prodotto & Area

## Direzione di Design (bozza)
- Tono: pulito, executive, orientato al business e alla lettura rapida dei KPI
- Note/preferenze (incl. branding, se citato): KPI in alto e analisi di dettaglio sotto; colori sobri con un colore guida per evidenziare trend positivi/negativi; filtri facilmente accessibili e coerenti tra le pagine; valuta di riferimento EUR

## Vincoli, Rischi, Note
- Vincolo: ambiente solo Power BI Desktop locale (no Fabric/servizio, no Direct Lake)
- Vincolo: refresh dati manuale in Import, nessun refresh incrementale richiesto
- Vincolo: nessun drill-through richiesto nella prima release
- Nota: periodo dati disponibile 2024–2025 (24 mesi), sufficiente per i confronti YoY
- Nota: criteri di approvazione del progetto — star schema con tabella fatti Vendite al centro, tutte le misure della sezione KPI implementate e validate in fase 2, entrambe le pagine coperte con i visual richiesti, nessun errore di validazione residuo su modello e report PBIR
