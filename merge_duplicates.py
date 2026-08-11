"""Find near-duplicate ingredients and merge them, keeping the row with the most references.
Run with no arguments to preview. Run with --apply to actually merge."""
import sys
from db import get_connection

# Pairs to merge: (keep_this_name, merge_these_into_it)
MERGES = [
    ("habanero pepper", ["habanero peppers"]),
    ("scotch bonnet pepper", ["scotch bonnet peppers"]),
    ("palm oil", ["red palm oil"]),
    ("bouillon cubes", [
        "chicken bouillon cubes", "knorr chicken bouillon cubes",
        "maggi seasoning cubes", "seasoning cubes",
    ]),
    ("tomatoes", ["roma tomatoes"]),
    ("onion", ["yellow onion"]),
]

apply = "--apply" in sys.argv

with get_connection() as conn:
    with conn.cursor() as cur:
        for keep_name, drop_names in MERGES:
            cur.execute("SELECT id FROM ingredients WHERE lower(name) = lower(%s);", (keep_name,))
            keep_row = cur.fetchone()
            if not keep_row:
                print(f"SKIP: no ingredient named '{keep_name}'")
                continue
            keep_id = keep_row[0]

            for drop_name in drop_names:
                cur.execute(
                    "SELECT id FROM ingredients WHERE lower(name) = lower(%s);", (drop_name,)
                )
                drop_row = cur.fetchone()
                if not drop_row:
                    continue
                drop_id = drop_row[0]

                cur.execute(
                    "SELECT count(*) FROM recipe_ingredients WHERE ingredient_id = %s;", (drop_id,)
                )
                recipe_refs = cur.fetchone()[0]
                cur.execute(
                    "SELECT count(*) FROM store_inventory WHERE ingredient_id = %s;", (drop_id,)
                )
                inv_refs = cur.fetchone()[0]

                print(f"MERGE '{drop_name}' -> '{keep_name}' "
                      f"({recipe_refs} recipe refs, {inv_refs} inventory rows)")

                if not apply:
                    continue

                cur.execute(
                    """UPDATE recipe_ingredients SET ingredient_id = %s
                       WHERE ingredient_id = %s
                         AND recipe_id NOT IN (
                           SELECT recipe_id FROM recipe_ingredients WHERE ingredient_id = %s
                         );""",
                    (keep_id, drop_id, keep_id),
                )
                cur.execute("DELETE FROM recipe_ingredients WHERE ingredient_id = %s;", (drop_id,))

                cur.execute(
                    """UPDATE substitutions SET original_id = %s
                       WHERE original_id = %s
                         AND substitute_id NOT IN (
                           SELECT substitute_id FROM substitutions WHERE original_id = %s
                         );""",
                    (keep_id, drop_id, keep_id),
                )
                cur.execute(
                    """UPDATE substitutions SET substitute_id = %s
                       WHERE substitute_id = %s
                         AND original_id NOT IN (
                           SELECT original_id FROM substitutions WHERE substitute_id = %s
                         );""",
                    (keep_id, drop_id, keep_id),
                )
                cur.execute(
                    "DELETE FROM substitutions WHERE original_id = %s OR substitute_id = %s;",
                    (drop_id, drop_id),
                )

                cur.execute(
                    "UPDATE substitution_reviews SET original_id = %s WHERE original_id = %s;",
                    (keep_id, drop_id),
                )

                cur.execute("DELETE FROM store_inventory WHERE ingredient_id = %s;", (drop_id,))
                cur.execute("DELETE FROM ingredients WHERE id = %s;", (drop_id,))
                conn.commit()

        cur.execute("SELECT count(*) FROM ingredients;")
        print(f"\nIngredients now: {cur.fetchone()[0]}")

if not apply:
    print("\nPreview only. Re-run with --apply to perform the merge.")