from __future__ import annotations

from dataclasses import dataclass
import json
import re

from pydantic import BaseModel, Field, ValidationError
from sqlmodel import Session

from api.services.live_context import get_live_context, save_recovered_live_cards
from core.config import Settings
from core.llm import LlmClient, LlmClientError


SYSTEM_PROMPT = (
    "You extract Slay the Spire card reward options from images. "
    "Return only compact JSON without markdown."
)


class LlmRecoveredCardsPayload(BaseModel):
    offered_cards: list[str] = Field(default_factory=list)


@dataclass
class RecoverLiveCardsResult:
    success: bool
    offered_cards: list[str]
    source: str
    llm_model: str | None
    llm_error: str | None


_NON_IDENTIFIER_CHARS = re.compile(r"[^A-Z0-9_]")


def _normalize_card_id(value: str) -> str | None:
    normalized = value.strip().upper().replace(" ", "_").replace("-", "_")
    if normalized.startswith("CARD."):
        normalized = normalized[5:]
    elif normalized.startswith("CARD_"):
        normalized = normalized[5:]

    normalized = _NON_IDENTIFIER_CHARS.sub("", normalized)
    if not normalized:
        return None
    return f"CARD.{normalized}"


def _coerce_offered_cards(cards: list[str]) -> list[str]:
    deduped: list[str] = []
    for card in cards:
        normalized = _normalize_card_id(card)
        if not normalized:
            continue
        if normalized in deduped:
            continue
        deduped.append(normalized)
        if len(deduped) >= 4:
            break
    return deduped


def _build_prompt(
    *, run_id: str | None, character: str | None, floor: int | None
) -> str:
    envelope = {
        "task": "Extract offered card rewards from screenshot",
        "context": {
            "run_id": run_id,
            "character": character,
            "floor": floor,
        },
        "constraints": [
            "Return only cards currently offered in the reward UI",
            "Use canonical IDs like CARD.BASH",
            "Return max 4 cards",
            "If uncertain, return fewer cards",
        ],
        "output_schema": {
            "offered_cards": ["string"],
        },
    }
    return json.dumps(envelope, ensure_ascii=True, separators=(",", ":"))


def recover_live_cards(
    *, session: Session, settings: Settings, image_base64: str
) -> RecoverLiveCardsResult:
    live_context = get_live_context(session)
    if not live_context.available:
        return RecoverLiveCardsResult(
            success=False,
            offered_cards=[],
            source="live_unavailable",
            llm_model=None,
            llm_error="live_unavailable",
        )

    if live_context.offered_cards:
        return RecoverLiveCardsResult(
            success=True,
            offered_cards=list(live_context.offered_cards),
            source="save",
            llm_model=None,
            llm_error=None,
        )

    if not settings.llm_enabled:
        return RecoverLiveCardsResult(
            success=False,
            offered_cards=[],
            source="llm_vision",
            llm_model=settings.llm_vision_model,
            llm_error="llm_disabled",
        )

    encoded_image = image_base64.strip()
    if not encoded_image:
        return RecoverLiveCardsResult(
            success=False,
            offered_cards=[],
            source="llm_vision",
            llm_model=settings.llm_vision_model,
            llm_error="empty_image",
        )

    prompt = _build_prompt(
        run_id=live_context.run_id,
        character=live_context.character,
        floor=live_context.floor,
    )
    client = LlmClient(
        base_url=settings.llm_base_url,
        model=settings.llm_vision_model,
        timeout_ms=settings.llm_timeout_ms,
    )

    try:
        llm_response = client.complete_json_with_image(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            image_base64=encoded_image,
        )
        payload = LlmRecoveredCardsPayload.model_validate(llm_response.payload)
        offered_cards = _coerce_offered_cards(payload.offered_cards)
        if not offered_cards:
            return RecoverLiveCardsResult(
                success=False,
                offered_cards=[],
                source="llm_vision",
                llm_model=llm_response.model,
                llm_error="no_cards_detected",
            )

        if live_context.run_id is not None:
            save_recovered_live_cards(
                run_id=live_context.run_id,
                floor=live_context.floor,
                offered_cards=offered_cards,
            )

        return RecoverLiveCardsResult(
            success=True,
            offered_cards=offered_cards,
            source="llm_vision",
            llm_model=llm_response.model,
            llm_error=None,
        )
    except (LlmClientError, ValidationError) as exc:
        return RecoverLiveCardsResult(
            success=False,
            offered_cards=[],
            source="llm_vision",
            llm_model=settings.llm_vision_model,
            llm_error=str(exc),
        )
