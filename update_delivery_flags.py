"""One-time update: set delivery platform availability for seeded stores."""
from db import get_connection

UPDATES = [
    ("Publix - Riverside", False, True),
    ("Walmart Supercenter - Beach Blvd", True, True),
    ("Mama Afrika Market", False, False),
]

with get_connection() as conn:
    with conn.cursor() as cur:
        for name, ubereats, doordash in UPDATES:
            cur.execute(
                "UPDATE stores SET on_ubereats = %s, on_doordash = %s WHERE name = %s;",
                (ubereats, doordash, name),
            )
            conn.commit()
            print(f"  OK: {name} -> UberEats={ubereats}, DoorDash={doordash}")