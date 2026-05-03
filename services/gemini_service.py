"""
Gemini AI Service
=================
Wraps Google Generative AI (Gemini 2.0 Flash Lite) for all AI-powered features.
Handles chat, quiz generation, fact-checking, and country information.
"""

import json
import logging
import os
import re
from typing import Any

import google.generativeai as genai
from google.generativeai.types import HarmBlockThreshold, HarmCategory

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")

SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
}

GENERATION_CONFIG = genai.GenerationConfig(
    temperature=0.7,
    top_p=0.95,
    top_k=40,
    max_output_tokens=1024,
)

# ── Persona Contexts ──────────────────────────────────────────────────────────
PERSONA_CONTEXTS: dict[str, str] = {
    "student": (
        "You are talking to a student (age 15-22) learning about elections for the first time. "
        "Use relatable examples, keep explanations simple and engaging, and connect civic "
        "participation to their daily life. Use occasional emojis to keep it friendly."
    ),
    "first_voter": (
        "You are talking to a first-time voter who needs practical, step-by-step guidance. "
        "Focus on actionable information: registration deadlines, polling locations, what to bring. "
        "Be encouraging and reassuring — voting for the first time can feel overwhelming."
    ),
    "researcher": (
        "You are talking to a researcher or policy professional who wants in-depth, nuanced "
        "information. Include data, comparative analysis across democracies, historical context, "
        "and cite the types of academic or official sources they should consult."
    ),
    "senior": (
        "You are talking to a senior citizen who prefers clear, simple language with no jargon. "
        "Use larger conceptual steps, avoid overwhelming detail, and emphasize accessibility "
        "features in the voting process (mail-in ballots, accessible polling stations, etc.)."
    ),
    "general": (
        "You are talking to a general audience member curious about elections. "
        "Balance depth with accessibility — be informative but not overwhelming."
    ),
}

BASE_SYSTEM_PROMPT = """You are ElectoGuide AI, the world's most helpful and knowledgeable \
election education assistant. Your mission is to empower citizens with clear, accurate, \
nonpartisan information about election processes worldwide.

You excel at:
• Breaking down complex election systems into clear, digestible steps
• Explaining voter registration, ballot casting, and electoral timelines
• Comparing election systems across different democracies
• Debunking election myths with evidence-based explanations
• Guiding first-time voters through their civic journey
• Answering questions about electoral laws, candidates, parties (informatively, not persuasively)

Core principles:
1. Always remain politically NEUTRAL — never favor any party, candidate, or ideology
2. Focus on EDUCATION and EMPOWERMENT — your goal is an informed citizenry
3. Be ACCURATE — only state verified facts; flag uncertainty when present
4. Be ENCOURAGING — civic participation is a fundamental right worth celebrating
5. Be ACCESSIBLE — adapt your language to the user's knowledge level

When you don't know something, say so honestly and suggest official sources (election.gov, \
government websites, etc.) rather than guessing.
"""


def _configure_genai() -> None:
    """Configure the Gemini API client once."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY environment variable is not set. "
            "Please set it in your .env file or Cloud Run environment."
        )
    genai.configure(api_key=api_key)


def _build_system_prompt(persona: str) -> str:
    """Combine base prompt with persona-specific context."""
    persona_ctx = PERSONA_CONTEXTS.get(persona, PERSONA_CONTEXTS["general"])
    return f"{BASE_SYSTEM_PROMPT}\n\nUser context: {persona_ctx}"


def _extract_json(text: str) -> dict[str, Any]:
    """Safely extract the first JSON object from a text response."""
    # Try direct parse first
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Try markdown code-fence extraction
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    # Fallback: find first {...} block
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract valid JSON from model response:\n{text[:300]}")


# ── Public API ─────────────────────────────────────────────────────────────────

async def generate_chat_response(
    message: str,
    history: list[dict[str, str]] | None = None,
    persona: str = "general",
) -> str:
    """
    Generate a chat response using Gemini.

    Args:
        message:  The user's current message.
        history:  List of {"role": "user"|"model", "content": "..."} dicts.
        persona:  One of student | first_voter | researcher | senior | general.

    Returns:
        The assistant's text response.
    """
    _configure_genai()
    system_prompt = _build_system_prompt(persona)

    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=system_prompt,
        safety_settings=SAFETY_SETTINGS,
        generation_config=GENERATION_CONFIG,
    )

    # Build Gemini-format history (keep last 10 turns to stay within context)
    gemini_history: list[dict] = []
    for turn in (history or [])[-10:]:
        role = turn.get("role", "user")
        content = turn.get("content", "")
        if role in ("user", "model") and content.strip():
            gemini_history.append({"role": role, "parts": [content]})

    chat = model.start_chat(history=gemini_history)
    response = await chat.send_message_async(message)
    return response.text


async def generate_quiz(
    topic: str,
    difficulty: str = "medium",
    count: int = 5,
) -> dict[str, Any]:
    """
    Generate multiple-choice quiz questions about an election topic.

    Returns:
        {"questions": [{id, question, options, correct, explanation}, ...]}
    """
    _configure_genai()
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        safety_settings=SAFETY_SETTINGS,
        generation_config=genai.GenerationConfig(temperature=0.8, max_output_tokens=2048),
    )

    prompt = f"""Generate exactly {count} multiple-choice quiz questions about the topic: "{topic}"
