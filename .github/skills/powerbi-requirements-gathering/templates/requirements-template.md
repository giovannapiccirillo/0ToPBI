# Requisiti del Report

## Setup
- Nome report:
- Modalità di raccolta: proposta da zero | requisiti già forniti (fonte: ...)

## Audience e Scopo
- Audience: {es. "Leadership — KPI concisi, trend, rischi"; "Analisti — drill-down e comparazioni"; "Audience esterna — storytelling guidato"}
- Scopo primario: {compito che il report deve supportare, es. "monitorare le performance", "trovare anomalie o opportunità"}
- Tono:
- Criteri di successo:

## Dati Disponibili e Granularità
- Tipo di DB:
- Modalità di connessione: Import | DirectQuery | Fabric Lakehouse | Import + Fabric Lakehouse
- Tabelle/file attesi in input/<NomeProgetto>/ (oppure workspace/Lakehouse Fabric):
- Gap noti: {oppure "Non applicabile: nessun gap emerso" se non ce ne sono}

## Mapping Requisiti → Schema Target

{da compilare ogni volta che è disponibile un documento/testo di requisiti; una riga per requisito atomico. Tabella.Colonna riportata solo se dichiarata esplicitamente nei requisiti stessi; ogni altro requisito → "Da confermare in fase 1.5" (lo schema reale lo esplora data-analyst, mai ispezionato qui). "Non applicabile" solo se non c'è alcun documento/testo di requisiti}

| Requisito atomico | Tabella.Colonna proposta | Allineato? | Note |
|---|---|---|---|

### Domande Aperte

{una riga per gap bloccante emerso; se non ce ne sono, scrivere "Non applicabile: nessun gap emerso", non lasciare un trattino vuoto}

## KPI e Metriche Chiave
- KPI: {una riga per KPI — "<nome KPI> — misura esistente: <nome>" oppure "<nome KPI> — serve nuova misura"}
- Calcoli mancanti segnalati per la fase 2: {misura/colonna calcolata necessaria e perché, o "Non applicabile: nessun calcolo mancante"}

## Numero Pagine, Visual Desiderati e Layout
1. {Nome pagina} — scopo: {a cosa serve questa pagina}
   - Visual: {primo visual desiderato, per nome/tipo — es. "card KPI soddisfazione media"}
   - Visual: {altri visual, uno per riga; marcare "(opzionale)" se non essenziale}
   - Filtri: {elenco filtri/slicer proposti per questa pagina}
2. ...

## Filtri/Slicer
{riepilogo aggregato dei filtri già raccolti per pagina sopra — un bullet per dimensione filtrabile, non nuove domande}
- {dimensione} — globale | specifico per pagina {Nome pagina}

## Direzione di Design (bozza)
- Tono:
- Note/preferenze (incl. branding, se citato):

## Vincoli, Rischi, Note
- {un bullet per ogni vincolo/rischio/nota emerso in qualsiasi round e non rientrante nelle sezioni sopra: scadenze, limiti di licenza, dipendenze da dati non ancora disponibili, preferenze organizzative, ecc. Se non ne è emerso nessuno, scrivere "Non applicabile: nessun vincolo/rischio/nota emerso"}
