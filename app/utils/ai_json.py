"""Tolerant JSON extraction for AI answers made without JSON mode."""
import json


def parse_json_object(text) -> dict | None:
    """The first complete JSON object in an AI answer, or None.

    Handles ```json fences, a chatty prefix ("Sure! Here is…") and text after the object.
    Braces inside strings are skipped, so the object ends at its real closing brace.
    """
    if isinstance(text, dict):
        return text
    if not text:
        return None
    s = str(text)
    start = s.find("{")
    while start != -1:
        depth, in_str, esc = 0, False, False
        for i in range(start, len(s)):
            c = s[i]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
            elif c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(s[start:i + 1])
                    except ValueError:
                        break
                    if isinstance(obj, dict):
                        return obj
                    break
        start = s.find("{", start + 1)
    return None
