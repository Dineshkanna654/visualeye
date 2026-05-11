# 👁️ VisualEye — AI Visual Accessibility Assistant

[![Live Demo](https://img.shields.io/badge/demo-live-brightgreen)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Model: Gemma 4](https://img.shields.io/badge/model-Gemma%204%2026B%20MoE-orange)](#why-gemma-4-26b-moe)
[![Free Tier](https://img.shields.io/badge/free%20tier-Gemini%20API-success)](#)

**VisualEye** is a free, open-source AI-powered accessibility tool that helps visually impaired users understand their surroundings. Point your camera at any scene, press one button, and hear a clear audio description — in English, Hindi, Tamil, Telugu, Kannada, or Bengali.

> Built for India's 8 million+ visually impaired people. Runs on the Gemini API free tier — no credit card required.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📸 Live Camera | Instant webcam capture via browser — no app install |
| 🖼️ Photo Upload | Upload saved photos from mobile gallery |
| 👁️ Scene Description | Full AI description of objects, layout, and context |
| 📄 Text Reading | OCR-style text extraction and reading |
| ⚠️ Hazard Detection | Safety analysis for navigation |
| 👥 People Description | Social context for interpersonal situations |
| 🔊 Multilingual TTS | Audio output in 6 Indian languages |
| 📋 Copy Description | Copy text to share or paste elsewhere |
| 🕒 Analysis History | Last 5 results stored in session |

---

## 🚀 Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/visualeye.git
cd visualeye

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set your Google Gemini API key (free tier — no credit card needed)
cp .env.example .env
# Edit .env and add: GEMINI_API_KEY=your_key_here
# Get a free key at: https://aistudio.google.com/apikey

# 4a. Run the FastAPI version (recommended)
python app.py
# Open http://localhost:8000 in your browser

# 4b. OR run the Streamlit version (backup)
streamlit run streamlit_app.py
```

---

## 🏗️ Project Structure

```
visualeye/
├── app.py              # FastAPI backend (REST API + HTML serving)
├── streamlit_app.py    # Streamlit backup (standalone, no FastAPI needed)
├── frontend/
│   └── index.html      # Complete single-file UI (vanilla JS, no frameworks)
├── utils/
│   ├── gemma.py        # Gemma 4 API calls via Google Gemini API
│   └── tts.py          # gTTS text-to-speech (6 languages)
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🤖 Why Gemma 4 26B MoE?

This is the most important architectural decision in the project — and it was deliberate.

### The Problem with Other Models

| Model | Issue |
|-------|-------|
| GPT-4o | $0.005/image — unsustainable for NGO deployment |
| Claude 3.5 | Paid tier only, API costs add up |
| Llava 1.5 | Outdated, weak multilingual support |
| Gemma 3 2B | Too small for accurate scene descriptions |

### Why Gemma 4 26B MoE Wins

**1. MoE Architecture = Efficiency at Scale**
Gemma 4 uses a Mixture-of-Experts architecture that activates only ~4 billion parameters per token despite having 26 billion total. This means:
- GPT-4 class reasoning at ~⅙ the compute cost
- Faster inference → lower latency for real-time accessibility
- Free tier on the Gemini API remains economically viable long-term

**2. Large Context Window**
Handles multi-turn conversations ("describe the person on the left", "now the person on the right") without losing context — critical for assistive technology workflows.

**3. Native Multimodal**
One model handles image understanding AND text generation in 6 languages. No separate OCR service, no separate translation API — zero additional cost.

**4. Apache 2.0 License**
NGOs, governments, and hospitals can deploy VisualEye in production without legal risk or licensing fees. This is non-negotiable for accessibility infrastructure in India.

**5. Free Tier on Google's Gemini API**
`gemma-4-26b-a4b-it` is available on the Gemini API free tier via Google AI Studio — straight from the model's creators, no third-party gateway needed. The free tier covers typical accessibility usage for individuals and small NGOs; paid tiers are available for higher-volume deployments. Combined with gTTS (also free), the operational cost stays near zero.

**6. Multilingual Excellence**
Gemma 4 was trained with strong multilingual support including Hindi, Tamil, Telugu, Kannada, and Bengali — the five major languages after English in India's visually impaired population.

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/`      | Serve frontend UI |
| `GET`  | `/health`| Health check + config status |
| `POST` | `/analyze` | Analyze image, return description + audio |
| `GET`  | `/history` | Last 5 analysis results |

### POST /analyze

**Request:**
```json
{
  "image_base64": "...",
  "language": "hi",
  "mode": "describe"
}
```

**Response:**
```json
{
  "description": "A person is standing at a pedestrian crossing...",
  "audio_base64": "//uQxAAAAAAAAAAAAAAAAAAAAAAAWGluZ...",
  "model_used": "gemma-4-26b-a4b-it",
  "processing_time_ms": 1240,
  "error": null
}
```

**Modes:** `describe` · `read_text` · `hazard` · `people`

**Languages:** `en` · `hi` · `ta` · `te` · `kn` · `bn`

---

## 🖥️ Screenshots

> _Add screenshots here_

---

## 🛠️ Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| AI Vision | Gemma 4 26B MoE | Free, multimodal, multilingual |
| AI Gateway | Google Gemini API | First-party access from model creators, free tier |
| Backend | FastAPI + Python | Fast async, auto-docs |
| TTS | gTTS | Free, supports all 6 languages |
| Frontend | Vanilla JS + HTML | Zero dependencies, accessible |
| Backup UI | Streamlit | Rapid deployment alternative |

---

## 🌍 Social Impact

India has over **8 million visually impaired people**, with 60% living in rural areas with limited access to assistive technology. Existing solutions like JAWS ($1,000+/year) or Be My Eyes (requires volunteers) are either expensive or dependent on human availability.

VisualEye runs on a **free API tier** (no credit card needed to start), works **offline-ready** (once the model is called), and speaks **regional languages** — making it the first AI accessibility tool designed specifically for India's linguistic diversity.

---

## 📄 License

MIT License — free for personal, educational, and commercial use.

```
Copyright (c) 2026 VisualEye Contributors
```
