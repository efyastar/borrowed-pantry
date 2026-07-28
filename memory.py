"""Memory layer: users, conversations, messages, and extracted facts."""
import json
import boto3
from db import get_connection

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

CLAUDE_MODEL_ID = "us.anthropic.claude-sonnet-4-6"


def get_or_create_user(email: str, display_name: str) -> str:
    """Return the user's id, creating the user if they don't exist."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email = %s;", (email,))
            row = cur.fetchone()
            if row:
                return str(row[0])
            cur.execute(
                "INSERT INTO users (email, display_name) VALUES (%s, %s) RETURNING id;",
                (email, display_name),
            )
            user_id = str(cur.fetchone()[0])
            conn.commit()
            return user_id


def start_conversation(user_id: str, title: str) -> str:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO conversations (user_id, title) VALUES (%s, %s) RETURNING id;",
                (user_id, title),
            )
            conv_id = str(cur.fetchone()[0])
            conn.commit()
            return conv_id


def save_message(conversation_id: str, role: str, content: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO messages (conversation_id, role, content) VALUES (%s, %s, %s);",
                (conversation_id, role, content),
            )
            conn.commit()


def get_conversation_history(conversation_id: str) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT role, content FROM messages WHERE conversation_id = %s ORDER BY created_at;",
                (conversation_id,),
            )
            return [{"role": role, "content": content} for role, content in cur.fetchall()]


def get_user_facts(user_id: str) -> list[str]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT fact_type, content FROM user_facts WHERE user_id = %s ORDER BY created_at;",
                (user_id,),
            )
            return [f"[{fact_type}] {content}" for fact_type, content in cur.fetchall()]


def save_fact(user_id: str, fact_type: str, content: str, conversation_id: str = None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO user_facts (user_id, fact_type, content, source_conversation)
                   VALUES (%s, %s, %s, %s);""",
                (user_id, fact_type, content, conversation_id),
            )
            conn.commit()


def extract_facts(user_id: str, conversation_id: str, user_msg: str, agent_reply: str):
    """Ask Claude to pull durable facts from the latest exchange and store them."""
    existing = get_user_facts(user_id)
    prompt = (
        "From this exchange between a user and a grocery-planning assistant, extract any DURABLE "
        "facts worth remembering for future sessions: budget preferences, dietary restrictions, "
        "approved or rejected ingredient substitutes, preferred stores, favorite dishes.\n"
        "Only include facts that would still matter next week. Do not repeat already-known facts.\n\n"
        f"Already known facts:\n{chr(10).join(existing) if existing else '(none)'}\n\n"
        f"User said: {user_msg}\n\n"
        f"Assistant replied: {agent_reply}\n\n"
        "Respond with ONLY a JSON array (no prose, no code fences). Each element: "
        '{"fact_type": "budget|dietary|sub_approved|sub_rejected|store_pref|dish_pref|other", '
        '"content": "one short sentence"}. Return [] if nothing new.'
    )
    response = bedrock.invoke_model(
        modelId=CLAUDE_MODEL_ID,
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 500,
            "messages": [{"role": "user", "content": prompt}],
        }),
        contentType="application/json",
        accept="application/json",
    )
    result = json.loads(response["body"].read())
    text = "".join(b["text"] for b in result["content"] if b["type"] == "text").strip()
    text = text.replace("```json", "").replace("```", "").strip()
    try:
        facts = json.loads(text)
    except json.JSONDecodeError:
        return []
    for fact in facts:
        save_fact(user_id, fact["fact_type"], fact["content"], conversation_id)
    return facts


if __name__ == "__main__":
    # Smoke test the memory primitives without involving the full agent
    user_id = get_or_create_user("afia@test.com", "Afia")
    print(f"User id: {user_id}")
    conv_id = start_conversation(user_id, "Test conversation")
    print(f"Conversation id: {conv_id}")
    save_message(conv_id, "user", "I want to cook garden egg stew, my budget is 25 dollars")
    save_message(conv_id, "assistant", "Great choice, here is a plan...")
    history = get_conversation_history(conv_id)
    print(f"History: {len(history)} messages saved and retrieved")
    facts = extract_facts(user_id, conv_id,
                          "I want to cook garden egg stew, my budget is 25 dollars",
                          "Great choice, here is a plan...")
    print(f"Extracted facts: {facts}")
    print(f"All stored facts for user: {get_user_facts(user_id)}")