"""Generate unknown dishes on the fly with Claude, then persist them to CockroachDB."""
import json
import boto3
from db import get_connection
from embeddings import get_embedding, vector_to_pg

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
CLAUDE_MODEL_ID = "us.anthropic.claude-sonnet-4-6"


GENERATION_PROMPT = """You are a knowledgeable African home cook helping build a database of
traditional dishes for students cooking abroad in the United States.

Generate complete, accurate data for this dish: "{dish}"

Respond with ONLY a JSON object, no prose, no code fences, in exactly this shape:

{{
  "name": "canonical dish name",
  "cuisine": "the specific country or region, e.g. Nigerian, Kenyan, Senegalese",
  "description": "two sentences: what it is and what it is served with",
  "est_time_minutes": 60,
  "ingredients": [
    {{
      "name": "lowercase ingredient name",
      "category": "produce|protein|spice|grain|oil|canned|dairy",
      "origin_note": "one short line of cultural or cooking context",
      "quantity": "amount for 4 servings, e.g. '2 cups'",
      "essential": true,
      "at_general_us_store": true,
      "est_price_general": 2.49,
      "at_african_market": true,
      "est_price_african": 3.99,
      "unit": "lb|each|bag|can|dozen"
    }}
  ],
  "substitutions": [
    {{
      "original": "an ingredient name from the list above, exactly as written there",
      "substitute": "short buyable product name, 2 to 4 words",
      "est_price_substitute": 4.99,
      "reason": "plain language: why it works, what changes about the dish, how to prepare it"
    }}
  ]
}}

Rules:
- 6 to 12 ingredients. Mark essential=false only for genuinely optional garnishes or additions.
- Ingredient "name" must be a short, buyable product name only: 2 to 4 words, lowercase,
  no parentheses, no "or", no alternatives, no descriptions. Write "egusi" not
  "ground egusi (melon seeds)". Write "goat meat" not "goat meat or beef".
  Write "spinach" not "fresh or frozen spinach (or bitter leaf)".
- Substitution "substitute" must also be a short buyable product name, 2 to 4 words, lowercase,
  no parentheses, no "or", no instructions. Write "pumpkin seeds" not "raw shelled pumpkin
  seeds ground in a blender". Put all preparation detail in the reason instead.
- If more than one substitute exists for an ingredient, output multiple separate entries in
  the substitutions array rather than combining them into one name.
- Set at_general_us_store=false for items only found at African or international markets.
- If at_general_us_store is false, est_price_general must be null.
- If at_african_market is false, est_price_african must be null.
- Include "est_price_substitute" (a realistic US price number) on every substitution entry.
- Prices should be realistic US retail estimates in dollars.
- Provide a substitution for every ingredient where at_general_us_store is false, if a
  reasonable substitute exists. If a dish truly cannot be made without the real thing
  (like palm nut cream for palmnut soup), do not invent a substitute for it.
- Substitution reasons are full explanations in plain words, including any preparation steps
  and what changes about the dish. Never use ratings or scores.
"""


def generate_recipe_data(dish_name: str) -> dict:
    """Ask Claude for structured data about a dish it has not seen in our database."""
    response = bedrock.invoke_model(
        modelId=CLAUDE_MODEL_ID,
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 8000,
            "messages": [{"role": "user", "content": GENERATION_PROMPT.format(dish=dish_name)}],
        }),
        contentType="application/json",
        accept="application/json",
    )
    result = json.loads(response["body"].read())
    text = "".join(b["text"] for b in result["content"] if b["type"] == "text").strip()
    text = text.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"\nCould not parse the generated JSON: {e}")
        print(f"Response length: {len(text)} characters")
        print(f"Last 200 characters received:\n...{text[-200:]}\n")
        raise


