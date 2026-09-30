"""Minimal deterministic derivation proof registry for V2-1.

Only exact value reuse is supported here. Semantic equivalence rules belong to
later phases and must be registered with their own versioned proof functions.
"""
from __future__ import annotations
from typing import Any


def verify_derivation(rule_id: str, rule_version: str,
                      parent_values: tuple[Any, ...], result: Any) -> bool:
    if (rule_id, rule_version) != ("share-line-item", "1"):
        return False
    return bool(parent_values) and all(value == result for value in parent_values)
