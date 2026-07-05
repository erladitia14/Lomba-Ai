import json
import re
from html import unescape
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import current_app


def _extract_json_object(content):
    content = content.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", content, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        content = fenced.group(1).strip()

    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1 or start >= end:
        raise ValueError("AI response does not contain a JSON object")

    json_text = content[start:end + 1]
    try:
        return json.loads(json_text)
    except json.JSONDecodeError:
        repaired = _repair_json_text(json_text)
        try:
            return json.loads(repaired)
        except json.JSONDecodeError as exc:
            lenient_questions = _extract_questions_lenient(json_text)
            if lenient_questions:
                return {"questions": lenient_questions}
            raise ValueError(f"AI returned invalid JSON near: {_json_error_context(json_text, exc)}") from exc


def _repair_json_text(json_text):
    # Common LLM mistakes: trailing commas and missing commas between object fields.
    json_text = re.sub(r",\s*([}\]])", r"\1", json_text)
    json_text = re.sub(r'"\s*\n\s*"(question|options|answer|explanation|source)"\s*:', r'",\n      "\1":', json_text)
    json_text = re.sub(r'(\]|\})\s*\n\s*"(question|options|answer|explanation|source)"\s*:', r'\1,\n      "\2":', json_text)
    json_text = re.sub(r'(\}|\])\s*\n\s*(\{|\[)', r'\1,\n    \2', json_text)
    return json_text


def _extract_questions_lenient(json_text):
    questions = []
    for block in _iter_object_blocks(json_text):
        item = _parse_question_block(block)
        if item:
            questions.append(item)
    return questions


def _iter_object_blocks(text):
    depth = 0
    start = None
    in_string = False
    escaped = False

    for index, char in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            if depth == 0:
                start = index
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0 and start is not None:
                yield text[start:index + 1]
                start = None


def _parse_question_block(block):
    if '"question"' not in block or '"options"' not in block or '"answer"' not in block:
        return None

    question = _field_string(block, "question")
    answer = _field_string(block, "answer")
    explanation = _field_string(block, "explanation")
    source = _field_string(block, "source")
    options = _field_array(block, "options")

    if not question or not answer or len(options) != 4:
        return None

    return {
        "question": question,
        "options": options,
        "answer": answer,
        "explanation": explanation or f"Jawaban yang tepat adalah {answer}.",
        "source": source,
    }


def _field_string(block, field):
    match = re.search(rf'"{field}"\s*:\s*"((?:\\.|[^"\\])*)"', block, flags=re.DOTALL)
    if not match:
        return ""
    return _decode_json_string(match.group(1))


def _field_array(block, field):
    match = re.search(rf'"{field}"\s*:\s*\[(.*?)\]', block, flags=re.DOTALL)
    if not match:
        return []
    return [_decode_json_string(item) for item in re.findall(r'"((?:\\.|[^"\\])*)"', match.group(1))]


def _decode_json_string(value):
    try:
        return json.loads(f'"{value}"').strip()
    except json.JSONDecodeError:
        return value.strip()


def _json_error_context(json_text, exc):
    start = max(0, exc.pos - 160)
    end = min(len(json_text), exc.pos + 160)
    snippet = json_text[start:end].replace("\n", " ")
    return f"line {exc.lineno} column {exc.colno}: {snippet}"


def _clean_value(value, max_chars=700):
    value = unescape(str(value or ""))
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"[`*_#>|\[\]{}]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value[:max_chars].strip()


def _normalize_options(options):
    if isinstance(options, dict):
        ordered_keys = sorted(options.keys(), key=_option_key)
        options = [options[key] for key in ordered_keys]
    elif isinstance(options, str):
        options = _split_option_text(options)
    elif isinstance(options, list) and len(options) == 1 and isinstance(options[0], str):
        split_options = _split_option_text(options[0])
        if len(split_options) >= 4:
            options = split_options

    if not isinstance(options, list):
        return []

    return _dedupe_options(options)


def _option_key(key):
    key_text = str(key).strip()
    if re.fullmatch(r"[A-Da-d]", key_text):
        return (0, ord(key_text.upper()) - ord("A"))
    if key_text.isdigit():
        return (1, int(key_text))
    return (2, key_text)


def _split_option_text(options_text):
    options_text = str(options_text or "")
    matches = re.findall(
        r"(?:^|\n)\s*[A-Da-d][\).:-]\s*(.+?)(?=\n\s*[A-Da-d][\).:-]\s*|$)",
        options_text,
        flags=re.DOTALL,
    )
    if matches:
        return matches
    return [line for line in options_text.splitlines() if line.strip()]


def _dedupe_options(options):
    unique_options = []
    seen = set()
    for option in options:
        clean_option = _clean_value(option, max_chars=140)
        normalized = clean_option.casefold()
        if not clean_option or normalized in seen:
            continue
        unique_options.append(clean_option)
        seen.add(normalized)
    return unique_options


