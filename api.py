"""FastAPI wrapper around the meals agent, for use by a frontend."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from memory import get_or_create_user, start_conversation, save_message, extract_facts
from chat import agent_reply

app = FastAPI(title="Meals Agent API")

# Allow a local React dev server (and later, your deployed frontend) to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this to your real frontend URL before submission
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