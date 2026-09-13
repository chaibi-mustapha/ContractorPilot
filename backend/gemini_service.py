import json
import logging
import os
import re
from typing import Any, Dict, List, Optional
import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("ContractorPilot.Gemini")

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiService:
    def __init__(self) -> None:
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()
        # Fallback cascade in case the requested model name is preview or tiered
        self.candidate_models = [
            self.model_name,
            "gemini-3.7-flash",
            "gemini-3.6-flash",
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
        ]

    def update_config(self, api_key: str, model_name: Optional[str] = None) -> None:
        self.api_key = api_key.strip()
        os.environ["GEMINI_API_KEY"] = self.api_key
        if model_name:
            self.model_name = model_name.strip()
            os.environ["GEMINI_MODEL"] = self.model_name
            if self.model_name not in self.candidate_models:
                self.candidate_models.insert(0, self.model_name)

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def analyze_walkthrough(self, voice_text: str) -> Optional[Dict[str, Any]]:
        """
        Uses Google Gemini (default Gemini 3.8 Flash) to extract structured construction scopes:
        - Rooms with dimensions (sq ft, length, width, height)
        - Subcontractor trade labor tasks (category, item_name, days, unit_price, notes)
        - Material takeoffs (category, item_name, quantity, unit, unit_price, notes)
        """
        if not self.is_configured():
            return None

        system_prompt = (
            "You are an expert American general contractor AI estimating assistant for residential and commercial remodels. "
            "Analyze the jobsite walkthrough audio transcription and extract the renovation scope into structured JSON.\n"
            "\n"
            "TOPIC RELEVANCE & SANITY CHECK:\n"
            "First, verify whether this dictation describes actual home renovation, construction, remodeling, room dimensions, building materials, or contractor trades. "
            "If the dictation is OFF-TOPIC, unrelated to construction/remodeling (e.g. food recipes, sports, politics, weather commentary, casual chit-chat, stories, poetry, or random gibberish):\n"
            'Set "is_relevant": false, "rejection_reason": "Provide a clear, polite explanation in the language of the prompt explaining that the text does not contain remodel, jobsite, or construction trade instructions.", "rooms": [], "tasks_by_trade": [], "materials": [].\n'
            "If the dictation IS related to renovation, construction, or remodeling:\n"
            'Set "is_relevant": true, "rejection_reason": null, and extract the scopes as follows:\n'
            "- Surfaces in 'sq ft'\n"
            "- Dimensions in 'ft'\n"
            "- Liquid materials (paint, sealer) in 'gal' (assume ~350 sq ft per gal for 2 coats)\n"
            "- Flooring/tile in 'sq ft' with 10% cut allowance\n"
            "- Subcontractor labor in 'days' with realistic contractor day rates ($350-$500/day)\n"
            "- Hardware and fixtures in 'units'\n"
            "\n"
            "Return ONLY a valid JSON object with this exact structure:\n"
            "{\n"
            '  "is_relevant": boolean,\n'
            '  "rejection_reason": "string or null",\n'
            '  "rooms": [\n'
            '    {"name": "string", "length": float, "width": float, "height": float, "surface": float, "renovation_types": ["string"], "notes": "string"}\n'
            "  ],\n"
            '  "tasks_by_trade": [\n'
            '    {"category": "string (Tiler|Painter|Electrician|Plumber|Drywall)", "item_name": "string", "quantity": float, "unit": "days", "item_type": "labor", "estimated_unit_price": float, "notes": "string"}\n'
            "  ],\n"
            '  "materials": [\n'
            '    {"category": "string (Flooring|Paint|Electrical|Plumbing|Drywall)", "item_name": "string", "quantity": float, "unit": "string (sq ft|gal|units)", "item_type": "material", "estimated_unit_price": float, "notes": "string"}\n'
            "  ]\n"
            "}"
        )

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{system_prompt}\n\nHere is the jobsite walkthrough dictation to analyze:\n\"\"\"{voice_text}\"\"\""}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            }
        }

        # Try models in order (starting with gemini-3.8-flash)
        async with httpx.AsyncClient(timeout=25.0) as client:
            for model in self.candidate_models:
                url = f"{GEMINI_API_BASE}/{model}:generateContent?key={self.api_key}"
                try:
                    logger.info(f"Calling Gemini API with model: {model}")
                    response = await client.post(url, json=payload)
                    
                    if response.status_code == 200:
                        data = response.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            raw_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                            # Parse JSON
                            cleaned = raw_text.strip()
                            if cleaned.startswith("```json"):
                                cleaned = cleaned[7:]
                            if cleaned.endswith("```"):
                                cleaned = cleaned[:-3]
                            parsed = json.loads(cleaned.strip())
                            
                            # Validate basic structure
                            if "rooms" in parsed or "tasks_by_trade" in parsed or "is_relevant" in parsed:
                                logger.info(f"Successfully analyzed walkthrough using {model} (is_relevant={parsed.get('is_relevant', True)})")
                                parsed["ai_model"] = model
                                return parsed
                    else:
                        logger.warning(f"Gemini API returned status {response.status_code} for {model}: {response.text[:200]}")
                        if response.status_code in [401, 403] or "API key not valid" in response.text:
                            logger.error(f"Gemini API key rejected: {response.text[:200]}")
                            break
                        # If 404 (model not found), continue to next candidate model
                        if response.status_code in [404, 400]:
                            continue
                except Exception as e:
                    logger.error(f"Error calling Gemini with model {model}: {e}")
                    continue

        return None

    async def analyze_walkthrough_audio(self, audio_base64: str, mime_type: str = "audio/wav") -> Optional[Dict[str, Any]]:
        """
        Uses Google Gemini Multimodal Audio to directly listen to the recorded jobsite walkthrough voice note,
        transcribe it verbatim, and extract structured renovation scopes, rooms, and materials.
        """
        if not self.is_configured():
            return None

        system_prompt = (
            "You are an expert American general contractor AI estimating assistant for residential and commercial remodels. "
            "Listen carefully to the recorded jobsite walkthrough audio.\n"
            "1. In 'transcription', provide the verbatim transcript of what was spoken in the audio (in the language spoken by the user).\n"
            "\n"
            "TOPIC RELEVANCE & SANITY CHECK:\n"
            "Determine if the spoken audio describes actual home renovation, construction, remodeling, room dimensions, building materials, or contractor trades. "
            "If the audio is OFF-TOPIC, unrelated to construction/remodeling (e.g. food/cooking, sports, politics, weather chat, personal thoughts, casual chitchat, or random noises/gibberish):\n"
            'Set "is_relevant": false, "rejection_reason": "Provide a clear, polite explanation in the language spoken in the audio explaining that the audio does not contain renovation, remodel, or construction trade instructions.", "rooms": [], "tasks_by_trade": [], "materials": [].\n'
            "If the audio IS related to renovation, construction, or remodeling:\n"
            'Set "is_relevant": true, "rejection_reason": null, and extract the scopes into structured JSON with USA Customary Units and USD ($) currency:\n'
            "- Surfaces in 'sq ft'\n"
            "- Dimensions in 'ft'\n"
            "- Liquid materials (paint, sealer) in 'gal'\n"
            "- Flooring/tile in 'sq ft' with 10% cut allowance\n"
            "- Subcontractor labor in 'days' with realistic contractor day rates ($350-$500/day)\n"
            "- Hardware and fixtures in 'units'\n"
            "\n"
            "Return ONLY a valid JSON object with this exact structure:\n"
            "{\n"
            '  "is_relevant": boolean,\n'
            '  "rejection_reason": "string or null",\n'
            '  "transcription": "Verbatim transcript of the voice audio",\n'
            '  "rooms": [\n'
            '    {"name": "string", "length": float, "width": float, "height": float, "surface": float, "renovation_types": ["string"], "notes": "string"}\n'
            "  ],\n"
            '  "tasks_by_trade": [\n'
            '    {"category": "string (Tiler|Painter|Electrician|Plumber|Drywall)", "item_name": "string", "quantity": float, "unit": "days", "item_type": "labor", "estimated_unit_price": float, "notes": "string"}\n'
            "  ],\n"
            '  "materials": [\n'
            '    {"category": "string (Flooring|Paint|Electrical|Plumbing|Drywall)", "item_name": "string", "quantity": float, "unit": "string (sq ft|gal|units)", "item_type": "material", "estimated_unit_price": float, "notes": "string"}\n'
            "  ]\n"
            "}"
        )

        raw_mime = (mime_type or "audio/wav").split(";")[0].strip().lower()
        mime_mapping = {
            "audio/wave": "audio/wav",
            "audio/x-wav": "audio/wav",
            "audio/mp3": "audio/mp3",
            "audio/mpeg": "audio/mp3",
            "audio/m4a": "audio/aac",
            "audio/mp4": "audio/aac",
            "audio/ogg": "audio/ogg",
            "audio/flac": "audio/flac",
            "audio/aiff": "audio/aiff",
            "audio/webm": "audio/webm",
        }
        clean_mime = mime_mapping.get(raw_mime, raw_mime or "audio/wav")

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": system_prompt},
                        {
                            "inlineData": {
                                "mimeType": clean_mime,
                                "data": audio_base64
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            }
        }

        # Models with native multimodal audio support in Google AI Studio
        audio_candidates = [
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-2.5-pro",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            self.model_name
        ]
        candidates: List[str] = []
        for m in audio_candidates:
            if m and m not in candidates:
                candidates.append(m)

        self.last_audio_error = None

        async with httpx.AsyncClient(timeout=45.0) as client:
            for model in candidates:
                url = f"{GEMINI_API_BASE}/{model}:generateContent?key={self.api_key}"
                try:
                    logger.info(f"Calling Gemini Audio API with model: {model} (mime: {clean_mime})")
                    response = await client.post(url, json=payload)
                    if response.status_code == 200:
                        data = response.json()
                        candidates_data = data.get("candidates", [])
                        if candidates_data:
                            raw_text = candidates_data[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                            cleaned = raw_text.strip()
                            if cleaned.startswith("```json"):
                                cleaned = cleaned[7:]
                            elif cleaned.startswith("```"):
                                cleaned = cleaned[3:]
                            if cleaned.endswith("```"):
                                cleaned = cleaned[:-3]

                            s_idx = cleaned.find("{")
                            e_idx = cleaned.rfind("}")
                            if s_idx != -1 and e_idx != -1:
                                cleaned = cleaned[s_idx:e_idx + 1]

                            parsed = json.loads(cleaned.strip())
                            if "rooms" in parsed or "tasks_by_trade" in parsed or "transcription" in parsed:
                                logger.info(f"Successfully processed direct audio walkthrough using {model}")
                                parsed["ai_model"] = model
                                return parsed
                    elif response.status_code in [401, 403] or "API key not valid" in response.text:
                        self.last_audio_error = "auth_error"
                        logger.error(f"Gemini API key rejected during audio analysis: {response.text[:200]}")
                        break
                    elif response.status_code == 429 or "RESOURCE_EXHAUSTED" in response.text:
                        self.last_audio_error = "rate_limit"
                        logger.warning(f"Gemini Audio API quota/rate limit (429) hit for {model}, trying next model in cascade...")
                        continue
                    else:
                        logger.warning(f"Gemini Audio API returned {response.status_code} for {model}: {response.text[:300]}")
                except Exception as e:
                    logger.error(f"Error calling Gemini Audio with {model}: {e}")
                    continue

        return None


# Global singleton instance
gemini_service = GeminiService()

