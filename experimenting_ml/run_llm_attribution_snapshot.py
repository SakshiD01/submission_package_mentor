#!/usr/bin/env python3
"""
Emit AttributionSnapshot JSON for a target (pipeline outputs only — no LLM call).

Usage:
  cd experimenting_ml
  python run_llm_attribution_snapshot.py --target TT_OB_Agri
  python run_llm_attribution_snapshot.py --target TT_OB_Agri --persona analyst_methods \\
      --question "Summarize test error and interval width."
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from llm_attribution import (  # noqa: E402
    assemble_attribution_snapshot,
    build_messages,
    list_persona_ids,
)


def main() -> None:
    p = argparse.ArgumentParser(description="Build fixed-schema attribution JSON for LLM layer")
    p.add_argument("--target", required=True, help="Target column name, e.g. TT_OB_Agri")
    p.add_argument(
        "--outputs-dir",
        type=Path,
        default=ROOT / "outputs",
    )
    p.add_argument("--selected-model", default=None)
    p.add_argument("--shap-top-k", type=int, default=5)
    p.add_argument("--trained-dir", type=Path, default=None)
    p.add_argument(
        "--persona",
        choices=list_persona_ids(),
        default=None,
        help="If set, print OpenAI-style messages JSON (still no API call)",
    )
    p.add_argument(
        "--question",
        default="Explain this target for the persona using only the JSON facts.",
    )
    args = p.parse_args()

    snap = assemble_attribution_snapshot(
        args.target,
        args.outputs_dir,
        selected_model=args.selected_model,
        shap_top_k=args.shap_top_k,
        trained_dir=args.trained_dir,
    )
    if args.persona:
        msgs = build_messages(args.persona, snap, args.question)
        print(json.dumps(msgs, indent=2))
    else:
        print(snap.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
