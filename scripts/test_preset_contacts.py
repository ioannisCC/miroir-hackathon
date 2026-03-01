"""Test preset switch + contact filtering end-to-end."""
import sys
sys.path.insert(0, ".")

from backend.core.database import get_db
from backend.services.guidelines import get_guidelines, activate_preset

db = get_db()

def get_contacts_for_preset():
    gl = get_guidelines()
    use_case = gl.get("preset_name", "debt_collection")
    result = db.table("contacts").select("name, email, use_case").eq("use_case", use_case).order("risk_score", desc=True).execute()
    return use_case, result.data

print("=== 1. Current preset (debt_collection) ===")
uc, contacts = get_contacts_for_preset()
print(f"  Active use_case: {uc}")
print(f"  Contacts ({len(contacts)}):")
for c in contacts:
    print(f"    - {c['name']} <{c['email']}> [{c['use_case']}]")

print()
print("=== 2. Switch to RECRUITMENT ===")
activate_preset("recruitment")
uc, contacts = get_contacts_for_preset()
print(f"  Active use_case: {uc}")
print(f"  Contacts ({len(contacts)}):")
for c in contacts:
    print(f"    - {c['name']} <{c['email']}> [{c['use_case']}]")

print()
print("=== 3. Switch BACK to debt_collection ===")
activate_preset("debt_collection")
uc, contacts = get_contacts_for_preset()
print(f"  Active use_case: {uc}")
print(f"  Contacts ({len(contacts)}):")
for c in contacts:
    print(f"    - {c['name']} <{c['email']}> [{c['use_case']}]")

print()
print("DONE")
