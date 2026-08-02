"""Drop redundant vector indexes created by repeated db.py runs, keeping one per table."""
from db import get_connection

DROP = [
    "ingredients_embedding_idx1", "ingredients_embedding_idx2", "ingredients_embedding_idx3",
    "ingredients_embedding_idx4", "ingredients_embedding_idx5", "ingredients_embedding_idx6",
    "recipes_embedding_idx1", "recipes_embedding_idx2", "recipes_embedding_idx3",
    "recipes_embedding_idx4", "recipes_embedding_idx5", "recipes_embedding_idx6",
]

TABLE_FOR = {"ingredients": "ingredients", "recipes": "recipes"}

with get_connection() as conn:
    with conn.cursor() as cur:
        for index_name in DROP:
            table = "ingredients" if index_name.startswith("ingredients") else "recipes"
            try:
                cur.execute(f"DROP INDEX {table}@{index_name};")
                conn.commit()
                print(f"  dropped {index_name}")
            except Exception as e:
                conn.rollback()
                print(f"  skipped {index_name}: {e}")