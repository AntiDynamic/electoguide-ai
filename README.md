# ElectoGuide AI 🗳️

**An AI-powered Election Process Education Assistant**  
*Built for the Google Antigravity Prompt Wars Competition*

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green)](https://fastapi.tiangolo.com)
[![Gemini](https://img.shields.io/badge/Gemini-2.0--flash--lite-orange)](https://ai.google.dev)
[![Cloud Run](https://img.shields.io/badge/Google%20Cloud-Cloud%20Run-blue)](https://cloud.google.com/run)

---

## 🎯 Chosen Vertical

**Election Process Education** — An assistant that helps users understand the election process, timelines, and steps in an interactive and easy-to-follow way.

---

## 🌟 What Makes This Unique

Unlike a basic Q&A bot, ElectoGuide AI is a **full civic education platform** with:

| Feature | Description |
|---|---|
| 🤖 **Persona-Aware AI Chat** | Adapts responses for Students, First Voters, Researchers, Seniors |
| 🌍 **Country Explorer** | Deep-dive into 30+ democracies' election systems via Gemini |
| 🗺️ **Voter Journey Map** | Personalized step-by-step voting guide per country & persona |
| 🧠 **Adaptive Quiz** | AI-generated questions across 6 topics & 3 difficulty levels |
| 🔍 **Myth Buster** | Real-time AI fact-checking with confidence scores |
| 🔊 **Voice Narration** | Google Cloud TTS + browser Web Speech API fallback |
| ♿ **Accessibility Panel** | High contrast, large font, voice controls — WCAG 2.1 AA |

---

## 🏗️ Architecture

```
ElectoGuide AI
├── Backend:  Python FastAPI (modular routers + services)
├── AI:       Google Gemini 2.0 Flash Lite (all AI features)
├── TTS:      Google Cloud Text-to-Speech (+ browser fallback)
├── Frontend: Vanilla HTML/CSS/JS (Zero framework, premium UI)
└── Deploy:   Docker → Google Cloud Run
```

---

## 📁 Project Structure

```
prompt_wars/
├── main.py                   # FastAPI app entry point
├── routes/
│   ├── chat.py               # Gemini AI chat endpoint
│   ├── quiz.py               # AI quiz generation
│   ├── factcheck.py          # Myth/fact verification
│   ├── tts.py                # Text-to-Speech
│   └── countries.py          # Country election info + journeys
├── services/
│   ├── gemini_service.py     # Gemini client & prompts
│   └── tts_service.py        # Cloud TTS client
├── static/
│   ├── style.css             # Design system
│   ├── extra.css             # Component styles
│   └── app.js                # SPA frontend logic
├── templates/
│   └── index.html            # Single Page Application
├── tests/
│   ├── test_chat.py          # Chat endpoint tests
│   └── test_routes.py        # All other endpoint tests
├── Dockerfile                # Multi-stage build
├── requirements.txt
└── .env.example
```

---

## 🧠 Approach & Logic

### Decision Making
The app uses **persona context injection** — when a user selects their persona (Student, First Voter, Researcher, etc.), that context is prepended to every Gemini system prompt, fundamentally changing the AI's communication style, depth, and focus.

### Google Services
1. **Gemini 2.0 Flash Lite** — Powers all AI features: chat, quiz generation, fact-checking, country info, and voter journeys. The model is given specialized system prompts for each feature.
2. **Google Cloud Text-to-Speech** — Converts AI responses to audio. The app gracefully falls back to the browser's Web Speech API when Cloud TTS credentials are unavailable.

### Security
- API keys loaded exclusively from environment variables (never hardcoded)
- Rate limiting on all AI endpoints (30 req/min for chat, 15 for quiz)
- Input sanitization and length limits on all user inputs
- Non-root Docker user; multi-stage build minimizes attack surface
- CORS configured with explicit method/header allowlists

### Efficiency
- Gemini `gemini-2.0-flash-lite` chosen for fast inference at low cost
- Frontend uses zero JS frameworks — pure Vanilla JS (~15KB)
- Multi-stage Docker build produces lean production image
- Chat history capped at 10 turns to control token usage

---

## 🚀 Local Development

```bash
# 1. Clone & enter
git clone <your-repo-url> && cd prompt_wars

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and set GEMINI_API_KEY

# 5. Run
python main.py
# Open http://localhost:8080
```

---

## 🧪 Running Tests

```bash
pytest tests/ -v
```

---

## 🐳 Docker

```bash
docker build -t electoguide-ai .
docker run -p 8080:8080 -e GEMINI_API_KEY=your_key electoguide-ai
```

---

## ☁️ Cloud Run Deployment

```bash
# Set your project
export PROJECT_ID=promptwars-495214
export REGION=us-central1

# Build and push
gcloud builds submit --tag gcr.io/$PROJECT_ID/electoguide-ai

# Deploy
gcloud run deploy electoguide-ai \
  --image gcr.io/$PROJECT_ID/electoguide-ai \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=your_key,GEMINI_MODEL=gemini-2.0-flash-lite \
  --port 8080 \
  --memory 512Mi \
  --min-instances 0 \
  --max-instances 10
```

---

## ⚙️ Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | ✅ Yes | — | Google Gemini API key |
| `GEMINI_MODEL` | No | `gemini-2.0-flash-lite` | Gemini model name |
| `PORT` | No | `8080` | Server port |
| `ENVIRONMENT` | No | `production` | `development` enables hot reload |
| `LOG_LEVEL` | No | `INFO` | Logging verbosity |
| `GOOGLE_APPLICATION_CREDENTIALS` | No | — | Path to GCP service account JSON (for Cloud TTS) |

---

## ♿ Accessibility

- **WCAG 2.1 AA** compliant structure
- Full **ARIA labels** on all interactive elements
- **Keyboard navigation** supported throughout
- **High contrast mode** toggle
- **Large font mode** toggle
- **Voice narration** for all AI responses
- **`aria-live`** regions for dynamic content updates

---

## 📋 Assumptions

1. Gemini 2.0 Flash Lite is available via the provided API key
2. Cloud TTS is optional — the app fully functions with browser TTS fallback
3. Election information provided by Gemini is educational and should be verified with official government sources for legal/voting decisions
4. The app is nonpartisan and does not endorse any political party or candidate

---

## 👨‍💻 Built With

- [FastAPI](https://fastapi.tiangolo.com) — Modern Python web framework
- [Google Gemini AI](https://ai.google.dev) — Generative AI backbone
- [Google Cloud Run](https://cloud.google.com/run) — Serverless container deployment
- [Google Cloud Text-to-Speech](https://cloud.google.com/text-to-speech) — Voice narration
