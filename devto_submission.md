---
title: "VisualEye: I Built a Free AI Accessibility Tool with Gemma 4 (₹0 Cost)"
published: true
tags: devchallenge, gemmachallenge, gemma, accessibility
cover_image: https://your-cover-image-url.png
---

> **TL;DR** — I built VisualEye, an AI assistant that helps visually impaired users "see" through their camera. It describes scenes, reads text, detects hazards, and speaks the answer aloud in 6 Indian languages. Cost: ₹0. Stack: Gemma 4 26B MoE, FastAPI, gTTS. Here's how and why.

---

## The Problem I'm Solving

India has **8.1 million visually impaired people** — the largest population of any country in the world. Yet the assistive technology available to them is either:

- **Too expensive** — JAWS screen reader costs ₹80,000/year
- **Language-limited** — most AI tools only work in English
- **Connectivity-dependent** — requiring volunteers (Be My Eyes) or always-on cloud subscriptions

I wanted to build something that runs at **zero cost**, speaks **regional languages**, and requires nothing more than a smartphone camera.

---

## What I Built: VisualEye

{% youtube YOUR_VIDEO_ID_HERE %}

**VisualEye** is a web app that:
1. Captures an image from your webcam or photo gallery
2. Sends it to **Gemma 4 26B MoE** for vision analysis
3. Returns a spoken audio description in English, Hindi, Tamil, Telugu, Kannada, or Bengali

Four analysis modes:
- **Describe Scene** — full contextual description
- **Read Text** — OCR-style text reading
- **Check Hazards** — safety analysis for navigation
- **Describe People** — social context awareness

---

## Why I Chose Gemma 4 26B MoE (Not GPT-4o, Not Claude)

This was the most important decision I made. Here's my reasoning:

### The Model Comparison

| Model | Cost/image | Multilingual | License | Free Tier |
|-------|-----------|--------------|---------|-----------|
| **Gemma 4 26B MoE** | **₹0** | **Excellent** | **Apache 2.0** | **Yes** |
| GPT-4o | ~₹0.40 | Good | Proprietary | No |
| Claude 3.5 Sonnet | ~₹0.35 | Good | Proprietary | No |
| Llava 1.5 13B | Self-host | Limited | Open | No |

### The MoE Advantage

Gemma 4 uses **Mixture-of-Experts** architecture — 26 billion total parameters, but only ~4 billion activate per token. What this means in practice:

```
Traditional 26B Dense Model:
Token → ALL 26B parameters activated → High compute cost

Gemma 4 26B MoE:
Token → Router selects top experts → ~4B parameters activated
Result: GPT-4 class quality at ~⅙ the inference cost
```

For an accessibility tool targeting NGOs with zero budget, this architecture difference is the reason the entire project is possible.

### 256K Context Window

Most accessibility tools are one-shot: take photo, get description. But real users ask follow-up questions:

> "What color is the shirt on the person on the left?"
> "Is there a door visible?"
> "What does the sign in the back say?"

Gemma 4's 256K context window means I can chain these queries in a multi-turn session without losing context — a feature that's technically impossible with 8K context models.

### Apache 2.0 License = Deployable by Anyone

This matters enormously for accessibility infrastructure. An NGO serving blind students in rural Bihar cannot afford to worry about:
- Terms of service changes
- API cost increases
- Model deprecation
- Data privacy clauses

Apache 2.0 means they can fork this repo, run it on their own server, and never worry about any of that. **That's what makes open source actually accessible.**

---

## The Architecture

```
Browser (index.html)
    │
    │ POST /analyze {image_base64, language, mode}
    ▼
FastAPI (app.py)
    │
    ├── utils/gemma.py ──► OpenRouter API ──► Gemma 4 26B MoE
    │                                              ▼
    │                                     Vision description text
    │
    └── utils/tts.py ───► gTTS ──► MP3 audio (base64)
    │
    ▼
Browser receives {description, audio_base64}
    │
    ├── Display description text
    └── Autoplay audio
```

Zero external paid services. Zero infrastructure costs. The only moving part is the OpenRouter free tier API call.

---

## Key Code: The Gemma 4 API Call

```python
# utils/gemma.py

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_ID = "google/gemma-4-26b-a4b-it:free"

def analyze_image(image_base64: str, mode: str, language_code: str) -> dict:
    payload = {
        "model": MODEL_ID,
        "messages": [
            {
                "role": "system",
                "content": "You are a visual accessibility assistant for visually "
                           "impaired users. Describe what you see clearly and concisely."
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    },
                    {
                        "type": "text",
                        "text": build_prompt(mode, language_code)
                    }
                ]
            }
        ],
        "max_tokens": 300
    }

    response = requests.post(
        OPENROUTER_API_URL,
        headers={
            "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
            "HTTP-Referer": "https://visualeye.app",
            "X-Title": "VisualEye Accessibility Tool"
        },
        json=payload,
        timeout=60
    )
    # ... error handling and retry logic
```

