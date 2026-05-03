"""
Gemini AI Service  (gemini-1.5-flash)
=======================================
Centralised Gemini client for all AI features:
  • Persona-aware election chat
  • Adaptive quiz generation
  • Myth / fact verification
  • Country election system explorer
  • Voter journey builder
"""

import json
import logging
import os
import re
from typing import Any

import google.generativeai as genai
from google.generativeai.types import HarmBlockThreshold, HarmCategory

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT:        HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH:        HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT:  HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT:  HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
}

CHAT_CONFIG   = genai.GenerationConfig(temperature=0.7, top_p=0.95, max_output_tokens=1024)
JSON_CONFIG   = genai.GenerationConfig(temperature=0.2, top_p=0.95, max_output_tokens=2048)
QUIZ_CONFIG   = genai.GenerationConfig(temperature=0.8, top_p=0.95, max_output_tokens=2048)

# ── Persona system prompts ────────────────────────────────────────────────────
PERSONAS: dict[str, str] = {
    "student": (
        "You are talking to a student (age 15–22) learning about elections for the first time. "
        "Use relatable examples, keep explanations engaging, and connect civic participation to "
        "their daily life. Emojis are welcome to keep it friendly."
    ),
    "first_voter": (
        "You are talking to a first-time voter who needs practical step-by-step guidance. "
        "Focus on registration deadlines, polling locations, and what to bring. "
        "Be encouraging — voting for the first time can feel overwhelming."
    ),
    "researcher": (
        "You are talking to a researcher or policy professional who wants in-depth, nuanced "
        "information. Include data, comparative analysis, historical context, and cite the types "
        "of authoritative sources they should consult."
    ),
    "senior": (
        "You are talking to a senior citizen who prefers clear, jargon-free language. "
        "Use large conceptual steps, avoid overwhelm, and emphasise accessibility options "
        "(mail-in ballots, accessible polling stations, etc.)."
    ),
    "general": (
        "You are talking to a general audience member who is curious about elections. "
        "Balance depth with accessibility — informative but not overwhelming."
    ),
}

BASE_SYSTEM_PROMPT = """\
You are ElectoGuide AI, the world's most helpful and knowledgeable election education assistant.
Your mission is to empower citizens with clear, accurate, nonpartisan information about election
processes worldwide.

You excel at:
• Breaking election systems into clear, digestible steps
• Explaining voter registration, ballot casting, and electoral timelines
• Comparing election systems across democracies
• Debunking election myths with evidence-based explanations
• Guiding first-time voters through their civic journey

Core principles:
1. Remain politically NEUTRAL — never favour any party, candidate, or ideology
2. Focus on EDUCATION and EMPOWERMENT — your goal is an informed citizenry
3. Be ACCURATE — only state verified facts; flag uncertainty when present
4. Be ENCOURAGING — civic participation is a fundamental right worth celebrating
5. Be ACCESSIBLE — adapt your language to the user's knowledge level

When unsure, say so honestly and suggest official sources (election.gov, government websites).
"""


# ── Internal helpers ──────────────────────────────────────────────────────────
def _configure() -> None:
    """Configure the Gemini SDK (idempotent)."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError("GEMINI_API_KEY is not set.")
    genai.configure(api_key=api_key)


def _model(config: genai.GenerationConfig) -> genai.GenerativeModel:
    return genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=BASE_SYSTEM_PROMPT,
        safety_settings=SAFETY_SETTINGS,
        generation_config=config,
    )


def _extract_json(text: str) -> dict[str, Any]:
    """Extract the first JSON object from a text response."""
    # Direct parse
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    # Markdown code fence
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # Raw brace extraction
    start, end = text.find("{"), text.rfind("}") + 1
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass
    raise ValueError(f"No valid JSON found in model response:\n{text[:300]}")


# ── Public API ────────────────────────────────────────────────────────────────

async def generate_chat_response(
    message: str,
    history: list[dict[str, str]] | None = None,
    persona: str = "general",
    entities: list[str] | None = None,
) -> str:
    """
    Generate a conversational response using Gemini 1.5 Flash.

    Args:
        message:  User's current message.
        history:  Previous turns [{role, content}]. Max 10 kept.
        persona:  One of student | first_voter | researcher | senior | general.
        entities: Optional list of detected entities (from Cloud NL API) to enrich context.
    """
    _configure()

    persona_ctx = PERSONAS.get(persona, PERSONAS["general"])
    system = f"{BASE_SYSTEM_PROMPT}\n\nUser context: {persona_ctx}"

    if entities:
        system += f"\n\nKey topics detected in the user's message: {', '.join(entities)}. Ensure your response addresses these specifically."

    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=system,
        safety_settings=SAFETY_SETTINGS,
        generation_config=CHAT_CONFIG,
    )

    # Build Gemini history
    gemini_history = [
        {"role": t["role"], "parts": [t["content"]]}
        for t in (history or [])[-10:]
        if t.get("role") in ("user", "model") and t.get("content", "").strip()
    ]

    chat = model.start_chat(history=gemini_history)
    response = await chat.send_message_async(message)
    return response.text


async def generate_quiz(topic: str, difficulty: str = "medium", count: int = 5) -> dict[str, Any]:
    """Generate multiple-choice quiz questions about an election topic."""
    _configure()
    model = _model(QUIZ_CONFIG)

    prompt = f"""Generate exactly {count} multiple-choice quiz questions about: "{topic}"
