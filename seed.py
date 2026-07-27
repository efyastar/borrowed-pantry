"""Seed data for the meals agent database."""
from db import get_connection


def run_seed():
    with get_connection() as conn:
        with conn.cursor() as cur:

            print("Seeding stores...")
            cur.execute("""
                INSERT INTO stores (name, chain, address, lat, lng, store_type) VALUES
                ('Publix - Riverside', 'Publix', '2033 Riverside Ave, Jacksonville, FL', 30.3164, -81.6821, 'general'),
                ('Walmart Supercenter - Beach Blvd', 'Walmart', '6767 103rd St, Jacksonville, FL', 30.2683, -81.7519, 'general'),
                ('Mama Afrika Market', NULL, '5290 Norwood Ave, Jacksonville, FL', 30.3776, -81.6702, 'african')
                ON CONFLICT DO NOTHING;
            """)
            conn.commit()
            print("  OK")

            print("Seeding ingredients...")
            cur.execute("""
                INSERT INTO ingredients (name, category, origin_note) VALUES
                ('garden eggs', 'produce', 'Small white/green African eggplant; mildly bitter; core of garden egg stew'),
                ('italian eggplant', 'produce', 'Large purple eggplant; common US substitute for garden eggs'),
                ('thai eggplant', 'produce', 'Small round green eggplant; closest US-available match to garden eggs'),
                ('palm nut cream concentrate', 'canned', 'Canned palm fruit extract; the base of abenkwan; no true substitute'),
                ('tomatoes', 'produce', 'Fresh; base of most Ghanaian stews'),
                ('onion', 'produce', 'Stew base'),
                ('fresh ginger', 'produce', 'Blended into stew base'),
                ('garlic', 'produce', 'Blended into stew base'),
                ('kpakpo shito', 'produce', 'Green Ghanaian bird pepper; aromatic heat'),
                ('habanero pepper', 'produce', 'Widely available; substitute for kpakpo shito or scotch bonnet'),
                ('scotch bonnet pepper', 'produce', 'Traditional pepper for Ghanaian soups and stews'),
                ('palm oil', 'oil', 'Red palm oil; signature color and flavor of garden egg stew'),
                ('vegetable oil', 'oil', 'Neutral substitute where palm oil unavailable, loses character'),
                ('smoked mackerel', 'protein', 'US-available smoked fish; substitute for Ghanaian smoked fish'),
                ('dried smoked fish', 'protein', 'Traditional; found at African markets'),
                ('koobi (salted tilapia)', 'protein', 'Salted dried tilapia; deep umami; African markets only'),
                ('turkey berries', 'produce', 'Kwahu nsusua; small bitter berries for palmnut soup'),
                ('goat meat', 'protein', 'Common protein for palmnut soup'),
                ('beef chuck', 'protein', 'Widely available protein substitute'),
                ('crab', 'protein', 'Traditional addition to palmnut soup'),
                ('eggs', 'protein', 'Boiled eggs often added to garden egg stew')
                ON CONFLICT DO NOTHING;
            """)
            conn.commit()
            print("  OK")

            print("Seeding recipes...")
            cur.execute("""
                INSERT INTO recipes (name, cuisine, description, video_url, est_time_minutes) VALUES
                ('Garden Egg Stew', 'Ghanaian',
                 'Silky stew of boiled garden eggs mashed into a palm-oil tomato base with smoked fish. Eaten with boiled yam, plantain, or rice.',
                 'https://www.youtube.com/results?search_query=ghanaian+garden+egg+stew', 50),
                ('Palmnut Soup (Abenkwan)', 'Ghanaian',
                 'Rich soup from palm nut cream simmered with meat, smoked fish, and peppers. Traditionally served with fufu or omo tuo.',
                 'https://www.youtube.com/results?search_query=ghanaian+palmnut+soup+abenkwan', 90)
                ON CONFLICT DO NOTHING;
            """)
            conn.commit()
            print("  OK")

            print("Seeding recipe_ingredients...")
            cur.execute("""
                INSERT INTO recipe_ingredients (recipe_id, ingredient_id, quantity, is_essential)
                SELECT r.id, i.id, x.qty, x.ess FROM (VALUES
                  ('Garden Egg Stew', 'garden eggs', '6-8 medium', true),
                  ('Garden Egg Stew', 'tomatoes', '4 medium', true),
                  ('Garden Egg Stew', 'onion', '2 medium', true),
                  ('Garden Egg Stew', 'fresh ginger', '1 inch piece', true),
                  ('Garden Egg Stew', 'garlic', '3 cloves', false),
                  ('Garden Egg Stew', 'kpakpo shito', '3-4 peppers', true),
                  ('Garden Egg Stew', 'palm oil', '1/3 cup', true),
                  ('Garden Egg Stew', 'dried smoked fish', '1 cup flaked', true),
                  ('Garden Egg Stew', 'eggs', '2-3 boiled', false),
                  ('Palmnut Soup (Abenkwan)', 'palm nut cream concentrate', '1 can (800g)', true),
                  ('Palmnut Soup (Abenkwan)', 'goat meat', '1.5 lb', true),
                  ('Palmnut Soup (Abenkwan)', 'tomatoes', '2 medium', true),
                  ('Palmnut Soup (Abenkwan)', 'onion', '1 large', true),
                  ('Palmnut Soup (Abenkwan)', 'fresh ginger', '1 inch piece', true),
                  ('Palmnut Soup (Abenkwan)', 'scotch bonnet pepper', '1-2 peppers', true),
                  ('Palmnut Soup (Abenkwan)', 'dried smoked fish', '1 cup', true),
                  ('Palmnut Soup (Abenkwan)', 'turkey berries', '1/2 cup', false),
                  ('Palmnut Soup (Abenkwan)', 'crab', '2 whole', false)
                ) AS x(recipe, ing, qty, ess)
                JOIN recipes r ON r.name = x.recipe
                JOIN ingredients i ON i.name = x.ing
                ON CONFLICT DO NOTHING;
            """)
            conn.commit()
            print("  OK")

            print("Seeding substitutions...")
            cur.execute("""
                INSERT INTO substitutions (original_id, substitute_id, quality_score, notes)
                SELECT o.id, s.id, x.score, x.note FROM (VALUES
                  ('garden eggs', 'thai eggplant', 5, 'Closest match: size, slight bitterness, holds shape when boiled. Asian markets.'),
                  ('garden eggs', 'italian eggplant', 4, 'Works well mashed into stew; milder, softer. Available everywhere.'),
                  ('kpakpo shito', 'habanero pepper', 4, 'Similar heat and fruitiness; use slightly less.'),
                  ('kpakpo shito', 'scotch bonnet pepper', 5, 'Nearly interchangeable in stews.'),
                  ('scotch bonnet pepper', 'habanero pepper', 5, 'Standard swap; nearly identical heat profile.'),
                  ('dried smoked fish', 'smoked mackerel', 4, 'Grocery-store smoked mackerel flakes in well; less intense.'),
                  ('goat meat', 'beef chuck', 4, 'Similar slow-cook texture; milder flavor.'),
                  ('palm oil', 'vegetable oil', 2, 'Stew will cook but loses signature color and taste. Get palm oil if possible.')
                ) AS x(orig, sub, score, note)
                JOIN ingredients o ON o.name = x.orig
                JOIN ingredients s ON s.name = x.sub
                ON CONFLICT DO NOTHING;
            """)
            conn.commit()
            print("  OK")

            print("Seeding store_inventory...")
            cur.execute("""
                INSERT INTO store_inventory (store_id, ingredient_id, price, unit, in_stock)
                SELECT st.id, i.id, x.price, x.unit, x.stock FROM (VALUES
                  ('Publix - Riverside', 'italian eggplant', 2.49, 'each', true),
                  ('Publix - Riverside', 'tomatoes', 1.99, 'lb', true),
                  ('Publix - Riverside', 'onion', 1.29, 'lb', true),
                  ('Publix - Riverside', 'fresh ginger', 3.99, 'lb', true),
                  ('Publix - Riverside', 'garlic', 0.79, 'head', true),
                  ('Publix - Riverside', 'habanero pepper', 4.99, 'lb', true),
                  ('Publix - Riverside', 'vegetable oil', 4.49, '48oz', true),
                  ('Publix - Riverside', 'smoked mackerel', 6.99, '8oz', true),
                  ('Publix - Riverside', 'beef chuck', 7.99, 'lb', true),
                  ('Publix - Riverside', 'eggs', 3.49, 'dozen', true),
                  ('Walmart Supercenter - Beach Blvd', 'italian eggplant', 1.98, 'each', true),
                  ('Walmart Supercenter - Beach Blvd', 'tomatoes', 1.48, 'lb', true),
                  ('Walmart Supercenter - Beach Blvd', 'onion', 0.98, 'lb', true),
                  ('Walmart Supercenter - Beach Blvd', 'fresh ginger', 2.98, 'lb', true),
                  ('Walmart Supercenter - Beach Blvd', 'habanero pepper', 3.98, 'lb', true),
                  ('Walmart Supercenter - Beach Blvd', 'palm oil', 8.99, '16oz', true),
                  ('Walmart Supercenter - Beach Blvd', 'beef chuck', 6.44, 'lb', true),
                  ('Walmart Supercenter - Beach Blvd', 'eggs', 2.98, 'dozen', true),
                  ('Mama Afrika Market', 'garden eggs', 5.99, 'lb', true),
                  ('Mama Afrika Market', 'palm nut cream concentrate', 7.49, '800g can', true),
                  ('Mama Afrika Market', 'palm oil', 6.99, '16oz', true),
                  ('Mama Afrika Market', 'kpakpo shito', 4.50, 'bag', true),
                  ('Mama Afrika Market', 'dried smoked fish', 9.99, 'pack', true),
                  ('Mama Afrika Market', 'koobi (salted tilapia)', 8.99, 'each', true),
                  ('Mama Afrika Market', 'scotch bonnet pepper', 3.99, 'bag', true),
                  ('Mama Afrika Market', 'turkey berries', 6.99, 'pack', false),
                  ('Mama Afrika Market', 'goat meat', 9.99, 'lb', true),
                  ('Mama Afrika Market', 'crab', 7.99, 'lb', true)
                ) AS x(store, ing, price, unit, stock)
                JOIN stores st ON st.name = x.store
                JOIN ingredients i ON i.name = x.ing
                ON CONFLICT DO NOTHING;
            """)
            conn.commit()
            print("  OK")


def verify():
    with get_connection() as conn:
        with conn.cursor() as cur:
            for table in ["stores", "ingredients", "recipes", "recipe_ingredients", "substitutions", "store_inventory"]:
                cur.execute(f"SELECT count(*) FROM {table};")
                print(f"  {table}: {cur.fetchone()[0]} rows")


if __name__ == "__main__":
    run_seed()
    print("\nVerifying row counts...")
    verify()