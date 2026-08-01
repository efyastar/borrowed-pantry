"""The meals agent: plans a shopping trip for a recipe at a chosen store within a budget."""
import json
import boto3
from db import get_connection
from embeddings import get_embedding, vector_to_pg

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

CLAUDE_MODEL_ID = "us.anthropic.claude-sonnet-4-6"

ALLERGY_INGREDIENT_MAP = {
    "shellfish allergy": ["crab", "shrimp", "prawns", "lobster"],
    "nut allergy": ["peanut", "peanuts", "groundnut", "cashew", "almond"],
    "dairy-free": ["milk", "butter", "cheese", "cream", "yogurt"],
    "gluten-free": ["wheat", "flour", "bread", "pasta"],
    "no pork": ["pork", "bacon", "ham"],
    "no beef": ["beef", "beef chuck"],
    "vegetarian": [
        "goat meat", "beef chuck", "crab", "smoked mackerel",
        "dried smoked fish", "koobi (salted tilapia)", "eggs",
    ],
}


def ingredients_triggered_by_allergies(allergies: list[str]) -> set[str]:
    """Expand a list of dietary restriction labels (as stored on the user profile) into
    the actual lowercased ingredient names they should force-substitute."""
    triggered = set()
    for allergy in allergies:
        key = allergy.strip().lower()
        for name in ALLERGY_INGREDIENT_MAP.get(key, []):
            triggered.add(name.lower())
    return triggered

