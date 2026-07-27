"""Test semantic search: find ingredients similar to a query phrase."""
from embeddings import get_embedding, vector_to_pg
from db import get_connection


def find_similar_ingredients(query: str, limit: int = 5):
    query_vector = vector_to_pg(get_embedding(query))
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT name, origin_note, embedding <-> %s AS distance
                FROM ingredients
                ORDER BY distance
                LIMIT %s;
                """,
                (query_vector, limit),
            )
            results = cur.fetchall()
            print(f"\nQuery: \"{query}\"")
            for name, note, distance in results:
                print(f"  {distance:.4f}  {name} — {note}")


if __name__ == "__main__":
    find_similar_ingredients("something like garden eggs")
    find_similar_ingredients("a spicy hot pepper")
    find_similar_ingredients("smoky protein for a soup")