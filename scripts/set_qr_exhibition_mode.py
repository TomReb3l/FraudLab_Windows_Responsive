import json
from pathlib import Path

path = Path("data/qr_scenarios.json")

data = json.loads(path.read_text(encoding="utf-8"))

allowed = {
    "email_delivery_qr",
    "email_bank_verification_qr",
    "email_invoice_payment_qr",
    "traffic_fine_qr",
}

original = data.get("items", [])

filtered = [
    item for item in original
    if item.get("id") in allowed
]

data["items"] = filtered

path.write_text(
    json.dumps(data, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print(f"Exhibition QR set active: {len(filtered)} scenarios")
print([item["id"] for item in filtered])
