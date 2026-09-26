"""LLM fallback for annual-report sections (hybrid mode).

Only invoked when rule-based extraction is low-confidence or sections are missing.
OpenAI-compatible chat completions via `openai` package (lazy import).
Primary provider: Groq (GROQ_API_KEY + https://api.groq.com/openai/v1).
Also supports OpenAI / any OpenAI-compatible endpoint via env overrides.
Strict JSON schema; confidence field gates auto-apply vs review_queue.
"""
from __future__ import annotations

import json
import os
import re
from typing import Optional

from app.ingest.normalize import RawBrand, RawPayload

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
# Fast, strong JSON extractor on Groq free tier
LLM_MODEL_DEFAULT = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You extract structured competitive-intelligence facts from annual-report text.
Return ONLY a JSON object (no markdown fences) with this schema:
{
  "description": string | null,          // 2-4 sentence company overview
  "brands": string[],                    // brand/product-line names only
  "regions": string[],                   // Indian states/regions of presence
  "parent_company": string | null,
  "is_listed": boolean | null,
  "facts": string[],                     // notable numeric/segment facts (short)
  "confidence": "high" | "medium" | "low"
}
Rules:
- Only extract facts explicitly supported by the text. Do not invent brands.
- regions: use full state names (e.g. "Gujarat", "Tamil Nadu").
- If a field is absent in text, use null or empty array.
- confidence: high if brands+regions clearly present; low if sparse/ambiguous.
"""


def _api_key() -> Optional[str]:
    return (
        os.environ.get("GROQ_API_KEY")
        or os.environ.get("INGEST_LLM_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or None
    )


def _base_url() -> str:
    return (
        os.environ.get("INGEST_LLM_BASE_URL")
        or os.environ.get("OPENAI_BASE_URL")
        or GROQ_BASE_URL
    )


def _model() -> str:
    return os.environ.get("INGEST_LLM_MODEL", LLM_MODEL_DEFAULT)


def llm_enabled() -> bool:
    if os.environ.get("INGEST_LLM_ENABLED", "").lower() in ("0", "false", "no"):
        return False
    return bool(_api_key())


def provider_name() -> str:
    if os.environ.get("GROQ_API_KEY"):
        return "groq"
    if os.environ.get("OPENAI_API_KEY") and not os.environ.get("GROQ_API_KEY"):
        return "openai"
    return "custom"


def _client():
    from openai import OpenAI  # lazy — optional dependency (works with Groq base_url)
    return OpenAI(api_key=_api_key(), base_url=_base_url())


def _parse_json(raw: str) -> Optional[dict]:
    raw = raw.strip()
    # Strip markdown fences if present
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        # Try to find first {...}
        m = re.search(r"\{.*\}", raw, re.S)
        if m:
            try:
                obj = json.loads(m.group(0))
                return obj if isinstance(obj, dict) else None
            except json.JSONDecodeError:
                return None
    return None


def extract_with_llm(text: str, company_name: str, source_url: str,
                     company_slug: str, max_chars: int = 12000) -> Optional[RawPayload]:
    """Ask LLM to extract structured facts from report text. Returns RawPayload or None."""
    if not llm_enabled():
        return None
    chunk = text[:max_chars]
    user = f"Company: {company_name}\nSource: {source_url}\n\nAnnual report excerpt:\n{chunk}"
    try:
        client = _client()
        resp = client.chat.completions.create(
            model=_model(),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user},
            ],
            temperature=0,
            response_format={"type": "json_object"},
            max_tokens=2048,
        )
        content = resp.choices[0].message.content or ""
    except Exception:
        # Some Groq models reject response_format; retry without it once.
        try:
            client = _client()
            resp = client.chat.completions.create(
                model=_model(),
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user},
                ],
                temperature=0,
                max_tokens=2048,
            )
            content = resp.choices[0].message.content or ""
        except Exception:
            return None

    data = _parse_json(content)
    if not data:
        return None

    conf = str(data.get("confidence") or "medium").lower()
    if conf not in ("high", "medium", "low"):
        conf = "medium"

    payload = RawPayload(
        company_slug=company_slug,
        source_type="annual_report",
        source_url=source_url,
        confidence=conf,
        description=(data.get("description") or None),
        parent_company=(data.get("parent_company") or None),
        is_listed=data.get("is_listed") if isinstance(data.get("is_listed"), bool) else None,
    )
    brands = data.get("brands") or []
    if isinstance(brands, list):
        for b in brands:
            if isinstance(b, str) and b.strip():
                payload.brands.append(RawBrand(name=b.strip()[:120], source_url=source_url))
    regions = data.get("regions") or []
    if isinstance(regions, list):
        payload.regions = [r.strip() for r in regions if isinstance(r, str) and r.strip()][:30]
    facts = data.get("facts") or []
    if isinstance(facts, list):
        payload.facts = [f.strip()[:300] for f in facts if isinstance(f, str) and f.strip()][:20]

    if not payload.brands and not payload.regions and not payload.description:
        return None
    return payload


def merge_payloads(rule_payload: RawPayload, llm_payload: RawPayload) -> RawPayload:
    """Merge rule + LLM results: rules win for overlap; LLM fills gaps. Best confidence kept."""
    merged = rule_payload
    # description
    if not merged.description and llm_payload.description:
        merged.description = llm_payload.description
    # brands union (case-insensitive)
    seen = {b.name.lower() for b in merged.brands}
    for b in llm_payload.brands:
        if b.name.lower() not in seen:
            merged.brands.append(b)
            seen.add(b.name.lower())
    # regions union
    rseen = {r.lower() for r in merged.regions}
    for r in llm_payload.regions:
        if r.lower() not in rseen:
            merged.regions.append(r)
            rseen.add(r.lower())
    # facts
    merged.facts.extend(llm_payload.facts)
    # confidence: higher of the two (rank)
    rank = {"low": 0, "medium": 1, "high": 2}
    if rank.get(llm_payload.confidence, 1) > rank.get(merged.confidence, 1):
        merged.confidence = llm_payload.confidence
    if llm_payload.parent_company and not merged.parent_company:
        merged.parent_company = llm_payload.parent_company
    if llm_payload.is_listed is not None and merged.is_listed is None:
        merged.is_listed = llm_payload.is_listed
    return merged