### Mode-Specific Prompts

```python
PROMPTS = {
    "describe": (
        "Describe this scene for a visually impaired person in {language}. "
        "Include what objects you see, their positions, any text, and important "
        "details. Be clear and concise. Maximum 3 sentences."
    ),
    "hazard": (
        "You are a safety assistant. Analyze this image for potential hazards "
        "or obstacles for someone who is visually impaired. List hazards clearly "
        "in {language}. If safe, say 'Path appears clear.' Maximum 2 sentences."
    ),
    # ...
}
```

---

## Key Code: Multilingual TTS

```python
# utils/tts.py — gTTS handles all 6 languages natively

from gtts import gTTS
import io, base64

def text_to_speech_base64(text: str, language_code: str = "en") -> dict:
    tts = gTTS(text=text, lang=language_code, slow=False)
    buffer = io.BytesIO()
    tts.write_to_fp(buffer)
    buffer.seek(0)
    return {
        "audio_base64": base64.b64encode(buffer.read()).decode("utf-8"),
        "error": None
    }
```

Language support: `en` · `hi` · `ta` · `te` · `kn` · `bn`

That's English, Hindi, Tamil, Telugu, Kannada, and Bengali — covering 95%+ of India's visually impaired population in their native language.

---

## Key Code: Frontend (Zero Dependencies)

The entire UI is a single `index.html` with vanilla JavaScript. No React, no Vue, no jQuery. This matters because:

1. **Load time**: ~8KB vs 200KB+ for a React app
2. **Accessibility**: Pure HTML semantics, ARIA labels, keyboard navigable
3. **Deployability**: Copy one file to any web server and it works

```javascript
// Camera capture
captureBtn.addEventListener('click', () => {
    const canvas = document.createElement('canvas');
    canvas.width  = videoEl.videoWidth;
    canvas.height = videoEl.videoHeight;
    canvas.getContext('2d').drawImage(videoEl, 0, 0);
    const dataURL = canvas.toDataURL('image/jpeg', 0.9);
    state.capturedImageBase64 = dataURL.split(',')[1];
    // ... show preview
});

// Analyze with fetch() — no axios, no jQuery
const response = await fetch('/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        image_base64: state.capturedImageBase64,
        language: langSelect.value,
        mode: state.mode,
    }),
});
const data = await response.json();
audioPlayer.src = 'data:audio/mp3;base64,' + data.audio_base64;
audioPlayer.play();
```

---

## Challenges I Solved

### 1. Rate Limiting (429 errors)

OpenRouter's free tier has rate limits. I implemented exponential backoff retry:

```python
for attempt in range(retries + 1):
    response = requests.post(...)
    if response.status_code == 429:
        wait = 2 ** attempt  # 1s, 2s, 4s
        if attempt < retries:
            time.sleep(wait)
            continue
        return {"error": "Rate limit reached. Please wait and try again."}
```

### 2. Autoplay Policies

Modern browsers block audio autoplay without prior user interaction. My solution:

```javascript
audioPlayer.play().catch(() => {
    // Silently fail — the audio player controls are visible
    // so the user can press play manually
});
```

The audio controls are always shown, so users never lose access to the audio even if autoplay is blocked.

### 3. Mobile Camera Orientation

Mobile cameras send images in varying orientations (EXIF rotation). PIL's `thumbnail()` method handles this correctly, and I set `facingMode: 'environment'` in getUserMedia to default to the rear camera on mobile.

---

## Setup (3 Minutes)

```bash
git clone https://github.com/yourusername/visualeye
cd visualeye
pip install -r requirements.txt
echo "OPENROUTER_API_KEY=your_key" > .env
python app.py
# → Open http://localhost:8000
```

Get a free API key at [openrouter.ai/keys](https://openrouter.ai/keys) — no credit card required.

**Streamlit alternative** (if FastAPI isn't available):
```bash
streamlit run streamlit_app.py
```

---

## What's Next

- [ ] Offline mode using a quantized Gemma 4 2B local model (GGUF)
- [ ] Android app wrapper (Capacitor)
- [ ] Braille display output via Web Bluetooth API
- [ ] NGO deployment guide for community health workers

---

## GitHub

🔗 [github.com/yourusername/visualeye](#)

Star it if you find it useful — it helps other accessibility developers discover it.

---

## The Bigger Picture

I built this in 48 hours for the DEV Gemma Challenge, but the real goal is longer-term: **prove that accessibility AI doesn't need to cost money**.

Every ₹0 spent on AI inference is a ₹ that can go toward training, hardware, or reaching more users. Gemma 4's MoE efficiency and Apache 2.0 license make that possible in a way no other model currently does.

If you work with accessibility NGOs or government programs in India, I'd love to talk. The code is yours — fork it, deploy it, improve it.

---

*Built with ❤️ for India's 8M+ visually impaired · Gemma 4 26B MoE via OpenRouter · MIT License*
