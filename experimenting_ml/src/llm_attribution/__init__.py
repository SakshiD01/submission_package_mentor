"""
LLM attribution layer: fixed-schema snapshots, personas, session store, golden checks.
"""

from llm_attribution.assembler import assemble_attribution_snapshot
from llm_attribution.golden import golden_numeric_fidelity
from llm_attribution.personas import PERSONA_SYSTEM_PROMPTS, get_system_prompt, list_persona_ids
from llm_attribution.prompting import build_messages
from llm_attribution.schema import AttributionSnapshot
from llm_attribution.session_store import FileSessionStore, SessionRecord

__all__ = [
    "assemble_attribution_snapshot",
    "AttributionSnapshot",
    "build_messages",
    "FileSessionStore",
    "SessionRecord",
    "golden_numeric_fidelity",
    "get_system_prompt",
    "list_persona_ids",
    "PERSONA_SYSTEM_PROMPTS",
]
