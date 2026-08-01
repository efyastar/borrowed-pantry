"""One-time update: rewrite substitution notes as full plain-language reasons."""
from db import get_connection

NOTES = [
    ("garden eggs", "thai eggplant",
     "Nearly the same thing: small, round, slightly bitter, and it holds its shape when boiled just like garden eggs. Found at Asian markets."),
    ("garden eggs", "italian eggplant",
     "Bigger and milder, but once boiled and mashed into the stew the texture comes out close. Use about half a large one for a batch."),
    ("kpakpo shito", "habanero pepper",
     "Same family of fruity heat. Habaneros run a bit hotter, so use slightly fewer than the recipe calls for."),
    ("kpakpo shito", "scotch bonnet pepper",
     "Basically interchangeable in a stew: same aroma, same kind of heat. If you find these, grab them."),
    ("scotch bonnet pepper", "habanero pepper",
     "The standard swap. Nearly identical heat and flavor; most people cannot tell the difference in a cooked dish."),
    ("dried smoked fish", "smoked mackerel",
     "Regular grocery smoked mackerel flakes into the stew well. The smoke is lighter than traditional dried fish, but it does the job."),
    ("goat meat", "beef chuck",
     "Slow-cooks to a similar tenderness. The flavor is milder than goat, but the texture in the soup is right."),
    ("palm oil", "vegetable oil",
     "It will cook, but the stew loses its deep red color and signature taste. Only use this if palm oil is truly out of reach."),
]

with get_connection() as conn:
    with conn.cursor() as cur:
        for orig, sub, note in NOTES:
            cur.execute(
                """
                UPDATE substitutions SET notes = %s
                WHERE original_id = (SELECT id FROM ingredients WHERE name = %s)
                  AND substitute_id = (SELECT id FROM ingredients WHERE name = %s);
                """,
                (note, orig, sub),
            )
            conn.commit()
            print(f"  OK: {orig} -> {sub}")