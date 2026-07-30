"""Interactive chat loop: the full agent with persistent memory."""
import json
import boto3
from db import get_connection
from agent import gather_context, compute_estimated_basket
from memory import (
    get_or_create_user, start_conversation, save_message,
    get_conversation_history, get_user_facts, extract_facts,
)

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

CLAUDE_MODEL_ID = "us.anthropic.claude-sonnet-4-6"


def get_catalog_summary() -> str:
    """Small summary of what recipes and stores exist, so the agent knows its world."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT name FROM recipes;")
            recipes = [r[0] for r in cur.fetchall()]
            cur.execute("SELECT name, store_type FROM stores;")
            stores = [f"{name} ({stype})" for name, stype in cur.fetchall()]
    return f"Known recipes: {', '.join(recipes)}. Known stores: {', '.join(stores)}."


def agent_reply(user_id: str, conversation_id: str, user_msg: str, already_have: list[str] | None = None) -> str:
    """One full agent turn: load memory, decide if recipe planning is needed, respond."""
    facts = get_user_facts(user_id)
    history = get_conversation_history(conversation_id)
    catalog = get_catalog_summary()

    routing_prompt = (
        f"{catalog}\n"
        f"User message: \"{user_msg}\"\n"
        "If this message is asking to plan/shop/cook one of the known recipes at one of the known "
        "stores (or clearly continues such a request), respond with ONLY JSON: "
        '{"needs_planning": true, "recipe": "<exact recipe name>", "store": "<exact store name>"}. '
        "If a store is not specified, use the user's preferred store from these facts if any: "
        f"{'; '.join(facts) if facts else '(none)'}. "
        "If no store can be determined, or the message does not need recipe planning, respond with "
        'ONLY JSON: {"needs_planning": false}.'
    )
    routing_response = bedrock.invoke_model(
        modelId=CLAUDE_MODEL_ID,
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 200,
            "messages": [{"role": "user", "content": routing_prompt}],
        }),
        contentType="application/json",
        accept="application/json",
    )
    routing_text = "".join(
        b["text"] for b in json.loads(routing_response["body"].read())["content"]
        if b["type"] == "text"
    ).strip().replace("```json", "").replace("```", "").strip()
    try:
        routing = json.loads(routing_text)
    except json.JSONDecodeError:
        routing = {"needs_planning": False}

    system_prompt = (
        "You are a warm, knowledgeable cooking assistant helping African students abroad shop for "
        "and cook traditional meals on a budget. Be concise and practical. Plain text only, no markdown.\n\n"
        f"{catalog}\n\n"
        "Facts you remember about this user from past sessions:\n"
        + ("\n".join(facts) if facts else "(none yet)")
    )

    context_block = ""
    if routing.get("needs_planning") and routing.get("recipe") and routing.get("store"):
        try:
            from agent import compute_estimated_basket, fit_basket_to_budget
            budget = 25.00
            for f in facts:
                if "budget" in f.lower():
                    import re
                    match = re.search(r"\$?(\d+(?:\.\d+)?)", f)
                    if match:
                        budget = float(match.group(1))
                        break

            context = gather_context(routing["recipe"], routing["store"], already_have=already_have)
            basket = compute_estimated_basket(context)
            fitted = fit_basket_to_budget(basket, budget)
            context_block = (
                f"\n\n[A FINAL basket decision has already been computed in Python using an "
                f"assumed budget of ${budget:.2f} based on remembered facts. The final_items, "
                f"final_total, removed_optional, and over_by fields are EXACT and FINAL. Do not "
                f"recompute or do any arithmetic yourself. State final_total exactly once.]\n"
                f"Final basket decision:\n{json.dumps(fitted, indent=2, default=str)}\n\n"
                f"Full recipe/store/substitute data:\n{json.dumps(context, indent=2, default=str)}"
            )
        except ValueError as e:
            context_block = f"\n\n[Note: {e}]"

    messages = history + [{"role": "user", "content": user_msg + context_block}]

    response = bedrock.invoke_model(
        modelId=CLAUDE_MODEL_ID,
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1500,
            "system": system_prompt,
            "messages": messages,
        }),
        contentType="application/json",
        accept="application/json",
    )
    result = json.loads(response["body"].read())
    return "".join(b["text"] for b in result["content"] if b["type"] == "text")


def main():
    print("Meals Agent (type 'quit' to exit)")
    email = input("Your email: ").strip()
    name = input("Your name: ").strip()
    user_id = get_or_create_user(email, name)

    facts = get_user_facts(user_id)
    if facts:
        print(f"\nWelcome back, {name}. I remember {len(facts)} things about you.")
    else:
        print(f"\nNice to meet you, {name}.")

    conversation_id = start_conversation(user_id, "Chat session")

    while True:
        user_msg = input("\nYou: ").strip()
        if user_msg.lower() in ("quit", "exit"):
            print("Bye! I'll remember our conversation.")
            break
        if not user_msg:
            continue

        save_message(conversation_id, "user", user_msg)
        reply = agent_reply(user_id, conversation_id, user_msg)
        save_message(conversation_id, "assistant", reply)
        print(f"\nAgent: {reply}")

        extract_facts(user_id, conversation_id, user_msg, reply)


if __name__ == "__main__":
    main()