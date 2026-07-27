"""Generate embeddings for ingredients and recipes using Amazon Titan, store them in CockroachDB."""
import json
import boto3
from db import get_connection

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

MODEL_ID = "amazon.titan-embed-text-v2:0"


def get_embedding(text: str) -> list[float]:
    """Call Titan Embeddings V2 and return a 1024-dim vector for the given text."""
    body = json.dumps({
        "inputText": text,
        "dimensions": 1024,
        "normalize": True,
    })
    response = bedrock.invoke_model(
        modelId=MODEL_ID,
        body=body,
        contentType="application/json",
        accept="application/json",
    )
    result = json.loads(response["body"].read())
    return result["embedding"]


def vector_to_pg(vector: list[float]) -> str:
    """Format a Python float list as a CockroachDB VECTOR literal string."""
    return "[" + ",".join(str(v) for v in vector) + "]"


def embed_ingredients():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, origin_note FROM ingredients WHERE embedding IS NULL;")
            rows = cur.fetchall()
            print(f"Embedding {len(rows)} ingredients...")
            for ing_id, name, note in rows:
                text = f"{name}. {note or ''}"
                vector = get_embedding(text)
                cur.execute(
                    "UPDATE ingredients SET embedding = %s WHERE id = %s;",
                    (vector_to_pg(vector), ing_id),
                )
                conn.commit()
                print(f"  OK: {name}")


def embed_recipes():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, description FROM recipes WHERE embedding IS NULL;")
            rows = cur.fetchall()
            print(f"Embedding {len(rows)} recipes...")
            for rec_id, name, desc in rows:
                text = f"{name}. {desc or ''}"
                vector = get_embedding(text)
                cur.execute(
                    "UPDATE recipes SET embedding = %s WHERE id = %s;",
                    (vector_to_pg(vector), rec_id),
                )
                conn.commit()
                print(f"  OK: {name}")


if __name__ == "__main__":
    embed_ingredients()
    embed_recipes()
    print("Done.")