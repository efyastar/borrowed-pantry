"""Estimate what a real store stocks, so newly discovered stores can be planned against."""
import json
import boto3
from db import get_connection

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
CLAUDE_MODEL_ID = "us.anthropic.claude-sonnet-4-6"

PROMPT = """You are estimating grocery inventory for a shopping assistant.

Store: "{store_name}"
Type: {store_type}
Location: {address}

For each ingredient below, say whether this store likely stocks it and a realistic US price.

Ingredients:
{ingredient_list}

Guidance:
- A mainstream US supermarket stocks common produce, meat, and pantry staples, but not
  West African specialty items like egusi, palm nut cream, kpakpo shito, or dried smoked fish.
- A store marked "african" here may be any international, African, Asian, Latin, halal, or
  ethnic market. These stock specialty items a mainstream store would not, and often carry
  common produce too, sometimes cheaper.
- Judge from the store's actual name where you can. A named Asian supermarket is unlikely to
  carry West African specialty items but very likely to carry substitutes like thai eggplant,
  dried shrimp, or pumpkin seeds.

Respond with ONLY a JSON array, no prose, no code fences:
[{{"name": "exact ingredient name from the list", "in_stock": true, "price": 2.49, "unit": "lb"}}]

Include every ingredient. Set in_stock false and price null when the store would not carry it.
"""


def estimate_inventory_for_store(store_id: str, store_name: str, store_type: str, address: str):
    """Estimate and persist inventory for every ingredient we know about, for one store."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM store_inventory WHERE store_id = %s LIMIT 1;", (store_id,))
            if cur.fetchone():
                return 0

            cur.execute("SELECT id, name FROM ingredients ORDER BY name;")
            ingredients = cur.fetchall()

    if not ingredients:
        return 0

    id_by_name = {name.lower(): ing_id for ing_id, name in ingredients}
    listing = "\n".join(f"- {name}" for _, name in ingredients)

    response = bedrock.invoke_model(
        modelId=CLAUDE_MODEL_ID,
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 6000,
            "messages": [{"role": "user", "content": PROMPT.format(
                store_name=store_name, store_type=store_type,
                address=address or "unknown", ingredient_list=listing,
            )}],
        }),
        contentType="application/json",
        accept="application/json",
    )
    result = json.loads(response["body"].read())
    text = "".join(b["text"] for b in result["content"] if b["type"] == "text").strip()
    text = text.replace("```json", "").replace("```", "").strip()

    try:
        rows = json.loads(text)
    except json.JSONDecodeError:
        print(f"Could not parse inventory estimate for {store_name}")
        return 0

    written = 0
    with get_connection() as conn:
        with conn.cursor() as cur:
            for row in rows:
                ing_id = id_by_name.get(str(row.get("name", "")).strip().lower())
                if not ing_id or not row.get("in_stock") or row.get("price") is None:
                    continue
                cur.execute(
                    """INSERT INTO store_inventory
                           (store_id, ingredient_id, price, unit, in_stock, is_estimated)
                       VALUES (%s, %s, %s, %s, true, true) ON CONFLICT DO NOTHING;""",
                    (store_id, ing_id, row["price"], row.get("unit", "each")),
                )
                conn.commit()
                written += 1
    return written


def ensure_inventory(store_id: str) -> int:
    """Estimate inventory for a store if it has none yet."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT name, store_type, address FROM stores WHERE id = %s;", (store_id,)
            )
            row = cur.fetchone()
            if not row:
                return 0
    return estimate_inventory_for_store(store_id, row[0], row[1], row[2])


if __name__ == "__main__":
    import sys
    store_name = sys.argv[1] if len(sys.argv) > 1 else "Uwajimaya"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, store_type, address FROM stores WHERE name = %s;", (store_name,)
            )
            row = cur.fetchone()
    if not row:
        print(f"No store named {store_name}")
    else:
        print(f"Estimating inventory for {row[1]}...")
        n = estimate_inventory_for_store(str(row[0]), row[1], row[2], row[3])
        print(f"Wrote {n} inventory rows.")