"""
Gemma 4 26B MoE vision API integration via Google's Gemini API.

Why Gemma 4 26B MoE (gemma-4-26b-a4b-it)?
- MoE architecture activates only ~4B parameters per token, giving GPT-4-class
  vision understanding at a fraction of inference cost — critical for NGOs and
  accessibility projects with zero budget.
- Native multimodal: single model for image + text understanding.
- Large context window handles long descriptions and multi-turn conversations.
- Apache 2.0 license allows commercial and non-profit deployment without legal risk.
- Available free on Google's Gemini API — serves India's 8M+ visually impaired
  population without any paid AI subscription.
"""

import os
import re
import time
import requests
from typing import Optional

MODEL_ID = "gemma-4-26b-a4b-it"
GEMINI_API_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_ID}:generateContent"
)

PROMPTS = {
    "describe": (
        "Describe this scene for a visually impaired person in {language}. "
        "Include what objects you see, their positions, any text, and important "
        "details. Be clear and concise. Maximum 3 sentences."
    ),
    "read_text": (
        "Read all text visible in this image for a visually impaired person. "
        "Start with the most important/prominent text first. If no text is visible, "
        "say so clearly. Respond in {language}."
    ),
    "hazard": (
        "You are a safety assistant. Analyze this image for potential hazards "
        "or obstacles for someone who is visually impaired. List hazards clearly "
        "in {language}. If safe, say 'Path appears clear.' Maximum 2 sentences."
    ),
    "people": (
        "Describe the people in this image for a visually impaired person. "
        "Include approximate number, positions, and any visible emotions or "
        "actions. Respond in {language}. If no people, say so."
    ),
}

LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "ta": "Tamil",
    "te": "Telugu",
    "kn": "Kannada",
    "bn": "Bengali",
}

SYSTEM_PREAMBLE = (
    "You are a visual accessibility assistant for visually impaired users. "
    "Describe what you see clearly and concisely. Include: objects and their "
    "positions, any visible text (read it aloud), potential hazards, people if "
    "present. Keep response under 4 sentences. Be direct.\n\n"
    "IMPORTANT: Reply ONLY with the final description sentences for the user. "
    "Do NOT show any reasoning, thinking process, analysis steps, headers, "
    "bullet points, or preamble. Speak directly to the user in plain prose.\n\n"
)


def build_prompt(mode: str, language_code: str) -> str:
    lang_name = LANGUAGE_NAMES.get(language_code, "English")
    template = PROMPTS.get(mode, PROMPTS["describe"])
    return template.format(language=lang_name)


# Gemma 4 emits a chain-of-thought scratchpad before the user-facing answer.
# Two patterns we've observed:
#   1. "Thinking Process:\n  1. ...\n  2. ..." then the final answer as prose.
#   2. A series of "* ..." bullet/draft lines, then the final answer concatenated
#      on the SAME line as the last bullet (no blank line separator).
# The reliable signal: the actual user-facing answer is plain prose that does
# not start with a list marker. We walk the text and keep the tail prose.
_LIST_MARKERS = ("*", "-", "•", "#", ">")
_NUMBERED = re.compile(r"^\d+[\.\)]\s")


def _looks_like_scratchpad_line(line: str) -> bool:
    s = line.lstrip()
    if not s:
        return False
    if s.startswith(_LIST_MARKERS):
        return True
    if _NUMBERED.match(s):
        return True
    return False


# Match the pattern (single line): a quoted draft sentence followed immediately
# by an unquoted sentence starting with a capital letter or opening quote.
# The draft section may itself contain inner single quotes around words.
_DRAFT_THEN_ANSWER = re.compile(
    r'[\"“][^\n\"”“]{15,}?[.!?][\"”]([A-Z“\"][^\n]{10,})\s*$'
)


def _extract_post_quote(line: str) -> Optional[str]:
    """If a line ends with `..."draft sentence."answer sentence...`, return the answer."""
    m = _DRAFT_THEN_ANSWER.search(line)
    if m:
        return m.group(1).strip()
    return None


def _extract_duplicate_tail(line: str) -> Optional[str]:
    """
    Gemma 4 often emits `<answer>.<answer>.` where the same sentence appears twice
    back-to-back. Detect that and return only the second copy.
    """
    # Look for two consecutive sentences ending in '.', '!', or '?' where the
    # tail (everything after the final period of the first sentence) starts
    # with a capital letter and is "long enough" to be a real sentence.
    # We try splits on '.', '!', '?' (right-most first) and check if what
    # precedes is roughly equal in length and shares many words with the tail.
    for sep in (".", "!", "?"):
        # Find all positions where this punctuation appears followed by an
        # uppercase letter (no space). That's the glue point.
        for i in range(len(line) - 1, 0, -1):
            if line[i] == sep and i + 1 < len(line) and line[i + 1].isupper():
                left = line[: i + 1].strip()
                right = line[i + 1:].strip()
                # Both halves should be substantive sentences.
                if len(left) < 25 or len(right) < 25:
                    continue
                # Compare word overlap to confirm they're near-duplicates.
                left_words = set(w.lower() for w in re.findall(r"\w+", left))
                right_words = set(w.lower() for w in re.findall(r"\w+", right))
                if not left_words or not right_words:
                    continue
                overlap = len(left_words & right_words) / max(
                    len(left_words), len(right_words)
                )
                if overlap >= 0.7:
                    return right
    return None