def _option_matches(value, options):
    normalized_value = _normalize_answer_text(value).casefold()
    return next((option for option in options if option.casefold() == normalized_value), "")


def _normalize_answer_text(value):
    return re.sub(r"^(?:jawaban|answer)?\s*[A-Da-d][\).:-]\s*", "", _clean_value(value, max_chars=140)).strip()


def _coerce_answer(answer, options):
    raw_answer = _clean_value(answer, max_chars=140)
    letter_match = re.fullmatch(r"(?:jawaban\s*)?([A-Da-d])", raw_answer)
    if letter_match:
        index = ord(letter_match.group(1).upper()) - ord("A")
        if index < len(options):
            return options[index]

    answer = _normalize_answer_text(raw_answer)
    if not answer:
        return ""

    matched_answer = _option_matches(answer, options)
    if matched_answer:
        return matched_answer

    for option in options:
        answer_key = answer.casefold()
        option_key = option.casefold()
        if len(answer_key) >= 4 and (answer_key in option_key or option_key in answer_key):
            return option

    return ""


def _normalize_ai_questions(payload, total):
    raw_questions = payload.get("questions") if isinstance(payload, dict) else None
    if not isinstance(raw_questions, list):
        raise ValueError("AI response JSON must contain a questions array")

    questions = []
    for item in raw_questions:
        if not isinstance(item, dict):
            continue

        question = _clean_value(item.get("question", ""), max_chars=900)
        options = item.get("options", [])
        explanation = _clean_value(item.get("explanation", ""), max_chars=700)
        source = _clean_value(item.get("source", ""), max_chars=240)

        if not question:
            continue

        clean_options = _normalize_options(options)
        answer = _coerce_answer(item.get("answer", ""), clean_options)
        if len(clean_options) != 4 or not answer:
            continue

        questions.append({
            "question": question,
            "options": clean_options,
            "answer": answer,
            "explanation": explanation or f"Jawaban yang tepat adalah {answer}.",
            "source": source,
        })

        if len(questions) >= total:
            break

    return questions


def _generate_questions_with_gemini(text, total):
    api_key = current_app.config.get("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    model = current_app.config["GEMINI_MODEL"]
    timeout = current_app.config.get("GEMINI_TIMEOUT", 120)
    material = text[: current_app.config.get("GEMINI_MAX_INPUT_CHARS", 14000)]
    prompt = f"""
Buat {total} soal pilihan ganda berkualitas dari materi PDF berikut.

Aturan wajib:
- Bahasa Indonesia.
- Setiap soal punya tepat 4 opsi jawaban.
- Jawaban benar harus sama persis dengan salah satu opsi, bukan huruf A/B/C/D.
- Distraktor harus masuk akal dan tidak terlalu mudah ditebak.
- Explanation singkat menjelaskan alasan jawaban benar.
- Source berisi potongan kalimat/paragraf pendukung dari materi, maksimal 180 karakter.
- Jangan memakai Markdown, HTML, bullet list, numbering, atau teks di luar JSON.
- Pastikan JSON valid: semua string memakai petik dua, tidak ada trailing comma, dan tidak ada komentar.

Format JSON wajib:
{{
  "questions": [
    {{
      "question": "...",
      "options": ["A", "B", "C", "D"],
      "answer": "A",
      "explanation": "...",
      "source": "..."
    }}
  ]
}}

Materi PDF:
{material}
""".strip()

    body = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": "Kamu adalah pembuat soal edukasi yang akurat dan hanya menghasilkan JSON valid.\n\n" + prompt}
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 4000,
            "responseMimeType": "application/json",
        },
    }

    request = Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Gemini HTTP {exc.code}: {detail[:500]}") from exc
    except URLError as exc:
        raise RuntimeError(f"Gemini connection failed: {exc.reason}") from exc

    content = _parse_gemini_response(response_payload)
    parsed_content = _extract_json_object(content)
    return _normalize_ai_questions(parsed_content, total)


def _parse_gemini_response(response_payload):
    candidates = response_payload.get("candidates", [])
    if not candidates:
        raise ValueError("Gemini response has no candidates")

    parts = candidates[0].get("content", {}).get("parts", [])
    content = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
    if not content.strip():
        raise ValueError("Gemini response has no text content")

    return content

def generate_questions(text, total=10):
    if not current_app.config.get("GEMINI_ENABLED", True):
        raise RuntimeError("Gemini harus aktif. Generator lokal/fallback manual tidak tersedia.")

    questions = _generate_questions_with_gemini(text, total)
    if not questions:
        raise RuntimeError("Gemini tidak menghasilkan soal valid.")

    return questions

