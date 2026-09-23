# Verifica che esista una sessione `az login` valida prima di usare la skill
# fabric-lakehouse-consumption (risoluzione workspace/item via `az rest`,
# query dati via MCP `execute_query`, che riusa la stessa sessione).
#
# Se la sessione manca o è scaduta, lancia `az login` interattivo: apre il
# browser di default per l'autenticazione Microsoft (nessun token/secret
# gestito da questo script). Non tenta login silenziosi/headless: qui si
# vuole esplicitamente il popup interattivo.
#
# Uso: python scripts/ensure_fabric_login.py
# Exit 0: sessione valida (già presente o appena stabilita).
# Exit 1: login fallito o annullato dall'utente.
import json
import shutil
import subprocess
import sys

# Su Windows `az` è az.cmd: subprocess.run non lo risolve da PATH senza
# passare per la shell (o senza il percorso pieno risolto da shutil.which).
AZ = shutil.which("az") or "az"


def _run(args):
    return subprocess.run(
        args, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )


def get_active_account():
    """Ritorna il dict dell'account attivo se la sessione az è valida, altrimenti None."""
    proc = _run([AZ, "account", "show", "--output", "json"])
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def login_interactive():
    """Lancia `az login` interattivo (apre il browser). Ritorna True se riuscito."""
    proc = subprocess.run([AZ, "login"])
    return proc.returncode == 0


def main():
    account = get_active_account()
    if account is not None:
        user = account.get("user", {}).get("name", "?")
        tenant = account.get("tenantDefaultDomain", account.get("tenantId", "?"))
        print(f"Sessione az attiva: {user} (tenant: {tenant})")
        return 0

    print("Nessuna sessione az valida trovata. Avvio az login (si aprirà il browser)...")
    if not login_interactive():
        print("Login fallito o annullato.", file=sys.stderr)
        return 1

    account = get_active_account()
    if account is None:
        print("Login apparentemente riuscito ma az account show fallisce ancora.", file=sys.stderr)
        return 1

    user = account.get("user", {}).get("name", "?")
    tenant = account.get("tenantDefaultDomain", account.get("tenantId", "?"))
    print(f"Login riuscito: {user} (tenant: {tenant})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
