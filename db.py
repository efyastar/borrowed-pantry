"""Database connection and schema setup for the meals agent."""
import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]


def get_connection():
    return psycopg.connect(DATABASE_URL)


SCHEMA_STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS users (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        email STRING UNIQUE NOT NULL,
        display_name STRING,
        default_budget DECIMAL(8,2),
        dietary_restrictions STRING[],
        created_at TIMESTAMPTZ DEFAULT now()
    );""",
    """CREATE TABLE IF NOT EXISTS stores (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name STRING NOT NULL,
        chain STRING,
        address STRING,
        lat FLOAT8,
        lng FLOAT8,
        store_type STRING DEFAULT 'general'
    );""",
    """CREATE TABLE IF NOT EXISTS ingredients (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name STRING UNIQUE NOT NULL,
        category STRING,
        origin_note STRING,
        embedding VECTOR(1024)
    );""",
    """CREATE TABLE IF NOT EXISTS store_inventory (
        store_id UUID REFERENCES stores(id),
        ingredient_id UUID REFERENCES ingredients(id),
        price DECIMAL(8,2) NOT NULL,
        unit STRING NOT NULL,
        in_stock BOOL DEFAULT true,
        PRIMARY KEY (store_id, ingredient_id)
    );""",
    """CREATE TABLE IF NOT EXISTS recipes (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name STRING NOT NULL,
        cuisine STRING,
        description STRING,
        video_url STRING,
        est_time_minutes INT,
        embedding VECTOR(1024)
    );""",
    """CREATE TABLE IF NOT EXISTS recipe_ingredients (
        recipe_id UUID REFERENCES recipes(id),
        ingredient_id UUID REFERENCES ingredients(id),
        quantity STRING NOT NULL,
        is_essential BOOL DEFAULT true,
        PRIMARY KEY (recipe_id, ingredient_id)
    );""",
    """CREATE TABLE IF NOT EXISTS substitutions (
        original_id UUID REFERENCES ingredients(id),
        substitute_id UUID REFERENCES ingredients(id),
        quality_score INT CHECK (quality_score BETWEEN 1 AND 5),
        notes STRING,
        PRIMARY KEY (original_id, substitute_id)
    );""",
    """CREATE TABLE IF NOT EXISTS conversations (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID REFERENCES users(id),
        title STRING,
        created_at TIMESTAMPTZ DEFAULT now()
    );""",
    """CREATE TABLE IF NOT EXISTS messages (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        conversation_id UUID REFERENCES conversations(id),
        role STRING NOT NULL,
        content STRING NOT NULL,
        created_at TIMESTAMPTZ DEFAULT now()
    );""",
    """CREATE TABLE IF NOT EXISTS user_facts (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID REFERENCES users(id),
        fact_type STRING NOT NULL,
        content STRING NOT NULL,
        source_conversation UUID REFERENCES conversations(id),
        created_at TIMESTAMPTZ DEFAULT now()
    );""",
    """CREATE TABLE IF NOT EXISTS cooked_history (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID REFERENCES users(id),
        recipe_id UUID REFERENCES recipes(id),
        store_name STRING,
        notes STRING,
        cooked_at TIMESTAMPTZ DEFAULT now()
    );""",
]

VECTOR_INDEX_STATEMENTS = [
    "CREATE VECTOR INDEX ON ingredients (embedding);",
    "CREATE VECTOR INDEX ON recipes (embedding);",
]


def run_schema():
    total = len(SCHEMA_STATEMENTS)
    with get_connection() as conn:
        with conn.cursor() as cur:
            for i, stmt in enumerate(SCHEMA_STATEMENTS, 1):
                table_name = stmt.split("EXISTS ")[1].split(" ")[0]
                try:
                    cur.execute(stmt)
                    conn.commit()
                    print(f"  [{i}/{total}] OK: {table_name}")
                except Exception as e:
                    print(f"  [{i}/{total}] FAIL: {table_name}: {e}")
                    conn.rollback()

            for stmt in VECTOR_INDEX_STATEMENTS:
                try:
                    cur.execute(stmt)
                    conn.commit()
                    print(f"  OK: vector index: {stmt[:50]}...")
                except Exception as e:
                    # Already exists is fine on re-run
                    print(f"  SKIP/FAIL: vector index: {e}")
                    conn.rollback()


if __name__ == "__main__":
    run_schema()
    print("\nSchema setup complete. Verifying...")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' ORDER BY table_name;
            """)
            tables = [r[0] for r in cur.fetchall()]
            print(f"Tables in database: {tables}")
            print(f"Total: {len(tables)}/{len(SCHEMA_STATEMENTS)}")