in the context of election education.

Difficulty level: {difficulty} (easy = basic concepts, medium = intermediate, hard = in-depth)

Return ONLY a valid JSON object with this exact schema (no markdown, no extra text):
{{
  "topic": "{topic}",
  "difficulty": "{difficulty}",
  "questions": [
    {{
      "id": 1,
      "question": "Clear question text here?",
      "options": [
        "Option A text",
        "Option B text",
        "Option C text",
        "Option D text"
      ],
      "correct": 0,
      "explanation": "Why this answer is correct, with educational context."
    }}
  ]
}}

The "correct" field is the 0-based index of the correct option in the options array.
Make sure all questions are factual, nonpartisan, and educational."""

    response = await model.generate_content_async(prompt)
    return _extract_json(response.text)


async def fact_check_claim(claim: str) -> dict[str, Any]:
    """
    Fact-check an election-related claim using Gemini.

    Returns:
        {claim, verdict, explanation, confidence, sources_hint}
    """
    _configure_genai()
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        safety_settings=SAFETY_SETTINGS,
        generation_config=genai.GenerationConfig(temperature=0.2, max_output_tokens=512),
    )

    prompt = f"""You are a nonpartisan election fact-checker. Analyze this claim:

CLAIM: "{claim}"

Return ONLY a valid JSON object (no markdown, no extra text):
{{
  "claim": "Restate the claim clearly",
  "verdict": "TRUE" | "FALSE" | "PARTIALLY TRUE" | "MISLEADING" | "UNVERIFIABLE",
  "explanation": "2-3 sentence evidence-based explanation, citing what is known",
  "confidence": <integer 0-100 representing your confidence in this verdict>,
  "sources_hint": "Suggest 1-2 types of authoritative sources to verify this",
  "context": "Brief additional context that helps the reader understand the topic"
}}

Be factual, nonpartisan, and educational. If the claim is about a specific country's election,
focus on that country's official rules and processes."""

    response = await model.generate_content_async(prompt)
    return _extract_json(response.text)


async def get_country_election_info(country: str) -> dict[str, Any]:
    """
    Get comprehensive election system information for a country.

    Returns:
        Structured data about the country's election process.
    """
    _configure_genai()
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        safety_settings=SAFETY_SETTINGS,
        generation_config=genai.GenerationConfig(temperature=0.3, max_output_tokens=1024),
    )

    prompt = f"""Provide accurate election system information for: {country}

Return ONLY a valid JSON object (no markdown, no extra text):
{{
  "country": "Full country name",
  "flag_emoji": "🏳",
  "system_type": "e.g. Federal Republic, Constitutional Monarchy, etc.",
  "electoral_system": "e.g. First Past the Post, Proportional Representation, etc.",
  "voting_age": 18,
  "election_frequency_years": 4,
  "branches": {{
    "legislature": "Name and structure",
    "executive": "How elected",
    "judiciary": "Appointment process"
  }},
  "registration_required": true,
  "compulsory_voting": false,
  "key_steps": [
    "Step 1: ...",
    "Step 2: ...",
    "Step 3: ...",
    "Step 4: ...",
    "Step 5: ..."
  ],
  "timeline": [
    {{"phase": "Campaign Period", "timing": "X months before election", "description": "..."}},
    {{"phase": "Voter Registration Closes", "timing": "X days before", "description": "..."}},
    {{"phase": "Election Day", "timing": "Day 0", "description": "..."}},
    {{"phase": "Results Announced", "timing": "Within X days", "description": "..."}}
  ],
  "unique_features": [
    "Notable feature 1",
    "Notable feature 2"
  ],
  "fun_fact": "One interesting or surprising fact about this country's election process"
}}"""

    response = await model.generate_content_async(prompt)
    return _extract_json(response.text)


async def generate_voter_journey(country: str, persona: str = "first_voter") -> dict[str, Any]:
    """
    Generate a personalized voter journey/checklist.
    """
    _configure_genai()
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        safety_settings=SAFETY_SETTINGS,
        generation_config=genai.GenerationConfig(temperature=0.5, max_output_tokens=1024),
    )

    persona_desc = PERSONA_CONTEXTS.get(persona, PERSONA_CONTEXTS["general"])

    prompt = f"""Create a practical voter journey for someone in {country}.
User persona: {persona_desc}

Return ONLY a valid JSON object (no markdown, no extra text):
{{
  "country": "{country}",
  "persona": "{persona}",
  "journey_title": "Your Voting Journey in {country}",
  "steps": [
    {{
      "step": 1,
      "icon": "📋",
      "title": "Step title",
      "description": "Detailed description of what to do",
      "deadline_note": "e.g. Must be done 15 days before election",
      "tips": ["Tip 1", "Tip 2"],
      "official_resource": "Type of official website or office to contact"
    }}
  ],
  "important_reminders": ["Reminder 1", "Reminder 2", "Reminder 3"],
  "accessibility_note": "Information about accessible voting options"
}}

Include 5-7 steps. Be practical and actionable."""

    response = await model.generate_content_async(prompt)
    return _extract_json(response.text)
