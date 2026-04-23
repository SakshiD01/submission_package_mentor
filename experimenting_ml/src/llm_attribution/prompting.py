"""
Build chat messages: system (persona) + user (JSON facts + question).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from llm_attribution.personas import get_system_prompt
from llm_attribution.schema import AttributionSnapshot


FACTS_INSTRUCTION = """Below is a JSON object called ATTRIBUTION_FACTS. Answer using ONLY these fields.
Do not add metrics, feature names, or intervals that are not present. If something is missing, say so."""


def build_messages(
    persona_id: str,
    snapshot: AttributionSnapshot,
    user_message: str,
    *,
    prior_turns: Optional[List[Dict[str, str]]] = None,
) -> List[Dict[str, Any]]:
    """OpenAI-style messages: system, [optional multi-turn], user."""
    system = get_system_prompt(persona_id)
    messages: List[Dict[str, Any]] = [{"role": "system", "content": system}]

    if prior_turns:
        for t in prior_turns:
            messages.append({"role": "user", "content": t["user"]})
            messages.append({"role": "assistant", "content": t["assistant"]})

    user_block = (
        f"{FACTS_INSTRUCTION}\n\nATTRIBUTION_FACTS:\n{snapshot.to_llm_json()}\n\nUSER_QUESTION:\n{user_message}"
    )
    messages.append({"role": "user", "content": user_block})
    return messages
