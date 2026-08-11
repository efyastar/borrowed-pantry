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
    already_have: list[str] = []


class ChatResponse(BaseModel):
    reply: str
    conversation_id: str
    user_id: str

class PlanRequest(BaseModel):
    email: str
    name: str
    recipe: str
    store: str
    budget: float
    already_have: list[str] = []
    extra_ingredients: list[str] = []
    excluded_ingredients: list[str] = []


@app.post("/plan")
def get_plan(req: PlanRequest):
    from agent import gather_context, compute_estimated_basket, fit_basket_to_budget

    user_id = get_or_create_user(req.email, req.name)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT dietary_restrictions FROM users WHERE id = %s;", (user_id,))
            row = cur.fetchone()
            allergies = row[0] if row and row[0] else []

    try:
        context = gather_context(
            req.recipe, req.store,
            already_have=req.already_have,
            extra_ingredients=req.extra_ingredients,
            excluded_ingredients=req.excluded_ingredients,
            allergies=allergies,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    basket = compute_estimated_basket(context)
    fitted = fit_basket_to_budget(basket, req.budget)

    return {
        "recipe": context["recipe"]["name"],
        "store": req.store,
        "already_have": context["already_have"],
        "excluded_by_user": context["excluded_by_user"],
        "allergy_substitutions_applied": context["allergy_substitutions_applied"],
        "final_items": fitted["final_items"],
        "final_total": fitted["final_total"],
        "removed_optional": fitted["removed_optional"],
        "fits_budget": fitted["fits_budget"],
        "over_by": fitted["over_by"],
        "unavailable_essentials": basket["unavailable_essentials"],
        "other_store_options": context["other_store_options"],
    }

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
    reply = agent_reply(user_id, conversation_id, req.message, already_have=req.already_have)
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
            cur.execute(
                """SELECT id, name, chain, address, lat, lng, store_type,
                          on_ubereats, on_doordash FROM stores;"""
            )
            return [
                {
                    "id": str(r[0]), "name": r[1], "chain": r[2],
                    "address": r[3], "lat": r[4], "lng": r[5], "store_type": r[6],
                    "on_ubereats": r[7], "on_doordash": r[8],
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

@app.get("/recipes/{recipe_id}/ingredients")
def get_recipe_ingredients(recipe_id: str):
    """List a recipe's ingredients, used to populate the checklist and review dropdown."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT i.id, i.name
                FROM recipe_ingredients ri
                JOIN ingredients i ON i.id = ri.ingredient_id
                WHERE ri.recipe_id = %s
                ORDER BY i.name;
                """,
                (recipe_id,),
            )
            return [{"id": str(r[0]), "name": r[1]} for r in cur.fetchall()]

class DishRequest(BaseModel):
    dish: str


@app.post("/dish")
def resolve_dish(req: DishRequest):
    """Find a dish by name, generating and saving it if we do not know it yet."""
    from recipe_generator import ensure_recipe_exists

    try:
        canonical_name = ensure_recipe_exists(req.dish)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not work out that dish: {e}")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, name, cuisine, description, video_url, est_time_minutes, is_generated
                   FROM recipes WHERE name = %s;""",
                (canonical_name,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Dish could not be created")
            return {
                "id": str(row[0]), "name": row[1], "cuisine": row[2],
                "description": row[3], "video_url": row[4],
                "est_time_minutes": row[5], "is_generated": row[6],
            }

class CookedRequest(BaseModel):
    user_id: str
    recipe_id: str
    store_name: str | None = None
    notes: str | None = None
    basket: list[dict] = []
    total: float | None = None


@app.post("/cooked")
def log_cooked(req: CookedRequest):
    import json as _json
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO cooked_history (user_id, recipe_id, store_name, notes, basket, total)
                   VALUES (%s, %s, %s, %s, %s, %s);""",
                (
                    req.user_id, req.recipe_id, req.store_name, req.notes,
                    _json.dumps(req.basket), req.total,
                ),
            )
            conn.commit()
    return {"status": "logged"}


@app.get("/cooked/{user_id}")
def get_cooked_history(user_id: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ch.id, r.name, ch.store_name, ch.notes, ch.cooked_at,
                       ch.basket, ch.total, r.video_url, r.cuisine, r.est_time_minutes
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
                    "basket": r[5] or [], "total": float(r[6]) if r[6] is not None else None,
                    "video_url": r[7], "cuisine": r[8], "est_time_minutes": r[9],
                }
                for r in cur.fetchall()
            ]

class ReviewRequest(BaseModel):
    user_id: str
    original_ingredient_id: str
    substitute_name: str
    notes: str
    recipe_id: str | None = None


@app.post("/reviews")
def submit_review(req: ReviewRequest):
    if not req.notes.strip():
        raise HTTPException(status_code=400, detail="Tell us why it works")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO substitution_reviews
                    (original_id, substitute_name, quality_score, notes, user_id, recipe_id)
                VALUES (%s, %s, 3, %s, %s, %s)
                RETURNING id;
                """,
                (
                    req.original_ingredient_id, req.substitute_name,
                    req.notes, req.user_id, req.recipe_id,
                ),
            )
            review_id = str(cur.fetchone()[0])
            conn.commit()
            return {"id": review_id}


@app.get("/community")
def list_community_tips(limit: int = 50):
    """All substitution tips shared by users, newest first."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT sr.id, i.name, sr.substitute_name, sr.notes,
                       u.display_name, r.name, sr.created_at
                FROM substitution_reviews sr
                JOIN ingredients i ON i.id = sr.original_id
                LEFT JOIN users u ON u.id = sr.user_id
                LEFT JOIN recipes r ON r.id = sr.recipe_id
                ORDER BY sr.created_at DESC
                LIMIT %s;
                """,
                (limit,),
            )
            return [
                {
                    "id": str(r[0]), "original": r[1], "substitute": r[2],
                    "notes": r[3], "author": r[4] or "Someone",
                    "recipe_name": r[5], "created_at": str(r[6]),
                }
                for r in cur.fetchall()
            ]


@app.get("/ingredients/search")
def search_ingredients(q: str = "", limit: int = 20):
    """Simple name search, used to pick which ingredient a tip is about."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name FROM ingredients WHERE name ILIKE %s ORDER BY name LIMIT %s;",
                (f"%{q}%", limit),
            )
            return [{"id": str(r[0]), "name": r[1]} for r in cur.fetchall()]


class NearbyRequest(BaseModel):
    lat: float
    lng: float


@app.post("/stores/nearby")
def stores_nearby(req: NearbyRequest):
    """Find and persist real stores near a location, then return everything we know."""
    from store_finder import ensure_stores_near

    try:
        ensure_stores_near(req.lat, req.lng)
    except Exception as e:
        print(f"Store lookup failed, falling back to existing stores: {e}")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, name, chain, address, lat, lng, store_type,
                          on_ubereats, on_doordash FROM stores;"""
            )
            return [
                {
                    "id": str(r[0]), "name": r[1], "chain": r[2],
                    "address": r[3], "lat": r[4], "lng": r[5], "store_type": r[6],
                    "on_ubereats": r[7], "on_doordash": r[8],
                }
                for r in cur.fetchall()
            ]


class EnsureInventoryRequest(BaseModel):
    store_id: str


@app.post("/stores/ensure-inventory")
def ensure_store_inventory(req: EnsureInventoryRequest):
    """Estimate inventory for a store that does not have any yet."""
    from inventory_estimator import ensure_inventory

    try:
        written = ensure_inventory(req.store_id)
        return {"rows_written": written}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not estimate inventory: {e}")

from mangum import Mangum

handler = Mangum(app)

