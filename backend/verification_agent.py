"""Evidence-grounded AI verifier for public research results.

The API key is intentionally read only on the server. The verifier assesses
search-result claims; it does not identify people from uploaded media.
"""
from __future__ import annotations

import json
import os
from typing import Any

import requests


def _parse_json(text: str) -> dict[str, Any]:
    """Parse model JSON, tolerating a fenced response from older models."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    return json.loads(cleaned)


def verify_results(target: str, results: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return claim assessments and a summary, or None when the agent is off."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key or not results:
        return None

    model = os.getenv("OPENAI_VERIFIER_MODEL", "gpt-5")
    evidence = [
        {"id": index, "title": row.get("title", ""), "url": row.get("url", ""), "detail": row.get("detail", ""), "date": row.get("date", "")}
        for index, row in enumerate(results)
    ]
    prompt = (
        "You are Trinetra's evidence verifier. Assess the supplied public search results "
        "about the target. Do not infer identity or invent facts. A result is supported "
        "only when its title/description directly supports the claim; mark unclear or "
        "conflicting material as unresolved. Return ONLY valid JSON with this shape: "
        '{"summary":"...","items":[{"id":0,"status":"supported|unresolved|contradicted",'
        '"confidence":0.0,"reason":"...","sources":["url"]}]}. '
        "Confidence must be between 0 and 1.\n\nTarget: " + target + "\nResults:\n" + json.dumps(evidence)
    )
    response = requests.post(
        "https://api.openai.com/v1/responses",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "input": prompt, "tools": [{"type": "web_search"}], "store": False},
        timeout=45,
    )
    response.raise_for_status()
    payload = response.json()
    text = payload.get("output_text", "")
    parsed = _parse_json(text)
    if not isinstance(parsed.get("items"), list):
        raise ValueError("Verifier returned no item assessments")
    return parsed
