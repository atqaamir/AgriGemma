"""
Batch translation endpoint.

Uses the same Google AI Studio key already configured for the chatbot to
translate a list of strings in a single Gemma prompt call.  Results are
cached by the browser (localStorage) so the API is only called once per
unique string per language.

POST /api/translate
  Body:     { "texts": ["...", ...], "target": "ur" }
  Response: { "translations": { "original": "translated", ... } }
"""
import json
import logging
import os
import urllib.error
import urllib.request

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)
translate_bp = Blueprint("translate", __name__)

_BASE = "https://generativelanguage.googleapis.com/v1beta"


def _translate_with_gemma(strings: list[str], target_lang: str = "ur") -> dict[str, str]:
    api_key = os.getenv("GOOGLE_API_KEY", "")
    model = os.getenv("GOOGLE_AI_MODEL", "gemma-4-26b-a4b-it")

    if not api_key:
        logger.warning("GOOGLE_API_KEY not set — returning originals unchanged")
        return {s: s for s in strings}

    lang_label = "Urdu (اردو)" if target_lang == "ur" else target_lang
    json_list = json.dumps(strings, ensure_ascii=False)

    prompt = (
        f"Translate these English strings to {lang_label}. "
        "Return ONLY a valid JSON object mapping each original English string to its "
        "translation. No markdown code fences, no explanation — just the raw JSON object.\n\n"
        f"Strings: {json_list}"
    )

    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2048},
    }).encode()

    url = f"{_BASE}/models/{model}:generateContent?key={api_key}"
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())

        raw = data["candidates"][0]["content"]["parts"][0]["text"].strip()

        # Strip markdown fences if the model wraps the JSON
        if "```" in raw:
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else parts[0]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip().rstrip("`").strip()

        translations = json.loads(raw)
        return {s: str(translations.get(s, s)) for s in strings}

    except Exception as exc:
        logger.warning("Translation API error: %s", exc)
        return {s: s for s in strings}


@translate_bp.post("/api/translate")
def translate():
    body = request.get_json(silent=True) or {}
    texts = body.get("texts", [])
    target = body.get("target", "ur")

    if not isinstance(texts, list) or target not in ("ur",):
        return jsonify({"error": "invalid input"}), 400

    # Deduplicate, strip blanks, cap at 100 strings per call
    unique = list(dict.fromkeys(
        str(t).strip() for t in texts if t and str(t).strip()
    ))[:100]

    if not unique:
        return jsonify({"translations": {}})

    translations = _translate_with_gemma(unique, target)
    return jsonify({"translations": translations})
