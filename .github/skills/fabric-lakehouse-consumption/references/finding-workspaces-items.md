<!-- Estratto e adattato da microsoft/skills-for-fabric common/COMMON-CLI.md
     § "Finding Workspaces and Items in Fabric" — solo la parte necessaria per
     risolvere workspaceId/itemId prima di chiamare execute_query. -->

# Trovare Workspace e Item in Fabric

Prima di chiamare `execute_query` servono il GUID del workspace e il GUID
dell'item (per un Lakehouse: l'id del suo **SQL analytics endpoint**, non
l'id del Lakehouse). Risolvili sempre da nome via `az rest` — mai GUID
inventati o assunti.

**Algoritmo**:

1. Se workspace e item sono noti per nome:
   1. Risolvi prima l'id del workspace (Resolve Workspace Properties by Name)
   2. Poi, con l'id del workspace, risolvi l'id dell'item (Resolve Item
      Properties by Name)
2. Se il workspace non è specificato: usa la Catalog Search API
   (`POST /v1/catalog/search`) — filtrabile per nome, descrizione, workspace
   o tipo (es. `"filter": "Type eq 'Lakehouse'"`). La risposta include sia
   l'`id` dell'item sia `hierarchy.workspace.id`, senza bisogno di una
   seconda chiamata.

> **Disambiguazione**: se la Catalog Search restituisce più corrispondenze,
> presentale all'utente (nome, tipo, workspace) e chiedi conferma su quale
> intende.

## Resolve Workspace Properties by Name

L'API Fabric non ha un endpoint "get workspace by name": serve list+filter.
L'oggetto Workspace espone `displayName`, non `name`.

```bash
WS_NAME="Marketing"
az rest --method get \
  --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/workspaces" \
  --query "value[?displayName=='$WS_NAME'] | [0].id" \
  --output tsv
```

> **Attenzione**: cerca solo nella prima pagina. Per tenant con molti
> workspace potrebbe servire paginazione (non coperta da questo estratto
> minimale — se necessario, consulta la sezione "Pagination Pattern" della
> skill upstream `sqldw-cli`/`COMMON-CLI.md`).

## Resolve Item Properties by Name

### Workspace noto

```bash
ITEM_NAME="SalesLakehouse"
ITEM_TYPE="Lakehouse"
az rest --method get \
  --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/workspaces/$WS_ID/items?type=$ITEM_TYPE" \
  --query "value[?displayName=='$ITEM_NAME'] | [0].id" \
  --output tsv
```

Per un Lakehouse, questo restituisce l'id dell'**item Lakehouse**: serve poi
recuperare separatamente l'id del suo SQL analytics endpoint:

```bash
az rest --method get \
  --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/workspaces/$WS_ID/lakehouses" \
  --query "value[?displayName=='$ITEM_NAME'].properties.sqlEndpointProperties.id" \
  --output tsv
```

### Workspace non noto

```bash
cat > /tmp/body.json << 'EOF'
{"search": "SalesLakehouse", "filter": "Type eq 'Lakehouse'", "pageSize": 30}
EOF
az rest --method post \
  --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/catalog/search" \
  --body @/tmp/body.json
```

La risposta include `id`, `type`, `displayName`, `description` e
`hierarchy.workspace` (con `id` e `displayName`) per ogni match. Nota: item
appena creati possono impiegare fino a 24 ore per comparire nella Catalog
Search.

## Autenticazione

Tutte le chiamate `az rest` richiedono una sessione Azure CLI attiva:

```bash
az login
```

Verifica il tenant selezionato senza stampare credenziali:

```bash
az account show --query tenantId --output tsv
```

L'MCP `execute_query` riusa la stessa sessione `az login` in modo
trasparente — non serve gestire token separati per le query dati.
