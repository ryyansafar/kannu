"""Start one datasheet-lookup Devin session per part on the builder's tray."""
import json
import sys
from pathlib import Path

from ops.devin_client import DevinClient, load_env

ROOT = Path(__file__).resolve().parent.parent
PARTS = {
    "MPU6050": "GY-521 MPU-6050 accelerometer and gyroscope breakout (I2C)",
    "DHT11": "DHT11 temperature and humidity module (3-pin breakout with pull-up)",
    "LDR": "LDR light sensor module with LM393 comparator (pins VCC GND DO AO)",
    "IR": "IR obstacle avoidance sensor module FC-51 (pins VCC GND OUT)",
    "SSD1306": "0.96 inch OLED display module SSD1306 (I2C)",
    "LCD1602": "16x2 character LCD with I2C backpack (PCF8574)",
    "MQ135": "MQ-135 air quality gas sensor module (pins VCC GND DO AO)",
}


def main(env_path: str) -> None:
    env = load_env(env_path)
    ids = json.loads((ROOT / ".devin_ids.json").read_text())
    schema = json.loads((ROOT / "devin/lookup.schema.json").read_text())
    client = DevinClient(env["DEVIN_TOKEN"], env["DEVIN_ORG"])
    out = {}
    for key, letters in PARTS.items():
        prompt = (f"@playbook:{ids['!kannu-lookup']}\nPART LETTERS: {letters}\n"
                  "Return only the structured JSON. The Raspberry Pi header is 3.3 V logic and not 5 V tolerant, "
                  "so be exact about logic levels and supply voltage.")
        res = client.create_session(prompt, title=f"LOOKUP-{key}", tags=["kannu", "lookup", key.lower()],
                                    max_acu_limit=2, playbook_id=ids["!kannu-lookup"],
                                    structured_output_schema=schema)
        out[key] = {"session_id": res.get("session_id"), "url": res.get("url")}
        print(key, "->", res.get("url"))
    (ROOT / ".lookups.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