Context: election education. Difficulty: {difficulty}.

Return ONLY valid JSON (no markdown, no extra text):
{{
  "topic": "{topic}",
  "difficulty": "{difficulty}",
  "questions": [
    {{
      "id": 1,
      "question": "Question text?",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct": 0,
      "explanation": "Educational explanation of the correct answer."
    }}
  ]
}}

"correct" is the 0-based index of the right option. All questions must be factual and nonpartisan."""

    response = await model.generate_content_async(prompt)
    return _extract_json(response.text)


async def fact_check_claim(claim: str) -> dict[str, Any]:
    """Fact-check an election-related claim."""
    _configure()
    model = _model(JSON_CONFIG)

    prompt = f"""You are a nonpartisan election fact-checker. Analyse this claim:

CLAIM: "{claim}"

Return ONLY valid JSON (no markdown, no extra text):
{{
  "claim": "Restate the claim clearly",
  "verdict": "TRUE" | "FALSE" | "PARTIALLY TRUE" | "MISLEADING" | "UNVERIFIABLE",
  "explanation": "2–3 sentence evidence-based explanation",
  "confidence": <integer 0–100>,
  "sources_hint": "Suggest 1–2 types of authoritative sources",
  "context": "Brief additional context for the reader"
}}"""

    response = await model.generate_content_async(prompt)
    return _extract_json(response.text)


async def get_country_election_info(country: str) -> dict[str, Any]:
    """Get structured election system information for a country."""
    _configure()
    model = _model(JSON_CONFIG)

    prompt = f"""Provide accurate election system information for: {country}

Return ONLY valid JSON (no markdown, no extra text):
{{
  "country": "Full country name",
  "flag_emoji": "🏳",
  "system_type": "e.g. Federal Republic",
  "electoral_system": "e.g. First Past the Post",
  "voting_age": 18,
  "election_frequency_years": 4,
  "registration_required": true,
  "compulsory_voting": false,
  "key_steps": ["Step 1", "Step 2", "Step 3", "Step 4", "Step 5"],
  "timeline": [
    {{"phase": "Campaign Period", "timing": "X months before", "description": "..."}},
    {{"phase": "Registration Closes", "timing": "X days before", "description": "..."}},
    {{"phase": "Election Day", "timing": "Day 0", "description": "..."}},
    {{"phase": "Results", "timing": "Within X days", "description": "..."}}
  ],
  "unique_features": ["Feature 1", "Feature 2"],
  "fun_fact": "One surprising fact about this country's elections"
}}"""

    response = await model.generate_content_async(prompt)
    return _extract_json(response.text)


async def generate_voter_journey(country: str, persona: str = "first_voter") -> dict[str, Any]:
    """Generate a personalised voter journey for a given country and persona."""
    _configure()
    model = _model(JSON_CONFIG)

    persona_desc = PERSONAS.get(persona, PERSONAS["general"])

    prompt = f"""Create a practical, personalised voter journey for someone in {country}.
User persona: {persona_desc}

Return ONLY valid JSON (no markdown, no extra text):
{{
  "country": "{country}",
  "persona": "{persona}",
  "journey_title": "Your Voting Journey in {country}",
  "steps": [
    {{
      "step": 1,
      "icon": "📋",
      "title": "Step title",
      "description": "Detailed, practical description",
      "deadline_note": "Must be done X days before election",
      "tips": ["Tip 1", "Tip 2"],
      "official_resource": "Type of official website or office to contact"
    }}
  ],
  "important_reminders": ["Reminder 1", "Reminder 2", "Reminder 3"],
  "accessibility_note": "Information about accessible voting options available"
}}

Include 5–7 steps. Be practical and actionable."""

    response = await model.generate_content_async(prompt)
    return _extract_json(response.text)