def gather_context(
    recipe_name: str,
    store_name: str,
    already_have: list[str] | None = None,
    extra_ingredients: list[str] | None = None,
    excluded_ingredients: list[str] | None = None,
    allergies: list[str] | None = None,
) -> dict:
    """Collect everything the agent needs to reason: recipe, inventory matches, gaps, substitutes.
    already_have: owned, excluded entirely.
    extra_ingredients: user-added items not in the base recipe, treated as essential.
    excluded_ingredients: user removed these from the base recipe outright.
    allergies: if a recipe ingredient matches an allergy, it is force-treated as missing so a
    substitute gets found automatically, even if the store actually stocks the allergen.
    """
    already_have_lower = {a.strip().lower() for a in (already_have or [])}
    excluded_lower = {a.strip().lower() for a in (excluded_ingredients or [])}
    allergy_triggered_ingredients = ingredients_triggered_by_allergies(allergies or [])

    with get_connection() as conn:
        with conn.cursor() as cur:
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
            skipped_owned = []
            skipped_excluded = []
            flagged_allergy = []
            for _, _, _, ing_id, ing_name, qty, essential in rows:
                name_lower = ing_name.strip().lower()
                if name_lower in already_have_lower:
                    skipped_owned.append(ing_name)
                    continue
                if name_lower in excluded_lower:
                    skipped_excluded.append(ing_name)
                    continue
                is_allergy_flagged = name_lower in allergy_triggered_ingredients
                if is_allergy_flagged:
                    flagged_allergy.append(ing_name)
                recipe["ingredients"].append({
                    "id": str(ing_id),
                    "name": ing_name,
                    "quantity": qty,
                    "essential": essential,
                    "allergy_flagged": is_allergy_flagged,
                })

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

            available, missing = [], []
            for ing in recipe["ingredients"]:
                stock = inventory.get(ing["name"])
                if stock and stock["in_stock"] and not ing["allergy_flagged"]:
                    available.append({**ing, **stock})
                else:
                    cur.execute(
                        """
                        SELECT s2.name, sub.quality_score, sub.notes
                        FROM substitutions sub
                        JOIN ingredients o ON o.id = sub.original_id
                        JOIN ingredients s2 ON s2.id = sub.substitute_id
                        WHERE o.name = %s
                        ORDER BY s2.name;
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

            extra_available, extra_missing = [], []
            if extra_ingredients:
                for extra_name in extra_ingredients:
                    cur.execute(
                        "SELECT id FROM ingredients WHERE lower(name) = lower(%s);",
                        (extra_name.strip(),),
                    )
                    row = cur.fetchone()
                    if not row:
                        continue
                    extra_id = row[0]
                    extra_name_lower = extra_name.strip().lower()
                    extra_allergy_flagged = extra_name_lower in allergy_triggered_ingredients
                    if extra_allergy_flagged:
                        flagged_allergy.append(extra_name)
                    stock = inventory.get(extra_name_lower) or inventory.get(extra_name.strip())
                    if stock and stock["in_stock"] and not extra_allergy_flagged:
                        extra_available.append({
                            "id": str(extra_id), "name": extra_name, "quantity": "as needed",
                            "essential": True, **stock,
                        })
                    else:
                        cur.execute(
                            """
                            SELECT s2.name, sub.quality_score, sub.notes
                            FROM substitutions sub
                            JOIN ingredients o ON o.id = sub.original_id
                            JOIN ingredients s2 ON s2.id = sub.substitute_id
                            WHERE lower(o.name) = lower(%s)
                            ORDER BY s2.name;
                            """,
                            (extra_name.strip(),),
                        )
                        subs = []
                        for sub_name, score, notes in cur.fetchall():
                            sub_stock = inventory.get(sub_name)
                            subs.append({
                                "name": sub_name, "quality_score": score, "notes": notes,
                                "at_this_store": bool(sub_stock and sub_stock["in_stock"]),
                                "price": sub_stock["price"] if sub_stock else None,
                                "unit": sub_stock["unit"] if sub_stock else None,
                            })
                        extra_missing.append({
                            "id": str(extra_id), "name": extra_name, "quantity": "as needed",
                            "essential": True, "substitutes": subs,
                        })

            return {
                "recipe": recipe,
                "store": store_name,
                "already_have": skipped_owned,
                "excluded_by_user": skipped_excluded,
                "allergy_substitutions_applied": list(dict.fromkeys(flagged_allergy)),
                "available_here": available + extra_available,
                "missing_here": missing + extra_missing,
                "other_store_options": other_store_options,
            }


def compute_estimated_basket(context: dict) -> dict:
    """Deterministically compute a suggested basket and total from the gathered context.
    Picks the best in-store substitute for each missing essential ingredient."""
    line_items = []
    total = 0.0
    skipped_optional = []
    unavailable_essentials = []

    for item in context["available_here"]:
        line_items.append({
            "ingredient": item["name"],
            "using": item["name"],
            "price": item["price"],
            "essential": item["essential"],
        })
        total += item["price"]

    for item in context["missing_here"]:
        in_store_subs = [s for s in item["substitutes"] if s["at_this_store"] and s["price"] is not None]
        best_sub = in_store_subs[0] if in_store_subs else None

        if best_sub:
            line_items.append({
                "ingredient": item["name"],
                "using": f"{best_sub['name']} (instead of {item['name']})",
                "reason": best_sub["notes"],
                "price": best_sub["price"],
                "essential": item["essential"],
            })
            total += best_sub["price"]
        elif item["essential"]:
            unavailable_essentials.append(item["name"])
        else:
            skipped_optional.append(item["name"])

    return {
        "line_items": line_items,
        "estimated_total": round(total, 2),
        "unavailable_essentials": unavailable_essentials,
        "skipped_optional_by_default": skipped_optional,
    }


def fit_basket_to_budget(basket: dict, budget: float) -> dict:
    """Deterministically decide what to cut (if anything) to fit the budget.
    Cuts all optional items first if needed; reports honestly if even essentials alone exceed budget."""
    items = basket["line_items"]
    essential_items = [i for i in items if i["essential"]]
    optional_items = [i for i in items if not i["essential"]]

    essential_total = round(sum(i["price"] for i in essential_items), 2)
    full_total = round(sum(i["price"] for i in items), 2)

    if full_total <= budget:
        return {
            "final_items": items,
            "final_total": full_total,
            "removed_optional": [],
            "fits_budget": True,
            "over_by": 0.0,
        }

    if essential_total <= budget:
        return {
            "final_items": essential_items,
            "final_total": essential_total,
            "removed_optional": [{"ingredient": i["ingredient"], "price": i["price"]} for i in optional_items],
            "fits_budget": True,
            "over_by": 0.0,
        }

    return {
        "final_items": essential_items,
        "final_total": essential_total,
        "removed_optional": [{"ingredient": i["ingredient"], "price": i["price"]} for i in optional_items],
        "fits_budget": False,
        "over_by": round(essential_total - budget, 2),
    }


def plan_shopping_trip(recipe_name: str, store_name: str, budget: float) -> str:
    """Gather context from the database, then have Claude reason over it and produce a plan."""
    context = gather_context(recipe_name, store_name)
    basket = compute_estimated_basket(context)
    fitted = fit_basket_to_budget(basket, budget)

    system_prompt = (
        "You are a warm, knowledgeable cooking assistant helping African students abroad "
        "shop for traditional meals. You are given structured data about a recipe, what a "
        "chosen store stocks, what is missing, ranked substitutes, other stores that carry "
        "missing items, and a FINAL basket decision that has already been computed in Python.\n\n"
        "CRITICAL: The final_items, final_total, removed_optional, and over_by fields are EXACT "
        "and FINAL. Do not recompute them, do not do any addition or subtraction yourself, do not "
        "mention any number that is not already given to you. State final_total exactly once, "
        "near the end. If removed_optional is non-empty, mention those items were left out to "
        "stay in budget, but do not restate a running total after each one - there is only ONE "
        "final total.\n\n"
        "Your job:\n"
        "1. Present the final shopping list with prices.\n"
        "2. For substitutes in the list, honestly flag quality tradeoffs (a 2/5 substitute needs "
        "a warning, a 5/5 is easy).\n"
        "3. If fits_budget is false, say so honestly, state over_by, and suggest the specific "
        "other-store options given in the data as alternatives.\n"
        "4. Mention removed_optional items once, briefly.\n"
        "5. End with the final total (already given, stated once) and one short encouraging line.\n"
        "Be concise and practical. Plain text only, no markdown."
    )

    user_message = (
        f"Budget: ${budget:.2f}\n"
        f"Store: {store_name}\n"
        f"Final basket decision (already computed, do not alter):\n"
        f"{json.dumps(fitted, indent=2, default=str)}\n\n"
        f"Full recipe/store/substitute data for context:\n{json.dumps(context, indent=2, default=str)}"
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