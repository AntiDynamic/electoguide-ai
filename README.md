# 🗳️ ElectoGuide AI

**Live Application:** [https://electoguide-ai-991060611253.us-central1.run.app](https://electoguide-ai-991060611253.us-central1.run.app)

ElectoGuide AI is an interactive, nonpartisan, and highly accessible election education platform. It leverages multiple Google Cloud services to demystify global election processes, debunk myths, and provide dynamically personalized civic journeys for different types of citizens (students, seniors, first-time voters, and researchers).

---

## 🧠 Architecture and Approach

Our approach is centered on **Persona-Driven Education** and **Graceful Degradation**. 
We built an agentic framework that dynamically adjusts its vocabulary, tone, and complexity based on the user's selected persona. To ensure a flawless user experience, the system relies on strictly structured JSON outputs from the Gemini model for UI-heavy features (like dynamic quizzes and fact-checking), while maintaining conversational flow using Cloud Firestore and the Cloud Natural Language API.

## ⚙️ How the Solution Works
1. **Context-Aware Chat**: Users interact with the Gemini AI. User prompts are first analyzed by the **Cloud Natural Language API** to extract key entities, which are then injected invisibly into the Gemini system prompt to enrich the AI's contextual awareness.
2. **Multi-lingual Support**: The UI incorporates the **Cloud Translation API** to translate AI responses into 12 different languages on-the-fly, instantly localizing the civic education experience.
3. **Session Persistence**: Chat history is persistently stored via **Cloud Firestore**, allowing conversations to survive page reloads and cross-device sessions seamlessly.
4. **Interactive Education Modules**: Beyond chat, the app features a dynamically generated Myth Buster, an Electoral Quiz, and Country Profiles—all generated in real-time using the `google-genai` SDK and `gemini-3.1-flash-lite-preview`.

## 📌 Design Principles
1. **Nonpartisan Foundation**: The AI must strictly refuse to endorse political candidates or ideologies, focusing purely on systemic and educational facts.
2. **Variable Internet Access**: The frontend is highly optimized Vanilla JS and CSS without heavy JavaScript framework bundles to download, catering to users in low-bandwidth environments.
3. **Hardware Accessibility**: Integrated Text-to-Speech (TTS) ensures users who cannot easily read lengthy texts can still access the information.

---

## 🛠️ Engineering Highlights

### Code Quality
* **Modular Architecture**: The codebase is logically separated into `routes/` (API endpoints), `services/` (business logic and GCP wrappers), and `tests/`. This separation of concerns ensures components can be scaled or swapped independently.
* **Strict Type Hinting**: The entire Python backend uses strict type annotations (`-> dict[str, Any]`, `list[str]`), drastically reducing runtime errors and improving IDE autocomplete.
* **Self-Documenting Code**: Every function contains comprehensive docstrings. We utilized **Pydantic** for declarative data validation, making the data contracts between the frontend and backend instantly readable.

### Security & Reliability
* **Strict Rate Limiting**: Implemented `slowapi` to enforce strict IP-based rate limits (e.g., `30/minute` on chat) to protect the Gemini API from abuse or Denial of Wallet attacks.
* **Robust Input Sanitization**: All user inputs route through Pydantic validators (`min_length`, `max_length`, `pattern`) to prevent prompt injection and buffer overflow attempts before they ever reach the AI model.
* **Secure Deployment**: Our `Dockerfile` uses a multi-stage build and strictly runs the application as a non-root, unprivileged user.
* **Graceful Degradation**: If Cloud Firestore or the Translation API goes down, the application doesn't crash. It seamlessly falls back to in-memory mode or English-only mode, maximizing uptime.

### Efficiency
* **High-Speed, Low-Cost Modeling**: Architected around **`gemini-3.1-flash-lite-preview`** for ultra-low latency responses.
* **Fully Asynchronous I/O**: The entire backend utilizes `async`/`await` (e.g., `await client.aio.models.generate_content`). This allows a single Uvicorn worker to handle thousands of concurrent connections efficiently without blocking the main event loop.

### Testing
* **Comprehensive Test Suite**: The repository includes a robust `pytest` suite containing **41 passing automated tests**.
* **Mocking External APIs**: We extensively mocked the Google Cloud services (Firestore, NL, Translation, and Gemini) via `unittest.mock` to ensure tests run deterministically and don't consume API quota.
* **Coverage**: We validate edge cases, such as fallback mechanisms when the `GEMINI_API_KEY` is missing, ensuring our error handling returns precise `503 Service Unavailable` codes instead of opaque 500 crashes.

### Google Cloud Integration
* **Cloud Firestore**: Provides a NoSQL persistent database. Chat sessions are saved instantly.
* **Cloud Natural Language API**: Analyzes user inputs to extract key topics and entities for prompt enrichment.
* **Cloud Translation API**: Powers real-time, bidirectional language localization.
* **Cloud Logging**: Every API request writes a structured telemetry log (including response times and extracted entities) for deep observability.
* **Cloud Run & Cloud Build**: The entire application is deployed as a serverless container, scaling dynamically from zero.