def save_recipe_data(data: dict) -> str:
    """Persist a generated recipe, its ingredients, inventory estimates, and substitutions."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO recipes (name, cuisine, description, est_time_minutes, video_url, is_generated)
                   VALUES (%s, %s, %s, %s, %s, true) RETURNING id;""",
                (
                    data["name"], data.get("cuisine"), data.get("description"),
                    data.get("est_time_minutes"),
                    f"https://www.youtube.com/results?search_query={data['name'].replace(' ', '+')}+recipe",
                ),
            )
            recipe_id = cur.fetchone()[0]
            conn.commit()

            cur.execute("SELECT id, name, store_type FROM stores;")
            stores = cur.fetchall()

            ingredient_ids = {}
            for ing in data["ingredients"]:
                name = ing["name"].strip().lower()
                cur.execute("SELECT id FROM ingredients WHERE lower(name) = %s;", (name,))
                row = cur.fetchone()
                if row:
                    ing_id = row[0]
                else:
                    cur.execute(
                        "INSERT INTO ingredients (name, category, origin_note) VALUES (%s, %s, %s) RETURNING id;",
                        (name, ing.get("category"), ing.get("origin_note")),
                    )
                    ing_id = cur.fetchone()[0]
                    conn.commit()
                ingredient_ids[name] = ing_id

                cur.execute(
                    """INSERT INTO recipe_ingredients (recipe_id, ingredient_id, quantity, is_essential)
                       VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING;""",
                    (recipe_id, ing_id, ing.get("quantity", "as needed"), ing.get("essential", True)),
                )
                conn.commit()

                for store_id, store_name, store_type in stores:
                    if store_type == "african":
                        available = ing.get("at_african_market")
                        price = ing.get("est_price_african")
                    else:
                        available = ing.get("at_general_us_store")
                        price = ing.get("est_price_general")
                    if available and price is not None:
                        cur.execute(
                            """INSERT INTO store_inventory
                                   (store_id, ingredient_id, price, unit, in_stock, is_estimated)
                               VALUES (%s, %s, %s, %s, true, true) ON CONFLICT DO NOTHING;""",
                            (store_id, ing_id, price, ing.get("unit", "each")),
                        )
                        conn.commit()

            for sub in data.get("substitutions", []):
                orig_name = sub["original"].strip().lower()
                sub_name = sub["substitute"].strip().lower()
                sub_price = sub.get("est_price_substitute") or 3.99

                cur.execute("SELECT id FROM ingredients WHERE lower(name) = %s;", (sub_name,))
                row = cur.fetchone()
                if row:
                    sub_id = row[0]
                else:
                    cur.execute(
                        "INSERT INTO ingredients (name, category) VALUES (%s, %s) RETURNING id;",
                        (sub_name, "substitute"),
                    )
                    sub_id = cur.fetchone()[0]
                    conn.commit()
                    for store_id, store_name, store_type in stores:
                        if store_type != "african":
                            cur.execute(
                                """INSERT INTO store_inventory
                                       (store_id, ingredient_id, price, unit, in_stock, is_estimated)
                                   VALUES (%s, %s, %s, %s, true, true) ON CONFLICT DO NOTHING;""",
                                (store_id, sub_id, sub_price, "each"),
                            )
                            conn.commit()

                orig_id = ingredient_ids.get(orig_name)
                if not orig_id:
                    continue
                cur.execute(
                    """INSERT INTO substitutions (original_id, substitute_id, quality_score, notes)
                       VALUES (%s, %s, 3, %s) ON CONFLICT DO NOTHING;""",
                    (orig_id, sub_id, sub["reason"]),
                )
                conn.commit()

            return str(recipe_id)


def embed_new_rows():
    """Fill in embeddings for anything newly created without one."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, origin_note FROM ingredients WHERE embedding IS NULL;")
            for ing_id, name, note in cur.fetchall():
                vec = get_embedding(f"{name}. {note or ''}")
                cur.execute("UPDATE ingredients SET embedding = %s WHERE id = %s;",
                            (vector_to_pg(vec), ing_id))
                conn.commit()

            cur.execute("SELECT id, name, description FROM recipes WHERE embedding IS NULL;")
            for rec_id, name, desc in cur.fetchall():
                vec = get_embedding(f"{name}. {desc or ''}")
                cur.execute("UPDATE recipes SET embedding = %s WHERE id = %s;",
                            (vector_to_pg(vec), rec_id))
                conn.commit()


def ensure_recipe_exists(dish_name: str) -> str | None:
    """Return the canonical recipe name, generating and saving the dish if we do not know it."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT name FROM recipes WHERE lower(name) = lower(%s);", (dish_name.strip(),))
            row = cur.fetchone()
            if row:
                return row[0]

            cur.execute(
                "SELECT name FROM recipes WHERE lower(name) LIKE lower(%s);",
                (f"%{dish_name.strip()}%",),
            )
            row = cur.fetchone()
            if row:
                return row[0]

    data = generate_recipe_data(dish_name)
    save_recipe_data(data)
    embed_new_rows()
    return data["name"]


if __name__ == "__main__":
    import sys
    dish = sys.argv[1] if len(sys.argv) > 1 else "Nigerian Jollof Rice"
    print(f"Looking up: {dish}")
    name = ensure_recipe_exists(dish)
    print(f"Recipe available as: {name}")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT i.name, ri.quantity, ri.is_essential
                   FROM recipe_ingredients ri
                   JOIN recipes r ON r.id = ri.recipe_id
                   JOIN ingredients i ON i.id = ri.ingredient_id
                   WHERE r.name = %s ORDER BY i.name;""",
                (name,),
            )
            for ing_name, qty, essential in cur.fetchall():
                mark = "" if essential else " (optional)"
                print(f"  {ing_name}: {qty}{mark}")