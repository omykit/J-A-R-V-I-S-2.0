"""AI response cleaning and text processing utilities."""
from __future__ import annotations

import re

RESPONSE_RULE_SUFFIX = (
    "Reply with only the final spoken answer. "
    "Never include analysis or reasoning."
)


def extract_quoted_candidate(text: str) -> str:
    matches = re.findall(r'"([^\\"]{2,80})"', text)
    for candidate in reversed(matches):
        cleaned = " ".join(candidate.strip().split())
        if cleaned and re.search(r"[A-Za-z]", cleaned):
            return cleaned
    return ""


def is_meta_reasoning_sentence(sentence: str) -> bool:
    lowered = sentence.casefold()
    meta_markers = (
        "the user", "user request", "user message", "they want",
        "i need", "i should", "i must", "i'm supposed", "i am supposed",
        "first thought", "second thought", "the key here", "the key is",
        "keep it", "tone", "instructions", "prompt", "roleplay",
        "voice assistant", "final answer", "one sentence", "two sentences",
        "concise", "overcomplicating", "friendly touch", "must be under",
        "but maybe", "let's unpack", "we are given", "since i'm", "since i am",
    )
    return any(marker in lowered for marker in meta_markers)


def normalize_answer_sentence(sentence: str) -> str:
    cleaned = sentence.strip().strip('"').strip()
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,")
    if not cleaned:
        return ""
    if cleaned[-1] not in ".!?":
        cleaned += "."
    return cleaned[0].upper() + cleaned[1:]


def salvage_meta_sentence(sentence: str) -> str:
    quoted = extract_quoted_candidate(sentence)
    if quoted:
        return normalize_answer_sentence(quoted)
    like_match = re.search(r"\blike\s+([A-Za-z][^.!?]{1,80})", sentence, flags=re.IGNORECASE)
    if like_match:
        candidate = like_match.group(1).split(" - ", 1)[0].strip(" ,")
        if candidate and not is_meta_reasoning_sentence(candidate):
            return normalize_answer_sentence(candidate)
    if ":" in sentence:
        candidate = sentence.rsplit(":", 1)[-1].strip(" ,")
        if candidate and not is_meta_reasoning_sentence(candidate):
            return normalize_answer_sentence(candidate)
    return ""


def clean_ai_response(text: str) -> str:
    cleaned = str(text or "").strip().strip('"').strip()
    if "</think>" in cleaned.casefold():
        cleaned = cleaned.rsplit("</think>", 1)[-1].strip()
    cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"</?think>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"```.*?```", " ", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"`([^`]*)`", r"\1", cleaned)
    cleaned = re.sub(r"^\s*[-*+]\s+", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(
        r"\b(currently|basically|actually|simply|right now|just)\b",
        "", cleaned, flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,")
    if not cleaned or not re.search(r"[A-Za-z0-9]", cleaned):
        return ""

    quoted_candidate = extract_quoted_candidate(cleaned)
    sentences = [
        sentence.strip(" ,")
        for sentence in re.split(r"(?<=[.!?])\s+", cleaned)
        if sentence.strip(" ,")
    ]
    if not sentences:
        return normalize_answer_sentence(quoted_candidate) if quoted_candidate else ""

    spoken_sentences: list[str] = []
    for sentence in sentences:
        if is_meta_reasoning_sentence(sentence):
            salvaged = salvage_meta_sentence(sentence)
            if salvaged:
                spoken_sentences.append(salvaged)
            continue
        if re.search(
            r"\b(i should|i need|i must|i'm supposed|prompt|instructions|roleplay|tone|sentence)\b",
            sentence, re.IGNORECASE,
        ):
            continue
        if sentence.count(",") >= 2 and len(sentence.split()) <= 8:
            continue
        normalized = normalize_answer_sentence(sentence)
        if normalized:
            spoken_sentences.append(normalized)

    if not spoken_sentences and quoted_candidate:
        return normalize_answer_sentence(quoted_candidate)
    if not spoken_sentences:
        return ""

    deduped: list[str] = []
    seen: set[str] = set()
    for sentence in spoken_sentences:
        key = sentence.casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(sentence)

    return " ".join(deduped[:2]).strip()


def clean_streaming_candidate(text: str) -> str:
    raw = str(text or "")
    lowered = raw.casefold()
    if "<think>" in lowered and "</think>" not in lowered:
        return ""
    return clean_ai_response(raw)
