"""
VisualEye — Streamlit backup version.

Fully self-contained: runs without the FastAPI backend.
Uses the same Gemma 4 and gTTS utilities.

Run:
    streamlit run streamlit_app.py
"""

import base64
import io
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

# Import shared utilities (same as FastAPI version)
from utils.gemma import analyze_image, MODEL_ID, LANGUAGE_NAMES
from utils.tts import text_to_speech_base64, get_supported_languages

# ── Page config ────────────────────────────────────────────
st.set_page_config(
    page_title="VisualEye – AI Accessibility Assistant",
    page_icon="👁️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ──────────────────────────────────────────────
st.markdown("""
<style>
  .main { background: #0d1117; }
  .stApp { background: #0d1117; color: #e6edf3; }
  h1, h2, h3 { color: #58a6ff !important; }
  .stButton > button {
    background: #1f6feb;
    color: white;
    border: none;
    border-radius: 10px;
    padding: 12px 24px;
    font-size: 1rem;
    font-weight: 600;
    width: 100%;
  }
  .stButton > button:hover { background: #388bfd; }
  .result-box {
    background: #161b22;
    border: 1px solid #30363d;
    border-left: 3px solid #58a6ff;
    border-radius: 10px;
    padding: 16px;
    font-size: 1.1rem;
    line-height: 1.75;
    color: #e6edf3;
    margin: 8px 0;
  }
  .history-item {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 10px 14px;
    margin: 6px 0;
    font-size: 0.9rem;
    color: #8b949e;
  }
</style>
""", unsafe_allow_html=True)

# ── Session state ───────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = []

# ── Header ──────────────────────────────────────────────────
st.markdown("# 👁️ VisualEye")
st.markdown("**AI-powered visual accessibility assistant** · Gemma 4 26B MoE · Free")

api_key = os.getenv("OPENROUTER_API_KEY", "")
if not api_key:
    st.error(
        "⚠️ OPENROUTER_API_KEY is not set. "
        "Create a `.env` file with `OPENROUTER_API_KEY=your_key_here`."
    )

st.divider()

# ── Mode tabs ────────────────────────────────────────────────
tab_describe, tab_text, tab_hazard, tab_people = st.tabs([
    "👁️ Describe Scene",
    "📄 Read Text",
    "⚠️ Check Hazards",
    "👥 Describe People",
])

MODE_MAP = {
    "👁️ Describe Scene":  "describe",
    "📄 Read Text":        "read_text",
    "⚠️ Check Hazards":   "hazard",
    "👥 Describe People":  "people",
}

# ── Image input ──────────────────────────────────────────────
st.markdown("### 📸 Capture or Upload")

col_cam, col_up = st.columns(2)

with col_cam:
    camera_photo = st.camera_input("Take a photo", label_visibility="collapsed")

with col_up:
    uploaded_file = st.file_uploader(
        "Or upload a photo",
        type=["jpg", "jpeg", "png", "webp"],
        label_visibility="visible",
    )

# Determine which image to use (camera takes priority)
image_source = camera_photo or uploaded_file
image_b64: str | None = None
pil_image: Image.Image | None = None

if image_source is not None:
    img_bytes = image_source.getvalue()
    # Resize to max 1024px wide to keep API payload small
    pil_image = Image.open(io.BytesIO(img_bytes))
    pil_image.thumbnail((1024, 1024), Image.LANCZOS)
    buf = io.BytesIO()
    pil_image.save(buf, format="JPEG", quality=85)
    image_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    st.image(pil_image, caption="Ready for analysis", use_container_width=True)

# ── Language selector ────────────────────────────────────────
st.markdown("### 🔊 Output Language")
lang_options = get_supported_languages()
lang_names   = [f"🔊 {l['name']}" for l in lang_options]
lang_codes   = [l["code"] for l in lang_options]

selected_lang_idx = st.selectbox(
    "Select language",
    range(len(lang_names)),
    format_func=lambda i: lang_names[i],
    label_visibility="collapsed",
)
selected_lang = lang_codes[selected_lang_idx]

# ── Analyze button in each tab ───────────────────────────────
def run_analysis(mode: str):
    if image_b64 is None:
        st.warning("Please capture or upload an image first.")
        return

    if not api_key:
        st.error("API key not configured. Set OPENROUTER_API_KEY in your .env file.")
        return

    with st.spinner("Gemma 4 is thinking…"):
        gemma_result = analyze_image(
            image_base64=image_b64,
            mode=mode,
            language_code=selected_lang,
        )

    if gemma_result["error"]:
        st.error(f"❌ {gemma_result['error']}")
        return

    description = gemma_result["description"]

    # Show description
    st.markdown("### 📝 Analysis Result")
    st.markdown(f'<div class="result-box">{description}</div>', unsafe_allow_html=True)

    # Copy button (workaround via st.code which is selectable)
    with st.expander("📋 Select text to copy"):
        st.code(description, language=None)

    # TTS
    with st.spinner("Generating audio…"):
        tts_result = text_to_speech_base64(description, selected_lang)

    if tts_result["error"]:
        st.warning(f"Audio unavailable: {tts_result['error']}")
    elif tts_result["audio_base64"]:
        audio_bytes = base64.b64decode(tts_result["audio_base64"])
        st.markdown("### 🔊 Audio Description")
        st.audio(audio_bytes, format="audio/mp3", autoplay=True)

    # Save to history
    st.session_state.history.insert(0, {
        "description": description,
        "mode": mode,
        "language": selected_lang,
    })
    if len(st.session_state.history) > 5:
        st.session_state.history = st.session_state.history[:5]

    st.success(f"✅ Analysis complete · {gemma_result['model_used']}")


with tab_describe:
    st.markdown("Gemma 4 will describe the full scene in detail.")
    if st.button("🔍 Analyze Scene", key="btn_describe"):
        run_analysis("describe")

with tab_text:
    st.markdown("Gemma 4 will read all visible text in the image.")
    if st.button("📖 Read Text", key="btn_text"):
        run_analysis("read_text")

with tab_hazard:
    st.markdown("Gemma 4 will identify hazards and obstacles.")
    if st.button("⚠️ Check for Hazards", key="btn_hazard"):
        run_analysis("hazard")

with tab_people:
    st.markdown("Gemma 4 will describe any people in the image.")
    if st.button("👥 Describe People", key="btn_people"):
        run_analysis("people")

# ── Analysis history ─────────────────────────────────────────
if st.session_state.history:
    st.divider()
    st.markdown("### 🕒 Recent Analyses")
    for item in st.session_state.history:
        mode_label = {
            "describe": "Describe", "read_text": "Read Text",
            "hazard": "Hazards", "people": "People",
        }.get(item["mode"], item["mode"])
        st.markdown(
            f'<div class="history-item"><strong>{mode_label} · '
            f'{item["language"].upper()}</strong><br/>{item["description"]}</div>',
            unsafe_allow_html=True,
        )

# ── Footer ───────────────────────────────────────────────────
st.divider()
st.markdown(
    "<small>Powered by Gemma 4 26B MoE via OpenRouter · Free tier · "
    "Built for India's 8M+ visually impaired population · MIT License</small>",
    unsafe_allow_html=True,
)
