# Reference — Mapping Requisiti → Schema Target

Si applica quando è disponibile un documento/testo di requisiti (`input/<NomeProgetto>/` o chat) da cui estrarre requisiti atomici — indipendentemente dal fatto che esista già una fonte-schema locale o Fabric.

**Confine con `data-analyst` (fase 2)**: `requirements-analyst` **non ispeziona mai lo schema** (né apre file `.xlsx`/`.csv` per leggerne le intestazioni, né esplora un Lakehouse Fabric) per dedurre un match `Tabella.Colonna`. Leggere lo schema reale — locale o Fabric — è compito esclusivo di `data-analyst` in fase 2. Questa sezione produce quindi solo:
- un match `Tabella.Colonna` **se e solo se è dichiarato esplicitamente nei requisiti stessi** (il documento o l'utente nomina letteralmente la tabella/colonna, es. "usa la colonna ImportoFatturato della tabella Vendite");
- altrimenti `Da confermare in fase 2`, per qualunque fonte (locale o Fabric) — stesso trattamento, non solo per Fabric.

Il mapping è "Non applicabile" solo quando non c'è alcun documento/testo di requisiti da cui estrarre requisiti atomici.

## Bozza di soluzione preesistente

Se nell'input è presente anche una "soluzione iniziale" (una proposta di mapping o di modello preesistente), leggila come qualunque altro file di input: può contenere requisiti o contesto utile. Il match `Tabella.Colonna` che eventualmente propone, però, non è una dichiarazione dell'utente — riportalo comunque come `Da confermare in fase 2` (vedi Output), esattamente come ogni altro requisito senza match esplicito nei requisiti stessi.

## Procedura

1. Leggi il documento dei requisiti (e il testo aggiuntivo in chat, se presente — la chat integra o corregge il documento, non lo sostituisce silenziosamente) e **spezzalo in requisiti atomici** (un'esigenza verificabile per voce).
2. Per ciascun requisito atomico:
   - se il documento/utente nomina esplicitamente la tabella/colonna che lo soddisfa, riportala così com'è dichiarata — non verificarne l'allineamento (tipo dato, granularità): quella verifica richiede di aprire lo schema, compito di `data-analyst`;
   - in tutti gli altri casi (match deducibile solo ispezionando file locali o Fabric), segna `Da confermare in fase 2` — non proporre un nome dedotto autonomamente.
3. Se il documento requisiti non è disponibile, non procedere per supposizioni: fai domande specifiche e mirate sui requisiti mancanti (mai domande generiche o aperte), poi applica il punto 2 alle risposte raccolte.

## Refuso trasversale

Fermati e chiedi — mai ipotesi implicite — in questi casi:

- **Manca ogni fonte di requisiti**: né documento né testo in chat da cui estrarre requisiti atomici.
- **Manca la modalità/tipo di connessione al db reale** per la componente locale, quando servirà alla fase 2 (per la componente Fabric la modalità è già `Fabric Lakehouse`: non richiederla di nuovo).
- **Il requisito stesso è ambiguo o incompleto** indipendentemente dallo schema (es. non è chiaro a quale entità si riferisce, o mescola più esigenze in una voce sola).

Le domande vanno sempre riferite al gap specifico, mai un questionario generico. Riportale (se presenti) nella sotto-sezione "Domande Aperte" dentro **Mapping Requisiti → Schema Target** di `output/<NomeProgetto>/requirements.md`.

## Output

Riga per riga nella tabella `## Mapping Requisiti → Schema Target` del template:

```markdown
| Requisito atomico | Tabella.Colonna proposta | Allineato? | Note |
|---|---|---|---|
| <requisito con match dichiarato esplicitamente nei requisiti> | <Tabella.Colonna come dichiarata> | — | allineamento da verificare in fase 2 |
| <ogni altro requisito atomico> | Da confermare in fase 2 | — | schema da esplorare con `data-analyst` |
```

Questa sezione si aggiunge a quelle previste dal template quando applicabile — non sostituisce il Round 2, fonte di verità per la raccolta di tipo di DB/modalità di connessione/tabelle attese.

## Elaborazione incrementale per file grandi

Quando converti o leggi il documento requisiti in `input/<NomeProgetto>/`, gestisci i token: se il file convertito è grande (molte pagine/sezioni), elaboralo a blocchi, riassumendo via via i requisiti atomici già estratti prima di passare al blocco successivo. Convalida il flusso su file piccoli prima di applicarlo a input di grandi dimensioni.
