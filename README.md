# 🗳️ ElectoGuide AI

**Live Application:** [https://electoguide-ai-991060611253.us-central1.run.app](https://electoguide-ai-991060611253.us-central1.run.app)

ElectoGuide AI is an interactive, nonpartisan, and highly accessible election education platform. It leverages multiple Google Cloud services to demystify global election processes, debunk myths, and provide dynamically personalized civic journeys for different types of citizens (students, seniors, first-time voters, and researchers).

---

## 🎯 Chosen Vertical
**Election Process Education**
*Create an assistant that helps users understand the election process, timelines, and steps in an interactive and easy-to-follow way.*

## 🧠 Approach and Logic
Our approach is centered on **Persona-Driven Education** and **Graceful Degradation**. 
We built an agentic framework that dynamically adjusts its vocabulary, tone, and complexity based on the user's selected persona. To ensure a flawless user experience, the system relies on strictly structured JSON outputs from the Gemini model for UI-heavy features (like dynamic quizzes and fact-checking), while maintaining conversational flow using Cloud Firestore and the Cloud Natural Language API.

## ⚙️ How the Solution Works
1. **Context-Aware Chat**: Users interact with the Gemini AI. User prompts are first analyzed by the **Cloud Natural Language API** to extract key entities, which are then injected invisibly into the Gemini system prompt to enrich the AI's contextual awareness.
2. **Multi-lingual Support**: The UI incorporates the **Cloud Translation API** to translate AI responses into 12 different languages on-the-fly, instantly localizing the civic education experience.
3. **Session Persistence**: Chat history is persistently stored via **Cloud Firestore**, allowing conversations to survive page reloads and cross-device sessions seamlessly.
4. **Interactive Education Modules**: Beyond chat, the app features a dynamically generated Myth Buster, an Electoral Quiz, and Country Profiles—all generated in real-time by the cutting-edge `google-genai` SDK using `gemini-3.1-flash-lite-preview`.

## 📌 Assumptions Made
1. **Nonpartisan Foundation**: We assume the AI must strictly refuse to endorse political candidates or ideologies, focusing purely on systemic and educational facts.
2. **Variable Internet Access**: We assumed users might be in low-bandwidth environments, so the frontend is highly optimized Vanilla JS and CSS without heavy JavaScript framework bundles to download.
3. **Hardware Accessibility**: We assumed not all users can easily read lengthy texts, so we integrated a fallback Text-to-Speech (TTS) system.

---

## 🏆 Evaluation Focus Areas

### 1. Code Quality
* **Structure**: Clean, modularized backend (`routes/`, `services/`, `main.py`) built on **FastAPI**.
* **Maintainability**: Fully type-hinted Python backend with clear Docstrings. Utilizes Dependency Injection patterns.
* **Modern Tooling**: Implemented the latest `google-genai` SDK and robust Pydantic models for data validation.

### 2. Security
* **Rate Limiting**: Strictly enforced API rate limits via `slowapi` (e.g., max 30 requests/minute per IP) to prevent abuse and denial-of-service.
* **Input Sanitization**: Pydantic validators strictly sanitize and limit user input lengths before any processing occurs.
* **Non-Root Docker**: The application is securely containerized and runs as a non-privileged user in production.

### 3. Efficiency
* **Optimal Resources**: Utilizing `gemini-3.1-flash-lite-preview` for ultra-fast, low-latency generation with an extremely lightweight footprint.
* **Async I/O**: Fully asynchronous FastAPI implementation (`await client.aio.models.generate_content`) ensuring the server never blocks under concurrent load.

### 4. Testing
* **Validation**: The repository includes a comprehensive `pytest` test suite with **41 passing tests** covering every endpoint, error state, and mocking all Google Cloud integrations.

### 5. Accessibility
* **Inclusive Design**: 
  - Fully responsive, high-contrast dark theme UI designed for maximum readability.
  - WCAG-compliant structural HTML (ARIA labels, semantic tags).
  - Integrated Text-to-Speech (TTS) for visually impaired users.
  - Dynamic Persona swapping (e.g., simplifying complex political jargon into plain language for Seniors).

### 6. Google Services Integration
ElectoGuide AI represents a meaningful, deep integration of the Google Cloud ecosystem:
* **Gemini API (3.1 Flash Lite)**: Core reasoning, formatting, and generation engine.
* **Cloud Firestore**: Persistent NoSQL session state management.
* **Cloud Natural Language API**: Deep entity extraction for conversational context.
* **Cloud Translation API**: Real-time multi-lingual localization.
* **Cloud Logging**: Structured request telemetry and monitoring across all endpoints.
* **Cloud Run**: Enterprise-grade, auto-scaling serverless deployment.

---
*Built for the Prompt Wars Hackathon.*
