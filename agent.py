"""The meals agent: plans a shopping trip for a recipe at a chosen store within a budget."""
import json
import boto3
from db import get_connection
from embeddings import get_embedding, vector_to_pg

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

# We will confirm the exact model ID together before running the Claude step.
CLAUDE_MODEL_ID = "us.anthropic.claude-sonnet-4-6"


def gather_context(recipe_name: str, store_name: str) -> dict:
    """Collect everything the agent needs to reason: recipe, inventory matches, gaps, substitutes."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1. The recipe and its ingredients
            cur.execute(
                """
                SELECT r.id, r.name, r.description, i.id, i.name, ri.quantity, ri.is_essential
                FROM recipes r
                JOIN recipe_ingredients ri ON ri.recipe_id = r.id
                JOIN ingredients i ON i.id = ri.ingredient_id
                WHERE r.name = %s;
                """,
                (recipe_name,),
            )
            rows = cur.fetchall()
            if not rows:
                raise ValueError(f"Recipe not found: {recipe_name}")

            recipe = {"name": rows[0][1], "description": rows[0][2], "ingredients": []}
            for _, _, _, ing_id, ing_name, qty, essential in rows:
                recipe["ingredients"].append({
                    "id": str(ing_id),
                    "name": ing_name,
                    "quantity": qty,
                    "essential": essential,
                })

            # 2. What the chosen store has, for each needed ingredient
            cur.execute(
                """
                SELECT i.name, inv.price, inv.unit, inv.in_stock
                FROM store_inventory inv
                JOIN stores s ON s.id = inv.store_id
                JOIN ingredients i ON i.id = inv.ingredient_id
                WHERE s.name = %s;
                """,
                (store_name,),
            )
            inventory = {name: {"price": float(price), "unit": unit, "in_stock": in_stock}
                         for name, price, unit, in_stock in cur.fetchall()}

            # 3. For each recipe ingredient the store lacks, find substitutes
            available, missing = [], []
            for ing in recipe["ingredients"]:
                stock = inventory.get(ing["name"])
                if stock and stock["in_stock"]:
                    available.append({**ing, **stock})
                else:
                    cur.execute(
                        """
                        SELECT s2.name, sub.quality_score, sub.notes
                        FROM substitutions sub
                        JOIN ingredients o ON o.id = sub.original_id
                        JOIN ingredients s2 ON s2.id = sub.substitute_id
                        WHERE o.name = %s
                        ORDER BY sub.quality_score DESC;
                        """,
                        (ing["name"],),
                    )
                    subs = []
                    for sub_name, score, notes in cur.fetchall():
                        sub_stock = inventory.get(sub_name)
                        subs.append({
                            "name": sub_name,
                            "quality_score": score,
                            "notes": notes,
                            "at_this_store": bool(sub_stock and sub_stock["in_stock"]),
                            "price": sub_stock["price"] if sub_stock else None,
                            "unit": sub_stock["unit"] if sub_stock else None,
                        })
                    missing.append({**ing, "substitutes": subs})

            # 4. Other stores that carry the missing originals (cross-store tip)
            other_store_options = []
            for ing in missing:
                cur.execute(
                    """
                    SELECT s.name, inv.price, inv.unit
                    FROM store_inventory inv
                    JOIN stores s ON s.id = inv.store_id
                    JOIN ingredients i ON i.id = inv.ingredient_id
                    WHERE i.name = %s AND inv.in_stock = true AND s.name != %s;
                    """,
                    (ing["name"], store_name),
                )
                for other_store, price, unit in cur.fetchall():
                    other_store_options.append({
                        "ingredient": ing["name"],
                        "store": other_store,
                        "price": float(price),
                        "unit": unit,
                    })

            return {
                "recipe": recipe,
                "store": store_name,
                "available_here": available,
                "missing_here": missing,
                "other_store_options": other_store_options,
            }


def plan_shopping_trip(recipe_name: str, store_name: str, budget: float) -> str:
    """Gather context from the database, then have Claude reason over it and produce a plan."""
    context = gather_context(recipe_name, store_name)

    system_prompt = (
        "You are a warm, knowledgeable cooking assistant helping African students abroad "
        "shop for traditional meals. You are given structured data about a recipe, what a "
        "chosen store stocks, what is missing, ranked substitutes, and other stores that "
        "carry the missing items. Your job:\n"
        "1. Build a shopping list for the chosen store with prices, staying within budget.\n"
        "2. For missing ingredients, recommend the best available substitute at this store, "
        "honestly noting quality tradeoffs (a 2/5 substitute deserves a warning, a 5/5 is easy).\n"
        "3. If an essential ingredient has no good substitute here, say which other store carries "
        "the real thing and the price difference.\n"
        "4. Non-essential missing ingredients can simply be skipped; say so.\n"
        "5. End with an estimated total and one short encouraging line about the dish.\n"
        "Be concise and practical. Use plain text, no markdown formatting."
    )

    user_message = (
        f"Budget: ${budget:.2f}\n"
        f"Store: {store_name}\n"
        f"Recipe data:\n{json.dumps(context, indent=2, default=str)}"
    )

    response = bedrock.invoke_model(
        modelId=CLAUDE_MODEL_ID,
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1500,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_message}
            ],
        }),
        contentType="application/json",
        accept="application/json",
    )
    result = json.loads(response["body"].read())
    return "".join(block["text"] for block in result["content"] if block["type"] == "text")


if __name__ == "__main__":
    plan = plan_shopping_trip("Garden Egg Stew", "Publix - Riverside", 25.00)
    print(plan)