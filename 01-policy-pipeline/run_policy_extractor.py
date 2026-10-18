"""Run the unchanged `policy-extractor` CLI through a Udacity/Vocareum API proxy.

Why this exists: the course proxy (ANTHROPIC_BASE_URL=https://claude.vocareum.com)
rejects the floating alias `claude-haiku-4-5` ("not available for your
organization") but serves the same model under its pinned snapshot ID
`claude-haiku-4-5-20251001`. The reference code hard-codes the alias (and its
tests assert on it), so instead of editing the system under test this launcher
rewrites that one model ID at the SDK call and then hands off to the real CLI.
Every other argument, model, and code path is untouched.

Usage (from the policy-pipeline solution folder, with the .env exported):
    <venv>/Scripts/python run_policy_extractor.py pipeline data/policies/ \
        --routing-out routing_decisions.json --seed 42
"""

from __future__ import annotations

import sys
from typing import Any

from anthropic.resources.messages import Messages

MODEL_ALIASES = {"claude-haiku-4-5": "claude-haiku-4-5-20251001"}

_original_create = Messages.create


def _create_with_pinned_model(self: Messages, *args: Any, **kwargs: Any) -> Any:
    model = kwargs.get("model")
    if model in MODEL_ALIASES:
        kwargs["model"] = MODEL_ALIASES[model]
    return _original_create(self, *args, **kwargs)


Messages.create = _create_with_pinned_model  # type: ignore[method-assign]

from policy_extractor.__main__ import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
