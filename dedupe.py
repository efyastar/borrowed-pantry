"""Remove duplicate stores and recipes created by re-running seed.py, keeping one of each."""
from db import get_connection

with get_connection() as conn:
    with conn.cursor() as cur:

        # --- RECIPES ---
        cur.execute("""
            SELECT name, array_agg(id ORDER BY id) FROM recipes
            GROUP BY name HAVING count(*) > 1;
        """)
        for name, ids in cur.fetchall():
            keep, drop = ids[0], ids[1:]
            for rid in drop:
                cur.execute("DELETE FROM recipe_ingredients WHERE recipe_id = %s;", (rid,))
                cur.execute("DELETE FROM cooked_history WHERE recipe_id = %s;", (rid,))
                cur.execute("DELETE FROM substitution_reviews WHERE recipe_id = %s;", (rid,))
                cur.execute("DELETE FROM user_favorite_recipes WHERE recipe_id = %s;", (rid,))
                cur.execute("DELETE FROM recipes WHERE id = %s;", (rid,))
            conn.commit()
            print(f"  recipes: kept 1 of {len(ids)} for '{name}'")

        # --- STORES ---
        cur.execute("""
            SELECT name, array_agg(id ORDER BY id) FROM stores
            GROUP BY name HAVING count(*) > 1;
        """)
        for name, ids in cur.fetchall():
            keep, drop = ids[0], ids[1:]
            for sid in drop:
                cur.execute("DELETE FROM store_inventory WHERE store_id = %s;", (sid,))
                cur.execute("DELETE FROM stores WHERE id = %s;", (sid,))
            conn.commit()
            print(f"  stores: kept 1 of {len(ids)} for '{name}'")

        # --- VERIFY ---
        print("\nFinal counts:")
        for t in ['stores', 'recipes', 'ingredients', 'recipe_ingredients',
                  'substitutions', 'store_inventory']:
            cur.execute(f"SELECT count(*) FROM {t};")
            print(f"  {t}: {cur.fetchone()[0]}")