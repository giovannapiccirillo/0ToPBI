# Design Brief — Report Vendite Mensile per il Management (progetto Prova)

Contratto di design della fase 3, derivato da `output/requirements.md` approvato.
Il blocco YAML sottostante è il contratto canonico implementato nei file PBIR di
`report/Prova.Report/`.

## Canonical design contract

```yaml
Design Brief:
  generated_by: powerbi-report-design
  contract_version: 1
  mode: greenfield
  design_identity:
    tone: "Corporate Cool - superficie grigio freddo #F1F5F9, card bianche, testo slate, colori sobri"
    signature: "Card KPI con accent bar sinistra 4px nel colore della misura; anno corrente in blu, anno precedente in grigio (highlight-and-grey) su ogni pagina"
  archetype: Executive
  color_map:
    - measure: Vendite[Fatturato Totale]
      color: "#0072B2"
      tint: "#D2E8F4"
    - measure: Vendite[Margine %]
      color: "#009E73"
      tint: "#CCEBE3"
    - measure: Vendite[Numero Ordini]
      color: "#D55E00"
      tint: "#F6DECC"
    - measure: Vendite[Var. % Fatturato YoY]
      color: "#64748B"
      tint: "#E0E4E9"
    - measure: Vendite[Sconto Medio %]
      color: "#CC79A7"
      tint: "#F2DEE9"
  pages:
    - name: "Andamento vendite mensile: fatturato, margine e confronto anno su anno"
      role: landing
      archetype: Executive
      layout_variant: B
      variant_rationale: "4 KPI di pari importanza (nessun hero singolo) + due chart di analisi: e' esattamente la firma della variante KPI-Strip; la variante A richiederebbe un hero dominante che i requisiti non individuano."
      page_background: "#F1F5F9"
      layout_summary: "Banda titolo+4 slicer in alto, striscia di 4 card KPI, poi trend mensile (2/3) e barre per categoria (1/3), footer fonte dati."
      layout_contract:
        canvas: { width: 1920, height: 1080, margin: 32, gutter: 24, snap: 8 }
        grid:
          columns: 12
          rows: 12
          regions:
            header:  [1, 1, 7, 2]
            filters: [7, 1, 13, 2]
            kpis:    [1, 2, 13, 4]
            trend:   [1, 4, 9, 12]
            ranking: [9, 4, 13, 12]
            footer:  [1, 12, 13, 13]
        placements:
          - id: page_title
            region: header
            kind: textbox
            text: "Andamento vendite mensile: fatturato, margine e confronto anno su anno"
          - { id: slicer_periodo, region: filters, kind: slicer, field_bindings: "Calendario[Anno - Mese] (gerarchia)", slicer_type: dropdown, slot: 1, of: 4 }
          - { id: slicer_regione, region: filters, kind: slicer, field_bindings: "Vendite[Region]", slicer_type: dropdown, slot: 2, of: 4 }
          - { id: slicer_categoria, region: filters, kind: slicer, field_bindings: "Prodotti[Category]", slicer_type: dropdown, slot: 3, of: 4 }
          - { id: slicer_cliente, region: filters, kind: slicer, field_bindings: "Vendite[CustomerName]", slicer_type: dropdown, slot: 4, of: 4 }
          - { id: card_fatturato, region: kpis, kind: cardVisual, purpose: "Quanto abbiamo fatturato?", field_bindings: "Vendite[Fatturato Totale]", color_strategy: measure_match, slot: 1, of: 4 }
          - { id: card_margine, region: kpis, kind: cardVisual, purpose: "Con che redditivita'?", field_bindings: "Vendite[Margine %]", color_strategy: measure_match, slot: 2, of: 4 }
          - { id: card_ordini, region: kpis, kind: cardVisual, purpose: "Su quanti ordini?", field_bindings: "Vendite[Numero Ordini]", color_strategy: measure_match, slot: 3, of: 4 }
          - { id: card_yoy, region: kpis, kind: cardVisual, purpose: "Meglio o peggio dell'anno scorso?", field_bindings: "Vendite[Var. % Fatturato YoY]", color_strategy: measure_match, slot: 4, of: 4, insight_basis: "delta YoY: e' la misura di confronto periodo-su-periodo richiesta" }
          - { id: trend_mensile, region: trend, kind: lineChart, purpose: "Come evolve il fatturato mese su mese rispetto all'anno precedente?", field_bindings: { Category: "Calendario[Mese]", Series: "Calendario[Anno]", Y: "Vendite[Fatturato Totale]", Tooltips: "MoM %, YoY %, YTD" }, color_strategy: semantic, comparison_basis: "stesso mese anno precedente (serie per anno: 2024 grigio, 2025 blu)" }
          - { id: bar_categorie, region: ranking, kind: barChart, purpose: "Quali categorie generano piu' fatturato?", field_bindings: { Category: "Prodotti[Category]", Y: "Vendite[Fatturato Totale]" }, sort_policy: value_desc, color_strategy: gradient }
          - { id: footer_fonte, region: footer, kind: textbox, text: "Fonte: staging/vendite.csv e prodotti.csv - refresh manuale (Import) - Periodo dati 2024-2025" }
        space_audit:
          content_cell_count: 132
          placed_cell_count: 132
          empty_cell_pct: 0
          unplaced_regions: []
          largest_region: { name: trend, pct_of_content: 48 }
          balance_rationale: "Il trend mensile e' l'evidenza principale del confronto YoY richiesto (regione hero 2/3); il ranking categorie (solo 3 categorie nei dati) sta comodo in 1/3; striscia KPI su 2 righe e footer riempiono il resto senza bande morte."
      note_topn: "Nei dati staging esistono 3 categorie: 'top 5 categorie' equivale a tutte, quindi nessun filtro TopN e' necessario (solo ordinamento decrescente)."
    - name: "Dettaglio per prodotto e area: dove si concentrano fatturato e sconti"
      role: detail
      archetype: Analytical
      layout_variant: A
      variant_rationale: "5 slicer richiesti (incl. Sottocategoria, solo su questa pagina) giustificano il filter-rail verticale (~50% di riempimento colonna); la variante B inline non ospita 5 controlli nella banda titolo."
      page_background: "#F1F5F9"
      layout_summary: "Titolo in alto, rail sinistro con 5 slicer, due bar chart affiancati (top 10 prodotti, sconto medio per categoria), matrice prodotto x regione a tutta larghezza, footer."
      layout_contract:
        canvas: { width: 1920, height: 1080, margin: 32, gutter: 24, snap: 8 }
        grid:
          columns: 12
          rows: 12
          regions:
            header: [1, 1, 13, 2]
            rail:   [1, 2, 3, 13]
            charts: [3, 2, 13, 7]
            detail: [3, 7, 13, 12]
            footer: [3, 12, 13, 13]
        placements:
          - id: page_title
            region: header
            kind: textbox
            text: "Dettaglio per prodotto e area: dove si concentrano fatturato e sconti"
          - { id: slicer_periodo, region: rail, kind: slicer, field_bindings: "Calendario[Anno - Mese] (gerarchia)", slicer_type: dropdown, slot: 1, of: 5 }
          - { id: slicer_regione, region: rail, kind: slicer, field_bindings: "Vendite[Region]", slicer_type: dropdown, slot: 2, of: 5 }
          - { id: slicer_categoria, region: rail, kind: slicer, field_bindings: "Prodotti[Category]", slicer_type: dropdown, slot: 3, of: 5 }
          - { id: slicer_sottocategoria, region: rail, kind: slicer, field_bindings: "Prodotti[SubCategory]", slicer_type: dropdown, slot: 4, of: 5 }
          - { id: slicer_cliente, region: rail, kind: slicer, field_bindings: "Vendite[CustomerName]", slicer_type: dropdown, slot: 5, of: 5 }
          - { id: bar_top10_prodotti, region: charts, kind: barChart, purpose: "Quali prodotti trainano il fatturato?", field_bindings: { Category: "Prodotti[ProductName]", Y: "Vendite[Fatturato Totale]" }, sort_policy: value_desc, color_strategy: gradient, slot: 1, of: 2 }
          - { id: bar_sconto_categoria, region: charts, kind: barChart, purpose: "Dove pesano di piu' gli sconti?", field_bindings: { Category: "Prodotti[Category]", Y: "Vendite[Sconto Medio %]" }, sort_policy: value_desc, color_strategy: gradient, slot: 2, of: 2 }
          - { id: matrice_prodotto_regione, region: detail, kind: pivotTable, purpose: "Come si distribuisce il fatturato per prodotto e regione?", field_bindings: { Rows: "Prodotti[ProductName]", Columns: "Vendite[Region]", Values: "Vendite[Fatturato Totale]" }, color_strategy: gradient }
          - { id: footer_fonte, region: footer, kind: textbox, text: "Fonte: staging/vendite.csv e prodotti.csv - refresh manuale (Import) - Periodo dati 2024-2025" }
        space_audit:
          content_cell_count: 110
          placed_cell_count: 110
          empty_cell_pct: 0
          unplaced_regions: []
          largest_region: { name: detail, pct_of_content: 45 }
          balance_rationale: "La matrice e' il visual di dettaglio richiesto e riceve la fascia inferiore piena; i due bar chart si dividono equamente la fascia superiore; il rail ospita i 5 filtri richiesti."
      note_topn: "I prodotti nei dati staging sono esattamente 10: 'top 10 prodotti' equivale a tutti, quindi nessun filtro TopN e' necessario (solo ordinamento decrescente)."
  interaction_pattern:
    drill_targets: []
    cross_filter_rules: "default cross-filter tra i visual della pagina (drillFilterOtherVisuals attivo); nessun drill-through nella prima release (vincolo requisiti)"
    sync_slicers: "Periodo/Regione/Categoria/Cliente sincronizzati tra le due pagine via syncGroup (SyncPeriodo, SyncRegione, SyncCategoria, SyncCliente); Sottocategoria solo pagina 2"
  accessibility:
    alt_text_strategy: "headline+trend: alt text specifico per contenuto su ogni visual dati"
    contrast_notes: "Testo #252423/#605E5C su bianco e #F1F5F9 rispetta WCAG AA; le etichette dati dei chart usano neutro scuro, mai il colore accento"
  theme:
    base: "assets/base.json adattato (safeguard testbox/tableEx/pivotTable preservati) -> StaticResources/RegisteredResources/ProvaCorporate-95b341dc.json"
    user_overrides: "dataColors[0]=#94A3B8 (grigio anno precedente), dataColors[1]=#0072B2 (blu anno corrente) per la firma highlight-and-grey del trend; nessun tema preesistente da preservare"
```

## Note di implementazione

- Le card KPI mostrano valore + etichetta; il contesto periodo-su-periodo richiesto
  dai requisiti è coperto dalla card dedicata "Var. % Fatturato vs Anno Prec." e
  dai tooltip (MoM %, YoY %, YTD) sul trend mensile.
- Lo slicer Periodo usa la gerarchia `Calendario['Anno - Mese']` in modalità
  dropdown (griglia annuale/mensile, 24 periodi), come da matrice decisionale
  slicer temporali; niente slicer `Between` su data piena.
- Deviazione dichiarata: la pagina 1 tiene 4 slicer inline nella banda titolo
  (la soglia consigliata è 3) perché i requisiti chiedono filtri "facilmente
  accessibili e coerenti tra le pagine"; a FHD i 4 dropdown da 200px stanno nella
  banda senza comprimere il titolo.
- Validazione PBIR: `powerbi-report-author validate report/Prova.Report` →
  succeeded, 0 errori, 0 warning.
