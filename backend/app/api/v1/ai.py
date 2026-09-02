from __future__ import annotations

from fastapi import APIRouter

from app.agents.agent import AgentService
from app.core.deps import DbSession, StorageDep
from app.schemas.chat import AnalyzeRequest, ChatRequest, ChatResponse, StoredChatMessage

router = APIRouter(prefix="/ai", tags=["ai"])

EXECUTIVE_SUMMARY_PROMPT = (
    "Give me an executive summary of this dataset: key statistics, important trends, "
    "and any data quality issues I should know about."
)


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, db: DbSession, storage: StorageDep) -> ChatResponse:
    service = AgentService(db, storage)
    result = service.chat(dataset_id=payload.dataset_id, session_id=payload.session_id, user_message=payload.message)
    return ChatResponse(**result)


@router.post("/analyze", response_model=ChatResponse)
async def analyze(payload: AnalyzeRequest, db: DbSession, storage: StorageDep) -> ChatResponse:
    service = AgentService(db, storage)
    result = service.chat(
        dataset_id=payload.dataset_id, session_id=payload.session_id, user_message=EXECUTIVE_SUMMARY_PROMPT
    )
    return ChatResponse(**result)


@router.get("/sessions/{session_id}/messages", response_model=list[StoredChatMessage])
async def get_messages(session_id: str, db: DbSession, storage: StorageDep) -> list[StoredChatMessage]:
    service = AgentService(db, storage)
    messages = service.get_messages(session_id)
    return [StoredChatMessage.model_validate(m) for m in messages]
