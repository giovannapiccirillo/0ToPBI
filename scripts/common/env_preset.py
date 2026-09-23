# Lettura del preset locale .env (non versionato, vedi .env.example).
# Nessuna dipendenza esterna: parser minimale per righe CHIAVE=valore.
#
# Il preset è solo un default silenzioso: qualunque valore indicato altrove
# (chat, argomenti da riga di comando) prevale sempre su quanto letto qui.
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
ENV_FILE = ROOT / ".env"

_LINE_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$")


def load_env(path: Path = ENV_FILE) -> dict:
    """Legge un file .env in un dict {CHIAVE: valore}. Righe vuote o che
    iniziano con # sono ignorate; valori vuoti non vengono inclusi (una
    chiave presente ma vuota equivale a 'non impostata')."""
    if not path.exists():
        return {}
    values = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        m = _LINE_RE.match(line)
        if not m:
            continue
        key, value = m.group(1), m.group(2)
        if value:
            values[key] = value
    return values


if __name__ == "__main__":
    preset = load_env()
    if not preset:
        print(f"Nessun preset trovato ({ENV_FILE.name} assente o vuoto).")
    else:
        for key, value in preset.items():
            print(f"{key}={value}")