def _strip_thinking(text: str) -> str:
    """Remove Gemma 4's chain-of-thought scratchpad, keep only the final answer."""
    text = text.strip()
    if not text:
        return text

    # Strategy: the user-facing answer is always at the very end of the output.
    # The model typically wraps a final draft in quotes and then writes the
    # de-quoted answer immediately after, on the same line. So:
    #   1. Check the last non-empty line for the `"draft"answer` glue pattern.
    #      If found, return just the answer portion.
    #   2. Otherwise, if there's an obvious scratchpad (bullets/numbered lines),
    #      return whatever prose follows the last scratchpad line.
    #   3. Otherwise, return the text as-is.

    lines = text.splitlines()

    # Step 1: last non-empty line glue patterns (most reliable).
    for line in reversed(lines):
        if line.strip():
            # 1a. `"draft sentence."Answer sentence...`
            post_quote = _extract_post_quote(line)
            if post_quote:
                return post_quote
            # 1b. `Answer sentence.Answer sentence.` (model doubles the output)
            dup_tail = _extract_duplicate_tail(line)
            if dup_tail:
                return dup_tail
            break

    # Step 2: scratchpad cutoff.
    last_scratch_idx = -1
    for i, line in enumerate(lines):
        if _looks_like_scratchpad_line(line):
            last_scratch_idx = i

    if last_scratch_idx != -1:
        tail = "\n".join(lines[last_scratch_idx + 1:]).strip()
        if tail:
            return tail

    return text


def analyze_image(
    image_base64: str,
    mode: str = "describe",
    language_code: str = "en",
    retries: int = 2,
) -> dict:
    """
    Send image to Gemma 4 via Google's Gemini API and return the description.

    Returns:
        dict with keys: description (str), model_used (str), error (str|None)
    """
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return {
            "description": "",
            "model_used": MODEL_ID,
            "error": "GEMINI_API_KEY environment variable is not set.",
        }

    prompt_text = SYSTEM_PREAMBLE + build_prompt(mode, language_code)

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": image_base64,
                        }
                    },
                    {"text": prompt_text},
                ],
            }
        ],
        "generationConfig": {
            # Gemma 4 emits an internal scratchpad before the final answer,
            # so we need plenty of headroom to ensure the user-facing reply fits.
            "maxOutputTokens": 1500,
            "temperature": 0.4,
        },
    }

    last_error: Optional[str] = None

    for attempt in range(retries + 1):
        try:
            response = requests.post(
                GEMINI_API_URL,
                headers=headers,
                json=payload,
                timeout=60,
            )

            if response.status_code == 429:
                wait = 2 ** attempt
                if attempt < retries:
                    time.sleep(wait)
                    continue
                return {
                    "description": "",
                    "model_used": MODEL_ID,
                    "error": (
                        "Gemini API rate limit reached. Please wait a moment "
                        "and try again."
                    ),
                }

            if response.status_code in (402, 403):
                return {
                    "description": "",
                    "model_used": MODEL_ID,
                    "error": (
                        "API quota exceeded or access denied. "
                        "Please check your Gemini API key and quota."
                    ),
                }

            if not response.ok:
                last_error = f"API error {response.status_code}: {response.text[:200]}"
                if attempt < retries:
                    time.sleep(1)
                    continue
                return {
                    "description": "",
                    "model_used": MODEL_ID,
                    "error": last_error,
                }

            data = response.json()

            # Gemini response shape:
            # { "candidates": [ { "content": { "parts": [ { "text": "..." } ] } } ] }
            candidates = data.get("candidates", [])
            if not candidates:
                # Could be blocked by safety filters
                prompt_feedback = data.get("promptFeedback", {})
                block_reason = prompt_feedback.get("blockReason")
                if block_reason:
                    return {
                        "description": "",
                        "model_used": MODEL_ID,
                        "error": f"Request blocked: {block_reason}. Try a different image.",
                    }
                return {
                    "description": "",
                    "model_used": MODEL_ID,
                    "error": "Gemma returned no candidates. Please try again.",
                }

            parts = candidates[0].get("content", {}).get("parts", [])
            raw_text = "".join(p.get("text", "") for p in parts).strip()
            description = _strip_thinking(raw_text)

            if not description:
                finish_reason = candidates[0].get("finishReason", "")
                return {
                    "description": "",
                    "model_used": MODEL_ID,
                    "error": (
                        f"Gemma returned an empty response (finishReason={finish_reason}). "
                        "Please try again."
                    ),
                }

            return {
                "description": description,
                "model_used": MODEL_ID,
                "error": None,
            }

        except requests.exceptions.Timeout:
            last_error = "Request timed out. The API took too long to respond."
            if attempt < retries:
                time.sleep(1)
                continue
        except requests.exceptions.ConnectionError:
            last_error = "Cannot reach Gemini API. Check your internet connection."
            if attempt < retries:
                time.sleep(2)
                continue
        except Exception as exc:  # noqa: BLE001
            last_error = f"Unexpected error: {str(exc)}"
            break

    return {
        "description": "",
        "model_used": MODEL_ID,
        "error": last_error or "Unknown error occurred.",
    }
