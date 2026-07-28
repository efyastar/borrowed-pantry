"""FastAPI wrapper around the meals agent, for use by a frontend."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from db import get_connection
from memory import get_or_create_user, start_conversation, save_message, extract_facts
from chat import agent_reply

app = FastAPI(title="Meals Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    email: str
    name: str
    message: str
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    conversation_id: str
    user_id: str


class ProfileRequest(BaseModel):
    email: str
    name: str
    default_budget: float | None = None
    dietary_restrictions: list[str] = []


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    user_id = get_or_create_user(req.email, req.name)

    conversation_id = req.conversation_id
    if not conversation_id:
        conversation_id = start_conversation(user_id, req.message[:60])

    save_message(conversation_id, "user", req.message)
    reply = agent_reply(user_id, conversation_id, req.message)
    save_message(conversation_id, "assistant", reply)

    extract_facts(user_id, conversation_id, req.message, reply)

    return ChatResponse(reply=reply, conversation_id=conversation_id, user_id=user_id)


@app.get("/profile/{email}")
def get_profile(email: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, email, display_name, default_budget, dietary_restrictions
                   FROM users WHERE email = %s;""",
                (email,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="User not found")
            return {
                "id": str(row[0]),
                "email": row[1],
                "name": row[2],
                "default_budget": float(row[3]) if row[3] is not None else None,
                "dietary_restrictions": row[4] or [],
            }


@app.post("/profile")
def upsert_profile(req: ProfileRequest):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (email, display_name, default_budget, dietary_restrictions)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (email) DO UPDATE SET
                    display_name = EXCLUDED.display_name,
                    default_budget = EXCLUDED.default_budget,
                    dietary_restrictions = EXCLUDED.dietary_restrictions
                RETURNING id;
                """,
                (req.email, req.name, req.default_budget, req.dietary_restrictions),
            )
            user_id = str(cur.fetchone()[0])
            conn.commit()
            return {"user_id": user_id}


@app.get("/stores")
def list_stores():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, chain, address, lat, lng, store_type FROM stores;")
            return [
                {
                    "id": str(r[0]), "name": r[1], "chain": r[2],
                    "address": r[3], "lat": r[4], "lng": r[5], "store_type": r[6],
                }
                for r in cur.fetchall()
            ]


@app.get("/recipes")
def list_recipes():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, cuisine, description, video_url, est_time_minutes FROM recipes;"
            )
            return [
                {
                    "id": str(r[0]), "name": r[1], "cuisine": r[2],
                    "description": r[3], "video_url": r[4], "est_time_minutes": r[5],
                }
                for r in cur.fetchall()
            ]


class CookedRequest(BaseModel):
    user_id: str
    recipe_id: str
    store_name: str | None = None
    notes: str | None = None


@app.post("/cooked")
def log_cooked(req: CookedRequest):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO cooked_history (user_id, recipe_id, store_name, notes)
                   VALUES (%s, %s, %s, %s);""",
                (req.user_id, req.recipe_id, req.store_name, req.notes),
            )
            conn.commit()
    return {"status": "logged"}


@app.get("/cooked/{user_id}")
def get_cooked_history(user_id: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ch.id, r.name, ch.store_name, ch.notes, ch.cooked_at
                FROM cooked_history ch
                JOIN recipes r ON r.id = ch.recipe_id
                WHERE ch.user_id = %s
                ORDER BY ch.cooked_at DESC;
                """,
                (user_id,),
            )
            return [
                {
                    "id": str(r[0]), "recipe_name": r[1], "store_name": r[2],
                    "notes": r[3], "cooked_at": str(r[4]),
                }
                for r in cur.fetchall()
            ]