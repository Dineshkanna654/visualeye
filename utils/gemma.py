"""
Gemma 4 26B MoE vision API integration via OpenRouter.

Why Gemma 4 26B MoE (google/gemma-4-26b-a4b-it:free)?
- MoE architecture activates only ~4B parameters per token, giving GPT-4-class
  vision understanding at a fraction of inference cost — critical for NGOs and
  accessibility projects with zero budget.
- 256K context window handles long descriptions and multi-turn conversations.
- Native multimodal: single model for image + text, no separate OCR service.
- Apache 2.0 license allows commercial and non-profit deployment without legal risk.
- Free tier on OpenRouter makes this viable for the 8M+ visually impaired users
  in India who cannot afford paid AI subscriptions.
"""

import os
import time
import base64
import requests
from typing import Optional

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_ID = "google/gemma-4-26b-a4b-it:free"

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

SYSTEM_PROMPT = (
    "You are a visual accessibility assistant for visually impaired users. "
    "Describe what you see clearly and concisely. Include: objects and their "
    "positions, any visible text (read it aloud), potential hazards, people if "
    "present. Keep response under 4 sentences. Be direct."
)


def build_prompt(mode: str, language_code: str) -> str:
    lang_name = LANGUAGE_NAMES.get(language_code, "English")
    template = PROMPTS.get(mode, PROMPTS["describe"])
    return template.format(language=lang_name)


def analyze_image(
    image_base64: str,
    mode: str = "describe",
    language_code: str = "en",
    retries: int = 2,
) -> dict:
    """
    Send image to Gemma 4 via OpenRouter and return the description.

    Returns:
        dict with keys: description (str), model_used (str), error (str|None)
    """
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        return {
            "description": "",
            "model_used": MODEL_ID,
            "error": "OPENROUTER_API_KEY environment variable is not set.",
        }

    prompt_text = build_prompt(mode, language_code)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://visualeye.app",
        "X-Title": "VisualEye Accessibility Tool",
    }

    payload = {
        "model": MODEL_ID,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt_text,
                    },
                ],
            },
        ],
        "max_tokens": 300,
    }

    last_error: Optional[str] = None

    for attempt in range(retries + 1):
        try:
            response = requests.post(
                OPENROUTER_API_URL,
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
                        "OpenRouter rate limit reached. Please wait a moment "
                        "and try again."
                    ),
                }

            if response.status_code == 402:
                return {
                    "description": "",
                    "model_used": MODEL_ID,
                    "error": "API quota exceeded. Please check your OpenRouter account.",
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
            description = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )

            if not description:
                return {
                    "description": "",
                    "model_used": MODEL_ID,
                    "error": "Gemma returned an empty response. Please try again.",
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
            last_error = "Cannot reach OpenRouter API. Check your internet connection."
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
