"""One-time setup: create the Devin playbooks and save their ids (never the token)."""
import json
import sys
from pathlib import Path

from ops.devin_client import DevinClient, load_env

ROOT = Path(__file__).resolve().parent.parent
PLAYBOOKS = (
    ("!kannu-lookup", "Kannu lookup (datasheet to JSON)", "devin/lookup.md", "devin/lookup.schema.json"),
)


def main(env_path: str) -> None:
    env = load_env(env_path)
    client = DevinClient(env["DEVIN_TOKEN"], env["DEVIN_ORG"])
    ids_path = ROOT / ".devin_ids.json"
    ids = json.loads(ids_path.read_text()) if ids_path.exists() else {}
    for macro, title, body_file, schema_file in PLAYBOOKS:
        if macro in ids:
            continue
        body = (ROOT / body_file).read_text()
        schema = json.loads((ROOT / schema_file).read_text())
        out = client.create_playbook(title, body, macro, schema)
        ids[macro] = out.get("playbook_id") or out.get("id") or out
        print(macro, "->", ids[macro])
    ids_path.write_text(json.dumps(ids, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
