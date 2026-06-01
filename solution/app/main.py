import os
import json
import re
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.models import HintRequest, HintResponse, Session, SessionMessage
from app.llm import OllamaClient
from app.prompts import (
    TIER1_SYSTEM,
    TIER2_SYSTEM,
    TIER3_SYSTEM,
    TIER_USER_TEMPLATE,
    SESSION_SYSTEM_PROMPT,
)

load_dotenv()

# We manage the OllamaClient lifecycle using a lifespan context manager.
ollama_client: OllamaClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global ollama_client
    ollama_client = OllamaClient()
    yield
    if ollama_client:
        await ollama_client.close()


app = FastAPI(
    title="DSA Hint Engine API - Solution",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow requests from any origin (local file:// frontend or localhost dev servers)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store
sessions_db: dict[str, list[dict[str, str]]] = {}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _build_user_content(request: HintRequest) -> str:
    """Format the shared user-prompt template with the student's request data."""
    return TIER_USER_TEMPLATE.format(
        difficulty=request.difficulty,
        programming_language=request.programming_language,
        problem_description=request.problem_description,
        code=request.code,
    )


def _strip_markdown_fences(text: str) -> str:
    """Strip markdown code fences (```json ... ```) that small models sometimes wrap around JSON."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


async def _generate_hint(request: HintRequest, system_prompt: str) -> HintResponse:
    """Shared pipeline: build messages, call Ollama, parse JSON, return HintResponse."""
    if not ollama_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ollama client is not initialized.",
        )

    user_content = _build_user_content(request)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    try:
        raw_response = await ollama_client.chat(messages, temperature=0.2, format="json")
        cleaned = _strip_markdown_fences(raw_response)
        parsed_data = json.loads(cleaned)

        return HintResponse(
            thought_process=parsed_data.get("thought_process", "No thought process generated."),
            hint=parsed_data.get("hint", "Try rethinking the problem constraints."),
            conceptual_explanation=parsed_data.get("conceptual_explanation"),
            pseudocode_steps=parsed_data.get("pseudocode_steps"),
        )
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to parse structured JSON response from local LLM.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while generating hint: {str(e)}",
        )


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Simplest health check. Returns 200 to verify the server is alive."""
    return {"status": "ok"}


@app.post("/hint/1", response_model=HintResponse, status_code=status.HTTP_200_OK)
async def hint_tier_1(request: HintRequest):
    """
    Tier 1 — Slight conceptual hint.
    Asks one Socratic guiding question without naming the algorithm.
    """
    return await _generate_hint(request, TIER1_SYSTEM)


@app.post("/hint/2", response_model=HintResponse, status_code=status.HTTP_200_OK)
async def hint_tier_2(request: HintRequest):
    """
    Tier 2 — Approach hint.
    Names the algorithm and explains complexity. No code.
    """
    return await _generate_hint(request, TIER2_SYSTEM)


@app.post("/hint/3", response_model=HintResponse, status_code=status.HTTP_200_OK)
async def hint_tier_3(request: HintRequest):
    """
    Tier 3 — Pseudocode hint.
    Numbered plain-English steps. No runnable code.
    """
    return await _generate_hint(request, TIER3_SYSTEM)


@app.post("/session", response_model=Session, status_code=status.HTTP_201_CREATED)
async def create_or_update_session(session_id: str, message: SessionMessage):
    """
    Stateful endpoint to maintain continuous chat context
     for DSA debugging.
    """
    if not ollama_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ollama client is not initialized.",
        )

    # 1. Initialize session with system prompt if not present.
    if session_id not in sessions_db:
        sessions_db[session_id] = [
            {"role": "system", "content": SESSION_SYSTEM_PROMPT}
        ]

    # 2. Append new user message.
    sessions_db[session_id].append({"role": message.role, "content": message.content})

    try:
        # 3. Generate the assistant response using full conversation history.
        reply_content = await ollama_client.chat(sessions_db[session_id], temperature=0.5)

        # 4. Save the assistant response in session history.
        sessions_db[session_id].append({"role": "assistant", "content": reply_content})

        # 5. Format history (skip system prompt in returned history).
        formatted_history = [
            SessionMessage(role=msg["role"], content=msg["content"])
            for msg in sessions_db[session_id]
            if msg["role"] != "system"
        ]
        return Session(session_id=session_id, history=formatted_history)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred in stateful session: {str(e)}",
        )